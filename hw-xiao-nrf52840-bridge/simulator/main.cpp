#include <ctime>
#include <semaphore.h>
#include <stdlib.h>
#include <unistd.h>

#include <string>

#include MIDIBOX_INCLUDE

const std::string rtmidi_client_name = "MidiboxBridgeSimulator";

VirtualMidiSerial Serial_HW1(rtmidi_client_name, "Control");
VirtualMidiSerial Serial_USB(rtmidi_client_name, "USB");
VirtualMidiSerial Serial_BLE(rtmidi_client_name, "BLE");

VirtualSerialMidi vSerial_HW1(Serial_HW1);
VirtualSerialMidi vSerial_USB(Serial_USB);
VirtualSerialMidi vSerial_BLE(Serial_BLE);

MidiInterfaceUsb MU(vSerial_USB);
MidiInterfaceBle MB(vSerial_BLE);
MidiInterfaceHwserial MS1(vSerial_HW1);

StdoutSerial Serial;

static uint8_t midi_cmd;

unsigned long micros()
{
        long o;
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        o = ts.tv_nsec / 1000;
        o += ts.tv_sec * 1000000;

        return o;
}

int main(int argc, char **argv)
{
	(void)argc; /*Unused*/
	(void)argv; /*Unused*/

	midi_init();
	//smidi_init();

	Serial.begin(115200);

	while(1) {
		midi_loop();
		usleep(50);
	}
	return 0;
}
