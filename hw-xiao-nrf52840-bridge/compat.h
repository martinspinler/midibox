#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#ifdef ARDUINO
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <bluefruit.h>
#else
#include <cstdint>

class StdoutSerial;
extern StdoutSerial Serial;
#endif

#include <MIDI.h>


#endif // _MIDIBOX_COMPAT_H
