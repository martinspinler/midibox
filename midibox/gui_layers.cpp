#include "midibox.h"
#include "midi.h"
#include "gui.h"

static const char *layer_btn_text[]     = {"", "", "", "", "", "", "", "", ""};
static const char *layer_btn_text_sel[] = {"_", "_", "_", "_", "_", "_", "_", "_", ""};

static const char *layer_btn_text_def[] = {"1", "2", "3", "4", "5", "6", "7", "8", ""};
static const char *layer_btn_text_emp[] = {" ", " ", " ", " ", " ", " ", " ", " ", ""};
static const char *layer_btn_text_dis[] = {"#FF0000 1#", "#FF0000 2#", "#FF0000 3", "#FF0000 4", "#FF0000 5", "#FF0000 6", "#FF0000 7", "#FF0000 8", ""};
static const char *layer_btn_text_ena[] = {"#00FF00 1#", "#00FF00 2#", "#00FF00 3", "#00FF00 4", "#00FF00 5", "#00FF00 6", "#00FF00 7", "#00FF00 8", ""};

#define LI_NAME     0
#define LI_TRANSP   1
#define LI_RANGE    2
#define LI_VOL      3
#define LI_BEHAV    4
#define LI_PEDAL    5

#define LI_NUMBER_ITEMS 6

const char *layer_items_names[LI_NUMBER_ITEMS] = {"Name", "Transp.", "Range", "Volume", "Behav.", "Pedal 1"};
lv_obj_t *layer_cfg_label[LI_NUMBER_ITEMS];
lv_obj_t *layer_cfg_item[LI_NUMBER_ITEMS];
lv_obj_t *layer_volume_slider;
lv_obj_t *layer_btns;
lv_obj_t *layer_btns_sel;
lv_obj_t *layer_label_effect_pedal_value;
lv_obj_t *range_label_high, *range_label_low;

lv_obj_t *layer_items_leftlabel[LI_NUMBER_ITEMS];

uint8_t layer_sel = 0;

static uint8_t gui_state = 0;

static void layer_update_button_hints()
{
	lv_obj_t *o;
	uint8_t i;
	lv_area_t a;
	lv_coord_t abs_x1 = a.x1;

	for (i = 0; i < HINT_BTNS; i++) {
	}

	switch (gui_state) {
		case 0:
			lv_obj_add_flag(btn_hints[0], LV_OBJ_FLAG_HIDDEN);
			lv_obj_get_coords(layer_btns, &a);
			for (i = 1; i < 9; i++) {
				lv_obj_clear_flag(btn_hints[i], LV_OBJ_FLAG_HIDDEN);
				//lv_obj_set_pos(btn_hints[i], a.x1 - 1 + (i-1) * (a.x2-a.x1)/8, a.y1);
				lv_obj_set_pos(btn_hints[i], a.x1 - 1 + (i-1) * (a.x2-a.x1)/8 + (a.x2-a.x1)/16-4, a.y1+2);
			}

			lv_obj_get_coords(layer_items_leftlabel[0], &a);
			lv_obj_clear_flag(btn_hints[BTN_OK], LV_OBJ_FLAG_HIDDEN);
			lv_obj_set_pos(btn_hints[BTN_OK], a.x1-8, a.y1-8);
			break;

		case 1:
			for (i = 0; i < LI_NUMBER_ITEMS; i++) {
				lv_obj_clear_flag(btn_hints[i+1], LV_OBJ_FLAG_HIDDEN);
				lv_obj_get_coords(layer_items_leftlabel[i], &a);
				lv_obj_set_pos(btn_hints[i+1], a.x1 - 8, a.y1 - 8);
			}
			for (; i <= 9; i++)
				lv_obj_add_flag(btn_hints[i+1], LV_OBJ_FLAG_HIDDEN);
			lv_obj_add_flag(btn_hints[BTN_OK], LV_OBJ_FLAG_HIDDEN);

			lv_obj_get_coords(layer_btns, &a);
			lv_obj_clear_flag(btn_hints[BTN_BK], LV_OBJ_FLAG_HIDDEN);
			lv_obj_set_pos(btn_hints[BTN_BK], a.x1, a.y1);
			break;
	}
}

