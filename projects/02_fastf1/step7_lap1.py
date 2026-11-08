"""Project 02, step 7 (v2): lap 1 - Hamilton attacking, Verstappen defending.

Method: both cars are tracked along the reference racing line. Lap 1 starts on
the grid, i.e. *behind* the start/finish line, so the first samples map to the
end of the lap; those are shifted negative to keep the sequence continuous.
The pass is the instant the two positions swap.
"""

import os

for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(var, None)
os.environ["NO_PROXY"] = "*"

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import fastf1

HERE = Path(__file__).resolve().parent
CACHE = str(HERE / "f1_cache")
OUT = HERE / "docs"
OUT.mkdir(exist_ok=True)
fastf1.Cache.configure(cache_dir=CACHE)


def fmt(td):
    s = td.total_seconds()
    return f"{int(s // 60)}:{s % 60:06.3f}"


def lap1(session, driver):
    laps = session.laps.pick_drivers(driver)
    sel = laps[laps["LapNumber"] == 1]
    return sel.iloc[0]


def track_along(tel, ref_xy, ref_dist, back=8, fwd=30):
    """Follow the reference line with a moving window, wrapping at the ends."""
    pts = np.column_stack([tel["X"].to_numpy(dtype=float), tel["Y"].to_numpy(dtype=float)])
    n = len(ref_xy)

    d0 = np.hypot(ref_xy[:, 0] - pts[0, 0], ref_xy[:, 1] - pts[0, 1])
    prev = int(np.argmin(d0))

    along = np.empty(len(pts))
    for i, p in enumerate(pts):
        idx = (prev + np.arange(-back, fwd)) % n
        dist = np.hypot(ref_xy[idx, 0] - p[0], ref_xy[idx, 1] - p[1])
        k = int(idx[int(np.argmin(dist))])
        along[i] = ref_dist[k]
        prev = k
    return along


s = fastf1.get_session(2021, "Abu Dhabi", "R")
s.load(telemetry=True, messages=False, weather=False)

ref = s.laps.pick_drivers("HAM").pick_fastest()
ref_tel = ref.get_telemetry()
ref_xy = np.column_stack([ref_tel["X"].to_numpy(dtype=float),
                          ref_tel["Y"].to_numpy(dtype=float)])
ref_dist = ref_tel["Distance"].to_numpy(dtype=float)
L = float(ref_dist.max())

series = {}
for drv in ("HAM", "VER"):
    lap = lap1(s, drv)
    tel = lap.get_telemetry()
    along = track_along(tel, ref_xy, ref_dist)

    first_ahead = np.where(along < L * 0.5)[0]
    if len(first_ahead) and first_ahead[0] > 0:
        along[: first_ahead[0]] -= L

    along = pd.Series(along).rolling(7, center=True, min_periods=1).mean().to_numpy()
    series[drv] = pd.DataFrame({
        "time": tel["SessionTime"].dt.total_seconds().to_numpy(),
        "along": along,
        "speed": tel["Speed"].to_numpy(dtype=float),
    })
    print(f"{drv}: lap {fmt(lap['LapTime'])}, {lap['Compound']}, "
          f"position {along[0]:.0f} .. {along[-1]:.0f} m")

t0 = max(series["HAM"]["time"].min(), series["VER"]["time"].min())
t1 = min(series["HAM"]["time"].max(), series["VER"]["time"].max())
common = np.linspace(t0, t1, 4000)

ham = np.interp(common, series["HAM"]["time"], series["HAM"]["along"])
ver = np.interp(common, series["VER"]["time"], series["VER"]["along"])
gap = ham - ver

print(f"\nat start: HAM {gap[0]:+.1f} m relative to VER")
cross = np.where(np.diff(np.sign(gap)) != 0)[0]
cross = [c for c in cross if common[c] > t0 + 2.0]
for c in cross:
    print(f"  order change: {common[c] - t0:5.1f} s, at {ham[c] % L:6.0f} m, gap {gap[c]:+6.1f} m")
print(f"at the end of lap 1: {gap[-1]:+.1f} m (positive = Hamilton ahead)")

fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
axes[0].plot(common - t0, gap, color="#1f77b4", linewidth=1.8)
axes[0].axhline(0, color="black", linewidth=1.0)
for c in cross:
    axes[0].axvline(common[c] - t0, color="#d62728", linestyle="--", linewidth=1.2)
axes[0].set_ylabel("HAM minus VER (m)")
axes[0].set_title("Abu Dhabi 2021 - lap 1 - Hamilton attacking, Verstappen defending")
axes[0].grid(alpha=0.3)

axes[1].plot(series["HAM"]["time"] - t0, series["HAM"]["speed"], linewidth=1.4, label="HAM (MEDIUM)")
axes[1].plot(series["VER"]["time"] - t0, series["VER"]["speed"], linewidth=1.3,
             linestyle="--", label="VER (SOFT)")
for c in cross:
    axes[1].axvline(common[c] - t0, color="#d62728", linestyle="--", linewidth=1.2)
axes[1].set_xlabel("Time from the start (s)")
axes[1].set_ylabel("Speed (km/h)")
axes[1].grid(alpha=0.3)
axes[1].legend(loc="lower right", fontsize=8)

fig.tight_layout()
out = OUT / "lap1_positions.png"
fig.savefig(out, dpi=150)
plt.close(fig)
print(f"\nchart: {out}")
