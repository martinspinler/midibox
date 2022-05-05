#ifndef __MIDI_H__
#define __MIDI_H__

#ifdef ARDUINO
#include <Arduino.h>
#else
#include <cstdint>
#endif

#define LAYERS 8

#define MIDIBOX_SYSEX_ID        0x77

#include "midi_def.h"

#define PEDAL_MODE_IGNORE       0
#define PEDAL_MODE_NORMAL       1
#define PEDAL_MODE_NOTELENGTH   2
#define PEDAL_MODE_TOGGLE_EN    3

#define NOTE_MODE_NORMAL        0
#define NOTE_MODE_HOLD          0x80 /* INFO: mask */
#define NOTE_MODE_CUT           0x40
#define NOTE_MODE_SHUFFLE       0x20
#define NOTE_MODE_HOLDTONEXT    0x81
#define NOTE_MODE_HOLD1_4       0x82
#define NOTE_MODE_HOLD1_2       0x83
#define NOTE_MODE_CUT1_4        0x42

struct midi_program_t {
	const char *name;
	const char *short_name;
	const char program; /* For Roland MIDI is from range 1..128, so decrease by 1 */
	const char ccm;
	const char ccl;
	const uint8_t *sysex;
};

extern struct midi_program_t midi_programs[];

struct layer_state {
	uint16_t channel_in_mask;
	uint16_t program_index;
	uint8_t enabled;
	uint8_t lo; /* Lower range */
	uint8_t hi; /* Upper range */
	uint8_t volume;
	int8_t  transposition;
	int8_t  channel_out_offset;
	uint8_t last_note_vol;
	uint8_t last_note;
	uint8_t cc_damper;
	uint8_t cc_expression;
	uint8_t cc_pedal1_mode; /* ignore, normal, bass... */
	uint8_t cc_pedal2_mode;
	uint8_t cc_pedal3_mode;
	uint8_t mode;
	uint8_t status;
	uint8_t note[128/8];

	uint8_t ticks_remains[128];
};

extern struct layer_state ls[LAYERS];

/*
unsigned char state_hammond_bars[14] = {0x40, 0x41, 0x51, 0x00, 0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0};
*/

struct midi_clock {
	uint16_t b;
	uint8_t q;
	uint8_t tc;
};

extern struct midi_clock mc;

struct core_comm {
	int cmd;
	union {
		struct {
			uint8_t index;
			struct layer_state state;
		} layer;
		uint8_t enable;
	};
};

extern struct core_comm comm_1to2;
extern struct core_comm comm_2to1;


#define COMM_CMD_LAYER 1
#define COMM_CMD_ENABLE 2


void midi_handle_config();
void midi_handle_command(uint8_t cmd);

void midi_secondary_handle_input();

void midi_change_tempo(unsigned long t);

#endif // __MIDI_H__
