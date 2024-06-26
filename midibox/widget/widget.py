import sys
import signal
import functools

from types import SimpleNamespace

import PyQt5
import PyQt5.QtWebEngine

from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtWidgets import QApplication

from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtCore import QUrl, QSize, QObject
from PyQt5.QtQuickWidgets import *

from ..controller import BaseMidibox
from .gui import QMidiBox, ProgramPresetModel, PedalCcModel, PedalModeModel, GraphUpdater

import pathlib


def initialize_webengine():
    global __webengine
    __webengine = PyQt5.QtWebEngine.QtWebEngine
    __webengine.initialize()


def populate_context(ctx, box: BaseMidibox):
    # Info: store all CP into namespace: setContextProperty doesnt't increment refcnt
    ns = SimpleNamespace()

    ns.midibox = box
    ns.reterm = False
    ns.qbox = QMidiBox(box)
    ns.gu = GraphUpdater(box)

    ns.ppm = ProgramPresetModel(box)
    ns.pcm = PedalCcModel(box)
    ns.pmm = PedalModeModel(box)

    ctx.setContextProperty("midibox", ns.qbox)
    ctx.setContextProperty("programPresetsModel", ns.ppm)
    ctx.setContextProperty("monitor", ns.gu)
    ctx.setContextProperty("reterm", ns.reterm)
    ctx.setContextProperty("pedalCcModel", ns.pcm)
    ctx.setContextProperty("pedalModeModel", ns.pmm)

    return ns

class MidiboxQuickWidget(QQuickWidget):
    def __init__(self, app, midibox, **kwargs):
        super().__init__()

        pathlib.Path(__file__).parent.resolve()
        #e.addImportPath(str(path.joinpath("midibox/style/")))

        self.midibox = midibox
        self.ctx = populate_context(self.rootContext(), self.midibox)
        self.qmidibox = self.ctx.qbox

        self.setResizeMode(self.SizeRootObjectToView)

        self.setSource(QUrl.fromLocalFile(str(pathlib.Path(__file__).parent/"StandaloneWidget.qml")))

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


def create_gui(midibox, big_mode=False, disable_sandbox=False):
    QIcon.setThemeName("Adwaita")
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if disable_sandbox:
        os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = str(1)
    initialize_webengine()

    app = QApplication(sys.argv)
    if big_mode:
        app.setFont(QFont("Helvetica", 36))

    app.midibox = midibox
    app.engine = w = QQmlApplicationEngine()
    cwd = pathlib.Path(__file__).parent.resolve()
    w.addImportPath(str(cwd.joinpath("style/")))

    app.ctx = populate_context(w.rootContext(), app.midibox)

    w.load(str(cwd.joinpath('midibox.qml')))
    w.quit.connect(app.quit)
    app.aboutToQuit.connect(w.deleteLater)

    if len(w.rootObjects()) == 0:
        sys.exit(1)
    root = w.rootObjects()[0]
    if big_mode:
        root.setProperty("visibility", "FullScreen")
        root.children()[1].setProperty("my_scale", 1)
    else:
        root.setProperty("width", 1280 // 1)
        root.setProperty("height", 720 // 1)
        root.children()[1].setProperty("my_scale", 1)

    return app
