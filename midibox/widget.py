import functools

import PyQt5
import PyQt5.QtWebEngine

from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtCore import QUrl, QRegExp, QSize
from PyQt5.QtQuickWidgets import *

from .controller import Midibox
from .gui import *

import pathlib

we = PyQt5.QtWebEngine.QtWebEngine
we.initialize()

class MidiboxQuickWidget(QQuickWidget):
    def __init__(self, app):
        super().__init__()

        e = self.engine()
        path = pathlib.Path(__file__).parent.resolve()
        #e.addImportPath(str(path.joinpath("midibox/style/")))

        box = Midibox("Control", "GigPanel", virtual=True, find=False, debug=True)
        #box = Midibox("XIAO nRF52840")
        #box = Midibox("Midibox XIAO BLE")

        self.midibox = box
        self.reterm = False
        self.qbox = QMidiBox(box)
        self.gu = GraphUpdater(box)

        # Info: store all CP into main class (setContextProperty doesnt't increment refcnt)
        self.pl = PlaylistModel()
        self.ppm = ProgramPresetModel(box)

        ctx = self.rootContext()
        ctx.setContextProperty("midibox", self.qbox)
        ctx.setContextProperty("programPresetsModel", self.ppm)
        ctx.setContextProperty("monitor", self.gu)
        ctx.setContextProperty("playlistModel", self.pl)
        ctx.setContextProperty("reterm", self.reterm)

        self.setResizeMode(self.SizeRootObjectToView)

        self.setSource(QUrl.fromLocalFile("midibox/StandaloneWidget.qml"));

        if hasattr(app, "aboutToQuit"):
            getattr(app, "aboutToQuit").connect(functools.partial(self.setSource, QUrl.fromLocalFile("")))

#    def minimumSizeHint(self):
#        return QSize(1280//2, 720//2)
#
#    def sizeHint(self):
#        return QSize(1280//1, 720//1)
