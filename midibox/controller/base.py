import mido

from pydispatch import Dispatcher
from typing import NamedTuple, List, Any, Callable, Optional, Tuple, TypeVar, Sequence


def clamp(val: int, lower: int, upper: int) -> int:
    return lower if val < lower else upper if val > upper else val


class MidiBoxProgram(NamedTuple):
    pc: int
    msb: int
    lsb: int
    sysex: List[List[int]]
    short: str
    name: str


T = TypeVar('T')

class CheckedPropHandler(Dispatcher):  # type: ignore[misc]
    _mb_properties: Sequence["CheckedProp[Any]"]
    _events_ = ['control_change']

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        #for p in self._mb_properties:
        #    setattr(self, f"_{p.name}", p.init_value)
        super().__init__(*args, **kwargs)

    def on_checkedprop_change(self, name: str, value: Any) -> None:
        pass

    def _on_checkedprop_change(self, cp: "CheckedProp[T]", value: Any) -> None:
        _name = f'_{cp.name}'
        value = cp.validator(self, value)
        if value != getattr(self, _name):
            setattr(self, _name, value)
            #cp.callback(self, cp.name, value)
            self.on_checkedprop_change(cp.name, value)
            self.emit('control_change', **{cp.name: value})


class CheckedProp[T]:
    def __init__(self, name: str, init_value: T, validator: Callable[[CheckedPropHandler, T], T]) -> None:  # , callback: Callable[[CheckedPropHandler, str, Any], None]) -> None:
        self.name = name
        self.init_value = init_value
        #self.callback = callback
        self.validator = validator

        getter: Callable[[CheckedPropHandler], T] = lambda cph: getattr(cph, f'_{name}')
        setter: Callable[[CheckedPropHandler, T], None] = lambda cph, val: cph._on_checkedprop_change(self, val)
        self.prop = property(getter, setter)


def mb_properties_init(cls: type[CheckedPropHandler]) -> type[CheckedPropHandler]:
    for item in cls._mb_properties:
        setattr(cls, f"_{item.name}", item.init_value)
        setattr(cls, item.name, item.prop)
    return cls


class BoolProp(CheckedProp[bool]):
    def __init__(self, name: str, default: bool = False) -> None:  # , callback: Optional[Callable[[Any, Any, Any], None]] = None) -> None:
        #validator: Callable[[Any, int], int] = lambda s, v: clamp(v, min, max)
        validator: Callable[[CheckedPropHandler, bool], bool] = lambda s, v: True if v else False
        super().__init__(name, default, validator)


class IntProp(CheckedProp[int]):
    def __init__(self, name: str, default: int = 0, min: int = 0, max: int = 127) -> None:  # , callback: Optional[Callable[[Any, Any, Any], None]] = None) -> None:
        validator: Callable[[CheckedPropHandler, int], int] = lambda s, v: clamp(v, min, max)
        super().__init__(name, default, validator)

        #if callback is None:
            # FIXME!!!
            #callback = lambda self, n, v: self._write_config(n, v)
        #    #callback = lambda self, n, v: self._layer._write_config(f"pedal{self._index}.{n}", v)



class UIntProp(IntProp):
    def __init__(self, name: str) -> None:
        super().__init__(name)


class SIntProp(IntProp):
    def __init__(self, name: str) -> None:
        super().__init__(name, min=-64, max=63)


MidiBoxPedalProps = [
    UIntProp("cc"),
    UIntProp("mode"),
]


@mb_properties_init
class MidiBoxPedal(CheckedPropHandler):
    _mb_properties = MidiBoxPedalProps

    def __init__(self, layer: "MidiBoxLayer", index: int):
        self._layer = layer
        self._index = index

    def _write_config(self, name: Optional[str] = None, value: Optional[Any] = None) -> None:
        self._layer._write_config(name, value)


