# Project 02 — Attack and defence: Abu Dhabi 2021, final lap

Why Hamilton could not defend the lead on the last lap, and what Verstappen did
differently. Built on real F1 telemetry through FastF1.

## Overview

The 2021 Abu Dhabi finale is usually discussed as a rules story. This project
looks at the part that telemetry can answer: **what the two drivers actually did
with the brakes and the throttle**, and how much of the 2.7-second gap on the
final lap came from where.

The same race contains both roles, mirrored:

| Moment | Attacking | Defending | Outcome |
|---|---|---|---|
| Lap 1 | Hamilton | Verstappen | Hamilton takes the lead |
| Lap 58 | Verstappen | Hamilton | Verstappen takes the lead |

## Data

| | |
|---|---|
| Session | 2021 Abu Dhabi Grand Prix, Race |
| Source | FastF1 3.9.0 (official F1 timing data) |
| Channels | Speed, throttle, brake, gear, X/Y position, `DriverAhead` |
| Reference lap | Hamilton fastest lap, 1:26.615 |

FastF1 needs credentials for the F1 live timing service. Without them the
requests return HTTP 403 and every channel comes back empty — see
`data/README.md`.

## Method

1. **Corners from curvature.** The driven path is turned into curvature
   (`dθ/ds`), smoothed over 40 m and peak-picked. Speed minima alone are not
   enough at Yas Marina: several corners are taken above 150 km/h.
2. **Per-corner metrics.** For each corner: brake application point, brake
   release, minimum speed, full-throttle point after the apex, exit speed 150 m
   later.
3. **Delta between drivers.** For each driver the function `t(d)` (time at which
   he reaches distance `d`) is built and the two curves are subtracted.
4. **Position along track.** Both cars are projected onto the reference line to
   find the instant the order changed.

## Results

### The overtake happened at the hairpin

Projection onto the racing line gives the gap in metres over the final lap: the
curves cross at **20.6 s, at ~1400 m** — on the brakes into the hairpin whose
apex sits at 1471 m.

| | Hamilton (HARD, 45 laps) | Verstappen (SOFT, 8 laps) |
|---|---|---|
| Brake application | 1307 m | 1303 m |
| Brake release | 1446 m | 1427 m |
| Braking distance | **139 m** | 124 m |
| Minimum speed | **67 km/h** | 75 km/h |
| Full throttle after apex | 1511 m | **1486 m** |
| Exit speed (+150 m) | 228 km/h | **234 km/h** |

### What changed against each driver's own baseline

Same driver, same corner, clean lap (lap 52) versus the final lap:

| | Hamilton | Verstappen |
|---|---|---|
| Brake point | 10 m later | unchanged |
| Braking distance | 102 → 139 m | 116 → 124 m |
| Minimum speed | 99 → 67 km/h (**−32**) | 93 → 75 km/h (−18) |
| Throttle on | 1506 → 1511 m | 1507 → 1486 m (**−21 m earlier**) |
| Exit speed | 236 → 228 km/h (−8) | 234 → 234 km/h (unchanged) |

### Lap 1: the mirrored situation

Tracking both cars along the racing line for the opening lap:

| Moment | What happens |
|---|---|
| Start | Hamilton is 15.6 m behind (second grid slot) |
| 3.7 s, ~160 m | The gap is within 1 m — they are side by side into Turn 1 |
| **42.8 s, ~2610 m** | **The order changes at the second hairpin** |
| End of lap 1 | Hamilton leads by 56 m |

The pass happened in the hairpin complex at ~2600 m, not on the straight: this
track rewards the driver who gets the exit of the slow corner, and that is where
both passes of the race were made.

### The engineering conclusion

Hamilton defended by braking later and holding the brake 26 metres longer than
in his own clean lap. That cost him the apex (67 km/h instead of 99) and, more
importantly, the exit: he got back on full throttle 25 m later than Verstappen
and left the corner 6 km/h slower.

Verstappen gave away apex speed (75 instead of 93) but **recovered the exit**:
he opened the throttle 21 m earlier than in his own baseline and matched his
normal exit speed. One lap of that, and the pass was done.

In one sentence: the defender spent his tyres and his line on not being
overtaken into the corner, and had nothing left for the exit; the attacker spent
the apex and bought the straight.

## Data availability (why this project covers 2021 only)

F1 live timing is no longer open. Without a valid account the CDN answers `403`
and FastF1 falls back to its community mirror; the mirror holds seasons 2018-2022
only, so 2023 and later return `404`.

Checked on 13 November 2026 with FastF1 3.9.2 (the latest release, published
2 November 2026):

| Check | Result |
|---|---|
| Sign-in to the F1 account | fails, `404` on `account.formula1.com/scripts/main.min.js` |
| Official CDN without a token | `403` |
| Mirror, 2021 and 2022 sessions | `200` |
| Mirror, 2023 and later | `404` |

An [issue in the FastF1 tracker](https://github.com/theOehrly/Fast-F1/issues/988)
shows the same shape of failure: access now requires an F1 TV Access account,
and some networks are refused before authentication runs.

**Consequence:** the planned second block, Sao Paulo 2024 (Verstappen vs Norris),
could not be produced and is not included. Abu Dhabi 2021 loads because its data
was cached while authentication still worked. A second block is possible once
sign-in is restored, either through a fixed FastF1 release or a different
network.

## Limitations

- **One lap is not a sample.** Every number here comes from a single lap of each
  driver. The conclusion is a well-supported hypothesis, not a proof.
- **Tyres differ.** Hamilton's set was 45 laps old and cold after the safety car;
  Verstappen's was 8 laps old. This is the situation being analysed, not a
  controlled experiment.
- **Track position differs.** The defender brakes on a different line by design,
  so part of the braking difference is the defensive line, not the tyre.
- **Corner numbering is ours.** Corners are numbered by distance from the start
  line; the hairpin is corner 4 in this code and Turn 5 officially.
- **Lap 1 is approximate.** The gap curve crosses zero several times around the
  hairpin complex, so the exact metre of the pass is uncertain; what is certain
  is the corner. The time delta method does not work here at all (standing
  start, cold tyres, grid offset), which is why lap 1 uses position tracking.
- **Only one race.** See *Data availability* above: 2023+ sessions are not
  reachable from this network, so the second block is missing.
- **Yas Marina passes close to itself.** A global nearest-point projection jumps
  between parallel pieces of track and produced 10 km "laps" in the first
  attempt. The fix was tracking the position in a moving window.

## Files

| File | Purpose |
|---|---|
| `f1_corners.py` | shared corner detection |
| `step1_corners.py` | corner list from the fastest lap |
| `step2_corner_compare.py` | per-corner table, four laps |
| `step3_track_map.py` | circuit map with numbered corners |
| `step4_delta.py` | time delta over the final lap |
| `step5_overtake.py` | where the order changed |
| `step6_hairpin.py` | detailed hairpin comparison |
| `step7_lap1.py` | lap 1, the mirrored situation (inconclusive) |
| `docs/` | charts |

## How to run

```bash
python step1_corners.py
python step6_hairpin.py
```

On Windows double-click `run_step1.bat` / `run_step2.bat`: they call the system
Python 3.11, which already has FastF1. The PyCharm training venv does not.
