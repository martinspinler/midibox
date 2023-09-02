#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#define PIN_SERIAL2_RX       (8)
#define PIN_SERIAL2_TX       (9)

#ifdef ARDUINO
#include <Arduino.h>
#else
#include <cstdint>

class StdoutSerial;
extern StdoutSerial Serial;
#endif

#include <MIDI.h>


#endif // _MIDIBOX_COMPAT_H
