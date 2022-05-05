#include "midibox.h"
#include "midi.h"
#include "gui.h"

void midibox_io_check_input();
void input_check_rot_enc();

void setup()
{
	Serial.begin(115200);
	lv_init();
	midibox_io_init();
	midibox_gui_init();
}

void loop()
{
	midibox_io_check_input();
	midi_secondary_handle_input();
	lv_timer_handler();
}

void setup1()
{
	midi_init();
}

void loop1()
{
	midi_loop();
	input_check_rot_enc();
}

void process_gui_cmd_send_to_midi(uint8_t cmd)
{
	rp2040.fifo.push(cmd);
	rp2040.fifo.pop();
}

int process_midi_cmd_available()
{
	return rp2040.fifo.available();
}

uint8_t process_midi_cmd_get()
{
	return rp2040.fifo.pop();
}

void process_midi_cmd_done()
{
	rp2040.fifo.push(0);
}
