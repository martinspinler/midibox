#include <ctime>
#include <semaphore.h>
#include <stdlib.h>
#include <unistd.h>

#include "../midibox/midibox.h"

VirtualMidiSerial Serial1;
VirtualSerial Serial;

static sem_t gui2midi_sema;
static sem_t midi2gui_sema;

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

void get_current_time(struct time_s & time)
{
	std::time_t t = std::time(0);
	std::tm* now = std::localtime(&t);

	time.year = now->tm_year + 1900;
	time.day = now->tm_mday;
	time.month = now->tm_mon + 1;
	time.hour = now->tm_hour;
	time.minute = now->tm_min;
	time.second = now->tm_sec;
}

void set_current_time(struct time_s & time)
{
	printf(__func__);
}

void *midi_thread_loop(void *data)
{
	while (1) {
		midi_loop();
		usleep(50);
	}
	return NULL;
}

void midibox_sim_init()
{
	sem_init(&gui2midi_sema, 0, 0);
	sem_init(&midi2gui_sema, 0, 0);
}

void process_gui_cmd_send_to_midi(uint8_t cmd)
{
	midi_cmd = cmd;
	sem_post(&gui2midi_sema);
	sem_wait(&midi2gui_sema);
}

int process_midi_cmd_available()
{
	int val;
	if (sem_getvalue(&gui2midi_sema, &val))
		fprintf(stderr, "Error: sem_getvalue failed in %s\n", __func__);
	return val <= 0 ? 0 : 1;
}

uint8_t process_midi_cmd_get()
{
	sem_wait(&gui2midi_sema);
	return midi_cmd;
}

void process_midi_cmd_done()
{
	sem_post(&midi2gui_sema);
}

int main(int argc, char **argv)
{
	(void)argc; /*Unused*/
	(void)argv; /*Unused*/

	static pthread_t pthread_midi;

	lv_init();

	midi_init();
	midibox_sim_init();
	midibox_io_init();
	midibox_gui_init();

	pthread_create(&pthread_midi, NULL, midi_thread_loop, NULL);

	while(1) {
		lv_timer_handler();
		usleep(2 * 1000);
	}

	return 0;
}
