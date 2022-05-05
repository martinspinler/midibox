#ifdef ARDUINO
#include <Arduino.h>
#include <lvgl.h>

#define ILI9341_DRIVER
#define TFT_MISO    16
#define TFT_MOSI    19
#define TFT_SCLK    18
#define TFT_CS      17
#define TFT_DC      21
#define TFT_RST     20
#define TOUCH_CS    22
#define SPI_FREQUENCY       70000000
#define SPI_READ_FREQUENCY  20000000
#define SPI_TOUCH_FREQUENCY  2500000
#define USER_SETUP_LOADED
#include <TFT_eSPI.h>

#include "RTCDS1307.h"
#include "PCF8574.h"

#include <SPI.h>
#define SDCARD_SPI SPI1
#include <RP2040_SD.h>

#include "midibox.h"

/* Pin definitions */
#define ROT_ENC_BTN 3
#define ROT_ENC_A 4
#define ROT_ENC_B 5

#define SWITCH1 6
#define SWITCH2 7
#define SWITCH3 2

#ifdef MATRIX_KBD_DIRECT
#define KBD_ROW 8
#define KBD_COL 12
#endif

extern volatile int16_t rot_enc;
extern volatile uint32_t enc_last32;
extern volatile uint32_t enc_last32b;

static const uint16_t screenWidth  = 320;
static const uint16_t screenHeight = 240;

static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[screenWidth * 32];

Sd2Card card;
SdVolume volume;
RP2040_SDLib::File root;

TFT_eSPI tft = TFT_eSPI(screenHeight, screenWidth);
RTCDS1307 rtc(0x68);

PCF8574 PCF(0x20, &Wire1);

volatile int16_t rot_enc = 0;

static uint8_t pa, pb;

volatile uint32_t enc_last32 = 0;
volatile uint32_t enc_last32b = 0;

void midibox_display_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p)
{
	uint32_t w = (area->x2 - area->x1 + 1);
	uint32_t h = (area->y2 - area->y1 + 1);

	tft.startWrite();
	tft.setAddrWindow( area->x1, area->y1, w, h);
	tft.pushColors((uint16_t *)&color_p->full, w * h, true);
	tft.endWrite();

	lv_disp_flush_ready(disp);
}

void midibox_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data)
{
	uint16_t touchX, touchY;
	bool touched = tft.getTouch( &touchX, &touchY, 600 );

	if(!touched) {
		data->state = LV_INDEV_STATE_REL;
	} else {
		data->state = LV_INDEV_STATE_PR;
		data->point.x = touchX;
		data->point.y = touchY;
	}
}

void midibox_encoder_read(lv_indev_drv_t * drv, lv_indev_data_t *data)
{
#if 0
	data->enc_diff = enc_get_new_moves();

	if (enc_pressed())
		data->state = LV_INDEV_STATE_PRESSED;
	else
	#endif
		data->state = LV_INDEV_STATE_RELEASED;
}

