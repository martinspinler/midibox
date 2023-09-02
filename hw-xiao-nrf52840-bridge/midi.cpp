#include <stddef.h>
#include "midi.h"

#define MIDI_TC_INTERNAL

using namespace midi;

const uint8_t MIDIBOX_SYSEX_ID1 = 0x77;
const uint8_t MIDIBOX_SYSEX_ID2 = 0x78;
const uint8_t MIDIBOX_SYSEX_PEDALS = 0x79;

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
	MB.send(msg);
	MU.send(msg);
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
	MU.read();
	MB.read();
	MS1.read();
}
