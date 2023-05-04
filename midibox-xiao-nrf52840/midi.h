#ifndef __MIDI_H__
#define __MIDI_H__

#include <MIDI.h>

#ifdef ARDUINO
#include "midibox-compat.h"
#else
#include <midibox-compat.h>
#endif

extern MidiInterfaceUsb MU;
extern MidiInterfaceHwserial MS1;
extern MidiInterfaceBle MB;


#define LAYERS 8
#define PEDALS 8

#define MIDIBOX_SYSEX_ID        0x77

#define PEDAL_MODE_IGNORE       0
#define PEDAL_MODE_NORMAL       1
#define PEDAL_MODE_NOTELENGTH   2
#define PEDAL_MODE_TOGGLE_EN    3

#define NOTE_MODE_NORMAL        0
#define NOTE_MODE_HOLD          0x40
#define NOTE_MODE_CUT           0x20
#define NOTE_MODE_SHUFFLE       0x10
#define NOTE_MODE_HOLDTONEXT    (NOTE_MODE_HOLD | 1)
#define NOTE_MODE_HOLD1_2       (NOTE_MODE_HOLD | 2)
#define NOTE_MODE_HOLD1_4       (NOTE_MODE_HOLD | 4)
#define NOTE_MODE_CUT1_4        (NOTE_MODE_CUT  | 2)

struct layer_state {
	uint16_t channel_in_mask;
	uint16_t program_index;
	uint8_t enabled;
	uint8_t lo; /* Lower range */
	uint8_t hi; /* Upper range */
	uint8_t volume;
	int8_t  transposition;
	int8_t  transposition_extra;
	int8_t  channel_out_offset;
	uint8_t last_note_vol;
	uint8_t last_note;
	uint8_t cc_sustain;
	uint8_t cc_expression;
#if 0
	uint8_t cc_pedal1_mode; /* ignore, normal, bass... */
	uint8_t cc_pedal2_mode;
	uint8_t cc_pedal3_mode;
#endif
	uint8_t mode;
	uint8_t status;
	uint8_t note[128/8];

	uint8_t pedal_cc[PEDALS];
	uint8_t pedal_mode[PEDALS];

	uint8_t ticks_remains[128];
	uint8_t note_origin[128];
};

struct midi_clock {
	uint16_t b;
	uint8_t q;
	uint8_t tc;
};

struct global_state {
	union {
		struct {
			bool enabled: 1;
			bool debug_s2u_all: 1;
			bool debug_s2b_all: 1;
			bool debug_s2b: 1;
			bool debug_smsg_print: 1;
			bool debug_cfg_print: 1;
		};
		uint8_t config;
	};

	uint8_t pedal_cc[PEDALS];
	uint8_t pedal_mode[PEDALS];

	unsigned long tempo;
	struct midi_clock mc;
};

extern struct layer_state ls[LAYERS];
extern struct global_state gs;

enum {
	MIDIBOX_CMD_GET_GLOBAL  = 1,
	MIDIBOX_CMD_SET_GLOBAL  = 2,
	MIDIBOX_CMD_GET_LAYER   = 3,
	MIDIBOX_CMD_SET_LAYER   = 4,
};

void midi_init();
void midi_loop();
void midi_handle_config();
void midi_handle_instrument_cmd(uint8_t cmd);
void midi_handle_controller_cmd(int origin, const uint8_t *cmd, uint16_t len);

void midi_secondary_handle_input();

void midi_change_tempo(unsigned long t);

static inline bool layer_is_playing(struct layer_state & ls, uint8_t note)
{
	return ls.note[note >> 3] & (1 << (note & 0x7));
}

static inline void layer_set_playing(struct layer_state & ls, uint8_t note, bool playing, uint8_t origin)
{
	if (playing) {
		if (note < 0x80) {
			ls.note[note >> 3] |=  (1 << (note & 0x7));
		}
		if (origin < 0x80) {
			ls.note_origin[origin] = 0x80 | note;
		}
	} else {
		if (note < 0x80) {
			ls.note[note >> 3] &= ~(1 << (note & 0x7));
		}
		if (origin < 0x80 || true) {
			ls.note_origin[origin] = 0;
		}
	}
}

#endif // __MIDI_H__
