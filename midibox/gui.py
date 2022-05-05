import signal
import sys
import time

from PyQt5 import QtCore, QtGui, QtWidgets, QtQuickWidgets

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, pyqtProperty
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtWidgets import QApplication
#from PyQt5.QtDeclarative import QDeclarativeItem

from PyQt5.QtChart import QChartView, QSplineSeries
from PyQt5.QtCore import QPoint, QRectF, QTimer
#import PyQt5.QtChart

import functools
import collections


class ProgramPreset(QtGui.QStandardItem):
    def __init__(self, pid, name):
        super().__init__(name)
        self.setData(pid, QtCore.Qt.UserRole)

class QMidiBox(QObject):
    layersChange = pyqtSignal() # Not used
    enableChange = pyqtSignal()

    transpositionExtraChange = pyqtSignal()

    def __init__(self, box):
        super().__init__()
        self.box = box

        self._layers = []
        for l in self.box.layers:
            l.bind(control_change=self.on_control_change)
            self._layers.append(QMidiboxLayer(l, self.box))

    @pyqtSlot(QObject)
    def loadSong(self, obj):
        #print(obj.property('text'), obj.property('pid'))
        pass

    @pyqtProperty(list, notify=layersChange)
    def layers(self):
        return self._layers

    def on_control_change(self, *args, **kwargs):
        name = list(kwargs.keys())[0]
        if name == "transpositionExtra":
            self.transpositionExtraChange.emit()

    @pyqtSlot(int, str)
    def requestKey(self, layer_index, target):
        self.box.requestKey('layer', layer_index, target)

    @pyqtSlot(int, result=str)
    def note2text(self, note):
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return note_names[note % 12] + str(note // 12 - 2)

    @pyqtSlot()
    def split12(self):
        self.layers[0].rangel = 56
        self.layers[1].rangeu = 55

    @pyqtProperty(bool, notify=enableChange)
    def enable(self): return self.box.enable

    @enable.setter
    def enable(self, v):
        self.box.enable = v
        self.enableChange.emit()

    @pyqtProperty(bool, notify=transpositionExtraChange)
    def transpositionExtra(self): return self.box.layers[0].transposition_extra == -12

    @transpositionExtra.setter
    def transpositionExtra(self, v):
        self.box.layers[0].transposition_extra = -12 if v else 0

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
            self.transpositionExtra = True
            self.enable = True


class PropertyMeta(type(QtCore.QObject)):
    def __new__(cls, name, bases, attrs):
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
        return getattr(inst._cl, self.name, self.initial_value)

    def setter(self, inst, value):
        setattr(inst._cl, self.name, value)
        getattr(inst, signal_attribute_name(self.name)).emit(value)

def signal_attribute_name(property_name):
    return f'_{property_name}_prop_signal_'

class QMidiboxLayer(QObject, metaclass=PropertyMeta):
    transposition = Property(0, 'transposition')
    program = Property('', 'program')
    volume = Property(100, 'volume')
    rangel = Property(0, 'rangel')
    rangeu = Property(127, 'rangeu')
    active = Property(False, 'active')

    programChange = pyqtSignal()
    #active = pyqtProperty(bool, notify=programChange)

    def __init__(self, layer, handler):
        super().__init__()
        self._cl = layer
        self._cl.bind(control_change=self.on_control_change)

    def prop_get(self, ):
        return self._cl.programs[self._cl.program].short

    def on_control_change(self, *args, **kwargs):
        name = list(kwargs.keys())[0]
        if name == "program":
            self.programChange.emit()
        if name in ["rangel", "rangeu", "active", "transposition", "program", "volume"]:
            getattr(self, signal_attribute_name(name)).emit(getattr(self._cl, name))

    @pyqtProperty(str, notify=programChange)
    def shortName(self):
        return self._cl.programs[self._cl.program].short


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

import warnings

class PlaylistModel(QtGui.QStandardItemModel):
    def __init__(self, app = None):
        super().__init__()
        self.setItemRoleNames({
            QtCore.Qt.DisplayRole: b"text",
            QtCore.Qt.UserRole: b"pid",
        })

        self.app = app

    def client_add(self, pli):
        song = self.gp.songs[pli['songId']]
        self.playlist.addItem(PlaylistItem(song, pli))

    def client_del(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.takeItem(self.playlist.row(item))
        del x

    def load(self, playlist):
        #print(self.app.songs)
        if self.app is None:
            warnings.warn('No app in Midibox PlaylistModel')
            return

        for songItem in playlist["items"]:
            song = self.app.songs[songItem['songId']]
            i = QtGui.QStandardItem(song['name'])
            i.setData(songItem['songId'], QtCore.Qt.UserRole)
            self.appendRow(i)

    def load_(self, playlist):
        if self.app is None:
            warnings.warn('No app in Midibox PlaylistModel')
            return

        self.playlist.clear()
        
        #x = self.playlist.takeItem(self.playlist.row(item))
        #del x

        for songItem in playlist["items"]:
            songId = songItem['songId']
            #print(songId)
            try:
                #song = [x for x in self.gp.db['Songs'] if x['name'] == name][0]
                song = app.songs[songId]
            except:
                #print("Cant find playlist song:", name)
                print("Cant find playlist song:", songItem)
            else:
                self.playlist.addItem(PlaylistItem(song, songItem))

    def play(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.setCurrentRow(self.playlist.row(item))

def ProgramPresetModel(box):
    model = QtGui.QStandardItemModel()
    model.setItemRoleNames({
        QtCore.Qt.DisplayRole: b"text",
        QtCore.Qt.UserRole: b"pid",
    })
    [model.appendRow(ProgramPreset(k, v.name)) for k, v in box.layers[0].programs.items()]
    #print(box.layers[0].programs)

    return model
