#include "midi.h"

#define MIDI_TC_INTERNAL

using namespace midi;

static unsigned long next_tick = 0;

struct global_state gs;
struct layer_state ls[LAYERS];

void midi_change_tempo(unsigned long t)
{
	gs.tempo = t % 1000;
	if (gs.tempo == 0)
		gs.tempo = 120;
	next_tick = micros();
}

void sendMidiLocalCTL(char state)
{
	for (char i = 0; i < LAYERS; i++) {
		MS1.sendControlChange(LocalControl, state ? 127 : 0, i+1);
	}
}

void sendMidiAllOff()
{
	for (char i = 0; i < 16; i++) {
		MS1.sendControlChange(AllSoundOff, 0, i+1);
		MS1.sendControlChange(ResetAllControllers, 0, i+1);
		MS1.sendControlChange(AllNotesOff, 0, i+1);
	}
}

void midi_handle_controller_cmd(int origin, const uint8_t *c, uint16_t len)
{
	static uint8_t s[32] = {0};
	struct layer_state lr;
	uint8_t cmd;
	int i;
	uint8_t l;
	uint8_t rlen = 0;

	if (len < 2)
		return;

	cmd = c[1];

	if (cmd == MIDIBOX_CMD_SET_GLOBAL) {
		if (len < 5 + PEDALS * 2)
			return;

		bool prev_enabled = gs.enabled;

		gs.config = c[2];
		gs.tempo = c[3] | (c[4] << 7);

		if (gs.enabled != prev_enabled)
			sendMidiLocalCTL(!gs.enabled);

		for (i = 0; i < PEDALS; i++) {
			gs.pedal_cc[i] = c[5 + i*2 + 0];
			gs.pedal_mode[i] = c[5 + i*2 + 1];
		}
		midi_change_tempo(gs.tempo);
	} else if (cmd == MIDIBOX_CMD_GET_GLOBAL) {
		s[2] = gs.config;
		s[3] = (gs.tempo >> 0) & 0x7F;
		s[4] = (gs.tempo >> 7) & 0x7F;

		for (i = 0; i < PEDALS; i++) {
			s[5 + i*2 + 0] = gs.pedal_cc[i];
			s[5 + i*2 + 1] = gs.pedal_mode[i];
		}

		rlen = 5 + PEDALS * 2;
	} else if (cmd == MIDIBOX_CMD_SET_LAYER) {
		if (len < 9 + 2*PEDALS)
			return;

		l = c[2];
		lr = ls[l];

		lr.enabled = c[3];
		lr.transposition = c[4] - 0x40;
		lr.lo = c[5];
		lr.hi = c[6];
		lr.mode = c[7];
		lr.transposition_extra = c[8] - 0x40;

		for (i = 0; i < PEDALS; i++) {
			lr.pedal_cc[i] = c[9 + i*2 + 0];
			lr.pedal_mode[i] = c[9 + i*2 + 1];
		}

		ls[l] = lr;
	} else if (cmd == MIDIBOX_CMD_GET_LAYER) {
		if (len < 3)
			return;

		l = c[2];
		lr = ls[l];

		s[2] = l;
		s[3] = lr.enabled;
		s[4] = lr.transposition + 0x40;
		s[5] = lr.lo;
		s[6] = lr.hi;
		s[7] = lr.mode;
		s[8] = lr.transposition_extra + 0x40;

		for (i = 0; i < PEDALS; i++) {
			s[9 + 0 + i*2] = lr.pedal_cc[i];
			s[9 + 1 + i*2] = lr.pedal_mode[i];
		}
		rlen = 10 + PEDALS * 2;
	}

	if (rlen) {
		s[0] = MIDIBOX_SYSEX_ID;
		s[1] = cmd;

		for (i = 0; i < rlen; i++) {
			if (s[i] & 0x80) {
				//Serial.println(String("S1 ERR send pos: ") + i + " val" + s[i]);
				s[i] &= ~0x80;
			}
		}

		if (origin == 0) {
			MU.sendSysEx(rlen, s, false);
		} else if (origin == 1) {
			MB.sendSysEx(rlen, s, false);
		}
	}
}


