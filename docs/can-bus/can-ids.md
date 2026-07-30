# CAN IDs

All of this was logged on a **F22 220d, N47D20C, 2014**. Treat it as F-series data. Several of
these IDs exist on E-series cars with different scaling, so do not carry the formulas backwards.

Kevin Bond's K-CAN reference at
[loopybunny.co.uk/CarPC/k_can.html](http://www.loopybunny.co.uk/CarPC/k_can.html) is what got me
started, and it is the page anyone doing this should read first. It documents an E9x though, so
it told me which IDs were worth watching rather than what they contain on my car. Every formula
below I worked out from my own logs on the F22. Where the E-series decode is actively misleading
I have said so.

Three files here, same data:

| File | For |
|------|-----|
| `can-ids.md` | reading, with the reasoning behind each decode |
| `bimmerscreenfs.dbc` | tooling (SavvyCAN, cantools, Vector, BusMaster) |
| `canbusfindings-raw.txt` | my original notes |

## Bus and format

One TWAI controller at **500 kbit/s**, accept-all filter, opened in `TWAI_MODE_LISTEN_ONLY`.
Everything below is on that single bus. Multi-byte fields are little-endian. Byte numbering is
zero-based and matches `msg.data[n]` in the sketch.

```c
twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT((gpio_num_t)5, (gpio_num_t)3, TWAI_MODE_LISTEN_ONLY);
g_config.rx_queue_len = 32;
twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
```

Listen-only matters here. The controller never transmits, never ACKs, and never puts error
frames on the wire, so adding this module cannot disturb the car's own arbitration.

## Engine

| ID | Rate | DLC | Bytes | Formula | Unit | Provenance |
|----|------|-----|-------|---------|------|------------|
| `0x0A5` | ~50 Hz | 8 | 5-6 LE | `raw / 4`, under 100 forced to 0 | rpm | mine, corrects the common decode |
| `0x3F9` | | >=6 | 4 | `raw - 48` | °C coolant | mine |
| `0x3F9` | | >=6 | 5 | `raw - 48` | °C oil | mine |
| `0x2F3` | | >=6 | 4-5 LE | `raw * 0.5` absolute, minus captured ambient | mbar gauge | mine, see caveat |
| `0x2C4` | ~7 Hz | >=2 | 0-1 LE | rolling counter, delta `* 1e-6` | litres | mine |

### 0x0A5 rpm, the one that was wrong

The decode I started from reads bytes 6 and 7 as `(B6 << 8) + B7`. It looks correct because it
lands within about 32 rpm of the truth, but it quantises to 64 rpm steps and reads a floating
60 rpm with the engine stopped, which is what gave it away. Byte 7 is a constant status byte,
`0xF1` on my car, not the low byte of the value.

The real field is bytes 5-6 little-endian at quarter-rpm resolution. The firmware also forces
anything under 100 to zero, and that clamp is load-bearing: the boost ambient capture below
depends on `rpm == 0` genuinely meaning the engine is stopped.

### 0x2F3 boost

Bytes 4-5 little-endian, 0.5 mbar per count, absolute rather than gauge.

I am fairly confident but not certain about this one. What it has going for it is that it
behaves like a real sensor rather than a modelled value: it jitters and drifts with the weather
while the engine is off, sits about +874 mbar over ambient at the logged full-load point (close
to the +0.9 bar that 59 mg/stroke of fuelling physically needs), dips to about -230 mbar on
overrun when the intake flap shuts, and decays smoothly after lift-off instead of snapping with
the pedal. It maps correctly across the range I can check. I have not confirmed it against a
scan tool, so treat the exact scaling as good rather than proven.

Because the field is absolute, gauge pressure needs an ambient reference. The firmware captures
one whenever an `0x0A5` frame has arrived and rpm is 0, since a stopped engine means manifold
pressure equals atmospheric. Weather and altitude therefore self-correct on every start. The
reference is written to NVS, throttled to changes of at least 5 mbar and at most once a minute,
so a drive where the engine was already running before the display finished booting falls back
on yesterday's ambient instead of reading 0 the whole way.

Do not confuse this with `0x3F9` byte 3, which is also a pressure but sits in the vacuum domain
and clamps between 112 and 118. That one is not boost.

### 0x2C4 consumption

A DME fuel integrator, not a rate. It is a rolling 16-bit counter, so it wraps, and the firmware
relies on `(uint16_t)(c - consPrev)` to stay correct across the wrap rather than special-casing
it.

It counts about 278 per second at warm idle and freezes completely with the engine off, which I
confirmed across three logs including one that caught the shutoff. At roughly 1 µL per count,
278 counts/s is 1.0 L/h at idle. Deltas accumulate over a one second window to give L/h, then
divide by speed for L/100km above 5 km/h; below that the display just shows L/h. It drops to
about zero on overrun fuel cut, matching what the OBC does.

Against the car's own computer at wide open throttle I read 29.5 L/100km where the cluster said
28.2. So `LITRES_PER_COUNT` is close but not exact. Trim it if yours is off by a constant factor.

## Fuel level

| ID | Rate | DLC | Bytes | Formula | Unit | Provenance |
|----|------|-----|-------|---------|------|------------|
| `0x330` | ~0.1 Hz | 8 | 4 | `raw * 0.5`, rejected above 90 | litres, left lobe | mine |
| `0x330` | ~0.1 Hz | 8 | 5 | `raw * 0.5`, rejected above 90 | litres, right lobe | mine |
| `0x349` | 5 Hz | 5 | 0-1 LE | raw sender count, curve unknown | one lobe | mine |
| `0x349` | 5 Hz | 5 | 2-3 LE | raw sender count, curve unknown | the other lobe | mine |

`0x349` comes from the JBE. This is the most involved part of the project, so it gets a full
explanation.

The tank has two lobes and two senders. `0x330` bytes 4 and 5 carry the cluster's own computed
level per lobe, but only in 0.5 L steps, and the cluster's internal 0.1 L values are never
broadcast. `0x349` carries the raw senders at much finer resolution, but on a nonlinear
per-lobe curve that only the cluster knows. A raw count on its own means nothing in litres.

**The E9x rule of `raw / 160 = litres` does not work on F-series.** That is the single biggest
trap if you come to this from the loopybunny page.

So the firmware calibrates one source against the other at runtime:

1. Both `0x349` fields run through an EMA at 0.02 per frame, about 10 seconds of smoothing,
   which kills slosh.
2. Every time a `0x330` half-litre step ticks, the smoothed raw value at that instant is a known
   pairing of raw count to an exact multiple of 0.5 L. That is an anchor.
3. Anchors fill an 82 slot table per lobe covering 0 to 40.5 L, and persist in NVS across drives.
4. With anchors either side of the current level, the raw value interpolates to about 0.1 L.

Two constraints keep it honest. Interpolation is clamped to the 0.5 L window the cluster
currently reports, so calibration can only refine the cluster's number and never contradict it.
And only single-step ticks are recorded, because refuelling crosses several boundaries between
two frames and there is no way to know the raw value at each one.

The firmware also does not assume which `0x349` field is which lobe. When exactly one side ticks
by exactly one step, whichever field moved more casts a vote. Three agreeing votes commits the
pairing to NVS. Until then the readout falls back to the cluster's 0.5 L value plus 0.25 L.

## Vehicle and body

| ID | Rate | DLC | Bytes | Formula | Unit | Provenance |
|----|------|-----|-------|---------|------|------------|
| `0x1A1` | | 5 | 2-3 LE | `raw / 64` | km/h | mine |
| `0x130` | | >=1 | 0 | nonzero means ignition live | terminal status | mine |

`0x1A1` also drives trip distance, which is integrated in software from speed and elapsed time
rather than read off the bus. It resets every ignition cycle and is clamped at 999.9 km because a
wider number overflows the value patch on screen.

`0x130` starts and stops everything. A transition to nonzero runs the boot sequence; a transition
to `0x00` plays the shutdown sound and the CRT collapse animation. Both edges are debounced by
2500 ms so cranking, which dips the terminal state, does not retrigger the boot animation.

## Decoded but not used by the firmware

These are confirmed on the F22 and sitting in my notes. The display does not read them yet.

| ID | DLC | Field | Formula |
|----|-----|-------|---------|
| `0x330` | 8 | Odometer | `B0 | (B1 << 8) | (B2 << 16)` km |
| `0x330` | 8 | Total fuel, damped | `B3` litres, lags the real value |
| `0x330` | 8 | Range | `(B6 | (B7 << 8)) / 16` km |
| `0x2F8` | 8 | Time | `B0` hour, `B1` minute, `B2` second |
| `0x2F8` | 8 | Date | `B3` day, month is the high nibble of `B4`, year is `B5 | (B6 << 8)` |
| `0x3F9` | >=6 | Vacuum-domain pressure | `B3`, clamps 112-118, not boost |

Still unknown: gear position, oil level, ambient temperature, individual wheel speeds.

## Warning thresholds

These are the firmware's own limits, not anything the car sends. Each has hysteresis so a value
sitting on the line does not retrigger the sound.

| Condition | Trigger | Clears below | DFPlayer track |
|-----------|---------|--------------|----------------|
| Oil temperature | above 95 °C | 90 °C | 2 |
| Coolant temperature | above 95 °C | 90 °C | 3 |
| Engine speed | above 4000 rpm | 3800 rpm | 4 |
| Ignition on | `0x130` byte 0 goes nonzero | n/a | 1 |
| Ignition off | `0x130` byte 0 goes `0x00` | n/a | 5 |

## Reading the bus yourself

`tools/logger.py` dumps frames over serial to a timestamped CSV. It expects a sketch that prints
raw frames, which the display firmware does not do, so it goes with the separate logging sketch I
used while working these out. Port and baud are hardcoded at the top of the file.
