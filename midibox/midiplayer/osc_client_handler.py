from ..osc.server import DispatchedOSCRequestHandler


class MidiplayerOSCClientHandler(DispatchedOSCRequestHandler):
    def setup(self):
        super().setup()

        self._mp_time = 0

        self.mp.update_cbs.append(self.mp_update_cb)
        self.__init_dispatcher()

    def __init_dispatcher(self):
        # Player section
        self.map("/player/play", lambda addr, x: self.play())
        self.map("/player/seek", lambda addr, x: self.seek(x))

    def mp_update_cb(self, status):
        time = status.get("current_time", 0)
        length = status.get("total_time", 1)
        if abs(self._mp_time - time) > 0.5:
            self._mp_time = time
            self.send_message("/player/pos", time / length)

    def seek(self, x):
        self.mp.seek(x * self.mp._midifile.length)

    def play(self):
        if self.mp.is_paused():
            self.mp.play()
        else:
            self.mp.pause()
