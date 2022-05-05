#include "midibox.h"
#include "midi.h"
#include "gui.h"

static unsigned long tempo_temp = 0;

static void metronome_tab_create(lv_obj_t *l)
{
}

static void mix_tab_create(lv_obj_t *l)
{
	lv_obj_t *o;

	o = lv_btn_create(l);
	lv_label_set_text(lv_label_create(o), "Mute");
}

static bool gui_handle_button(uint8_t b, signed char state)
{
	switch (b) {
		case 0 ... 9:
			tempo_temp *= 10;
			tempo_temp += b;
			return true;
/*		case 0xE:
			maintab_change(MT_INFO);
//			for (int i = 0; i < 4; i++)
//				last_tap[0] = 0;
			return true;
	*/
		case 0xF:
			if (tempo_temp % 1000) {
				midi_change_tempo(tempo_temp % 1000);
				maintab_change(MT_INFO);
			} /*else {
				tempo_temp = 0;
				if (tempo_temp > 30)
			}*/

			return true;
	}
	return false;
}

void scroll_begin_event(lv_event_t * e);

void midibox_gui_tab_config_create(lv_obj_t * tab)
{
	uint8_t i;
	lv_obj_t *o;
	lv_obj_t *l = tab;

	lv_obj_t *tabview;
	tabview = lv_tabview_create(tab, LV_DIR_TOP, 24);

	static const char *panel_text[] = {"Metronome", "Mix"};
	for (i = 0; i < 2; i++) {
		l = lv_tabview_add_tab(tabview, panel_text[i]);
		lv_obj_set_style_pad_left(l, 5, LV_PART_MAIN);
		lv_obj_set_style_pad_right(l, 5, LV_PART_MAIN);
		lv_obj_set_style_pad_top(l, 5, LV_PART_MAIN);
		lv_obj_set_style_pad_bottom(l, 5, LV_PART_MAIN);

		switch(i) {
			case 0: metronome_tab_create(l); break;
			case 1: mix_tab_create(l); break;
		}
	}

	lv_obj_add_event_cb(lv_tabview_get_content(tabview), scroll_begin_event, LV_EVENT_SCROLL_BEGIN, NULL);
	lv_obj_add_event_cb(lv_tabview_get_content(tabview), scroll_begin_event, LV_EVENT_SCROLL_END, NULL);
}

struct panel_callbacks pc_config = {
	.button_pressed = gui_handle_button,
	.init = midibox_gui_tab_config_create,
};
