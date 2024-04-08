from pydispatch import Dispatcher
from typing import NamedTuple, TypedDict, Any, List, Literal

def clamp(val: int, lower: int, upper: int):
    return lower if val < lower else upper if val > upper else val

class MidiBoxProgram(NamedTuple):
    pc: int
    msb: int
    lsb: int
    sysex: List[List[int]]
    short: str
    name: str


def propsetter(self, value, name, validator, callback):
    _name = f'_{name}'
    value = validator(self, value)
    if value == getattr(self, _name):
        return
    setattr(self, _name, value)
    callback(self, name, value)
    self.emit('control_change', **{name: value})


class CheckedProp():
    def __init__(self, *args):
        keys = ['name', 'init_value', 'validator', 'callback']
        if len(args) < len(keys):
            keys = keys[:len(args)]
        for k, v in zip(keys, args):
            setattr(self, k, v)

        setter = self.validator if hasattr(self, 'validator') else None
        if setter:
            self.prop = property(
                lambda s, name=self.name: getattr(s, f'_{name}'),
                lambda s, val, name=self.name: propsetter(s, val, name, setter, self.callback)
            )

def mb_properties_init(cls):
    for item in cls._mb_properties:
        setattr(cls, f"_{item.name}", item.init_value)
        if hasattr(item, 'prop'):
            setattr(cls, item.name, item.prop)
    return cls

MidiBoxPedalProps = [
    CheckedProp('cc', 0,
        lambda s, v: clamp(v, 0, 127),
        lambda self, n, v: self._layer._write_config(f"pedal{self._index}.{n}", v)
    ),
    CheckedProp('mode', 0,
        lambda s, v: clamp(v, 0, 127),
        lambda self, n, v: self._layer._write_config(f"pedal{self._index}.{n}", v)
    ),
]

@mb_properties_init
class MidiBoxPedal(Dispatcher):
    _mb_properties = MidiBoxPedalProps
    _events_ = ['control_change']

    def __init__(self, layer, index):
        self._layer = layer
        self._index = index


