#include "midibox.h"
#include "midi.h"
#include <stdio.h>

uint8_t sysex_p []         = {0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00, MIDI_SYSEX_END};
uint8_t sysex_ep[]         = {0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02, MIDI_SYSEX_END};
uint8_t sysex_hammond []   = {0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F, MIDI_SYSEX_END};
uint8_t sysex_bass[]       = {0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04, MIDI_SYSEX_END};

struct midi_program_t midi_programs[] = {
	{"Piano",       "Pn",  1,  0, 68, sysex_p},
	{"ePiano",      "eP",  5,  0, 67, sysex_ep},
	{"Hammond",     "Hm", 17, 32, 68, sysex_hammond},
	{"Bass",        "Bs", 33,  0, 71, sysex_bass},
	{"Fretless b.", "FB", 36,  0,  0, sysex_bass},
	{"Vibraphone",  "Vb", 12,  0,  0, sysex_hammond},
	{NULL},
};

enum PGMS {PGM_PNO = 0, PGM_EPNO, PGM_HAMMOND, PGM_BASS, PGM_FRETLETTBASS, PGM_VIBRAPHONE};

inline static void set_program(uint8_t l, int pgm_index)
{
	comm_1to2.layer.state = ls[l];
	comm_1to2.layer.index = l;
	comm_1to2.layer.state.program_index = pgm_index;
	process_gui_cmd_send_to_midi(COMM_CMD_LAYER);
}

extern volatile unsigned long tempo;

void midi_layers_load_quick_setting(uint8_t qs)
{
	uint8_t i;

	for (i = 0; i < LAYERS; i++) {
		ls[i].enabled = 0;

		ls[i].lo = 0;
		ls[i].hi = 127;
		ls[i].cc_pedal1_mode = PEDAL_MODE_NORMAL;
		ls[i].cc_pedal2_mode = PEDAL_MODE_NORMAL;
		ls[i].cc_pedal3_mode = PEDAL_MODE_IGNORE;
		ls[i].mode = NOTE_MODE_NORMAL;
	}

	switch (qs) {
		case 1:
			/* Pno only */
			ls[1].enabled = 1;
			ls[1].transposition = 0;
			ls[1].hi = 127;
			ls[1].lo = 0;
			set_program(1, PGM_PNO);
			break;
		case 2:
			/* Pno + bass */
			ls[1].enabled = 1;
			ls[2].enabled = 1;
			ls[1].transposition = 0;
			ls[2].transposition = 0;
			ls[1].lo = 54;
			ls[2].hi = 53;
			set_program(1, PGM_PNO);
			set_program(2, PGM_BASS);

			ls[0].cc_pedal2_mode = PEDAL_MODE_TOGGLE_EN;
			ls[2].cc_pedal2_mode = PEDAL_MODE_TOGGLE_EN;
			ls[0].hi = 53;
			set_program(0, PGM_EPNO);
			ls[0].transposition = 12;
			break;
		case 3:
			/* Pno 8va + bass */
			ls[1].enabled = 1;
			ls[2].enabled = 1;
			ls[1].transposition = -12;
			ls[2].transposition = 0;
			ls[1].lo = 54;
			ls[2].hi = 53;
			set_program(1, PGM_PNO);
			set_program(2, PGM_BASS);
			break;

		case 8:
			tempo = 200;

			/* Pno + pno*/
			ls[1].enabled = 1;
			ls[2].enabled = 1;
			ls[3].enabled = 0;
			ls[1].transposition = 0;
			ls[2].transposition = 0;
			ls[3].transposition = 0;
			ls[1].lo = 54;
			ls[2].hi = 53;
			ls[3].hi = 53;

			ls[1].cc_pedal2_mode = PEDAL_MODE_IGNORE;
			ls[2].cc_pedal2_mode = PEDAL_MODE_TOGGLE_EN;
			ls[3].cc_pedal1_mode = PEDAL_MODE_IGNORE;
			ls[3].cc_pedal3_mode = PEDAL_MODE_NOTELENGTH; /* Swing for NOTE_MODE_SHUFFLE */
			ls[3].cc_pedal2_mode = PEDAL_MODE_TOGGLE_EN;

			ls[3].mode = NOTE_MODE_SHUFFLE;

			set_program(0, PGM_PNO);
			set_program(1, PGM_PNO);
			set_program(2, PGM_PNO);
			break;

		case 9:
			/* Pno + pno*/
			ls[1].enabled = 1;
			ls[2].enabled = 1;
			ls[1].transposition = 0;
			ls[2].transposition = 0;
			ls[1].lo = 54;
			ls[2].hi = 53;

			ls[1].lo = 54-5;
			ls[2].hi = 53-5;

			ls[1].cc_pedal3_mode = PEDAL_MODE_IGNORE;
			ls[2].cc_pedal3_mode = PEDAL_MODE_NOTELENGTH;

			ls[2].mode = NOTE_MODE_CUT1_4;
			ls[2].mode = NOTE_MODE_HOLD1_2;
			set_program(1, PGM_PNO);
			set_program(2, PGM_PNO);
			break;
	}

	for (i = 0; i < LAYERS; i++) {
		ls[i].status = ls[i].enabled;
	}
}
