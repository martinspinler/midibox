#include "midibox.h"
#include "midi.h"

#define MIDI_TC_INTERNAL

struct layer_state ls[LAYERS];

extern uint8_t layer_sel;

char sysex_len;
unsigned char sysex_data[32];

char config_enable = 0;

struct core_comm comm_1to2;
struct core_comm comm_2to1;


struct midi_clock mc;

static unsigned long next_tick = 0;
volatile unsigned long tempo = 120;

void midi_change_tempo(unsigned long t)
{
	tempo = t % 1000;
	if (tempo == 0)
		tempo = 120;
	next_tick = micros();
}

inline bool layer_is_playing(struct layer_state & ls, uint8_t note)
{
	return ls.note[note >> 3] & (1 << (note & 0x7));
}

inline void layer_set_playing(struct layer_state & ls, uint8_t note, bool playing)
{
	if (playing)
		ls.note[note >> 3] |=  (1 << (note & 0x7));
	else
		ls.note[note >> 3] &= ~(1 << (note & 0x7));
}

void midi_init()
{
	Serial1.begin(31250);

	for (uint8_t l = 0; l < LAYERS; l++) {
		ls[l].enabled = 0;
		ls[l].status = ls[l].enabled;
		ls[l].lo = 0;
		ls[l].hi = 127;
		ls[l].channel_in_mask = 0xffff;
		ls[l].channel_out_offset = 0;
		ls[l].transposition = 0;
		ls[l].volume = 100;

		ls[l].cc_expression = 100;

		for (uint8_t j = 0; j < 128/8; j++) {
			ls[l].note[j] = 0;
		}
	}

	ls[1].enabled = 1;
	ls[1].status = ls[1].enabled;

	next_tick = micros();
}

void sendMidiLocalCTL(char state)
{
	/* Local CTL = off*/
	for (char i = 0; i < LAYERS; i++) {
		Serial1.write(MIDI_CONTROL_CHANGE + i);
		Serial1.write(122);
		Serial1.write(state ? 127 : 0);
	}
}

void sendMidiAllOff()
{
	/* Send: All Sounds Off, Reset All Controllers, All Notes Off */
	for (char i = 0; i < 16; i++) {
		Serial1.write((uint8_t)MIDI_CONTROL_CHANGE + i);
		Serial1.write((uint8_t)120);
		Serial1.write((uint8_t)0);

		Serial1.write((uint8_t)MIDI_CONTROL_CHANGE + i);
		Serial1.write((uint8_t)121);
		Serial1.write((uint8_t)0);

		Serial1.write((uint8_t)MIDI_CONTROL_CHANGE + i);
		Serial1.write((uint8_t)123);
		Serial1.write((uint8_t)0);
	}
}

void sendMidiControlChange(char channel, char cc, char value)
{
	Serial1.write(MIDI_CONTROL_CHANGE | channel);
	Serial1.write(cc);
	Serial1.write(value);
}

void sendMidiProgramChange(char channel, char program)
{
	Serial1.write(MIDI_PROGRAM_CHANGE | channel);
	Serial1.write(program);
}

static unsigned char roland_sysex_crc;

void roland_sysex_begin()
{
	static char roland_sysex_header[4] = {0x41, 0x10, 0x42, 0x12};
	unsigned char i;

	roland_sysex_crc = 0;

	Serial1.write(0xF0);

	for (i = 0; i < 4; i++) {
		Serial1.write(roland_sysex_header[i]);
	}
}

void roland_sysex_xmit(unsigned char byte)
{
	Serial1.write(byte);
	roland_sysex_crc += byte;
}

void roland_sysex_end()
{
	Serial1.write(128 - (roland_sysex_crc & 0x7F));
	Serial1.write(0xF7);
}

