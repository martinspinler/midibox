import logging
import re
import time

from typing import Any, ClassVar, Optional

import mido

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtQuick import QQuickItem
from PyQt6.sip import wrappertype as pyqtWrapperType

from ..config import Preset
from ..controller.base import (
    BaseMidibox,
    General,
    GeneralPedal,
    GeneralPedalProps,
    GeneralProps,
    Layer,
    LayerProps,
    Pedal,
    PedalProps,
)

logger = logging.getLogger(__name__)


def signal_attribute_name(property_name: str) -> str:
    return f"_{property_name}_prop_signal_"


def _emit_property_changes(obj: QObject, **kwargs: Any) -> None:
    """Emit notifier signals for any properties that changed."""
    for name, value in kwargs.items():
        sig_name = signal_attribute_name(name)
        if hasattr(obj, sig_name):
            getattr(obj, sig_name).emit(value)


class PropertyMeta(pyqtWrapperType):  # type: ignore[misc]
    def __new__(cls: Any, name: Any, bases: Any, attrs: Any) -> Any:
        if "_prop_meta_dict" in attrs:
            props = attrs.pop("_prop_meta_dict")
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
                initial_value, name=key, type_=type_, notify=notifier
            )
            attrs[signal_attribute_name(key)] = notifier
        return super().__new__(cls, name, bases, attrs)


class Property:
    def __init__(self, initial_value: Any, name: str = "") -> None:
        self.initial_value = initial_value
        self.name = name


class PropertyImpl(pyqtProperty):
    def __init__(
        self,
        initial_value: Any,
        name: str,
        type_: type,
        notify: Optional[Any] = None,
    ) -> None:
        super().__init__(type_, self.pgetter, self.psetter, notify=notify)
        self.initial_value = initial_value
        self.name = name

    def pgetter(self, inst: Any) -> Any:
        return getattr(inst._proxy, self.name, self.initial_value)

    def psetter(self, inst: Any, value: Any) -> None:
        setattr(inst._proxy, self.name, value)
        getattr(inst, signal_attribute_name(self.name)).emit(value)


