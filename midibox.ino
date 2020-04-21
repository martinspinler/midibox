#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_PCD8544.h>

Adafruit_PCD8544 display = Adafruit_PCD8544(6, 5, 4, 3, 2);

enum menu_screen_e {
	MENU_MAIN,
	MENU_PRESETS,
	MENU_CONFIGURE,
	MENU_PROGRAM,
	MENU_HAMMOND,
	MENU_TRANSPOSE,
	MENU_SPLIT_OVERRIDE,
};

enum config_mode_e {
	MODE_NORMAL,
	MODE_ALTER,
};

enum menu_screen_e menu = MENU_MAIN;

char menu_state_channel = 0;
char menu_state_program = 0;
char menu_state_hammond_bar = 0;

char sysex_len;
char sysex_data[64];

char config_enable = 0;
char config_split_override = 0;
char config_split = 59;
const enum config_mode_e config_mode = MODE_NORMAL;

char state_transpose[8] = {0, 0, 0, 0, 1, 0, -1, 0};
unsigned char state_hammond_bars[14] = {0x40, 0x41, 0x51, 0x00, 0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0};

struct program_t {
	const char *name;
	const char program;
	const char ccm;
	const char ccl;
	const char sysex_length;
	char *sysex;
};

char sysex_p [] 		= {0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00};
char sysex_ep[] 		= {0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02};
char sysex_hammond [] 	= {0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F};
char sysex_bass[] 		= {0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04};

struct program_t programs[] = {
	{"Piano",        0,  0, 68, 9, sysex_p},
	{"ePiano",		 4,  0, 67, 9, sysex_ep},
	{"Hammond1",    16, 32, 68, 9, sysex_hammond},
	{"Bass",        32,  0, 71, 9, sysex_bass},
};

inline void printOn(char x, char y, const char *text) {
	display.setCursor(x, y);
	display.print(text);
}

inline void printOn(char x, char y, const char *text, char i) {
	printOn(x, y, text);
	display.print(i, DEC);
}

void sendRolandSysex(const unsigned char * data, unsigned char length)
{
	static char roland_sysex_header[4] = {0x41, 0x10, 0x42, 0x12};

	unsigned char crc = 0;
	unsigned char i;

	Serial.write(0xF0);

	for (i = 0; i < 4; i++) {
		Serial.write(roland_sysex_header[i]);
	}
		
	for (i = 0; i < length; i++) {
		Serial.write(data[i]);
		crc += data[i];
	}

	Serial.write(128 - (crc & 0x7F));
	Serial.write(0xF7);
}

void sendMidiLocalCTL(char state)
{
	/* Local CTL = off*/
	for (char i = 0; i < 4; i++) {
		Serial.write(0xb0 + i);
		Serial.write(122);
		Serial.write(state ? 127 : 0);
	}
}

void sendMidiAllOff()
{
	/* Send: All Sounds Off, Reset All Controllers, All Notes Off */
	for (char i = 0; i < 16; i++) {
		Serial.write(0xb0 + i);
		Serial.write(120);
		Serial.write(0);

		Serial.write(0xb0 + i);
		Serial.write(121);
		Serial.write(0);

		Serial.write(0xb0 + i);
		Serial.write(123);
		Serial.write(0);
	}
}

void sendMidiControlChange(char channel, char cc, char value)
{
	Serial.write(0xb0 | channel);
	Serial.write(cc);
	Serial.write(value);
}

void sendMidiProgramChange(char channel, char program)
{
	Serial.write(0xc0 | channel);
	Serial.write(program);
}

void sendHammondBars()
{
	sendRolandSysex(state_hammond_bars, 14);
}

void setProgram(char channel, char program)
{
	struct program_t *pgm = &programs[program];

	sendMidiControlChange(channel, 0, pgm->ccm);
	sendMidiControlChange(channel, 32, pgm->ccl);
	sendMidiProgramChange(channel, pgm->program);

	pgm->sysex[1] = 0x40 | (channel + 1);
	sendRolandSysex(pgm->sysex, pgm->sysex_length);
}

