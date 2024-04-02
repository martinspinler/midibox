#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#include <cstdint>

#include "io.h"

class StdoutSerial;
extern StdoutSerial Serial;

typedef midi::SerialMIDI<VirtualMidiSerial> VirtualSerialMidi;

typedef midi::MidiInterface<VirtualSerialMidi> MidiInterfaceUsb;
typedef midi::MidiInterface<VirtualSerialMidi> MidiInterfaceHwserial;

extern MidiInterfaceUsb MU;
extern MidiInterfaceHwserial MS1;

#define thread_midi_msg_send_to_control control_handle_midi_msg

#endif // _MIDIBOX_COMPAT_H