MidiBoxLayerProps = [
    CheckedProp('transposition', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('transposition_extra', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('enabled', False,
        lambda s, v: True if v else False,
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('active', True,
        lambda s, v: True if v else False,
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('rangel', 21,
        lambda s, v: clamp(v, 0, s._rangeu),
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('rangeu', 108,
        lambda s, v: clamp(v, s._rangel, v),
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('program', '-unknown-',
        lambda s, v: v if v in s.programs else s.programs[s._program],
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('volume', 100,
        lambda s, v: clamp(v, 0, 127),
        lambda self, n, v: self._write_config(n, v)
    ),
    #CheckedProp('init', False,
    #    lambda s, v: True if v else False,
    #    lambda self, n, v: self._write_config()
    #),
    CheckedProp('release', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('attack', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('cutoff', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, n, v: self._write_config(n, v)
    ),
    CheckedProp('decay', 0,
        lambda s, v: clamp(v, -64, 63),
        lambda self, n, v: self._write_config(n, v)
    ),

    CheckedProp('percussion', 0,
        lambda s, v: s.percussions[clamp(v, 0, 5)][1],
        lambda self, n, v: self._write_config(n, v)
    ),
    *[
        CheckedProp(f'harmonic_bar{i}', 0,
            lambda s, v: clamp(v, 0, 15),
            lambda self, n, v: self._write_config(n, v)
        ) for i in range(9)
    ],
]

efx = {
    'none':   [0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04],
    'dumper': [0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00],
    'rotary': [0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F],
    'epiano': [0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02],
}

@mb_properties_init
class MidiBoxLayer(Dispatcher):
    _mb_properties = MidiBoxLayerProps
    _events_ = ['control_change']
    programs = {          #PC MSB LSB
        'piano'         : MidiBoxProgram( 1,  0, 68, [efx['dumper']], 'Pn', 'Piano'),
        'epiano'        : MidiBoxProgram( 5,  0, 67, [efx['epiano']], 'eP', 'E-Piano'),
        'bass'          : MidiBoxProgram(33,  0, 71, [efx['none']],   'Bs', 'Bass'),
        'hammond'       : MidiBoxProgram(17, 32, 68, [efx['rotary']], 'Hm', 'Hammond'),
        'vibraphone'    : MidiBoxProgram(12,  0,  0, [efx['rotary']], 'Vp', 'Vibraphone'),
        'marimba'       : MidiBoxProgram(13,  0, 64, [efx['rotary']], 'Mb', 'Marimba'),
        'fretlessbass'  : MidiBoxProgram(36,  0,  0, [efx['none']],   'FB', 'Fretlett Bass'),
    }
    percussions = [
        ('Off'           , 0x00),
        ('4, Short'      , 0x01),
        ('2+2/3, Short'  , 0x02),
        ('4, Long'       , 0x41),
        ('2+2/3, Long'   , 0x42),
    ]

    def __init__(self, dev: "BaseMidibox", index: int):
        self._index = index
        self._part = (index + 1) & 0xF if index != 9 else 0
        self._dev = dev
        self._mode = 0

        pedal_cc = ['Sustain', 'Hold', 'Expression'] + [0] + ['GPC1', 'GPC2', 'GPC3', 'GPC4']
        self._pedal_cc = [self._dev.pedal_cc[x] if isinstance(x, str) else x for x in pedal_cc]

        pedal_mode = ['Ignore', 'Normal', 'NoteLength', 'Toggle Active', 'Push Active']
        self._pedal_mode = [self._dev.pedal_mode[x] if x in self._dev.pedal_mode else x for x in pedal_mode]

        self._hb = [0] * 9

        self.pedals = [MidiBoxPedal(self, i) for i in range(8)]

    def reset(self):
        for p in self._mb_properties:
            if p.name == 'program':
                setattr(self, p.name, 'piano')
            else:
                setattr(self, p.name, p.init_value)

    def setProgram(self, value: str):
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

    def _write_config(self, name=None, value=None):
        self._dev._write_layer_config(self, name, value)

    def _read_layer_config(self):
        self._dev._read_layer_config(self)

MidiBoxProps = [
    CheckedProp('enable', False,
        lambda s, v: True if v else False,
        lambda s, n, v: s._write_config(n, v)
    ),
    CheckedProp('mute', False,
        lambda s, v: True if v else False,
        lambda s, n, v: s._write_config(n, v)
    ),
]


@mb_properties_init
class BaseMidibox(Dispatcher):
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
    pedal_mode = {
        'Ignore': 0,
        'Normal': 1,
        'NoteLength': 2,
        'Toggle Active': 3,
        'Push Active': 4,
    }

    layers: List[MidiBoxLayer]

    def __init__(self):
        self.layers = [MidiBoxLayer(self, i) for i in range(8)]
        self._callbacks = []

        self._requestKey = None

    def disconnect(self):
        self._disconnect()

    def connect(self):
        self._connect()
        self.emit_all()

    def emit_control(self, name):
        kwargs = {name: getattr(self, name)}
        self.emit('control_change', **kwargs)

    def emit_all(self):
        for ctrl in BaseMidibox._mb_properties:
            kwargs = {ctrl.name: getattr(self, ctrl.name)}
            self.emit('control_change', **kwargs)

        for lr in self.layers:
            for ctrl in MidiBoxLayer._mb_properties:
                kwargs = {ctrl.name: getattr(lr, ctrl.name)}
                lr.emit('control_change', **kwargs)

            for p in lr.pedals:
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
                if msg.data[0:4] == (65, 16, 66, 18):
                    self.input_callback_roland_sysex(msg)
            except:
                pass

    def input_callback_roland_sysex(self, msg):
        if msg.data[4] == 0x40:
            msg.data[5] & 0x0F
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
                    #print(eff_type, msg.data)

    def initialize(self):
        self._initialize()

    def requestKey(self, target, index, prop):
        self.mute = True
        self._requestKey = (target, index, prop)

    def allSoundsOff(self):
        for i, lr in enumerate(self.layers):
            self.cc(i, 120, 0)

    def note_on(self, channel, note, vel):  self._write([0x90 | (channel & 0xF), note & 0x7F, vel & 0x7F])
    def note_off(self, channel, note, vel): self._write([0x80 | (channel & 0xF), note & 0x7F, vel & 0x7F])
    def cc(self, channel, cc, val):         self._write([0xB0 | (channel & 0xF), cc   & 0x7F, val & 0x7F])
    def pc(self, channel, pgm):             self._write([0xC0 | (channel & 0xF), pgm  & 0x7F])

    def roland_sysex(self, data):
        self._write_sysex([0x41, 0x10, 0x42, 0x12] + data + [(128 - sum(data)) & 0x7F])

    def setPartParam(self, part: int, param: int, val: int):
        self.setSystemParam(0x10 | (part & 0xF), param, val)

    def setSystemParam(self, a, param, val):
        if type(val) not in [bytes, list]:
            val = [val]
        self.roland_sysex([0x40, 0x00 | a, param] + val)
