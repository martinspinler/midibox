#include <stddef.h>
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

static const char roland_sysex_header[4] = {0x41, 0x10, 0x42, 0x12};

/* data is without 0xF0 / 0xF7 */
int8_t roland_sysex_begin(unsigned char * data)
{
	uint8_t i = sizeof(roland_sysex_header);
	memcpy(data, roland_sysex_header, i);
	return i;
}

/* length is only for the user part */
int8_t roland_sysex_finish(unsigned char * data, uint8_t length)
{
	const uint8_t o = sizeof(roland_sysex_header);
	uint8_t i;

	unsigned char crc = 0;

	for (i = 0; i < length; i++) {
		crc += data[o + i];
	}

	data[o + i] = 128 - (crc & 0x7F);
	return o + i + 1;
}

void layer2reg(struct layer_state &lr)
{
	lr.r.transposition = lr.transposition + 0x40;
	lr.r.transposition_extra = lr.transposition_extra + 0x40;
#if 0
	lr.r.release = lr.release + 0x40;
	lr.r.attack = lr.attack + 0x40;
	lr.r.cutoff = lr.cutoff + 0x40;
	lr.r.decay = lr.decay + 0x40;
#endif
}

void reg2layer(struct layer_state &lr)
{
	lr.transposition = lr.r.transposition - 0x40;
	lr.transposition_extra = lr.r.transposition_extra - 0x40;
#if 0
	lr.release = lr.r.release - 0x40;
	lr.attack = lr.r.attack - 0x40;
	lr.cutoff = lr.r.cutoff - 0x40;
	lr.decay = lr.r.decay - 0x40;
#endif
}

void gs2reg(struct global_state &gs)
{
	gs.r.tempo_lsb = (gs.tempo >> 0) & 0x7F;
	gs.r.tempo_msb = (gs.tempo >> 7) & 0x7F;
}

void reg2gs(struct global_state &gs)
{
	gs.tempo  = gs.r.tempo_lsb << 0;
	gs.tempo |= gs.r.tempo_msb << 7;
}

void midi_handle_pedal_input(uint8_t pedal, uint8_t val)
{
	uint8_t i;
	uint8_t cmd, cc, pm;

	if (pedal >= 8)
		return;

	if (gs.r.pedal_mode[pedal] == PEDAL_MODE_NORMAL) {
		MU.sendControlChange(gs.r.pedal_cc[pedal], val, 1);
		MB.sendControlChange(gs.r.pedal_cc[pedal], val, 1);
	}

	for (i = 0; i < LAYERS; i++) {
		struct layer_state & lr = ls[i];

		cc = lr.r.pedal_cc[pedal];
		pm = lr.r.pedal_mode[pedal];
		if (pm == PEDAL_MODE_NORMAL) {
			MS1.sendControlChange(cc, val, i + 1);
		} else if (pm == PEDAL_MODE_TOGGLE_ACT) {
			/* FIXME */
			if (val == 0) {
				lr.activate = 0;
				//lr.r.enabled = lr.status;
			} else if (val == 0x7F) {
				lr.activate = 1;
				//lr.r.enabled = !lr.status;
			}
		}
	}
}

