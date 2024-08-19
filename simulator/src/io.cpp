#include <MIDI.h>

#include "io.h"

using namespace midi;

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

	if (verbosity < 2 && (cmd == midi::Clock || cmd == ActiveSensing))
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

void VirtualMidiSerial::begin(int speed)
{
	const int read_time = 0;
	const int read_sense = 0;

	m_midiin.openVirtualPort(m_port_name + "_input");
	m_midiin.ignoreTypes(false, read_time ? false : true, read_sense ? false : true);

	m_midiout.openVirtualPort(m_port_name + "_output");
}

int VirtualMidiSerial::available()
{
	uint8_t cmd;
	if (!m_input_message.empty()) {
		return m_input_message.size();
	}

	m_midiin.getMessage(&m_input_message);
	print_msg(m_input_message, m_port_name + " IN  ", m_verbosity);
	return m_input_message.size();
}

int VirtualMidiSerial::read()
{
	char ch;

	if (!m_input_message.empty()) {
		ch = m_input_message.front();
		m_input_message.erase(m_input_message.begin());
		return ch;
	} else {
		std::cerr << "Read with null data\n";
	}
	return 0;
}

size_t VirtualMidiSerial::write(uint8_t byte)
{
	int req_size;

	m_output_message.push_back(byte);
	req_size = parse_req_size(m_output_message);
	if (m_output_message.size() >= req_size) {
		print_msg(m_output_message, m_port_name + " OUT ", m_verbosity);

		m_midiout.sendMessage(&m_output_message);
		m_output_message.clear();
	}
	return 1;
}
