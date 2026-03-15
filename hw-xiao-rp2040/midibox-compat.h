#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#include <cstdint>

#include "io.h"

#define MIDIBOX_HAVE_PORT1

unsigned long micros();

typedef midi::SerialMIDI<VirtualSerial> UartVirtualSerialMidi;
typedef midi::SerialMIDI<VirtualSerial> TUDVirtualSerialMidi;
typedef midi::SerialMIDI<VirtualSerial> PioUartVirtualSerialMidi;

struct HwMidiSettings : public midi::DefaultSettings
{
	static const bool UseReceiverActiveSensing = true;
	static const bool UseSenderActiveSensing = true;
	static const unsigned SenderActiveSensingPeriodicity = 250;
};
struct HwPioMidiSettings : public midi::DefaultSettings
{
	static const bool UseReceiverActiveSensing = false;
	static const bool UseSenderActiveSensing = false;
	static const unsigned SenderActiveSensingPeriodicity = 250;
};

struct SimulatorPlatform: public midi::DefaultPlatform
{
	static unsigned long now() {return micros() / 1000;}
};

typedef midi::MidiInterface<UartVirtualSerialMidi, HwMidiSettings, SimulatorPlatform> MidiInterfaceHwserial;
typedef midi::MidiInterface<PioUartVirtualSerialMidi, HwPioMidiSettings, SimulatorPlatform> MidiInterfacePioHwserial;
typedef midi::MidiInterface<TUDVirtualSerialMidi> MidiInterfaceUsb;

class StdoutSerial;
extern StdoutSerial Serial;

extern MidiInterfaceUsb MU;
extern MidiInterfaceHwserial MS1;
extern MidiInterfacePioHwserial MS2;

#define thread_midi_msg_send_to_control control_handle_midi_msg

#endif // _MIDIBOX_COMPAT_H
