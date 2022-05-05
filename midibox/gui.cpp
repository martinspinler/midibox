#include "midibox.h"
#include "midi.h"
#include "gui.h"

lv_obj_t *mtview;

extern struct panel_callbacks pc_info, pc_layers, pc_comps, pc_mix, pc_config;

struct time_s current_time;

struct panel_callbacks panels_callbacks[MT_MAX_PANELS] = {
	pc_info,
	pc_layers,
	pc_comps,
//	pc_mix,
	pc_config,
};

struct panel_callbacks *current_panel = &panels_callbacks[0];

uint32_t mt = 0;

lv_obj_t *btn_hints[16];

static void gui_update()
{
	uint8_t i;
	for (i = 0; i < HINT_BTNS; i++) {
		lv_obj_add_flag(btn_hints[i], LV_OBJ_FLAG_HIDDEN);
	}

	lv_area_t a;
	lv_obj_get_coords(mtview, &a);
	for (i = 0x0A; i <= 0x0D; i++) {
		lv_obj_clear_flag(btn_hints[i], LV_OBJ_FLAG_HIDDEN);
		lv_obj_set_pos(btn_hints[i], a.x1 + (i-0xA) * (a.x2-a.x1)/4 + 2/*(a.x2-a.x1)/8-4*/, a.y1 + 4);
	}

	if (current_panel->update) {
		current_panel->update();
	}
}

void scroll_begin_event(lv_event_t * e)
{
	/*Disable the scroll animations. Triggered when a tab button is clicked */
	if (lv_event_get_code(e) == LV_EVENT_SCROLL_BEGIN) {
		lv_anim_t *a = (lv_anim_t*) lv_event_get_param(e);
		if (a)
			a->time = 0;
	}
	/* Update panel here, in this moment are all widgets in correct position for lv_obj_get_coords */
	if (lv_event_get_code(e) == LV_EVENT_SCROLL_END) {
		if (lv_event_get_target(e) == lv_tabview_get_content(mtview)) {
			gui_update();
		}
	}
}

static void maintab_value_changed(lv_event_t * e)
{
	mt = lv_tabview_get_tab_act(mtview);
	current_panel = &panels_callbacks[mt];
}

void maintab_change(int l)
{
	mt = l;
	current_panel = &panels_callbacks[l];
	lv_tabview_set_act(mtview, mt, LV_ANIM_OFF);
	gui_update();
}

void midibox_handle_button(uint8_t b, int8_t state)
{
	if (!current_panel->button_pressed || !current_panel->button_pressed(b, state)) {
		switch(b) {
			case 0xA ... 0xD:
				maintab_change(MT_INFO + b - 0xA);
				break;
			case 0xE:
				maintab_change(MT_INFO);
				break;
		}
	}
}

void midibox_gui_init()
{
	static lv_style_t style_tab;
	uint8_t i;
	lv_style_init(&style_tab);
	lv_style_set_max_height(&style_tab, 30);

	lv_obj_t *o;
	lv_obj_t *l;
	lv_obj_t *tabview;

	static const char * hint_btn_text[] = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "*", "#"};
	for (i = 0; i < 16; i++) {
		o = btn_hints[i] = lv_label_create(lv_layer_sys());
		lv_label_set_text(o, hint_btn_text[i]);
		lv_obj_set_x(o, i*40);
		lv_obj_set_size(o, 15, 20);
		lv_obj_set_style_pad_all(o, 3, LV_PART_MAIN);
		lv_obj_set_style_text_color(o, lv_palette_main(LV_PALETTE_YELLOW), 0);
		//lv_obj_set_style_bg_color(o, lv_palette_main(LV_PALETTE_YELLOW), 0);
		//lv_obj_set_style_bg_opa(o, 192, LV_PART_MAIN);
		lv_obj_set_style_opa(o, 192, LV_PART_MAIN);
		lv_obj_set_style_radius(o, LV_STATE_DEFAULT, 20);
	}

	mtview = tabview = lv_tabview_create(lv_scr_act(), LV_DIR_TOP, 30);
//	lv_obj_set_style_pad_top(tabview, 0, LV_PART_MAIN);
//	lv_obj_set_style_pad_top(lv_tabview_get_tab_btns(tabview), 0, LV_PART_MAIN);
//	lv_obj_set_style_pad_top(lv_tabview_get_content(tabview), 0, LV_PART_MAIN);
	lv_obj_add_event_cb(lv_tabview_get_content(tabview), scroll_begin_event, LV_EVENT_SCROLL_BEGIN, NULL);
	lv_obj_add_event_cb(lv_tabview_get_content(tabview), scroll_begin_event, LV_EVENT_SCROLL_END, NULL);
	lv_obj_add_event_cb(tabview, maintab_value_changed, LV_EVENT_VALUE_CHANGED, NULL);

	static const char *panel_text[MT_MAX_PANELS] = {"Info", "Layers", "Comp.", /*"Mix",*/ "Conf."};
	for (i = 0; i < MT_MAX_PANELS; i++) {
		l = lv_tabview_add_tab(tabview, panel_text[i]);
		lv_obj_set_style_pad_left(l, 5, LV_PART_MAIN);
		lv_obj_set_style_pad_right(l, 5, LV_PART_MAIN);
		lv_obj_set_style_pad_top(l, 5, LV_PART_MAIN);
		lv_obj_set_style_pad_bottom(l, 5, LV_PART_MAIN);
		panels_callbacks[i].init(l);
	}

	gui_update();
}

void midibox_gui_tab_mix_create(lv_obj_t * tab)
{
	lv_obj_t *o;
	lv_obj_t *l = tab;

	o = lv_btn_create(l);
	lv_label_set_text(lv_label_create(o), "Mute");
}

struct panel_callbacks pc_mix = {
	.init = midibox_gui_tab_mix_create,
};

