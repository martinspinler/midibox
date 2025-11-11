from dataclasses import dataclass
from typing import Optional
import logging
import numpy as np


log_phaser = logging.getLogger("midibox.beater.phaser")

def pfl(fl):
    return "[" + ", ".join([f"{n:.3f}" for n in fl]) +"]"


def to_interval(val, inc, to, fr=0):
    cnt = 0
    if val > to:
        while val - inc >= fr:
            val -= inc
            cnt += 1
    else:
        while val < fr:
            val += inc
            cnt -= 1
    return val, cnt



@dataclass
class Prediction:
    beat_len: Optional[float] = None
    note_weight: float = 0
    #note_weight: Optional[float] = None
    beat_offset: float = 0


class TempoPredictor:
    def __init__(self, visualiser):
        self.beat_len = 0
        self.beats_abs = []
        self.events = []
        self.beat_last = None
        self.beat_len_hint = None
        self.beat_len_avg = []
        self.v = visualiser
        self.offbeats = []

        self.beat_len_predicted = 1e9
        self.current_prediction = Prediction()

        #self._current_beat_offset = 0

    def set_hint(self, tempo, time_mult=1):
        self._time_mult = time_mult
        #self._tempo_hint = tempo
        self.beat_len_hint = (60 / tempo) * time_mult

    def reset(self, time):
        notes = self.events
        self.beat_len_avg = []
        self.offbeats = []

        self.beat_len = 0
        self.beat_last = time
        self.beats_abs = []

        self.beat_last = notes[0]

        self.v.resets.append(time)
        log_phaser.info("Reset")
        print(">>Reset<<")

    def prepare_first_beat(self):
        notes = self.events
        beat_len = notes[1] - notes[0]
        self.beat_len = beat_len
        if self.beat_len_hint is not None:
            diff = abs(beat_len - self.beat_len_hint)
            #print("Hint diff:", self.beat_len_hint, self.beat_len_hint * 0.45, diff)
            if True or self.beat_len_hint * 0.45 < diff:
                self.beat_len = self.beat_len_hint

        self.beat_last = notes[0]
        self.beats_abs = [notes[0], notes[1]]
        self.beats_abs = [notes[0]]
        return beat_len

    def on_note_event(self, time, note):
        current = time

        if len(self.events):
            abs_diff = current - self.events[-1]
            #print("<><> AD: ", abs_diff, abs_diff / time_mult, current, self.beat_last)
            if abs_diff / self._time_mult > 7:  # 7 seconds (real seconds)
                self.events.clear()

        self.check_beat(time)
        self.events.append(time)
        self.v.notes.append([time, note.note])

        if len(self.events) == 1:
            self.reset(time)
            self.beat(0) #self.beat_len)
        elif len(self.events) == 2:
            self.prepare_first_beat()
            self.beat(self.beat_len)

        if True or len(self.events) > 2:
            self.offbeats.append(current)

        #prediction = self.predict()
        prediction, poff = Prediction(), 0

        #for off in [0, 1/3, 2/3, 1/2, 1/4]: # 0 is implicit (from previous line)
        #for off in [0, 1/2]: # 0 is implicit (from previous line)
        for off in [0]: # 0 is implicit (from previous line)
            p = self.predict(off, verbose=(2 if off == 0 else 1))
            print(f"P off {off:0.2f} {p.note_weight} >>>>>>>>>>>>>>")

            # TODO: Do not switch offset if notes from past N beats stays
            if p.note_weight * 0.8 > prediction.note_weight:
                prediction, poff = p, off

        #p = self.predict(poff)
        prediction.beat_offset = poff
        self.current_prediction = prediction

        if prediction.beat_len is not None:
            self.beat_len_predicted = prediction.beat_len

    def predict(self, ev_rel_offset=0, verbose=1):
        if self.beat_len == 0:
            return Prediction()

        # TODO: process current note immediately!
        # The beats / event here are in relative values
        beats = [(n - m) for n, m in zip(self.beats_abs[1:], self.beats_abs[:-1])]
        beats_weight = [max(1 / (len(beats)) * (n+2), 0.1) for n in range(len(beats))]

        notes = []
        notes_weight = []
        notes_weight_pow = []
        offbeats = []
        #for sep_offset in [0, 1/3, 2/3]:
          
        for ind, e in enumerate(reversed(self.offbeats)):
            best, off = None, None
            for sep_offset in [0, 1/2]:
                beat_exp = self.beat_last + (self.beat_len * (ev_rel_offset + sep_offset))
                ret = self.note_probe(e, beat_exp, self.beat_len, sep_offset, verbose=verbose)
                use, timestamp, probability, weight, weight_pow = ret

                if best is None or best[2] < probability:
                    best, off = ret, sep_offset
            if best is not None:
                use, timestamp, probability, weight, weight_pow = best
                if probability < 0.55:
                    #self.v.offbeat.append(e)
                    pass
                else:
                    if True or verbose > 1:
                        print(f"Best {e:0.3f}: {timestamp:0.3f} for {off} / {probability:0.2f}")
                    notes.append(timestamp)
                    notes_weight.append(weight)
                    notes_weight_pow.append(weight_pow)

        #notes_weight = [1] * len(notes)
        #notes = [n for i, n in enumerate(notes) if notes_weight[i] > 0.8]
        #notes_weight = [n for n in notes_weight if n > 0.8]

        events, events_weight = ((beats + notes), (beats_weight + notes_weight))
        if len(events) < 1:
            return Prediction()

        bl = float(np.average(events, weights=events_weight))

        if verbose:
            if len(notes_weight):
                ep = float(np.average(notes, weights=notes_weight))
                print(f"NPRED: {ep:.3f} | {pfl(notes):35s} {pfl(notes_weight):35s} | {pfl(notes_weight_pow)}")

            bp = float(np.average(beats, weights=beats_weight))
            print(f"BPRED: {bp:.3f} | {pfl(beats[-3:]):35s} {pfl(beats_weight[-3:]):35s}")

            print(f"TPRED: {bl:.3f} offset: {ev_rel_offset: .2f}")
            #print(f"TPRED: {bl:.3f} | NTP: {sum(notes_weight) / len(notes_weight)} | {pfl(beats[-3:]):35s} {pfl(beats_weight[-3:]):35s} {pfl(notes):35s} {pfl(notes_weight):35s}")

        return Prediction(bl, sum(notes_weight_pow))

    def note_probe(self, e, beat_exp, beat_len, sep_offset_temp, verbose=0):
        # Max divergence to be a beat
        MAX_DIV = 0.20
        # ed:   event difference
        # edi:  event difference in interval (0, beat_len)
        # edn:  event difference normalized (percentual value to beat)
        # edni: event difference normalized in interval (0, 1), 1 means one beat ago
        #ed = beat_exp - e
        ed = e - beat_exp
        #ed = e - self.beat_last
        edi, cnt = to_interval(ed, beat_len, beat_len, 0)
        edn = ed / beat_len
        edni, cnt = to_interval(edn, 1, 1, 0)
        acnt = -cnt if cnt < 0 else 1

        # HERE sort to 1/3, 2/3, 1/2 ....
        probability = 0
        weight = 0
        weight_pow = 0
        timestamp = None
        state = "X"
        if False and cnt > 2:
            ##self.v.offbeat.append(e)
            state = "xxx"
        elif edni < 0.5:
            timestamp = edi + 1
            probability = 1 - edni * 2
            weight = probability / (acnt*1)
            weight_pow = probability * probability / (acnt * acnt)
            state = f"< {edi + 1:.3f} | {1/acnt:.3f} = {probability:0.2f}, {weight:.2f}, {weight_pow:.2f}"
        elif edni > 0.5:
            timestamp = edi + 0
            probability = edni * 2 - 1
            weight = probability / (acnt*1)
            weight_pow = probability * probability / (acnt * acnt)
            state = f"> {edi + 0:.3f} | {1/acnt:.3f} = {probability:0.2f}, {weight:.2f}, {weight_pow:.2f}"
        if verbose > 1:
            print(f"{e:0.3f} {sep_offset_temp:0.1f} | {ed: 5.3f} {edi: 5.3f} {edn: 5.3f} {edni: 5.3f} | {cnt} {acnt} {state}")

        use = probability != 0
        return use, timestamp, probability, weight, weight_pow

    def check_beat(self, current):
        if self.beat_last is None:
            return
        while self.beat_last + self.beat_len_predicted < current:
            #self.offbeats.clear()

            # Trigger offset
            if self.current_prediction.beat_offset:
                log_phaser.info("!!!", time=current)
                print("!!!!!!!!!!!!!!!!!!!!!")
                self.v.resets.append(self.beat_last)
                abs_offset = self.beat_len_predicted * (1 - self.current_prediction.beat_offset)
                self.beats_abs = [n - abs_offset for n in self.beats_abs]
                self.beat_last -= abs_offset
                self.current_prediction.beat_offset = 0

            self.beat(self.beat_len_predicted)
            #self.predict(verbose=False)
            self.predict()#self.current_prediction.beat_offset)

    def beat(self, beat_len):
        self.beat_len = beat_len
        self.beat_last += beat_len

        #if offset:

        self.beats_abs.append(self.beat_last)
        if len(self.beats_abs) > 6:
            self.beats_abs.pop(0)

        beats_rel = [(n - m) for n, m in zip(self.beats_abs[1:], self.beats_abs[:-1])]

        bpm_mult = 60 * self._time_mult
        bpm = bpm_mult / self.beat_len if self.beat_len != 0 else 0
        #print("Add beat", bpm_mult / self.beat_len, self.beat_len, "[", *[float(x) for x in self.beats_abs],"]",)
        print("+" * 10 + f" {len(self.v.beats): 4d} BEAT {self.beat_last:.3f} | {bpm: 6.1f} | {self.beat_len:.3f}", pfl(beats_rel))
        self.v.beats.append(self.beat_last)
        self.v.beats_len.append(self.beat_len)
        self.v.beats_err.append([self.beat_len*0.1, self.beat_len*0.1])
