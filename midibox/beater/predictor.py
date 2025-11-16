from dataclasses import dataclass, field
from typing import Optional, Any
import math
import logging
import numpy as np


log_phaser = logging.getLogger("midibox.beater.phaser")


def pfl(fl):
    return "[" + ", ".join([f"{n:.3f}" for n in fl]) +"]"


def to_interval(val: float, inc: float, to: float, fr: float = 0):
    if fr <= val <= to:
        return val, 0

    if val > to:
        steps = int((val - fr) // inc)
        new_val = val - steps * inc
        steps = -steps
    else:
        steps = math.ceil((fr - val) / inc)
    new_val = val + steps * inc

    return new_val, -steps


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
class PredictionContext:
    beat_last: Optional[float]
    beats_abs: list[float] = field(default_factory=lambda: [])
    beat_len: float = 0
    events: list[Event] = field(default_factory=lambda: [])


@dataclass
class Prediction:
    ctx: PredictionContext = field(default_factory=lambda: PredictionContext(None))
    beat_len: float = 0
    note_weight: float = 0
    #note_weight: Optional[float] = None
    beat_phase: float = 0
    dbg_predicted_notes: list[NoteOffsetPrediction] = field(default_factory=lambda: [])
    dbg_beats_with_weight: Any = None

    dbg_all_phases: list["Prediction"] = field(default_factory=lambda: [])


@dataclass
class PredictionConfiguration:
    nws_coef: float = 0.8
    bw_coef: float = 5/3


class TempoPredictor:
    def __init__(self, visualiser, debug=False, debug_beats=[], verbosity=0):
        self.beat_len_hint = None
        self.v = visualiser

        self.current_prediction = Prediction()

        self._dbg_last_showed_event = 0
        self._last_phase_change = 1e9
        self._debug = debug
        self._verbosity = verbosity
        self._debug_beats = debug_beats

        self.conf = PredictionConfiguration()
        self.ctx = PredictionContext(None)

    def set_hint(self, tempo, time_mult=1):
        self._time_mult = time_mult
        self.beat_len_hint = (60 / tempo) * time_mult

    def reset(self, time):
        notes = self.ctx.events

        self.ctx = PredictionContext(2e9)
        ctx = self.ctx

        ctx.events = [notes[0]]
        ctx.beat_len = 0
        ctx.beat_last = time
        ctx.beats_abs = []

        ctx.beat_last = notes[0]

        self.v.resets.append(time)

        print(">>> Reset")

    def prepare_first_beat(self):
        ctx = self.ctx
        notes = ctx.events
        beat_len = notes[0] - notes[1]
        ctx.beat_len = beat_len
        if self.beat_len_hint is not None:
            diff = abs(beat_len - self.beat_len_hint)
            if True or self.beat_len_hint * 0.45 < diff:
                ctx.beat_len = self.beat_len_hint
            print("Hint diff:", self.beat_len_hint, self.beat_len_hint * 0.45, diff, "|", ctx.beat_len)

        ctx.beat_last = notes[0]
        ctx.beats_abs = [notes[0]]

    def on_note_event(self, time, msg_id, msg, msg_text):
        event = time
        note = msg.note
        ctx = self.ctx

        if len(ctx.events):
            abs_diff = event - ctx.events[0]
            if abs_diff / self._time_mult > 7:  # 7 seconds (real seconds)
                ctx.events.clear()

        self.check_beat(time)
        ctx.events.insert(0, time)
        self.v.notes.append([time, note])

        if self._debug:
            print("=" * 10, f"{msg_id: 4d} {msg_text}", f"{time:.3f}")

        if len(ctx.events) == 1:
            self.reset(time)
            return
        elif len(ctx.events) == 2:
            self.prepare_first_beat()
            self.ctx = self.beat(Prediction(ctx, ctx.beat_len))

        cp = self.predict(self.ctx)
        self.current_prediction = cp

    def predict_note(self, e, beat_exp, beat_len, beat_phase):
        # ed:   event difference
        # edi:  event difference in interval (0, beat_len)
        # edn:  event difference normalized (percentual value to beat)
        # edni: event difference normalized in interval (0, 1), 1 means one beat ago
        ed = e - beat_exp
        edi, cnt = to_interval(ed, beat_len, beat_len, 0)
        edn = ed / beat_len
        edni, cnt = to_interval(edn, 1, 1, 0)
        acnt = -cnt if cnt < 0 else 1

        # HERE sort to 1/3, 2/3, 1/2 ....
        if edni <= 0.5:
            timestamp = edi + 1
            probability = 1 - edni * 2
            st = "<"
        else:
            timestamp = edi + 0
            probability = edni * 2 - 1
            st = ">"

        weight = probability / (acnt * 3.5)
        weight_pow = probability * probability / (acnt * acnt)

        p = NotePrediction(e, timestamp, probability, weight, weight_pow, acnt)
        if self._debug:
            state = f"{st} {timestamp:.3f} | {1/acnt:.3f} = {probability:.3f}, {weight:.3f}, {weight_pow:.3f}"
            p.dbg_state = (f"{e:.3f} {beat_phase:.2f} | {ed: 5.3f} {edi: 5.3f} {edn: 5.3f} {edni: 5.3f} | {beat_len:.3f} | {cnt: 3d} {acnt} {state}")
        return p
        
    def predict_notes(self, ctx, beat_phase):
        all_best = []
        probed_notes = ctx.events
        unused_index = None
        for index, e in enumerate(probed_notes):
            best = None
            all_local = []
            for local_beat_phase in [0, 1/3, 2/3, 1/2]:
            #for local_beat_phase in [0, 1/2]:
                beat_exp = ctx.beat_last + (ctx.beat_len * (beat_phase + local_beat_phase))
                n_prediction = self.predict_note(e, beat_exp, ctx.beat_len, local_beat_phase)

                if self._debug:
                    all_local.append((n_prediction, local_beat_phase))

                if best is None or best.p.probability < n_prediction.probability:
                    best = NoteOffsetPrediction(n_prediction, local_beat_phase, [])

            best.dbg_all_p = all_local

            if best.p.probability < 0.55:
                if self._debug:
                    best.dbg_state = f"Best {e:.3f}: NONE"
                pass
            else:
                if self._debug:
                    best.dbg_state = f"Best {e:.3f}: {best.p.rel_time:.3f} for {best.beat_phase:.2f} / {best.p.probability:.2f}"
                all_best.append(best)

            if best.p.rel_beat > 32:
                unused_index = index
                break

        return all_best, unused_index

    def predict(self, ctx):
        # The beats / event here are in relative values
        beats = [(n - m) for n, m in zip(ctx.beats_abs[1:], ctx.beats_abs[:-1])]
        beats_weight = [max(1 / (len(beats) * (self.conf.bw_coef *(n+1))), 0.1) for n in range(len(beats))]

        best = None
        #for off in [0, 1/3, 2/3, 1/2, 1/4]: # 0 is implicit (from previous line)
        #for off in [0, 1/2]: # 0 is implicit (from previous line)
        #for beat_phase in [0]: # 0 is implicit (from previous line)
        all_phases = []
        for beat_phase in [0, 1/3, 2/3, 1/2, 1/4]:
            predicted_notes, unused_index = self.predict_notes(ctx, beat_phase)
            if unused_index is not None:
                # TODO
                del ctx.events[unused_index:]

            predicted_notes_sel = [(i.p.rel_time, i.p.weight, i.p.weight_pow) for i in predicted_notes]
            notes, notes_weight, notes_weight_pow = [list(i) for i in zip(*predicted_notes_sel)] if len(predicted_notes_sel) else ([], [], [])

            events, events_weight = ((beats + notes), (beats_weight + notes_weight))
            if len(events) < 1:
                return Prediction(ctx)

            bl = float(np.average(events, weights=events_weight))
            #notes_weight_pow_sum = sum(notes_weight_pow)
            notes_weight_sum = sum(notes_weight)

            p = Prediction(ctx, bl, notes_weight_sum, beat_phase)
            if self._debug:
                p.dbg_predicted_notes = predicted_notes
            all_phases.append(p)

            if best is None or notes_weight_sum * self.conf.nws_coef > best[2]:
                best = p, predicted_notes, notes_weight_sum, beat_phase

        prediction = best[0]
        if self._debug:
            prediction.dbg_beats_with_weight = beats, beats_weight
            prediction.dbg_all_phases = all_phases
        return prediction

    def pdebug(self, prediction=None, beat_next=None, beat_len=None, beat_phase_dbg=None):
        ctx = self.ctx
        if prediction is None:
            prediction = self.current_prediction
        if beat_len is None:
            beat_len = prediction.beat_len
        if beat_next is None:
            beat_next = ctx.beat_last + beat_len
        if beat_phase_dbg is None:
            beat_phase_dbg = ""

        verbose = self._verbosity

        beats_rel = [(n - m) for n, m in zip(ctx.beats_abs[1:], ctx.beats_abs[:-1])]
        bpm_mult = 60 * self._time_mult
        bpm = bpm_mult / beat_len if beat_len != 0 else 0

        p = prediction
        if p and self._debug and p.dbg_beats_with_weight:
            if verbose > 1:
                MAX_N = 8
                predicted_notes_sel = [(i.p.rel_time, i.p.weight, i.p.weight_pow) for i in p.dbg_predicted_notes]
                notes, notes_weight, notes_weight_pow = [list(i) for i in zip(*predicted_notes_sel)] if predicted_notes_sel else ([], [], [])

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

            for nop in p.dbg_predicted_notes:
                if nop.p.event > self._dbg_last_showed_event:
                    self.v.predictions.append([nop.p.event, nop.beat_phase, nop.p.probability])
                    self._dbg_last_showed_event = nop.p.event
        if beat_phase_dbg:
            print(beat_phase_dbg)

        if verbose:
            print("+" * 10 + f" {len(self.v.beats): 4d} BEAT {beat_next:.3f} | {bpm: 6.1f} | {beat_len:.3f}", pfl(beats_rel))

        #if verbose:
        #    print(f"Phase {prediction.beat_phase:2f} >>>>>>>>>>>>>>")

    def beat(self, prediction):
        if len(self.v.beats) in self._debug_beats:
            breakpoint()

        ctx = prediction.ctx
        # Trigger offset
        beat_len = prediction.beat_len
        beat_phase_dbg = ""
        if prediction.beat_phase and self._last_phase_change > 8:
            self._last_phase_change = 0
            self.v.resets.append(ctx.beat_last)

            bp = self.current_prediction.beat_phase
            bpc = bp + 1 if bp < 0.5 else bp + 0
            abs_offset = beat_len * (bpc)
            beat_phase_dbg = f">>> Phase shitf {bp:.2f} {bpc:.2f} {abs_offset:.2f}"
            ctx.beats_abs = [n + abs_offset for n in ctx.beats_abs]
            ctx.beat_last += abs_offset
            #self.current_prediction.beat_phase = 0
        self._last_phase_change += 1

        beat_next = ctx.beat_last + beat_len

        self.pdebug(prediction, beat_next, beat_len, beat_phase_dbg)

        ctx.beat_len = beat_len
        ctx.beat_last = beat_next

        ctx.beats_abs.append(ctx.beat_last)
        if len(ctx.beats_abs) > 6:
            ctx.beats_abs.pop(0)

        self.v.beats.append(ctx.beat_last)
        self.v.beats_len.append(ctx.beat_len)
        self.v.beats_err.append([ctx.beat_len*0.1, ctx.beat_len*0.1])

        return ctx

    def check_beat(self, current_time):
        cp = self.current_prediction
        ctx = self.ctx
        if ctx.beat_last is None or cp.beat_len == 0:
            return
        while ctx.beat_last + cp.beat_len < current_time:
            self.ctx = self.beat(cp)
            ctx = self.ctx

            # If no event will arise, recompute prediction anyway
            self.current_prediction = self.predict(ctx)
