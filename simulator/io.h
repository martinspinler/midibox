/* Arduino core */
#include <Stream.h>

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

class VirtualMidiSerial: public Stream
{
	RtMidiIn  m_midiin;
	RtMidiOut m_midiout;

	std::vector<uint8_t> m_input_message;
	std::vector<uint8_t> m_output_message;
public:
	VirtualMidiSerial() {};
	virtual ~VirtualMidiSerial() {};

	void begin(int speed);

	virtual int available();
	virtual int read();
	virtual int peek() {return 0;}
	virtual size_t write(uint8_t);
};

#endif
