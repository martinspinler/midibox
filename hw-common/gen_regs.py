#!/usr/bin/env python3
"""Generate api.h from mido_regs.py — Python is the single source of truth.

Reads item lists via RegStruct.build_items(), filtering by isinstance for
C-relevant items (RegLayout mixin). Only C output is generated; Python
uses the definitions directly.
"""
from __future__ import annotations

from pathlib import Path
from collections import OrderedDict

from midibox.mido.mido_regs import (
    MidiboxDefs,
    LayerState, GeneralState, RegistrationIstruction,
    RegOperation, PedalMode, CcInternal, NoteMode, MidiboxCmd, GsStatus,
)
from midibox.mido.reg_spec import RegLayout, SubStructItem

API_H_PATH = Path(__file__).resolve().parent / "api.h"

# ── Helpers ──────────────────────────────────────────────────────────

def _fmt(val: int) -> str:
    return f"0x{val:02X}" if val > 9 else str(val)


def _dim(item) -> str:
    """Emit an array dimension — use MIDIBOX_-prefixed constant if dim is set."""
    if getattr(item, 'dim', None) is not None:
        return f'MIDIBOX_{item.dim}'
    count = getattr(item, 'array_count', None) or getattr(item, 'count', None)
    return str(count)


# ── C header generation ─────────────────────────────────────────────

def gen_c_header() -> str:
    lines: list[str] = []
    w = lines.append

    w("/* Auto-generated from mido_regs.py — DO NOT EDIT */")
    w("")

    w("#include <stdbool.h>")
    w("#include <stdint.h>")
    w("")

    # Constants — all emitted as #define with MIDIBOX_ prefix
    for c_name, val in MidiboxDefs.c_items():
        w(f"#define {c_name} {_fmt(val)}")
    w("")

    # Enums
    for enum_cls in [RegOperation, PedalMode, CcInternal, NoteMode, MidiboxCmd, GsStatus]:
        doc = (enum_cls.__doc__ or "").strip()
        if doc:
            w(f"/* {doc} */")
        w(f"enum {enum_cls.__name__} {{")
        c_prefix = getattr(enum_cls, '__c_prefix__', '')
        members = list(enum_cls)
        for i, member in enumerate(members):
            comma = "," if i < len(members) - 1 else ""
            if c_prefix:
                full_name = f"{c_prefix}_{member.name}"
                if member.name.startswith(c_prefix + '_'):
                    c_name = member.name
                else:
                    c_name = full_name
            else:
                c_name = member.name
            w(f"\t{c_name} = {_fmt(member.value)}{comma}")
        w("};")
        w("")

    # Structs — driven by item lists, filtered for RegLayout
    for struct_cls in [LayerState, GeneralState, RegistrationIstruction]:
        all_items = struct_cls.build_items()
        reg_items = [i for i in all_items if isinstance(i, RegLayout)]

        # Collect bitfield groups, regular fields, and sub-structs from items
        bf_groups: OrderedDict[int, list[tuple[str, int]]] = OrderedDict()
        bf_byte_names: dict[int, str] = {}
        regular_fields: list[tuple[int, str, int | None, str | None]] = []
        sub_structs: list[SubStructItem] = []

        for item in reg_items:
            if isinstance(item, SubStructItem):
                sub_structs.append(item)
            elif item.bit is not None:
                off = item.offset
                if off not in bf_groups:
                    bf_groups[off] = []
                    bf_byte_names[off] = item.byte_name
                bf_groups[off].append((item.name, item.bit))
            else:
                regular_fields.append((item.offset, item.name, item.count, getattr(item, 'dim', None)))

        # Emit sub-struct definitions before the main struct
        for ss in sub_structs:
            w(f"struct {ss.c_name} {{")
            # Generate member fields from the sub-struct's build_items()
            ss_items = ss.cls.build_items()
            for item in ss_items:
                if isinstance(item, RegLayout) and not isinstance(item, SubStructItem):
                    if getattr(item, 'bit', None) is not None:
                        w(f"\tbool {item.name}: 1;")
                    else:
                        w(f"\tuint8_t {item.name};")
            w("};")
            w("")

        doc = (struct_cls.__doc__ or "").strip()
        if doc:
            w(f"/* {doc} */")

        w(f"struct {struct_cls.c_name} {{")

        # Walk through offsets in order
        all_offsets = sorted(set(
            [off for off, *_ in regular_fields] +
            list(bf_groups.keys()) +
            [ss.offset for ss in sub_structs]
        ))

        for off in all_offsets:
            if off in bf_groups:
                bits = bf_groups[off]
                byte_name = bf_byte_names.get(off, 'config')
                w("\tunion {")
                w("\t\tstruct {")
                for bname, bbit in sorted(bits, key=lambda x: x[1]):
                    w(f"\t\t\tbool {bname}: 1;")
                w("\t\t};")
                w(f"\t\tuint8_t {byte_name};")
                w("\t};")

            for r_off, r_name, r_count, r_dim in regular_fields:
                if r_off != off:
                    continue
                if r_count is not None:
                    size = f'MIDIBOX_{r_dim}' if r_dim else str(r_count)
                    w(f"\tuint8_t {r_name}[{size}];")
                else:
                    w(f"\tuint8_t {r_name};")

            # Sub-struct arrays at this offset
            for ss in sub_structs:
                if ss.offset != off:
                    continue
                w(f"\tstruct {ss.c_name} {ss.name}[{_dim(ss)}];")

        w("};")
        w("")

    return "\n".join(lines) + "\n"


def main():
    c_code = gen_c_header()
    _ = API_H_PATH.write_text(c_code)
    print(f"Generated {API_H_PATH}")


if __name__ == "__main__":
    main()
