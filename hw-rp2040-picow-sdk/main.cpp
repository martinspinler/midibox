#include "pico/stdlib.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <string>

#include "bsp/board_api.h"
#include "tusb.h"


#include "midi.h"
#include "io.h"

const std::string rtmidi_client_name = "MidiboxSimulator";

TUHMidiSerial     Serial_HW1;
UartMidiSerial    Serial_USB;

TUHVirtualSerialMidi vSerial_HW1(Serial_HW1);
UartVirtualSerialMidi vSerial_USB(Serial_USB);

MidiInterfaceHwserial MS1(vSerial_HW1);
MidiInterfaceUsb MU(vSerial_USB);

StdoutSerial Serial;


void midi_host_rx_task(void);

int main(void)
{
	board_init();
	stdio_init_all();

	stdio_set_translate_crlf(&stdio_uart, false);

	tusb_rhport_init_t host_init = {
		.role = TUSB_ROLE_HOST,
		.speed = TUSB_SPEED_AUTO
	};
	tusb_init(BOARD_TUH_RHPORT, &host_init);

	midi_init();
	smidi_init();

	while (1) {
		tuh_task();
		midi_loop();
		Serial_HW1.tx_cb();
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

void tuh_midi_mount_cb(uint8_t idx, const tuh_midi_mount_cb_t* mount_cb_data)
{
}

void tuh_midi_umount_cb(uint8_t idx)
{
}

void tuh_midi_rx_cb(uint8_t idx, uint32_t xferred_bytes)
{
	Serial_HW1.rx_cb(xferred_bytes);
}

void tuh_midi_tx_cb(uint8_t idx, uint32_t xferred_bytes)
{
	(void) idx;
	(void) xferred_bytes;
}
