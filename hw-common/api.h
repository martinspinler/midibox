#define LAYERS 8
#define PEDALS 8

#include <stdbool.h>

const uint8_t MIDIBOX_LAYERS = LAYERS;
const uint8_t MIDIBOX_PEDALS = PEDALS;
const uint8_t MIDIBOX_SYSEX_ID1 = 0x77;
const uint8_t MIDIBOX_SYSEX_ID2 = 0x78;
const uint8_t MIDIBOX_PEDAL_SYSEX_ID = 0x79;
const uint8_t MIDIBOX_LAYER_ID_GLOBAL = 15;

enum {
        PEDAL_MODE_IGNORE     = 0,
        PEDAL_MODE_NORMAL     = 1,
        PEDAL_MODE_NOTELENGTH = 2,
        PEDAL_MODE_TOGGLE_ACT = 3,
        PEDAL_MODE_PUSH_ACT   = 4,
};

enum {
        NOTE_MODE_NORMAL      = 0,
        NOTE_MODE_HOLD        = 0x40,
        NOTE_MODE_CUT         = 0x20,
        NOTE_MODE_SHUFFLE     = 0x10,
        NOTE_MODE_HOLDTONEXT  = (NOTE_MODE_HOLD | 1),
        NOTE_MODE_HOLD1_2     = (NOTE_MODE_HOLD | 2),
        NOTE_MODE_HOLD1_4     = (NOTE_MODE_HOLD | 4),
        NOTE_MODE_CUT1_4      = (NOTE_MODE_CUT  | 2),
};

enum {
	MIDIBOX_CMD_INFO      = 0, /* Info request / info response */
	MIDIBOX_CMD_UPDATE    = 1, /* Update data; like READ_RES, but spontaneous update */
	MIDIBOX_CMD_READ_REQ  = 2, /* Read data request */
	MIDIBOX_CMD_READ_RES  = 3, /* Response to read data request */
	MIDIBOX_CMD_WRITE_REQ = 4, /* Write data request */
	MIDIBOX_CMD_WRITE_ACK = 5, /* Write data request was sucessfuly done */
	MIDIBOX_CMD_WRITE_NAK = 6, /* Error occured when handling write request */
	_MIDIBOX_CMD_DONT_USE = 7, /* This will be wrongly coded as SysEx begin: 0xF0 */
	/* INFO: WRITE_ACK can containts data with slightly modified/clamped values */
};

struct layer_state_reg {
	union {
		struct {
			bool enabled: 1;
			bool active: 1;
			bool _init: 1; /* W/O */
		};
		uint8_t config;
	};

	uint8_t status;	/* R/O */
	uint8_t init;	/* W/O */
	uint8_t pgm;
	uint8_t bs;
	uint8_t bs_lsb;
	uint8_t lo; /* Lower range */
	uint8_t hi; /* Upper range */

	uint8_t volume;
	uint8_t mode;
	uint8_t transposition;
	uint8_t transposition_extra;
	uint8_t release;
	uint8_t attack;
	uint8_t cutoff;
	uint8_t decay;
//	uint8_t _unusedp0[6];

	uint8_t pedal_cc[PEDALS];
	uint8_t pedal_mode[PEDALS];

	uint8_t percussion;
	uint8_t harmonic_bar[9];
	uint8_t portamento_time;
};

struct global_state_reg {
	union {
		struct {
			bool enabled: 1;
			bool debug_s2u_all: 1;
			bool debug_s2u: 1;
			bool debug_s2b_all: 1;
			bool debug_s2b: 1;
			bool debug_smsg_print: 1;
			bool debug_cfg_print: 1;
		};
		uint8_t config;
	};

	uint8_t status;	/* R/O */
	uint8_t init;	/* W/O */
	uint8_t selected_layer;

	uint8_t tempo_msb;
	uint8_t tempo_lsb;
//	int8_t _unused0[2];

	uint8_t pedal_cc[PEDALS];
	uint8_t pedal_mode[PEDALS];
};
