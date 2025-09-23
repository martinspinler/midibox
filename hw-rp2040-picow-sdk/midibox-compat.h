#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#include <cstdint>

#include "io.h"

unsigned long micros();

typedef midi::SerialMIDI<VirtualSerial> UartVirtualSerialMidi;
typedef midi::SerialMIDI<VirtualSerial> TUHVirtualSerialMidi;

struct HwMidiSettings : public midi::DefaultSettings
{
	static const bool UseReceiverActiveSensing = true;
	static const bool UseSenderActiveSensing = true;
	static const unsigned SenderActiveSensingPeriodicity = 250;
};
struct SimulatorPlatform: public midi::DefaultPlatform
{
	static unsigned long now() {return micros() / 1000;}
};

typedef midi::MidiInterface<UartVirtualSerialMidi> MidiInterfaceUsb;
typedef midi::MidiInterface<TUHVirtualSerialMidi, HwMidiSettings, SimulatorPlatform> MidiInterfaceHwserial;

class StdoutSerial;
extern StdoutSerial Serial;

extern MidiInterfaceUsb MU;
extern MidiInterfaceHwserial MS1;

#define thread_midi_msg_send_to_control control_handle_midi_msg

#endif // _MIDIBOX_COMPAT_H
