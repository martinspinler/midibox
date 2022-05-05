#include "midibox.h"
#include "midi.h"
#include "gui.h"

extern struct time_s current_time;
extern lv_obj_t *comp_table;

lv_obj_t *label_time;
lv_obj_t *gui_info_status;

void get_current_time(struct time_s & time);
void midi_layers_load_quick_setting(uint8_t qs);

extern char config_enable;

extern volatile unsigned long tempo;

static const char *layer_btn_text[] = {"_", "_", "_", "_", "_", "_", "_", "_", ""};
static lv_obj_t *layer_btns;
static lv_obj_t *switch_enable;

static lv_obj_t *label_tempo;
static lv_obj_t *metronome_leds[4];

extern struct panel_callbacks pc_info;

static void gui_update_rt()
{
	uint8_t i;
	for (i = 0; i < 8; i++) {
		layer_btn_text[i] = midi_programs[ls[i].program_index].short_name;
		ls[i].enabled ?
			lv_btnmatrix_set_btn_ctrl(layer_btns, i, LV_BTNMATRIX_CTRL_CHECKED) :
			lv_btnmatrix_clear_btn_ctrl(layer_btns, i, LV_BTNMATRIX_CTRL_CHECKED);
	}

	lv_btnmatrix_set_map(layer_btns, layer_btn_text);
}

static void gui_update()
{
	uint8_t i;

#if 0
	/* INFO: workaround for call from metronome timer */
	if (current_panel != &pc_info) {
		return;
	}
#endif
	for (i = 0; i < HINT_BTNS; i++) {
	}

	lv_area_t a;
	lv_coord_t abs_x1 = a.x1;
	lv_obj_get_coords(layer_btns, &a);
	for (i = 0x0A; i <= 0x0D; i++) {
		//lv_obj_set_pos(btn_hints[i], a.x1 - 1 + (i-1) * (a.x2-a.x1)/8, a.y1);
	}
	gui_update_rt();
}


static void midibox_midi_enable(uint8_t enabled)
{
	comm_1to2.enable = enabled;
	process_gui_cmd_send_to_midi(COMM_CMD_ENABLE);

	if (enabled && !lv_obj_has_state(switch_enable, LV_STATE_CHECKED))
		lv_obj_add_state(switch_enable, LV_STATE_CHECKED);
	else if (!enabled && lv_obj_has_state(switch_enable, LV_STATE_CHECKED))
		lv_obj_clear_state(switch_enable, LV_STATE_CHECKED);
}

void switch_enable_value_changed(lv_event_t * e)
{
	midibox_midi_enable(lv_obj_has_state(switch_enable, LV_STATE_CHECKED));
}

static bool gui_handle_button(uint8_t b, signed char state)
{
	switch (b) {
		case 0:
			midibox_midi_enable(!config_enable);
			return true;
		case 1 ... 9:
			midi_layers_load_quick_setting(b);
			gui_update();
			return true;
			/*
		case 0xA .. 0xD:
			return false;
			maintab_change(MT_INFO);
			return true;
		case 0xB:
			maintab_change(MT_LAYERS);
			return true;
		case 0xC:
			maintab_change(MT_COMPS);
			return true;
		case 0xD:
			maintab_change(MT_CONFIG);
			return true;
			*/
		case 0xE: /* TODO: Next scene */
			return true;
		case 0xF: /* TODO: Next part */
			return true;
		case 0x10:
			midi_change_tempo(tempo + state);
			return true;
	}
	return false;
}

void update_time_timer(lv_timer_t * timer)
{
//	uint32_t * user_data = timer->user_data;
	static String time;
	get_current_time(current_time);
/*
	time = String(current_time.hour) + ":" + String(current_time.minute) + ":" + String(current_time.second)
		+ " " + String(current_time.day) + "." + String(current_time.month) + "." + String(current_time.year);
*/
//	time = String(current_time.hour) + ":" + String(current_time.minute) + ":" + String(current_time.second);
	static char buf[10];
	lv_snprintf(buf, sizeof(buf), "%02d:%02d:%02d", current_time.hour, current_time.minute, current_time.second);
	lv_label_set_text(label_time, buf);
//	lv_label_set_text(label_time, time.c_str());
}

void midi_handle_tc(void);

