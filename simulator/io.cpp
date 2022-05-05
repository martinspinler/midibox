#include <ctime>
#include <semaphore.h>

#define SDL_MAIN_HANDLED
#include <SDL2/SDL.h>
#include <lvgl/lvgl.h>
#include <lv_drivers/sdl/sdl.h>

#include "../midibox/midibox.h"
#include "../midibox/midi_def.h"
#include "../midibox/gui.h"

void midibox_keyboard_read(lv_indev_drv_t * indev_drv, lv_indev_data_t * data)
{
	sdl_keyboard_read(indev_drv, data);
	if (data->state == LV_INDEV_STATE_PRESSED) {
		if (data->key >= '0' && data->key <= '9') {
			midibox_handle_button(data->key - '0', 1);
		} else if (data->key >= 'a' && data->key <= 'f') {
			midibox_handle_button(data->key - 'a' + 0x0A, 1);
		}
	}
}

void midibox_io_init(void)
{
	sdl_init();

	static lv_disp_draw_buf_t disp_buf1;
	static lv_color_t buf1_1[SDL_HOR_RES * 100];
	lv_disp_draw_buf_init(&disp_buf1, buf1_1, NULL, SDL_HOR_RES * 100);

	static lv_disp_drv_t disp_drv;
	lv_disp_drv_init(&disp_drv);
	disp_drv.draw_buf = &disp_buf1;
	disp_drv.flush_cb = sdl_display_flush;
	disp_drv.hor_res = SDL_HOR_RES;
	disp_drv.ver_res = SDL_VER_RES;

	lv_disp_t * disp = lv_disp_drv_register(&disp_drv);

	lv_theme_t * th = lv_theme_default_init(disp, lv_palette_main(LV_PALETTE_BLUE), lv_palette_main(LV_PALETTE_RED), true, LV_FONT_DEFAULT);
	lv_disp_set_theme(disp, th);

	lv_group_t * g = lv_group_create();
	lv_group_set_default(g);

	static lv_indev_drv_t indev_drv_1;
	lv_indev_drv_init(&indev_drv_1);
	indev_drv_1.type = LV_INDEV_TYPE_POINTER;

	indev_drv_1.read_cb = sdl_mouse_read;
	lv_indev_t *mouse_indev = lv_indev_drv_register(&indev_drv_1);

	static lv_indev_drv_t indev_drv_2;
	lv_indev_drv_init(&indev_drv_2);
	indev_drv_2.type = LV_INDEV_TYPE_KEYPAD;
	indev_drv_2.read_cb = midibox_keyboard_read;
	lv_indev_t *kb_indev = lv_indev_drv_register(&indev_drv_2);
	lv_indev_set_group(kb_indev, g);

	static lv_indev_drv_t indev_drv_3;
	lv_indev_drv_init(&indev_drv_3);
	indev_drv_3.type = LV_INDEV_TYPE_ENCODER;
	indev_drv_3.read_cb = sdl_mousewheel_read;
	lv_indev_t * enc_indev = lv_indev_drv_register(&indev_drv_3);
	lv_indev_set_group(enc_indev, g);
}

void VirtualMidiSerial::begin(int speed)
{
	m_midiin.openVirtualPort("MidiBox Input");
	m_midiout.openVirtualPort("MidiBox Output");

	m_midiin.ignoreTypes(false, false, false);
}

int VirtualMidiSerial::available()
{
	if (!m_input_message.empty()) {
		return m_input_message.size();
	}

	m_midiin.getMessage(&m_input_message);
#if 0
	if (m_input_message.size())
		std::cout << "Get" << m_input_message.size() << "\n";
#endif
	return m_input_message.size();
}

int VirtualMidiSerial::read()
{
	char ch;
	if (!m_input_message.empty()) {
		ch = m_input_message.front();
		m_input_message.erase(m_input_message.begin());
		return ch;
	} else {
		std::cerr << "Read with null data\n";
	}
	return 0;
}

size_t VirtualMidiSerial::write(uint8_t byte)
{
	int req_size;
	uint8_t cmd;

	m_output_message.push_back(byte);

	cmd = m_output_message.front() & 0xF0;
#if 1
	if (cmd == MIDI_SYSEX) {
		req_size = m_output_message.size();
		if (byte != MIDI_SYSEX_END)
			req_size += 1;
	} else if (cmd == MIDI_PROGRAM_CHANGE || cmd == MIDI_CHANNEL_PRESSURE) {
		req_size = 2;
	} else if (cmd == MIDI_NOTE_ON || cmd == MIDI_NOTE_OFF || cmd == MIDI_POLYPHONIC_AFTERTOUCH || cmd == MIDI_CONTROL_CHANGE) {
		req_size = 3;
	} else {
		std::cerr << "Unknown message in write: " << (int) cmd << "\n";
		req_size = 1;
	}

	if (m_output_message.size() >= req_size) {
		m_midiout.sendMessage(&m_output_message);
		m_output_message.clear();
	}
#endif
	return 1;
}
