#!/usr/bin/python
import os
import sys
import signal
import socket
import pathlib
import argparse

import qasync
import asyncio

from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtWidgets import QApplication
#import PyQt5.QtWebEngineCore

from .controller import Midibox
from .widget import populate_context, initialize_webengine


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--simulator", help="Use simulator", action='store_true')
    parser.add_argument("-d", "--debug", help="Debug Midibox", action='store_true')
    parser.add_argument("--disable-sandbox", help="Disable sandbox for QtWebEngine", action='store_true')
    return parser.parse_args()

def mymain(*args, **kwargs):
    global app

    if kwargs.get("disable_sandbox"):
        os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = str(1)
    initialize_webengine()
    app = QApplication(sys.argv)
    reterm = socket.gethostname() in ["alarmpi"]
    if reterm:
        app.setFont(QFont("Helvetica", 36))

    #app = QApplication.instance()
    def tryInstance(lst):
        for cls in lst:
            try:
                return cls()
            except:
                pass
        raise

    #if reterm:
    midibox_params = {'port_name': 'Midibox XIAO BLE', 'debug': kwargs["debug"]}
    if kwargs.get("simulator"):
        midibox_params["port_name"] = 'MidiboxSim'
        midibox_params["virtual"] = True
        midibox_params["find"] = False
        midibox_params["find"] = True
        midibox_params["debug"] = True

    app.midibox = Midibox(**midibox_params)

    app.engine = w = QQmlApplicationEngine()
    cwd = pathlib.Path(__file__).parent.resolve()
    w.addImportPath(str(cwd.joinpath("style/")))

    app.ctx = populate_context(w.rootContext(), app.midibox)

    app.midibox.connect()

    w.load(str(cwd.joinpath('midibox.qml')))
    w.quit.connect(app.quit)
    app.aboutToQuit.connect(w.deleteLater)

    if len(w.rootObjects()) == 0:
        sys.exit(1)
    root = w.rootObjects()[0]
    if reterm:
        root.setProperty("visibility", "FullScreen")
        root.children()[1].setProperty("my_scale", 1)
    else:
        root.setProperty("width", 1280 // 1)
        root.setProperty("height", 720 // 1)
        root.children()[1].setProperty("my_scale", 1)

    #pc = livelist.PlaylistClient(None, 'perfecttime.livelist.cz')
    return app


#from asyncqt import QEventLoop


def main():
    #os.environ["QT_QUICK_CONTROLS_CONF"] = str(cwd.joinpath("qtquickcontrols2.conf"))
    QIcon.setThemeName("Adwaita")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    args = parse_args()

    global app
    app = mymain(**vars(args))
    ##loop = asyncqt.QEventLoop(app)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    ##app.exec()

    #asyncio.ensure_future(app.pc.get_messages())
    asyncio.ensure_future(xmain())

    with loop:
        loop.run_forever()
    app.midibox.disconnect()

#async def main_async(*args, **kwargs):
#    app = mymain(*args, **kwargs)
#    loop = qasync.QEventLoop(app)
#    asyncio.set_event_loop(loop)
#    #app = QApplication.instance()
#    #init_parser(app)
#    #set_style(app)
#    loop, future = gigpanel.init_loop(app)

async def xmain():
    global app
    #await app.pc.connect()
    #app.songs = await app.pc.get_db()
    #dlpl = await app.pc.get_playlist()
    #app.pl.load(dlpl)


use_async = False

if __name__ == "__main__":
    main()
    #if not use_async:
    #    main(**vars(args))
    #else:
    #    try:
    #        qasync.run(main_async())
    #    except asyncio.exceptions.CancelledError:
    #        sys.exit(0)
        #if False:
        #    app.exec()
        #    with loop:
        #        try:
        #            loop.run_forever()
        #        except asyncio.exceptions.CancelledError:
        #            pass

            #print("X")
        #    try:
        #        asyncio.ensure_future(app.pc.get_messages())
        #        await future
        #    except:
        #        raise
