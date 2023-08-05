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
    def __init__(self, app, midibox_params={}, **kwargs):
        super().__init__()

        e = self.engine()
        path = pathlib.Path(__file__).parent.resolve()
        #e.addImportPath(str(path.joinpath("midibox/style/")))

        box = Midibox(**midibox_params)

        self.midibox = box
        self.reterm = False
        self.qbox = QMidiBox(box)
        self.gu = GraphUpdater(box)

        # Info: store all CP into main class (setContextProperty doesnt't increment refcnt)
        self.ppm = ProgramPresetModel(box)
        self.pcm = PedalCcModel(box)

        ctx = self.rootContext()
        ctx.setContextProperty("midibox", self.qbox)
        ctx.setContextProperty("programPresetsModel", self.ppm)
        ctx.setContextProperty("monitor", self.gu)
        ctx.setContextProperty("reterm", self.reterm)
        ctx.setContextProperty(f"pedalCcModel", self.pcm)

        self.setResizeMode(self.SizeRootObjectToView)

        self.setSource(QUrl.fromLocalFile(str(pathlib.Path(__file__).parent/"StandaloneWidget.qml")));

        if kwargs.get("playlist_url"):
            ro = self.rootObject()
            wv = ro.findChild(QObject, "playlistWebView")
            wv.setProperty("url", kwargs.get("playlist_url"))

        if hasattr(app, "aboutToQuit"):
            # Set empty source to avoid bad contextProperty references on exit
            getattr(app, "aboutToQuit").connect(functools.partial(self.setSource, QUrl.fromLocalFile("")))

    def minimumSizeHint(self):
        return QSize(0, 720)#1280//2, 720//2)
        return QSize(1280//2, 720//2)

    def sizeHint(self):
        return QSize(0, 720)
        return QSize(1280//1, 720//1)
