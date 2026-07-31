# Building and flashing

This is an Arduino IDE sketch. There is no `platformio.ini` and I have not written one, so if you
prefer PlatformIO you are on your own for the board config.

## Toolchain

| | |
|---|---|
| IDE | Arduino IDE 2.x |
| Core | Espressif `esp32` (Boards Manager) |
| Board | ESP32C3 Dev Module |
| Upload | native USB, no external programmer |
| Serial monitor | 115200 |

I have not pinned exact core and library versions. Both `driver/twai.h` and `Preferences.h` come
from the ESP32 core itself and the API used here is stable across the 2.x and 3.x lines, so a
current core should build it.

## Board settings that matter

Most of the defaults are fine. This one is not:

**USB CDC On Boot: Enabled.**

Get this wrong and the build still compiles, uploads, and comes up with a working display and dead
audio. The reason is that the DFPlayer is on GPIO20 and GPIO21, which are the chip's default UART0
pins. With USB CDC enabled, `Serial` goes to the USB peripheral and UART1 has GPIO20/21 to itself.
With it disabled, `Serial.begin(115200)` claims UART0 on those same two pins and the two fight over
the wires. If your screen works and the speaker never makes a sound, check this before you check
anything else.

Flash size only needs to cover the background bitmap, which is 76,800 pixels at 2 bytes each, so
150 KB of the binary is picture. Any 4 MB board with the default partition scheme has plenty of
room.

## Libraries

Install these four from Library Manager:

| Library | Why |
|---------|-----|
| Adafruit GFX Library | drawing primitives, `GFXcanvas16`, the fonts |
| Adafruit ILI9341 | the panel driver |
| Adafruit BusIO | dependency of the two above, Library Manager pulls it in |
| DFRobotDFPlayerMini | audio module |

The four fonts the sketch includes (`FreeSans9pt7b`, `FreeSansBold12pt7b`, `FreeSansBold18pt7b`,
`FreeMonoBoldOblique9pt7b`) ship inside Adafruit GFX. Nothing extra to install.

**There is no `User_Setup.h` here.** If you have built ILI9341 projects before, you are probably
thinking of TFT_eSPI, which is a different library and is not used. Adafruit's driver takes its pins
from the constructor, so the display pins live in the sketch:

```c
#define TFT_DC 1
#define TFT_CS 8
Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC);
```

SCK and MOSI are not named anywhere. That two argument constructor uses the default `SPI` object, so
they come from the board definition: GPIO4 for SCK and GPIO6 for MOSI on the C3. If you wire the
display to different pins, nothing will appear and the sketch will give you no clue why.

### The vendored header

`src/esp32c3sp_firmware_bmw/Adafruit_ILI9341.h` is a copy of the library's own header sitting next to
the sketch, and the sketch includes it with quotes rather than angle brackets. That means the local
copy wins over whatever Library Manager installed, while the matching `.cpp` still comes from the
installed library.

That works as long as the two agree. If you install a version of Adafruit ILI9341 whose header has
changed, you get declarations that do not match the compiled implementation, and the errors are
confusing. If you hit that, delete the local header and change the include to
`#include <Adafruit_ILI9341.h>`.

## CAN setup

Nothing to configure, but worth knowing what the sketch asks for:

```c
twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT((gpio_num_t)5, (gpio_num_t)3, TWAI_MODE_LISTEN_ONLY);
g_config.rx_queue_len = 32;
twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
```

TX is GPIO5, RX is GPIO3, 500 kbit/s, no hardware filtering, and listen-only so the controller never
puts anything on the bus. The 32 frame receive queue is deliberately deep: the display and audio code
both block for tens of milliseconds at a time during animations, and a shallower queue drops frames
while that happens.

If `twai_driver_install()` fails it prints `TWAI install failed` on the serial monitor and the sketch
carries on with a display that never updates.

## Audio files

Put five files on the microSD. GLaDOS style examples can be found (here)[https://github.com/TZeys/BimmerScreenFS/tree/main/docs/firmware/Audio-FIles]. 
The firmware calls tracks by index:

| Index | Plays on |
|-------|----------|
| 1 | ignition on |
| 2 | oil over 95 °C |
| 3 | coolant over 95 °C |
| 4 | over 4000 rpm |
| 5 | ignition off |

DFPlayer's index is the order files were physically written to the card, not alphabetical order and
not the filename. This catches everyone. Format the card FAT32, then copy `0001.mp3` through
`0005.mp3` one at a time in order, and do not let your file manager copy them in parallel. If your
warning sounds come out in the wrong order, that is why.

Volume is hardcoded to 30, which is the module's maximum, and `enableDAC()` is called at startup.

## First run without a car

The display stays black until `0x130` says the ignition is live, so on a bench with no CAN traffic
you get nothing and it looks broken. Two options:

- Send a `0x130` frame with a nonzero byte 0 from another CAN node.
- Temporarily force `systemIsOn = true` and call `bootSequence()` at the end of `setup()` to check
  the panel wiring and the animations on their own.

Every ten seconds the sketch prints a status line to serial whether or not the ignition is on, so
that is the fastest way to tell if CAN is being received at all:

```
[st] rawA=... rawB=... halves L=.. R=.. pair=. vote=. tank=..L lph=.. cons=.. rpm=.. spd=..
```

## Fuel calibration on a fresh board

The tank readout is not immediately accurate. It needs anchors, and anchors only appear when the
cluster's half-litre value ticks over while the engine is running, so the first few drives it falls
back to the cluster's coarse number plus 0.25 L. Calibration data lives in the `fuelcal` NVS
namespace and survives reflashing. It gets wiped by an erase-flash upload, and then you start over.

Watch it learn on the serial monitor:

```
[cal] loaded 12 anchors, pairing=1 vote=3
[cal] anchor ancL: 18.5L @ raw 41230
[cal] pairing decided: 0x349 bytes0-1 = LEFT tank
```
