from typing import Any, Tuple

from .controller import BaseMidibox
from .mido import MidoMidibox
from .osc.client import OscMidibox

default_backend = "mido"

backends: dict[str, Tuple[type[BaseMidibox], dict[Any, Any]]] = {
    'osc': (
        OscMidibox, {
        },
    ),
    'mido': (
        MidoMidibox, {
        },
    ),
    'simulator': (
        MidoMidibox, {
            'port_name': 'MidiboxSimulator:Control',
            'find': True,
        },
    ),
}


def create_midibox_from_config(backend: str = "mido", **kwargs: Any) -> BaseMidibox:
    mb_class, mb_params = backends[backend]
    mb_params = mb_params.copy()
    mb_params.update(**kwargs)
    return mb_class(**mb_params)
