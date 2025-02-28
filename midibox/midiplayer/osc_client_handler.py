from ..osc.server import DispatchedOSCRequestHandler
from .midiplayer import Midiplayer, MidiplayerStatus


class MidiplayerOSCClientHandler(DispatchedOSCRequestHandler):
    mp: Midiplayer

    def setup(self) -> None:
        super().setup()

        self._mp_time: float = 0

        self.mp.update_cbs.append(self.mp_update_cb)
        self.__init_dispatcher()

    def __init_dispatcher(self) -> None:
        # Player section
        self.map("/player/play", lambda addr, x: self.play())
        self.map("/player/seek", lambda addr, x: self.seek(x))

    def mp_update_cb(self, status: MidiplayerStatus) -> None:
        time: float = 0 if status.current_time is None else status.current_time
        length: float = 1 if status.total_time is None else status.total_time
        if abs(self._mp_time - time) > 0.5:
            self._mp_time = time
            self.send_message("/player/pos", time / length)

    def seek(self, x: float) -> None:
        if self.mp._midifile is None:
            return
        self.mp.seek(x * self.mp._midifile.length)

    def play(self) -> None:
        if self.mp.is_paused():
            self.mp.play()
        else:
            self.mp.pause()
