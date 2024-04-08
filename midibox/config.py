from types import SimpleNamespace
from .controller.base import MidiBoxLayerProps, MidiBoxProps, MidiBoxPedalProps


def validate_config(config, props):
    try:
        from schema import Schema, SchemaError, Optional, Or
    except:
        print("module schema not found, config not validated!")
        return

    config_schema = Schema({
        Optional("presets"): [
            {
                "label": str,
                "name": str,
                Optional("global"): {
                    Optional("enabled"): bool,
                },

                Optional("copy"): Or(
                    [str], str
                ),
                Optional("layers"): [
                    {
                        Optional("copy"): Or(
                            None, # copy prev layer
                            {   # copy single layer
                                Optional("preset"): str,
                                Optional("layer"): int,
                            },
                            [{Optional("layer"): int}], # copy multiple: layer should be specified, otherwise is nonsense (copy n times the same prev layer)
                        ),
                        Optional("layer"): int,
                        Optional("program"): str,
                        Optional("enabled"): bool,
                        Optional("active"): bool,
                        Optional("rangeu"): int,
                        Optional("rangel"): int,
                        Optional("volume"): int,
                        Optional("transposition"): int,
                        Optional("transposition_extra"): int,
                        Optional("pedals"): [
                            {
                                Optional("copy"): Or(None),
                                Optional("pedal"): int,
                                Optional("mode"): Or("none", "normal", "note_length", "toggle_active", "push_active"),
                                Optional("cc"): int,
                            }
                        ],
                    }
                ]
            }
        ]
    })

    try:
        config_schema.validate({'presets': config.get("presets", [])})
        print("Configuration is valid.")
    except SchemaError as se:
        #raise se
        print(se)

class PedalPreset():
    def __str__(self):
        return f"Pedal {self.layer} {self.index}"

    def __init__(self, layer, cfg, index):
        self._cfg = cfg
        self.index = cfg.get("pedal", index)
        self.layer = layer
        self._base = []
        self._presets = None

    def update_refs(self, presets):
        if self._presets is not None:
            return
        self._presets = presets

        if "copy" in self._cfg.keys(): # value can be None
            copy = self._cfg.get("copy")
            if isinstance(copy, list):
                base = copy
            elif isinstance(copy, dict):
                base = [copy]
            elif copy is None:
                base = [{}]
            else:
                raise NotImplemented()

            for copy in base:
                preset = presets.get(copy.get("preset"), self.layer.preset)
                preset.update_refs(presets)
                layer = preset.get_layer(copy.get("layer", self.layer.index))

                pi = copy.get("pedal", self.index - (1 if self.layer == layer else 0))
                assert pi >= 0
                self._base.append(layer.get_pedal(pi))

    def get_config(self, config):
        for base in self._base:
            base.get_config(config)

        for k, v in self._cfg.items():
            if k in self.layer.preset._props.pedal:
                config[k] = v


class LayerPreset():
    def __init__(self, preset, cfg, index):
        self._cfg = cfg
        self.index = cfg.get("layer", index)
        self.preset = preset
        self._pedals = {}
        self._base = []
        self._presets = None

        for k, v in cfg.items():
            if k == 'pedals':
                index = 0
                for p in v:
                    pedal = PedalPreset(self, p, index)
                    index = pedal.index
                    assert 0 <= index <= 8
                    assert self._pedals.get(index) == None
                    self._pedals[index] = pedal
                    index += 1

    def __str__(self):
        return f"Layer {self.preset.name} {self.index}"

    def update_refs(self, presets):
        if self._presets is not None:
            return
        self._presets = presets

        if "copy" in self._cfg.keys():
            copy = self._cfg.get("copy")
            if isinstance(copy, list):
                base = copy
            elif isinstance(copy, dict):
                base = [copy] 
            elif copy is None:
                base = [{}]
            else:
                raise NotImplemented()

            for copy in base:
                preset = presets.get(copy.get("preset"), self.preset)
                preset.update_refs(presets)

                layer = copy.get("layer", self.index - (1 if preset == self.preset else 0))
                assert layer >= 0
                self._base.append(preset.get_layer(layer))

        for pedal in self._pedals.values():
            pedal.update_refs(presets)

    def get_config(self, config):
        if config.get('pedals') is None:
            config['pedals'] = {}

        for base in self._base:
            base.get_config(config)

        for k, v in self._cfg.items():
            if k in self.preset._props.layer:
                config[k] = v

        for pedal in self._pedals.values():
            if config['pedals'].get(pedal.index) is None:
                config['pedals'][pedal.index] = {}
            pedal.get_config(config['pedals'][pedal.index])

    def get_pedal(self, index):
        if index in self._pedals:
            return self._pedals[index]
        elif self._base:
            return self._base.get_pedal(index)
        raise Exception(f"No futher base to get pedal in {self}:{index}")



class Preset():
    def __init__(self, cfg, props):
        self._cfg = cfg
        self.name = cfg.get("name")
        self.label = cfg.get("label")
        self._layers = {}
        self._base = []
        self._presets = None
        self._props = props

        for k, v in cfg.items():
            if k == 'layers':
                index = 0
                for l in v:
                    layer = LayerPreset(self, l, index)
                    index = layer.index
                    assert 0 <= index <= 8
                    assert self._layers.get(index) == None
                    self._layers[index] = layer
                    index += 1

    def __str__(self):
        return f"Preset {self.name}"

    def update_refs(self, presets):
        if self._presets is not None:
            return
        self._presets = presets

        if "copy" in self._cfg.keys():
            copy = self._cfg.get("copy")
            if isinstance(copy, list):
                base = copy
            elif isinstance(copy, str):
                base = [copy]
            else:
                raise NotImplemented()

            for copy in base:
                self._base.append(presets.get(copy))

        for layer in self._layers.values():
            layer.update_refs(presets)

    def get_layer(self, index):
        if index in self._layers:
            return self._layers[index]
        elif self._base:
            return self._base.get_layer(index)
        raise Exception(f"No futher base to get layer in {self}:{index}")

    def get_config(self, config):
        if config.get('layers') is None:
            config['layers'] = {}

        for base in self._base:
            base.get_config(config)

        for k, v in self._cfg.items():
            if k in self._props.glob:
                config[k] = v

        for layer in self._layers.values():
            if config['layers'].get(layer.index) is None:
                config['layers'][layer.index] = {}
            layer.get_config(config['layers'][layer.index])


def presets_from_config(config):
    props = SimpleNamespace(
        glob=[prop.name for prop in MidiBoxProps],
        layer=[prop.name for prop in MidiBoxLayerProps],
        pedal=[prop.name for prop in MidiBoxPedalProps],
    )

    validate_config(config, props)

    # Sanitize input config
    presets = {p["name"]: Preset(p, props) for p in config.get('presets', [])}

    for p in presets.values():
        p.update_refs(presets)

    if False:#: and (presets := config.get('presets')):
        for p, preset in []: #enumerate(presets):
            #presets = {preset.name: Preset(preset)}
            li = 0
            for layer in preset.get('layers', []):
                # Override index
                layer['__index'] = layer.get("layer", li)

                pi = 0
                for pedal in layer.get('pedals', []):
                    pedal['__index'] = pedal.get("pedal", pi)
                    pi = pedal['__index'] + 1

                li = layer['__index'] + 1

    return presets
