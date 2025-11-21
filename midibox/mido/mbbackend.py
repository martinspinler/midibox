import time
import mido
import re
import logging
from typing import List, Optional, Tuple, Any

from ..controller.base import BaseMidibox, Layer, PropHandler, General, Pedal, PropChange, Program, prg_id

from threading import Thread


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


def sbit(val: int, n: int, set: bool = True, numbits: int = 8) -> int:
    if set:
        return val | (1 << n)
    else:
        return val & (((1 << numbits) - 1) - (1 << n))


class PortNotFoundError(Exception):
    pass


class MidoMidibox(BaseMidibox):
    PERIODIC_CHECK = False

    _SYSEX_ID = 0x77
    _LAYER_GENERAL = 15

    _CMD_INFO      = 0 # noqa
    _CMD_UPDATE    = 1 # noqa
    _CMD_READ_REQ  = 2 # noqa
    _CMD_READ_RES  = 3 # noqa
    _CMD_WRITE_REQ = 4 # noqa
    _CMD_WRITE_ACK = 5 # noqa
    _CMD_WRITE_NAK = 6 # noqa

    _LR_GENERAL_OFFSETS = {
        "pedal_cc": 6,
        "pedal_mode": 14,
        "pedal_min": 22,
        "pedal_max": 30
    }

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
                index = self._LAYER_GENERAL
                if index not in origs:
                    origs[index] = self._config[index].copy()
                self._update_general_config({p.name: p.value})
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
                    self.portout = None
                    self.portin = None

                    while self.portin is None and not self._midi_thread_exit:
                        try:
                            self._open_port()
                        except PortNotFoundError:
                            time.sleep(0.2)
                            continue

                        try:
                            self._init_config(retries=1)
                        except ConnectionError:
                            self.portout = None
                            self.portin = None

                    self.emit_all()

                elif not checking:
                    checking = True
                    self._send_mbreq(self._CMD_READ_REQ, self._LAYER_GENERAL, 0, 1)
            elif checking:
                checking = False

    def _input_callback(self, msg: mido.Message) -> None:
        self._midi_last_activity = time.time()

        if self._debug:
            print("recv", mido.format_as_string(msg, False))

        if not self._rc_callback(msg):
            self.input_callback(msg)

    def _init_config(self, retries: Optional[int] = None, timeout: float = READ_TIMEOUT) -> None:
        self._read_general_config(retries, timeout)

        for lr in self.layers:
            self._read_layer_config(lr, retries, timeout)

        c = self._config.get(self._LAYER_GENERAL)
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
        self.send([0xF0, self._SYSEX_ID, c, offset, reqlen] + msg + [0xF7])

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
        MAXREQ = 64
        while lastreg > firstreg:
            reqlen = min(lastreg - firstreg, MAXREQ)

            c = None
            burst_retries = retries
            while c is None:
                self._cb_data = None
                self._cb_data_waiting = (lr_index, firstreg, reqlen)
                self._send_mbreq(self._CMD_READ_REQ, lr_index, firstreg, reqlen)
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
        if msg.type == 'sysex' and len(msg.data) > 2 and msg.data[0] == self._SYSEX_ID:
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
            else:
                # Unrequested update
                if cmd == self._CMD_READ_RES:
                    grp: Optional[PropHandler] = None

                    if layer < 8:
                        grp = self.layers[layer]
                    elif layer == self._LAYER_GENERAL:
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
        elif isinstance(source, Layer):
            self._load_layer_config(source)
        elif isinstance(source, Pedal):
            self._load_layer_config(source._layer)

    def _write_general_config(self) -> None:
        c = self._config.get(self._LAYER_GENERAL)
        if c is None:
            self._log.info("not connected")
            return

    def _update_general_config(self, names: dict[str, Any]) -> None:
        c = self._config[self._LAYER_GENERAL]
        if "enable" in names:
            c[0] = sbit(c[0], 0, self.general.enable)

        if "_check-keep-alive" in names:
            c[0] = sbit(c[0], 6, names["_check-keep-alive"])

        if "_send-adc-rawdata" in names:
            c[0] = sbit(c[0], 5, names["_send-adc-rawdata"])

        for i in range(8):
            for n, o in self._LR_GENERAL_OFFSETS.items():
                name = f"{n}{i}"
                if name in names:
                    c[o+i] = getattr(self.general, name)

        #####c[2] = 1 if self._do_init.get(self.general, 1) else 0
        #c[3] = self._selected_layer
        self._do_init[self.general] = False
        #c[4:6] = [120, 0] # tempo

    def _read_general_config(self, retries: Optional[int] = None, timeout: float = READ_TIMEOUT) -> None:
        c = self._read_regs(self._LAYER_GENERAL, 0, 6 + 16 + 16, retries, timeout)
        self._config[self._LAYER_GENERAL] = c
        self._load_general_config()

    def _load_general_config(self) -> None:
        c = self._config[self._LAYER_GENERAL]
        self.general.enable = True if c[0] & 1 else False

        for i in range(8):
            for n, o in self._LR_GENERAL_OFFSETS.items():
                name = f"{n}{i}"
                setattr(self.general, name, c[o+i])

    def _write_layer_config(self, layer: Layer) -> None:
        c = self._config.get(layer)
        if c is None:
            self._log.info("not connected")
            return

        orig_c = c.copy()
        # Clear W/O flags
        orig_c[2] = 0

    def _update_layer_config(self, lr: Layer, names: list[str]) -> None:
        c = self._config[lr._index]
        # FIXME: general

        if "enabled" in names:
            c[0] = sbit(c[0], 0, lr.enabled)
        if "active" in names:
            c[0] = sbit(c[0], 1, lr.active)

        #c[2] = 1 if self._do_init.get(lr, 1) else 0
        #self._do_init[lr] = False

        if "rangel" in names:
            c[6] = lr.rangel
        if "rangeu" in names:
            c[7] = lr.rangeu
        if "volume" in names:
            c[8] = lr.volume
        if "transposition" in names:
            c[10] = lr.transposition + 64
        if "transposition_extra" in names:
            c[11] = lr.transposition_extra + 64
        if "release" in names:
            c[12] = lr.release + 64
        if "attack" in names:
            c[13] = lr.attack + 64
        if "cutoff" in names:
            c[14] = lr.cutoff + 64
        if "decay" in names:
            c[15] = lr.decay + 64

        if "program" in names:
            p = None
            m = re.fullmatch("_pgm_(\d+)_(\d+)_(\d+)_", lr.program)
            if m is not None:
                g = m.groups()
                pc, msb, lsb = int(g[0]), int(g[1]), int(g[2])
                print("SP", lr.program, pc, msb, lsb)
                c[3:6] = [pc - 1, msb, lsb]
        if "percussion" in names:
            c[32] = lr.percussion
        for i in range(9):
            n = f'harmonic_bar{i}'
            if n in names:
                c[33 + i] = getattr(lr, n)
        if "portamento_time" in names:
            c[42] = lr._portamento_time

        if "volume_ch" in names:
            c[43] = lr._volume_ch

    def _update_pedal_config(self, p: Pedal, names: list[str]) -> None:
        lr = p._layer
        i = p._index
        c = self._config[lr._index]

        if "cc" in names:
            c[16 + i] = p.cc
        if "mode" in names:
            c[24 + i] = p.mode # Disable pedal temporarily

    def _write_diff(self, id: int, c: list[int], orig_c: list[int]) -> None:
        r = get_diff_range(c, orig_c)
        if r is not None:
            self._send_mbreq(self._CMD_WRITE_REQ, id, r.start, len(r) + 1, c[r.start:r.stop + 1])

    def _read_layer_config(self, layer: Layer, retries: Optional[int] = None, timeout: float = READ_TIMEOUT) -> None:
        lr = layer
        self._config[lr._index] = self._read_regs(lr._index, 0, 44, retries, timeout)
        self._load_layer_config(lr)

    def _load_layer_config(self, layer: Layer) -> None:
        lr = layer
        c = self._config[lr._index]
        lr.enabled = True if c[0] & 1 else False
        lr.active = True if c[0] & 2 else False
        lr.rangel, lr.rangeu, lr.volume = c[6], c[7], c[8]
        lr.transposition = c[10] - 64
        lr.transposition_extra = c[11] - 64
        lr.release = c[12] - 64
        lr.attack = c[13] - 64
        lr.cutoff = c[14] - 64
        lr.decay = c[15] - 64

        pc, bs, bs_lsb = c[3:6]
        pc += 1
        program = f"_pgm_{pc}_{bs}_{bs_lsb}_"
        lr.program = program

        for i in range(len(lr.pedals)):
            lr.pedals[i].cc = c[16 + i]
            lr.pedals[i].mode = c[24 + i]

        lr.percussion = c[32]
        for i in range(9):
            setattr(lr, f'harmonic_bar{i}', c[33 + i])

        lr.portamento_time = c[42]
        lr.volume_ch = c[43]