MidiBoxLayerProps: list[CheckedProp[Any]] = [
    SIntProp("transposition"),
    SIntProp("transposition_extra"),
    BoolProp('enabled'),
    BoolProp('active', True),
    CheckedProp('rangel', 21, lambda s, v: clamp(v, 0, s._rangeu)),
    CheckedProp('rangeu', 108, lambda s, v: clamp(v, s._rangel, v)),
    CheckedProp('program', '-unknown-', lambda s, v: v if v in s.programs else s.programs[s._program]),
    IntProp("volume", default=100),
    SIntProp("release"),
    SIntProp("attack"),
    SIntProp("cutoff"),
    SIntProp("decay"),
    UIntProp("portamento_time"),
    CheckedProp('percussion', 0, lambda s, v: s.percussions[clamp(v, 0, 5)][1]),
    *[
        CheckedProp(f'harmonic_bar{i}', 0, lambda s, v: clamp(v, 0, 15)) for i in range(9)
    ],
]

efx = {
    'none'  : [0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04], # noqa
    'dumper': [0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00],
    'rotary': [0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F],
    'epiano': [0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02],
}


@mb_properties_init
class MidiBoxLayer(CheckedPropHandler):
    _mb_properties = MidiBoxLayerProps
    programs = {  #                      PC MSB LSB
        'piano'         : MidiBoxProgram( 1,  0, 68, [efx['dumper']], 'Pn', 'Piano'), # noqa
        'epiano'        : MidiBoxProgram( 5,  0, 67, [efx['epiano']], 'eP', 'E-Piano'), # noqa
        'bass'          : MidiBoxProgram(33,  0, 71, [efx['none']],   'Bs', 'Bass'), # noqa
        'hammond'       : MidiBoxProgram(17, 32, 68, [efx['rotary']], 'Hm', 'Hammond'), # noqa
        'vibraphone'    : MidiBoxProgram(12,  0,  0, [efx['rotary']], 'Vp', 'Vibraphone'), # noqa
        'marimba'       : MidiBoxProgram(13,  0, 64, [efx['rotary']], 'Mb', 'Marimba'), # noqa
        'mallet_isle'   : MidiBoxProgram(115, 0, 64, [efx['rotary']], 'Mi', 'Mallet Isle'), # noqa
        'fretlessbass'  : MidiBoxProgram(36,  0,  0, [efx['none']],   'FB', 'Fretlett Bass'), # noqa
        'bass_cymbal'   : MidiBoxProgram(33,  0, 66, [efx['none']],   'Bc', 'Bass + Cymbal'), # noqa
    }
    percussions = [
        ('Off'           , 0x00), # noqa
        ('4, Short'      , 0x01), # noqa
        ('2+2/3, Short'  , 0x02), # noqa
        ('4, Long'       , 0x41), # noqa
        ('2+2/3, Long'   , 0x42), # noqa
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

    def reset(self) -> None:
        for p in self._mb_properties:
            if p.name == 'program':
                setattr(self, p.name, 'piano')
            else:
                setattr(self, p.name, p.init_value)

    def setProgram(self, value: str) -> None:
        p = self.programs[value]

        self._dev.cc((self._index) & 0xF, 0, p.msb)
        self._dev.cc((self._index) & 0xF, 32, p.lsb)
        self._dev.pc((self._index) & 0xF, p.pc - 1)

        # Check?
        for sysex in p.sysex:
            sysex[1] = 0x40 | (self._part)
            self._dev.roland_sysex(sysex)

    #def hb(self, path, index, value) -> None:
    #    val = int(value * 16) & 0xF
    #    self._hb[index[0]] = val
    #    #hammond_bars[14] = {0x40, 0x41, 0x51, 0x00, 0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    #    self._dev.roland_sysex([0x40, 0x40 | (self._part), 0x51, 0x00, 0x01] + self._hb)

    def on_checkedprop_change(self, name: str, value: Any) -> None:
        self._write_config(name, value)

    def _write_config(self, name: Optional[str] = None, value: Optional[Any] = None) -> None:
        self._dev._write_layer_config(self) #, name, value)

    def _read_layer_config(self) -> None:
        self._dev._read_layer_config(self)


MidiBoxProps = [
    BoolProp('enable'),
    BoolProp('mute'),
]


@mb_properties_init
class BaseMidibox(CheckedPropHandler):
    _mb_properties = MidiBoxProps

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

    def __init__(self) -> None:
        super().__init__()

        self.layers = [MidiBoxLayer(self, i) for i in range(8)]
        self._callbacks: list[Callable[[mido.Message], None]] = []

        self._requestKey: Optional[Tuple[str, int, str]] = None

    def disconnect(self) -> None:
        self._disconnect()

    def connect(self) -> None:
        self._connect()
        self.emit_all()

    def on_checkedprop_change(self, name: str, value: Any) -> None:
        self._write_config()

    def emit_control(self, name: str) -> None:
        kwargs = {name: getattr(self, name)}
        self.emit('control_change', **kwargs)

    def emit_all(self) -> None:
        for ctrl in BaseMidibox._mb_properties:
            kwargs = {ctrl.name: getattr(self, ctrl.name)}
            self.emit('control_change', **kwargs)

        for lr in self.layers:
            for lctrl in MidiBoxLayer._mb_properties:
                kwargs = {lctrl.name: getattr(lr, lctrl.name)}
                lr.emit('control_change', **kwargs)

            for p in lr.pedals:
                for pctrl in MidiBoxPedal._mb_properties:
                    kwargs = {pctrl.name: getattr(p, pctrl.name)}
                    p.emit('control_change', **kwargs)

    def inputCallback(self, msg: mido.Message) -> None:
        for c in self._callbacks:
            c(msg)

        if msg.type == 'clock':
            return

        if msg.type == 'note_on':
            if self._requestKey is not None:
                target, layer_index, target_prop = self._requestKey
                assert target == 'layer'
                setattr(self.layers[layer_index], target_prop, msg.note)
                self._requestKey = None
                self.mute = False

        if msg.type == 'sysex':
            data = msg.data
            if len(data) >= 4 and data[0:4] == (65, 16, 66, 18):
                self.input_callback_roland_sysex(data)

    def input_callback_roland_sysex(self, data: list[int]) -> None:
        if len(data) > 6 and data[4] == 0x40:
            data[5] & 0x0F
            bank = data[5] & 0xF0
            addr = data[6]

            if bank == 0x00:
                "System Parameters"
            if bank >= 0x10:
                "Part Parameters"
                if len(data) > 8 and bank == 0x40 and addr == 0x23:
                    "Effect"
                    eff_type = (data[7] << 8) | data[8]
                    if eff_type == 0x0125:
                        "Tremolo"
                    #print(eff_type, data)

    def initialize(self) -> None:
        self._initialize()

    def requestKey(self, target: str, index: int, prop: str) -> None:
        self.mute = True
        self._requestKey = (target, index, prop)

    def allSoundsOff(self) -> None:
        for i, lr in enumerate(self.layers):
            self.cc(i, 120, 0)

    def note_on(self, channel: int, note: int, vel: int) -> None:
        self._write([0x90 | (channel & 0xF), note & 0x7F, vel & 0x7F])

    def note_off(self, channel: int, note: int, vel: int) -> None:
        self._write([0x80 | (channel & 0xF), note & 0x7F, vel & 0x7F])

    def cc(self, channel: int, cc: int, val: int) -> None:
        self._write([0xB0 | (channel & 0xF), cc & 0x7F, val & 0x7F])

    def pc(self, channel: int, pgm: int) -> None:
        self._write([0xC0 | (channel & 0xF), pgm & 0x7F])

    def roland_sysex(self, data: list[int]) -> None:
        self._write_sysex([0x41, 0x10, 0x42, 0x12] + data + [(128 - sum(data)) & 0x7F])

    #def setPartParam(self, part: int, param: int, val: list[int]) -> None:
    #    self.setSystemParam(0x10 | (part & 0xF), param, val)

    #def setSystemParam(self, a: int, param: int, val: list[int]) -> None:
    #    if type(val) not in [bytes, list]:
    #        val = [val]
    #    self.roland_sysex([0x40, 0x00 | a, param] + val)
