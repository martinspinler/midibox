#ifndef __MIDIBOX_H__
#define __MIDIBOX_H__

#ifdef ARDUINO
#include <Arduino.h>
#define LV_CONF_INCLUDE_SIMPLE
#include <lvgl.h>
#include <Regexp.h>
#else
#include <stdio.h>
#include <unistd.h>

/* Arduino libraries */
#include <lvgl/lvgl.h>
#include <Regexp/Regexp.h>

/* Arduino core */
#include <String.h>

/* User includes */
#include "../simulator/io.h"

using namespace arduino;

extern VirtualMidiSerial Serial1;
extern VirtualSerial Serial;
#endif

#define ARRAY_SIZE(a) (sizeof(a) / sizeof(a[0]))

struct time_s {
	uint16_t year;
	uint8_t month, weekday, day, hour, minute, second;
};

void midibox_handle_button(uint8_t b, int8_t state);
void midibox_gui_init();
void midibox_io_init();

void midi_init();
void midi_loop();

void process_gui_cmd_send_to_midi(uint8_t cmd);

int process_midi_cmd_available();
uint8_t process_midi_cmd_get();
void process_midi_cmd_done();

void get_current_time(struct time_s & time);
void set_current_time(struct time_s & time);

#endif // __MIDIBOX_H__
