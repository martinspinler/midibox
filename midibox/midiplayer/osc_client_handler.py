import dataclasses

from ..osc.server import DispatchedOSCRequestHandler
from .midiplayer import Midiplayer, MidiplayerStatus


class MidiplayerOSCClientHandler(DispatchedOSCRequestHandler):
    mp: Midiplayer

    def setup(self) -> None:
        super().setup()

        self._mp_time: float = 0

        self.mp.update_cbs.append(self.mp_update_cb)
        self.__init_dispatcher()
        self._last_status: MidiplayerStatus | None = None
        #self._last_status = self.mp.status.copy()
        self.mp_update_cb(self.mp.status)

    def __init_dispatcher(self) -> None:
        # Player section
        self.map("/player/play", lambda addr, x: self.play())
        self.map("/player/seek", lambda addr, x: self.seek(x))
        self.map("/player/load", lambda addr, x: self.load(x))

    def mp_update_cb(self, status: MidiplayerStatus) -> None:
        if self._last_status is None or self._last_status.paused != status.paused:
            self.send_message("/player/play", not status.paused)

        time: float = 0 if status.current_time is None else status.current_time
        length: float = 1 if status.total_time is None else status.total_time

        #print("Seeking  to ", (time/length )if length > 0 else "X", time)
        if length > 0 and abs(self._mp_time - time) > 0.5 or (
                self._last_status is not None and (
                self._last_status.measure != status.measure or
                self._last_status.beat != status.beat)
            ):

            self._mp_time = time
            #self.send_message("/player/pos", time / length)
            self.send_message("/player/seek", time / length)
            self.send_message("/player/measure", status.measure, status.beat)

        self._last_status = dataclasses.replace(status)

    def load(self, x) -> None:
        self.mp.load(bytes(x))

    def seek(self, x: float) -> None:
        if self._last_status is None or self._last_status.total_time == 0:
            return

        #print("Seek to ", x, x * self._last_status.total_time)
        self.mp.seek(x * self._last_status.total_time)

    def play(self) -> None:
        self.mp.play(self.mp.is_paused())
