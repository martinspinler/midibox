import numpy as np
import matplotlib.pyplot as plt

from matplotlib.markers import MarkerStyle
from matplotlib.transforms import Affine2D

from .predictor import TempoListener


def pfl(fl):
    return "[" + ", ".join([f"{n:.3f}" for n in fl]) +"]"


class Visualiser(TempoListener):
    def __init__(self, debug=False, debug_beats=[], verbosity=0):
        self._debug = debug
        self._verbosity = verbosity
        self._debug_beats = debug_beats

        self.notes = []
        self.beats = []
        self.beats_err = []
        self.beats_len = []
        self.resets = []
        self.offbeat = []
        self.predictions = []
        self.nearest_pred = []

        self._time_mult = 1

    def on_reset(self, time):
        if self._debug:
            print(">>> Reset")
        self.resets.append(time)

    def on_note_event(self, time, msg_id, msg, msg_text):
        self.notes.append([time, msg.note])
        if self._debug:
            print("=" * 10, f"{msg_id: 4d} {msg_text}", f"{time:.3f}")

    def on_beat(self, beat_last, beat_len):
        self.beats.append(beat_last)
        self.beats_len.append(beat_len)
        self.beats_err.append([beat_len*0.1, beat_len*0.1])

    def on_tempo_hint(self, tempo_hint, time_mult):
        self._time_mult = time_mult

    def on_apply_prediction(self, prediction=None, beat_phase_dbg=None):
        ctx = prediction.ctx
        beat_len = prediction.beat_len
        beat_next = prediction.beat_next()
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
                #print(f"TPRED: {pl.beat_len:.3f} | NTP: {sum(notes_weight) / len(notes_weight):.3f} | {pfl(beats[-3:]):35s} {pfl(beats_weight[-3:]):35s} {pfl(notes):35s} {pfl(notes_weight):35s}")
                print(f"TPRED: {p.beat_len:.3f} | NTP: {sum(notes_weight) / len(notes_weight):.3f} | {pfl(beats[-3:]):35s} {pfl(beats_weight[-3:]):35s}")

            for nop in p.dbg_predicted_notes:
                if nop.p.rel_beat == 1:
                    self.nearest_pred.append(nop)
                        #[nop.p.event, nop.beat_phase, nop.p.probability, nop.p.rel_time, p])

        self.predictions.append(prediction)

        if beat_phase_dbg:
            print(beat_phase_dbg)

        if verbose:
            print("+" * 10 + f" {ctx.beat_last_id: 4d} BEAT {beat_next:.3f} | {bpm: 6.1f} | {beat_len:.3f}", pfl(beats_rel))

        #if verbose:
        #    print(f"Phase {prediction.beat_phase:2f} >>>>>>>>>>>>>>")


class MPVisualiser(Visualiser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fig, self.ax = fig, ax = plt.subplots(figsize=(20, 5))
        fig.canvas.mpl_connect('pick_event', self.on_pick)
        fig.canvas.mpl_connect('key_press_event', self.on_press)

    def on_press(self, event):
        fig, ax = self.fig, self.ax
        if event.key == 'left':
            print('press', event.key)
            fig.canvas.draw()

    def on_pick(self, event):
        #o =event.artist
        #print(event.ind, len(self.predictions))
        p = self.predictions[event.ind[0]]
        self.on_apply_prediction(p)
        pass

    def draw(self, x1 = None, x2 = None):
        fig, ax = self.fig, self.ax

        npred = self.nearest_pred
        n = self.notes
        b = self.beats
        if len(self.notes) == 0:
            return
        n, npitch = np.array(self.notes).T
        npitch = [1 + 0.3*(n-33)/(55-33) for n in npitch]
        #ax.scatter(self.notes, [1]*len(self.notes), s=sizes, c=colors, vmin=0, vmax=100)
        ax.scatter([], [], marker="|")
        ax.scatter(b, [0.96]*len(b), marker="o", picker=True)
        ax.scatter([n], [npitch], marker="x", linewidth=0.75)
        ax.scatter([n], [1]*len(n), marker="|")
        ax.scatter([self.offbeat], [1]*len(self.offbeat), marker="1")

        for phase in [0, 1/3, 2/3, 1/2, 1/4]:
            ph = 'full' if phase == 0 else 'left'
            t = Affine2D().rotate_deg(phase* 360)
            ps = [nop.p.event for nop in npred if nop.beat_phase]

            ms = MarkerStyle('o', ph, t)
            ax.scatter([ps], [1]*len(ps), marker=ms, linewidth=0.75)
            ms = MarkerStyle('o', 'none', t)
            ax.scatter([ps], [1]*len(ps), marker=ms, linewidth=0.75)

        MarkerStyle('o', 'left', t)

        ax.stairs(self.beats_len, edges=[0] + b)

        ax.eventplot([b], linewidth=0.75)

        xerrs = [((0, nop.p.err_diff) if nop.p.err_diff > 0 else (-nop.p.err_diff, 0)) for nop in npred]
        yerrs = [(0, 1.01-nop.p.probability) for nop in npred]
        ax.errorbar([nop.p.event for nop in npred], [0.95]*len(npred), xerr=np.array(xerrs).T, yerr=np.array(yerrs).T, linewidth=0.75, linestyle='none')

        ax.plot(self.resets, [0.92]*len(self.resets), 'v')

        if x1 is None:
            x1 = n[0]
        if x2 is None:
            x2 = n[-1]
        plt.xlim(x1, x2)
        plt.ylim(0.9, 1.5)

        plt.show()
