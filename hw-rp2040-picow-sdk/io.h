/* Arduino core */
//#include <Stream.h>
//#include <String.h>

#include <string>
#include <vector>

//#include <rtmidi/RtMidi.h>

#ifndef __VIRTUALSERIAL_H__
#define __VIRTUALSERIAL_H__

unsigned long micros();

class VirtualSerial//: public Stream
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

class TUHMidiSerial: public VirtualSerial
{
	std::vector<uint8_t> m_input_message;
//	std::vector<uint8_t> m_output_message;
	uint8_t m_buf[256];
public:
	TUHMidiSerial() {
		m_input_message.reserve(256);
//		m_output_message.reserve(256);
	}
	virtual ~TUHMidiSerial() {}

	void begin(int speed) {}

	virtual int available();
	virtual int read();
	virtual int peek() {return 0;}
	virtual size_t write(uint8_t);

	void rx_cb(uint8_t);
	void tx_cb();
};

class UartMidiSerial: public VirtualSerial
{
	int m_buf;
public:
	UartMidiSerial() {m_buf = -1;};
	virtual ~UartMidiSerial() {};

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
