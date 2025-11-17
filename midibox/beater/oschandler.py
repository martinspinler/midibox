import dataclasses

from ..osc.server import DispatchedOSCRequestHandler
from .predictor import TempoPredictor, TempoListener, PredictionContext


class TempoPredictorOSCClientHandler(TempoListener, DispatchedOSCRequestHandler):
    tp: TempoPredictor

    def setup(self) -> None:
        super().setup()
        self.tp.listeners.append(self)

    def on_beat(self, beat_last, beat_length):
        self.send_message("/beater/beat", beat_last, beat_length)
