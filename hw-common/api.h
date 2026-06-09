/* Auto-generated from mido_regs.py — DO NOT EDIT */

#include <stdbool.h>
#include <stdint.h>

#define MIDIBOX_LAYERS 8
#define MIDIBOX_PEDALS 8
#define MIDIBOX_SYSEX_ID1 0x77
#define MIDIBOX_SYSEX_ID2 0x78
#define MIDIBOX_PEDAL_SYSEX_ID 0x79
#define MIDIBOX_LAYER_ID_GLOBAL 0x0F
#define MIDIBOX_LAYER_ID_REG_BASE 8
#define MIDIBOX_REGS 7
#define MIDIBOX_REG_INSTRS 0x10
#define MIDIBOX_REG_STASH_SLOTS 0x20

/* Registration operation types */
enum RegOperation {
	REG_OP_NOP = 0,
	REG_OP_NEXT = 1,
	REG_OP_STASH = 2,
	REG_OP_RESTORE = 3,
	REG_OP_SET = 4,
	REG_OP_ADD = 5,
	REG_OP_SET_BIT = 6,
	REG_OP_CLEAR_BIT = 7
};

enum PedalMode {
	PEDAL_MODE_IGNORE = 0,
	PEDAL_MODE_NORMAL = 1,
	PEDAL_MODE_NOTELENGTH = 2,
	PEDAL_MODE_TOGGLE_ACT = 3,
	PEDAL_MODE_PUSH_ACT = 4,
	PEDAL_MODE_REGISTRATION = 5
};

enum CcInternal {
	CC_INT_SUSTAIN = 0,
	CC_INT_SOSTENUTO = 1,
	CC_INT_SOFT = 2,
	CC_INT_COUNT = 3
};

enum NoteMode {
	NOTE_MODE_NORMAL = 0,
	NOTE_MODE_HOLD = 0x40,
	NOTE_MODE_CUT = 0x20,
	NOTE_MODE_SHUFFLE = 0x10,
	NOTE_MODE_HOLDTONEXT = 0x41,
	NOTE_MODE_HOLD1_2 = 0x42,
	NOTE_MODE_HOLD1_4 = 0x44,
	NOTE_MODE_CUT1_4 = 0x24
};

enum MidiboxCmd {
	MIDIBOX_CMD_INFO = 0,
	MIDIBOX_CMD_UPDATE = 1,
	MIDIBOX_CMD_READ_REQ = 2,
	MIDIBOX_CMD_READ_RES = 3,
	MIDIBOX_CMD_WRITE_REQ = 4,
	MIDIBOX_CMD_WRITE_ACK = 5,
	MIDIBOX_CMD_WRITE_NAK = 6
};

enum GsStatus {
	GS_STATUS_INITED = 1
};

struct pedal_config_layer {
	uint8_t cc;
	uint8_t mode;
};

/* Per-layer state register */
struct layer_state_reg {
	union {
		struct {
			bool enabled: 1;
			bool active: 1;
			bool _init: 1;
		};
		uint8_t config;
	};
	union {
		struct {
			bool active_status: 1;
		};
		uint8_t status;
	};
	uint8_t init;
	uint8_t pgm;
	uint8_t bs;
	uint8_t bs_lsb;
	uint8_t rangel;
	uint8_t rangeu;
	uint8_t volume;
	uint8_t mode;
	uint8_t transposition;
	uint8_t transposition_extra;
	uint8_t release;
	uint8_t attack;
	uint8_t cutoff;
	uint8_t decay;
	struct pedal_config_layer pedals[MIDIBOX_PEDALS];
	uint8_t percussion;
	uint8_t harmonic_bar[9];
	uint8_t portamento_time;
	uint8_t volume_ch;
	uint8_t noteon_volume;
	uint8_t cc_mode[3];
};

struct pedal_config_global {
	uint8_t cc;
	uint8_t mode;
	uint8_t min;
	uint8_t max;
};

/* Global state register */
struct global_state_reg {
	union {
		struct {
			bool enabled: 1;
			bool debug_s2u_all: 1;
			bool debug_s2u: 1;
			bool debug_s2b_all: 1;
			bool debug_s2b: 1;
			bool debug_smsg_print: 1;
			bool check_keep_alive: 1;
		};
		uint8_t config;
	};
	uint8_t status;
	uint8_t init;
	uint8_t selected_layer;
	uint8_t tempo_msb;
	uint8_t tempo_lsb;
	struct pedal_config_global pedals[MIDIBOX_PEDALS];
};

/* Instruction encoding (4 bytes, all values 7-bit safe for SysEx) */
struct reg_instruction {
	uint8_t operation;
	uint8_t target_layer;
	uint8_t target_offset;
	uint8_t source_value;
};

