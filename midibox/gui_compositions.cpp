#include "midibox.h"
#include "gui.h"

String comp_filter = "";

lv_obj_t *comp_table;

const char *compositions [] = {
	"You hit the spot",
	"Taking chance on love",
	"Embraceable you",
	"Take the A train",
	"Obelix Samba",
};

static void comp_fill_table();

static void comp_fill_table()
{
	String s;
	MatchState ms;
	static String comp_filter_regex;
	comp_filter_regex = "";

	static const char *nummap[] = {"[0 ]", "[1]", "[2abcABC]", "[3defDEF]", "[4ghiGHI]", "[5jklJKL]", "[6mnoMNO]", "[7pqrsPQRS]", "[8tuvTUV]", "[9wxyzWXYZ]"};
	uint16_t i, j;

	for (i = 0; i < comp_filter.length(); i++) {
		char ch = comp_filter.charAt(i);
		if (ch >= '0' && ch <= '9') {
			comp_filter_regex += nummap[ch - '0'];
		}
	}
	lv_table_set_row_cnt(comp_table, 0);
	for (i = 0, j = 0; i < 5; i++) {
		s = compositions[i];
		ms.Target(s.begin());
		char result = ms.Match(comp_filter_regex.c_str(), 0);
		if (result)
			lv_table_set_cell_value(comp_table, j++, 0, compositions[i]);
	}
}

static bool gui_handle_button(uint8_t b, signed char state)
{
	switch (b) {
		case 0x0 ... 0x9:
			comp_filter += (char)('0' + b);
			comp_fill_table();
			return true;
		case 0xE:
			if (comp_filter.length()) {
//				comp_filter.remove(comp_filter.length()-1);
				comp_filter = "";
				comp_fill_table();
			} else {
				return false;
//				maintab_change(MT_INFO);
			}
			return true;
	}
	return false;
}

#if 0
static void comp_table_part_event_cb(lv_event_t * e)
{
	lv_obj_t * obj = lv_event_get_target(e);
	lv_obj_draw_part_dsc_t * dsc = lv_event_get_param(e);
	/*If the cells are drawn...*/
	if(dsc->part == LV_PART_ITEMS) {
		uint32_t row = dsc->id /  lv_table_get_col_cnt(obj);
		uint32_t col = dsc->id - row * lv_table_get_col_cnt(obj);

		/*Make the texts in the first cell center aligned*/
		if(row == 0) {
			dsc->label_dsc->align = LV_TEXT_ALIGN_CENTER;
			dsc->rect_dsc->bg_color = lv_color_mix(lv_palette_main(LV_PALETTE_BLUE), dsc->rect_dsc->bg_color, LV_OPA_20);
			dsc->rect_dsc->bg_opa = LV_OPA_COVER;
		}
		/*In the first column align the texts to the right*/
		else if(col == 0) {
			dsc->label_dsc->align = LV_TEXT_ALIGN_RIGHT;
		}
#if 0
		/*MAke every 2nd row grayish*/
		if((row != 0 && row % 2) == 0) {
			dsc->rect_dsc->bg_color = lv_color_mix(lv_palette_main(LV_PALETTE_GREY), dsc->rect_dsc->bg_color, LV_OPA_10);
			dsc->rect_dsc->bg_opa = LV_OPA_COVER;
		}
#endif
	}
}
#endif

static void comp_changed(lv_event_t * e)
{
/*
	lv_event_code_t code = lv_event_get_code(e);
	lv_obj_t * obj = lv_event_get_target(e);
	uint32_t user = (uint64_t) lv_event_get_user_data(e);
	if(code == LV_EVENT_VALUE_CHANGED) {
		uint32_t b = lv_btnmatrix_get_selected_btn(obj);
		if (user == 0) {
			if (layer_sel != b) {
				layer_select(b);
			} else {
				layer_enable(b, !layer_enabled[b]);
			}
		}
o	}
*/
}

void midibox_gui_tab_compositions(lv_obj_t *tab)
{
	lv_obj_t *o;
	lv_obj_t *l = tab;

	//lv_obj_t * ta = lv_textarea_create(tab);

	//lv_textarea_set_accepted_chars(ta, "0123456789:");
	//lv_textarea_set_text(ta, "");

	o = comp_table = lv_table_create(l);
	lv_obj_add_event_cb(o, comp_changed, LV_EVENT_VALUE_CHANGED, NULL);
//	lv_obj_set_y(o, 30);
	lv_table_set_row_cnt(o, 0);
	lv_table_set_col_cnt(o, 1);
	lv_table_set_col_width(o, 0, 280);
	//lv_table_set_row_height(o, 0, 280);

	comp_fill_table();
}

struct panel_callbacks pc_comps = {
	.button_pressed = gui_handle_button,
	.init = midibox_gui_tab_compositions,
};
