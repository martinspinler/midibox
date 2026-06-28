#include "pico/stdlib.h"
#include "hardware/adc.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <string>
#include <pt.h>

#include "bsp/board_api.h"
//#include "tusb.h"
#include "uart_pio.h"


#include "midi.h"
#include "io.h"

#include "midibox-compat.h"

//#define OVERRIDE_DEFAULT_MIDI_CONFIG
#define ENABLE_PEDAL_AVG

UartMidiSerial    Serial_HW1;
PioUartMidiSerial Serial_HW2;
TUDMidiSerial     Serial_USB;

UartVirtualSerialMidi vSerial_HW1(Serial_HW1);
PioUartVirtualSerialMidi vSerial_HW2(Serial_HW2);
TUDVirtualSerialMidi vSerial_USB(Serial_USB);

MidiInterfaceHwserial MS1(vSerial_HW1);
MidiInterfacePioHwserial MS2(vSerial_HW2);
MidiInterfaceUsb MU(vSerial_USB);

StdoutSerial Serial;

static struct pt pt_charlieplex;

const int CPP_FIRST = 2;
const int CPP_LAST  = 4;


static const int ANALOG_PEDALS = 3;

static void pio_rx_handler(uint8_t data)
{
	static bool in_sysex = false;
#if 0
	if (data == 0xf0)
		in_sysex = true;
	else if (data == 0xf7)
		in_sysex = false;
#endif
	/* Replace pedal channel (2) to channel 5 */
	if (in_sysex == false && data & 0x80 && data < 0xF0) {
		data &= ~0x0F;
		data |= 0x04;
	}
	Serial_HW2.rx_cb(data);
}

static int charlieplex(struct pt *pt)
{
	static int i;
	static int x, y;
	static int state;
	static unsigned long output_delay;

	static uint8_t val;
	static uint8_t b[1 << (CPP_LAST - CPP_FIRST + 1)];

	static int8_t btn_map[] = {/*6*/-1, -1, 7, 4, 6, 5};
	PT_BEGIN(pt);

	i = 0;
	for (x = CPP_FIRST; x <= CPP_LAST; x++) {
		gpio_set_dir(x, 1);
		gpio_put(x, 0);

		output_delay  = micros();
		PT_WAIT_UNTIL(pt, micros() - output_delay > 30000);

		output_delay = micros();
		for (y = CPP_FIRST; y <= CPP_LAST; y++) {
			if (y == x)
				continue;

			val = gpio_get(y) ? 0x00 : 0x7F;

			if (val != b[i]) {
				b[i] = val;
				if (btn_map[i] >= 0) {
					midi_handle_pedal_input(btn_map[i], val);
				}
			}

			i++;
		}

		gpio_put(x, 1);
		gpio_set_dir(x, 0);
	}

	PT_END(pt);
}

