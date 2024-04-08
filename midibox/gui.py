import time

from PyQt5 import QtCore, QtGui

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, pyqtProperty
#from PyQt5.QtDeclarative import QDeclarativeItem

from PyQt5.QtCore import QTimer
#import PyQt5.QtChart


from .controller.base import MidiBoxLayerProps, MidiBoxProps, MidiBoxPedalProps


class PropertyMeta(type(QtCore.QObject)):
    def __new__(cls, name, bases, attrs):
        if '_prop_meta_dict' in attrs:
            props = attrs.pop('_prop_meta_dict')
            for prop in props:
                attrs[prop.name] = Property(prop.init_value, prop.name)

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
    def __init__(self, initial_value, name=''):
        self.initial_value = initial_value
        self.name = name

class PropertyImpl(QtCore.pyqtProperty):
    def __init__(self, initial_value, name='', type_=None, notify=None):
        super().__init__(type_, self.getter, self.setter, notify=notify)
        self.initial_value = initial_value
        self.name = name

    def getter(self, inst):
        return getattr(inst._proxy, self.name, self.initial_value)

    def setter(self, inst, value):
        setattr(inst._proxy, self.name, value)
        getattr(inst, signal_attribute_name(self.name)).emit(value)

def signal_attribute_name(property_name):
    return f'_{property_name}_prop_signal_'

class QMidiboxPedal(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = MidiBoxPedalProps

    def __init__(self, p, handler):
        super().__init__()
        self._proxy = p


class QMidiboxLayer(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = MidiBoxLayerProps

    programChange = pyqtSignal()
    pedalsChange = pyqtSignal()

    def __init__(self, layer, handler):
        super().__init__()
        self._proxy = self._cl = layer
        self._cl.bind(control_change=self.on_control_change)

        self._pedals = []
        for p in self._cl.pedals:
            self._pedals.append(QMidiboxPedal(p, handler))

    @pyqtSlot()
    def reset(self):
        self._proxy.reset()

    @pyqtProperty(list, notify=pedalsChange)
    def pedals(self): return self._pedals

    def on_control_change(self, *args, **kwargs):
        for name, value in kwargs.items():
            if name == "program":
                self.programChange.emit()

            if hasattr(self, signal_attribute_name(name)):
                getattr(self, signal_attribute_name(name)).emit(value)

    @pyqtProperty(str, notify=programChange)
    def shortName(self):
        return self._cl.programs[self._cl.program].short if self._cl.program in self._cl.programs else '?'

class QMidiBox(QObject, metaclass=PropertyMeta):
    _prop_meta_dict = MidiBoxProps

    layersChange = pyqtSignal() # Not used
    transpositionExtraChange = pyqtSignal()

    def __init__(self, box):
        super().__init__()
        self._proxy = self.box = box

        self.box.bind(control_change=self.on_control_change)

        self._layers = []
        for lr in self.box.layers:
            self._layers.append(QMidiboxLayer(lr, self.box))
            lr.bind(control_change=self.on_layer_control_change)

    @pyqtProperty(list, notify=layersChange)
    def layers(self): return self._layers

    @pyqtProperty(bool, notify=transpositionExtraChange)
    def transpositionExtra(self): return self.box.layers[0].transposition_extra == -12

    @transpositionExtra.setter
    def transpositionExtra(self, v): self.box.layers[0].transposition_extra = -12 if v else 0

    def on_control_change(self, *args, **kwargs):
        for name, value in kwargs.items():
            if hasattr(self, signal_attribute_name(name)):
                getattr(self, signal_attribute_name(name)).emit(value)

    def on_layer_control_change(self, *args, **kwargs):
        name = list(kwargs.keys())[0]
        if name == "transposition_extra":
            self.transpositionExtraChange.emit()

    @pyqtSlot(int, str)
    def requestKey(self, layer_index, target):
        self.box.requestKey('layer', layer_index, target)

    @pyqtSlot(int, result=str)
    def note2text(self, note):
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return note_names[note % 12] + str(note // 12 - 2)

    @pyqtSlot()
    def initialize(self):
        self.box.initialize()

    @pyqtSlot()
    def split12(self):
        self.layers[0].rangel = 56
        self.layers[1].rangeu = 55

    @pyqtSlot()
    def allSoundsOff(self):
        self.box.allSoundsOff()

    @pyqtSlot(int)
    def loadPreset(self, p):
        if p in [0, 1, 2, 3]:
            prgs = {0: 'piano', 1: 'epiano', 2: 'marimba', 3: 'vibraphone'}
            prg = prgs[p]

            self.layers[0].rangeu = 127
            self.layers[0].rangel = 56
            self.layers[1].rangeu = 55
            self.layers[1].rangel = 0
            self.layers[0].rangeu = 127
            self.layers[0].program = prg
            self.layers[1].program = 'bass'
            self.layers[0].active = True
            self.layers[1].active = True
            self.layers[0].enabled = True
            self.layers[1].enabled = True

            self.layers[2].program = prg
            self.layers[2].active = False
            self.layers[2].enabled = True

            self.layers[0].pedals[7].mode = 4 #'Push Active'
            self.layers[1].pedals[7].mode = 4 #'Push Active'
            self.layers[2].pedals[7].mode = 4 #'Push Active'

            self.transpositionExtra = True
            self.enable = True



class GraphUpdater(QObject):
    foo = pyqtSignal(int, int)
    def __init__(self, box):
        super().__init__()
        #self._deque = collections.deque([0] * 360)
        self._deque_start = int(time.time())
        self._deque_count = 0
        self.incDeque()
        box._callbacks.append(self.midi_cb)
        self.tmr = QTimer(self)
        self.tmr.start(5000)
        self.tmr.timeout.connect(self.incDeque)

    def incDeque(self):
        t = int(time.time()) - self._deque_start
        self.foo.emit(t, self._deque_count)

        #self._deque.appendleft(self._deque_count)
        self._deque_count = 0
        #self.tmr = threading.Timer(5, self.incDeque)
        #tmr.start()

    def midi_cb(self, msg):
        if msg.type == 'note_on':
            #i = int(time.time())
            self._deque_count += 1

class NameDataItem(QtGui.QStandardItem):
    def __init__(self, iid, name):
        super().__init__(name)
        self.setData(iid, QtCore.Qt.UserRole)

def NameDataItemModel(items, urname=b'value'):
    model = QtGui.QStandardItemModel()
    model.setItemRoleNames({
        QtCore.Qt.DisplayRole: b"text",
        QtCore.Qt.UserRole: urname,
    })
    for i in items:
        model.appendRow(i)
    return model

class ProgramPreset(NameDataItem):
    def __init__(self, iid, name):
        super().__init__(iid, name)
class PedalCc(NameDataItem):
    def __init__(self, iid, name):
        super().__init__(iid, name)
class PedalMode(NameDataItem):
    def __init__(self, iid, name):
        super().__init__(iid, name)

def ProgramPresetModel(box): return NameDataItemModel([ProgramPreset(k, v.name) for k, v in box.layers[0].programs.items()])
def PedalCcModel(box): return NameDataItemModel([PedalCc(v, k) for k, v in box.pedal_cc.items()])
def PedalModeModel(box): return NameDataItemModel([PedalMode(v, k) for k, v in box.pedal_mode.items()])
