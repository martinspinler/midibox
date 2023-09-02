#ifndef __MIDI_H__
#define __MIDI_H__

#ifdef ARDUINO_Seeed_XIAO_nRF52840
#define MIDIBOX_HAVE_BT
#else
#endif

#include <MIDI.h>

#ifdef ARDUINO
#include "midibox-compat.h"
#else
#include <midibox-compat.h>
#endif

#ifdef MIDIBOX_HAVE_BT
extern MidiInterfaceUsb MU;
extern MidiInterfaceHwserial MS1;
extern MidiInterfaceBle MB;
#else
extern MidiInterfaceHwserial MS1;
extern MidiInterfaceHwserial MS2;
#endif

#include "api.h"


struct layer_state {
	struct layer_state_reg r;

	struct {
		uint8_t active: 1;
		uint8_t activate: 1;
	};
	int8_t  transposition;
	int8_t  transposition_extra;
	uint8_t cc_sustain;
	uint8_t cc_expression;
	uint8_t part; /* Maybe RO */
	uint8_t channel; /* 1..16, Maybe RO */
	uint8_t channel_out_offset;
	uint16_t channel_in_mask;
	uint8_t last_note_vol;
	uint8_t last_note;

#if 0
	int8_t release;
	int8_t attack;
	int8_t cutoff;
	int8_t decay;
#endif

#if 0
	uint8_t cc_pedal1_mode; /* ignore, normal, bass... */
	uint8_t cc_pedal2_mode;
	uint8_t cc_pedal3_mode;
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
};

extern struct layer_state ls[LAYERS];
extern struct global_state gs;


void smidi_init();
void midi_init();
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
