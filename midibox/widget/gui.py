import time
import mido
from typing import Any, Optional

from PyQt5 import QtCore, QtGui

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtCore import pyqtProperty
#from PyQt5.QtDeclarative import QDeclarativeItem

from PyQt5.QtCore import QTimer
#import PyQt5.QtChart

from PyQt5.QtQuick import QQuickItem


from ..controller.base import GeneralProps, LayerProps, PedalProps, BaseMidibox, General, Layer, Pedal

from ..config import Preset

from sip import wrappertype as pyqtWrapperType


class PropertyMeta(pyqtWrapperType):  # type: ignore
    def __new__(cls: Any, name: Any, bases: Any, attrs: Any) -> Any:
        if '_prop_meta_dict' in attrs:
            props = attrs.pop('_prop_meta_dict')
            for prop in props:
                attrs[prop.name] = Property(prop.initial, prop.name)

        for key in list(attrs.keys()):
            attr = attrs[key]
            if not isinstance(attr, Property):
                continue

            initial_value = attr.initial_value
            type_ = type(initial_value)
            notifier = QtCore.pyqtSignal(type_)
            attrs[key] = PropertyImpl(
                initial_value, name=key, type_=type_, notify=notifier)
            attrs[signal_attribute_name(key)] = notifier
        return super().__new__(cls, name, bases, attrs)


class Property:
    def __init__(self, initial_value: Any, name: str = '') -> None:
        self.initial_value = initial_value
        self.name = name


class PropertyImpl(pyqtProperty):
    def __init__(self, initial_value: Any, name: str, type_: type, notify: Optional[Any] = None) -> None:
        super().__init__(type_, self.pgetter, self.psetter, notify=notify)
        self.initial_value = initial_value
        self.name = name

    def pgetter(self, inst: Any) -> Any:
        return getattr(inst._proxy, self.name, self.initial_value)

    def psetter(self, inst: Any, value: Any) -> Any:
        setattr(inst._proxy, self.name, value)
        getattr(inst, signal_attribute_name(self.name)).emit(value)


def signal_attribute_name(property_name: str) -> str:
    return f'_{property_name}_prop_signal_'


