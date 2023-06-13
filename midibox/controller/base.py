import time
from pydispatch import Dispatcher

clamp = lambda x, l, u: l if x < l else u if x > u else x

class MidiBoxProgram():
    def __init__(self, *args):
        keys = ['pc', 'msb', 'lsb', 'sysex', 'short', 'name']
        for k, v in zip(keys, args): setattr(self, k, v)

def propsetter(self, value, name, validator, callback):
    value = validator(self, value)
    if value == getattr(self, name): return
    setattr(self, name, value)
    ret = callback(self, value)
    self.emit('control_change', **{name[1:]: value})

class CheckedProp():
    def __init__(self, *args):
        keys = ['name', 'init_value', 'validator', 'callback']
        if len(args) < len(keys): keys = keys[:len(args)]
        for k, v in zip(keys, args): setattr(self, k, v)

        setter = self.validator if hasattr(self, 'validator') else None
        if setter:
            self.prop = property(lambda s, name=self.name: getattr(s, f'_{name}'), lambda s, val, name=self.name: propsetter(s, val, f'_{name}', setter, self.callback))

def mb_properties_init(cls):
    for item in cls._mb_properties:
        setattr(cls, f"_{item.name}", item.init_value)
        if hasattr(item, 'prop'):
            setattr(cls, item.name, item.prop)
    return cls

MidiBoxPedalProps = [
    CheckedProp('cc', 0,
        lambda s, v: clamp(v, 0, 127),
        lambda self, v: self._layer._write_config()
    ),
]

@mb_properties_init
class MidiBoxPedal(Dispatcher):
    _mb_properties = MidiBoxPedalProps
    _events_ = ['control_change']

    def __init__(self, layer, index):
        self._layer = layer


MidiBoxLayerProps = [
    CheckedProp('transposition', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, _: self._write_config()
    ),
    CheckedProp('transposition_extra', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, _: self._write_config()
    ),
    CheckedProp('active', False,
        lambda s, v: True if v else False,
        lambda self, _: self._write_config()
    ),
    CheckedProp('rangel', 21,
        lambda s, v: clamp(v, 0, s._rangeu),
        lambda self, _: self._write_config()
    ),
    CheckedProp('rangeu', 108,
        lambda s, v: clamp(v, s._rangel, v),
        lambda self, _: self._write_config()
    ),
    CheckedProp('program', '-unknown-',
        lambda s, v: v if v in s.programs else s.programs[s._program],
        lambda self, _: self._write_config()
       #lambda s, v: s.setProgram(v)
    ),
    CheckedProp('volume', 100,
        lambda s, v: clamp(v, 0, 127),
        lambda self, _: self._write_config()
       #lambda s, v: s._dev.setPartParam(s._part, 0x19, v) # CHECK + 1?
    ),
    #CheckedProp('init', False,
    #    lambda s, v: True if v else False,
    #    lambda self, _: self._write_config()
    #),
    CheckedProp('release', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, _: self._write_config()
    ),
    CheckedProp('attack', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, _: self._write_config()
    ),
    CheckedProp('cutoff', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, _: self._write_config()
    ),
    CheckedProp('decay', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, _: self._write_config()
    ),
]


