set(PROJECT midibox_pico_w)
cmake_minimum_required(VERSION 3.12)
set(PICO_BOARD pico_w)

set(ARDUINO_LIBRARIES_DIR "$ENV{HOME}/Arduino/libraries")
set(ARDUINO_CORE_DIR "$ENV{HOME}/.arduino15/packages/rp2040/hardware/rp2040/3.4.1/cores/rp2040")

include_directories(${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src ${ARDUINO_LIBRARIES_DIR}/Protothreads/src)

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)
project(${PROJECT} C CXX ASM)

pico_sdk_init()
add_executable(${PROJECT})
target_sources(${PROJECT} PUBLIC
	${CMAKE_CURRENT_LIST_DIR}/main.cpp
	${CMAKE_CURRENT_LIST_DIR}/midi.cpp
	${CMAKE_CURRENT_LIST_DIR}/io.cpp
#	${CMAKE_CURRENT_LIST_DIR}/usb_descriptors.c
)

target_include_directories(${PROJECT} PUBLIC
	${CMAKE_CURRENT_LIST_DIR}
)
#target_compile_options(${PROJECT} PUBLIC -DPICO_STDIO_USB_ENABLE_RESET_VIA_VENDOR_INTERFACE=1)

target_link_libraries(${PROJECT} pico_stdlib pico_multicore hardware_adc tinyusb_host tinyusb_board)
pico_add_extra_outputs(${PROJECT})
pico_enable_stdio_usb(${PROJECT} 0)
pico_enable_stdio_uart(${PROJECT} 1)