void update_metronome_timer(lv_timer_t *timer)
{
	uint8_t i;
	static char buf[32];

	for (i = 0; i < ARRAY_SIZE(metronome_leds); i++) {
		mc.q == i ?
			lv_led_on(metronome_leds[i]) :
			lv_led_off(metronome_leds[i]);
	}

	lv_snprintf(buf, sizeof(buf), "%d bpm, 4/4", tempo);
	lv_label_set_text(label_tempo, buf);

	/* TODO */
	static uint8_t x = 0;
	if ((x++ % 4) == 0) {
		update_time_timer(timer);
		gui_update_rt();
	}
}

static lv_color_t layer_btns_color[LAYERS];

static void layer_btns_event_cb(lv_event_t * e)
{
	lv_event_code_t code = lv_event_get_code(e);
	lv_obj_t * obj = lv_event_get_target(e);
	if(code == LV_EVENT_DRAW_PART_BEGIN) {
		lv_obj_draw_part_dsc_t * dsc = (lv_obj_draw_part_dsc_t*)lv_event_get_param(e);
		if (ls[dsc->id].enabled)
			dsc->rect_dsc->bg_color = ls[dsc->id].enabled ? layer_btns_color[dsc->id] : lv_palette_main(LV_PALETTE_GREY);
	}
}

static void gui_create(lv_obj_t * tab)
{
	uint8_t i;
	lv_obj_t *o;
	lv_obj_t *l = tab;
	static lv_style_t style_bg;
	static lv_style_t style_btn;
	lv_style_init(&style_btn);
	//lv_style_set_bg_color(&style_btn, lv_color_hex(0x115588));
	lv_style_set_bg_opa(&style_btn, LV_OPA_50);
	lv_style_set_border_width(&style_btn, 5);
	lv_style_set_border_color(&style_btn, lv_color_black());

///	lv_obj_set_style_pad_all(l, 0, LV_PART_MAIN);

	static lv_style_t style_btn_red;
	lv_style_init(&style_btn_red);
	lv_style_set_bg_color(&style_btn_red, lv_palette_main(LV_PALETTE_RED));
//	lv_style_set_pad_top(&style_btn, 20);
//	lv_style_set_x(&style_btn, 50);

	lv_style_init(&style_bg);
	lv_style_set_pad_all(&style_bg, 0);
	lv_style_set_pad_gap(&style_bg, 0);
	lv_style_set_clip_corner(&style_bg, true);
	lv_style_set_radius(&style_bg, 0);
	lv_style_set_border_width(&style_bg, 0);

//	static lv_style_t style_btn;
	lv_style_reset(&style_btn);
	//lv_style_set_pad_all(&style_btn, 0);
	//lv_style_set_pad_gap(&style_btn, 0);
	lv_style_set_radius(&style_btn, 0);
	lv_style_set_border_width(&style_btn, 1);
	lv_style_set_border_opa(&style_btn, LV_OPA_50);
	lv_style_set_border_color(&style_btn, lv_palette_main(LV_PALETTE_GREY));
	lv_style_set_border_side(&style_btn, LV_BORDER_SIDE_INTERNAL);
	lv_style_set_radius(&style_btn, 0);

	static lv_coord_t tab_layers_col_dsc[] = {50, LV_GRID_FR(1), LV_GRID_FR(1), LV_GRID_FR(1), LV_GRID_FR(1), LV_GRID_TEMPLATE_LAST};
	static lv_coord_t tab_layers_row_dsc[] = {LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_TEMPLATE_LAST};

	lv_obj_set_style_grid_column_dsc_array(l, tab_layers_col_dsc, 0);
	lv_obj_set_style_grid_row_dsc_array(l, tab_layers_row_dsc, 0);

	lv_obj_set_style_pad_all(l, 0, LV_PART_MAIN);
	lv_obj_set_style_pad_top(l, 2, LV_PART_MAIN);

	lv_obj_set_layout(l, LV_LAYOUT_GRID);
	lv_obj_center(l);
	lv_obj_set_style_pad_row(l, 0, 0);
//	lv_obj_set_style_pad_column(l, 0, 0);

	layer_btns_color[0] = lv_palette_main(LV_PALETTE_RED);
	layer_btns_color[1] = lv_palette_main(LV_PALETTE_GREEN);
	layer_btns_color[2] = lv_palette_main(LV_PALETTE_BLUE);
	layer_btns_color[3] = lv_palette_main(LV_PALETTE_YELLOW);
	layer_btns_color[4] = lv_palette_main(LV_PALETTE_CYAN);
	layer_btns_color[5] = lv_palette_main(LV_PALETTE_TEAL);
	layer_btns_color[6] = lv_palette_main(LV_PALETTE_DEEP_ORANGE);
	layer_btns_color[7] = lv_palette_main(LV_PALETTE_AMBER);

	o = layer_btns = lv_btnmatrix_create(l);
	lv_obj_add_event_cb(o, layer_btns_event_cb, LV_EVENT_ALL, NULL);

	const int CS = ARRAY_SIZE(tab_layers_col_dsc) - 2;
	uint8_t row = 0;

	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 0, CS+1, LV_GRID_ALIGN_STRETCH, row, 1);