static void layer_enable_button_update(uint8_t i)
{
//	layer_btn_text[i] = ls[i].enabled ? layer_btn_text_ena[i] : layer_btn_text_dis[i];
	layer_btn_text[i] = layer_btn_text_def[i];
	lv_btnmatrix_set_map(layer_btns, layer_btn_text);
	ls[i].enabled ?
		lv_btnmatrix_set_btn_ctrl(layer_btns, i, LV_BTNMATRIX_CTRL_CHECKED) :
		lv_btnmatrix_clear_btn_ctrl(layer_btns, i, LV_BTNMATRIX_CTRL_CHECKED);
}

static void layer_select_button_update()
{
	lv_btnmatrix_set_btn_ctrl(layer_btns_sel, layer_sel, LV_BTNMATRIX_CTRL_CHECKED);
}

void layer_update()
{
	static const char *note_names[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};

	static char buf[8];
	static char rl[4];
	static char rh[4];
	static char effp[4];
	uint8_t l = layer_sel;

	int8_t ova, semi;

	lv_dropdown_set_selected(layer_cfg_item[LI_NAME], ls[l].program_index);
	lv_bar_set_start_value(layer_cfg_item[LI_RANGE], ls[l].lo, LV_ANIM_OFF);
	lv_slider_set_value(layer_cfg_item[LI_RANGE], ls[l].hi, LV_ANIM_OFF);
	lv_slider_set_value(layer_cfg_item[LI_VOL], ls[l].volume, LV_ANIM_OFF);
	//lv_slider_set_value(layer_cfg_item[LI_VOL], ls[l].volume, LV_ANIM_OFF);
	lv_dropdown_set_selected(layer_cfg_item[LI_PEDAL], ls[l].cc_pedal2_mode);

	lv_snprintf(buf, sizeof(buf), "%d", ls[l].volume);
	lv_label_set_text(layer_cfg_label[LI_VOL], buf);

	lv_snprintf(rl, sizeof(rl), "%s%d", note_names[ls[l].lo % 12], ls[l].lo / 12);
	lv_snprintf(rh, sizeof(rh), "%s%d", note_names[ls[l].hi % 12], ls[l].hi / 12);
	lv_label_set_text(range_label_low, rl);
	lv_label_set_text(range_label_high, rh);

	ova = ls[l].transposition / 12;
	semi = ls[l].transposition % 12;
	lv_spinbox_set_value(layer_cfg_item[LI_TRANSP], ova * 100 + semi);

	layer_enable_button_update(l);

	lv_snprintf(effp, sizeof(effp), "%d", ls[l].cc_expression);
	lv_label_set_text(layer_label_effect_pedal_value, effp);
}

void layer_select(uint8_t l)
{
	layer_sel = l;
	layer_select_button_update();
	layer_update();
}

void layer_config(uint8_t l)
{
	comm_1to2.layer.index = l;
	process_gui_cmd_send_to_midi(COMM_CMD_LAYER);

	layer_update();
}

void layer_enable(uint8_t l, bool enable)
{
	if (ls[l].enabled == enable)
		return;

	comm_1to2.layer.state = ls[l];
	comm_1to2.layer.state.enabled = enable;
	comm_1to2.layer.state.status = enable;
	layer_config(l);
}

bool layer_sel_enable(uint8_t l)
{
	if (layer_sel != l) {
		layer_select(l);
		return true;
	} else {
		layer_enable(l, !ls[l].enabled);
		return false;
	}
}

