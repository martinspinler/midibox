import time
from pydispatch import Dispatcher

clamp = lambda x, l, u: l if x < l else u if x > u else x

class MidiBoxProgram():
    def __init__(self, *args):
        keys = ['pc', 'msb', 'lsb', 'sysex', 'short', 'name']
        for k, v in zip(keys, args): setattr(self, k, v)


class MidiBoxLayer(Dispatcher):
    _events_ = ['control_change', 'transposition', 'active']
    controls = ['transposition', 'range', 'active', "channel_in_mask", "channel_out_offset"]
    programs = {          #PC MSB LSB
        'piano'         : MidiBoxProgram( 1,  0, 68, [[0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00]], 'Pn', 'Piano'),
        'epiano'        : MidiBoxProgram( 5,  0, 67, [[0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02]], 'eP', 'E-Piano'),
        'bass'          : MidiBoxProgram(33,  0, 71, [[0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04]], 'Bs', 'Bass'),
        'hammond'       : MidiBoxProgram(17, 32, 68, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]], 'Hm', 'Hammond'),
        'vibraphone'    : MidiBoxProgram(12,  0,  0, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]], 'Vp', 'Vibraphone'),
        'marimba'       : MidiBoxProgram(13,  0, 64, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]], 'Mb', 'Marimba'),
        'fretlessbass'  : MidiBoxProgram(36,  0,  0, [[0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04]], 'FB', 'Fretlett Bass'),
    }

    pedal_cc = {
        'Unknown': 0,
        'Sustain': 64,
        'Expression': 11,
        'Portamento': 65,
        'Portamento time': 5,
        'Sostenuto': 66,
        'Soft': 67,
        'Legato': 68,
        'Hold': 69,
        'GPC1': 16,
        'GPC2': 17,
        'GPC3': 18,
        'GPC4': 19,
    }
    def __init__(self, dev, index):
        self._index = index
        self._part = (index + 1) & 0xF # if index != 9 else 0
        self._dev = dev
        self._transposition = 0
        self._active = False
        self._channel_in_mask = 0
        self._channel_out_offset = 0
        self._rangel, self._rangeu = 21, 108
        self._program = "piano"
        self._volume = 100
        self._mode = 0

        self._transposition_extra = 0

        self._channel_in_mask = 0x7F

        self._hb = [0] * 9

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        value = clamp(value, 0, 127)
        if value == self._volume: return
        self._volume = value 

        self._dev.setPartParam(self._part + 1, 0x19, value) # CHECK + 1?
        self.emit('control_change', volume=self._volume)

    @property
    def transposition_extra(self):
        return self._transposition_extra

    @transposition_extra.setter
    def transposition_extra(self, value):
        value = clamp(value, 0-64, 127-64)
        if value == self._transposition_extra: return

        self._transposition_extra = value
        self._write_config()
        self.emit('control_change', transposition_extra=value)

    @property
    def program(self):
        return self._program

    @program.setter
    def program(self, value):
        assert value in self.programs
        if value == self._program: return
        self._program = value
        p = self.programs[value]

        self._dev.cc((self._index) & 0xF, 0, p.msb)
        self._dev.cc((self._index) & 0xF, 32, p.lsb)
        self._dev.pc((self._index) & 0xF, p.pc-1)

        # Check?
        for sysex in p.sysex:
            sysex[1] = 0x40 | (self._part)
            self._dev.roland_sysex(sysex)

        self.emit('control_change', program=value)

    def hb(self, path, index, value):
        val = int(value*16) & 0xF
        self._hb[index[0]] = val
        #hammond_bars[14] = {0x40, 0x41, 0x51, 0x00, 0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        self._dev.roland_sysex([0x40, 0x40 | (self._part), 0x51, 0x00, 0x01] + self._hb)

    @property
    def transposition(self):
        return self._transposition

    @transposition.setter
    def transposition(self, value: int):
        value = clamp(value, -64, 63)
        if value == self._transposition: return
        self._transposition = value
        self._write_config()
        self.emit('control_change', transposition=value)

    @property
    def rangel(self): return self._rangel

    @property
    def rangeu(self): return self._rangeu

    @rangel.setter
    def rangel(self, value: int):
        value = clamp(value, 0, self._rangeu)
        self.range = (value, self._rangeu)
        self.emit('control_change', rangel=value)

    @rangeu.setter
    def rangeu(self, value: int):
        value = clamp(value, self._rangel, 127)
        self.range = (self._rangel, value)
        self.emit('control_change', rangeu=value)

    @property
    def range(self):
        return (self._rangel, self._rangeu)

    @range.setter
    def range(self, value: (int, int)):
        value = (clamp(value[0], 0, 127), clamp(value[1], clamp(value[0], 0, 127), 127))
        if value == (self._rangel, self._rangeu):
            return

        self._rangel, self._rangeu = value
        self._write_config()
        self.emit('control_change', range=value)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value: bool):
        if value == self._active:
            return
        #print("Setting active", self._index, value)
        self._active = value
        self._write_config()
        self.emit('control_change', active=value)

    def _write_config(self):
        self._dev._write_layer_config(self)

    def _read_layer_config(self):
        self._dev._read_layer_config(self)


class BaseMidiBox():
    def __init__(self):
        self.layers = [MidiBoxLayer(self, i) for i in range(8)]
        self._callbacks = []

        self.local_ctl = False
        self._requestKey = None
        self._mute = False

    def connect(self):
        ret = self._connect()

    def inputCallback(self, msg):
        for c in self._callbacks:
            c(msg)

        if msg.type == 'clock':
            return

        if msg.type == 'note_on':
            if self._requestKey:
                target, layer_index, target_prop = self._requestKey
                assert target == 'layer'
                setattr(self.layers[layer_index], target_prop, msg.note)
                self._requestKey = None
                self.mute = False

    def requestKey(self, target, index, prop):
        self.mute = True
        self._requestKey = (target, index, prop)

    @property
    def enable(self):
        return self.local_ctl

    @enable.setter
    def enable(self, v: bool):
        if  v == self.local_ctl: return
        self.local_ctl = v
        self._write_config()
        for i, l in enumerate(self.layers):
            l._write_config()
            #self.setPartParam(l._part, 3, i)
        #self.cc(0, 122, 127 if self.local_ctl else 0)

    @property
    def mute(self):
        return self._mute

    @mute.setter
    def mute(self, v: bool):
        if  v == self._mute: return
        self._mute = v
        for l in self.layers:
            l._write_config()

    def allSoundsOff(self):
        for i, l in enumerate(self.layers):
            self.cc(i, 120, 0)

    def note_on(self, channel, note, vel):  self._write([0x90 | (channel & 0xF), note & 0x7F, vel & 0x7F])
    def note_off(self, channel, note, vel): self._write([0x80 | (channel & 0xF), note & 0x7F, vel & 0x7F])
    def cc(self, channel, cc, val):         self._write([0xB0 | (channel & 0xF), cc   & 0x7F, val & 0x7F])
    def pc(self, channel, pgm):             self._write([0xC0 | (channel & 0xF), pgm  & 0x7F])

    def roland_sysex(self, data):
        self._write_sysex([0x41, 0x10, 0x42, 0x12] + data + [(128 - sum(data)) & 0x7F])

    def setPartParam(self, part, param, val):
        self.setSystemParam(0x10 | (part & 0xF), param, val)

    def setSystemParam(self, a, param, val):
        if type(val) not in [bytes, list]: val = [val]
        self.roland_sysex([0x40, 0x00 | a, param] + val)
