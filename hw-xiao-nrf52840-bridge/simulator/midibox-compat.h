#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#include <cstdint>

#include "io.h"

typedef midi::SerialMIDI<VirtualMidiSerial> VirtualSerialMidi;

typedef midi::MidiInterface<VirtualSerialMidi> MidiInterfaceUsb;
typedef midi::MidiInterface<VirtualSerialMidi> MidiInterfaceHwserial;
typedef midi::MidiInterface<VirtualSerialMidi> MidiInterfaceBle;

class StdoutSerial;
extern StdoutSerial Serial;

#define thread_midi_msg_send_to_control control_handle_midi_msg


#endif // _MIDIBOX_COMPAT_H
