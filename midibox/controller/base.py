import mido

from pydispatch import Dispatcher
from typing import NamedTuple, List, Any, Callable, Optional, Tuple, TypeVar, Sequence, Type
from types import TracebackType


def clamp(val: int, lower: int, upper: int) -> int:
    return lower if val < lower else upper if val > upper else val


class Program(NamedTuple):
    pc: int
    msb: int
    lsb: int
    sysex: List[List[int]]
    short: str
    name: str


T = TypeVar('T')


class PropHandler(Dispatcher):  # type: ignore[misc]
    _mb_properties: Sequence["CheckedProp[Any]"]
    _events_ = ['control_change']

    def __init__(self, dev: "BaseMidibox", *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._dev = dev
        super().__init__(*args, **kwargs)

    def on_checkedprop_change(self, name: str, value: Any) -> None:
        self._dev.set_prop(self, name, value)

    def reset(self) -> None:
        for prop in self._mb_properties:
            setattr(self, prop.name, prop.default)

    def emit_control(self, name: str) -> None:
        kwargs = {name: getattr(self, name)}
        self.emit('control_change', **kwargs)

    def emit_all(self) -> None:
        for ctrl in self._mb_properties:
            kwargs = {ctrl.name: getattr(self, ctrl.name)}
            self.emit('control_change', **kwargs)

    def _on_checkedprop_change(self, cp: "CheckedProp[T]", value: Any) -> None:
        _name = f'_{cp.name}'
        value = cp.validator(self, value)
        if value != getattr(self, _name):
            setattr(self, _name, value)
            self.on_checkedprop_change(cp.name, value)
            self.emit('control_change', **{cp.name: value})


class CheckedProp[T]:
    def __init__(self, name: str, default: T, validator: Callable[[PropHandler, T], T], initial: Optional[T] = None) -> None:
        self.name = name
        self.validator = validator
        self.default = default
        self.initial = initial if initial is not None else default

        getter: Callable[[PropHandler], T] = lambda cph: getattr(cph, f'_{name}')
        setter: Callable[[PropHandler, T], None] = lambda cph, val: cph._on_checkedprop_change(self, val)
        self.prop = property(getter, setter)


class BoolProp(CheckedProp[bool]):
    def __init__(self, name: str, default: bool = False) -> None:
        validator: Callable[[PropHandler, bool], bool] = lambda s, v: True if v else False
        super().__init__(name, default, validator)


class IntProp(CheckedProp[int]):
    def __init__(self, name: str, default: int = 0, min: int = 0, max: int = 127) -> None:
        validator: Callable[[PropHandler, int], int] = lambda s, v: clamp(v, min, max)
        super().__init__(name, default, validator)


class UIntProp(IntProp):
    pass


class SIntProp(IntProp):
    def __init__(self, name: str) -> None:
        super().__init__(name, min=-64, max=63)


def mb_properties_init(cls: type[PropHandler]) -> type[PropHandler]:
    for item in cls._mb_properties:
        setattr(cls, f"_{item.name}", item.initial)
        setattr(cls, item.name, item.prop)
    return cls


PedalProps = [
    UIntProp("cc"),
    UIntProp("mode"),
]


@mb_properties_init
class Pedal(PropHandler):
    _mb_properties = PedalProps

    def __init__(self, dev: "BaseMidibox", layer: "Layer", index: int):
        super().__init__(dev)
        self._dev = dev
        self._layer = layer
        self._index = index


LayerProps: list[CheckedProp[Any]] = [
    SIntProp('transposition'),
    SIntProp('transposition_extra'),
    BoolProp('enabled'),
    BoolProp('active', True),
    CheckedProp('rangel', 21, lambda s, v: clamp(v, 0, s._rangeu)),
    CheckedProp('rangeu', 108, lambda s, v: clamp(v, s._rangel, v)),
    CheckedProp('program', 'piano', lambda s, v: v if v in s.programs else s.programs[s._program], initial='-unknown-'),
    IntProp('volume', default=100),
    SIntProp('release'),
    SIntProp('attack'),
    SIntProp('cutoff'),
    SIntProp('decay'),
    UIntProp('portamento_time'),
    CheckedProp('percussion', 0, lambda s, v: s.percussions[clamp(v, 0, 4)][1]),
    *[
        CheckedProp(f'harmonic_bar{i}', 0, lambda s, v: clamp(v, 0, 15)) for i in range(9)
    ],
    UIntProp('volume_ch'),
]

efx = {
    'none'  : [0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04], # noqa
    'dumper': [0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00],
    'rotary': [0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F],
    'epiano': [0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02],
}


@mb_properties_init
class Layer(PropHandler):
    _mb_properties = LayerProps
    programs = {  #                      PC MSB LSB
        'piano'         : Program( 1,  0, 68, [efx['dumper']], 'Pn', 'Piano'), # noqa
        'epiano'        : Program( 5,  0, 67, [efx['epiano']], 'eP', 'E-Piano'), # noqa
        'bass'          : Program(33,  0, 71, [efx['none']],   'Bs', 'Bass'), # noqa
        'hammond'       : Program(17, 32, 68, [efx['rotary']], 'Hm', 'Hammond'), # noqa
        'vibraphone'    : Program(12,  0,  0, [efx['rotary']], 'Vp', 'Vibraphone'), # noqa
        'marimba'       : Program(13,  0, 64, [efx['rotary']], 'Mb', 'Marimba'), # noqa
        'mallet_isle'   : Program(115, 0, 64, [efx['rotary']], 'Mi', 'Mallet Isle'), # noqa
        'fretlessbass'  : Program(36,  0,  0, [efx['none']],   'FB', 'Fretlett Bass'), # noqa
        'bass_cymbal'   : Program(33,  0, 66, [efx['none']],   'Bc', 'Bass + Cymbal'), # noqa
    }
    percussions = [
        ('Off'           , 0x00), # noqa
        ('4, Short'      , 0x01), # noqa
        ('2+2/3, Short'  , 0x02), # noqa
        ('4, Long'       , 0x41), # noqa
        ('2+2/3, Long'   , 0x42), # noqa
    ]

    def __init__(self, dev: "BaseMidibox", index: int):
        super().__init__(dev)
        self._index = index
        self._part = (index + 1) & 0xF if index != 9 else 0
        self._mode = 0

        pedal_cc = ['Sustain', 'Hold', 'Expression'] + [0] + ['GPC1', 'GPC2', 'GPC3', 'GPC4']
        self._pedal_cc = [self._dev.pedal_cc[x] if isinstance(x, str) else x for x in pedal_cc]

        pedal_mode = ['Ignore', 'Normal', 'NoteLength', 'Toggle Active', 'Push Active']
        self._pedal_mode = [self._dev.pedal_mode[x] if x in self._dev.pedal_mode else x for x in pedal_mode]

        self.pedals = [Pedal(dev, self, i) for i in range(8)]

    def reset(self) -> None:
        super().reset()
        for p in self.pedals:
            p.reset()

    def emit_all(self) -> None:
        super().emit_all()
        for p in self.pedals:
            p.emit_all()


GeneralProps = [
    BoolProp('enable'),
    BoolProp('mute'),
]


@mb_properties_init
class General(PropHandler):
    _mb_properties = GeneralProps


class PropChange(NamedTuple):
    source: PropHandler
    name: str
    value: Any


class BundleManager:
    def __init__(self, request_handler: "BaseMidibox"):
        self._mb = request_handler

    def __enter__(self) -> None:
        if self._mb._bundle_inner == 0:
            self._mb._bundle = None
            self._mb._bundle = []
        self._mb._bundle_inner += 1

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc: Optional[BaseException], traceback: Optional[TracebackType]) -> Optional[bool]:
        self._mb._bundle_inner -= 1
        if self._mb._bundle_inner == 0:
            if self._mb._bundle:
                bundle = self._mb._bundle
                self._mb._bundle = None
                self._mb.set_props(bundle)
        return None


