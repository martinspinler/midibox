import time
import mido
from typing import List, Optional, Tuple

from .base import BaseMidibox, MidiBoxLayer

from threading import Thread


class PortNotFoundError(Exception):
    pass

READ_TIMEOUT = 1.0

class Midibox(BaseMidibox):
    _SYSEX_ID = 0x77
    _LAYER_GLOBAL = 15

    _CMD_INFO      = 0
    _CMD_UPDATE    = 1
    _CMD_READ_REQ  = 2
    _CMD_READ_RES  = 3
    _CMD_WRITE_REQ = 4
    _CMD_WRITE_ACK = 5
    _CMD_WRITE_NAK = 6

    _config: Optional[List[int]]

    def __init__(self, port_name: str="XIAO nRF52840", client_name=None, virtual=False, find=True, debug=False):
        self._port_name = port_name
        self._client_name = client_name
        self._virtual = virtual
        self._find = find
        self._debug = debug

        self.portout = None
        self.portin = None

        super().__init__()

        self._do_init = False
        self._config = None
        for lr in self.layers:
            lr._config = None
            lr._do_init = False

        self._cb_data = None
        self._cb_data_waiting: Optional[Tuple[int, int, int]] = None

        if self._debug:
            self._callbacks.append(lambda msg: print("recv", mido.format_as_string(msg, False)))

        self._callbacks.append(self._rc_callback)
        self._midi_thread_exit = False
        self._midi_thread = Thread(target=self._connection_check)

    def _wait_for_cb_data(self, timeout: float=READ_TIMEOUT):
        while not self._cb_data and timeout > 0:
            time.sleep(0.01)
            timeout -= 0.01
        ret = self._cb_data
        #assert ret is not None
        if not ret:
            print("Error: no data received")
        self._cb_data = None
        return ret

    def _disconnect(self):
        self._midi_thread_exit = True
        if self._midi_thread.is_alive():
            self._midi_thread.join()

    def _connect(self):
        self._open_port()
        self._midi_thread.start()
        self._init_configuration()

    def _open_port(self):
        if self._find:
            def findSubstr(strings, substr):
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

        print(f"RolandMidibox: using {self._port_name} ({self._client_name})")
        self.portout = mido.open_output(self._output_port_name, client_name=self._client_name, virtual=self._virtual, api=api)
        self.portin  = mido.open_input(self._input_port_name, client_name=self._client_name, virtual=self._virtual, api=api)

        # Let the patch to connect
        if self._virtual:
            time.sleep(0.3)

        self.portin.callback = self.inputCallback

    def _connection_check(self):
        checking = False
        self._midi_last_activity = time.time()
        while not self._midi_thread_exit:
            time.sleep(0.2)
            if time.time() > self._midi_last_activity + 1:
                if time.time() > self._midi_last_activity + 2:
                    print("Reconnecting")
                    self.portout = None
                    self.portin = None

                    while self.portin is None and not self._midi_thread_exit:
                        try:
                            self._open_port()
                        except PortNotFoundError:
                            time.sleep(0.2)
                            continue

                        try:
                            self._init_configuration(retries=1)
                        except ConnectionError:
                            self.portout = None
                            self.portin = None

                    self.emit_all()

                elif not checking:
                    checking = True
                    #print("Setting check and requesting")
                    self._send_mbreq(self._CMD_READ_REQ, self._LAYER_GLOBAL, 0, 1)
            elif checking:
                checking = False
                #print("Resetting check")

    def inputCallback(self, msg):
        self._midi_last_activity = time.time()
        super().inputCallback(msg)

    def _init_configuration(self, retries: Optional[int]=None, timeout: float=READ_TIMEOUT):
        self._read_config(retries, timeout)

        # INFO: all debug, not enable
        #self._config[2] |= 0x7e

        for lr in self.layers:
            self._read_layer_config(lr, retries, timeout)

    def _write_sysex(self, msg):
        self._write([0xF0] + msg + [0xF7])

    def _send_mbreq(self, cmd: int, layer: int, offset: int, reqlen: int, msg = []):
        c = ((cmd & 0x07) << 4) | (layer & 0x0F)
        assert c < 0xF0
        if msg:
            assert reqlen == len(msg)
        self._write([0xF0, self._SYSEX_ID, c, offset, reqlen] + msg + [0xF7])

    def _write(self, b: bytes):
        msg = mido.Message.from_bytes(b)
        if self._debug:
            print("send", mido.format_as_string(msg, False))

        if self.portout:
            self.portout.send(msg)
        else:
            print("write failed, portout is None:", mido.format_as_string(msg, False))

    def _read_regs(self, lr_index, firstreg, lastreg, retries: Optional[int]=None, timeout: float=READ_TIMEOUT) -> List[int]:
        ret: List[int] = []
        MAXREQ = 16
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

    def _initialize(self):
        self._do_init = True
        self._write_config()
        for i, lr in enumerate(self.layers):
            lr._do_init = True
            self._write_layer_config(lr)

    def _write_config(self, name=None, value=None):
        c = self._config
        if c is None:
            print("not connected")
            return

        c[0] = (self._config[0] | 1) if self._enable else (self._config[0] & ~1)
        c[2] = 1 if self._do_init else 0
        #c[3] = self._selected_layer
        self._do_init = False
        #c[4:6] = [120, 0] # tempo
        self._send_mbreq(self._CMD_WRITE_REQ, self._LAYER_GLOBAL, 0, 3, c[0:3])

    def _read_config(self, retries: Optional[int]=None, timeout: float=READ_TIMEOUT):
        self._config = self._read_regs(self._LAYER_GLOBAL, 0, 6+16, retries, timeout)
        self._enable = True if self._config[0] & 1 else False

    def _write_layer_config(self, layer: MidiBoxLayer, name=None, value=None):
        lr = layer
        c = lr._config
        if c is None:
            print("not connected")
            return

        orig_c = c.copy()
        # Clear W/O flags
        orig_c[2] = 0

        c[0] = 1 if lr._enabled and not self._mute else 0
        c[0] |= 2 if lr._active else 0

        c[2] = 1 if lr._do_init else 0
        lr._do_init = False
        c[6:9] = [lr._rangel, lr._rangeu, lr._volume]
        c[10:12] = [lr._transposition + 64, lr._transposition_extra + 64]
        c[12:16] = [lr._release + 64, lr._attack + 64, lr._cutoff + 64, lr._decay + 64]

        if lr._program in lr.programs:
            p = layer.programs[layer._program]
            c[3:6] = [p.pc-1, p.msb, p.lsb]

        for i in range(len(lr.pedals)):
            c[16+i] = lr.pedals[i]._cc
            c[24+i] = lr.pedals[i]._mode # Disable pedal temporarily

        c[32] = lr._percussion
        for i in range(9):
            c[33+i] = getattr(lr, f'_harmonic_bar{i}')

        change_first = None
        change_last = None
        for i in range(len(c)):
            if c[i] != orig_c[i] and change_first is None:
                change_first = i
                break

        for i in reversed(range(len(c))):
            if c[i] != orig_c[i] and change_last is None:
                change_last = i
                break

        if change_first is None or change_last is None: # Both must be None or both must be int value
            return

        self._send_mbreq(self._CMD_WRITE_REQ, lr._index, change_first, change_last - change_first + 1, c[change_first:change_last+1])

    def _read_layer_config(self, layer: MidiBoxLayer, retries: Optional[int]=None, timeout: float=READ_TIMEOUT):
        lr = layer
        lr._config = self._read_regs(lr._index, 0, 42, retries, timeout)
        self._load_layer_config(lr)

    def _load_layer_config(self, layer: MidiBoxLayer):
        lr = layer
        c = lr._config
        lr._enabled = True if c[0] & 1 else False
        lr._active = True if c[0] & 2 else False
        lr._rangel, lr._rangeu, lr._volume = c[6], c[7], c[8]
        lr._transposition = c[10] - 64
        lr._transposition_extra = c[11] - 64
        lr._release = c[12] - 64
        lr._attack = c[13] - 64
        lr._cutoff = c[14] - 64
        lr._decay = c[15] - 64

        pc, bs, bs_lsb = c[3:6]
        program = '-unknown-'
        for pn in layer.programs:
            p = layer.programs[pn]
            if p.pc == pc + 1 and p.msb == bs and p.lsb == bs_lsb:
                program = pn
                break

        lr._program = program

        for i in range(len(lr.pedals)):
             lr.pedals[i]._cc = c[16+i]
             lr.pedals[i]._mode = c[24+i]

        lr._percussion = c[32]
        for i in range(9):
            setattr(lr, f'_harmonic_bar{i}', c[33+i])

    def _rc_callback(self, msg):
        if msg.type == 'sysex' and len(msg.data) > 2 and msg.data[0] == self._SYSEX_ID:
            cmd = (msg.data[1] >> 4) & 0x07
            layer = msg.data[1] & 0x0F
            offset = msg.data[2]
            reqlen = msg.data[3]
            # FIXME: only READ_RES
            data = list(msg.data[4:])

            #assert offset == 0
            assert reqlen == len(msg.data) - 4

            if self._cb_data_waiting == (layer, offset, reqlen):
                self._cb_data = data
                self._cb_data_waiting = None
            else:
                if cmd == self._CMD_READ_RES and layer < 8:
                    lr = self.layers[layer]
                    for i in range(len(data)):
                        lr._config[offset + i] = data[i]

                    program = lr._program
                    volume = lr._volume

                    self._load_layer_config(lr)

                    # Emit value
                    self.emit_all()
                    if lr._program != program:
                        self.emit_control('program')
                        #print("Emit")
                    if lr._program != volume:
                        self.emit_control('volume')
