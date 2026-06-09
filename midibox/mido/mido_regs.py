from dataclasses import dataclass
from enum import IntEnum
from typing import Any, ClassVar

from midibox.props import clamp, VirtualProp, BoolProp, UInt14Prop
from .reg_struct import RegStruct, BoolField, IntField, ArrayField, FieldMap
from .reg_spec import (
    BoolPropMeta, UIntPropMeta, SIntPropMeta,
    ExpandMeta, SubStructMeta,
)


@dataclass
class LayerPedalConfig(RegStruct):
    """Per-layer pedal sub-struct: cc + mode (2 bytes)."""
    SIZE: ClassVar[int] = 2
    c_name: ClassVar[str] = 'pedal_config_layer'

    cc: int = IntField(0, prop=UIntPropMeta())
    mode: int = IntField(1, prop=UIntPropMeta())


@dataclass
class GeneralPedalConfig(RegStruct):
    """Global pedal sub-struct: cc + mode + min + max (4 bytes)."""
    SIZE: ClassVar[int] = 4
    c_name: ClassVar[str] = 'pedal_config_global'

    cc: int = IntField(0, prop=UIntPropMeta())
    mode: int = IntField(1, prop=UIntPropMeta())
    min: int = IntField(2, prop=UIntPropMeta())
    max: int = IntField(3, prop=UIntPropMeta())


def _check_rangel(s, v):
    return clamp(v, 0, s._rangeu)

def _check_rangeu(s, v):
    return clamp(v, s._rangel, v)

def _check_mode(s, v):
    return v if v in s.modes else s._mode

def _check_percussion(s, v):
    return s.percussions[clamp(v, 0, 4)][1]

def _check_program(s, v):
    if v in s.programs:
        return s.programs[v].ident
    elif isinstance(v, str) and v.startswith("_pgm_"):
        return v
    else:
        return s._program


class MidiboxDefs:
    """Protocol and layout constants.

    Class attributes are the Python names; C names are ``MIDIBOX_{attr}``.
    Iterate via ``_Defs.c_items()`` to get ``(c_name, value)`` pairs for C header generation.
    """
    LAYERS = 8
    PEDALS = 8
    SYSEX_ID1 = 0x77
    SYSEX_ID2 = 0x78
    PEDAL_SYSEX_ID = 0x79
    LAYER_ID_GLOBAL = 0x0F
    LAYER_ID_REG_BASE = 8
    REGS = 7
    REG_INSTRS = 0x10
    REG_STASH_SLOTS = 0x20

    @classmethod
    def c_items(cls) -> list[tuple[str, int]]:
        """Yield (C_NAME, value) pairs in definition order."""
        return [
            (f'MIDIBOX_{k}', v)
            for k, v in vars(cls).items()
            if k.isupper() and not k.startswith('_')
        ]


class RegOperation(IntEnum):
    """Registration operation types"""
    __c_prefix__ = 'REG_OP'
    NOP = 0           # skip this instruction
    NEXT = 1          # pedal_next[triggering_pedal] = source_value
    STASH = 2         # stash[source_value] = target; target unchanged
    RESTORE = 3       # target = stash[source_value]
    SET = 4           # target = source_value
    ADD = 5           # target += (source_value - 64), signed
    SET_BIT = 6       # target |= (1 << source_value)
    CLEAR_BIT = 7     # target &= ~(1 << source_value)


class PedalMode(IntEnum):
    __c_prefix__ = 'PEDAL_MODE'
    IGNORE = 0
    NORMAL = 1
    NOTELENGTH = 2
    TOGGLE_ACT = 3
    PUSH_ACT = 4
    REGISTRATION = 5


class CcInternal(IntEnum):
    __c_prefix__ = 'CC_INT'
    SUSTAIN = 0
    SOSTENUTO = 1
    SOFT = 2
    COUNT = 3


class NoteMode(IntEnum):
    __c_prefix__ = 'NOTE_MODE'
    NORMAL = 0
    HOLD = 0x40
    CUT = 0x20
    SHUFFLE = 0x10
    HOLDTONEXT = 0x41   # HOLD | 1
    HOLD1_2 = 0x42      # HOLD | 2
    HOLD1_4 = 0x44      # HOLD | 4
    CUT1_4 = 0x24       # CUT  | 4


class MidiboxCmd(IntEnum):
    __c_prefix__ = 'MIDIBOX_CMD'
    INFO = 0            # Info request / info response
    UPDATE = 1          # Spontaneous update
    READ_REQ = 2        # Read data request
    READ_RES = 3        # Response to read data request
    WRITE_REQ = 4       # Write data request
    WRITE_ACK = 5       # Write succeeded
    WRITE_NAK = 6       # Write failed