void midi_handle_controller_cmd(int origin, const uint8_t *c, uint16_t len)
{
	static struct layer_state lr_prev;
	static struct global_state gs_prev;
	static uint8_t sysex[32];

	uint8_t * s = sysex;
	uint8_t cmd;
	int i;
	uint8_t layer;
	uint8_t offset;
	uint8_t reqlen;
	uint8_t reslen = 0;
	uint8_t rescmd = 0;

	struct {
		int gs_enabled : 1;
		int gs_tempo : 1;
		int program : 1;
		int volume: 1;
		int all : 1;
#if 0
		int part: 1;
#endif
	} changes = {0};

	if (len < 4)
		return;

	cmd = (c[1] >> 4) & 0x07;
	layer = c[1] & 0x0F;
	offset = c[2];
	reqlen = c[3];

	c += 4;
	s += 4;
	len -= 4;

	if (cmd == MIDIBOX_CMD_WRITE_REQ && layer == 15) {
		if (reqlen != len || offset + reqlen > sizeof(gs.r))
			return;

		gs_prev = gs;

		memcpy(&gs.r + offset, c, len);

		gs.tempo = gs.r.tempo_msb << 7 + gs.r.tempo_lsb;

		if (gs.r.init) {
			gs.r.init = 0;
			changes.gs_enabled = 1;
			changes.gs_tempo = 1;
		}

		if (gs.r.enabled != gs_prev.r.enabled)
			changes.gs_enabled = 1;
		if (gs.tempo != gs_prev.tempo)
			changes.gs_tempo = 1;

		if (changes.gs_enabled)
			sendMidiLocalCTL(!gs.r.enabled);
		if (changes.gs_tempo)
			midi_change_tempo(gs.tempo);

	} else if (cmd == MIDIBOX_CMD_READ_REQ && layer == 15) {
		if (offset + reqlen > sizeof(gs.r))
			return;

		memcpy(s, &gs.r + offset, reqlen);
		reslen = reqlen;
		rescmd = MIDIBOX_CMD_READ_RES;
	} else if (cmd == MIDIBOX_CMD_WRITE_REQ && layer < LAYERS) {
		struct layer_state & lr = ls[layer];

		if (reqlen != len || offset + reqlen > sizeof(lr.r))
			return;

		lr_prev = ls[layer];

		memcpy(&lr.r + offset, c, reqlen);

		reg2layer(lr);

		if (lr.r.init) {
			lr.r.init = 0;
			changes.all = 1;
		}

		if (lr_prev.r.bs != lr.r.bs || lr_prev.r.bs_lsb != lr.r.bs_lsb || lr_prev.r.pgm != lr.r.pgm)
			changes.program = 1;

		if (lr_prev.r.volume != lr.r.volume)
			changes.volume = 1;

#if 0
		if (lr_prev.part != lr.part) {
			changes.program = 1;
			changes.volume = 1;
			changes.part = 1;
		}
#endif

		if (changes.program || changes.all) {
			MS1.sendControlChange(BankSelect, lr.r.bs, lr.channel);
			MS1.sendControlChange(BankSelectLSB, lr.r.bs_lsb, lr.channel);
			MS1.sendProgramChange(lr.r.pgm, lr.channel);
		}
#if 1
		if (lr_prev.r.release != lr.r.release || changes.all)
			MS1.sendControlChange(72, lr.r.release, lr.channel);

		if (lr_prev.r.attack != lr.r.attack || changes.all)
			MS1.sendControlChange(73, lr.r.attack, lr.channel);

		if (lr_prev.r.cutoff != lr.r.cutoff || changes.all)
			MS1.sendControlChange(74, lr.r.cutoff, lr.channel);

		if (lr_prev.r.decay != lr.r.decay || changes.all)
			MS1.sendControlChange(75, lr.r.decay, lr.channel);
#endif
		if (changes.volume || changes.all) {
			i = roland_sysex_begin(sysex);
			sysex[i+0] = 0x40;
			sysex[i+1] = 0x10 | lr.part;
			sysex[i+2] = 0x19;
			sysex[i+3] = lr.r.volume;
			reslen = roland_sysex_finish(sysex, 3+1);
			MS1.sendSysEx(reslen, sysex, false);

			reslen = 0;
		}
	} else if (cmd == MIDIBOX_CMD_READ_REQ && layer < LAYERS) {
		struct layer_state & lr = ls[layer];

		if (offset + reqlen > sizeof(lr.r))
			return;

		memcpy(s, &lr.r + offset, reqlen);
		reslen = reqlen;
		rescmd = MIDIBOX_CMD_READ_RES;
	}

	if (reslen) {
		sysex[0] = MIDIBOX_SYSEX_ID;
		sysex[1] = ((rescmd & 0x07) << 4) | (layer & 0x0F);
		sysex[2] = offset;
		sysex[3] = reslen;

		reslen += 4;

		for (i = 0; i < reslen; i++) {
			if (sysex[i] & 0x80) {
				//Serial.println(String("S1 ERR send pos: ") + i + " val" + s[i]);
				sysex[i] &= ~0x80;
			}
		}

		if (origin == 0) {
			MU.sendSysEx(reslen, sysex, false);
		} else if (origin == 1) {
			MB.sendSysEx(reslen, sysex, false);
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

	//Serial.println(String("S1 MSG: ") + cmd + " len: " + l);

	if (gs.r.debug_s2u_all) {
		MU.send(msg);
	}

	if (gs.r.debug_s2b_all || (gs.r.debug_s2b && (msg.type == 0xF0 || msg.type == 0xf7)))
		MB.send(msg);

	for (l = 0; l < LAYERS; l++) {
		struct layer_state & lr = ls[l];
		lmask = 1 << l;
		lchannel = ((lr.channel_out_offset + l) & 0x0F) + 1;
		lnote = (b1 + lr.transposition + lr.transposition_extra) & 0x7F;
		lenabled = lr.r.enabled && ((lr.activate == 0 && lr.active == 1) || (lr.activate == 1 && lr.active == 0));
//			(lr.channel_in_mask & (1 << (uint16_t) (channel-1)));

		note_in_bounds = (b1 + lr.transposition + lr.transposition_extra) == lnote ? 1 : 0;

		/* NoteOff must be passed even when midibox not enabled */
		if (cmd == midi::NoteOff) {
			/* Original note (before any transposition */
			if (true || lr.note_origin[b1] & 0x80) {
				lnote = lr.note_origin[b1] & 0x7F;
				note_in_bounds = 1;
			}

			if (note_in_bounds && layer_is_playing(lr, lnote)) {
				if (lr.r.mode & NOTE_MODE_HOLD && lr.ticks_remains[lnote] != 0)
					continue;

				layer_set_playing(lr, lnote, false, b1);
				MS1.sendNoteOff(lnote, b2, lchannel);

				/* FIXME: better handling */
				lr.ticks_remains[lnote] = 0;

				if (lr.r.mode == NOTE_MODE_SHUFFLE) {
					/* TODO: cancel next note on */
				}
			}
			continue;
		}

		if (!gs.r.enabled)
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
			if (note_in_bounds /*&& !layer_is_playing(lr, lnote)*/ && b1 >= lr.r.lo && b1 <= lr.r.hi) {
				/* FIXME: Repeat already playing same note for NOTE_MODE_HOLD */
				layer_set_playing(lr, lnote, true, b1);
				layer_handle_note_on_special(lr, lnote, b2);

				vol = b2;
				vol *= lr.r.volume;

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
		} else if (cmd == midi::ProgramChange) {
			/* Send PC only to selected layer */
			if (l == gs.r.selected_layer) {
				MS1.send(msg_out);
			}
		} else if (cmd == midi::ControlChange) {
			if (b1 == BankSelect || b1 == BankSelectLSB) {
				if (l == gs.r.selected_layer) {
					MS1.send(msg_out);
				}
			} else {
				MS1.send(msg_out);
			}
		} else if (cmd == midi::SystemExclusive) {
			/* FIXME: modify sysex */
			if (l == gs.r.selected_layer) {
				/* INFO: copy sysex array if modified */
				MS1.send(msg);
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
	int i;
	gs.r.config = 0;
	gs.r.status = 0;
	gs.r.init = 0;
	gs.r.selected_layer = 0;

	gs.tempo = 120;

	gs2reg(gs);

	gs.r.pedal_cc[0] = Sustain;
	gs.r.pedal_cc[1] = SoftPedal;
	gs.r.pedal_cc[2] = Sostenuto;

	gs.r.pedal_cc[0] = 0;
	gs.r.pedal_cc[1] = 0;
	gs.r.pedal_cc[2] = 0;

	gs.r.pedal_cc[3] = 0;
	gs.r.pedal_cc[4] = GeneralPurposeController1;
	gs.r.pedal_cc[5] = GeneralPurposeController2;
	gs.r.pedal_cc[6] = GeneralPurposeController3;
	gs.r.pedal_cc[7] = GeneralPurposeController4;

	for (i = 0; i < MIDIBOX_PEDALS; i++)
		gs.r.pedal_mode[i] = PEDAL_MODE_NORMAL;
	gs.r.pedal_mode[3] = PEDAL_MODE_IGNORE;

	for (uint8_t l = 0; l < LAYERS; l++) {
		struct layer_state & lr = ls[l];

		lr.r.enabled = 0;
		lr.r.status = 0;
		lr.r.init = 0;
		lr.r.pgm = 0;
		lr.r.bs = 0;
		lr.r.bs_lsb = 68;
		lr.r.lo = 0;
		lr.r.hi = 127;

		lr.r.volume = 100;
		lr.r.mode = 0;

		lr.transposition = 0;
		lr.transposition_extra = 0;
		lr.channel_in_mask = 0xffff;
		lr.channel = l + 1;
		lr.channel_out_offset = 0;
		lr.cc_sustain = 0;
		lr.cc_expression = 100;

		lr.r.release = 0x40;
		lr.r.attack = 0x40;
		lr.r.cutoff = 0x40;
		lr.r.decay = 0x40;

		/* TODO: "activate" feature (mode of pedal) is to temporary disable (default) or enable channel */
		//lr.active = 0; /* pedal mode == activate */
		lr.active = 1; /* pedal mode == deactivate */
		lr.activate = 0; /* This represents current state of the "activate" pedal */

		//lr.part = l + 1;
		layer2reg(lr);

		lr.r.pedal_cc[0] = Sustain;
		lr.r.pedal_cc[1] = SoftPedal;
		lr.r.pedal_cc[2] = Sostenuto;

		lr.r.pedal_cc[0] = 0;
		lr.r.pedal_cc[1] = 0;
		lr.r.pedal_cc[2] = 0;
		lr.r.pedal_cc[3] = 0;
		lr.r.pedal_cc[4] = GeneralPurposeController1;
		lr.r.pedal_cc[5] = GeneralPurposeController2;
		lr.r.pedal_cc[6] = GeneralPurposeController3;
		lr.r.pedal_cc[7] = GeneralPurposeController4;

		for (i = 0; i < MIDIBOX_PEDALS; i++)
			lr.r.pedal_mode[i] = PEDAL_MODE_NORMAL;
		lr.r.pedal_mode[3] = PEDAL_MODE_IGNORE;

		for (uint8_t j = 0; j < 128/8; j++) {
			lr.note[j] = 0;
		}
	}

	ls[0].transposition_extra = -12;
	ls[0].r.enabled = 1;
	ls[0].r.lo = 56;
	ls[1].r.hi = 55;
	ls[1].r.enabled = 1;
	ls[1].r.bs_lsb = 71;
	ls[1].r.bs = 0;
	ls[1].r.pgm = 33-1;

	layer2reg(ls[0]);
	layer2reg(ls[1]);

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
					(b1 == midi::Sostenuto && lr.cc_pedal2_mode == PEDAL_MODE_TOGGLE_ACT) ||
					(b1 == midi::SoftPedal && lr.cc_pedal3_mode == PEDAL_MODE_TOGGLE_ACT)
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
