import time
import mido

from .base import BaseMidiBox

class Midibox(BaseMidiBox):
    _SYSEX_ID = 0x77
    _LAYER_GLOBAL = 15

    _CMD_INFO      = 0
    _CMD_UPDATE    = 1
    _CMD_READ_REQ  = 2
    _CMD_READ_RES  = 3
    _CMD_WRITE_REQ = 4
    _CMD_WRITE_ACK = 5
    _CMD_WRITE_NAK = 6

    def __init__(self, port_name="XIAO nRF52840", client_name=None, virtual=False, find=True, debug=False):
        self._port_name = port_name
        self._client_name = client_name
        self._virtual = virtual
        self._find = find
        self._debug = debug

        self.portout = None
        self.portin = None

        super().__init__()

        self._config = None
        for l in self.layers:
            l._config = None

        self._cb_data = None

    def _wait_for_cb_data(self, timeout=0.2):
        while not self._cb_data and timeout > 0:
            time.sleep(0.01)
            timeout -= 0.01
        ret = self._cb_data
        assert ret is not None
        self._cb_data = None
        return ret


    def _connect(self):
        if self._find:
            def findSubstr(strings, substr):
                for i in strings:
                    if substr in i:
                        return i
                raise Exception('Midibox port not found...')

            io_name = findSubstr(mido.get_input_names(), self._port_name)
            in_name = findSubstr(mido.get_input_names(), self._port_name)
            out_name = findSubstr(mido.get_output_names(), self._port_name)
        else:
            in_name = out_name = self._port_name

        if self._virtual:
            in_name += "_input"
            out_name += "_output"

        api = None
        #api = 'UNIX_JACK'
        #self.ioport = mido.open_ioport(io_name, client_name=self._client_name, virtual=virtual, api=api)
        #self.portin = self.ioport.input
        #self.portout = self.ioport.output

        print(f"RolandMidibox: using {self._port_name} ({self._client_name})")
        self.portout = mido.open_output(out_name, client_name=self._client_name, virtual=self._virtual, api=api)
        self.portin  = mido.open_input(in_name, client_name=self._client_name, virtual=self._virtual, api=api)

        # Let the patch to connect
        if self._virtual:
            time.sleep(0.3)

        self.portin.callback = self.inputCallback

        if self._debug:
            self._callbacks.append(lambda msg: print("recv", mido.format_as_string(msg, False)))

        self._callbacks.append(self._rc_callback)
        self._init_configuration()

    def _init_configuration(self):
        self._read_config()

        # INFO: all debug, not enable
        self._config[2] = 0x7e

        for l in self.layers:
            self._read_layer_config(l)

    def _write_sysex(self, msg):
        self._write([0xF0] + msg + [0xF7])

    def _send_mbreq(self, cmd, layer, offset, reqlen, msg = []):
        c = ((cmd & 0x07) << 4) | (layer & 0x0F);
        assert c < 0xF0
        if msg:
            assert reqlen == len(msg)
        self._write([0xF0, self._SYSEX_ID, c, offset, reqlen] + msg + [0xF7])

    def _write(self, b):
        msg = mido.Message.from_bytes(b)
        if self._debug:
            print("send", mido.format_as_string(msg, False))

        if self.portout:
            self.portout.send(msg)

    def _write_config(self):
        c = self._config
        if c is None:
            print("not connected")
            return

        c[0] = (self._config[0] | 1) if self._enable else (self._config[0] & ~1)
        c[2] = 1 if self._initialize else 0
        self._initialize = False
        #c[4:6] = [120, 0] # tempo
        self._send_mbreq(self._CMD_WRITE_REQ, self._LAYER_GLOBAL, 0, 3, c[0:3])

    def _read_config(self,):
        #self._config = None
        self._cb_data = None
        self._send_mbreq(self._CMD_READ_REQ, self._LAYER_GLOBAL, 0, 6+16)
        self._config = self._wait_for_cb_data()

        self._enable = True if self._config[0] & 1 else False

    def _write_layer_config(self, layer):
        l = layer
        c = l._config
        if c is None:
            print("not connected")
            return

        c[0] = 1 if l._active and not self._mute else 0
        c[2] = 1 if l._initialize else 0
        l._initialize = False
        c[6:9] = [l._rangel, l._rangeu, l._volume]
        c[10:12] = [l._transposition + 64, l._transposition_extra + 64]
        c[12:16] = [l._release + 64, l._attack + 64, l._cutoff + 64, l._decay + 64]

        if l._program in l.programs:
            p = layer.programs[layer._program]
            c[3:6] = [p.pc-1, p.msb, p.lsb]

        for i in range(len(l.pedals)):
            c[16+0+i] = l.pedals[i]._cc
            #c[16+8+i] = 0 # Disable pedal temporarily

        self._send_mbreq(self._CMD_WRITE_REQ, l._index, 0, len(c), c)

    def _read_layer_config(self, layer):
        l = layer
        l._config = None
        self._cb_data = None
        self._send_mbreq(self._CMD_READ_REQ, l._index, 0, 16)
        c = self._wait_for_cb_data()

        self._cb_data = None
        self._send_mbreq(self._CMD_READ_REQ, l._index, 16, 16)
        c += self._wait_for_cb_data()

        l._config = c
        l._active = True if c[0] & 1 else False
        l._rangel, l._rangeu, l._volume = c[6], c[7], c[8]
        l._transposition = c[10] - 64
        l._transposition_extra = c[11] - 64
        l._release = c[12] - 64
        l._attack = c[13] - 64
        l._cutoff= c[14] - 64
        l._decay = c[15] - 64

        pc, bs, bs_lsb = c[3:6]
        program = '-unknown-'
        for pn in layer.programs:
            p = layer.programs[pn]
            if p.pc == pc + 1 and p.msb == bs and p.lsb == bs_lsb:
                program = pn
                break

        l._program = program

        for i in range(len(l.pedals)):
             l.pedals[i]._cc = c[16+0+i]
             #l.pedals[i]._mode = c[16+8+i]

    def _rc_callback(self, msg):
        if msg.type == 'sysex' and len(msg.data) > 2 and msg.data[0] == self._SYSEX_ID:
            cmd = (msg.data[1] >> 4) & 0x07
            layer = msg.data[1] & 0x0F
            offset = msg.data[2]
            reqlen = msg.data[3]

            #assert offset == 0
            assert reqlen == len(msg.data) - 4

            self._cb_data = list(msg.data[4:])
            #if cmd == self._CMD_READ_RES and layer == self._LAYER_GLOBAL:
            #    #self._config = list(msg.data[4:])
            #    self._cb_data = list(msg.data[4:])
            #elif cmd == self._CMD_READ_RES and layer < 8:
            #    #self.layers[layer]._config = list(msg.data[4:])
            #    self._cb_data = list(msg.data[4:])