class QMidiboxPedal(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = PedalProps

    def __init__(self, p: Pedal, handler: BaseMidibox) -> None:
        super().__init__()
        self._proxy = p
        self._proxy.bind(control_change=self.on_control_change)

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        for name, value in kwargs.items():
            if hasattr(self, signal_attribute_name(name)):
                getattr(self, signal_attribute_name(name)).emit(value)


class QMidiboxLayer(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = LayerProps

    programChange = pyqtSignal()
    pedalsChange = pyqtSignal()

    def __init__(self, layer: Layer, handler: BaseMidibox) -> None:
        super().__init__()
        self._proxy = layer
        self._proxy.bind(control_change=self.on_control_change)

        self._pedals: list[QMidiboxPedal] = []
        for p in self._proxy.pedals:
            self._pedals.append(QMidiboxPedal(p, handler))

    @pyqtSlot()
    def reset(self) -> None:
        self._proxy.reset()

    @pyqtProperty(list, notify=pedalsChange)  # type: ignore
    def pedals(self) -> list[QMidiboxPedal]:
        return self._pedals

    def on_control_change(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        for name, value in kwargs.items():
            if name == "program":
                self.programChange.emit()

            if hasattr(self, signal_attribute_name(name)):
                getattr(self, signal_attribute_name(name)).emit(value)

    @pyqtProperty(str, notify=programChange)  # type: ignore
    def shortName(self) -> str:
        return self._proxy.programs_by_ident[self._proxy.program].short if self._proxy.program in self._proxy.programs_by_ident else '?'


class QMidiboxGeneral(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = GeneralProps

    def __init__(self, general: General, handler: BaseMidibox) -> None:
        super().__init__()
        self._proxy = general
        self._proxy.bind(control_change=self.on_control_change)

    @pyqtSlot()
    def reset(self) -> None:
        self._proxy.reset()

    def on_control_change(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        for name, value in kwargs.items():
            if hasattr(self, signal_attribute_name(name)):
                getattr(self, signal_attribute_name(name)).emit(value)


class QMidiBox(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = GeneralProps

    layersChange = pyqtSignal() # Not used
    generalChange = pyqtSignal() # Not used
    transpositionExtraChange = pyqtSignal()

    def __init__(self, box: BaseMidibox) -> None:
        super().__init__()
        self._proxy = self.box = box
        self._general = QMidiboxGeneral(self.box.general, self.box)

        self.box.general.bind(control_change=self.on_control_change)

        self._layers: list[QMidiboxLayer] = []
        for lr in self.box.layers:
            self._layers.append(QMidiboxLayer(lr, self.box))
            lr.bind(control_change=self.on_layer_control_change)

        self._presets: dict[int, Preset] = {}

    def init(self, ro: QQuickItem, config: dict[str, Any], presets: dict[str, Preset]) -> None:
        presets_btns = ro.findChild(QObject, "presets")
        presets_list = list(presets.values())
        self._presets = {k: v for k, v in enumerate(presets_list)}
        if presets_btns:
            for i, child in enumerate(presets_btns.children()):
                if len(presets_list) > i:
                    preset = presets_list[i]
                    child.setProperty("text", preset.label)

    @pyqtProperty(QObject, notify=generalChange)  # type: ignore
    def general(self) -> QMidiboxGeneral:
        return self._general

    @pyqtProperty(list, notify=layersChange)  # type: ignore
    def layers(self) -> list[QMidiboxLayer]:
        return self._layers

    @pyqtProperty(bool, notify=transpositionExtraChange)
    def transpositionExtra(self):
        return self.box.layers[0].transposition_extra == -12

    @transpositionExtra.setter # type: ignore
    def transpositionExtra(self, v) -> None:
        self.box.layers[0].transposition_extra = -12 if v else 0

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        for name, value in kwargs.items():
            if hasattr(self, signal_attribute_name(name)):
                getattr(self, signal_attribute_name(name)).emit(value)

    def on_layer_control_change(self, *args: Any, **kwargs: Any) -> None:
        name = list(kwargs.keys())[0]
        if name == "transposition_extra":
            self.transpositionExtraChange.emit()

    @pyqtSlot(int, str)
    def requestKey(self, layer_index: int, target: str) -> None:
        self.box.requestKey('layer', layer_index, target)

    @pyqtSlot(int, result=str)
    def note2text(self, note: int) -> str:
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return note_names[note % 12] + str(note // 12 - 2)

    @pyqtSlot()
    def initialize(self) -> None:
        self.box.initialize()

    @pyqtSlot()
    def split12(self) -> None:
        self.box.layers[0].rangel = 56
        self.box.layers[1].rangeu = 55

    @pyqtSlot()
    def allSoundsOff(self) -> None:
        self.box.allSoundsOff()

    @pyqtSlot(int)
    def loadPreset(self, p: int) -> None:
        if p in self._presets:
            preset = self._presets[p]
            config: dict[str, Any] = {}
            try:
                preset.get_config(config)
            except RecursionError:
                print("Cycle in configuration!!!")
                return

            with self.box.bundle():
                for layer_index, layer_config in config.get("layers", {}).items():
                    layer = self._layers[layer_index]
                    for k, v in layer_config.items():
                        if k == 'pedals':
                            for pi, pedal_config in v.items():
                                pedal = layer.pedals[pi]
                                for pk, pv in pedal_config.items():
                                    if hasattr(pedal, pk):
                                        if pk == "mode":
                                            pv = {
                                                'none': 0,
                                                'normal': 1,
                                                'note_length': 2,
                                                'toggle_active': 3,
                                                'push_active': 4,
                                            }[pv]
                                        setattr(pedal, pk, pv)
                        else:
                            if hasattr(layer, k):
                                setattr(layer, k, v)

                for k, v in config.get("global", {}).items():
                    if k not in ['enabled', 'transpositionExtra']:
                        continue
                    if hasattr(self, k):
                        setattr(self, k, v)


class GraphUpdater(QObject):
    foo = pyqtSignal(int, int)

    def __init__(self, box: BaseMidibox) -> None:
        super().__init__()
        #self._deque = collections.deque([0] * 360)
        self._deque_start = int(time.time())
        self._deque_count = 0
        self.incDeque()
        box._callbacks.append(self.midi_cb)
        self.tmr = QTimer(self)
        self.tmr.start(5000)
        self.tmr.timeout.connect(self.incDeque)

    def incDeque(self) -> None:
        t = int(time.time()) - self._deque_start
        self.foo.emit(t, self._deque_count)

        #self._deque.appendleft(self._deque_count)
        self._deque_count = 0
        #self.tmr = threading.Timer(5, self.incDeque)
        #tmr.start()

    def midi_cb(self, msg: mido.Message) -> None:
        if msg.type == 'note_on':
            #i = int(time.time())
            self._deque_count += 1


class NameDataItem(QtGui.QStandardItem):
    def __init__(self, iid: Any, name: str):
        super().__init__(name)
        self.setData(iid, QtCore.Qt.UserRole)


class NameDataItemModel(QtGui.QStandardItemModel):
    pass


def _NameDataItemModel(items: list[NameDataItem]) -> NameDataItemModel:
    model = NameDataItemModel()
    model.setItemRoleNames({
        QtCore.Qt.DisplayRole: b"text",
        QtCore.Qt.UserRole: b"value",
    })
    for i in items:
        model.appendRow(i)
    return model


class ProgramPreset(NameDataItem):
    def __init__(self, iid: str, name: str):
        super().__init__(iid, name)


class PedalCc(NameDataItem):
    def __init__(self, iid: int, name: str):
        super().__init__(iid, name)


class PedalMode(NameDataItem):
    def __init__(self, iid: int, name: str):
        super().__init__(iid, name)


def ProgramPresetModel(box: BaseMidibox) -> NameDataItemModel:
    return _NameDataItemModel([ProgramPreset(v.ident, v.label) for k, v in box.layers[0].programs.items()])


def PedalCcModel(box: BaseMidibox) -> NameDataItemModel:
    return _NameDataItemModel([PedalCc(v, k) for k, v in box.pedal_cc.items()])


def PedalModeModel(box: BaseMidibox) -> NameDataItemModel:
    return _NameDataItemModel([PedalMode(v, k) for k, v in box.pedal_mode.items()])
