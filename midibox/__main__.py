#!/usr/bin/python
import os
import sys
import time
import socket
import pathlib
import argparse

from .controller import Midibox
from .osc.client import OscMidibox
from .osc.client_handler import MidiboxOSCClientHandler
from .osc.server import SharedTCPServer, zc_register_osc_tcp


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-O", "--osc-server", help="Enable OSC server", action='store_true')
    parser.add_argument("-o", "--osc-client", help="Use OSC client as device")
    parser.add_argument("-s", "--simulator", help="Use simulator as device", action='store_true')
    parser.add_argument("-p", "--port", help="Specify device port")
    parser.add_argument("-G", "--no-gui", help="Do not run GUI", action='store_false', dest='gui')
    parser.add_argument("-d", "--debug", help="Debug Midibox", action='store_true')
    parser.add_argument("--disable-sandbox", help="Disable sandbox for QtWebEngine", action='store_true')
    #parser.add_argument("--disable-sandbox", help="Disable sandbox for QtWebEngine", action='store_true')
    return parser.parse_args()


def create_midibox_instance(args):
    midibox_params = {
        'port_name': 'XIAO nRF52840',
        'debug': args.debug,
    }
    if args.port:
        midibox_params["port_name"] = args.port

    if args.simulator:
        midibox_params["port_name"] = 'MidiboxSimulator'
        midibox_params["virtual"] = True
        midibox_params["find"] = True

    if args.osc_client:
        midibox = OscMidibox(args.osc_client)
    else:
        midibox = Midibox(**midibox_params)

    return midibox


def main():
    args = parse_args()

    midibox = create_midibox_instance(args)
    midibox.connect()

    if args.osc_server:
        MidiboxOSCClientHandler.mb = midibox
        osc_srv = SharedTCPServer(MidiboxOSCClientHandler)
        zc_svcs = zc_register_osc_tcp()

    if args.gui:
        import qasync
        import asyncio
        from .widget import create_gui
        app = create_gui(midibox, disable_sandbox=args.disable_sandbox)

        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        #asyncio.ensure_future(app.pc.get_messages())
        with loop:
            loop.run_forever()
    else:
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

    if args.osc_server:
        for zc, si in zc_svcs:
            zc.close()
        osc_srv.shutdown()

    midibox.disconnect()

if __name__ == "__main__":
    main()
