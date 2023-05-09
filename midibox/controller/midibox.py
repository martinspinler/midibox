import time
import mido

from .base import BaseMidiBox

class Midibox(BaseMidiBox):
    _SYSEX_ID = 0x77

    _CMD_GET_GLOBAL = 1
    _CMD_SET_GLOBAL = 2
    _CMD_GET_LAYER  = 3
    _CMD_SET_LAYER  = 4

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
            self._callbacks.append(lambda msg: print("recv", msg))

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

    def _write(self, b):
        msg = mido.Message.from_bytes(b)
        if self._debug:
            print("send", msg)
        if self.portout:
            self.portout.send(msg)

    def _write_config(self):
        c = self._config
        c[2] = (self._config[2] | 1) if self._enable else (self._config[2] & ~1)
        c[3:4] = [120, 0] # tempo
        self._write_sysex(c)

    def _read_config(self):
        self._config = None
        self._write_sysex([self._SYSEX_ID, self._CMD_GET_GLOBAL])
        while not self._config:
            time.sleep(0.01)
        self._config[1] = self._CMD_SET_GLOBAL

        self._enable = True if self._config[2] & 1 else False

    def _write_layer_config(self, layer):
        l = layer
        c = l._config
        if c is None:
            print("not connected")
            return

        c[3:9] = [
            1 if l._active and not self._mute else 0,
            l._transposition + 64,
            l._rangel, l._rangeu, l._mode, l._transposition_extra + 64,
        ]
        for i in range(len(l.pedals)):
            c[9+2*i+0] = l.pedals[i]._cc
        self._write_sysex(c)

    def _read_layer_config(self, layer):
        l = layer
        l._config = None
        self._write_sysex([self._SYSEX_ID, self._CMD_GET_LAYER, l._index])
        while not l._config:
            time.sleep(0.01)

        l._config[1] = self._CMD_SET_LAYER

        c = l._config
        l._active = True if c[3] & 1 else False
        l._transposition = c[4] - 64
        l._rangel, l._rangeu = c[5], c[6]
        l._mode = c[7]
        l._transposition_extra = c[8] - 64
        for i in range(len(l.pedals)):
             l.pedals[i]._cc = c[9+2*i+0]

    def _rc_callback(self, msg):
        if msg.type == 'sysex' and len(msg.data) > 2 and msg.data[0] == self._SYSEX_ID:
            if msg.data[1] == self._CMD_GET_GLOBAL:
                self._config = list(msg.data[:])
            elif msg.data[1] == self._CMD_GET_LAYER:
                l = msg.data[2]
                self.layers[l]._config = list(msg.data[:])
