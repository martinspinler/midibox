#!/usr/bin/python3
import time
import io
import threading
import queue
import mido

from typing import Optional, Callable, Tuple, Iterable

import dataclasses
from dataclasses import dataclass


def now() -> float:
    return time.time()


@dataclass
class MidiplayerStatus():
    total_time: float = 0
    current_time: float = 0  # Current time from beggining of the midi file
    playing: bool = False
    paused: bool = False  # Can be playing and paused together
    measure: int = 1
    beat: int = 1


@dataclass
class MidiplayerState():
    midi_iter: Iterable[mido.Message]
    total_time: float = 0
    next_event: float = 0 # Absolute time of next event from input file iterator
    #abs_beat: int = 0

    speed: float = 1.0  # Relative speed change
    ct_measure: int = 1
    ct_beat: int = 1
    ct_tempo: int = 500000
    ct_bpm: Optional[int] = None
    #ct_tempo_time: float = 0 # Last time when tempo or time_signature changed
    ts: Tuple[int, int] = (4, 4)
    #ts_beat: int = 0 # Relative beat count from last time_signature change
    next_beat_reltime: Optional[float] = None
    global_time: Optional[float] = None

    _paused: Optional[float] = None
    current_time_offset: float = 0
    beat_time: float = 0


class Midiplayer():
    def __init__(self, port: str):
        self._port_name = port
        self._midifile = None
        self._seek_state: MidiplayerState = MidiplayerState(iter(()))

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._seek = threading.Event()
        self.update_cbs: list[Callable[[MidiplayerStatus], None]] = []
        self._update_queue: queue.Queue[MidiplayerStatus] = queue.Queue()

        self._playing_notes: dict[Tuple[int, int], int] = {}
        self._tpb = 480

        self.status = MidiplayerStatus()
        self.jumps: list[tuple[tuple[int, int], tuple[int, int]]] = [
            #((16, 1), (32, 1)),
            #((5, 1), (1, 1)),
        ]

    def init(self) -> None:
        self._output = mido.open_output(self._port_name)

        self._thread = threading.Thread(target=self._run)
        self._thread.start()

        self._update_thread = threading.Thread(target=self._update_func)
        self._update_thread.start()

    def destroy(self) -> None:
        self._stop.set()
        self._thread.join()
        self._update_thread.join()

    def is_paused(self) -> bool:
        return self._pause.is_set()

    def pause(self) -> None:
        self.play(False)

    def play(self, play: bool = True) -> None:
        if not self.is_paused() == play:
            return

        if play:
            self._pause.clear()
        else:
            self._pause.set()

    def open(self, filename: str) -> None:
        self._midifile = mido.MidiFile(filename, ticks_per_beat=self._tpb)
        if self._midifile is None:
            return
        self.rewind()

    def load(self, data: bytes) -> None:
        file = io.BytesIO(data)
        self._midifile = mido.MidiFile(file=file, ticks_per_beat=self._tpb)
        if self._midifile is None:
            return
        self.rewind()

    def rewind(self):
        self.pause()
        self.seek(0)

    def seek(self, timestamp: float | None = None, measure: Optional[int] = None) -> None:
        if self._midifile is None:
            return

        st = MidiplayerState(iter(self._midifile))
        st.total_time = self._midifile.length

        temp_iter: Iterable[mido.MidiMessage] = iter(self._midifile)
        for msg in temp_iter:
            pt = st.next_event * 1_000_000
            self._advance_beat(pt, st)

            if \
                    (timestamp is not None and st.next_event > timestamp) or \
                    (measure is not None and st.ct_measure == measure):
                break

            st.next_event += msg.time

            if isinstance(msg, mido.MetaMessage):
                self._handle_msg_meta(st.next_event, st, msg)
            next(st.midi_iter)

        self._seek_state = st
        self._seek.set()

    def _stop_all_playing_notes(self) -> None:
        # FIXME: send AllNotesOff(), because user can play too
        self._output.reset()

        for c in set([channel for (note, channel), vel in self._playing_notes.items()]):
            self._output.send(mido.Message('control_change', channel=c, control=120, value=0))
            #self._output.send(mido.Message('note_off', channel=c, note=note, velocity=0))
        self._playing_notes.clear()

    def _handle_msg(self, pt: float, st: MidiplayerState, msg: mido.Message) -> None:
        if isinstance(msg, mido.MetaMessage):
            self._handle_msg_meta(pt, st, msg)
        else:
            self._handle_msg_nonmeta(msg)

    def _handle_msg_nonmeta(self, msg: mido.Message) -> None:
        if not isinstance(msg, mido.MetaMessage):
            if msg.type == 'note_on' and msg.velocity == 0:
                msg.type = 'note_off'

            if msg.type == 'note_on':
                note = (msg.note, msg.channel)
                self._playing_notes.update({note: msg.velocity})
            elif msg.type == 'note_off':
                note = (msg.note, msg.channel)
                if note in self._playing_notes:
                    del self._playing_notes[note]

            if True or msg.type in ['note_on', 'note_off', 'control_change', 'program_change']:
                self._output.send(msg)

    def _handle_msg_meta(self, pt: float, st: MidiplayerState, msg: mido.Message) -> None:
        if msg.type == 'time_signature':
            st.ts = (msg.numerator, msg.denominator)
            #print("TS:", st.ts)
            #st.ts_beat = st.abs_beat
        elif msg.type == 'set_tempo':
            # Current beat relative position (percent)
            #rel_position = (pt - st.beat_time) / st.ct_tempo
            #beat_time = pt - rel_position * msg.tempo
            #print("Tempo", mido.tempo2bpm(msg.tempo))
            st.beat_time = (msg.tempo * (st.beat_time - pt) + st.ct_tempo * pt) / st.ct_tempo
            st.ct_tempo = msg.tempo

    def _update_func(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._update_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            for cb in self.update_cbs:
                cb(item)

    def _update_cbs(self, status: MidiplayerStatus) -> None:
        self.status = dataclasses.replace(status)
        while True:
            try:
                _ = self._update_queue.get(timeout=0)
            except queue.Empty:
                break

        self._update_queue.put_nowait(self.status)

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._seek.is_set():
                time.sleep(0.01)
                continue

            self._seek.clear()
            ss = self._seek_state

            self._do_play(ss)
            self._stop_all_playing_notes()

    def _do_pause(self, status: MidiplayerStatus, st: MidiplayerState) -> bool:
        if self._pause.is_set():
            if st._paused is None:
                self._stop_all_playing_notes()
                st._paused = now()
                status.paused = True
                self._update_cbs(status)
            return True

        if st._paused is not None:
            st.current_time_offset += now() - st._paused
            st._paused = None

        status.paused = False

        self._update_cbs(status)
        return False

    def _can_play(self) -> bool:
        return not (self._stop.is_set() or self._seek.is_set())

    def _advance_beat(self, pt: float, st: MidiplayerState) -> bool:
        mod = False
        while pt - st.beat_time > st.ct_tempo:
            st.beat_time += st.ct_tempo
            #st.abs_beat += 1
            st.ct_beat += 1
            mod = True
            # FIXME: compute with denominators other than 4
            if st.ct_beat > st.ts[0]:
                st.ct_beat = 1
                st.ct_measure += 1
        return mod

    def _do_play(self, st: MidiplayerState):
        msg: Optional[mido.Message] = None
        st.current_time_offset = now() - st.next_event
        #print(f"{st.ct_measure}.{st.ct_beat}")

        status = MidiplayerStatus(st.total_time, st.next_event, False, self.is_paused(), st.ct_measure, st.ct_beat)

        self._update_cbs(status)
        while self._can_play():
            if self._do_pause(status, st):
                time.sleep(0.01)
                continue

            if msg is None:
                try:
                    msg = next(st.midi_iter) #type: ignore
                except StopIteration:
                    self.rewind()
                    break
                st.next_event += msg.time
            playback_time = now() - st.current_time_offset

            pt = playback_time * 1_000_000
            if self._advance_beat(pt, st):
                #print(f"{st.ct_measure}.{st.ct_beat}")
                if self.jumps:
                    (cm, cb), (nm, nb) = self.jumps[0]
                    if (cm, cb) == (st.ct_measure, st.ct_beat):
                        self.seek(measure=nm)

            status = MidiplayerStatus(st.total_time, st.next_event, False, self.is_paused(), st.ct_measure, st.ct_beat)

            status.playing = True
            status.current_time = playback_time
            status.measure = st.ct_measure
            status.beat = st.ct_beat
            self._update_cbs(status)

            duration_to_next_event = st.next_event - playback_time
            if duration_to_next_event > 0.0:
                time.sleep(min(duration_to_next_event, 0.01))
                continue

            self._handle_msg(pt, st, msg)
            msg = None