class GsStatus(IntEnum):
    __c_prefix__ = 'GS_STATUS'
    GS_STATUS_INITED = 1


@dataclass
class LayerState(RegStruct):
    """Per-layer state register"""
    SIZE: ClassVar[int] = 48
    c_name: ClassVar[str] = 'layer_state_reg'

    _prop_extras: ClassVar[list[Any]] = [
        VirtualProp('program', 'piano', _check_program, initial='-unknown-'),
    ]

    # Byte 0: config
    enabled: bool = BoolField(0, 0, prop=BoolPropMeta())
    active: bool = BoolField(0, 1, prop=BoolPropMeta(default=True))
    _init: bool = BoolField(0, 2)

    # Byte 1: status
    active_status: bool = BoolField(1, 0, prop=BoolPropMeta(default=True), byte_name='status')

    init: int = IntField(2)
    pgm: int = IntField(3)                                   # composed into 'program'
    bs: int = IntField(4)                                    # composed into 'program'
    bs_lsb: int = IntField(5)                                # composed into 'program'
    lo: int = IntField(6, prop=UIntPropMeta(name='rangel', default=21, validator=_check_rangel))
    hi: int = IntField(7, prop=UIntPropMeta(name='rangeu', default=108, validator=_check_rangeu))
    volume: int = IntField(8, prop=UIntPropMeta(default=100))
    mode: int = IntField(9, prop=UIntPropMeta(validator=_check_mode))
    transposition: int = IntField(10, prop=SIntPropMeta())
    transposition_extra: int = IntField(11, prop=SIntPropMeta())
    release: int = IntField(12, prop=SIntPropMeta())
    attack: int = IntField(13, prop=SIntPropMeta())
    cutoff: int = IntField(14, prop=SIntPropMeta())
    decay: int = IntField(15, prop=SIntPropMeta())
    pedals: list[int] = ArrayField(16, 16, prop=SubStructMeta(LayerPedalConfig), dim='PEDALS')
    percussion: int = IntField(32, prop=UIntPropMeta(validator=_check_percussion))
    harmonic_bar: list[int] = ArrayField(33, 9, prop=ExpandMeta(max=15))
    portamento_time: int = IntField(42, prop=UIntPropMeta())
    volume_ch: int = IntField(43, prop=UIntPropMeta())       # React to volume controller on channel
    noteon_volume: int = IntField(44)                         # Max NoteOn volume
    cc_mode: list[int] = ArrayField(45, 3, prop=ExpandMeta(prefix='cc_int_mode', one_based=True))


@dataclass
class GeneralState(RegStruct):
    """Global state register"""
    SIZE: ClassVar[int] = 38
    c_name: ClassVar[str] = 'global_state_reg'

    _prop_extras: ClassVar[list[Any]] = [
        UInt14Prop('tempo'),
        BoolProp('mute'),
    ]

    # Byte 0: config
    enabled: bool = BoolField(0, 0, prop=BoolPropMeta())
    debug_s2u_all: bool = BoolField(0, 1)
    debug_s2u: bool = BoolField(0, 2)
    debug_s2b_all: bool = BoolField(0, 3)
    debug_s2b: bool = BoolField(0, 4)
    debug_smsg_print: bool = BoolField(0, 5)
    check_keep_alive: bool = BoolField(0, 6)

    status: int = IntField(1)
    init: int = IntField(2)
    selected_layer: int = IntField(3)
    tempo_msb: int = IntField(4)                             # composed into 'tempo' (uint14)
    tempo_lsb: int = IntField(5)                             # composed into 'tempo' (uint14)
    pedals: list[int] = ArrayField(6, 32, prop=SubStructMeta(GeneralPedalConfig), dim='PEDALS')


@dataclass
class RegistrationIstruction(RegStruct):
    """Instruction encoding (4 bytes, all values 7-bit safe for SysEx)"""
    SIZE: ClassVar[int] = 4
    c_name: ClassVar[str] = 'reg_instruction'

    operation: int = IntField(0)                             # REG_OP_* enum
    target_layer: int = IntField(1)                          # 0..7=layer, GLOBAL=global
    target_offset: int = IntField(2)                         # byte offset within target
    source_value: int = IntField(3)                          # literal / stash index / next index



LAYER_SYNC = LayerState.build_sync_map()
GENERAL_SYNC = GeneralState.build_sync_map(virtual_fields=[
    FieldMap('tempo', ('tempo_msb', 'tempo_lsb'), 'uint14'),
])
