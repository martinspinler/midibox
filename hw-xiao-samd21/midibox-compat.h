#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#ifndef ARDUINO
#error "This is not Arduino platform, provide own compatibility header"
#endif

#define PIN_SERIAL2_TX 8
#define PIN_SERIAL2_RX 9

#include <MIDI.h>
#include <Arduino.h>

struct MySettings : public midi::DefaultSettings {
	static const long BaudRate = 31250;
};


typedef midi::SerialMIDI<HardwareSerial> HardwareSerialMIDI;
typedef midi::SerialMIDI<HardwareSerial, struct MySetting> HardwareSerialMIDIFast;

typedef midi::MidiInterface<HardwareSerialMIDI> MidiInterfaceHwserial;
typedef midi::MidiInterface<HardwareSerialMIDIFast> MidiInterfaceHwserialFast;

#define MIDIBOX_HAVE_UART2

#define thread_midi_msg_send_to_control control_handle_midi_msg

#endif // _MIDIBOX_COMPAT_H