void handleUsbMidiMessage(const Message<128> & msg)
{
	int i;

	if (msg.type == SystemExclusive) {
		if (msg.sysexArray[1] == MIDIBOX_SYSEX_ID) {
			midi_handle_controller_cmd(0, msg.sysexArray + 1, msg.getSysExSize() - 2);
		} else {
			MS1.send(msg);
		}
	} else {
		switch (msg.type)
		{
		case NoteOff:
		case NoteOn:
		case ControlChange:
		case PitchBend:
		case AfterTouchPoly:
		case AfterTouchChannel:
		case ProgramChange:
			MS1.send(msg);
			break;
		default:
			break;
		}
	}
}

void handleBleMidiMessage(const Message<128> & msg)
{
	int i;

	if (msg.type == SystemExclusive) {
		if (msg.sysexArray[1] == MIDIBOX_SYSEX_ID) {
			midi_handle_controller_cmd(1, msg.sysexArray + 1, msg.getSysExSize() - 2);
		} else {
			MS1.send(msg);
		}
	} else {
		switch (msg.type)
		{
		case NoteOff:
		case NoteOn:
		case ControlChange:
		case PitchBend:
		case AfterTouchPoly:
		case AfterTouchChannel:
		case ProgramChange:
			MS1.send(msg);
			break;
		default:
			break;
		}
	}
}

void layer_handle_note_on_special(struct layer_state & lr, uint8_t lnote, uint8_t vol)
{
	lr.ticks_remains[lnote] = 0;
	lr.last_note = lnote;
	lr.last_note_vol = vol;
#if 0
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
					if (lnote != j) {
						layer_set_playing(lr, j, false, -1);
					}
					MS1.sendNoteOff(j, 0, lchannel);
				}
			}
		}
	}
#endif
}

void handleS1MidiMessage(const midi::Message<128> & msg)
{
	static midi::Message<128> msg_out;

	static unsigned char l;
	static unsigned char data;
	static unsigned char channel;
	static unsigned char cmd;
	static uint16_t vol;

	static unsigned char b1, b2;
	static unsigned char lnote;
	static unsigned char lchannel;

	static unsigned char lmask;
	static bool send, already_sent, note_in_bounds, lenabled;

	if (msg.type == ActiveSensing || msg.type == Clock)
		return;

	channel = msg.channel;
	cmd = msg.type;
	b1 = msg.data1;
	b2 = msg.data2;
	l = msg.length;

	Serial.println(String("S1 MSG: ") + cmd + " len: " + l);

	if (gs.debug_s2u_all) {
		MU.send(msg);
	}

	if (gs.debug_s2b_all || (gs.debug_s2b && (msg.type == 0xF0 || msg.type == 0xf7)))
		MB.send(msg);

	for (l = 0; l < LAYERS; l++) {
		struct layer_state & lr = ls[l];
		lmask = 1 << l;
		lchannel = ((lr.channel_out_offset + l) & 0x0F) + 1;
		lnote = (b1 + lr.transposition + lr.transposition_extra) & 0x7F;
		lenabled = lr.enabled && (lr.channel_in_mask & (1 << (uint16_t) (channel-1)));


		note_in_bounds = (b1 + lr.transposition + lr.transposition_extra) == lnote ? 1 : 0;

		/* NoteOff must be passed even when midibox not enabled */
		if (cmd == midi::NoteOff) {
			/* Original note (before any transposition */
			if (true || lr.note_origin[b1] & 0x80) {
				lnote = lr.note_origin[b1] & 0x7F;
				note_in_bounds = 1;
			}

			if (note_in_bounds && layer_is_playing(lr, lnote)) {
				if (lr.mode & NOTE_MODE_HOLD && lr.ticks_remains[lnote] != 0)
					continue;

				layer_set_playing(lr, lnote, false, b1);
				MS1.sendNoteOff(lnote, b2, lchannel);

				/* FIXME: better handling */
				lr.ticks_remains[lnote] = 0;

				if (lr.mode == NOTE_MODE_SHUFFLE) {
					/* TODO: cancel next note on */
				}
			}
			continue;
		}

		if (!gs.enabled)
			continue;

#if 0
		send = false;
		already_sent = false;
		if (cmd == midi::ControlChange) {
			if (b1 == midi::Sustain && lr.cc_sustain) {
				lr.cc_sustain = b2;
				send = true;
				already_sent = true;
			}

			if ((b1 == midi::Sostenuto && lr.cc_pedal2_mode == PEDAL_MODE_TOGGLE_EN) ||
				(b1 == midi::SoftPedal && lr.cc_pedal3_mode == PEDAL_MODE_TOGGLE_EN)) {
				if (b2 == 0) {
					lr.enabled = lr.status;
				} else if (b2 == 0x7F) {
					lr.enabled = !lr.status;
				}
			}

			if (send) {
				MS1.sendControlChange(lnote, b2, lchannel);
			}
		}
		#endif

		if (!lenabled)
			continue;

		msg_out.type = msg.type;
		msg_out.channel = lchannel;
		msg_out.data1 = msg.data1;
		msg_out.data2 = msg.data2;
		msg_out.valid = msg.valid;
		msg_out.length = msg.length;

		if (cmd == midi::NoteOn) {
			if (note_in_bounds /*&& !layer_is_playing(lr, lnote)*/ && b1 >= lr.lo && b1 <= lr.hi) {
				/* FIXME: Repeat already playing same note for NOTE_MODE_HOLD */
				layer_set_playing(lr, lnote, true, b1);
				layer_handle_note_on_special(lr, lnote, b2);

				vol = b2;
				vol *= lr.volume;

				MS1.sendNoteOn(lnote, vol / 100, lchannel);
			}
#if 0
		} else if (cmd == midi::ControlChange) {
			send = true;
			if (b1 == midi::Sustain) {
				lr.cc_sustain = b2;

				if (lr.cc_pedal1_mode != PEDAL_MODE_NORMAL)
					send = false;
			} else if ((b1 == midi::SoftPedal && lr.cc_pedal3_mode == PEDAL_MODE_NOTELENGTH) ||
					   (b1 == midi::Sostenuto && lr.cc_pedal2_mode == PEDAL_MODE_NOTELENGTH)) {
				lr.cc_expression = b2;

//					if (lr.cc_pedal3_mode != PEDAL_MODE_NORMAL)
					send = false;
			} else if (b1 == midi::Sostenuto) {
				if (lr.cc_pedal2_mode != PEDAL_MODE_NORMAL)
					send = false;
			}
			if (send && !already_sent) {
				MS1.send(msg);
			}
		#endif
		} else if (cmd == midi::SystemExclusive) {
			if (l == 0) {
				/* INFO: copy sysex array if modified */
				//MS1.send(msg);
			}
		} else {
			/* TODO: filter out:
			 * - balance CC
			 */
			MS1.send(msg_out);
		}
	}
}