//	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 0, CS+1, LV_GRID_ALIGN_STRETCH, row, 1);
	lv_obj_set_grid_align(o, LV_GRID_ALIGN_SPACE_EVENLY, LV_GRID_ALIGN_SPACE_EVENLY);
	for (i = 0; i < 8; i++) {
		layer_btn_text[i] = midi_programs[ls[i].program_index].short_name;
	}
	lv_btnmatrix_set_map(layer_btns, layer_btn_text);
	lv_obj_add_style(layer_btns, &style_bg, 0);
	lv_obj_add_style(layer_btns, &style_btn, LV_PART_ITEMS);
	row++;

	o = lv_label_create(l);
	lv_label_set_text(o, "Comp");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 0, 1, LV_GRID_ALIGN_STRETCH, row, 1);
	//lv_obj_add_style(o, &style_btn, 0);
	o = lv_label_create(l);
	lv_label_set_text(o, "-");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 1, CS, LV_GRID_ALIGN_STRETCH, row, 1);
	row++;

	o = lv_label_create(l);
	lv_label_set_text(o, "Section");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 0, 1, LV_GRID_ALIGN_STRETCH, row, 1);
	gui_info_status = o = lv_label_create(l);
	lv_label_set_text(o, "bridge");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 1, CS, LV_GRID_ALIGN_STRETCH, row, 1);
	row++;

#if 0
	o = lv_label_create(l);
	lv_label_set_text(o, "Enable");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 0, 1, LV_GRID_ALIGN_STRETCH, row, 1);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 0, 1, LV_GRID_ALIGN_STRETCH, row+1, 1);
#endif


	row++;

	label_tempo = o = lv_label_create(l);
	lv_label_set_text(o, "Tempo");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 0, 1, LV_GRID_ALIGN_STRETCH, row, 1);
	label_tempo = o = lv_label_create(l);
	lv_label_set_text(o, "120 bpm, 4/4");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 1, CS, LV_GRID_ALIGN_STRETCH, row, 1);

	label_time = o = lv_label_create(l);
	lv_label_set_text(o, "88:88:88");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 3, 3, LV_GRID_ALIGN_STRETCH, row, 1);
	row++;

	switch_enable = o = lv_switch_create(l);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 1, 1, LV_GRID_ALIGN_START, row, 1);
	lv_obj_set_style_max_height(o, 25, LV_PART_MAIN);
//	lv_obj_set_style_pad_all(o, -25, LV_PART_MAIN);
	lv_obj_set_style_pad_all(o, -5, LV_PART_KNOB);
//	lv_obj_set_style_radius(o, 5, LV_PART_MAIN);
	lv_obj_add_event_cb(switch_enable, switch_enable_value_changed, LV_EVENT_VALUE_CHANGED, NULL);
	lv_obj_set_grid_cell(switch_enable, LV_GRID_ALIGN_START, 0, 1, LV_GRID_ALIGN_START, row, 1);

	for (i = 0; i < ARRAY_SIZE(metronome_leds); i++) {
		metronome_leds[i] = o = lv_led_create(l);
		lv_obj_set_style_pad_all(o, 0, LV_PART_MAIN);
		lv_obj_set_style_pad_top(o, -15, LV_PART_MAIN);
//		lv_obj_set_style_max_height(o, 25, LV_PART_MAIN);
		lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, i+1, 1, LV_GRID_ALIGN_START, row, 1);
		lv_led_set_color(o, i == 0 ? lv_palette_main(LV_PALETTE_RED) : lv_palette_main(LV_PALETTE_GREEN));
		lv_led_off(o);
	}
	row++;

//	static lv_timer_t *timer = lv_timer_create(update_time_timer, 1000, NULL);
	static lv_timer_t *timer2 = lv_timer_create(update_metronome_timer, 50, NULL);
}

struct panel_callbacks pc_info = {
	.button_pressed = gui_handle_button,
	.init = gui_create,
	.update = gui_update,
};
