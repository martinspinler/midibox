#ifndef __MIDI_DEF_H__
#define __MIDI_DEF_H__

#define MIDI_NOTE_ON            0x90
#define MIDI_NOTE_OFF           0x80
#define MIDI_POLYPHONIC_AFTERTOUCH 0xA0
#define MIDI_CONTROL_CHANGE     0xB0
#define MIDI_PROGRAM_CHANGE     0xC0
#define MIDI_CHANNEL_PRESSURE   0xD0
#define MIDI_PITCH_WHEEL_CHANGE 0xE0
#define MIDI_SYSEX              0xF0
#define MIDI_SYSEX_END          0xF7

#define MIDI_CC_BANK_SELECT     0
#define MIDI_CC_LSB_OFFSET     32
#define MIDI_CC_EXPRESSION     11
#define MIDI_CC_P_HOLD         64
#define MIDI_CC_P_SOSTENUTO    66
#define MIDI_CC_P_SOFT         67

#endif // __MIDI_DEF_H__
