#ifndef _MIDIBOX_COMPAT_H
#define _MIDIBOX_COMPAT_H

#ifndef ARDUINO
#error "This is not Arduino platform, provide own compatibility header"
#endif

#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <bluefruit.h>

typedef midi::SerialMIDI<Adafruit_USBD_MIDI> USBSerialMIDI;
typedef midi::SerialMIDI<HardwareSerial> HardwareSerialMIDI;
typedef midi::SerialMIDI<BLEMidi> BleMIDI;

typedef midi::MidiInterface<USBSerialMIDI> MidiInterfaceUsb;
typedef midi::MidiInterface<HardwareSerialMIDI> MidiInterfaceHwserial;
typedef midi::MidiInterface<BleMIDI> MidiInterfaceBle;

#define thread_midi_msg_send_to_control control_handle_midi_msg

#endif // _MIDIBOX_COMPAT_H
