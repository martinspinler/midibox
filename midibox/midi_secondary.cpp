#include "midibox.h"
#include "midi.h"

void handle_secondary_sysex(uint8_t *sysex, uint8_t len)
{
	if (sysex[0] == 0xc1) {
		struct time_s time;
		time.year  = 1900;
		time.year += sysex[1];
		time.year += sysex[2] << 4;
		time.month = sysex[3];
		time.day   = sysex[4];
		time.hour  = sysex[5];
		time.minute= sysex[6];
		time.second= sysex[7];
		set_current_time(time);
	}
}

void midi_secondary_handle_input()
{
	static uint8_t state = 0;

	static uint8_t sysex[64];
	static uint8_t sysex_len;

	uint8_t data, cmd;
	while (Serial.available()) {
		data = Serial.read();

		cmd = (data & 0xF0);
		if (data == MIDI_SYSEX) {
			state = 1;
			sysex_len = 0;
		} else if (data == MIDI_SYSEX_END) {
			state = 0;
			if (sysex_len)
				handle_secondary_sysex(sysex, sysex_len);
		} else if (state == 1) {
			sysex[sysex_len] = data;
			sysex_len++;
			if (sysex_len > 64) {
				state = 2;
				sysex_len = 0;
			}
		}
	}
}
