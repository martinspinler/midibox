#!/usr/bin/python3
import time
import threading
import queue
import mido


class Midiplayer():
    def __init__(self, port, **kwargs):
        self._port_name = port
        self._midifile = None
        self._midiiter = iter(())
        self._global_time = 0.0

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._timer_reset = threading.Event()
        self.update_cbs = []
        self._update_queue = queue.Queue()

    def _update_func(self):
        while not self._stop.is_set():
            try:
                item = self._update_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            for cb in self.update_cbs:
                cb(item)

    def init(self):
        self.pause()

        self._thread = threading.Thread(target=self._run)
        self._thread.start()

        self._update_thread = threading.Thread(target=self._update_func)
        self._update_thread.start()

    def destroy(self):
        self._stop.set()
        self._thread.join()
        self._update_thread.join()

    def is_paused(self):
        return self._pause.is_set()

    def pause(self):
        self.play(False)

    def play(self, play=True):
        if not self.is_paused() == play:
            return

        if play:
            self._timer_reset.set()
            self._pause.clear()
        else:
            self._pause.set()

    def load(self, filename):
        self._midifile = mido.MidiFile(filename)
        self._midiiter = iter(self._midifile)

    def seek(self, timestamp=0.0):
        midiiter = iter(self._midifile)
        tempiter = iter(self._midifile)
        total_time = 0.0
        for msg in tempiter:
            if total_time >= timestamp:
                break
            total_time += msg.time
            next(midiiter)

        self._global_time = total_time

        self._midiiter = midiiter
        self._timer_reset.set()

    def _stop_all_playing_notes(self):
        self._output.reset()
        for n, vel in self._playing_notes.items():
            note, channel = n
            #self._output.send(mido.Message('note_off', channel=channel, note=note, velocity=0))

        #self._playing_notes.clear()

    def _handle_msg(self, msg):
        #print(msg)
        if not isinstance(msg, mido.MetaMessage):
            if msg.type == 'note_on' and msg.velocity == 0:
                print("RETYPE to note_off")
                msg.type = 'note_off'

            if msg.type == 'note_on':
                note = (msg.note, msg.channel)
                self._playing_notes.update({note: msg.velocity})
                #print("Add", note, self._playing_notes)
            elif msg.type == 'note_off':
                note = (msg.note, msg.channel)
                if note in self._playing_notes:
                    #print("Del", note, self._playing_notes)
                    del self._playing_notes[note]

            if True or msg.type in ['note_on', 'note_off', 'control_change', 'program_change']:
                self._output.send(msg)

    def _run(self):
        def now():
            return time.time()

        self._playing_notes = {}
        paused_msg = None

        t0 = None
        input_time = 0.0
        global_time = 0.0

        self._output = mido.open_output(self._port_name)

        while not self._stop.is_set():
            if self._pause.is_set():
                #t0 = None
                time.sleep(0.05)
                continue

            if self._timer_reset.is_set():
                self._timer_reset.clear()
                t0 = None
                paused_msg = None
                midi_iter = self._midiiter
                global_time = self._global_time
                midifile_length = self._midifile.length

            #for n, vel in self._playing_notes.items():
            #    note, channel = n
            #    self._output.send(mido.Message('note_on', channel=channel, note=note, velocity=vel))

            if paused_msg:
                self._handle_msg(paused_msg)
                paused_msg = None

            for msg in midi_iter:
                if not t0:
                    t0 = time.time()
                    input_time = 0.0

                input_time += msg.time

                run = True
                play = False

                while run and not play:
                    if self._timer_reset.is_set():
                        break
                    playback_time = now() - t0
                    duration_to_next_event = input_time - playback_time
                    if duration_to_next_event > 0.0:
                        time.sleep(min(duration_to_next_event, 0.05))
                    else:
                        play = True
                    self._playback_time = input_time
                    status = {
                        "current_time": global_time + input_time,
                        "total_time": midifile_length,
                    }
                    self._update_cbs(status)

                    if self._stop.is_set() or self._timer_reset.is_set() or self._pause.is_set():
                        run = False

                if play:
                    self._handle_msg(msg)
                else:
                    paused_msg = msg if self._pause.is_set() else None

                if not run:
                    if not self._pause.is_set():
                        self._playing_notes.clear()
                    break
            else:
                #playback_time = now() - t0
                status = dict()
                self._update_cbs(status)
                time.sleep(0.05)
            self._stop_all_playing_notes()

        self._stop_all_playing_notes()

    def _update_cbs(self, status):
        if self._update_queue.qsize() < 2:
            self._update_queue.put_nowait(status)
