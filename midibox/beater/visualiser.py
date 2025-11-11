import numpy as np
import matplotlib.pyplot as plt


class Visualiser:
    def __init__(self):
        self.notes = []
        self.beats = []
        self.beats_err = []
        self.beats_len = []
        self.resets = []
        self.offbeat = []


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

        ax.stairs(self.beats_len, edges=[0] + b)

        ax.eventplot([b], linewidth=0.75)
        #ax.errorbar(b, [0.95]*len(b), xerr=np.array(self.beats_err).T, linewidth=0.75, linestyle='none')

        ax.plot(self.resets, [1]*len(self.resets), 'v')

        plt.xlim(x1, x2)
        plt.ylim(0.9, 1.5)

        plt.show()
