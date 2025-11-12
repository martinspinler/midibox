import numpy as np
import matplotlib.pyplot as plt

from matplotlib.markers import MarkerStyle
from matplotlib.transforms import Affine2D


class Visualiser:
    def __init__(self):
        self.notes = []
        self.beats = []
        self.beats_err = []
        self.beats_len = []
        self.resets = []
        self.offbeat = []
        self.predictions = []


class MPVisualiser(Visualiser):
    def draw(self, x1, x2):
        fig, ax = plt.subplots(figsize=(20, 5))
        n = self.notes
        b = self.beats
        if len(self.notes) == 0:
            return
        n, npitch = np.array(self.notes).T
        npitch = [1 + 0.3*(n-33)/(55-33) for n in npitch]
        #ax.scatter(self.notes, [1]*len(self.notes), s=sizes, c=colors, vmin=0, vmax=100)
        ax.scatter([], [], marker="|")
        #ax.scatter(b, [1]*len(b), marker="|")
        ax.scatter([n], [npitch], marker="x", linewidth=0.75)
        ax.scatter([n], [1]*len(n), marker="|")
        ax.scatter([self.offbeat], [1]*len(self.offbeat), marker="1")

        for phase in [0, 1/3, 2/3, 1/2, 1/4]:
            ph = 'full' if phase == 0 else 'left'
            t = Affine2D().rotate_deg(phase* 360)
            ps = [n[0] for n in self.predictions if n[1] == phase]

            ms = MarkerStyle('o', ph, t)
            ax.scatter([ps], [1]*len(ps), marker=ms, linewidth=0.75)
            ms = MarkerStyle('o', 'none', t)
            ax.scatter([ps], [1]*len(ps), marker=ms, linewidth=0.75)

        MarkerStyle('o', 'left', t)

        ax.stairs(self.beats_len, edges=[0] + b)

        ax.eventplot([b], linewidth=0.75)

        ax.errorbar([n[0] for n in self.predictions], [0.95]*len(self.predictions), yerr=np.array([(0, 1-n[2]) for n in self.predictions]).T, linewidth=0.75, linestyle='none')

        ax.plot(self.resets, [0.92]*len(self.resets), 'v')

        plt.xlim(x1, x2)
        plt.ylim(0.9, 1.5)

        plt.show()