inline void prActivate(char preset)
{
	switch (preset) {
	case 0:
		/* Piano only */
		//state_transpose[0] = 0;
		setProgram(0, 0);
		setProgram(2, 0);
		break;
	case 1:
		/* ePiano + Bass */
		//state_transpose[0] = 0;
		setProgram(0, 1);
		setProgram(2, 1);
		break;
	case 2:
		/* Piano + Bass */
		//state_transpose[0] = 0;
		setProgram(0, 0);
		setProgram(2, 3);
		break;
	case 3:
		/* ePiano + Bass */
		//state_transpose[0] = 0;
		setProgram(0, 1);
		setProgram(2, 3);
		break;
	}
}

inline void smMain()
{
	//printOn(0, 0, "^ OUT ^ v IN v");
	printOn(0, 8, "<Preset\n\n<\n\n<Conf");
	printOn(48, 8, "Panic>");
	printOn(42, 24,  state_transpose[0] == 0 ? "Ova -1>" : "Ova =0>");
	printOn(36, 40, config_enable ? "Disable>" : " Enable>");
}

inline void smPresets()
{
	printOn(0,  8,  "<P\n\n<eP");
	printOn(84-6*7, 8,  "P&Bass>");
	printOn(84-6*8, 24, "eP&Bass>");

	printOn(0, 40,  "<Back");
	printOn(84-6*5, 40, "Next?");
}

inline void smConfigure()
{
	printOn(0, 8, "<Tran\n\n<Prgm\n\n<Back");
//	printOn(84-5*6, 8, "Layr>");
//	printOn(84-8*6, 24, config_mode == MODE_NORMAL ? "Ch.altr>" : "Ch.orig>");
	printOn(84-8*6, 8, "Hammond>");
	printOn(84-8*6, 40, "SplitOv>");
}

inline void smProgram()
{
	printOn(18, 0, "Program\n+\n-");
	printOn(6, 12, "Ch:", menu_state_channel+1);
	printOn(84-6,  8, "+");
	printOn(84-6, 16, "-");
	printOn(84-7*6, 12, "Pgm:", menu_state_program+1);
	printOn(6*2, 28, programs[menu_state_program].name);
	printOn(84-6*4, 40, "Set>");
	printOn(0, 40, "<Back");
}

inline void smHammond()
{
	char i;
	for (i = 0; i < 9; i++) {
		display.fillRect((i << 3) + 6, 8, 6, (state_hammond_bars[i+5] << 1) + 1, BLACK);
	}
	printOn((menu_state_hammond_bar << 3) + 6, 0, "v");
	printOn(0, 40, "<Back");
	printOn(84-6*8, 40, "Perc: ", state_hammond_bars[4]);
	printOn(84-6, 40, ">");
}

inline void smTranspose()
{
	printOn(12,  0, "Transpose\n+\n-");
	printOn(6, 12, "Ch:", menu_state_channel+1);
	printOn(84-6,  8, "+");
	printOn(84-6, 16, "-");
	printOn(84-7*6, 12, state_transpose[menu_state_channel] >= 0 ? "Oct: " : "Oct:", state_transpose[menu_state_channel]);
	printOn(0, 40, "<Back");
}

inline void smSplitOverride()
{
	printOn(0,  0, "Split Override");
	printOn(6, 12, "Note:", config_split);
	printOn(0,  8, "+");
	printOn(0, 16, "-");
	printOn(0, 40, "<Back");
	printOn(54, 24, "Scan>");
	printOn(36, 40, config_split_override ? "Disable>" : " Enable>");
}

inline void hbMain(char button)
{
	switch (button) {
	case 1:	menu = MENU_PRESETS; break;
	case 3:	menu = MENU_CONFIGURE; break;
	case 4:	sendMidiAllOff(); break;
	case 5:	state_transpose[0] = state_transpose[0] == 0 ? -1 : 0; break;
	case 6:
		sendMidiLocalCTL(config_enable);
		config_enable = config_enable == 1 ? 0 : 1;
		break;
	}
}

inline void hbPresets(char button)
{
	switch (button) {
	case 1:	prActivate(0); break;
	case 2:	prActivate(1); break;
	case 4:	prActivate(2); break;
	case 5:	prActivate(3); break;
	case 6:	prActivate(4); break;
	}
	menu = MENU_MAIN;
}

inline void hbConfigure(char button)
{

	switch (button) {
	case 1:	menu = MENU_TRANSPOSE; break;
	case 2:	menu = MENU_PROGRAM; break;
	case 3:	menu = MENU_MAIN; break;
	case 4:	menu = MENU_HAMMOND; break;
	case 5: break;
	case 6:	menu = MENU_SPLIT_OVERRIDE; break;
	}
}