void setProgram(char channel, char program)
{
	struct midi_program_t *pgm = &midi_programs[program];
	uint8_t i, j;


	sendMidiControlChange(channel, MIDI_CC_BANK_SELECT, pgm->ccm);
	sendMidiControlChange(channel, MIDI_CC_BANK_SELECT + MIDI_CC_LSB_OFFSET, pgm->ccl);
	sendMidiProgramChange(channel, pgm->program - 1);

	for (i = 0, j = 0; pgm->sysex[i] != 0xF7; i++) {
		if (pgm->sysex[i] == 0xF0 && j != 0) { /* j == 0 should not occur */
			roland_sysex_end();
			j = 0;
			continue;
		}
		if (j == 0) {
			roland_sysex_begin();
		}

		if (j == 1) {
			roland_sysex_xmit(0x40 | (channel + 1));
		} else {
			roland_sysex_xmit(pgm->sysex[i]);
		}
		j++;
	}
	if (j)
		roland_sysex_end();
}

void sendRolandSysex(const unsigned char * data, unsigned char length)
{
	static char roland_sysex_header[4] = {0x41, 0x10, 0x42, 0x12};

	unsigned char crc = 0;
	unsigned char i;

	Serial1.write(0xF0);

	for (i = 0; i < 4; i++) {
		Serial1.write(roland_sysex_header[i]);
	}

	for (i = 0; i < length; i++) {
		Serial1.write(data[i]);
		crc += data[i];
	}

	Serial1.write(128 - (crc & 0x7F));
	Serial1.write(0xF7);
}

void midi_handle_sysex()
{
	unsigned char *data = sysex_data;
	char part;

	if (sysex_len < 2)
		return;

	if (
			data[0] == 0x41 && /* ID number (Roland) */
#if 0
			data[1] == 0x10 && /* Device ID */
#endif
			data[2] == 0x42 && /* Model ID */
			data[3] == 0x12 /* Command ID (DT1) */
	   ) {
		if (sysex_len < 8)
			return;
		if (data[4] == 0x40) {
			if (data[5] & 0xF0 == 0) {
				/* System parameters */
			} else {
				/* Part parameters */
				/* Transmit for selected channel from gui */
				if (config_enable == 1 /*&& config_mode == MODE_NORMAL*/) {
					data[5] &= 0x0F;
					data[5] |= layer_sel + 1;
				}
				sendRolandSysex(data + 4, sysex_len - 4 - 1);
			}
		}
	}
}

void midi_handle_config()
{
	uint8_t cmd;

	while (process_midi_cmd_available()) {
		cmd = process_midi_cmd_get();
		midi_handle_command(cmd);
		process_midi_cmd_done();
	}
}

void sendRolandSysex(const unsigned char * data, unsigned char length);

void midi_layer_transpose(unsigned char l, signed char transposition)
{
	signed char offset = transposition - ls[l].transposition;
	unsigned char i;

	unsigned char lmask = 1 << l;
	unsigned char lchannel = (ls[l].channel_out_offset + l) & 0xF;

	if (offset < 0) {
		/* INFO: overflow */
		for (i = 127; i < 128; i--) {
			if (layer_is_playing(ls[l], i)) {
				layer_set_playing(ls[l], i, false);
				if (i - ((unsigned)offset) < 128) {
					layer_set_playing(ls[l], i - offset, true);
				} else {
					Serial1.write(MIDI_NOTE_OFF | lchannel);
					Serial1.write(i);
					Serial1.write((unsigned char)0);
				}
			}
		}
	} else if (offset > 0) {
		for (i = 0; i < 128; i++) {
			if (layer_is_playing(ls[l], i)) {
				layer_set_playing(ls[l], i, false);
				if (i >= offset) {
					layer_set_playing(ls[l], i - offset, true);
				} else {
					Serial1.write(MIDI_NOTE_OFF | lchannel);
					Serial1.write(i);
					Serial1.write((unsigned char)0);
				}
			}
		}
	}
}

