"""Project 02, step 2: per-corner comparison.

For each corner measures:
  brake_on   — where the brake was applied (distance, m)
  min_speed  — speed at the apex (km/h)
  throttle_on— where full throttle was re-applied after the apex (m)
  exit_speed — speed 150 m after the apex (km/h)

Laps used:
  HAM 52 — baseline: clean air, 39-lap-old hards
  HAM 58 — final lap, defending on 45-lap-old hards
  VER 52 — baseline on hards
  VER 58 — final lap, attacking on fresh softs
"""

import os

for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(var, None)
os.environ["NO_PROXY"] = "*"

import numpy as np
import fastf1
from scipy.signal import find_peaks

CACHE = r"C:\Users\user\OneDrive\Документы\deepseek-harness\default-workspace\race-engineering-portfolio\projects\02_fastf1\f1_cache"
fastf1.Cache.configure(cache_dir=CACHE)

s = fastf1.get_session(2021, "Abu Dhabi", "R")
s.load(telemetry=True, messages=False, weather=False)


def corners_of(lap):
    tel = lap.get_telemetry()
    x = tel["X"].to_numpy(dtype=float)
    y = tel["Y"].to_numpy(dtype=float)
    d = tel["Distance"].to_numpy(dtype=float)

    dx, dy = np.diff(x), np.diff(y)
    ds = np.hypot(dx, dy)
    ds[ds < 1e-6] = np.nan
    theta = np.unwrap(np.arctan2(dy, dx))
    kappa = np.nan_to_num(np.diff(theta) / ds[:-1])

    step = float(np.nanmedian(ds))
    win = max(5, int(40.0 / max(step, 0.1)) | 1)
    kappa = np.convolve(kappa, np.ones(win) / win, mode="same")

    min_gap = max(1, int(60.0 / max(step, 0.1)))
    peaks, _ = find_peaks(np.abs(kappa), prominence=0.0025, distance=min_gap)

    merged = []
    for p in peaks:
        if merged and abs(d[p] - d[merged[-1]]) < 40.0:
            if abs(kappa[p]) > abs(kappa[merged[-1]]):
                merged[-1] = p
        else:
            merged.append(p)
    return np.array([d[p] for p in merged])


def lap_by_number(driver, number):
    laps = s.laps.pick_drivers(driver)
    sel = laps[laps["LapNumber"] == number]
    return sel.iloc[0] if len(sel) else None


def measure(lap, apexes):
    tel = lap.get_telemetry()
    d = tel["Distance"].to_numpy(dtype=float)
    v = tel["Speed"].to_numpy(dtype=float)
    brake = tel["Brake"].to_numpy(dtype=float)
    thr = tel["Throttle"].to_numpy(dtype=float)

    rows = []
    for apex in apexes:
        window = (d >= apex - 180) & (d <= apex)
        brake_pts = d[window & (brake > 0)]
        brake_on = float(brake_pts.min()) if len(brake_pts) else np.nan

        near = (d >= apex - 25) & (d <= apex + 25)
        apex_speed = float(v[near].min()) if near.any() else np.nan

        after = (d > apex + 10) & (d <= apex + 250)
        full = d[after & (thr > 95)]
        throttle_on = float(full.min()) if len(full) else np.nan

        exit_w = (d >= apex + 140) & (d <= apex + 160)
        exit_speed = float(v[exit_w].mean()) if exit_w.any() else np.nan

        rows.append({
            "apex_m": round(float(apex)),
            "brake_on_m": round(brake_on) if brake_on == brake_on else None,
            "min_kmh": round(apex_speed, 1) if apex_speed == apex_speed else None,
            "thr_on_m": round(throttle_on) if throttle_on == throttle_on else None,
            "exit_kmh": round(exit_speed, 1) if exit_speed == exit_speed else None,
        })
    return rows


ref = s.laps.pick_drivers("HAM").pick_fastest()
apexes = corners_of(ref)

laps = {
    "HAM 52": lap_by_number("HAM", 52),
    "HAM 58": lap_by_number("HAM", 58),
    "VER 52": lap_by_number("VER", 52),
    "VER 58": lap_by_number("VER", 58),
}

data = {}
for name, lap in laps.items():
    if lap is None:
        print(f"{name}: круг не найден")
        continue
    data[name] = measure(lap, apexes)

print(f"поворотов: {len(apexes)}")
for metric, label, unit in [
    ("min_kmh", "МИНИМАЛЬНАЯ СКОРОСТЬ", "км/ч"),
    ("exit_kmh", "СКОРОСТЬ НА ВЫХОДЕ (+150 м)", "км/ч"),
]:
    print()
    print(f"=== {label} ({unit}) ===")
    print(f"{'апекс':>7} | {'HAM 52':>7} {'HAM 58':>7} {'ΔHAM':>6} | {'VER 52':>7} {'VER 58':>7} {'ΔVER':>6} | {'VER58-HAM58':>11}")
    for i, apex in enumerate(apexes):
        row = {k: data[k][i] for k in data}
        vals = [row[k][metric] for k in ("HAM 52", "HAM 58", "VER 52", "VER 58")]
        dh = None if None in (row["HAM 52"][metric], row["HAM 58"][metric]) else row["HAM 58"][metric] - row["HAM 52"][metric]
        dv = None if None in (row["VER 52"][metric], row["VER 58"][metric]) else row["VER 58"][metric] - row["VER 52"][metric]
        diff = None if None in (row["HAM 58"][metric], row["VER 58"][metric]) else row["VER 58"][metric] - row["HAM 58"][metric]
        fmt = lambda x: f"{x:+6.1f}" if x is not None else "     —"
        print(f"{apex:>7.0f} | {str(vals[0]):>7} {str(vals[1]):>7} {fmt(dh)} | "
              f"{str(vals[2]):>7} {str(vals[3]):>7} {fmt(dv)} | {fmt(diff):>11}")
