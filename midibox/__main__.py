#!/usr/bin/python
import os
import sys
import signal
import time
import socket
import pathlib

from PyQt5.QtCore import QObject, pyqtSlot, pyqtProperty
from PyQt5.QtGui import QGuiApplication, QIcon, QFont
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtWidgets import QApplication
from PyQt5.QtQuickWidgets import QQuickWidget
import PyQt5.QtWebEngineCore
import PyQt5.QtWebEngine

from PyQt5 import QtCore, QtGui, QtWidgets, QtQuickWidgets

from controller import Midibox
from gui import *

import pathlib
cwd = pathlib.Path(__file__).parent.resolve()

reterm = socket.gethostname() in ["alarmpi"]

#os.environ["QT_QUICK_CONTROLS_CONF"] = str(cwd.joinpath("qtquickcontrols2.conf"))
if reterm:
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = str(1)

QIcon.setThemeName("Adwaita")

from PyQt5.QtWebEngineWidgets import QWebEngineView

def mymain():
    global app
    we = PyQt5.QtWebEngine.QtWebEngine
    we.initialize()
    app = QApplication(sys.argv)
    if reterm:
        app.setFont(QFont("Helvetica", 36))

    #app = QApplication.instance()
    def tryInstance(l):
        for cls in l:
            try: return cls()
            except: pass
        raise

    #if reterm:
    #box = Midibox()
    box = Midibox("Control", "GigPanel", virtual=True, find=False, debug=True)
    #else:
    #    box = tryInstance([RolandMidibox, FakeMidibox])

    qbox = QMidiBox(box)
    gu = GraphUpdater(box)

    w = QQmlApplicationEngine()
    w.addImportPath(str(cwd.joinpath("style/")))

    pl = PlaylistModel(app)
    ppm = ProgramPresetModel(box)
    ctx = w.rootContext()
    ctx.setContextProperty("midibox", qbox)
    ctx.setContextProperty("programPresetsModel", ppm)
    ctx.setContextProperty("monitor", gu)
    ctx.setContextProperty("playlistModel", pl)
    ctx.setContextProperty("reterm", reterm)
    w.load(str(cwd.joinpath('midibox.qml')))
    w.quit.connect(app.quit)
    app.aboutToQuit.connect(w.deleteLater)

    if len(w.rootObjects()) == 0: exit(1)
    root = w.rootObjects()[0]
    if reterm:
        root.setProperty("visibility", "FullScreen")
        root.children()[1].setProperty("my_scale", 1)
    else:
        root.setProperty("width", 1280 // 2)
        root.setProperty("height", 720 // 2)
        root.children()[1].setProperty("my_scale", 1)


#mb = root.findChild(QObject, 'MidiStatsChart')
#mb.setProperty("currentIndex", 1)
#win = w.rootObjects()[0]

    pc = playlist.PlaylistClient(None, 'perfecttime.livelist.cz')
    app.pc = pc
    app.pl = pl
    app.mydata = [pl, ppm, qbox, box, gu, pl, w]
    return app


import playlist
import qasync
import asyncio
#from asyncqt import QEventLoop


def umain():
    global app
    app = mymain()
    ##loop = asyncqt.QEventLoop(app)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    ##app.exec()

    #asyncio.ensure_future(app.pc.get_messages())
    asyncio.ensure_future(xmain())

    with loop:
        loop.run_forever()

async def main():
    app = mymain()
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    #app = QApplication.instance()
    #init_parser(app)
    #set_style(app)
    loop, future = gigpanel.init_loop(app)

async def xmain():
    global app
    #await app.pc.connect()
    #app.songs = await app.pc.get_db()
    #dlpl = await app.pc.get_playlist()
    #app.pl.load(dlpl)

if False:
    app.exec()

    with loop:
        try:
            loop.run_forever()
        except asyncio.exceptions.CancelledError:
            pass

    #print("X")
#    try:
#        asyncio.ensure_future(app.pc.get_messages())
#        await future
#    except:
#        raise

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    umain()
#    try:
#        qasync.run(main())
#    except asyncio.exceptions.CancelledError:
#        sys.exit(0)
