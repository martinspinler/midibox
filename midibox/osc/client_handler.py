

from ..controller.base import MidiBoxLayerProps, MidiBoxProps, MidiBoxPedalProps
from .server import DispatchedOSCRequestHandler

class ControlChangeHandlerProxy():
    def __init__(self, p, handler):
        self._p = p
        self._handler = handler
        p.bind(control_change=self.on_control_change)

    def on_control_change(self, *args, **kwargs):
        self._handler(self._p, *args, **kwargs)


class MidiboxOSCClientHandler(DispatchedOSCRequestHandler):
    def setup(self):
        super().setup()
        self.mb._callbacks.append(self.mb_midi_callback)

        self.init_dispatcher()
        self.init()

    def init_dispatcher(self):
        self.map("/init", lambda addr: self.init())

        # Midibox section
        self.mb.bind(control_change=self.on_main_control_change)
        for item in MidiBoxProps:
            self.map("/midibox/%s" % (item.name), self.main_control_change, item.name)

        self.map("/midibox/initialize", self.initialize)
        self.map("/midibox/midi", self.on_midi)

        self.lrs = []
        self._chp = []

        for lr in self.mb.layers:
            for item in MidiBoxLayerProps:
                self.map("/midibox/layers/%d/%s" % (lr._index, item.name), self.layer_control_change, lr, item.name)
            self._chp.append(ControlChangeHandlerProxy(lr, self.on_layer_control_change))
            for pedal in lr.pedals:
                for item in MidiBoxPedalProps:
                    self.map("/midibox/layers/%d/pedal%d.%s" % (lr._index, pedal._index, item.name), self.layer_pedal_control_change, pedal, item.name)
                self._chp.append(ControlChangeHandlerProxy(pedal, self.on_layer_pedal_control_change))

    def init(self):
        for item in MidiBoxProps:
            self.send_message("/midibox/%s" % (item.name), getattr(self.mb, item.name))

        for lr in self.mb.layers:
            index = lr._index
            for item in MidiBoxLayerProps:
                prop = item.name
                self.send_message("/midibox/layers/%d/%s" % (lr._index, prop), getattr(self.mb.layers[index], prop))

            for pedal in lr.pedals:
                for item in MidiBoxPedalProps:
                    prop = item.name
                    self.send_message("/midibox/layers/%d/pedal%d.%s" % (lr._index, pedal._index, prop), getattr(pedal, prop))

    def finish(self):
        self.mb._callbacks.remove(self.mb_midi_callback)
        super().finish()

    def mb_midi_callback(self, msg):
        if msg.type == 'clock':
            return

        self.send_message("/midibox/midi", bytes(msg.bytes()))

    def on_midi(self, addr, param):
        midi = list(param)
        #msg = mido.Message.from_bytes(midi)
        self.mb._write(midi)

    def initialize(self, addr):
        self.mb.initialize()

    def on_main_control_change(self, *args, **kwargs):
        prop, value = list(kwargs.items())[0]
        self.send_message("/midibox/%s" % (prop), value)

    def on_layer_control_change(self, layer, *args, **kwargs):
        prop, value = list(kwargs.items())[0]
        self.send_message("/midibox/layers/%d/%s" % (layer._index, prop), value)

    def on_layer_pedal_control_change(self, pedal, *args, **kwargs):
        prop, value = list(kwargs.items())[0]
        self.send_message("/midibox/layers/%d/pedal%d.%s" % (pedal._layer._index, pedal._index, prop), value)

    def main_control_change(self, addr, args, value):
        prop, = args
        if hasattr(self.mb, prop):
            setattr(self.mb, prop, value)

    def layer_control_change(self, addr, args, value):
        layer, prop = args
        if hasattr(layer, prop):
            setattr(layer, prop, value)

    def layer_pedal_control_change(self, addr, args, value):
        pedal, prop = args
        if hasattr(pedal, prop):
            setattr(pedal, prop, value)
