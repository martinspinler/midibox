#include <MIDI.h>

#include "io.h"

using namespace midi;

void VirtualMidiSerial::begin(int speed)
{
	m_midiin.openVirtualPort(m_port_name + "_input");
	//m_midiin.ignoreTypes(false, false, false);
	m_midiin.ignoreTypes(false, true, true);
	m_midiout.openVirtualPort(m_port_name + "_output");
}

int VirtualMidiSerial::available()
{
	if (!m_input_message.empty()) {
		return m_input_message.size();
	}

	m_midiin.getMessage(&m_input_message);
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
	uint8_t cmd;

	m_output_message.push_back(byte);

	cmd = m_output_message.front() & 0xF0;

	if (cmd == SystemExclusiveStart) {
		req_size = m_output_message.size();
		if (byte != SystemExclusiveEnd)
			req_size += 1;
	} else if (cmd == ProgramChange || cmd == AfterTouchChannel) {
		req_size = 2;
	} else if (cmd == NoteOn || cmd == NoteOff || cmd == AfterTouchPoly|| cmd == ControlChange) {
		req_size = 3;
	} else {
		std::cerr << "Unknown message in write: " << (int) cmd << "\n";
		for (int i = 0; i < m_output_message.size(); i++)
			std::cerr << (int) m_output_message[i] << " ";
		std::cerr << "\n";

		req_size = 1;
	}

	if (m_output_message.size() >= req_size) {
		m_midiout.sendMessage(&m_output_message);
		m_output_message.clear();
	}
	return 1;
}
