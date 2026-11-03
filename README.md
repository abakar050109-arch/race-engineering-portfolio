# Race Engineering Portfolio

Telemetry analysis and race engineering projects — on the path from sim racing data to a race engineer seat in international motorsport.

## About

First-year engineering student at **Bauman Moscow State Technical University** (Department of Automatic Control Systems, IU-1).

**Goal:** race engineer in international motorsport — starting in GT3/GT4, moving through WEC / Formula E, with **Formula 1** as the long-term target.

This repository is a working portfolio, not a showcase. Everything here is built from real data: Assetto Corsa Competizione logs exported through MoTeC i2, and real Formula 1 telemetry through FastF1.

## Tools

| Area | Stack |
|---|---|
| Telemetry logging | Assetto Corsa Competizione, MoTeC i2 |
| Data analysis | Python 3.11, pandas, numpy, scipy |
| Visualisation | matplotlib |
| Real-world F1 data | FastF1 |
| Version control | Git, GitHub |

## Projects

| # | Project | Focus | Status |
|---|---------|-------|--------|
| 01 | Lap detection & telemetry baseline | Slicing a session into laps, speed / throttle / brake traces | 🚧 in progress |
| 02 | Time delta analysis | Where time is gained and lost against a reference lap | ⏳ planned |
| 03 | Braking analysis | Brake points, release, trail braking | ⏳ planned |
| 04 | Tyre analysis | Temperatures, pressures, degradation across a stint | ⏳ planned |
| 05 | Setup comparison | Effect of a setup change on the same car and track | ⏳ planned |
| 06 | Ideal lap builder | Theoretical best lap from best sectors | ⏳ planned |
| 07 | Strategy simulator | Stint length, pit window, fuel and tyre degradation | ⏳ planned |
| 08 | Formula 1 telemetry | Real F1 data comparison through FastF1 | ⏳ planned |

## Standard

Every project in this repository follows the same structure:

```
raw data  →  analysis  →  engineering conclusion  →  report
```

A chart on its own is not a result. The result is a sentence a driver can act on:

> "In T3 you brake 5 metres earlier than in your best lap and release the brake 0.1 s later — that costs about 0.2 s per lap."

If a project cannot produce a sentence like that, it is not finished.

## Repository layout

```
race-engineering-portfolio/
├── README.md            ← this file
├── ROADMAP.md           ← project plan and skill progression
├── projects/
│   ├── 00_TEMPLATE/     ← project report template
│   └── ...              ← one folder per project
└── docs/                ← reports, notes, CV
```

## Contact

- GitHub: `@your-handle`
- LinkedIn: `your-linkedin`
- Email: `your-email`