static bool gui_handle_button(uint8_t b, signed char state)
{
	bool handled = true;
	switch (gui_state) {
		case 0:
			switch (b) {
				case 0x1 ... 0x8:
					layer_sel_enable(b-1);
					break;
				case 0xF:
					gui_state = 1;
					break;
				default:
					handled = false;
					break;
			}
			break;
		case 1:
			switch (b) {
				case 0x1 ... 0x8:
					lv_group_focus_obj(layer_cfg_item[b-1]);
					lv_group_set_editing(lv_group_get_default(), true);
					break;
				case 0xE:
					gui_state = 0;
					break;
				case 0x10:
					ls[layer_sel].cc_expression += state;
					layer_update();
				default:
					handled = false;
					break;
			}
			break;
		default:
			handled = false;
			break;
	}

	layer_update_button_hints();
	return handled;
}

static void layer_btns_event(lv_event_t * e)
{
	lv_event_code_t code = lv_event_get_code(e);
	lv_obj_t * obj = lv_event_get_target(e);
	uint32_t user = (uint64_t) lv_event_get_user_data(e);
	uint32_t l = lv_btnmatrix_get_selected_btn(obj);
	if (code == LV_EVENT_VALUE_CHANGED) {
		if (user == 0) {
			layer_sel_enable(l);
		} else {
			layer_select(l);
		}
	}
}

static void layer_volume_event_cb(lv_event_t * e)
{
	lv_obj_t * slider = lv_event_get_target(e);
	int volume = (int)lv_slider_get_value(slider);

	comm_1to2.layer.state = ls[layer_sel];
	comm_1to2.layer.state.volume = volume;
	layer_config(layer_sel);
	layer_update();
 //   lv_obj_align_to(layer_cfg_item[LI_VOL], slider, LV_ALIGN_OUT_BOTTOM_MID, 0, 10);
}

static void program_change_event_cb(lv_event_t * e)
{
	comm_1to2.layer.state = ls[layer_sel];
	comm_1to2.layer.state.program_index = lv_dropdown_get_selected(layer_cfg_item[LI_NAME]);
	layer_config(layer_sel);
	layer_update();
}

static void lv_transp_increment_event_cb(lv_event_t * e)
{
	int8_t user = (int64_t) lv_event_get_user_data(e);
	lv_event_code_t code = lv_event_get_code(e);

	int32_t increment = 0, val;
	int8_t ova, semi;
	if (code == LV_EVENT_VALUE_CHANGED && user == 4) {
		val = ls[layer_sel].transposition;
		return;
#if 0
		val = lv_spinbox_get_value(layer_cfg_item[LI_TRANSP]);
		ova = val / 100;
		semi = val % 100;

		if (val > 0) {
			if (semi >= 12 && semi <= 50) {
				ova += 1;
				semi = 0;
//				val += 99;
			} else if (semi > 50 && semi <= 99) {
				ova -= 1;
				semi = 0;
//				val += 99;
			}

//			if (val % 100 == 99)
//				val -= 99;
		}
		val = ova * 100 + semi;
#endif
	} else if (code == LV_EVENT_PRESSED) {
		val = ls[layer_sel].transposition;
		switch (user) {
			case 0: val += -12; break;
			case 1: val +=  -1; break;
			case 2: val +=   1; break;
			case 3: val +=  12; break;
		}
	} else {
		return;
	}

	if (val > 12*8)
		val = 12*8;
	if (val < -12*8)
		val = -12*8;

	if (val != ls[layer_sel].transposition) {
		comm_1to2.layer.state = ls[layer_sel];
		comm_1to2.layer.state.transposition = val;
		layer_config(layer_sel);
	}
	layer_update();
}

static void layer_range_event_cb(lv_event_t * e)
{
	int8_t user = (int64_t) lv_event_get_user_data(e);
	//lv_event_code_t code = lv_event_get_code(e);
	//comm_1to2.command = CMD_GET_ONE_KEY;
	//comm_1to2.param = user == 1 ? CMD_SET_RANGE_LOW : CMD_SET_RANGE_HIGH;
}

