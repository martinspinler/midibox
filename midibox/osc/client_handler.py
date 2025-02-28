import mido
from typing import Callable, Any

from ..controller.base import BaseMidibox, Layer, Pedal, GeneralProps, LayerProps, PedalProps, PropHandler
from .server import DispatchedOSCRequestHandler

from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_bundle_builder import OscBundleBuilder as OriginalOscBundleBuilder, IMMEDIATELY


class OscBundleBuilder(OriginalOscBundleBuilder):
    def __init__(self) -> None:
        super().__init__(IMMEDIATELY)

    def add_msg(self, address: str, value: Any) -> None:
        values = [value]
        builder = OscMessageBuilder(address=address)
        for val in values:
            builder.add_arg(val)
        self.add_content(builder.build())  # type: ignore


class ControlChangeHandlerProxy():
    def __init__(self, p: PropHandler, handler: Callable[..., None]) -> None:
        self._p = p
        self._handler = handler
        p.bind(control_change=self.on_control_change)

    def on_control_change(self, *args: Any, **kwargs: Any) -> None:
        self._handler(self._p, *args, **kwargs)


class MidiboxOSCClientHandler(DispatchedOSCRequestHandler):
    mb: BaseMidibox

    def setup(self) -> None:
        super().setup()
        self.mb._callbacks.append(self.mb_midi_callback)

        self.__init_dispatcher()
        self.__init()

    def __init_dispatcher(self) -> None:
        self.map("/init", self.__init)

        # Midibox section
        self.mb.general.bind(control_change=self.on_main_control_change)
        for mbp in GeneralProps:
            self.map("/midibox/%s" % (mbp.name), self.main_control_change, mbp.name)

        self.map("/midibox/initialize", self.initialize)
        self.map("/midibox/midi", self.on_midi)

        self._chp = []

        for lr in self.mb.layers:
            for mblp in LayerProps:
                self.map("/midibox/layers/%d/%s" % (lr._index, mblp.name), self.layer_control_change, lr, mblp.name)
            self._chp.append(ControlChangeHandlerProxy(lr, self.on_layer_control_change))
            for pedal in lr.pedals:
                for mbpp in PedalProps:
                    self.map("/midibox/layers/%d/pedal%d.%s" % (lr._index, pedal._index, mbpp.name), self.layer_pedal_control_change, pedal, mbpp.name)
                self._chp.append(ControlChangeHandlerProxy(pedal, self.on_layer_pedal_control_change))

    def __init(self, addr: str = '') -> None:
        bundle = OscBundleBuilder()

        for mbp in GeneralProps:
            bundle.add_msg("/midibox/%s" % (mbp.name), getattr(self.mb.general, mbp.name))

        for lr in self.mb.layers:
            index = lr._index
            for mblp in LayerProps:
                prop = mblp.name
                bundle.add_msg("/midibox/layers/%d/%s" % (lr._index, prop), getattr(self.mb.layers[index], prop))

            for pedal in lr.pedals:
                for mbpp in PedalProps:
                    prop = mbpp.name
                    bundle.add_msg("/midibox/layers/%d/pedal%d.%s" % (lr._index, pedal._index, prop), getattr(pedal, prop))

        self.send_msg(bundle.build())

    def finish(self) -> None:
        self.mb._callbacks.remove(self.mb_midi_callback)
        super().finish()

    def mb_midi_callback(self, msg: mido.Message) -> None:
        if msg.type == 'clock':
            return

        self.send_message("/midibox/midi", bytes(msg.bytes()))

    def on_midi(self, addr: str, param: list[int]) -> None:
        midi = list(param)
        msg = mido.Message.from_bytes(midi)
        self.mb.sendmsg(msg)

    def initialize(self, addr: str) -> None:
        self.mb.initialize()

    def on_main_control_change(self, **kwargs: Any) -> None:
        prop, value = list(kwargs.items())[0]
        self.send_message("/midibox/%s" % (prop), value)

    def on_layer_control_change(self, layer: Layer, **kwargs: Any) -> None:
        prop, value = list(kwargs.items())[0]
        self.send_message("/midibox/layers/%d/%s" % (layer._index, prop), value)

    def on_layer_pedal_control_change(self, pedal: Pedal, **kwargs: Any) -> None:
        prop, value = list(kwargs.items())[0]
        self.send_message("/midibox/layers/%d/pedal%d.%s" % (pedal._layer._index, pedal._index, prop), value)

    def main_control_change(self, addr: str, prop: str, value: Any) -> None:
        if hasattr(self.mb.general, prop):
            setattr(self.mb.general, prop, value)

    def layer_control_change(self, addr: str, layer: Layer, prop: str, value: Any) -> None:
        if hasattr(layer, prop):
            setattr(layer, prop, value)

    def layer_pedal_control_change(self, addr: str, pedal: Pedal, prop: str, value: Any) -> None:
        if hasattr(pedal, prop):
            setattr(pedal, prop, value)
