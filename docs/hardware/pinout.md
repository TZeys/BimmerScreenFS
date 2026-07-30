# Pinout

Every pin below is either a `#define` in the sketch, an argument to a driver init call, or
something I confirmed on my own build. Nothing here is inferred from a tutorial.

## ESP32-C3 SuperMini

| GPIO | Goes to | Set in code by |
|------|---------|----------------|
| 1 | TFT `DC` | `#define TFT_DC 1` |
| 3 | SN65HVD230 `RX` (CAN receive into the ESP32) | `TWAI_GENERAL_CONFIG_DEFAULT(..., (gpio_num_t)3, ...)` |
| 4 | TFT `SCK` | default FSPI clock, not set in code |
| 5 | SN65HVD230 `TX` | `TWAI_GENERAL_CONFIG_DEFAULT((gpio_num_t)5, ...)` |
| 6 | TFT `SDI` / `MOSI` | default FSPI MOSI, not set in code |
| 8 | TFT `CS` | `#define TFT_CS 8` |
| 20 | DFPlayer `TX` (audio module talking back) | `DFSerial.begin(9600, SERIAL_8N1, 20, 21)` |
| 21 | DFPlayer `RX` (commands out to the module) | same call, 4th argument |

The TFT reset line is not driven. The sketch builds the driver with
`Adafruit_ILI9341(TFT_CS, TFT_DC)`, and that two argument constructor leaves `_RST` at -1, so
tie the module's `RST` to 3.3V.

## Three pin conflicts worth knowing about

These all work on my build, but only for reasons that are easy to break if you start rewiring.

**GPIO5 is CAN TX and also the ESP32-C3's default SPI MISO.** The sketch never sets SPI pins, so
`SPI` comes up on the C3 defaults (SCK 4, MISO 5, MOSI 6, SS 7). `tft.begin()` runs first and
claims GPIO5 as a MISO input, then `twai_driver_install()` reassigns it through the GPIO matrix.
That is fine here because the display is write only: nothing calls `readcommand8()`, there is no
touch controller, and the panel's `SDO` pin is left unconnected. If you ever need to read from the
display, move CAN TX first.

**GPIO8 is CS and also the onboard LED on most SuperMini boards.** It is also a strapping pin that
has to be high at reset. Chip select idles high so booting is fine, but the LED flickers with SPI
traffic, and a display module with a pulldown on `CS` will stop the board from booting.

**GPIO20 and GPIO21 are the chip's default UART0 pins.** The DFPlayer sits on them via UART1. That
only works if `Serial` is on USB, so **USB CDC On Boot has to be enabled**. Turn it off and
`Serial.begin(115200)` grabs UART0 on the same two pins and fights the audio module. This is the
single most likely reason someone else's build comes up mute.

## SN65HVD230

| Module pin | Connects to |
|------------|-------------|
| `VCC` | 3.3V, not 5V |
| `GND` | common ground |
| `RX` | ESP32 GPIO3 |
| `TX` | ESP32 GPIO5 |
| `CANH` | headunit connector pin 11 |
| `CANL` | headunit connector pin 9 |

The transceiver is a 3.3V part. Most breakout boards for it have no regulator, so feeding `VCC`
from the 5V rail will damage it. Take 3.3V off the ESP32.

Do not fit a 120 ohm termination resistor. The car's bus is already terminated at both ends, and
this module is a passive third party sitting in the middle of it. Some SN65HVD230 boards ship with
termination populated, so check the board and remove it if it is there.

## Display

2.8 inch ILI9341, 320x240, running in landscape (`setRotation(1)`).

| Module pin | Connects to |
|------------|-------------|
| `VCC` | 3.3V |
| `GND` | common ground |
| `CS` | GPIO8 |
| `RESET` | 3.3V |
| `DC` | GPIO1 |
| `SDI` / `MOSI` | GPIO6 |
| `SCK` | GPIO4 |
| `LED` | 3.3V |
| `SDO` / `MISO` | leave unconnected |

The backlight is wired straight to 3.3V. There is no PWM and no brightness control anywhere in the
firmware, so it is on at full whenever the module has power. That matters for the drain problem
described in [schematic.md](schematic.md).

## DFPlayer Mini

| Module pin | Connects to |
|------------|-------------|
| `VCC` | 5V rail |
| `GND` | common ground |
| `RX` | ESP32 GPIO21, through a 1k series resistor |
| `TX` | ESP32 GPIO20 |
| `SPK_1` / `SPK_2` | 4 ohm 3 W speaker |

`VCC` is on the 5V rail off the buck, not 3.3V. The module accepts 3.2 to 5V but the onboard
amplifier is quieter at the bottom of that range.

Runs at 9600 baud 8N1. The 1k resistor on the module's `RX` is what DFRobot's own datasheet asks
for, and it does cut down on audible noise when the module is idle.

The speaker is a 4 ohm 3 W driver straight off `SPK_1` and `SPK_2`. DFPlayer has a 3 W mono
amplifier built in, so it matches without an external amp.

## microSD card

The sounds live on a microSD card in the DFPlayer, not in the ESP32's flash. Format it FAT32 and
name the files `0001.mp3`, `0002.mp3`, `0003.mp3`, `0004.mp3`, `0005.mp3`.

Tracks, in the order the firmware calls them:

| Track | Plays when |
|-------|-----------|
| 1 | ignition on, after the boot animation |
| 2 | oil above 95 °C |
| 3 | coolant above 95 °C |
| 4 | rpm above 4000 |
| 5 | ignition off |

Volume is fixed at 30, which is the module's maximum, and `enableDAC()` is called at startup.

The numbering is not cosmetic. DFPlayer indexes tracks by the order they were physically written to
the card rather than by filename, so copy them across one at a time in order. See
[build-and-flash.md](../firmware/build-and-flash.md) if the sounds come out in the wrong order.

## Power

| From | To |
|------|-----|
| Headunit connector pin 15 (12V, terminal 30) | LM2596 input |
| Headunit connector pin 12 (GND) | LM2596 ground and the common ground |
| LM2596 5V output | ESP32-C3 `5V` pin, DFPlayer `VCC` |
| ESP32-C3 `3V3` pin | SN65HVD230 `VCC`, TFT `VCC`, TFT `LED` |

Set the LM2596 output to 5.0V with the trimpot and check it with a meter **before** connecting the
ESP32. These modules ship at whatever the pot was left at, and plenty arrive above 12V.

## Every pin here is confirmed

Signal pins come from the sketch, the rails and the connector pins are from my own build. Nothing on
this page is inferred from a reference design, so if something does not match your hardware it is
because your modules differ, not because I guessed.
