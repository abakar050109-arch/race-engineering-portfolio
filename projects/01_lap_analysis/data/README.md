# Data

Put MoTeC CSV exports here. **These files are ignored by git** — raw logs are
large and belong to the driver, not to the repository.

## Expected format

A MoTeC i2 CSV export from Assetto Corsa Competizione:

- a metadata block on top, then a header row whose first field is `Time`;
- `SPEED` in **m/s** (not km/h);
- `THROTTLE` and `BRAKE` in **percent** (0–100), `BRAKE` is not a boolean;
- roughly **200 Hz**;
- the track name in the `Venue` field of the metadata block.

Example of the first lines:

```
"Format","MoTeC CSV File",,,"Workbook",""
"Venue","red_bull_ring",,,"Worksheet",""
"Vehicle","AMG GT3 Evo",,,"Vehicle Desc",""
...
"Time","LAP_BEACON","G_LAT","ROTY","STEERANGLE","SPEED","THROTTLE","BRAKE","GEAR",...
```

## Files used in this project

| File | Track | Car | Laps |
|------|-------|-----|------|
| `data.csv` | Red Bull Ring | Mercedes-AMG GT3 Evo | 10 |
| `data1.csv` | Silverstone | Porsche 992 GT3 R | 5 |

## Running with data

```bash
python analyze.py                 # every CSV in this folder
python analyze.py --data x.csv    # one specific file
```

The track length is looked up from the venue name. For a track that is not in
`TRACK_LENGTHS_M`, pass it explicitly:

```bash
python analyze.py --track-length 4318
```