void midi_loop()
{
	MU.read();
	MB.read();
	MS1.read();
}

void midi_init()
{
	gs.config = 0;
	gs.tempo = 120;

	gs.pedal_cc[0] = Sustain;
	gs.pedal_cc[1] = SoftPedal;
	gs.pedal_cc[2] = Sostenuto;
	gs.pedal_cc[3] = 0;
	gs.pedal_cc[4] = GeneralPurposeController1;
	gs.pedal_cc[5] = GeneralPurposeController2;
	gs.pedal_cc[6] = GeneralPurposeController3;
	gs.pedal_cc[7] = GeneralPurposeController4;

	gs.pedal_mode[0] = PEDAL_MODE_NORMAL;
	gs.pedal_mode[1] = PEDAL_MODE_NORMAL;
	gs.pedal_mode[2] = PEDAL_MODE_NORMAL;
	gs.pedal_mode[3] = PEDAL_MODE_IGNORE;
	gs.pedal_mode[4] = PEDAL_MODE_NORMAL;
	gs.pedal_mode[5] = PEDAL_MODE_NORMAL;
	gs.pedal_mode[6] = PEDAL_MODE_NORMAL;
	gs.pedal_mode[7] = PEDAL_MODE_NORMAL;

	for (uint8_t l = 0; l < LAYERS; l++) {
		ls[l].enabled = 0;
		ls[l].status = ls[l].enabled;
		ls[l].lo = 0;
		ls[l].hi = 127;
		ls[l].channel_in_mask = 0xffff;
		ls[l].channel_out_offset = 0;
		ls[l].transposition = 0;
		ls[l].transposition_extra = 0;
		ls[l].volume = 100;
		ls[l].mode = 0;

		ls[l].pedal_cc[0] = Sustain;
		ls[l].pedal_cc[1] = SoftPedal;
		ls[l].pedal_cc[2] = Sostenuto;
		ls[l].pedal_cc[3] = 0;
		ls[l].pedal_cc[4] = GeneralPurposeController1;
		ls[l].pedal_cc[5] = GeneralPurposeController2;
		ls[l].pedal_cc[6] = GeneralPurposeController3;
		ls[l].pedal_cc[7] = GeneralPurposeController4;

		ls[l].pedal_mode[0] = PEDAL_MODE_NORMAL;
		ls[l].pedal_mode[1] = PEDAL_MODE_NORMAL;
		ls[l].pedal_mode[2] = PEDAL_MODE_NORMAL;
		ls[l].pedal_mode[3] = PEDAL_MODE_IGNORE;
		ls[l].pedal_mode[4] = PEDAL_MODE_NORMAL;
		ls[l].pedal_mode[5] = PEDAL_MODE_NORMAL;
		ls[l].pedal_mode[6] = PEDAL_MODE_NORMAL;
		ls[l].pedal_mode[7] = PEDAL_MODE_NORMAL;

		ls[l].cc_expression = 100;
		ls[l].cc_sustain = 0;

		for (uint8_t j = 0; j < 128/8; j++) {
			ls[l].note[j] = 0;
		}
	}

	next_tick = micros();

	MU.begin(MIDI_CHANNEL_OMNI);
	MU.turnThruOff();
	MU.setHandleMessage(handleUsbMidiMessage);

	MS1.begin(MIDI_CHANNEL_OMNI);
	MS1.turnThruOff();
	MS1.setHandleMessage(handleS1MidiMessage);

	MB.begin(MIDI_CHANNEL_OMNI);
	MB.turnThruOff();
	MB.setHandleMessage(handleBleMidiMessage);
}


