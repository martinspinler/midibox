#ifndef TUSB_CONFIG_H_
#define TUSB_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

#define CFG_TUH_ENABLED       1
#define CFG_TUH_MAX_SPEED     BOARD_TUH_MAX_SPEED

#define BOARD_TUH_RHPORT      0
#define BOARD_TUH_MAX_SPEED   OPT_MODE_DEFAULT_SPEED

#define CFG_TUH_ENUMERATION_BUFSIZE 256

#define CFG_TUH_HUB                 1
#define CFG_TUH_DEVICE_MAX          (3*CFG_TUH_HUB + 1)

#define CFG_TUH_MIDI                CFG_TUH_DEVICE_MAX

#ifdef __cplusplus
}
#endif

#endif