void midi_handle_command(uint8_t cmd)
{
	if (cmd == COMM_CMD_LAYER) {
		if (config_enable) {
			uint8_t l = comm_1to2.layer.index;
			if (comm_1to2.layer.state.program_index != ls[l].program_index) {
				setProgram((comm_1to2.layer.state.channel_out_offset + l), comm_1to2.layer.state.program_index);
//TODO:
//				sendRolandSysex()
			}
			if (comm_1to2.layer.state.transposition != ls[l].transposition) {
				midi_layer_transpose(l, comm_1to2.layer.state.transposition);
			}

			ls[l] = comm_1to2.layer.state;
		}
	} else if (cmd == COMM_CMD_ENABLE) {
		if (config_enable != comm_1to2.enable) {
			config_enable = comm_1to2.enable;
			sendMidiLocalCTL(!config_enable);
		}
	}
}

void midi_handle_tc()
{
	uint8_t l, n;
	mc.tc++;
	if (mc.tc >= 24) {
		mc.tc = 0;
		mc.q++;
		if (mc.q >= 4) {
			mc.q = 0;
			mc.b++;
		}
	}

	for (l = 0; l < LAYERS; l++) {
		struct layer_state & lr = ls[l];
		if (
				lr.mode == NOTE_MODE_HOLDTONEXT ||
				lr.mode == NOTE_MODE_HOLD1_4 ||
				lr.mode == NOTE_MODE_HOLD1_2 ||
				lr.mode == NOTE_MODE_CUT1_4  ||
				lr.mode == NOTE_MODE_SHUFFLE) {
			for (n = 0; n < 128; n++) {
				if (layer_is_playing(lr, n)) {
					if (lr.ticks_remains[n] > 0) {
						lr.ticks_remains[n]--;
						if (lr.ticks_remains[n] == 0) {
							layer_set_playing(lr, n, false);
							Serial1.write(MIDI_NOTE_OFF | ((lr.channel_out_offset + l) & 0xF));
							Serial1.write(n);
							Serial1.write((uint8_t)0);
							if (lr.mode == NOTE_MODE_SHUFFLE && n == lr.last_note) {
							/* FIXME: check bounds */
								uint16_t v = lr.cc_expression;
								uint16_t vol = lr.last_note_vol;
								vol *= vol * 16 / 12;
								vol = vol > 127 ? 127 : vol;

//								lr.ticks_remains[n+12] = v / 8;
								lr.ticks_remains[n+12] = 20 - v * 15 / 127;
								layer_set_playing(lr, n+12, true);
								Serial1.write(MIDI_NOTE_ON | ((lr.channel_out_offset + l) & 0xF));
								Serial1.write(n+12);
								Serial1.write(lr.last_note_vol);
							}
						}
					}
#if 0
					if (lr.ticks_remains[n] == 0xFF) {
					} else if (lr.ticks_remains[n] == 1) {
						layer_set_playing(lr, n, false);
						Serial1.write(MIDI_NOTE_OFF | ((lr.channel_out_offset + l) & 0xF));
						Serial1.write(n);
						Serial1.write(0);

						lr.ticks_remains[n]--;
					} else if (lr.ticks_remains[n] != 0) {
						lr.ticks_remains[n]--;
					}
#endif
				}
			}
		}
	}
}

void midi_handle_cmd(uint8_t cmd, uint8_t b1, uint8_t b2)
{
}

