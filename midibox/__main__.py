#!/usr/bin/python
import time
import yaml
import argparse

from . import backends
from .mido import MidoMidibox
from .osc.client_handler import MidiboxOSCClientHandler
from .osc.server import TCPOSCServer, zc_register_osc_tcp

from .midiplayer import Midiplayer, MidiplayerOSCClientHandler
from .controller import BaseMidibox
from .recorder import Recorder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-O", "--osc-server", help="Enable OSC server", action='store_true')
    parser.add_argument("-o", "--osc-client", help="Use OSC client as device")
    parser.add_argument("-s", "--simulator", help="Use simulator as device", action='store_true')
    parser.add_argument("-p", "--port", help="Specify device port")
    parser.add_argument("-G", "--no-gui", help="Do not run GUI", action='store_false', dest='gui')
    parser.add_argument("-d", "--debug", help="Debug Midibox", action='store_true')
    parser.add_argument("-c", "--config", help="Configuration YAML", default=None)

    parser.add_argument("--osc-server-port", help="Specify OSC server port", metavar='int', type=int, default=4302)
    parser.add_argument("--disable-sandbox", help="Disable sandbox for QtWebEngine", action='store_true')
    return parser.parse_args()


def create_midibox_instance(args: argparse.Namespace) -> BaseMidibox:
    mb_params = {
        'debug': args.debug,
    }

    if args.osc_client:
        mb_backend = 'osc'
        mb_params['url'] = args.osc_client
    else:
        mb_backend = 'simulator' if args.simulator else backends.default_backend

    if args.port:
        mb_params["port_name"] = args.port
    return backends.create_midibox_from_config(mb_backend, **mb_params)


class MainOSCClientHandler(MidiboxOSCClientHandler, MidiplayerOSCClientHandler):
    pass


def main_loop_gui(args, midibox, config):
    import qasync
    import asyncio
    from .widget import create_gui

    app = create_gui(midibox, disable_sandbox=args.disable_sandbox, config=config)

    loop = qasync.QEventLoop(app.qapp)
    asyncio.set_event_loop(loop)

    # asyncio.ensure_future(app.pc.get_messages())
    with loop:
        loop.run_forever()


def main() -> None:
    args = parse_args()

    config = {}
    if args.config:
        with open(args.config, 'r') as file:
            config = yaml.safe_load(file)

    midibox = create_midibox_instance(args)
    midibox.connect()

    if args.osc_server:
        if not isinstance(midibox, MidoMidibox):
            raise ValueError("The MidoMidibox must be used for server mode")

        mp = Midiplayer(midibox._output_port_name)
        mp.init()
        mr = Recorder(midibox._input_port_name)

        midi_file = config.get("midiplayer", {}).get("autoload")
        if midi_file:
            mp.open(midi_file)
        MainOSCClientHandler.mp = mp
        MainOSCClientHandler.mb = midibox
        osc_srv = TCPOSCServer(("0.0.0.0", args.osc_server_port), MainOSCClientHandler)
        osc_srv.start()
        allowed_ips = None
        #allowed_ips = ['10.42.0.1']
        zc_svcs = zc_register_osc_tcp(allowed_ips=allowed_ips, port=args.osc_server_port)

    try:
        if args.gui:
            main_loop_gui(args, midibox, config)
        else:
            while True:
                time.sleep(0.1)
    finally:
        if args.osc_server:
            mr.close()

            for zc, si in zc_svcs:
                zc.close()
            osc_srv.stop()

            mp.destroy()

        midibox.disconnect()


if __name__ == "__main__":
    main()
