import os
import sys
import signal
import functools
import pathlib

from typing import Any
from dataclasses import dataclass

import PyQt5
import PyQt5.QtWebEngine

from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtWidgets import QApplication

from PyQt5.QtQml import QQmlContext
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtCore import QUrl, QSize, QObject

from ..controller import BaseMidibox
from ..config import presets_from_config
from .gui import QMidiBox, NameDataItemModel, ProgramPresetModel, PedalCcModel, PedalModeModel, GraphUpdater


__webengine: Any


def initialize_webengine() -> None:
    __webengine = PyQt5.QtWebEngine.QtWebEngine
    __webengine.initialize()  # type: ignore


@dataclass
class ApplicationContext:
    qbox: QMidiBox
    gu: GraphUpdater
    ppm: NameDataItemModel
    pcm: NameDataItemModel
    pmm: NameDataItemModel


@dataclass
class Application():
    qapp: QApplication
    qml_engine: QQmlApplicationEngine
    ctx: ApplicationContext
    box: BaseMidibox


def init_context(ctx: ApplicationContext, ro: QQuickItem, config: dict[str, Any]) -> None:
    ro.children()[1].setProperty("my_scale", config.get("gui", {}).get("scale", 1))

    presets = presets_from_config(config)
    ctx.qbox.init(ro, config, presets)


def populate_context(ctx: QQmlContext, box: BaseMidibox) -> ApplicationContext:
    # Info: store all CP into namespace: setContextProperty doesnt't increment refcnt
    ns = ApplicationContext(
        QMidiBox(box),
        GraphUpdater(box),
        ProgramPresetModel(box),
        PedalCcModel(box),
        PedalModeModel(box),
    )

    ctx.setContextProperty("midibox", ns.qbox)
    ctx.setContextProperty("programPresetsModel", ns.ppm)
    ctx.setContextProperty("monitor", ns.gu)
    ctx.setContextProperty("pedalCcModel", ns.pcm)
    ctx.setContextProperty("pedalModeModel", ns.pmm)

    return ns


class MidiboxQuickWidget(QQuickWidget):
    def __init__(self, app: QApplication, midibox: BaseMidibox, **kwargs: Any) -> None:
        super().__init__()

        pathlib.Path(__file__).parent.resolve()
        #e.addImportPath(str(path.joinpath("midibox/style/")))

        self.midibox = midibox
        self.ctx = populate_context(self.rootContext(), self.midibox)
        self.qmidibox = self.ctx.qbox

        self.setResizeMode(self.SizeRootObjectToView)

        self.setSource(QUrl.fromLocalFile(str(pathlib.Path(__file__).parent / "StandaloneWidget.qml")))
        ro = self.rootObject()
        config = kwargs.get('config', {})
        init_context(self.ctx, ro, config)

        if kwargs.get("playlist_url") is not None:
            wv = ro.findChild(QObject, "playlistWebView")
            if wv is not None:
                wv.setProperty("url", kwargs.get("playlist_url"))

        if hasattr(app, "aboutToQuit"):
            # Set empty source to avoid bad contextProperty references on exit
            getattr(app, "aboutToQuit").connect(functools.partial(self.setSource, QUrl.fromLocalFile("")))

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 720)#1280//2, 720//2)
        return QSize(1280 // 2, 720 // 2)

    def sizeHint(self) -> QSize:
        return QSize(0, 720)
        return QSize(1280 // 1, 720 // 1)


def create_gui(midibox: BaseMidibox, big_mode: bool = False, disable_sandbox: bool = False, config: Any = None) -> Application:
    QIcon.setThemeName("Adwaita")
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if disable_sandbox:
        os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = str(1)
    initialize_webengine()

    qapp = QApplication(sys.argv)
    if big_mode:
        qapp.setFont(QFont("Helvetica", 36))

    e = QQmlApplicationEngine()
    cwd = pathlib.Path(__file__).parent.resolve()
    e.addImportPath(str(cwd.joinpath("style/")))

    ctx = populate_context(e.rootContext(), midibox)

    e.load(str(cwd.joinpath('midibox.qml')))
    e.quit.connect(qapp.quit)
    qapp.aboutToQuit.connect(e.deleteLater)

    if len(e.rootObjects()) == 0:
        sys.exit(1)
    root: QQuickItem = e.rootObjects()[0]  # type: ignore
    init_context(ctx, root, config)

    if big_mode:
        root.setProperty("visibility", "FullScreen")
    else:
        root.setProperty("width", 1280 // 1)
        root.setProperty("height", 720 // 1)

    return Application(qapp, e, ctx, midibox)
