import os
import sys
import signal
import functools
import pathlib

from typing import Any
from dataclasses import dataclass

from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from PyQt6.QtQml import QQmlContext
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtCore import QUrl, QSize, QObject

from ..controller import BaseMidibox
from ..config import presets_from_config
from .gui import (
    QMidiBox, NameDataItemModel, ProgramPresetModel, PedalCcModel,
    PedalModeModel, GraphUpdater, PlayModeModel,
)


DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720


@dataclass
class ApplicationContext:
    qbox: QMidiBox
    gu: GraphUpdater
    ppm: NameDataItemModel
    pcm: NameDataItemModel
    pmm: NameDataItemModel
    plmm: NameDataItemModel


@dataclass
class Application:
    qapp: QApplication
    qml_engine: QQmlApplicationEngine
    ctx: ApplicationContext
    box: BaseMidibox


def init_context(
    ctx: ApplicationContext, ro: QQuickItem, config: dict[str, Any]
) -> None:
    children = ro.children()
    if len(children) > 1:
        children[1].setProperty(
            "my_scale", config.get("gui", {}).get("scale", 1)
        )

    presets = presets_from_config(config)
    ctx.qbox.init(ro, config, presets)


def populate_context(
    ctx: QQmlContext, box: BaseMidibox
) -> ApplicationContext:
    # Store all context properties: setContextProperty doesn't increment refcnt
    ns = ApplicationContext(
        QMidiBox(box),
        GraphUpdater(box),
        ProgramPresetModel(box),
        PedalCcModel(box),
        PedalModeModel(box),
        PlayModeModel(box),
    )

    ctx.setContextProperty("midibox", ns.qbox)
    ctx.setContextProperty("programPresetsModel", ns.ppm)
    ctx.setContextProperty("monitor", ns.gu)
    ctx.setContextProperty("pedalCcModel", ns.pcm)
    ctx.setContextProperty("pedalModeModel", ns.pmm)
    ctx.setContextProperty("playModeModel", ns.plmm)

    return ns


class MidiboxQuickWidget(QQuickWidget):
    def __init__(
        self, app: QApplication, midibox: BaseMidibox, **kwargs: Any
    ) -> None:
        super().__init__()

        self.midibox = midibox
        self.ctx = populate_context(self.rootContext(), self.midibox)
        self.qmidibox = self.ctx.qbox

        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        self.setSource(
            QUrl.fromLocalFile(
                str(pathlib.Path(__file__).parent / "StandaloneWidget.qml")
            )
        )
        ro = self.rootObject()
        config = kwargs.get("config", {})
        init_context(self.ctx, ro, config)

        playlist_url = kwargs.get("playlist_url")
        if playlist_url is not None:
            wv = ro.findChild(QObject, "playlistWebView")
            if wv is not None:
                wv.setProperty("url", playlist_url)

        # Set empty source to avoid bad contextProperty references on exit
        app.aboutToQuit.connect(
            functools.partial(self.setSource, QUrl.fromLocalFile(""))
        )

    def minimumSizeHint(self) -> QSize:
        return QSize(0, DEFAULT_HEIGHT)

    def sizeHint(self) -> QSize:
        return QSize(0, DEFAULT_HEIGHT)


def create_gui(
    midibox: BaseMidibox,
    big_mode: bool = False,
    disable_sandbox: bool = False,
    config: Any = None,
) -> Application:
    QIcon.setThemeName("Adwaita")
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if disable_sandbox:
        os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

    qapp = QApplication(sys.argv)
    if big_mode:
        qapp.setFont(QFont("Helvetica", 36))

    e = QQmlApplicationEngine()
    cwd = pathlib.Path(__file__).parent.resolve()
    e.addImportPath(str(cwd.joinpath("style/")))

    ctx = populate_context(e.rootContext(), midibox)

    e.load(str(cwd.joinpath("midibox.qml")))
    e.quit.connect(qapp.quit)
    qapp.aboutToQuit.connect(e.deleteLater)

    if not e.rootObjects():
        sys.exit(1)

    root: QQuickItem = e.rootObjects()[0]  # type: ignore[assignment]
    init_context(ctx, root, config)

    if big_mode:
        root.setProperty("visibility", "FullScreen")
    else:
        root.setProperty("width", DEFAULT_WIDTH)
        root.setProperty("height", DEFAULT_HEIGHT)

    return Application(qapp, e, ctx, midibox)