#if 0
void midi_handle_tc()
{
	uint8_t l, n;
	gs.mc.tc++;
	if (gs.mc.tc >= 24) {
		gs.mc.tc = 0;
		gs.mc.q++;
		if (gs.mc.q >= 4) {
			gs.mc.q = 0;
			gs.mc.b++;
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
							layer_set_playing(lr, n, false, -1);
							Serial1.write(midi::NoteOff| ((lr.channel_out_offset + l) & 0xF));
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
								layer_set_playing(lr, n+12, true, -1);
								Serial1.write(midi::NoteOn| ((lr.channel_out_offset + l) & 0xF));
								Serial1.write(n+12);
								Serial1.write(lr.last_note_vol);
							}
						}
					}
#if 0
					if (lr.ticks_remains[n] == 0xFF) {
					} else if (lr.ticks_remains[n] == 1) {
						layer_set_playing(lr, n, false);
						Serial1.write(midi::NoteOff | ((lr.channel_out_offset + l) & 0xF));
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
#endif
#if 0
void midi_handle_instrument_cmd(uint8_t cmd, uint8_t b1, uint8_t b2)
{
	uint8_t ch = (cmd & 0x0F) + 1;
	cmd &= 0xF0;

	if (cmd == midi::NoteOff) {
		USBMIDI.sendNoteOff(b1, b2, ch);
	} else if (cmd == midi::NoteOn) {
		USBMIDI.sendNoteOn(b1, b2, ch);
	} else if (cmd == midi::ProgramChange) {
		USBMIDI.sendProgramChange(b1, ch);
	} else if (cmd == midi::ProgramChange) {
		USBMIDI.sendControlChange(b1, b2, ch);
	}
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

	//midi_handle_config();

	while (Serial1.available()) {
		data = Serial1.read();
		cmd = (data & 0xF0);
#if 0
		if (1/*cmd != 240 */) {
			Serial.print("MIDI cmd: "); Serial.print(cmd);
//			Serial.print(" data "); Serial.print(data);
			Serial.println("");
		}

		continue;
#endif

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
			if (data == midi::SystemExclusiveStart) {
				in_sysex = 1;
				sysex_len = 0;
			} else if (data == midi::SystemExclusiveEnd) {
				in_sysex = 0;
				midi_handle_sysex();
			} else if (data == midi::TimeCodeQuarterFrame) {
				while (Serial1.available() == 0);
				b1 = Serial1.read();
			} else if (data == midi::SongPosition) {
				while (Serial1.available() == 0);
				b1 = Serial1.read();
				while (Serial1.available() == 0);
				b2 = Serial1.read();
			} else if (data == midi::SongSelect) {
				while (Serial1.available() == 0);
				b1 = Serial1.read();
			} else if (data >= midi::Clock && data < midi::SystemReset) {
				if (data == midi::Clock) {
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

		if (cmd != midi::ProgramChange && cmd != midi::AfterTouchChannel) {
			while (Serial1.available() == 0);
			b2 = Serial1.read();
		}
		midi_handle_instrument_cmd(cmd, b1, b2);
		//DEBUG_PRINT_MIDI_CMD

		for (l = 0; l < LAYERS; l++) {
			struct layer_state & lr = ls[l];
			lmask = 1 << l;
			lchannel = (lr.channel_out_offset + l) & 0xF;
			lnote = (b1 + lr.transposition) & 0x7F;

			note_in_bounds = (b1 + lr.transposition) == lnote ? 1 : 0;
			//DEBUG_PRINT_LR_STATE

			if (cmd == midi::NoteOff) {
				/* Original note (before any transposition */
				if (true || lr.note_origin[b1] & 0x80) {
					lnote = lr.note_origin[b1] & 0x7F;
					note_in_bounds = 1;
				}

				if (note_in_bounds && layer_is_playing(lr, lnote)) {
					if (lr.mode & NOTE_MODE_HOLD && lr.ticks_remains[lnote] != 0)
						continue;

					layer_set_playing(lr, lnote, false, b1);
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

			if (!gs.enabled)
				continue;

			send = false;
			finalize_sent = false;
			if (cmd == midi::ControlChange) {
				if (b1 == midi::Sustain && lr.cc_damper) {
					lr.cc_damper = b2;
					send = true;
					finalize_sent = true;
				}

				if (
					(b1 == midi::Sostenuto && lr.cc_pedal2_mode == PEDAL_MODE_TOGGLE_EN) ||
					(b1 == midi::SoftPedal && lr.cc_pedal3_mode == PEDAL_MODE_TOGGLE_EN)
				) {
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

			if (cmd == midi::NoteOn) {
				if (note_in_bounds /*&& !layer_is_playing(lr, lnote)*/ && b1 >= lr.lo && b1 <= lr.hi) {
					/* FIXME: Repeat already playing same note for NOTE_MODE_HOLD */
					layer_set_playing(lr, lnote, true, b1);
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
									if (lnote != j) {
										layer_set_playing(lr, j, false, -1);
									}
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
			} else if (cmd == midi::NoteOff) {
				/* Already handled */
				if (note_in_bounds && layer_note[lnote] & lmask) {
					layer_note[lnote] &= ~lmask;
					Serial1.write(cmd | lchannel);
					Serial1.write(lnote);
					Serial1.write(b2);
				}
#endif
			} else if (cmd == midi::ProgramChange || cmd == midi::AfterTouchChannel) {
				Serial1.write(cmd | lchannel);
				Serial1.write(b1);
			} else if (cmd == midi::ControlChange) {
				send = true;
				if (b1 == midi::Sustain) {
					lr.cc_damper = b2;

					if (lr.cc_pedal1_mode != PEDAL_MODE_NORMAL)
						send = false;
				} else if ((b1 == midi::SoftPedal && lr.cc_pedal3_mode == PEDAL_MODE_NOTELENGTH) ||
				           (b1 == midi::Sostenuto && lr.cc_pedal2_mode == PEDAL_MODE_NOTELENGTH)) {
					lr.cc_expression = b2;

//					if (lr.cc_pedal3_mode != PEDAL_MODE_NORMAL)
						send = false;
				} else if (b1 == midi::Sostenuto) {
					if (lr.cc_pedal2_mode != PEDAL_MODE_NORMAL)
						send = false;
				}
				if (send && !finalize_sent) {
					Serial1.write(cmd | lchannel);
					Serial1.write(b1);
					Serial1.write(b2);
				}
			} else if (cmd == midi::AfterTouchPoly || cmd == midi::PitchBend) {
				Serial1.write(cmd | lchannel);
				Serial1.write(b1);
				Serial1.write(b2);
			}
		}
	}
}
#endif