static void layer_note_behaviour_event_cb(lv_event_t * e)
{
	uint8_t cfg;
	cfg = lv_dropdown_get_selected(layer_cfg_item[LI_BEHAV]);

	comm_1to2.layer.state = ls[layer_sel];

	switch (cfg) {
		case 0: cfg = NOTE_MODE_NORMAL; break;
		case 1: cfg = NOTE_MODE_HOLDTONEXT; break;
		case 2: cfg = NOTE_MODE_HOLD1_2; break;
		case 3: cfg = NOTE_MODE_HOLD1_4; break;
		case 4: cfg = NOTE_MODE_CUT1_4; break;
		case 5: cfg = NOTE_MODE_SHUFFLE; break;
		default: return;
	}
	comm_1to2.layer.state = ls[layer_sel];
	comm_1to2.layer.state.mode = cfg;

	layer_config(layer_sel);
}

static void layer_pedal_behaviour_event_cb(lv_event_t * e)
{
	uint8_t cfg;
	cfg = lv_dropdown_get_selected(layer_cfg_item[LI_PEDAL]);

	comm_1to2.layer.state = ls[layer_sel];
/*
	switch (cfg) {
		case 0: cfg = PEDAL_MODE_IGNORE; break;
		case 1: cfg = PEDAL_MODE_NORMAL; break;
		case 2: cfg = PEDAL_MODE_NOTELENGTH; break;
		case 3: cfg = PEDAL_MODE_TOGGLE_EN; break;
		default: return;
	}
*/
	comm_1to2.layer.state = ls[layer_sel];
	comm_1to2.layer.state.cc_pedal2_mode = cfg;

	layer_config(layer_sel);
}

void midibox_gui_tab_layer_create(lv_obj_t * tab)
{
	lv_obj_t *o;
	lv_obj_t *l;

	l = tab;

	static lv_coord_t tab_layers_top_col_dsc[] = {LV_GRID_FR(1), LV_GRID_TEMPLATE_LAST};
	static lv_coord_t tab_layers_top_row_dsc[] = {25, 5, LV_GRID_FR(1), LV_GRID_TEMPLATE_LAST};

	lv_obj_set_style_pad_all(l, 0, LV_PART_MAIN);
	lv_obj_set_style_pad_top(l, 2, LV_PART_MAIN);

	lv_obj_set_style_grid_column_dsc_array(l, tab_layers_top_col_dsc, 0);
	lv_obj_set_style_grid_row_dsc_array(l, tab_layers_top_row_dsc, 0);
	lv_obj_set_grid_align(l, LV_GRID_ALIGN_SPACE_EVENLY, LV_GRID_ALIGN_SPACE_EVENLY);
	lv_obj_set_layout(l, LV_LAYOUT_GRID);
	lv_obj_center(l);
	lv_obj_set_style_pad_row(l, 0, 0);

	static lv_style_t style_bg;
	lv_style_init(&style_bg);
	lv_style_set_pad_all(&style_bg, 0);
	lv_style_set_pad_gap(&style_bg, 0);
	lv_style_set_clip_corner(&style_bg, true);
	lv_style_set_radius(&style_bg, 0);
	lv_style_set_border_width(&style_bg, 0);

	static lv_style_t style_btn;
	lv_style_init(&style_btn);
	//lv_style_set_pad_all(&style_btn, 0);
	//lv_style_set_pad_gap(&style_btn, 0);
	lv_style_set_radius(&style_btn, 0);
	lv_style_set_border_width(&style_btn, 1);
	lv_style_set_border_opa(&style_btn, LV_OPA_50);
	lv_style_set_border_color(&style_btn, lv_palette_main(LV_PALETTE_GREY));
	lv_style_set_border_side(&style_btn, LV_BORDER_SIDE_INTERNAL);
	lv_style_set_radius(&style_btn, 0);

	uint8_t i;
	o = layer_btns = lv_btnmatrix_create(l);
	for (i = 0; i < 8; i++) {
		//layer_btn_text[i] = layer_btn_text_dis[i];
		layer_btn_text[i] = layer_btn_text_def[i];
	}
	lv_obj_add_event_cb(o, layer_btns_event, LV_EVENT_VALUE_CHANGED, (void *)0);
	lv_btnmatrix_set_map(layer_btns, layer_btn_text);
	for (i = 0; i < 8; i++) {
		//lv_btnmatrix_set_btn_ctrl(layer_btns, i, LV_BTNMATRIX_CTRL_RECOLOR);
		lv_btnmatrix_set_btn_ctrl(layer_btns, i, LV_BTNMATRIX_CTRL_CHECKABLE);
		lv_btnmatrix_set_btn_ctrl(layer_btns, i, LV_BTNMATRIX_CTRL_CLICK_TRIG);	
	}
	lv_obj_add_style(layer_btns, &style_bg, 0);
	lv_obj_add_style(layer_btns, &style_btn, LV_PART_ITEMS);

	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 0, 1, LV_GRID_ALIGN_STRETCH, 0, 1);
	lv_obj_set_grid_align(o, LV_GRID_ALIGN_SPACE_EVENLY, LV_GRID_ALIGN_SPACE_EVENLY);

	o = layer_btns_sel = lv_btnmatrix_create(l);
	lv_obj_add_event_cb(o, layer_btns_event, LV_EVENT_VALUE_CHANGED, (void *)1);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 0, 1, LV_GRID_ALIGN_STRETCH, 1, 1);
	lv_obj_add_style(o, &style_bg, 0);
	lv_obj_add_style(o, &style_btn, LV_PART_ITEMS);
	lv_btnmatrix_set_one_checked(o, true);
	lv_btnmatrix_set_map(o, layer_btn_text_sel);
	for (i = 0; i < 8; i++) {
		lv_btnmatrix_set_btn_ctrl(o, i, LV_BTNMATRIX_CTRL_RECOLOR);
		lv_btnmatrix_set_btn_ctrl(o, i, LV_BTNMATRIX_CTRL_CHECKABLE);
	}
	lv_btnmatrix_set_btn_ctrl(o, 0, LV_BTNMATRIX_CTRL_CHECKED);

	static const char *panel_text[] = {"Main", "Pedals"};

