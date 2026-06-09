import logging
import re
import time
from threading import Thread
from typing import Any, Optional

import mido

from ..controller.base import (
    BaseMidibox,
    General,
    GeneralPedal,
    Layer,
    Pedal,
    PropChange,
    PropHandler,
)
from .mido_regs import (
    MidiboxDefs,
    MidiboxCmd,
    GeneralState,
    LayerState,
    GENERAL_SYNC,
    LAYER_SYNC,
)
from .reg_struct import load_from_reg, update_reg_from_handler

READ_TIMEOUT = 1.0


def get_first_diff_index(a: list[int], b: list[int], reverse: bool) -> Optional[int]:
    r = reversed(range(len(a))) if reverse else range(len(a))
    for i in r:
        if a[i] != b[i]:
            return i
    return None


def get_diff_range(a: list[int], b: list[int]) -> Optional[range]:
    di_b, di_e = [get_first_diff_index(a, b, rev) for rev in [False, True]]
    if di_b is None or di_e is None:
        return None
    return range(di_b, di_e)


class PortNotFoundError(Exception):
    pass


class MidoMidibox(BaseMidibox):
    PERIODIC_CHECK = False

    _config: dict[int, List[int]]
    _do_init: dict[PropHandler, bool]

    def __init__(self, port_name: str = "XIAO nRF52840", client_name: Optional[str] = None, virtual: bool = False, find: bool = True, debug: bool = False) -> None:
        self._log = logging.getLogger(__name__)
        self._port_name = port_name
        self._client_name = client_name
        self._virtual = virtual
        self._find = find
        self._debug = debug

        self.portout: Optional[mido.ports.BaseOutput] = None
        self.portin: Optional[mido.ports.BaseInput] = None

        super().__init__()

        self._do_init = {}
        self._config = {}

        self._cb_data: Optional[list[int]] = None
        self._cb_data_waiting: Optional[Tuple[int, int, int]] = None

        self._midi_thread_exit = False
        self._midi_thread = Thread(target=self._connection_check)

    def connect(self) -> None:
        self._open_port()
        self._midi_thread.start()
        self._init_config()

    def disconnect(self) -> None:
        self._midi_thread_exit = True
        if self._midi_thread.is_alive():
            self._midi_thread.join()

    def sendmsg(self, msg: mido.Message) -> None:
        if self._debug:
            print("send", mido.format_as_string(msg, False))

        if self.portout:
            self.portout.send(msg)
        else:
            self._log.warning("write failed, portout is None: " + mido.format_as_string(msg, False))

    def set_props(self, props: list[PropChange]) -> None:
        #done = []
        origs: dict[int, list[int]] = {}
        pprops: list[Optional[PropChange]] = [*props, None]
        for p, np in zip(pprops, pprops[1:]):
            if p is None:
                # This not happend
                continue
            s = p.source if isinstance(p, PropChange) else None
            ns = np.source if isinstance(np, PropChange) else None

            if isinstance(s, General):
                index = MidiboxDefs.LAYER_ID_GLOBAL
                if index not in origs:
                    origs[index] = self._config[index].copy()
                self._update_general_config({p.name: p.value})
            elif isinstance(s, GeneralPedal):
                index = MidiboxDefs.LAYER_ID_GLOBAL
                if index not in origs:
                    origs[index] = self._config[index].copy()
                self._update_general_pedal_config(s, [p.name])
            elif isinstance(s, Layer):
                index = s._index
                if index not in origs:
                    origs[index] = self._config[index].copy()
                self._update_layer_config(s, [p.name])
            elif isinstance(s, Pedal):
                index = s._layer._index
                if index not in origs:
                    origs[index] = self._config[index].copy()
                self._update_pedal_config(s, [p.name])

            if not self._same_layer(s, ns):
                self._write_diff(index, self._config[index], origs[index])
                del origs[index]

    def _layer_index(self, x: PropHandler | None) -> Optional[int]:
        if isinstance(x, Layer):
            index = x._index
        elif isinstance(x, Pedal):
            index = x._layer._index
        else:
            index = None
        return index

    def _same_layer(self, a: PropHandler | None, b: PropHandler | None) -> bool:
        i = tuple(self._layer_index(x) for x in (a, b))
        return i[0] == i[1] and i[0] is not None

    def initialize(self) -> None:
        self._do_init[self.general] = True
        #self._write_general_config()
        for i, lr in enumerate(self.layers):
            self._do_init[lr] = True
            #self._write_layer_config(lr)

    def _open_port(self) -> None:
        if self._find:
            def findSubstr(strings: list[str], substr: str) -> str:
                for i in strings:
                    if substr in i:
                        return i
                raise PortNotFoundError(f'Midibox port {substr} not found in: ' + ", ".join(strings))
            self._input_port_name = findSubstr(mido.get_input_names(), self._port_name)
            self._output_port_name = findSubstr(mido.get_output_names(), self._port_name)
        else:
            self._input_port_name = self._output_port_name = self._port_name

        in_name = str(self._input_port_name)
        out_name = str(self._output_port_name)
        if self._virtual:
            in_name += "_input"
            out_name += "_output"

        api = None
        #api = 'UNIX_JACK'
        #self.ioport = mido.open_ioport(io_name, client_name=self._client_name, virtual=virtual, api=api)
        #self.portin = self.ioport.input
        #self.portout = self.ioport.output

        self._log.info(f"Midibox using {self._port_name} ({self._client_name})")
        self.portout = mido.open_output(self._output_port_name, client_name=self._client_name, virtual=self._virtual, api=api)
        self.portin = mido.open_input(self._input_port_name, client_name=self._client_name, virtual=self._virtual, api=api)

        #if self.portin is None:
        # Let the patch to connect
        if self._virtual:
            time.sleep(0.3)

        self.portin.callback = self._input_callback

    def close(self):
        if self.portin is not None:
            self.portin.close()
        if self.portout  is not None:
            self.portout.close()
        self.portout = None
        self.portin = None

    def _connection_check(self) -> None:
        checking = False
        self._midi_last_activity = time.time()
        while not self._midi_thread_exit:
            time.sleep(0.2)
            if not self.PERIODIC_CHECK:
                self._midi_last_activity = time.time()
            if time.time() > self._midi_last_activity + 1:
                if time.time() > self._midi_last_activity + 2:
                    self._log.info("Midibox reconnecting")
                    self.close()

                    while self.portin is None and not self._midi_thread_exit:
                        try:
                            self._open_port()
                        except PortNotFoundError:
                            time.sleep(0.2)
                            continue

                        try:
                            self._init_config(retries=1)
                        except ConnectionError:
                            self.close()

                    self.emit_all()

                elif not checking:
                    checking = True
                    self._send_mbreq(MidiboxCmd.READ_REQ, MidiboxDefs.LAYER_ID_GLOBAL, 0, 1)
            elif checking:
                checking = False

    def _input_callback(self, msg: mido.Message) -> None:
        self._midi_last_activity = time.time()

        if self._debug:
            print("recv", mido.format_as_string(msg, False))
        try:
            if not self._rc_callback(msg):
                self.input_callback(msg)
        except Exception as e:
            print(e)


    def _init_config(self, retries: Optional[int] = None, timeout: float = READ_TIMEOUT) -> None:
        self._read_general_config(retries, timeout)

        for lr in self.layers:
            self._read_layer_config(lr, retries, timeout)

        c = self._config.get(MidiboxDefs.LAYER_ID_GLOBAL)
        if c is None:
            return

        p = [
            PropChange(self.general, "_check-keep-alive", self.PERIODIC_CHECK),
            PropChange(self.general, "_send-adc-rawdata", False),
        ]
        self.set_props(p)

    def _send_mbreq(self, cmd: int, layer: int, offset: int, reqlen: int, msg: list[int] = []) -> None:
        c = ((cmd & 0x07) << 4) | (layer & 0x0F)
        assert c < 0xF0
        if msg:
            assert reqlen == len(msg)
        self.send([0xF0, MidiboxDefs.SYSEX_ID1, c, offset, reqlen] + msg + [0xF7])

    def _wait_for_cb_data(self, timeout: float = READ_TIMEOUT) -> Optional[list[int]]:
        while not self._cb_data and timeout > 0:
            time.sleep(0.01)
            timeout -= 0.01
        ret = self._cb_data
        #assert ret is not None
        if not ret:
            self._log.error("Error: no data received")
        self._cb_data = None

        return ret

    def _read_regs(self, lr_index: int, firstreg: int, lastreg: int, retries: Optional[int] = None, timeout: float = READ_TIMEOUT) -> List[int]:
        ret: List[int] = []
        MAXREQ = 32
        while lastreg > firstreg:
            reqlen = min(lastreg - firstreg, MAXREQ)

            c = None
            burst_retries = retries
            while c is None:
                self._cb_data = None
                self._cb_data_waiting = (lr_index, firstreg, reqlen)
                self._send_mbreq(MidiboxCmd.READ_REQ, lr_index, firstreg, reqlen)
                c = self._wait_for_cb_data(timeout)
                if c is None:
                    if burst_retries is not None and burst_retries == 0:
                        raise ConnectionError("No response for read request")
                    elif burst_retries is not None and burst_retries > 0:
                        burst_retries -= 1
                    print("Retrying read reg")

            ret += c
            firstreg += reqlen
        return ret

    def _rc_callback(self, msg: mido.Message) -> bool:
        if msg.type == 'sysex' and len(msg.data) > 2 and msg.data[0] == MidiboxDefs.SYSEX_ID1:
            cmd = (msg.data[1] >> 4) & 0x07
            layer = msg.data[1] & 0x0F
            offset = msg.data[2]
            reqlen = msg.data[3]
            # FIXME: only READ_RES
            data = list(msg.data[4:])

            if reqlen != len(msg.data) - 4:
                self._log.error("Request length != data length")
                return True

            if self._cb_data_waiting == (layer, offset, reqlen):
                self._cb_data = data
                self._cb_data_waiting = None
            # Unrequested update
            elif cmd == MidiboxCmd.READ_RES:
                grp: Optional[PropHandler] = None

                if layer < 8:
                    grp = self.layers[layer]
                elif layer == MidiboxDefs.LAYER_ID_GLOBAL:
                    grp = self.general

                if grp is not None:
                    cfg = self._config[layer]
                    cfg[offset:offset + reqlen] = data
                    self._load_config(grp)
            return True
        return False

    def _load_config(self, source: PropHandler) -> None:
        if isinstance(source, General):
            self._load_general_config()
        elif isinstance(source, GeneralPedal):
            self._load_general_config()
        elif isinstance(source, Layer):
            self._load_layer_config(source)
        elif isinstance(source, Pedal):
            self._load_layer_config(source._layer)

    def _write_general_config(self) -> None:
        c = self._config.get(MidiboxDefs.LAYER_ID_GLOBAL)
        if c is None:
            self._log.info("not connected")
            return

    def _update_general_config(self, names: dict[str, Any]) -> None:
        reg = GeneralState.unpack(self._config[MidiboxDefs.LAYER_ID_GLOBAL])

        # Generic field update from sync map (handles enabled, tempo)
        update_reg_from_handler(self.general, reg, list(names), GENERAL_SYNC)

        # Internal flags not in the prop system
        if "_check-keep-alive" in names:
            reg.check_keep_alive = names["_check-keep-alive"]
        if "_send-adc-rawdata" in names:
            reg.debug_smsg_print = names["_send-adc-rawdata"]

        self._do_init[self.general] = False
        self._config[MidiboxDefs.LAYER_ID_GLOBAL] = reg.pack()

    def _update_general_pedal_config(self, p: GeneralPedal, names: list[str]) -> None:
        reg = GeneralState.unpack(self._config[MidiboxDefs.LAYER_ID_GLOBAL])
        update_reg_from_handler(self.general, reg, names, GENERAL_SYNC, sub_index=p._index)
        self._config[MidiboxDefs.LAYER_ID_GLOBAL] = reg.pack()

    def _read_general_config(self, retries: Optional[int] = None, timeout: float = READ_TIMEOUT) -> None:
        c = self._read_regs(MidiboxDefs.LAYER_ID_GLOBAL, 0, GeneralState.SIZE, retries, timeout)
        self._config[MidiboxDefs.LAYER_ID_GLOBAL] = c
        self._load_general_config()

    def _load_general_config(self) -> None:
        reg = GeneralState.unpack(self._config[MidiboxDefs.LAYER_ID_GLOBAL])
        load_from_reg(self.general, reg, GENERAL_SYNC)

    def _write_layer_config(self, layer: Layer) -> None:
        c = self._config.get(layer)
        if c is None:
            self._log.info("not connected")
            return

        orig_c = c.copy()
        # Clear W/O flags
        orig_c[2] = 0

    def _update_layer_config(self, lr: Layer, names: list[str]) -> None:
        reg = LayerState.unpack(self._config[lr._index])

        # Generic field update from sync map
        update_reg_from_handler(lr, reg, names, LAYER_SYNC)

        # Custom: encode program into pgm+bs+bs_lsb
        if "program" in names:
            m = re.fullmatch(r"_pgm_(\d+)_(\d+)_(\d+)_", lr.program)
            if m is not None:
                g = m.groups()
                reg.pgm = int(g[0]) - 1
                reg.bs = int(g[1])
                reg.bs_lsb = int(g[2])
        self._config[lr._index] = reg.pack()

    def _update_pedal_config(self, p: Pedal, names: list[str]) -> None:
        reg = LayerState.unpack(self._config[p._layer._index])
        update_reg_from_handler(p._layer, reg, names, LAYER_SYNC, sub_index=p._index)
        self._config[p._layer._index] = reg.pack()

    def _write_diff(self, id: int, c: list[int], orig_c: list[int]) -> None:
        r = get_diff_range(c, orig_c)
        if r is not None:
            self._send_mbreq(MidiboxCmd.WRITE_REQ, id, r.start, len(r) + 1, c[r.start:r.stop + 1])

    def _read_layer_config(self, layer: Layer, retries: Optional[int] = None, timeout: float = READ_TIMEOUT) -> None:
        lr = layer
        self._config[lr._index] = self._read_regs(lr._index, 0, LayerState.SIZE, retries, timeout)
        self._load_layer_config(lr)

    def _load_layer_config(self, layer: Layer) -> None:
        lr = layer
        reg = LayerState.unpack(self._config[lr._index])

        # Generic field loading from sync map
        load_from_reg(lr, reg, LAYER_SYNC)

        # Custom: decode program from pgm+bs+bs_lsb
        pc = reg.pgm + 1
        lr.program = f"_pgm_{pc}_{reg.bs}_{reg.bs_lsb}_"
