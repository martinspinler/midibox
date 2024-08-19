from .controller import Midibox
from .osc.client import OscMidibox

default_backend = "mido"

backends = {
    'osc': (
        OscMidibox, {
        },
    ),
    'mido': (
        Midibox, {
        },
    ),
    'simulator': (
        Midibox, {
            'port_name': 'MidiboxSimulator:Control',
            'find': True,
        },
    ),
}


def create_midibox_from_config(backend="mido", **kwargs):
    mb_class, mb_params = backends[backend]
    mb_params = mb_params.copy()
    mb_params.update(**kwargs)
    return mb_class(**mb_params)
