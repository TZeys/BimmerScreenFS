# Bill of materials

Five modules, no PCB, no custom parts. Prices are rough mid-2026 EUR for single quantities from the
usual places, and they move around a lot, so treat them as a ballpark rather than a quote. The
datasheet links are the ones worth reading before you buy. Aliexpress might be your best option. Just copy the product name.

| # | Part | What it does | Rough price | Where |
|---|------|--------------|-------------|-------|
| 1 | ESP32-C3 SuperMini | Runs the firmware, decodes CAN with the built-in TWAI controller, drives the panel over SPI | 4 to 5 | [pinout reference](https://www.espboards.dev/esp32/esp32-c3-super-mini/), [ProtoSupplies](https://protosupplies.com/product/esp32c3-supermini/) |
| 2 | SN65HVD230 breakout | Turns the car's differential CANH/CANL into 3.3V logic the ESP32 can read | 4 to 10 | [TI product page](https://www.ti.com/product/SN65HVD230), [Waveshare board](https://www.amazon.com/SN65HVD230-CAN-Board-Communication-Development/dp/B00KM6XMXO) |
| 3 | 2.8 inch ILI9341 SPI TFT, 320x240 | The screen | 6 to 12 | [Elecrow](https://www.elecrow.com/2-8-inch-320x240-spi-serial-tft-lcd-module-display-with-driver-ic-ili9341.html), [non-touch version](https://www.amazon.com/2-8-inch-SPI-module-ILI9341/dp/B0C7L1SY7V) |
| 4 | DFPlayer Mini (DFR0299) | Plays the startup, shutdown and warning sounds off a microSD | 5 to 6 | [DFRobot](https://www.dfrobot.com/product-1121.html), [wiki and datasheet](https://wiki.dfrobot.com/dfr0299) |
| 5 | LM2596 buck module | Drops the car's 12V to 5.0V | 1 to 3 | [TI datasheet](https://www.ti.com/lit/ds/symlink/lm2596.pdf) |

Plus the small stuff:

| Part | Notes |
|------|-------|
| 4 ohm 3 W speaker | straight off `SPK_1` and `SPK_2`, no external amp needed |
| microSD card | FAT32, holds the five sounds. Any small card does, the files are tiny |
| wire, heatshrink | thin twisted pair for the CAN stub |

Call the whole thing 25 to 40 EUR depending on how cheap you go on the display.

## Notes on the choices

**The regulator is a buck converter, not an LDO.** I originally used an LDO. A linear regulator dropping 12V to 5V at the roughly 200 to 250 mA this build pulls
throws away about 1.75 W as heat, and a car interior in summer is the worst possible place to ask a
small TO-220 to do that. The LM2596 switches instead, so it stays cool.

**The transceiver must be a 3.3V part.** The SN65HVD230 is exactly that, which is why it pairs with
the ESP32 without level shifting. Most breakouts for it have no onboard regulator, so `VCC` goes to
3.3V and never to 5V.

**Display driver has to be ILI9341.** The sketch includes `Adafruit_ILI9341.h` and calls
`setRotation(1)` for landscape 320x240. An ST7789 or ILI9488 panel of the same size will not work
without swapping the library and redoing every coordinate in the drawing code, and there are a lot
of hardcoded coordinates. Buy the non-touch version unless you want the touch controller for
something, since nothing in the firmware uses it.

**The panel has to tolerate 3.3V logic and a 3.3V backlight.** Mine runs `VCC` and `LED` both from
the ESP32's 3.3V pin. Some modules expect 5V on `VCC` and have an onboard regulator, which changes
the wiring, so check yours.

**DFPlayer Mini is overkill for five sounds** and I would probably use a bare I2S DAC if I did it
again. It is what I had. It does mean the sounds live on a swappable microSD instead of in flash,
which is genuinely convenient when you want to change the warning chime without reflashing. Its 3 W
mono amp also drives the speaker directly, so there is nothing else to buy.

It runs on the 5V rail. The datasheet allows 3.2 to 5V, but the amplifier gets noticeably quieter at
the low end and you are already generating 5V for nothing else, so use it.

## What you also need

- A USB-C cable for flashing. The ESP32-C3 has native USB, so no separate programmer.
- Trim tools to get the head unit out. On the F22 it is clips and four bolts.
- A multimeter. Not optional for trim-bucks: you are setting a regulator output and confirming which pin at the
  connector is which before you cut anything.