inline void hbProgram(char button)
{
	switch (button) {
	case 1:	if (menu_state_channel < 7) { menu_state_channel++; } break;
	case 2:	if (menu_state_channel > 0) { menu_state_channel--; } break;
	case 3:	menu = MENU_CONFIGURE; break;
	case 4:	if (menu_state_program < 3) { menu_state_program++; } break;
	case 5:	if (menu_state_program > 0) { menu_state_program--; } break;
	case 6: setProgram(menu_state_channel, menu_state_program); break;
	}
}

inline void hbHammond(char button)
{
	switch (button) {
	case 1:	if (menu_state_hammond_bar < 8) { menu_state_hammond_bar++; } break;
	case 2:	if (menu_state_hammond_bar > 0) { menu_state_hammond_bar--; } break;
	case 5:	if (state_hammond_bars[menu_state_hammond_bar+5] < 15) { state_hammond_bars[menu_state_hammond_bar+5]++; sendHammondBars();} break;
	case 4:	if (state_hammond_bars[menu_state_hammond_bar+5] > 0)  { state_hammond_bars[menu_state_hammond_bar+5]--; sendHammondBars();} break;
	case 3:	menu = MENU_CONFIGURE; break;
	case 6: state_hammond_bars[4]++; if (state_hammond_bars[4] > 2) { state_hammond_bars[4] = 0; } break;
	default: break;
	}
}

inline void hbTranspose(char button)
{
	switch (button) {
	case 1:	if (menu_state_channel < 7) { menu_state_channel++; } break;
	case 2:	if (menu_state_channel > 0) { menu_state_channel--; } break;
	case 3:	menu = MENU_CONFIGURE; break;
	case 4:	state_transpose[menu_state_channel]++; break;
	case 5:	state_transpose[menu_state_channel]--; break;
	}
}

inline void hbSplitOverride(char button)
{
	switch (button) {
	case 1:	if (config_split < 127) { config_split++; } break;
	case 2:	if (config_split > 0) { config_split--; } break;
	case 3:	menu = MENU_CONFIGURE; break;
	case 5:	config_split_override = 2; break;
	case 6:	config_split_override = config_split_override ? 0 : 1;
	}
}

struct menu_screen {
	void (*show)(void);
	void (*buttonPressed)(char button);
} menu_screens[] = {
	[MENU_MAIN]             = {.show = smMain, .buttonPressed = hbMain},
	[MENU_PRESETS]          = {.show = smPresets, .buttonPressed = hbPresets},
	[MENU_CONFIGURE]        = {.show = smConfigure, .buttonPressed = hbConfigure},
	[MENU_PROGRAM]          = {.show = smProgram, .buttonPressed = hbProgram},
	[MENU_HAMMOND]          = {.show = smHammond, .buttonPressed = hbHammond},
	[MENU_TRANSPOSE]        = {.show = smTranspose, .buttonPressed = hbTranspose},
	[MENU_SPLIT_OVERRIDE]   = {.show = smSplitOverride, .buttonPressed = hbSplitOverride},
};

void updateMenu()
{
	display.clearDisplay();
	menu_screens[menu].show();
	display.display();
}

inline void handleButton(char button)
{
	menu_screens[menu].buttonPressed(button);
	updateMenu();
}

void handle_sysex()
{
	char *data = sysex_data;
	char part;

	if (config_enable || sysex_len < 2)
		return;
	if (
			data[0] == 0x41 && /* ID number (Roland) */
//			data[1] == 0x10 && /* Device ID */
			data[2] == 0x42 && /* Model ID */
			data[3] == 0x12 /* Command ID (DT1) */
			) {
		if (sysex_len < 8)
			return;
		if (data[4] == 0x40) {
			if (data[5] & 0xF0 == 0) {
				/* System parameters */
			} else {
				/* Part parameters */
				part = data[5] & 0x0F;
			
				if (config_enable == 1 && config_mode == MODE_NORMAL) {
					data[5] &= 0x0F;
					data[5] |= part + 4;
				}
				sendRolandSysex(data + 4, sysex_len-4-1);
			}
		}
	}
}

