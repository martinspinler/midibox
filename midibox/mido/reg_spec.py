"""Lightweight prop descriptors for register field metadata.

Stored in dataclass field ``metadata['prop']`` alongside serialization info.
No dependencies on midibox.props or controller.base — safe to import from
code generators and C-header tools.
"""
from __future__ import annotations

from typing import Any, Callable


class PropMeta:
    """Base: describes how a register field maps to a UI property."""

    def build_items(self, f_name: str, *, offset: int, bit: int | None,
                    count: int | None, byte_name: str, dim: str | None) -> list[Any]:
        """Build items produced by this meta given register context.

        Override in subclasses to return the appropriate list of items
        (RegField, RegBoolProp, UIntProp, etc.).  The default raises
        NotImplementedError; implementations that depend on midibox.props
        types are attached from reg_struct.py after import.
        """
        raise NotImplementedError(type(self).__name__)


class BoolPropMeta(PropMeta):
    def __init__(self, name: str | None = None, default: bool = False) -> None:
        self.name = name
        self.default = default


class UIntPropMeta(PropMeta):
    def __init__(self, name: str | None = None, default: int = 0, max: int = 127,
                 validator: Callable[[Any, Any], Any] | None = None) -> None:
        self.name = name
        self.default = default
        self.max = max
        self.validator = validator


class SIntPropMeta(PropMeta):
    """Unsigned register field exposed as signed prop (±64 transform)."""
    def __init__(self, name: str | None = None) -> None:
        self.name = name


class SubobjectMeta(PropMeta):
    """Array field mapped to sub-object properties (e.g. pedals[i].cc)."""
    def __init__(self, subobject: str, field: str) -> None:
        self.subobject: str = subobject
        self.field: str = field

    def build_items(self, f_name: str, *, offset: int, bit: int | None,
                    count: int | None, byte_name: str, dim: str | None) -> list[Any]:
        return [RegField(f_name, offset=offset, count=count,
                         byte_name=byte_name, dim=dim)]


class ExpandMeta(PropMeta):
    """Array field expanded to individually numbered props (e.g. harmonic_bar0..8)."""
    def __init__(self, prefix: str | None = None, one_based: bool = False, max: int = 127) -> None:
        self.prefix = prefix
        self.one_based = one_based
        self.max = max


class SubStructMeta(PropMeta):
    """Interleaved sub-struct array mapped to a RegStruct subclass.

    E.g. pedals[8] where each element is described by pedal_config_layer (a
    RegStruct with cc and mode fields), stored as interleaved bytes in the
    parent register.
    """
    def __init__(self, cls: type) -> None:
        self.cls: type = cls          # RegStruct subclass defining the sub-struct

    def build_items(self, f_name: str, *, offset: int, bit: int | None,
                    count: int | None, byte_name: str, dim: str | None) -> list[Any]:
        return [SubStructItem(self.cls, name=f_name,
                              offset=offset, array_count=count // self.cls.SIZE,
                              dim=dim)]


class RegLayout:
    """Mixin: register layout info for C header generation.

    Items carrying this mixin are included in C struct output by gen_regs.py.
    Combined with CheckedProp via multiple inheritance for register-backed UI props.
    """

    def _init_reg_layout(self, *, offset: int, bit: int | None = None,
                          count: int | None = None, byte_name: str = 'config') -> None:
        self.offset: int = offset
        self.bit: int | None = bit
        self.count: int | None = count
        self.byte_name: str = byte_name


class RegField(RegLayout):
    """Register field with no UI prop — appears in C header only."""

    def __init__(self, name: str, *, offset: int, bit: int | None = None,
                 count: int | None = None, byte_name: str = 'config',
                 dim: str | None = None) -> None:
        self.name = name
        self.offset: int = offset
        self.bit: int | None = bit
        self.count: int | None = count
        self.byte_name: str = byte_name
        self.dim = dim


class SubStructItem(RegLayout):
    """Sub-struct array — emitted as nested struct in C header."""

    def __init__(self, cls: type, *, name: str,
                 offset: int, array_count: int, dim: str | None = None) -> None:
        self.cls = cls
        self.name: str = name          # field name in parent (e.g. 'pedals')
        self.c_name: str = cls.c_name  # C struct name (e.g. 'pedal_config_layer')
        self.offset = offset
        self.array_count = array_count
        self.dim = dim
        self.bit: int | None = None
        self.count: int | None = array_count * cls.SIZE
        self.byte_name: str = 'config'