class QMidiboxPedal(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = PedalProps

    def __init__(self, p: Pedal, handler: BaseMidibox) -> None:
        super().__init__()
        self._proxy = p
        self._proxy.bind(control_change=self.on_control_change)

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        _emit_property_changes(self, **kwargs)


class QMidiboxLayer(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = LayerProps

    programChange = pyqtSignal()
    pedalsChange = pyqtSignal()

    def __init__(self, layer: Layer, handler: BaseMidibox) -> None:
        super().__init__()
        self._proxy = layer
        self._proxy.bind(control_change=self.on_control_change)

        self._pedals: list[QMidiboxPedal] = [
            QMidiboxPedal(p, handler) for p in self._proxy.pedals
        ]

    @pyqtSlot()
    def reset(self) -> None:
        self._proxy.reset()

    @pyqtProperty(list, notify=pedalsChange)  # type: ignore[arg-type]
    def pedals(self) -> list[QMidiboxPedal]:
        return self._pedals

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        if "program" in kwargs:
            self.programChange.emit()
        _emit_property_changes(self, **kwargs)

    @pyqtProperty(str, notify=programChange)  # type: ignore[arg-type]
    def shortName(self) -> str:
        program = self._proxy.program
        programs = self._proxy.programs_by_ident
        return programs[program].short if program in programs else "?"


class QMidiboxGeneralPedal(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = GeneralPedalProps

    def __init__(self, gpedal: GeneralPedal) -> None:
        super().__init__()
        self._proxy = gpedal
        self._proxy.bind(control_change=self.on_control_change)

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        _emit_property_changes(self, **kwargs)


class QMidiboxGeneral(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = GeneralProps

    pedalsChange = pyqtSignal()  # Not used

    def __init__(self, general: General, handler: BaseMidibox) -> None:
        super().__init__()
        self._proxy = general
        self._proxy.bind(control_change=self.on_control_change)

        self._pedals: list[QMidiboxGeneralPedal] = [
            QMidiboxGeneralPedal(p) for p in general.pedals
        ]

    @pyqtSlot()
    def reset(self) -> None:
        self._proxy.reset()

    @pyqtProperty(list, notify=pedalsChange)  # type: ignore[arg-type]
    def pedals(self) -> list[QMidiboxGeneralPedal]:
        return self._pedals

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        _emit_property_changes(self, **kwargs)


class QMidiBox(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = GeneralProps

    layersChange = pyqtSignal()  # Not used
    generalChange = pyqtSignal()  # Not used
    transpositionExtraChange = pyqtSignal()

    _MODE_MAP: ClassVar[dict[str, int]] = {
        "none": 0,
        "normal": 1,
        "note_length": 2,
        "toggle_active": 3,
        "push_active": 4,
    }

    def __init__(self, box: BaseMidibox) -> None:
        super().__init__()
        self._proxy = self.box = box
        self._general = QMidiboxGeneral(self.box.general, self.box)

        self.box.general.bind(control_change=self.on_control_change)

        self._layers: list[QMidiboxLayer] = []
        for lr in self.box.layers:
            layer = QMidiboxLayer(lr, self.box)
            self._layers.append(layer)
            lr.bind(control_change=self.on_layer_control_change)

        self._presets: dict[int, Preset] = {}
        self._gpedal_regex = re.compile(r"pedal(\d+)_(\w+)")

    def init(
        self, ro: QQuickItem, config: dict[str, Any], presets: dict[str, Preset]
    ) -> None:
        presets_btns = ro.findChild(QObject, "presets")
        presets_list = list(presets.values())
        self._presets = dict(enumerate(presets_list))

        if presets_btns is None:
            return

        for i, child in enumerate(presets_btns.children()):
            if i < len(presets_list):
                child.setProperty("text", presets_list[i].label)

    @pyqtProperty(QObject, notify=generalChange)  # type: ignore[arg-type]
    def general(self) -> QMidiboxGeneral:
        return self._general

    @pyqtProperty(list, notify=layersChange)  # type: ignore[arg-type]
    def layers(self) -> list[QMidiboxLayer]:
        return self._layers

    @pyqtProperty(bool, notify=transpositionExtraChange)
    def transpositionExtra(self) -> bool:
        return self.box.layers[0].transposition_extra == -12

    @transpositionExtra.setter  # type: ignore[arg-type]
    def transpositionExtra(self, v: bool) -> None:
        self.box.layers[0].transposition_extra = -12 if v else 0

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        _emit_property_changes(self, **kwargs)

    def on_layer_control_change(self, *args: Any, **kwargs: Any) -> None:
        if "transposition_extra" in kwargs:
            self.transpositionExtraChange.emit()

    @pyqtSlot(int, str)
    def requestKey(self, layer_index: int, target: str) -> None:
        self.box.requestKey("layer", layer_index, target)

    _NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    @pyqtSlot(int, result=str)
    def note2text(self, note: int) -> str:
        return self._NOTE_NAMES[note % 12] + str(note // 12 - 2)

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
        if p not in self._presets:
            return

        preset = self._presets[p]
        config: dict[str, Any] = {}
        try:
            preset.get_config(config)
        except RecursionError:
            logger.error("Cycle in configuration for preset %s", preset)
            return

        with self.box.bundle():
            self._apply_layer_config(config.get("layers", {}))
            self._apply_general_config(config.get("general", {}))

    def _apply_layer_config(self, layers_cfg: dict[str, Any]) -> None:
        for layer_index, layer_config in layers_cfg.items():
            try:
                layer = self._layers[layer_index]
            except IndexError:
                logger.warning("Layer index %s out of range", layer_index)
                continue

            for k, v in layer_config.items():
                if k == "pedals":
                    self._apply_pedal_config(layer, v)
                elif hasattr(layer, k):
                    setattr(layer, k, v)

    def _apply_pedal_config(
        self, layer: QMidiboxLayer, pedal_configs: dict[str, Any]
    ) -> None:
        for pi, pedal_config in pedal_configs.items():
            try:
                pedal = layer.pedals[pi]
            except IndexError:
                logger.warning("Pedal index %s out of range", pi)
                continue

            for pk, pv in pedal_config.items():
                if not hasattr(pedal, pk):
                    continue

                if pk == "mode":
                    pv = self._MODE_MAP.get(pv, pv)
                setattr(pedal, pk, pv)

    def _apply_general_config(self, general_cfg: dict[str, Any]) -> None:
        for k, v in general_cfg.items():
            if k.startswith("pedal"):
                match = self._gpedal_regex.fullmatch(k)
                if match is None:
                    continue

                index = int(match.group(1))
                prop = match.group(2)

                try:
                    pedal = self._general.pedals[index]
                except IndexError:
                    logger.warning("General pedal index %s out of range", index)
                    continue

                if hasattr(pedal, prop):
                    setattr(pedal, prop, v)
            elif hasattr(self._general, k):
                setattr(self._general, k, v)


class GraphUpdater(QObject):
    statsUpdated = pyqtSignal(int, int)

    _TIMER_INTERVAL_MS = 5000

    def __init__(self, box: BaseMidibox) -> None:
        super().__init__()
        self._deque_start = int(time.time())
        self._deque_count = 0
        self.incDeque()
        box._callbacks.append(self.midi_cb)

        self.tmr = QTimer(self)
        self.tmr.timeout.connect(self.incDeque)
        self.tmr.start(self._TIMER_INTERVAL_MS)

    def incDeque(self) -> None:
        t = int(time.time()) - self._deque_start
        self.statsUpdated.emit(t, self._deque_count)
        self._deque_count = 0

    def midi_cb(self, msg: mido.Message) -> None:
        if msg.type == "note_on":
            self._deque_count += 1


class NameDataItem(QtGui.QStandardItem):
    def __init__(self, iid: Any, name: str) -> None:
        super().__init__(name)
        self.setData(iid, QtCore.Qt.ItemDataRole.UserRole)


class NameDataItemModel(QtGui.QStandardItemModel):
    pass


def _NameDataItemModel(items: list[NameDataItem]) -> NameDataItemModel:
    model = NameDataItemModel()
    model.setItemRoleNames({
        QtCore.Qt.ItemDataRole.DisplayRole: b"text",
        QtCore.Qt.ItemDataRole.UserRole: b"value",
    })
    for i in items:
        model.appendRow(i)
    return model


class ProgramPreset(NameDataItem):
    def __init__(self, iid: str, name: str) -> None:
        super().__init__(iid, name)


class PedalCc(NameDataItem):
    def __init__(self, iid: int, name: str) -> None:
        super().__init__(iid, name)


class PedalMode(NameDataItem):
    def __init__(self, iid: int, name: str) -> None:
        super().__init__(iid, name)


def ProgramPresetModel(box: BaseMidibox) -> NameDataItemModel:
    return _NameDataItemModel(
        [ProgramPreset(v.ident, v.label) for v in box.layers[0].programs.values()]
    )


def PedalCcModel(box: BaseMidibox) -> NameDataItemModel:
    return _NameDataItemModel(
        [PedalCc(v, k) for k, v in box.pedal_cc.items()]
    )


def PedalModeModel(box: BaseMidibox) -> NameDataItemModel:
    return _NameDataItemModel(
        [PedalMode(v, k) for k, v in box.pedal_mode.items()]
    )


def PlayModeModel(box: BaseMidibox) -> NameDataItemModel:
    return _NameDataItemModel(
        [PedalMode(v, k) for k, v in box.layers[0].modes_r.items()]
    )