void checkButtonPressed()
{
	static uint16_t buttonTimer;
	static char buttonState[6] = {HIGH,HIGH,HIGH,HIGH,HIGH,HIGH};
	const char buttonMap[6] = {4,5,6,1,2,3};

	if (buttonTimer > 0) {
		buttonTimer--;
	} else {
		for (char i = 0; i < 6; i++) {
			if (digitalRead(i + 14) != buttonState[i]) {
				buttonState[i] = !buttonState[i];
				buttonTimer = 10000;
				if (!buttonState[i]) {
					handleButton(buttonMap[i]);
				}
			}
		}
	}
}

void setup()
{
	Serial.begin(31250);

	for (char i = 14; i <= 19; i++)
		pinMode(i, INPUT_PULLUP);

	display.begin();
	display.setContrast(44);
	display.setTextSize(1);
	display.setTextColor(BLACK);
	updateMenu();
}

void loop()
{
	static char in_sysex = 0;

	unsigned char data;
	unsigned char channel;
	unsigned char cmd;

again:
	checkButtonPressed();	

	if (Serial.available()) {
		data = Serial.read();
		cmd = (data & 0xF0);

		/* Not status byte? Not in sync */
		if ((data & 0x80) == 0) {
			if (in_sysex == 1) {
				/* Store SysEx */
				if (sysex_len < 64) {
					sysex_data[sysex_len] = data;
					sysex_len++;
				} else {
					/* Max size overflowed */
					in_sysex = 0;
				}
				goto again;
			} else {
				/* Error in SysEx */
				in_sysex = 0;
				goto again;
			}
		}

		/* System Common Messages */
		if (cmd == 0xF0) {
			/* System Exclusive */
			if (data == 0xF0) {
				in_sysex = 1;
				sysex_len = 0;
				goto again;
			/* End of Exclusive */
			} else if (data == 0xF7) {
				in_sysex = 0;
				/* Handle stored SysEx */
				handle_sysex();
#if 0
			/* MIDI Time Code Quarter Frame */
			} else if (data == 0xF1) {
				while (Serial.available() == 0);
				Serial.read();
			/* Song Position Pointer */
			} else if (data == 0xF2) {
				while (Serial.available() == 0);
				Serial.read();
				while (Serial.available() == 0);
				Serial.read();
			/* Song Select */
			} else if (data == 0xF2) {
				while (Serial.available() == 0);
				Serial.read();
			/* System Real-Time Messages */
			} else if (data >= 0xF8 && data < 0xFF) {
#endif
			}
			goto again;
		}

		if (config_enable == 0)
			goto again;

		/* Note On / Off events */
		if (cmd == 0x80 || cmd == 0x90) {
			channel = data & 0x0F;

			/* Key number */
			while (Serial.available() == 0);
			data = Serial.read();

			if (config_mode == MODE_ALTER) {
				if (data > config_split)
					channel = 4;
				else
					channel = 5;
			} else {
				if (config_split_override == 2) {
					config_split = data - 1;
					config_split_override = 1;
					updateMenu();
				} else if (config_split_override) {
					if (data > config_split)
						channel = 0;
					else
						channel = 2;
				}
			}

			Serial.write(cmd | channel);

			if (channel < 8) {
				data += ((signed)state_transpose[channel]) * 12;
			}
			Serial.write(data);

			/* Velocity */
			while (Serial.available() == 0);
			data = Serial.read();
			Serial.write(data);
		/* Program Change / Channel Pressure */
		} else if (cmd == 0xC0 || cmd == 0xD0) {
			Serial.write(data);

			/* B1 */
			while (Serial.available() == 0);
			data = Serial.read();
			Serial.write(data);
		/* Control Change */
		} else if (cmd == 0xB0) {
			channel = data & 0x0F;

			if (config_mode == MODE_ALTER) {
				channel += 4;
			} else {
			}

			Serial.write(cmd | channel);

			/* B1 */
			while (Serial.available() == 0);
			data = Serial.read();
			Serial.write(data);

			/* B2 */
			while (Serial.available() == 0);
			data = Serial.read();
			Serial.write(data);
		/* Polyphonic Aftertouch / Pitch Wheel Change */
		} else if (cmd == 0xA0 || cmd == 0xE0) {
			Serial.write(data);

			/* B1 */
			while (Serial.available() == 0);
			data = Serial.read();
			Serial.write(data);

			/* B2 */
			while (Serial.available() == 0);
			data = Serial.read();
			Serial.write(data);
		}
		goto again;
	}
}
