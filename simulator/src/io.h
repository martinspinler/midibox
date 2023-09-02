/* Arduino core */
#include <Stream.h>
#include <String.h>

#include <string>

#include <rtmidi/RtMidi.h>

#ifndef __VIRTUALSERIAL_H__
#define __VIRTUALSERIAL_H__

unsigned long micros();

class VirtualSerial: public Stream
{
public:
	VirtualSerial() {}
	virtual ~VirtualSerial() {}

	void begin(int speed) {}
	virtual int available() {return 0;}
	virtual int read() {return 0;}
	virtual int peek() {return 0;}
	virtual size_t write(uint8_t) {return 0;}
};

class VirtualMidiSerial: public VirtualSerial
{
	RtMidiIn  m_midiin;
	RtMidiOut m_midiout;

	std::string m_port_name;

	std::vector<uint8_t> m_input_message;
	std::vector<uint8_t> m_output_message;
public:
	VirtualMidiSerial(std::string client_name, std::string port_name) :
		m_midiin(RtMidi::UNSPECIFIED, client_name), m_midiout(RtMidi::UNSPECIFIED, client_name), m_port_name(port_name) {}
	virtual ~VirtualMidiSerial() {};

	void begin(int speed);

	virtual int available();
	virtual int read();
	virtual int peek() {return 0;}
	virtual size_t write(uint8_t);
};

class StdoutSerial: public VirtualSerial
{
public:
	StdoutSerial() {}
	virtual ~StdoutSerial() {};

	virtual size_t write(uint8_t c) {fprintf(stdout, "%c", c); fflush(stdout); return 1;}
};

extern StdoutSerial Serial;
#endif
