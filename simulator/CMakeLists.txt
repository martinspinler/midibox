cmake_minimum_required(VERSION 3.10)
project(midibox-simulator)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

SET(CMAKE_CXX_FLAGS "-O3 -g")

include_directories(${PROJECT_SOURCE_DIR})

set(MIDIBOX_SRC_DIR "../midibox-xiao-nrf52840")
set(ARDUINO_LIBRARIES_DIR "$ENV{HOME}/Arduino/libraries")
set(ARDUINO_CORE_DIR "$ENV{HOME}/.arduino15/packages/rp2040/hardware/rp2040/1.13.1/cores/rp2040")

# for the MIDI_Library
function (increase_warning_level)
endfunction()

add_subdirectory("${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src" midi)

file(GLOB INCLUDES
    "${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src/*.h"
    "${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src/*.hpp"
    "${ARDUINO_CORE_DIR}/api/String.h"
    "${ARDUINO_CORE_DIR}/api/Print.h"

    "${MIDIBOX_SRC_DIR}/*.h"
    "*.h"
)
file(GLOB SOURCES
    "${ARDUINO_CORE_DIR}/api/String.cpp"
	"${ARDUINO_CORE_DIR}/api/Print.cpp"
    "misc/itoa.cpp"

    "${MIDIBOX_SRC_DIR}/*.cpp" 
    "*.cpp"
)

add_compile_definitions("MIDIBOX_INCLUDE=\"${MIDIBOX_SRC_DIR}/midi.h\"")
include_directories(${ARDUINO_CORE_DIR}/api ${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src ${ARDUINO_LIBRARIES_DIR}/Protothreads/src)

add_executable(main ${SOURCES} ${INCLUDES})
target_link_libraries(main PRIVATE rtmidi)
target_include_directories(main PRIVATE ${MIDIBOX_SRC_DIR}/)
