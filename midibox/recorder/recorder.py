import time
import mido
from pathlib import Path
from typing import Optional
from mido import Message, MidiFile, MidiTrack

from ..controller.base import BaseMidibox


DEFAULT_TEMPO = 500000
DEFAULT_TICKS_PER_BEAT = 480


class Recorder():
    def __init__(self, midibox: BaseMidibox):
        self._midibox = midibox
        self._midifile = None

        self.track = MidiTrack()
        self.mid = MidiFile(ticks_per_beat=DEFAULT_TICKS_PER_BEAT)
        self.mid.tracks.append(self.track)
        self.filepath: Optional[Path] = None
        self.last_save: Optional[float] = None
        self.last_event = 0.0
        self.init()

    def init(self) -> None:
        self._midibox._callbacks.append(self._input_callback)

    def _input_callback(self, msg: Message) -> None:
        ts = time.time()
        if msg.type in ['note_on', 'note_off', 'control_change']:
            if self.last_save is None:
                self.last_event = ts
                self.last_save = ts
                self.filepath = Path(f"~/midibox_rec_{int(ts)}.mid").expanduser()

            rts = ts - self.last_event
            tst = mido.second2tick(rts, DEFAULT_TICKS_PER_BEAT, DEFAULT_TEMPO)
            m2 = msg.copy(time=tst)
            self.track.append(m2)
            self.last_event = ts

        if self.last_save is not None and (
                msg.type == "reset" or
                (self.last_save < self.last_event and self.last_save + 60 * 5 < ts)
        ):
            self.last_save = self.last_event
            self.mid.save(self.filepath)

    def close(self):
        self.last_save = self.last_event
        if self.filepath is not None:
            self._input_callback(Message('reset'))
