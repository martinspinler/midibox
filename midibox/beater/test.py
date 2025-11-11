import logging
import argparse
import mido

from visualiser import MPVisualiser
from predictor import TempoPredictor


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
            range(260, 10000)
        ],
        "time_mult": 1 / 0.483,
    }, {
        "filename": "bands/Perfect Time/midi/Aruanda.mid",
        "skip_ranges": [
            range(0, 55),
            range(240, 100000),
        ],
        "tempo_hint": 176 * 2,
        "time_mult": 2.933 * 2,
    }, {
        "filename": "bands/Perfect Time/midi/Can You Can Two Toucans in Two Cans.mid",
        "bch": 3,
        "tempo_hint": 180,
        "time_mult": 1/3,
        "skip_ranges": [
            range(60, 360000),
        ],
    }, {
        "filename": "bands/Perfect Time/midi/Days of Wine and Roses.mid",
        "bch": 3,
        "tempo_hint": 165,
        "time_mult": 1 / 0.3636,
        "skip_ranges": [
            range(0, 36),
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
    parser.add_argument('-b', '--begin', type=float, default=0)
    parser.add_argument('-e', '--end', type=float, default=1e9)
    args = parser.parse_args()

    tf = testfiles[1]

    filename = args.root + tf["filename"]
    _midifile = mido.MidiFile(filename)
    temp_iter = iter(_midifile)
    visualiser = MPVisualiser()
    tp = TempoPredictor(visualiser)
    time_mult = tf.get("time_mult", 1)
    tp.set_hint(tf.get("tempo_hint", 120), time_mult)

    bch = tf.get("bch", 2)

    offset = None
    ttime = 0
    for msg_id, msg in enumerate(temp_iter):
        skip = skip_msg(tf, msg_id)
        time += msg.time
        ttime = time * time_mult

        if isinstance(msg, mido.MetaMessage):
            pass
        else:
            if msg.type == 'note_on' and msg.channel == bch:
                show_orig = False

                if offset is None and not skip:
                    offset = ttime

                ttime = ttime - (offset if offset is not None else 0)

                if offset is not None:
                    if args.begin is not None and args.begin > ttime:
                        logging.basicConfig(level=logging.DEBUG)
                    if args.end is not None and args.end < ttime:
                        logging.basicConfig(level=logging.WARNING)
                        skip = True

                if not skip:
                    tp.check_beat(ttime) # Helper for correct printing sequence
                if not skip:
                    print(('-' if skip else "=") * 10, f"{msg_id: 4d} {note2text(msg.note):4}", f"{ttime:.3f}", f"(orig: {(ttime+offset) / time_mult:.3f})" if show_orig else "", "=" * 10)
                if not skip:
                    tp.on_note_event(ttime, msg)

    visualiser.draw(max(args.begin, 0), min(ttime, args.end))

if __name__ == "__main__":
    test()