//	lv_obj_t * tabview = l = lv_tabview_create(tab, LV_DIR_TOP, 32);
//	lv_obj_set_style_pad_top(l, 40, LV_PART_MAIN);
//	l = lv_tabview_add_tab(tabview, panel_text[0]);

//	static lv_coord_t tab_layers_col_dsc[] = {60, LV_GRID_FR(2), LV_GRID_FR(1) LV_GRID_FR(6), LV_GRID_FR(1), LV_GRID_TEMPLATE_LAST};
	static lv_coord_t tab_layers_col_dsc[] = {60, LV_GRID_FR(2), LV_GRID_FR(1), LV_GRID_FR(6), LV_GRID_FR(1), LV_GRID_FR(2), LV_GRID_TEMPLATE_LAST};
	const uint8_t spacer = 0;
	static lv_coord_t tab_layers_row_dsc[LI_NUMBER_ITEMS+1] = {LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_FR(2), LV_GRID_TEMPLATE_LAST};

	l = lv_obj_create(l);
	lv_obj_set_style_pad_all(l, 0, LV_PART_MAIN);
	lv_obj_set_style_pad_top(l, 5, LV_PART_MAIN);
	//lv_obj_remove_style_remove_prop(l, o&style, LV_STYLE_BG_COLOR);
