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

int TUDMidiSerial::available()
{
	return m_input_message.size();
}

int TUDMidiSerial::read()
{
	char ch;
	if (m_input_message.empty()) {
		return -1;
	}

	ch = m_input_message.front();
	m_input_message.erase(m_input_message.begin());
	return ch;
}

void TUDMidiSerial::rx_cb(uint8_t xferred_bytes)
{
	int b;
	uint32_t ret;
	uint8_t cable_num = 0;
	ret = tud_midi_n_available(0, 0);
	if (ret == 0)
		return;

	ret = tud_midi_n_stream_read(0, cable_num, m_buf, 256);
	for (b = 0; b < ret; b++) {
		m_input_message.push_back(m_buf[b]);
	}
}

size_t TUDMidiSerial::write(uint8_t byte)
{
	uint8_t buffer[1];
	buffer[0] = byte;

	return tud_midi_n_stream_write(0, 0, buffer, 1);
}

void TUDMidiSerial::tx_cb()
{
	//tuh_midi_write_flush(0);
}


int UartMidiSerial::available()
{
	return uart_is_readable(uart0);
}

int UartMidiSerial::read()
{
	if (available() == 0)
		return -1;
	return uart_getc(uart0);
}

size_t UartMidiSerial::write(uint8_t byte)
{
	uart_putc(uart0, byte);
	return 1;
}

int PioUartMidiSerial::available()
{
	return m_input_message.size();
}

int PioUartMidiSerial::read()
{
	char ch;
	if (m_input_message.empty()) {
		return -1;
	}

	ch = m_input_message.front();
	m_input_message.erase(m_input_message.begin());
	return ch;

}

size_t PioUartMidiSerial::write(uint8_t byte)
{
	return 1;
}

void PioUartMidiSerial::rx_cb(uint8_t byte)
{
	m_input_message.push_back(byte);
}

