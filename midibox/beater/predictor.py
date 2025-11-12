from dataclasses import dataclass, field
from typing import Optional, Any
import logging
import numpy as np


DEBUG = True
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


Event = type[float]
BeatPhase = type[float]


@dataclass
class NotePrediction:
    event: Event
    rel_time: float
    probability: float
    weight: float
    weight_pow: float
    rel_beat: float
    weight_pow_sum: float = 0

    dbg_state: str = ""


@dataclass
class NoteOffsetPrediction:
    p: NotePrediction
    beat_phase: BeatPhase

    dbg_all_p: list[(NotePrediction, BeatPhase)]
    dbg_state: str = ""


@dataclass
class Prediction:
    beat_len: Optional[float] = None
    note_weight: float = 0
    #note_weight: Optional[float] = None
    beat_phase: float = 0
    dbg_predicted_notes: list[NoteOffsetPrediction] = field(default_factory=lambda: [])
    dbg_beats_with_weight: Any = None

    dbg_all_phases: list["Prediction"] = field(default_factory=lambda: [])


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
        self.events_in_process = []

        self.beat_len_predicted = 1e9
        self.current_prediction = Prediction()

        self._dbg_last_showed_event = 0
        self._last_phase_change = 1e9
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
        log_phaser.info(">>> Reset")

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

    def on_note_event(self, time, msg_id, msg, msg_text):
        current = time
        note = msg.note

        if len(self.events):
            abs_diff = current - self.events[-1]
            if abs_diff / self._time_mult > 7:  # 7 seconds (real seconds)
                self.events.clear()

        self.check_beat(time)
        self.events.append(time)
        self.v.notes.append([time, note])

        if len(self.events) == 1:
            self.reset(time)
            self.beat(0) #self.beat_len)
        elif len(self.events) == 2:
            self.prepare_first_beat()
            self.beat(self.beat_len)

        if DEBUG:
            print("=" * 10, f"{msg_id: 4d} {msg_text}", f"{time:.3f}")

        if True or len(self.events) > 2:
            self.offbeats.insert(0, current)
        self.events_in_process.append(current)

        self.current_prediction = self.predict()

        if self.current_prediction.beat_len is not None:
            self.beat_len_predicted = self.current_prediction.beat_len

    def predict_note(self, e, beat_exp, beat_len, beat_phase):
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

        if edni <= 0.5:
            timestamp = edi + 1
            probability = 1 - edni * 2
            st = "<"
        else:
            timestamp = edi + 0
            probability = edni * 2 - 1
            st = ">"

        weight = probability / (acnt*3.5)
        weight_pow = probability * probability / (acnt * acnt)
        state = f"{st} {timestamp:.3f} | {1/acnt:.3f} = {probability:.3f}, {weight:.3f}, {weight_pow:.3f}"

        p = NotePrediction(e, timestamp, probability, weight, weight_pow, acnt)
        if DEBUG:
            p.dbg_state = (f"{e:.3f} {beat_phase:.2f} | {ed: 5.3f} {edi: 5.3f} {edn: 5.3f} {edni: 5.3f} | {cnt: 3d} {acnt} {state}")
        return p
        
    def predict_notes(self, probed_notes, beat_phase):
        all_best = []
        for e in probed_notes:
            best = None
            all_local = []
            for local_beat_phase in [0, 1/3, 2/3, 1/2]:
            #for local_beat_phase in [0, 1/2]:
                beat_exp = self.beat_last + (self.beat_len * (beat_phase + local_beat_phase))
                n_prediction = self.predict_note(e, beat_exp, self.beat_len, local_beat_phase)
                all_local.append((n_prediction, local_beat_phase))

                if best is None or best.p.probability < n_prediction.probability:
                    best = NoteOffsetPrediction(n_prediction, local_beat_phase, [])

            if DEBUG:
                best.dbg_all_p = all_local

            if best.p.probability < 0.55:
                if DEBUG:
                    best.dbg_state = f"Best {e:.3f}: NONE"
                pass
            else:
                if DEBUG:
                    best.dbg_state = f"Best {e:.3f}: {best.p.rel_time:.3f} for {best.beat_phase:.2f} / {best.p.probability:.2f}"
                all_best.append(best)

            if best.p.rel_beat > 32:
                break
        return all_best

    def predict(self):
        if self.beat_len == 0 or len(self.beats_abs) < 2:
            return Prediction()

        # The beats / event here are in relative values
        beats = [(n - m) for n, m in zip(self.beats_abs[1:], self.beats_abs[:-1])]
        beats_weight = [max(1 / (len(beats) * (5/3 *(n+1))), 0.1) for n in range(len(beats))]

        best = None
        #for off in [0, 1/3, 2/3, 1/2, 1/4]: # 0 is implicit (from previous line)
        #for off in [0, 1/2]: # 0 is implicit (from previous line)
        #for beat_phase in [0]: # 0 is implicit (from previous line)
        all_phases = []
        for beat_phase in [0, 1/3, 2/3, 1/2, 1/4]:
            predicted_notes = self.predict_notes(self.offbeats, beat_phase)

            predicted_notes_sel = [(i.p.rel_time, i.p.weight, i.p.weight_pow) for i in predicted_notes]
            notes, notes_weight, notes_weight_pow = [list(i) for i in zip(*predicted_notes_sel)]

            events, events_weight = ((beats + notes), (beats_weight + notes_weight))
            if len(events) < 1:
                return Prediction()

            bl = float(np.average(events, weights=events_weight))
            #notes_weight_pow_sum = sum(notes_weight_pow)
            notes_weight_sum = sum(notes_weight)

            p = Prediction(bl, notes_weight_sum, beat_phase)
            if DEBUG:
                p.dbg_predicted_notes = predicted_notes
            all_phases.append(p)

            if best is None or notes_weight_sum * 0.8 > best[2]:
                best = p, predicted_notes, notes_weight_sum, beat_phase

        prediction = best[0]
        if DEBUG:
            prediction.dbg_beats_with_weight = beats, beats_weight
            prediction.dbg_all_phases = all_phases
            #prediction.dbg_all_phases = all_phases
        return prediction

    def beat_apply_prediction(self, prediction, beat_next, beat_len, beat_phase_dbg):
        verbose = 0

        beats_rel = [(n - m) for n, m in zip(self.beats_abs[1:], self.beats_abs[:-1])]
        bpm_mult = 60 * self._time_mult
        bpm = bpm_mult / beat_len if beat_len != 0 else 0

        p = prediction
        if p and DEBUG:
            if verbose:
                MAX_N = 8
                predicted_notes_sel = [(i.p.rel_time, i.p.weight, i.p.weight_pow) for i in p.dbg_predicted_notes]
                notes, notes_weight, notes_weight_pow = [list(i) for i in zip(*predicted_notes_sel)]

                for pn in p.dbg_predicted_notes:
                    for notep, np_bp in pn.dbg_all_p:
                        pfx = (" " * 13 + " > ") if notep == pn.p else " " * 16 
                        print(pfx + notep.dbg_state)
                    print(" " * 12 + pn.dbg_state)

                beats, beats_weight = p.dbg_beats_with_weight

                #if len(notes_weight):
                #    ep = float(np.average(notes, weights=notes_weight))
                #    print(f"NPRED: {ep:.3f} | {pfl(notes[:MAX_N]):35s} {pfl(notes_weight[:MAX_N]):35s} | {pfl(notes_weight_pow[:MAX_N])}")

                #bp = float(np.average(beats, weights=beats_weight))
                #print(f"BPRED: {bp:.3f} | {pfl(beats[-3:]):35s} {pfl(beats_weight[-3:]):35s}")

                for ph in p.dbg_all_phases:
                    predicted_notes_sel = [(i.p.rel_time, i.p.weight, i.p.weight_pow) for i in ph.dbg_predicted_notes]
                    notes, notes_weight, notes_weight_pow = [list(i) for i in zip(*predicted_notes_sel)]

                    pfx = (" " * 5 + " > ") if ph == p else " " * 8
                    if len(notes_weight):
                        ep = float(np.average(notes, weights=notes_weight))
                        print(pfx + f"ALT NPRED: {ep:.3f}, {ph.beat_phase: .2f} | {sum(notes_weight):.3f} {sum(notes_weight_pow):.3f} | {pfl(notes[:MAX_N]):35s} {pfl(notes_weight[:MAX_N]):35s} | {pfl(notes_weight_pow[:MAX_N])}")

                for ph in p.dbg_all_phases:
                    pfx = (" " * 5 + " > ") if ph == p else " " * 8
                    print(pfx + f"ALT BPRED: {ph.beat_len:.3f}, {ph.beat_phase: .2f} | {ph.note_weight:.3f}")
                #print(f"TPRED: {p.beat_len:.3f} phase: {p.beat_phase: .2f}")
                #print(f"TPRED: {pl.beat_len:.3f} | NTP: {sum(notes_weight) / len(notes_weight)} | {pfl(beats[-3:]):35s} {pfl(beats_weight[-3:]):35s} {pfl(notes):35s} {pfl(notes_weight):35s}")
                print(f"TPRED: {p.beat_len:.3f} | NTP: {sum(notes_weight) / len(notes_weight)} | {pfl(beats[-3:]):35s} {pfl(beats_weight[-3:]):35s}")

            for nop in reversed(p.dbg_predicted_notes):
                if nop.p.event > self._dbg_last_showed_event:
                    #nop.p.event
                    self.v.predictions.append([nop.p.event, nop.beat_phase, nop.p.probability])
                    self._dbg_last_showed_event = nop.p.event
        if beat_phase_dbg:
            print(beat_phase_dbg)

        if verbose:
            print("+" * 10 + f" {len(self.v.beats): 4d} BEAT {beat_next:.3f} | {bpm: 6.1f} | {beat_len:.3f}", pfl(beats_rel))

        #if verbose:
        #    print(f"Phase {prediction.beat_phase:2f} >>>>>>>>>>>>>>")

    def beat(self, beat_len, prediction=None):
        # Trigger offset
        beat_phase_dbg = ""
        if self.current_prediction.beat_phase and self._last_phase_change > 8:
            self._last_phase_change = 0
            self.v.resets.append(self.beat_last)

            bp = self.current_prediction.beat_phase
            bpc = bp + 1 if bp < 0.5 else bp + 0
            abs_offset = self.beat_len_predicted * (bpc)
            beat_phase_dbg = f">>> Phase shitf {bp:.2f} {bpc:.2f} {abs_offset:.2f}"
            self.beats_abs = [n + abs_offset for n in self.beats_abs]
            self.beat_last += abs_offset
            #self.current_prediction.beat_phase = 0
        self._last_phase_change += 1

        beat_next = self.beat_last + beat_len

        self.beat_apply_prediction(prediction, beat_next, beat_len, beat_phase_dbg)

        self.beat_len = beat_len
        self.beat_last = beat_next

        self.beats_abs.append(self.beat_last)
        if len(self.beats_abs) > 6:
            self.beats_abs.pop(0)

        self.v.beats.append(self.beat_last)
        self.v.beats_len.append(self.beat_len)
        self.v.beats_err.append([self.beat_len*0.1, self.beat_len*0.1])

    def check_beat(self, current):
        if self.beat_last is None:
            return
        while self.beat_last + self.beat_len_predicted < current:
            #self.offbeats.clear()

            self.beat(self.beat_len_predicted, self.current_prediction)

            # If no event will arise, recompute prediction anyway
            self.current_prediction = self.predict()
