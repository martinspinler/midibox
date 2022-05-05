cmake_minimum_required(VERSION 3.10)
project(lvgl)
set(CMAKE_C_STANDARD 11)#C11
set(CMAKE_CXX_STANDARD 17)#C17
set(CMAKE_CXX_STANDARD_REQUIRED ON)

INCLUDE_DIRECTORIES(${PROJECT_SOURCE_DIR})

set(MIDIBOX_SRC_DIR "../midibox")
set(ARDUINO_LIBRARIES_DIR "$ENV{HOME}/Arduino/libraries")
set(ARDUINO_CORE_DIR "$ENV{HOME}/.arduino15/packages/rp2040/hardware/rp2040/1.13.1/cores/rp2040")
set(LVGL_SRC_DIR "${ARDUINO_LIBRARIES_DIR}/lvgl")
set(LVDRVR_SRC_DIR "lv_drivers")

file(GLOB_RECURSE INCLUDES "${LVGL_SRC_DIR}/src/*.h" "${LVDRVR_SRC_DIR}/*.h" "${LVGL_SRC_DIR}/lvgl.h" "${ARDUINO_LIBRARIES_DIR}/Regexp/*.h"  )
file(GLOB_RECURSE SOURCES  "${LVGL_SRC_DIR}/src/*.c" "${LVDRVR_SRC_DIR}/*.c"                          "${ARDUINO_LIBRARIES_DIR}/Regexp/*.cpp")


file(GLOB MB_SIM_INCLUDES "*.h"  "${ARDUINO_CORE_DIR}/api/String.h"   "${ARDUINO_CORE_DIR}/api/Print.h")
file(GLOB MB_SIM_SOURCES "*.cpp" "${ARDUINO_CORE_DIR}/api/String.cpp" "${ARDUINO_CORE_DIR}/api/Print.cpp")

file(GLOB MB_INCLUDES "${MIDIBOX_SRC_DIR}/*.h")
file(GLOB MB_SOURCES "${MIDIBOX_SRC_DIR}/*.cpp" "misc/itoa.cpp")

SET(CMAKE_CXX_FLAGS "-O3 -g")

find_package(SDL2 REQUIRED SDL2)
include_directories(${SDL2_INCLUDE_DIRS} ${LVGL_SRC_DIR}/.. ${ARDUINO_CORE_DIR}/api)
add_executable(main ${SOURCES} ${MB_SOURCES} ${INCLUDES} ${MB_INCLUDES} ${MB_SIM_INCLUDES} ${MB_SIM_SOURCES})
add_compile_definitions(LV_CONF_INCLUDE_SIMPLE)
target_link_libraries(main PRIVATE SDL2 rtmidi)
target_include_directories(main
	PRIVATE ${MIDIBOX_SRC_DIR}/
)
add_custom_target (run COMMAND ${EXECUTABLE_OUTPUT_PATH}/main)
