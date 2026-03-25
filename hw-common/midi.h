#ifndef __MIDI_H__
#define __MIDI_H__

#include <MIDI.h>

#ifdef ARDUINO
#include "midibox-compat.h"
#else
#include <midibox-compat.h>
#endif

#include "api.h"

enum {
	CC_INT_SUSTAIN = 0,
	CC_INT_SOSTENUTO,
	CC_INT_SOFT,

	CC_INT_COUNT,
};

struct layer_state {
	struct layer_state_reg r;

	uint8_t index;
	int8_t  transposition;
	int8_t  transposition_extra;
	uint8_t cc_mode[CC_INT_COUNT];
	uint8_t cc_val[CC_INT_COUNT];
	uint8_t part; /* Maybe RO */
	uint8_t channel; /* 1..16, Maybe RO */
	uint8_t channel_out_offset;
	uint16_t channel_in_mask;
	uint8_t last_note_vol;
	uint8_t last_note;
	int8_t note_length_mod;

#if 0
	int8_t release;
	int8_t attack;
	int8_t cutoff;
	int8_t decay;
#endif

//	uint8_t status;
	uint8_t note[128/8];

	uint8_t ticks_remains[128];
	uint8_t note_origin[128];
};

struct midi_clock {
	uint16_t b;
	uint8_t q;
	uint8_t tc;
};

struct global_state {
	struct global_state_reg r;

	/* Not paged values */
	unsigned long tempo;
	struct midi_clock mc;
	uint8_t init_delay;
};

extern struct layer_state ls[LAYERS];
extern struct global_state gs;


void smidi_init();
void midi_init();
void midi_send_init();
void midi_loop();
void midi_handle_config();
void midi_handle_instrument_cmd(uint8_t cmd);
void midi_handle_controller_cmd(int origin, const uint8_t *cmd, uint16_t len);
void midi_handle_pedal_input(uint8_t pedal, uint8_t val);

void midi_piano_connect();

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
