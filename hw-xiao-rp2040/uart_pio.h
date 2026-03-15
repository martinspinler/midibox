#ifndef UART_RX
#define UART_RX

#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/irq.h"
#include "hardware/clocks.h"
#include "uart_rx.pio.h"

#ifdef __cplusplus
extern "C" {
#endif


typedef void (*uart_rx_handler_t)(uint8_t data);

void uart_rx_init(PIO pio, uint sm, uint pin, uint baudrate, uint irq);
void uart_rx_set_handler(uart_rx_handler_t handler);

#ifdef __cplusplus
}
#endif

#endif