void check_inputs()
{
	static const int ANALOG_PEDALS = 3;
	static const int ANALOG_PEDALS_AVG = 16;
	int i, j;
	static unsigned long ms = 0, cms;
	static unsigned long pedal_value_prev_time[ANALOG_PEDALS] = {0};
	static uint8_t pedal_value_prev[ANALOG_PEDALS] = {0};
	static uint16_t pedal_value_avg[ANALOG_PEDALS][ANALOG_PEDALS_AVG] = {0};

	uint8_t send, invert;
	uint16_t val;
	uint16_t oval;
	uint16_t avg, vmin, vmax;
	uint16_t pmin, pmax;


	cms = micros() / 1000;
	if (cms > ms + 5) {
		ms = cms;

		for (i = 0; i < ANALOG_PEDALS; i++) {
			send = 0;
			pmin = gs.r.pedals[i].min;
			pmax = gs.r.pedals[i].max;
			invert = pmin > pmax ? 1 : 0;
			if (invert) {
				val = pmin;
				pmin = pmax;
				pmax = val;
			}

			adc_select_input(i);
			/* 4096: 12b */
			oval = adc_read();

			if (gs.r.debug_smsg_print) {
				MU.sendControlChange(70, (oval>>0) & 0x7F, i+1);
				MU.sendControlChange(71, (oval>>7) & 0x7F, i+1);
			}

			val = oval << 4; /* 4096->65536: 12->16b */
			pmin <<= 9; /* 128->65536: 7->16b */
			pmax <<= 9;

			if (val < pmin)
				val = pmin;
			if (val > pmax)
				val = pmax;

			val = val - pmin;
			val = val / ((pmax - pmin) >> 7); /* 65536 -> 128 */
			val = (val > 0x8000 ? 0 : (val > 0x7F ? 0x7F : val));

			if (invert)
				val = 0x7F - val;
#ifdef ENABLE_PEDAL_AVG

			avg = val;
			pmin = 0x7f;
			pmax = 0x00;
			for (j = ANALOG_PEDALS_AVG; j > 1; j--) {
				pedal_value_avg[i][j-1] = pedal_value_avg[i][j-2];
				avg += pedal_value_avg[i][j-1];

				if (pmin > pedal_value_avg[i][j-1])
					pmin = pedal_value_avg[i][j-1];
				if (pmax < pedal_value_avg[i][j-1])
					pmax = pedal_value_avg[i][j-1];
			}
			pedal_value_avg[i][0] = val;
			avg /= ANALOG_PEDALS_AVG;

			pmax = avg <  0x7f ? avg + 1 : 0x7f;
			pmin = avg >= 0x01 ? avg - 1 : 0x00;
#endif

			if (
					((val < pmin || val > pmax) || (val == 0x00 || val == 0x7f)) &&
					pedal_value_prev_time[i] + 20 < ms &&
					pedal_value_prev[i] != val) {
				pedal_value_prev[i] = val;

				midi_handle_pedal_input(i, val);
				pedal_value_prev_time[i] = ms;
			}
		}
	}

	charlieplex(&pt_charlieplex);
}

void midi_host_rx_task(void);

int main(void)
{
	int i;
	PIO pio = pio0;

	board_init();
	stdio_usb_init();
	stdio_uart_deinit();

	//stdio_set_translate_crlf(&stdio_uart, false);

	tusb_init();

	for (i = CPP_FIRST; i <= CPP_LAST; i++) {
		gpio_init(i);
		gpio_set_dir(i, 0);
		gpio_pull_up(i);
	}

	adc_init();
	for (i = 26; i <= 26 + ANALOG_PEDALS; i++) {
		adc_gpio_init(i);
		gpio_set_pulls(i, true, false);
	}

	uart_init(uart0, 31250);
	gpio_set_function(0, UART_FUNCSEL_NUM(0, 0));
	gpio_set_function(1, UART_FUNCSEL_NUM(0, 1));

	uint sm_rx = pio_claim_unused_sm(pio, true);
	uart_rx_init(pio, sm_rx, 29, 31250, PIO0_IRQ_0);
	uart_rx_set_handler(pio_rx_handler);

	midi_init();
	smidi_init();

#ifdef OVERRIDE_DEFAULT_MIDI_CONFIG
	gs.r.pedal_mode[0] = PEDAL_MODE_IGNORE;
	gs.r.pedal_mode[1] = PEDAL_MODE_IGNORE;
	gs.r.pedal_mode[2] = PEDAL_MODE_IGNORE;

	gs.r.check_keep_alive = 1;
#endif

	gs.r.pedals[0].min = 80;
	gs.r.pedals[0].max = 100;
	gs.r.pedals[1].min = 80;
	gs.r.pedals[1].max = 100;
	gs.r.pedals[2].min = 42;
	gs.r.pedals[2].max = 120;

	while (1) {
		tud_task();
		midi_loop();
		check_inputs();
		//Serial_HW1.tx_cb();
		Serial_USB.rx_cb(0);
	}

	return 0;
}

unsigned long micros()
{
	return to_us_since_boot(get_absolute_time());
}

void midi_piano_connect()
{
}

void tud_midi_rx_cb(uint8_t idx, uint32_t xferred_bytes)
{
	Serial_USB.rx_cb(xferred_bytes);
}

void tud_midi_tx_cb(uint8_t idx, uint32_t xferred_bytes)
{
	(void) idx;
	(void) xferred_bytes;
}
