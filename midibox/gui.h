#include "midibox.h"

#define MT_INFO     0
#define MT_LAYERS   1
#define MT_COMPS    2
#define MT_CONFIG   3

#define MT_MAX_PANELS 4

void maintab_change(int l);

struct panel_callbacks {
	bool (*button_pressed)(uint8_t b, signed char state);
	void (*init)(lv_obj_t *l);
	void (*update)();
};

extern struct panel_callbacks *current_panel;

extern struct time_s current_time;

#define HINT_BTNS 16
enum BTNS {BTN_A = 10, BTN_B, BTN_C, BTN_D, BTN_BK, BTN_OK};
extern lv_obj_t *btn_hints[HINT_BTNS];