void midi_loop()
{
	static char in_sysex = 0;

	static unsigned char l;
	static unsigned char data;
	static unsigned char channel;
	static unsigned char cmd;

	static unsigned char b1, b2;
	static unsigned char lnote;
	static unsigned char lchannel;

	static unsigned char lmask;
	static bool send, finalize_sent, note_in_bounds;

#ifdef MIDI_TC_INTERNAL
	static unsigned long us;

	us = micros();
	if (us > next_tick) {
		next_tick = us + 1000000 / (tempo * 24 / 60);
		midi_handle_tc();
	}
#endif

	midi_handle_config();

	while (Serial1.available()) {
		data = Serial1.read();
		cmd = (data & 0xF0);

		/* Not status byte? Not in sync */
		if ((data & 0x80) == 0) {
			if (in_sysex == 1) {
				/* Store SysEx */
				if (sysex_len < sizeof(sysex_data)) {
					sysex_data[sysex_len] = data;
					sysex_len++;
				} else {
					/* Max size overflowed */
					in_sysex = 0;
				}
			} else {
				/* Error in SysEx */
				in_sysex = 0;
			}
			continue;
		}

		/* System Common Messages */
		if (cmd == 0xF0) {
			/* System Exclusive */
			if (data == 0xF0) {
				in_sysex = 1;
				sysex_len = 0;
				/* End of Exclusive */
			} else if (data == 0xF7) {
				in_sysex = 0;
				/* Handle stored SysEx */
				midi_handle_sysex();
				/* MIDI Time Code Quarter Frame */
			} else if (data == 0xF1) {
				while (Serial1.available() == 0);
				b1 = Serial1.read();
				/* Song Position Pointer */
			} else if (data == 0xF2) {
				while (Serial1.available() == 0);
				b1 = Serial1.read();
				while (Serial1.available() == 0);
				b2 = Serial1.read();
				/* Song Select */
			} else if (data == 0xF2) {
				while (Serial1.available() == 0);
				b1 = Serial1.read();
				/* System Real-Time Messages */
			} else if (data >= 0xF8 && data < 0xFF) {
				/* Timing clock*/
				if (data == 0xF8) {
				#ifndef MIDI_TC_INTERNAL
					midi_handle_tc();
				#endif
				}
			}
			continue;
		}

		channel = data & 0x0F;

		while (Serial1.available() == 0);
		b1 = Serial1.read();

		if (cmd != MIDI_PROGRAM_CHANGE && cmd != MIDI_CHANNEL_PRESSURE) {
			while (Serial1.available() == 0);
			b2 = Serial1.read();
		}
		midi_handle_cmd(cmd, b1, b2);

		for (l = 0; l < LAYERS; l++) {
			struct layer_state & lr = ls[l];
			lmask = 1 << l;
			lchannel = (lr.channel_out_offset + l) & 0xF;
			lnote = (b1 + lr.transposition) & 0x7F;

			note_in_bounds = (b1 + lr.transposition) == lnote ? 1 : 0;

			if (cmd == MIDI_NOTE_OFF) {
				if (note_in_bounds && layer_is_playing(lr, lnote)) {
					if (lr.mode & NOTE_MODE_HOLD && lr.ticks_remains[lnote] != 0)
						continue;

					layer_set_playing(lr, lnote, false);
					Serial1.write(cmd | lchannel);
					Serial1.write(lnote);
					Serial1.write(b2);

					/* FIXME: better handling */
					lr.ticks_remains[lnote] = 0;

					if (lr.mode == NOTE_MODE_SHUFFLE) {
						/* TODO: cancel next note on */
					}
				}
				continue;
			}

			if (!config_enable)
				continue;

			send = false;
			finalize_sent = false;
			if (cmd == MIDI_CONTROL_CHANGE) {
				if (b1 == MIDI_CC_P_HOLD && lr.cc_damper) {
					lr.cc_damper = b2;
					send = true;
					finalize_sent = true;
				}

				if ((b1 == MIDI_CC_P_SOSTENUTO && lr.cc_pedal2_mode == PEDAL_MODE_TOGGLE_EN) ||
				    (b1 == MIDI_CC_P_SOFT      && lr.cc_pedal3_mode == PEDAL_MODE_TOGGLE_EN)) {
					if (b2 == 0) {
						lr.enabled = lr.status;
					} else if (b2 == 0x7F) {
						lr.enabled = !lr.status;
					}
				}

				if (send) {
					Serial1.write(cmd | lchannel);
					Serial1.write(b1);
					Serial1.write(b2);
				}
			}

			if (!(lr.enabled) || !(lr.channel_in_mask & (1 << (uint16_t) channel)))
				continue;

			if (cmd == MIDI_NOTE_ON) {
				/* FIXME: no lnote for range, but b1 */
				if (note_in_bounds /*&& !layer_is_playing(lr, lnote)*/ && b1 >= lr.lo && b1 <= lr.hi) {
					/* FIXME: Repeat already playing same note for NOTE_MODE_HOLD */
					layer_set_playing(lr, lnote, true);
					lr.ticks_remains[lnote] = 0;
					lr.last_note = lnote;
					lr.last_note_vol = b2;

					if (lr.cc_pedal3_mode == PEDAL_MODE_NOTELENGTH) {
						if (true || lr.cc_expression < 127) {
							uint16_t v = lr.cc_expression;
							if (lr.mode == NOTE_MODE_HOLD1_4 || lr.mode == NOTE_MODE_CUT1_4) {
								lr.ticks_remains[lnote] = v / 4;
							} else if (lr.mode == NOTE_MODE_HOLD1_2) {
								lr.ticks_remains[lnote] = v / 2;
							} else if (lr.mode == NOTE_MODE_SHUFFLE) {
								lr.ticks_remains[lnote] = v / 8;
								lr.ticks_remains[lnote] = 4 + v * 15 / 127;
							}

							/* HOLD TO NEXT */
							for (int j = 0; j < 128; j++) {
								/* FIXME: Repeat already playing same note for NOTE_MODE_HOLD??? */
								if (/*lnote != j &&*/ layer_is_playing(lr, j)) {
									if (lnote != j)
										layer_set_playing(lr, j, false);
									Serial1.write(cmd | lchannel);
									Serial1.write(j);
									Serial1.write((unsigned char)0);
								}
							}
						}
					}

					uint16_t vol = b2;
					vol *= lr.volume;
					Serial1.write(cmd | lchannel);
					Serial1.write(lnote);
					Serial1.write(vol / 100);
				}
#if 0
			} else if (cmd == MIDI_NOTE_OFF) {
				/* Already handled */
				if (note_in_bounds && layer_note[lnote] & lmask) {
					layer_note[lnote] &= ~lmask;
					Serial1.write(cmd | lchannel);
					Serial1.write(lnote);
					Serial1.write(b2);
				}
#endif
			} else if (cmd == MIDI_PROGRAM_CHANGE || cmd == MIDI_CHANNEL_PRESSURE) {
				Serial1.write(cmd | lchannel);
				Serial1.write(b1);
			} else if (cmd == MIDI_CONTROL_CHANGE) {
				send = true;
				if (b1 == MIDI_CC_P_HOLD) {
					lr.cc_damper = b2;

					if (lr.cc_pedal1_mode != PEDAL_MODE_NORMAL)
						send = false;
				} else if ((b1 == MIDI_CC_P_SOFT && lr.cc_pedal3_mode == PEDAL_MODE_NOTELENGTH) ||
				           (b1 == MIDI_CC_P_SOSTENUTO && lr.cc_pedal2_mode == PEDAL_MODE_NOTELENGTH)) {
					lr.cc_expression = b2;

//					if (lr.cc_pedal3_mode != PEDAL_MODE_NORMAL)
						send = false;
				} else if (b1 == MIDI_CC_P_SOSTENUTO) {
					if (lr.cc_pedal2_mode != PEDAL_MODE_NORMAL)
						send = false;
				}
				if (send && !finalize_sent) {
					Serial1.write(cmd | lchannel);
					Serial1.write(b1);
					Serial1.write(b2);
				}
			} else if (cmd == MIDI_POLYPHONIC_AFTERTOUCH || cmd == MIDI_PITCH_WHEEL_CHANGE) {
				Serial1.write(cmd | lchannel);
				Serial1.write(b1);
				Serial1.write(b2);
			}
		}
	}
}
