"""Project 02, step 6: the hairpin where the lead changed.

Measures, to the metre, what each driver did on the approach to the hairpin
(apex at ~1471 m): brake application, brake release, minimum speed, throttle
application and exit speed.
"""

import os

for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(var, None)
os.environ["NO_PROXY"] = "*"

from pathlib import Path

import numpy as np
import pandas as pd
import fastf1

HERE = Path(__file__).resolve().parent
CACHE = str(HERE / "f1_cache")
fastf1.Cache.configure(cache_dir=CACHE)

APEX = 1471.0
BEFORE = 260.0
AFTER = 220.0


def fmt(td):
    s = td.total_seconds()
    return f"{int(s // 60)}:{s % 60:06.3f}"


def lap_by_number(session, driver, number):
    laps = session.laps.pick_drivers(driver)
    sel = laps[laps["LapNumber"] == number]
    return sel.iloc[0] if len(sel) else None


def segment(lap):
    tel = lap.get_telemetry()
    d = tel["Distance"].to_numpy(dtype=float)
    t = (tel["SessionTime"] - tel["SessionTime"].iloc[0]).dt.total_seconds().to_numpy()
    v = tel["Speed"].to_numpy(dtype=float)
    br = tel["Brake"].to_numpy(dtype=float)
    th = tel["Throttle"].to_numpy(dtype=float)

    w = (d >= APEX - BEFORE) & (d <= APEX + AFTER)
    d, t, v, br, th = d[w], t[w], v[w], br[w], th[w]

    braking = br > 0
    brake_start = float(d[braking].min()) if braking.any() else np.nan

    # отпускание тормоза: последний метр, где тормоз ещё нажат
    release = float(d[braking].max()) if braking.any() else np.nan

    apex_speed = float(v.min())
    apex_at = float(d[int(np.argmin(v))])

    after_apex = d > apex_at
    full_gas = after_apex & (th > 98)
    thr_on = float(d[full_gas].min()) if full_gas.any() else np.nan

    exit_w = (d >= APEX + 150) & (d <= APEX + 170)
    exit_speed = float(v[exit_w].mean()) if exit_w.any() else np.nan

    return {
        "lap_time": fmt(lap["LapTime"]),
        "compound": lap["Compound"],
        "tyre_life": int(lap["TyreLife"]),
        "brake_start_m": brake_start,
        "brake_release_m": release,
        "braking_len_m": release - brake_start if release == release else np.nan,
        "apex_m": apex_at,
        "apex_kmh": apex_speed,
        "throttle_on_m": thr_on,
        "exit_kmh": exit_speed,
    }


s = fastf1.get_session(2021, "Abu Dhabi", "R")
s.load(telemetry=True, messages=False, weather=False)

rows = []
for label, drv, num in [
    ("HAM baseline", "HAM", 52),
    ("HAM final", "HAM", 58),
    ("VER baseline", "VER", 52),
    ("VER final", "VER", 58),
]:
    lap = lap_by_number(s, drv, num)
    if lap is None:
        continue
    r = segment(lap)
    r["label"] = label
    rows.append(r)

df = pd.DataFrame(rows)[[
    "label", "lap_time", "compound", "tyre_life", "brake_start_m", "brake_release_m",
    "braking_len_m", "apex_m", "apex_kmh", "throttle_on_m", "exit_kmh",
]]

pd.set_option("display.width", 200)
print("=== Шпилька: вход, апекс, выход ===")
print(f"окно анализа: {APEX - BEFORE:.0f} .. {APEX + AFTER:.0f} м (апекс {APEX:.0f} м)")
print()
print(df.to_string(index=False, float_format=lambda x: f"{x:.1f}"))

print()
print("=== Что изменилось от базлайна к финальному кругу ===")
for drv in ("HAM", "VER"):
    base = next(r for r in rows if r["label"] == f"{drv} baseline")
    fin = next(r for r in rows if r["label"] == f"{drv} final")
    print(f"{drv}: тормоз позже на {base['brake_start_m'] - fin['brake_start_m']:+.0f} м, "
          f"апекс {fin['apex_kmh'] - base['apex_kmh']:+.1f} км/ч, "
          f"газ {fin['throttle_on_m'] - base['throttle_on_m']:+.0f} м, "
          f"выход {fin['exit_kmh'] - base['exit_kmh']:+.1f} км/ч")

ham_fin = next(r for r in rows if r["label"] == "HAM final")
ver_fin = next(r for r in rows if r["label"] == "VER final")
print()
print("=== Разница на финальном круге (VER минус HAM) ===")
print(f"  тормоз:  {ver_fin['brake_start_m'] - ham_fin['brake_start_m']:+.0f} м "
      f"(минус = Ферстаппен позже)")
print(f"  апекс:   {ver_fin['apex_kmh'] - ham_fin['apex_kmh']:+.1f} км/ч")
print(f"  газ:     {ver_fin['throttle_on_m'] - ham_fin['throttle_on_m']:+.0f} м "
      f"(минус = раньше)")
print(f"  выход:   {ver_fin['exit_kmh'] - ham_fin['exit_kmh']:+.1f} км/ч")