//	lv_obj_set_style_bg_color(l, lv_palette_main(LV_PALETTE_NONE), LV_PART_MAIN);
	lv_obj_set_style_bg_opa(l, LV_OPA_TRANSP, LV_PART_MAIN);
	lv_obj_set_style_border_width(l, 0, LV_PART_MAIN);
	lv_obj_set_style_grid_column_dsc_array(l, tab_layers_col_dsc, 0);
	lv_obj_set_style_grid_row_dsc_array(l, tab_layers_row_dsc, 0);
	lv_obj_set_grid_align(l, LV_GRID_ALIGN_SPACE_EVENLY, LV_GRID_ALIGN_SPACE_EVENLY);
	lv_obj_set_grid_cell(l, LV_GRID_ALIGN_STRETCH, 0, 1, LV_GRID_ALIGN_STRETCH, 2, 1);
	lv_obj_set_layout(l, LV_LAYOUT_GRID);
	lv_obj_center(l);
	lv_obj_set_style_pad_row(l, 0, 0);

	uint8_t row = 0;
	const bool create_label[LI_NUMBER_ITEMS] = {false, false, true, true, false, false};
	
	for (i = 0; i < LI_NUMBER_ITEMS; i++) {
		o = layer_items_leftlabel[i] = lv_label_create(l);
		lv_label_set_text(o, layer_items_names[i]);
		lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 0, 1, LV_GRID_ALIGN_CENTER, row, 1);
		if (create_label[i]) {
			o = layer_cfg_label[i] = lv_label_create(l);
			lv_label_set_text(o, "");
			lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 1, 5, LV_GRID_ALIGN_CENTER, row, 1);
		}
		row++;
	}

	static String program_names = "";
	for (i = 0; midi_programs[i].name != 0; i++) {
		if (i)
			program_names += "\n";
		program_names += midi_programs[i].name;
	}
	/* Program name */
	row = LI_NAME;
	o = layer_cfg_item[row] = lv_dropdown_create(l); 	
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 1, 5, LV_GRID_ALIGN_CENTER, row, 1);

	lv_dropdown_set_options(o, program_names.c_str());
	lv_obj_set_style_pad_top(o, 2, LV_PART_MAIN);
	lv_obj_set_style_pad_bottom(o, 2, LV_PART_MAIN);
	lv_obj_add_event_cb(o, program_change_event_cb, LV_EVENT_VALUE_CHANGED, (void *)(uint32_t)4);

	/* Transpose */
	row = LI_TRANSP;
	o = layer_cfg_item[row] = lv_spinbox_create(l);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 3, 1, LV_GRID_ALIGN_CENTER, row, 1);
	lv_spinbox_set_digit_format(o, 3, 1);
	lv_obj_set_style_pad_left(o, 20, LV_PART_MAIN);
	lv_obj_set_style_pad_right(o, 20, LV_PART_MAIN);
	lv_spinbox_set_value(o, 0);
	lv_spinbox_set_range(o, -800, 800);
	lv_spinbox_set_rollover(o, false);
	lv_obj_add_event_cb(o, lv_transp_increment_event_cb, LV_EVENT_VALUE_CHANGED, (void *)(uint32_t)4);

	for (i = 0; i < 4; i++) {
		o = lv_btn_create(l);
		lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, i < 2 ?  (i + 1) : (i + 2), 1, LV_GRID_ALIGN_CENTER, row, 1);
		lv_obj_set_style_pad_all(o, 0, LV_PART_MAIN);
		lv_obj_set_style_pad_left(o, 3, LV_PART_MAIN);

		lv_obj_t*label = lv_label_create(o);
		switch (i) {
			case 0: lv_label_set_text(label, LV_SYMBOL_MINUS " " LV_SYMBOL_MINUS); break;
			case 1: lv_label_set_text(label, LV_SYMBOL_MINUS); break;
			case 2: lv_label_set_text(label, LV_SYMBOL_PLUS); break;
			case 3: lv_label_set_text(label, LV_SYMBOL_PLUS " " LV_SYMBOL_PLUS); break;
		}
		lv_obj_add_event_cb(o, lv_transp_increment_event_cb, LV_EVENT_PRESSED, (void*)(uintptr_t)i);
	}

	/* Volume */
	row = LI_VOL;
	o = layer_cfg_item[row] = lv_slider_create(l);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 1, 4, LV_GRID_ALIGN_CENTER, row, 1);
	lv_obj_set_style_pad_all(o, -15, LV_PART_KNOB);
	lv_obj_add_event_cb(o, layer_volume_event_cb, LV_EVENT_VALUE_CHANGED, NULL);
	lv_slider_set_range(o, 0, 127);
	o = layer_cfg_label[row];
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_START, 5, 1, LV_GRID_ALIGN_STRETCH, row, 1);

	/* Range */
	row = LI_RANGE;
	o = layer_cfg_item[row] = lv_slider_create(l);
	lv_slider_set_range(o, 0, 127);
	lv_bar_set_start_value(o, 0, LV_ANIM_OFF);
	lv_slider_set_mode(o, LV_SLIDER_MODE_RANGE);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 3, 1, LV_GRID_ALIGN_CENTER, row, 1);
	lv_obj_set_style_pad_all(o, -15, LV_PART_KNOB);
	o = lv_btn_create(l);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 1, 2, LV_GRID_ALIGN_CENTER, row, 1);
	lv_obj_add_event_cb(o, layer_range_event_cb, LV_EVENT_VALUE_CHANGED, (void*)0);
	o = range_label_low = lv_label_create(o);
	lv_label_set_text(o, "C0");
	o = lv_btn_create(l);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 4, 2, LV_GRID_ALIGN_CENTER, row, 1);
	lv_obj_add_event_cb(o, layer_range_event_cb, LV_EVENT_VALUE_CHANGED, (void*)1);
	o = range_label_high = lv_label_create(o);
	lv_label_set_text(o, "C0");

	/* Note behaviour */
	row = LI_BEHAV;
	o = layer_cfg_item[row] = lv_dropdown_create(l); 	
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 1, 5, LV_GRID_ALIGN_CENTER, row, 1);
	lv_dropdown_set_options(o, "Normal\nHold until next\nHold 1/4\nHold 1/2\nCut 1/4\nShuffle");
	lv_obj_add_event_cb(o, layer_note_behaviour_event_cb, LV_EVENT_VALUE_CHANGED, (void*)1);
	lv_obj_set_style_pad_top(o, 2, LV_PART_MAIN);
	lv_obj_set_style_pad_bottom(o, 2, LV_PART_MAIN);

	/* Switch pedal behaviour */
	row = LI_PEDAL;
	o = layer_cfg_item[row] = lv_dropdown_create(l);
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 1, 4, LV_GRID_ALIGN_CENTER, row, 1);
	/* FIXME: Rewrite toggle enable to MUTE */
	lv_dropdown_set_options(o, "Ignore\nNormal\nNote length\nToggle enable");
	lv_obj_add_event_cb(o, layer_pedal_behaviour_event_cb, LV_EVENT_VALUE_CHANGED, (void*)1);
	lv_obj_set_style_pad_top(o, 2, LV_PART_MAIN);
	lv_obj_set_style_pad_bottom(o, 2, LV_PART_MAIN);

	layer_label_effect_pedal_value = o = lv_label_create(l);
	lv_label_set_text(o, "");
	lv_obj_set_grid_cell(o, LV_GRID_ALIGN_STRETCH, 5, 1, LV_GRID_ALIGN_CENTER, row, 1);
