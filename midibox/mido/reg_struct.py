"""Register struct base: pack/unpack driven by dataclass field metadata.

Also provides prop-building and sync-map helpers that introspect PropMeta
annotations on RegStruct fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Callable, ClassVar, TypeVar

from midibox.props import BoolProp, UIntProp, SIntProp, CheckedProp
from .reg_spec import (
    PropMeta, BoolPropMeta, UIntPropMeta, SIntPropMeta,
    SubobjectMeta, ExpandMeta, SubStructMeta,
    RegLayout, RegField,
)


T = TypeVar('T', bound='RegStruct')


# ── Field factories ──────────────────────────────────────────────────
def BoolField(offset: int, bit: int, *, prop: PropMeta | None = None, byte_name: str = 'config'):
    """Single-bit field within a byte register."""
    meta: dict[str, Any] = {'offset': offset, 'bit': bit, 'byte_name': byte_name}
    if prop is not None:
        meta['prop'] = prop
    return field(default=False, metadata=meta)


def IntField(offset: int, *, prop: PropMeta | None = None):
    """Byte-sized register field."""
    meta: dict[str, Any] = {'offset': offset}
    if prop is not None:
        meta['prop'] = prop
    return field(default=0, metadata=meta)


def ArrayField(offset: int, count: int, *, prop: PropMeta | None = None,
               dim: str | None = None):
    """Contiguous array of byte-sized fields."""
    meta: dict[str, Any] = {'offset': offset, 'count': count}
    if prop is not None:
        meta['prop'] = prop
    if dim is not None:
        meta['dim'] = dim
    return field(default_factory=lambda _c=count: [0] * _c, metadata=meta)


# ── Combined item types (RegLayout + CheckedProp via MI) ─────────────

class RegBoolProp(RegLayout, BoolProp):
    """Register-backed bool prop — appears in both C header and UI."""

    def __init__(self, name: str, default: bool = False, *,
                 offset: int, bit: int, byte_name: str = 'config') -> None:
        self._init_reg_layout(offset=offset, bit=bit, byte_name=byte_name)
        BoolProp.__init__(self, name, default)


class RegUIntProp(RegLayout, UIntProp):
    """Register-backed uint prop — appears in both C header and UI."""

    def __init__(self, name: str, default: int = 0, *, min: int = 0, max: int = 127,
                 offset: int, bit: int | None = None, byte_name: str = 'config',
                 validator: Callable[[Any, Any], Any] | None = None) -> None:
        self._init_reg_layout(offset=offset, bit=bit, byte_name=byte_name)
        if validator is not None:
            CheckedProp.__init__(self, name, default, validator)
        else:
            UIntProp.__init__(self, name, default, min=min, max=max)


class RegSIntProp(RegLayout, SIntProp):
    """Register-backed signed int prop — appears in both C header and UI."""

    def __init__(self, name: str, *, offset: int, bit: int | None = None,
                 byte_name: str = 'config') -> None:
        self._init_reg_layout(offset=offset, bit=bit, byte_name=byte_name)
        SIntProp.__init__(self, name)


# ── PropMeta.build_items implementations (cross-module) ─────────────
#
# These depend on RegBoolProp / RegUIntProp / RegSIntProp / UIntProp
# which are not available in reg_spec.py (deliberate: no midibox.props dep).
# We attach them here after the combined classes are defined.

def _bool_meta_build_items(self: BoolPropMeta, f_name: str, *, offset: int,
                            bit: int | None, count: int | None,
                            byte_name: str, dim: str | None) -> list[Any]:
    name = self.name or f_name
    return [RegBoolProp(name, self.default, offset=offset,
                        bit=bit if bit is not None else 0,
                        byte_name=byte_name)]


def _uint_meta_build_items(self: UIntPropMeta, f_name: str, *, offset: int,
                           bit: int | None, count: int | None,
                           byte_name: str, dim: str | None) -> list[Any]:
    name = self.name or f_name
    if self.validator is not None:
        return [RegUIntProp(name, self.default, offset=offset,
                            byte_name=byte_name, validator=self.validator)]
    return [RegUIntProp(name, self.default, max=self.max,
                        offset=offset, byte_name=byte_name)]


def _sint_meta_build_items(self: SIntPropMeta, f_name: str, *, offset: int,
                           bit: int | None, count: int | None,
                           byte_name: str, dim: str | None) -> list[Any]:
    name = self.name or f_name
    return [RegSIntProp(name, offset=offset, byte_name=byte_name)]


def _expand_meta_build_items(self: ExpandMeta, f_name: str, *, offset: int,
                             bit: int | None, count: int | None,
                             byte_name: str, dim: str | None) -> list[Any]:
    items: list[Any] = [RegField(f_name, offset=offset, count=count,
                                 byte_name=byte_name, dim=dim)]
    assert count is not None
    prefix = self.prefix or f_name
    for i in range(count):
        idx = i + 1 if self.one_based else i
        items.append(UIntProp(f'{prefix}{idx}', max=self.max))
    return items


BoolPropMeta.build_items = _bool_meta_build_items
UIntPropMeta.build_items = _uint_meta_build_items
SIntPropMeta.build_items = _sint_meta_build_items
ExpandMeta.build_items = _expand_meta_build_items


# ── Sync map types ───────────────────────────────────────────────────

class FieldMap:
    """Maps a single prop to a register field with optional transform."""
    __slots__ = ('prop', 'reg', 'xform')

    def __init__(self, prop: str, reg: str | tuple[str, ...], xform: str | None = None) -> None:
        self.prop = prop
        self.reg = reg
        self.xform = xform  # None | 'signed' | 'uint14'


class ArrayMap:
    """Maps array register fields to sub-object properties."""
    __slots__ = ('subobject', 'field_map')

    def __init__(self, subobject: str, field_map: dict[str, str]) -> None:
        self.subobject = subobject   # e.g. 'pedals'
        self.field_map = field_map   # e.g. {'cc': 'pedal_cc', 'mode': 'pedal_mode'}


class ExpandMap:
    """Maps an array register field to individually numbered props."""
    __slots__ = ('prefix', 'reg', 'count', 'one_based', 'xform')

    def __init__(self, prefix: str, reg: str, count: int,
                 one_based: bool = False, xform: str | None = None) -> None:
        self.prefix = prefix
        self.reg = reg
        self.count = count
        self.one_based = one_based
        self.xform = xform


class SubStructMap:
    """Maps an interleaved sub-struct array to sub-object properties."""
    __slots__ = ('sub_name', 'cls', 'reg_field', 'stride')

    def __init__(self, sub_name: str, cls: type, reg_field: str) -> None:
        self.sub_name = sub_name   # e.g. 'pedals'
        self.cls = cls             # RegStruct subclass (e.g. pedal_config)
        self.reg_field = reg_field # field name in parent struct (e.g. 'pedals')
        self.stride = cls.SIZE


# ── Base class ───────────────────────────────────────────────────────

@dataclass
class RegStruct:
    """Base for register-struct dataclasses.

    Subclasses use ``@dataclass`` with ``BoolField``, ``IntField``,
    or ``ArrayField`` to declare layout.  Provides ``pack()`` /
    ``unpack()`` and standard dataclass features (``__init__``,
    ``__repr__``, ``__eq__``, ``fields()`` iteration).

    Class methods ``build_items()``, ``build_ui_props()``, and
    ``build_sync_map()`` introspect PropMeta annotations to produce
    mixed item lists, UI prop lists, and sync mappings.

    ``c_name`` sets the C struct name (defaults to ``__name__``).
    """

    SIZE: ClassVar[int]
    c_name: ClassVar[str]  # overridden per subclass

    def pack(self) -> list[int]:
        """Serialize to a plain list of bytes (wire format)."""
        data = [0] * self.SIZE
        for f in fields(self):
            m = f.metadata
            offset: int = m["offset"]
            val = getattr(self, f.name)
            if "bit" in m:
                if val:
                    data[offset] |= 1 << m["bit"]
            elif "count" in m:
                for i, v in enumerate(val):
                    data[offset + i] = v
            else:
                data[offset] = val
        return data

    # ── Item/prop-building class methods ─────────────────────────────

    @classmethod
    def build_items(cls) -> list[Any]:
        """Introspect fields and build a mixed list of register and UI items.

        Items with RegLayout mixin appear in C header generation.
        Items that are CheckedProp instances appear in UI layer.
        Items with both (RegBoolProp, RegUIntProp, RegSIntProp) appear in both.
        """
        items: list[Any] = []
        for f in fields(cls):
            meta: PropMeta | None = f.metadata.get('prop')
            offset: int = f.metadata['offset']
            bit: int | None = f.metadata.get('bit')
            count: int | None = f.metadata.get('count')
            byte_name: str = f.metadata.get('byte_name', 'config')
            dim: str | None = f.metadata.get('dim')

            if meta is None:
                # Register field with no UI prop
                items.append(RegField(f.name, offset=offset, bit=bit,
                                      count=count, byte_name=byte_name,
                                      dim=dim))
            else:
                items.extend(meta.build_items(f.name, offset=offset, bit=bit,
                                              count=count, byte_name=byte_name,
                                              dim=dim))

        # Append extras (virtual props with no register backing)
        extras = getattr(cls, '_prop_extras', [])
        items.extend(extras)

        return items

    @classmethod
    def build_ui_props(cls) -> list[CheckedProp[Any]]:
        """Return UI-relevant props only (CheckedProp instances from build_items)."""
        return [i for i in cls.build_items() if isinstance(i, CheckedProp)]

    @classmethod
    def build_sync_map(
        cls,
        virtual_fields: list[FieldMap] | None = None,
    ) -> list[FieldMap | ArrayMap | ExpandMap]:
        """Introspect fields and build a sync mapping list.

        The returned list drives load_from_reg() and update_reg_from_handler().
        virtual_fields adds extra FieldMap entries for composite/virtual props
        (e.g. tempo spanning tempo_msb + tempo_lsb).
        """
        syncs: list[FieldMap | ArrayMap | ExpandMap | SubStructMap] = []
        subobject_maps: dict[str, dict[str, str]] = {}
        substruct_fields: dict[str, type] = {}  # field_name -> cls

        for f in fields(cls):
            meta: PropMeta | None = f.metadata.get('prop')
            if meta is None:
                continue

            if isinstance(meta, SubStructMeta):
                substruct_fields[f.name] = meta.cls
                continue

            if isinstance(meta, SubobjectMeta):
                if meta.subobject not in subobject_maps:
                    subobject_maps[meta.subobject] = {}
                subobject_maps[meta.subobject][meta.field] = f.name
                continue

            if isinstance(meta, ExpandMeta):
                count = f.metadata['count']
                prefix = meta.prefix or f.name
                syncs.append(ExpandMap(prefix, f.name, count, meta.one_based))
                continue

            # Simple field mapping
            prop_name = meta.name or f.name
            xform: str | None = None
            if isinstance(meta, SIntPropMeta):
                xform = 'signed'
            syncs.append(FieldMap(prop_name, f.name, xform))

        # Add sub-struct entries
        for field_name, cls in substruct_fields.items():
            syncs.append(SubStructMap(field_name, cls, field_name))

        # Add flat sub-object entries
        for so_name, fmap in subobject_maps.items():
            syncs.append(ArrayMap(so_name, fmap))

        # Add virtual/composite fields
        if virtual_fields:
            syncs.extend(virtual_fields)

        return syncs

    @classmethod
    def unpack(cls: type[T], data: list[int] | bytearray) -> T:
        """Deserialize from a byte list (e.g. received over MIDI)."""
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            m = f.metadata
            offset: int = m["offset"]
            if "bit" in m:
                val = bool(data[offset] & (1 << m["bit"]))
            elif "count" in m:
                val = list(data[offset : offset + m["count"]])
            else:
                val = data[offset]
            kwargs[f.name] = val
        return cls(**kwargs)


# ── Sync helper functions ────────────────────────────────────────────

def load_from_reg(handler: Any, reg: RegStruct, sync_map: list) -> None:
    """Load prop values from a RegStruct into a PropHandler (device -> UI)."""
    for m in sync_map:
        if isinstance(m, FieldMap):
            if isinstance(m.reg, tuple):
                if m.xform == 'uint14':
                    msb_name, lsb_name = m.reg
                    val = (getattr(reg, msb_name) << 7) | getattr(reg, lsb_name)
                else:
                    continue  # unknown composite
            elif m.xform == 'signed':
                val = getattr(reg, m.reg) - 64
            else:
                val = getattr(reg, m.reg)
            setattr(handler, m.prop, val)
        elif isinstance(m, SubStructMap):
            arr = getattr(reg, m.reg_field)
            subobjs = getattr(handler, m.sub_name)
            member_names = [f.name for f in fields(m.cls)]
            for i, sub in enumerate(subobjs):
                for j, member in enumerate(member_names):
                    setattr(sub, member, arr[i * m.stride + j])
        elif isinstance(m, ArrayMap):
            subobjs = getattr(handler, m.subobject)
            for i, sub in enumerate(subobjs):
                for sub_prop, reg_arr in m.field_map.items():
                    setattr(sub, sub_prop, getattr(reg, reg_arr)[i])
        elif isinstance(m, ExpandMap):
            arr = getattr(reg, m.reg)
            for i in range(m.count):
                idx = i + 1 if m.one_based else i
                val = arr[i] - 64 if m.xform == 'signed' else arr[i]
                setattr(handler, f'{m.prefix}{idx}', val)


def update_reg_from_handler(
    handler: Any,
    reg: RegStruct,
    names: list[str],
    sync_map: list,
    sub_index: int | None = None,
) -> None:
    """Update a RegStruct from changed prop names (UI -> device).

    sub_index limits sub-object updates to a single element
    (e.g. when one pedal changes, not all eight).
    """
    for m in sync_map:
        if isinstance(m, FieldMap):
            if m.prop not in names:
                continue
            if isinstance(m.reg, tuple):
                if m.xform == 'uint14':
                    val = getattr(handler, m.prop)
                    msb_name, lsb_name = m.reg
                    setattr(reg, msb_name, (val >> 7) & 0x7F)
                    setattr(reg, lsb_name, val & 0x7F)
            elif m.xform == 'signed':
                setattr(reg, m.reg, getattr(handler, m.prop) + 64)
            else:
                setattr(reg, m.reg, getattr(handler, m.prop))
        elif isinstance(m, SubStructMap):
            arr = getattr(reg, m.reg_field)
            subobjs = getattr(handler, m.sub_name)
            member_names = [f.name for f in fields(m.cls)]
            if sub_index is not None:
                for j, member in enumerate(member_names):
                    if member in names:
                        arr[sub_index * m.stride + j] = getattr(subobjs[sub_index], member)
            else:
                for i, sub in enumerate(subobjs):
                    for j, member in enumerate(member_names):
                        if member in names:
                            arr[i * m.stride + j] = getattr(sub, member)
        elif isinstance(m, ArrayMap):
            for sub_prop, reg_arr in m.field_map.items():
                if sub_prop not in names:
                    continue
                subobjs = getattr(handler, m.subobject)
                if sub_index is not None:
                    getattr(reg, reg_arr)[sub_index] = getattr(subobjs[sub_index], sub_prop)
                else:
                    for i, sub in enumerate(subobjs):
                        getattr(reg, reg_arr)[i] = getattr(sub, sub_prop)
        elif isinstance(m, ExpandMap):
            arr = getattr(reg, m.reg)
            for i in range(m.count):
                idx = i + 1 if m.one_based else i
                name = f'{m.prefix}{idx}'
                if name in names:
                    val = getattr(handler, name)
                    arr[i] = val + 64 if m.xform == 'signed' else val