@mb_properties_init
class MidiBoxLayer(Dispatcher):
    _mb_properties = MidiBoxLayerProps
    _events_ = ['control_change']
    programs = {          #PC MSB LSB
        'piano'         : MidiBoxProgram( 1,  0, 68, [[0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00]], 'Pn', 'Piano'),
        'epiano'        : MidiBoxProgram( 5,  0, 67, [[0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02]], 'eP', 'E-Piano'),
        'bass'          : MidiBoxProgram(33,  0, 71, [[0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04]], 'Bs', 'Bass'),
        'hammond'       : MidiBoxProgram(17, 32, 68, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]], 'Hm', 'Hammond'),
        'vibraphone'    : MidiBoxProgram(12,  0,  0, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]], 'Vp', 'Vibraphone'),
        'marimba'       : MidiBoxProgram(13,  0, 64, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]], 'Mb', 'Marimba'),
        'fretlessbass'  : MidiBoxProgram(36,  0,  0, [[0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04]], 'FB', 'Fretlett Bass'),
    }

    def __init__(self, dev, index):
        self._index = index
        self._part = (index + 1) & 0xF if index != 9 else 0
        self._dev = dev
        self._mode = 0
        self._initialize = False

        pedal_cc = ['Sustain', 'Hold', 'Expression'] + [0] + ['GPC1', 'GPC2', 'GPC3', 'GPC4']
        self._pedal_cc = [self._dev.pedal_cc[x] if x in self._dev.pedal_cc else x for x in pedal_cc]

        self._hb = [0] * 9

        self.pedals = [MidiBoxPedal(self, i) for i in range(8)]

    def reset(self):
        for p in self._mb_properties:
            if p.name == 'program':
                setattr(self, p.name, 'piano')
            else:
                setattr(self, p.name, p.init_value)
    def setProgram(self, value):
        p = self.programs[value]

        self._dev.cc((self._index) & 0xF, 0, p.msb)
        self._dev.cc((self._index) & 0xF, 32, p.lsb)
        self._dev.pc((self._index) & 0xF, p.pc-1)

        # Check?
        for sysex in p.sysex:
            sysex[1] = 0x40 | (self._part)
            self._dev.roland_sysex(sysex)

    def hb(self, path, index, value):
        val = int(value*16) & 0xF
        self._hb[index[0]] = val
        #hammond_bars[14] = {0x40, 0x41, 0x51, 0x00, 0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        self._dev.roland_sysex([0x40, 0x40 | (self._part), 0x51, 0x00, 0x01] + self._hb)

    def _write_config(self):
        self._dev._write_layer_config(self)

    def _read_layer_config(self):
        self._dev._read_layer_config(self)

MidiBoxProps = [
    CheckedProp('enable', False,
        lambda s, v: True if v else False,
        lambda s, v: s.setEnable(v)
    ),
    CheckedProp('mute', False,
        lambda s, v: True if v else False,
        lambda s, v: s.setMute(v)
    ),
]


@mb_properties_init
class BaseMidiBox(Dispatcher):
    _mb_properties = MidiBoxProps
    _events_ = ['control_change']

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

    def __init__(self):
        self._initialize = False
        self.layers = [MidiBoxLayer(self, i) for i in range(8)]
        self._callbacks = []

        self._requestKey = None

    def connect(self):
        ret = self._connect()

        for ctrl in BaseMidiBox._mb_properties:
            kwargs = {ctrl.name: getattr(self, ctrl.name)}
            self.emit('control_change', **kwargs)

        for l in self.layers:
            for ctrl in MidiBoxLayer._mb_properties:
                kwargs = {ctrl.name: getattr(l, ctrl.name)}
                l.emit('control_change', **kwargs)

            for p in l.pedals:
                for ctrl in MidiBoxPedal._mb_properties:
                    kwargs = {ctrl.name: getattr(p, ctrl.name)}
                    p.emit('control_change', **kwargs)

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

        if msg.type == 'sysex':
            try:
                if msg.data[0] == 119:
                    pass
                else:
                    if msg.data[0:4] == (65, 16, 66, 18):
                        if msg.data[4] == 0x40:
                            part = msg.data[5] & 0x0F
                            bank = msg.data[5] & 0xF0
                            addr = msg.data[6]

                            if bank == 0x00:
                                "System Parameters"
                            if bank >= 0x10:
                                "Part Parameters"
                                if bank == 0x40 and addr == 0x23:
                                    "Effect"
                                    eff_type = (msg.data[7] << 8) | msg.data[8]
                                    if eff_type == 0x0125:
                                        "Tremolo"
            except:
                pass
                                    #print(eff_type, msg.data)

    def initialize(self):
        self._initialize = True
        self._write_config()

        for i, l in enumerate(self.layers):
            l._initialize = True
            self._write_layer_config(l)

    def requestKey(self, target, index, prop):
        self.mute = True
        self._requestKey = (target, index, prop)

    def setEnable(self, v: bool):
        self._write_config()
        for i, l in enumerate(self.layers):
            l._write_config()
            #self.setPartParam(l._part, 3, i)
        #self.cc(0, 122, 127 if self._enable else 0)

    def setMute(self, v: bool):
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
