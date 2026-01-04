#!/usr/bin/python
import time
import yaml
import argparse
import mido

from . import backends
from .mido import MidoMidibox
from .osc.client_handler import MidiboxOSCClientHandler
from .osc.server import TCPOSCServer, ZCPublisher

from .midiplayer import Midiplayer, MidiplayerOSCClientHandler
from .controller import BaseMidibox
from .recorder import Recorder
from .beater import TempoPredictor, TempoPredictorOSCClientHandler, TempoListener
from .beater.visualiser import Visualiser


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
    parser.add_argument("--player", help="Enable MIDI player", action='store_true')
    parser.add_argument("--recorder", help="Enable MIDI recording", action='store_true')
    parser.add_argument("--predictor", help="Enable beat predictor", action='store_true')
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


class MyTempoListener(TempoListener):
    def __init__(self, midibox):
        self._midibox = midibox
        self.playing = False
        self.time_start = time.time()

    def on_beat(self, beat_last, beat_len):
        if not self.playing:
            msg = mido.Message(type='note_on', note=60, velocity=(0 if self.playing else 100))
            self.playing = False
            self._midibox.sendmsg(msg)


def connect_tempo_predictor_t1(midibox, tp, tl, mp):
    def note_event(msg):
        try:
            print(msg)
            if msg.type == 'note_on' and msg.note < 60:
                mp.play()
            if msg.type == 'control_change' and msg.control == 67:
                tp.on_note_event(time.time() - tl.time_start, 0, msg, str(msg))
        except Exception as e:
            import traceback
            print(e)
            traceback.print_exc()

    midibox._callbacks.append(note_event)
    tp.listeners.append(tl)
    tp.listeners.append(Visualiser(debug=True, verbosity=3))


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

    if args.player:
        midiplayer = Midiplayer(midibox)
        midiplayer.init()

        midi_file = config.get("midiplayer", {}).get("autoload")
        if midi_file:
            midiplayer.open(midi_file)

    if args.recorder:
        recorder= Recorder(midibox)

    if args.predictor:
        tl = MyTempoListener(midibox)
        tempopredictor = TempoPredictor()
        connect_tempo_predictor_t1(midibox, tempopredictor, tl, midiplayer)

    if args.osc_server:
        class MbOCH(MidiboxOSCClientHandler):
            mb = midibox

        OCH = MbOCH
        if args.player:
            class MplOCH(OCH, MidiplayerOSCClientHandler):  # type: ignore[valid-type, misc]
                mp = midiplayer
            OCH = MplOCH

        if args.predictor:
            class MprOCH(OCH, TempoPredictorOSCClientHandler):  # type: ignore[valid-type, misc]
                tp = tempopredictor
            OCH = MprOCH

        osc_srv = TCPOSCServer(("0.0.0.0", args.osc_server_port), OCH)
        osc_srv.start()
        allowed_ips = None
        #allowed_ips = ['10.42.0.1']
        zc = ZCPublisher(allowed_ips=allowed_ips, port=args.osc_server_port)

    try:
        if args.gui:
            main_loop_gui(args, midibox, config)
        else:
            while True:
                tempopredictor.check_beat(time.time() - tl.time_start)
                time.sleep(0.01)
    finally:
        if args.recorder:
            recorder.close()

        if args.osc_server:
            zc.stop()
            osc_srv.stop()

        if args.player:
            midiplayer.destroy()

        midibox.disconnect()


if __name__ == "__main__":
    main()