void input_check_rot_enc()
{
	static unsigned long locktime;
	static uint8_t lock = 0;

	uint8_t a, b;
	unsigned long us;

	a = digitalRead(ROT_ENC_A);

	if (a == pa)
		return;
	pa = a;
	us = micros();

	if (a == 0) {
		if (locktime < us) {
			lock = 0;
			pb = 2;
		}
		if (lock)
			return;
		b = digitalRead(ROT_ENC_B);
		if (b == pb)
			return;
		lock = 1;
//		if (rot_enc == 0 || (rot_enc > 0 && b) || (rot_enc < 0 && !b))
			rot_enc += b ? -1 : 1;
	} else {
		b = digitalRead(ROT_ENC_B);
		if (lock && b == pb)
			return;
		lock = 0;
	}

	pb = b;
	locktime = us + 150000;
#if 0
	static uint8_t a, b;
	a = digitalRead(ROT_ENC_A);
	b = digitalRead(ROT_ENC_B);

	if (a && b && a != pa) {
		rot_enc++;
	} else if (pa == a && pb != b) {
		rot_enc--;
	}
	pa = a;
	pb = b;
#endif
#if 0
	static uint8_t last_change = 0;
	static uint8_t i, enc_last, j;
	static uint8_t p = 0;
	if (last_change) {
		last_change--;
		return;
	}

	i = digitalRead(ROT_ENC_A);
	j = digitalRead(ROT_ENC_B);
	if ((enc_last == LOW) && (i == HIGH)) {
		if (p == 0)
			p = 31;
		if (j == LOW) {
			if (rot_enc<= 0)
			rot_enc--;
			//midibox_handle_button(16, 1);
			//encoder0Pos--;
		} else {
			if (rot_enc >= 0)
			rot_enc++;
			//midibox_handle_button(17, 2);
			//encoder0Pos++;
		}
		last_change = 100;
	}
	enc_last = i;
	if (p > 0) {
		enc_last32 <<= 1;
		enc_last32 |= i;

		enc_last32b <<= 1;
		enc_last32b |= i;
		p--;
	}
#endif
}

void midibox_io_check_input()
{
	static const char btn_map[16] = {1,2,3,0xA,4,5,6,0xB,7,8,9,0xC,14,0,15,0xD};// {0xD, 0xC, 0xB,  14, 15, 9, 6, 2, 0, 8, 5, 3, 14, 7, 4, 0xA};
	static uint32_t btn_state = 0;
	static uint32_t btn_mask;
	static char enc_last;
	uint8_t i;
	uint8_t btn;

#ifdef MATRIX_KBD_DIRECT
	static uint16_t buttonTimer = 0;
	if (buttonTimer > 0) {
		buttonTimer--;
	} else {
		for (char y = 0; y < 4; y++) {
			for (char z = 0; z < 4; z++) {
				digitalWrite(KBD_COL+z, y!=z);
			}
			
			for (char x = 0; x < 4; x++) {
				i = btnmap[(y*4)+x];
				if (digitalRead(KBD_ROW + x) != kbd[i]) {
					kbd[i] = !kbd[i];
					buttonTimer = 5;
					if (!kbd[i]) {
						midibox_handle_button(i, kbd[i]);
					}
				}
			}
		}
		for (char z = 0; z < 4; z++) {
			digitalWrite(KBD_COL+z, 1);
		}
	}
#else
	if ((~PCF.read8()) >> 4) {
		btn_mask = 1;

		// y = col, x = row
		for (char y = 0; y < 4; y++) {
			PCF.write8(~(1 << y));
			i = (~PCF.read8()) >> 4;
			for (char x = 0; x < 4; x++) {
				btn = x * 4 + y;
				if ((i & 1) && !(btn_mask & btn_state)) {
					btn_state |=  btn_mask;
					midibox_handle_button(btn_map[btn], 1);
				} else if (!(i & 1) && (btn_mask & btn_state)) {
					btn_state &= ~btn_mask;
				}
				i >>= 1;
				btn_mask <<= 1;
			}
		}
		PCF.write8(0xF0);
	}
#endif

	if (rot_enc) {
		int16_t r = rot_enc;
		rot_enc = 0;

		midibox_handle_button(16, r);
		/*
		while (r > 0) {
			midibox_handle_button(16, 1);
			r--;
		}
		while (r < 0) {
			midibox_handle_button(16, -1);
			r++;
		}*/
	}
	
	static const uint8_t sw[] = {ROT_ENC_BTN, SWITCH1, SWITCH2, SWITCH3};
	for (i = 0; i < sizeof(sw); i++) {
		btn = digitalRead(sw[i]);
		btn_mask = 1 << (17 + i);
		if (!btn && !(btn_mask & btn_state)) {
			btn_state |= btn_mask;
			midibox_handle_button(17+i, 1);
		} else if (btn && (btn_mask & btn_state)) {
			btn_state &= ~btn_mask;
		}
	}
}

