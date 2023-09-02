#include "midi.h"


Uart Serial2(&sercom2, 4, 5, (SERCOM_RX_PAD_1), (UART_TX_PAD_0));

void SERCOM2_Handler()
{
  Serial2.IrqHandler();
}

using namespace midi;

/*struct MySettings : public midi::DefaultSettings {
	static const long BaudRate = 31250;
};
*/

SerialMIDI<HardwareSerial> Serial1_midi(Serial1);
SerialMIDI<HardwareSerial/*, MySettings*/> Serial2_midi(Serial2);

MidiInterfaceHwserial MS1(Serial1_midi);
MidiInterfaceHwserial MS2(Serial2_midi);


void setup()
{
	int i;

#if defined(ARDUINO_ARCH_MBED) && defined(ARDUINO_ARCH_RP2040)
	TinyUSB_Device_Init(0);
#endif

	//usb_midi.setStringDescriptor("TinyUSB MIDI");

	Serial.begin(115200);

	midi_init();
	smidi_init();
}

#if 0
void midi_loop()
{
#ifdef MIDIBOX_HAVE_UART2
	MS2.read();
#endif
#ifdef MIDIBOX_HAVE_BT
	MB.read();
#endif
	MS1.read();
}
#endif

void loop()
{
	midi_loop();
}

void midi_piano_connect()
{
}
