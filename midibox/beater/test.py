import logging
import argparse
import mido

from .visualiser import MPVisualiser
from .predictor import TempoPredictor


testfiles = [
    {
        "filename": "TestMidi.mid",
        "tempo_hint": 120,
        "skip_msgs": [
#            14,
            24,
        #    71,
            88,
            75,
            119,
        ],
        "skip_ranges": [
            range(0, 13),
            #range(260, 10000)
        ],
        "time_mult": 1 / 0.483,
    }, {
        "filename": "bands/Perfect Time/midi/Aruanda.mid",
        "skip_ranges": [
            range(0, 55),
            #range(240, 100000),
        ],
        "tempo_hint": 176 * 1,
        "time_mult": 2.933 * 1,
        "style_hint": "samba",
    }, {
        "filename": "bands/Perfect Time/midi/Can You Can Two Toucans in Two Cans.mid",
        "bch": 3,
        "tempo_hint": 180*2,
        "time_mult": 1/3 *2,
        "skip_ranges": [
            #range(60, 360000),
        ],
        "style_hint": "samba",
    }, {
        "filename": "bands/Perfect Time/midi/Days of Wine and Roses.mid",
        "bch": 3,
        "tempo_hint": 165,
        "time_mult": 1 / 0.3636,
        "skip_ranges": [
            #range(0, 36),
            #range(200, 20000),
        ],
    },
]


def skip_msg(tf, msg_id):
    skip_msgs = tf.get("skip_msgs", [])
    skip_ranges = tf.get("skip_ranges", [])
    if msg_id in skip_msgs:
        return True
    for r in skip_ranges:
        if msg_id in r:
            return True
    return False


def note2text(note: int) -> str:
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return note_names[note % 12] + str(note // 12 - 2)


def test():
    time = 0
    #logging.basicConfig(level=logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--root')
    parser.add_argument('-f', '--file', type=int, default=0)
    parser.add_argument('-b', '--begin', type=float, default=0)
    parser.add_argument('-e', '--end', type=float, default=1e9)
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-g', '--graph', action='store_true')
    parser.add_argument('-o', '--omni', action='store_true')
    parser.add_argument('-D', '--debug-beats', type=str, default="")
    parser.add_argument('-v', '--verbose', action='count', default=0)
    args = parser.parse_args()

    tf = testfiles[args.file]

    filename = args.root + tf["filename"]
    _midifile = mido.MidiFile(filename)
    temp_iter = iter(_midifile)
    visualiser = MPVisualiser(debug=args.debug, verbosity=args.verbose)
    tp = TempoPredictor(debug=args.debug, debug_beats=[int(n) for n in args.debug_beats.split(",") if n], verbosity=args.verbose)
    tp.listeners.append(visualiser)
    visualiser.pred = tp

    time_mult = tf.get("time_mult", 1)
    tp.set_hint(tf.get("tempo_hint", 120), time_mult, tf.get("style_hint", "swing"))

    bch = tf.get("bch", 2)

    offset = None
    ttime = 0
    last = None
    for msg_id, msg in enumerate(temp_iter):
        skip = skip_msg(tf, msg_id)
        time += msg.time
        ttime = time * time_mult

        if isinstance(msg, mido.MetaMessage):
            pass
        else:
            if msg.type == 'note_on' and (msg.channel == bch or args.omni):
                if offset is None and not skip:
                    offset = ttime

                ttime = ttime - (offset if offset is not None else 0)

                if offset is not None:
                    if args.begin is not None and args.begin > ttime:
                        logging.basicConfig(level=logging.DEBUG)
                    if args.end is not None and args.end < ttime:
                        logging.basicConfig(level=logging.WARNING)
                        if last is None:
                            last = ttime
                        skip = True

                if not skip:
                    tp.on_note_event(ttime, msg_id, msg, f"{note2text(msg.note):4}")

    if last:
        tp.check_beat(last)

    if args.graph:
        visualiser.draw(max(args.begin, 0), min(ttime, args.end))

if __name__ == "__main__":
    test()
