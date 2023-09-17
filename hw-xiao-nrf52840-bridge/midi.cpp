#include <stddef.h>
#include "midi.h"

#define MIDI_TC_INTERNAL

using namespace midi;

const uint8_t MIDIBOX_SYSEX_ID1 = 0x77;
const uint8_t MIDIBOX_SYSEX_ID2 = 0x78;
const uint8_t MIDIBOX_SYSEX_PEDALS = 0x79;

#define THROTTLE_CC_SIZE 8
const uint8_t throttle_cc[THROTTLE_CC_SIZE] = {
	Sustain,
	Portamento,
	Sostenuto,
	SoftPedal,
	Effects1,
	Effects3,
	ChannelVolume,
	ExpressionController,
};

struct throttle {
	unsigned long lastsync;
	uint8_t lastval;
	uint8_t currval;
};

#define THROTTLE_CC_CHANNEL_SIZE 3
struct throttle throttle[THROTTLE_CC_CHANNEL_SIZE][THROTTLE_CC_SIZE];

#define THROTTLE_CC_TIME 40

void midi_handle_pedal_input(uint8_t pedal, uint8_t val)
{
	uint8_t i;
	uint8_t cmd, cc, pm;

	static uint8_t sysex[4];

	if (pedal >= 8)
		return;

	sysex[0] = MIDIBOX_SYSEX_PEDALS;
	sysex[1] = 0x01;
	sysex[2] = pedal;
	sysex[3] = val;

	MS1.sendSysEx(4, sysex, false);
}

void handleUsbMidiMessage(const Message<128> & msg)
{
	MS1.send(msg);
}

void handleBleMidiMessage(const Message<128> & msg)
{
	MS1.send(msg);
}

void handleS1MidiMessage(const midi::Message<128> & msg)
{
	static uint8_t i;
	static uint8_t filter;
	static unsigned long ct;

	ct = millis();

	MU.send(msg);

	if (msg.type == ControlChange &&
			msg.channel <= THROTTLE_CC_CHANNEL_SIZE) {
		filter = 0;
		for (i = 0; i < THROTTLE_CC_SIZE; i++) {
			if (msg.data1 == throttle_cc[i]) {
				struct throttle & t = throttle[msg.channel-1][i];

				t.currval = msg.data2;
				if (t.lastsync + THROTTLE_CC_TIME < ct) {
					filter = 1;
				} else {
					t.lastval = t.currval;
					t.lastsync = ct;
				}
			}
		}
		if (!filter) {
			MB.send(msg);
		}
	} else {
		MB.send(msg);
	}
}

void midi_init()
{
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

void midi_loop()
{
	static uint8_t i;
	static uint8_t c;
	static unsigned long ct;

	MU.read();
	MB.read();
	MS1.read();

	ct = millis();

	for (c = 0; c < THROTTLE_CC_CHANNEL_SIZE; c++) {
		for (i = 0; i < THROTTLE_CC_SIZE; i++) {
			struct throttle & t = throttle[c][i];
			if (t.currval != t.lastval) {
				if (t.lastsync + THROTTLE_CC_TIME >= ct) {
					t.lastval = t.currval;
					t.lastsync = ct;
					MB.sendControlChange(throttle_cc[i], t.currval, c+1);
				}
			}
		}
	}
}
