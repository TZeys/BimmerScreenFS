# Changelog

## 2026-07-30

First public version. The firmware itself has been running in the car for a while; this is the point
where it stopped being three files on my desktop.

**Relicensed from GPL-3.0 to MIT.** The repo went up with GPL-3.0 and I have changed it to MIT. I am
the only author so this is mine to do, but it does loosen the terms: closed-source forks are allowed
now and they were not before. Anyone who forked while it was GPL-3.0 keeps GPL rights to that
snapshot. The vendored Adafruit header was always BSD and stays BSD.

Repo work:

- Split the 320x240 background bitmap out of the sketch into `background.h`. It was 76,800 hex values
  on one 537 KB line, which meant GitHub would not render or diff the sketch at all. The array is
  byte for byte the same, the `.ino` is now 25 KB.
- Moved the sketch into `src/esp32c3sp_firmware_bmw/` so the folder name matches the `.ino` and
  Arduino IDE opens it without complaining, and the logger into `tools/`.
- Wrote up the CAN work three ways: prose with the reasoning in `docs/can-bus/can-ids.md`, a DBC file
  for SavvyCAN and cantools, and my original notes kept as-is.
- Documented the pinout, the BOM, and the wiring, including the head unit connector pinout.
- Added a file header to the sketch. Left the existing comments alone.

Things I worked out while writing the docs rather than while building it:

- Pin 15 is labelled Terminal 30 on the connector diagram, but it is not permanently live on this
  car. It wakes when the car is unlocked and drops about 30 minutes after locking, because the energy
  management sleeps the head unit feed. I briefly had this documented the other way round, as a
  standby drain problem, on the strength of the connector label alone. It is not a problem: it is why
  the display powers itself up and down without any sleep code, and why the shutdown animation gets
  to finish after ignition off.
- GPIO5 is CAN TX and also the C3's default SPI MISO. It works because the display is never read and
  listen-only never drives TX, but it is luck rather than design.
- GPIO20 and GPIO21 are the default UART0 pins, so the audio only works because USB CDC On Boot is
  enabled. That is now the first thing the build doc tells you.

Firmware state at this point, for reference:

- Eight values on screen: rpm, speed, trip distance, consumption, oil, coolant, boost, fuel.
- Fuel level self-calibrates by anchoring the raw senders against the cluster's 0.5 L ticks, and
  learns which sender belongs to which side of the tank.
- Boost captures its own ambient reference whenever rpm is 0, persisted to NVS.
- rpm decode uses bytes 5 and 6 of `0x0A5`. The older bytes 6 and 7 version was wrong: it quantised
  to 64 rpm steps and read about 60 rpm with the engine stopped.
- TWAI is listen-only at 500 kbit/s with a 32 frame receive queue.

Known and not fixed: consumption reads about 4% high against the OBC, `0x2F3` scaling is well
supported but unproven, and tank accuracy needs a few drives to build up calibration anchors.