class BaseMidibox():
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

    layers: List[Layer]

    _bundle: Optional[list[PropChange]]
    _bundle_inner: int

    def __init__(self) -> None:
        super().__init__()

        self.layers = [Layer(self, i) for i in range(8)]
        self.general = General(self)
        self._callbacks: list[Callable[[mido.Message], None]] = []

        self._requestKey: Optional[Tuple[str, int, str]] = None
        self._bundle = None
        self._bundle_inner = 0

    def disconnect(self) -> None:
        pass

    def connect(self) -> None:
        pass

    def emit_all(self) -> None:
        self.general.emit_all()
        for lr in self.layers:
            lr.emit_all()

    def reset(self) -> None:
        self.general.reset()
        for lr in self.layers:
            lr.reset()

    def send(self, b: bytes | list[int]) -> None:
        if isinstance(b, list):
            b = bytes(b)
        msg = mido.Message.from_bytes(b)
        self.sendmsg(msg)

    def bundle(self) -> BundleManager:
        return BundleManager(self)

    def set_prop(self, source: PropHandler, name: str, value: Any) -> None:
        pc = PropChange(source, name, value)
        if self._bundle is not None:
            self._bundle.append(pc)
        else:
            self.set_props([pc])

    def set_props(self, props: list[PropChange]) -> None:
        raise NotImplementedError

    def sendmsg(self, msg: mido.Message) -> None:
        raise NotImplementedError

    def input_callback(self, msg: mido.Message) -> None:
        for cb in self._callbacks:
            cb(msg)

        if msg.type == 'clock':
            return

        if msg.type == 'note_on':
            if self._requestKey is not None:
                target, layer_index, target_prop = self._requestKey
                if target == 'layer':
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
        pass

    def requestKey(self, target: str, index: int, prop: str) -> None:
        self.mute = True
        self._requestKey = (target, index, prop)

    def allSoundsOff(self) -> None:
        for i, lr in enumerate(self.layers):
            self.cc(i, 120, 0)

    def note_on(self, channel: int, note: int, vel: int) -> None:
        self.send([0x90 | (channel & 0xF), note & 0x7F, vel & 0x7F])

    def note_off(self, channel: int, note: int, vel: int) -> None:
        self.send([0x80 | (channel & 0xF), note & 0x7F, vel & 0x7F])

    def cc(self, channel: int, cc: int, val: int) -> None:
        self.send([0xB0 | (channel & 0xF), cc & 0x7F, val & 0x7F])

    def pc(self, channel: int, pgm: int) -> None:
        self.send([0xC0 | (channel & 0xF), pgm & 0x7F])

    def sysex(self, msg: list[int]) -> None:
        self.send([0xF0] + msg + [0xF7])

    def roland_sysex(self, data: list[int]) -> None:
        self.sysex([0x41, 0x10, 0x42, 0x12] + data + [(128 - sum(data)) & 0x7F])