//	lv_obj_set_style_pad_top(lv_obj_get_child(o, 0),-5, LV_PART_MAIN);

	/* TODO: Add 'affected by SysEx' for program change */

//	lv_obj_t *label
#if 0
	static lv_style_t style_slider;
	lv_style_init(&style_slider);
	//lv_style_set_pad_all(&style_btn, 0);
	//lv_style_set_pad_gap(&style_btn, 0);
//	lv_style_set_radius(&style_slider, 5);
//	lv_style_set_max_width(&style_slider, 10);
	lv_style_set_pad_all(&style_slider, -3);
	lv_obj_add_style(o, &style_slider, LV_PART_KNOB);
//	lv_style_set_pad_all(&style_slider, -6);
//	lv_obj_add_style(o, &style_slider, LV_PART_MAIN);
#endif

	for (i = 0; i < LAYERS; i++)
		layer_enable_button_update(i);
	//layer_update(0);
}

void gui_layers_update()
{
	uint8_t i;
	gui_state = 0;
	for (i = 0; i < LAYERS; i++)
		layer_enable_button_update(i);
	layer_update();
	layer_update_button_hints();
}

struct panel_callbacks pc_layers = {
	.button_pressed = gui_handle_button,
	.init = midibox_gui_tab_layer_create,
	.update = gui_layers_update,
};
