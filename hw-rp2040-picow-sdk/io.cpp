#include <iostream>
#include <MIDI.h>

#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/bootrom.h"

#include "io.h"

#include "tusb.h"

using namespace midi;
using namespace std;

static int parse_req_size(std::vector<uint8_t> &m_output_message)
{
	uint8_t cmd;
	int req_size;

	if (m_output_message.size() == 0)
		return 1;

	cmd = m_output_message.front();
	if (cmd < 0xF0) {
		cmd &= 0xF0;
	}

	if (cmd == SystemExclusiveStart) {
		req_size = m_output_message.size();
		if (m_output_message.back() != SystemExclusiveEnd)
			req_size += 1;
	} else if (cmd == ProgramChange || cmd == AfterTouchChannel) {
		req_size = 2;
	} else if (cmd == NoteOn || cmd == NoteOff || cmd == AfterTouchPoly|| cmd == ControlChange) {
		req_size = 3;
	} else if (cmd >= 0xF8 && cmd <= 0xFF) {
		req_size = 1;
	} else {
		std::cerr << "Unknown message in write: " << (int) cmd << "\n";
		for (int i = 0; i < m_output_message.size(); i++)
			std::cerr << (int) m_output_message[i] << " ";
		std::cerr << "\n";

		req_size = 1;
	}
	return req_size;
}

static void print_msg(std::vector<uint8_t> &m_output_message, std::string name, int verbosity)
{
	static const char *msgs[24] = {
	    "NoteOff",
	    "NoteOn",
	    "AfterTouchPoly",
	    "ControlChange",
	    "ProgramChange",
	    "AfterTouchChannel",
	    "PitchBend",
	    "----",
	    "SystemExclusive",
	    "SCM: TCQF",
	    "SCM: SP",
	    "SCM: SS",
	    "SCM: F4",
	    "SCM: F5",
	    "SCM: TR",
	    "SystemExclusiveEnd",
	    "SRT: Clock",
	    "SRT: Reserved: 0xF9",
	    "SRT: Start",
	    "SRT: Continue",
	    "SRT: Stop",
	    "SRT: Reserved: 0xFD",
	    "SRT: Active Sensing",
	    "SRT: Reset",
	};

	uint8_t cmd;

	int req_size = parse_req_size(m_output_message);

	if (m_output_message.size() == 0)
		return;

	cmd = m_output_message.front();

	//if (verbosity < 2 && (cmd == midi::Clock || cmd == ActiveSensing))
	if ((cmd == midi::Clock || cmd == ActiveSensing))
		return;

	if (verbosity < 1)
		return;

	if (cmd < 0xF0) {
		cmd = (cmd & 0xF0) - 0x80;
		cmd >>= 4;
	} else {
		cmd = cmd - 0xF0 + 8;
	}

	std::cerr << name;

	if (msgs[cmd])
		std::cerr << msgs[cmd] << " ";

	for (int i = 0; i < req_size; i++) {
		fprintf(stderr, " %02x", m_output_message[i]);
	}
	std::cerr << std::endl;
}

int TUHMidiSerial::available()
{
	return m_input_message.size();
}

int TUHMidiSerial::read()
{
	char ch;
	if (m_input_message.empty()) {
		return -1;
	}

	ch = m_input_message.front();
	m_input_message.erase(m_input_message.begin());
	return ch;
}

void TUHMidiSerial::rx_cb(uint8_t xferred_bytes)
{
	int b;
	uint32_t ret;
	uint8_t cable_num = 0;

	ret = tuh_midi_stream_read(0, &cable_num, m_buf, 256);
	for (b = 0; b < ret; b++) {
		m_input_message.push_back(m_buf[b]);
	}
}

size_t TUHMidiSerial::write(uint8_t byte)
{
	uint8_t buffer[1];
	buffer[0] = byte;

	return tuh_midi_stream_write(0, 0, buffer, 1);
}

void TUHMidiSerial::tx_cb()
{
	tuh_midi_write_flush(0);
}

void check_reset(int c)
{
	static int m = 0;
	if (c < 0)
		return;

	if (0) ;
	else if (m == 0 && c == 'r') m++;
	else if (m == 1 && c == 'e') m++;
	else if (m == 2 && c == 's') m++;
	else if (m == 3 && c == 'e') m++;
	else if (m == 4 && c == 't') m++;
	else m = 0;

	if (m == 5)
		rom_reset_usb_boot(0, 0);
}

int UartMidiSerial::available()
{
	if (m_buf >= 0) {
		return 1;
	}
	m_buf = stdio_getchar_timeout_us(0);
	check_reset(m_buf);
	if (m_buf >= 0) {
		return 1;
	}
	return 0;
}

int UartMidiSerial::read()
{
	int b;
	if (m_buf >= 0) {
		b = m_buf;
		m_buf = -1;
		return b;
	}
	b = stdio_getchar_timeout_us(0);
	check_reset(b);
	return b;
}

size_t UartMidiSerial::write(uint8_t byte)
{
	stdio_putchar_raw(byte);
	fflush(stdout);
	return 1;
}
