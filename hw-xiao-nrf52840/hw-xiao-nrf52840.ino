#include <pt.h>

#include "midi.h"

using namespace midi;

Adafruit_USBD_MIDI usb_midi;
BLEDis bledis;
BLEMidi blemidi;

USBSerialMIDI usb_serial_midi(usb_midi);
SerialMIDI<HardwareSerial> Serial1_midi(Serial1);
BleMIDI Ble_midi(blemidi);

MidiInterfaceUsb MU(usb_serial_midi);
MidiInterfaceHwserial MS1(Serial1_midi);
MidiInterfaceBle MB(Ble_midi);

static struct pt pt_charlieplex;

const int CPP_FIRST = 8;
const int CPP_LAST  = 10;

static int charlieplex(struct pt *pt)
{
	static int i;
	static int x, y;
	static int state;
	static unsigned long output_delay;

	static uint8_t val;
	static uint8_t b[1 << (CPP_LAST - CPP_FIRST + 1)];

	static int8_t btn_map[] = {-1, 6, -1, 5, 7, 4};
	PT_BEGIN(pt);

	i = 0;
	for (x = CPP_FIRST; x <= CPP_LAST; x++) {
		pinMode(x, OUTPUT);
		digitalWrite(x, 0);

		output_delay  = millis();
		PT_WAIT_UNTIL(pt, millis() - output_delay > 30);

		output_delay = millis();
		for (y = CPP_FIRST; y <= CPP_LAST; y++) {
			if (y == x)
				continue;

			val = digitalRead(y) ? 0x00 : 0x7F;

			if (val != b[i]) {
				b[i] = val;
				if (btn_map[i] >= 0) {
					midi_handle_pedal_input(btn_map[i], val);
				}
			}

			i++;
		}

		digitalWrite(x, 1);
		pinMode(x, INPUT_PULLUP);
	}

	PT_END(pt);
}

void check_inputs()
{
	static const int ANALOG_PEDALS = 3;
	int i, j;
	static unsigned long ms = 0;
	static unsigned long pedal_value_prev_time[ANALOG_PEDALS] = {0};
	static uint8_t pedal_value_prev[ANALOG_PEDALS] = {0};
	static uint16_t pedal_value_avg[ANALOG_PEDALS][8] = {0};

	uint16_t send;
	uint16_t val;
	uint16_t oval;
	uint16_t avg, vmin, vmax;

	if (ms + 5 < millis()) {
		ms = millis();

		for (i = 0; i < ANALOG_PEDALS; i++) {
			send = 0;
			if (gs.r.pedal_analog[i] == 0) {
				val = digitalRead(i);
				val = val == 0 ? 0x00: 0x7F;
				//val = val == 0 ? 0x7F: 0x00;
				if (pedal_value_prev[i] != val) {
					send = 1;
				}
			} else {
				oval = analogRead(i);
				val = oval;
				val <<= 5;
				val += 15;
				val >>= 8;

				val &= 0x7F;

				val = (val + 3) & 0x7C;

				avg = val;
				vmin = 0x7f;
				vmax = 0x00;

				for (j = 8; j > 1; j--) {
					pedal_value_avg[i][j-1] = pedal_value_avg[i][j-2];
					avg += pedal_value_avg[i][j-1];

					if (vmin > pedal_value_avg[i][j-1])
						vmin = pedal_value_avg[i][j-1];
					if (vmax < pedal_value_avg[i][j-1])
						vmax = pedal_value_avg[i][j-1];
				}
				avg >>= 3;

				if ((val < vmin || val > vmax) && pedal_value_prev_time[i] + 20 < ms) {
					send = 1;
				}
			}

			if (send) {
				pedal_value_prev[i] = val;
				if (gs.r.pedal_analog[i])
					Serial.println(String("Pedal: ") + i + " oval: " + oval + " val:" + val + "vmin: " + vmin + " vmax: " + vmax);

				midi_handle_pedal_input(i, val);
				pedal_value_prev_time[i] = ms;
			}
		}
	}

	charlieplex(&pt_charlieplex);
}

void ble_start_adv(void)
{
	Bluefruit.setName("Midibox XIAO BLE");
	Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
	Bluefruit.Advertising.addTxPower();
	Bluefruit.Advertising.addService(blemidi);
	Bluefruit.ScanResponse.addName();

	Bluefruit.Advertising.restartOnDisconnect(true);
	Bluefruit.Advertising.setInterval(32, 244);
	Bluefruit.Advertising.setFastTimeout(30);
	Bluefruit.Advertising.start(0);
}

void setup()
{
	int i;

#if defined(ARDUINO_ARCH_MBED) && defined(ARDUINO_ARCH_RP2040)
	TinyUSB_Device_Init(0);
#endif

	//usb_midi.setStringDescriptor("TinyUSB MIDI");

	pinMode(LED_BUILTIN, OUTPUT);

	/* Analog inputs */
	pinMode(0, INPUT_PULLUP);
	pinMode(1, INPUT_PULLUP);
	pinMode(2, INPUT_PULLUP);

	/* Charlieplex + protothread init */
	for (i = CPP_FIRST; i <= CPP_LAST; i++) {
		pinMode(i, INPUT_PULLUP);
	}

	PT_INIT(&pt_charlieplex);

	Serial.begin(115200);

	Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
	Bluefruit.begin();
	Bluefruit.setTxPower(4);
	Bluefruit.autoConnLed(true);

	bledis.setManufacturer("Adafruit Industries");
	bledis.setModel("Bluefruit Feather52");
	bledis.begin();

	midi_init();
	smidi_init();

#ifdef MIDIBOX_ENABLE_BLE
	ble_start_adv();
#endif
}

void loop()
{
	midi_loop();
	check_inputs();
}

void midi_piano_connect()
{
}
