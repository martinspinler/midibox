#ifndef __MIDI_H__
#define __MIDI_H__

#include <MIDI.h>

#ifdef ARDUINO
#include "midibox-compat.h"
#else
#include <midibox-compat.h>
#endif

extern MidiInterfaceUsb MU;
extern MidiInterfaceHwserial MS1;
extern MidiInterfaceBle MB;

void midi_init();
void midi_loop();

void midi_handle_pedal_input(uint8_t pedal, uint8_t val);

#endif // __MIDI_H__