void get_current_time(struct time_s & time)
{
	bool period = 0;
	uint8_t year;

	rtc.getDate(year, time.month, time.day, time.weekday);
	rtc.getTime(time.hour, time.minute, time.second, period);
	time.year = 1900 + (uint16_t)year;
}

void set_current_time(struct time_s & time)
{
	rtc.setDate(time.year - 1900, time.month, time.day);
	rtc.setTime(time.hour, time.minute, time.second);
}

void midibox_io_init()
{
	Wire1.setSDA(14);
	Wire1.setSCL(15);

	rtc.begin();

 	/* SD-card */
	SPI1.setRX(12);
	SPI1.setTX(11);
	SPI1.setSCK(10);
	SPI1.setCS(13);

	card.init(SPI_HALF_SPEED, 13);
	volume.init(card);
	SD.begin(13);
	root = SD.open("/");

	tft.init();
	tft.initDMA();
	tft.fillScreen(TFT_BLACK);
	tft.setRotation(3);

	PCF.begin();
	PCF.write8(0xF0);

	uint16_t p[5] = {396, 3561, 205, 3661, 1};

#ifdef CALIBRATE_TOUCHSCREEN
	uint8_t i;
	tft.calibrateTouch(p, TFT_WHITE, TFT_RED, 15);
	Serial.print("Touchscreen calibration data: ");
	for (i = 0; i < 5; i++) {
		Serial.print(p[i]);
		Serial.print(" ");
	}
	Serial.println("");
#else
	tft.setTouch(p);
#endif

	lv_disp_draw_buf_init(&draw_buf, buf, NULL, screenWidth * 10);

	static lv_disp_drv_t disp_drv;
	lv_disp_drv_init(&disp_drv);
	disp_drv.hor_res = screenWidth;
	disp_drv.ver_res = screenHeight;
	disp_drv.flush_cb = midibox_display_flush;
	disp_drv.draw_buf = &draw_buf;
	lv_disp_t *disp = lv_disp_drv_register(&disp_drv);

	/* Initialize the (dummy) input device driver */
	static lv_indev_drv_t indev_drv_touch;
	lv_indev_drv_init(&indev_drv_touch);
	indev_drv_touch.type = LV_INDEV_TYPE_POINTER;
	indev_drv_touch.read_cb = midibox_touchpad_read;
	lv_indev_drv_register(&indev_drv_touch);

	static lv_indev_drv_t indev_drv_enc;
	lv_indev_drv_init(&indev_drv_enc);
	indev_drv_enc.type = LV_INDEV_TYPE_ENCODER;
	indev_drv_enc.read_cb = midibox_encoder_read;
	lv_indev_drv_register(&indev_drv_enc);

	lv_theme_t *th = lv_theme_default_init(disp, lv_palette_main(LV_PALETTE_BLUE), lv_palette_main(LV_PALETTE_RED), true, LV_FONT_DEFAULT);
	lv_disp_set_theme(disp, th);

	pinMode(ROT_ENC_BTN, INPUT_PULLUP);
	pinMode(ROT_ENC_A, INPUT_PULLUP);
	pinMode(ROT_ENC_B, INPUT_PULLUP);
	pinMode(SWITCH1, INPUT_PULLUP);
	pinMode(SWITCH2, INPUT_PULLUP);
	pinMode(SWITCH3, INPUT_PULLUP);

	pa = digitalRead(ROT_ENC_A);
	pb = digitalRead(ROT_ENC_B);

#ifdef MATRIX_KBD_DIRECT
	pinMode(KBD_ROW+0, INPUT_PULLUP);
	pinMode(KBD_ROW+1, INPUT_PULLUP);
	pinMode(KBD_ROW+2, INPUT_PULLUP);
	pinMode(KBD_ROW+3, INPUT_PULLUP);

	pinMode(KBD_COL+0, OUTPUT);
	pinMode(KBD_COL+1, OUTPUT);
	pinMode(KBD_COL+2, OUTPUT);
	pinMode(KBD_COL+3, OUTPUT);
#endif
}
#endif
