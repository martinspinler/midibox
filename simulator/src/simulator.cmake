#cmake_minimum_required(VERSION 3.10)
#
#project(mb-sim)
#
#set(PROJ mb-sim)

#set(SIM_COMMON_SRC_DIR "../../simulator/src")
set(MIDIBOX_SRC_DIR "..")
set(ARDUINO_LIBRARIES_DIR "$ENV{HOME}/Arduino/libraries")
set(ARDUINO_CORE_DIR "$ENV{HOME}/.arduino15/packages/rp2040/hardware/rp2040/3.4.1/cores/rp2040")

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "-O3 -g")

include_directories(${PROJECT_SOURCE_DIR})
include_directories(${SIM_COMMON_SRC_DIR})

# for the MIDI_Library
function (increase_warning_level)
endfunction()

add_subdirectory("${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src" midi)

file(GLOB INCLUDES
    "${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src/*.h"
    "${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src/*.hpp"
    "${ARDUINO_CORE_DIR}/api/String.h"
    "${ARDUINO_CORE_DIR}/api/Print.h"
	"${SIM_COMMON_SRC_DIR}/*.h"

    "${MIDIBOX_SRC_DIR}/*.h"
    "*.h"
)
file(GLOB SOURCES
    "${ARDUINO_CORE_DIR}/api/String.cpp"
	"${ARDUINO_CORE_DIR}/api/Print.cpp"
	"${SIM_COMMON_SRC_DIR}/misc/itoa.cpp"
	"${SIM_COMMON_SRC_DIR}/*.cpp"

    "${MIDIBOX_SRC_DIR}/*.cpp" 
    "*.cpp"
)

add_compile_definitions("MIDIBOX_INCLUDE=\"${MIDIBOX_SRC_DIR}/midi.h\"")
include_directories(${ARDUINO_CORE_DIR}/api ${ARDUINO_LIBRARIES_DIR}/MIDI_Library/src ${ARDUINO_LIBRARIES_DIR}/Protothreads/src)

add_executable(${PROJ} ${SOURCES} ${INCLUDES})
target_link_libraries(${PROJ} PRIVATE rtmidi)
target_include_directories(${PROJ} PRIVATE ${MIDIBOX_SRC_DIR}/)
