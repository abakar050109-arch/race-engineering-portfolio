"""Project 02, step 5: locate the overtake on the final lap.

Method: the reference racing line is a list of points ordered by distance along
the lap. Each car's telemetry sample is matched to the reference point closest
to *where the car is expected to be* (a small window ahead of the previous
match), not to the globally nearest point. Yas Marina passes close to itself in
the marina section, and a global nearest-point search jumps between the two
parallel pieces of track - that is what broke the first attempt.
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


def lap_by_number(session, driver, number):
    laps = session.laps.pick_drivers(driver)
    sel = laps[laps["LapNumber"] == number]
    return sel.iloc[0] if len(sel) else None


def along_track(tel, ref_xy, ref_dist, window_back=6, window_fwd=25):
    """Track progress along the reference line, sample by sample."""
    pts = np.column_stack([tel["X"].to_numpy(dtype=float), tel["Y"].to_numpy(dtype=float)])
    n = len(ref_xy)
    prev = 0
    along = np.empty(len(pts))

    for i, p in enumerate(pts):
        lo = max(0, prev - window_back)
        hi = min(n, prev + window_fwd)
        d = np.hypot(ref_xy[lo:hi, 0] - p[0], ref_xy[lo:hi, 1] - p[1])
        k = lo + int(np.argmin(d))
        along[i] = ref_dist[k]
        prev = k

    return pd.Series(along).rolling(5, center=True, min_periods=1).mean().to_numpy()


s = fastf1.get_session(2021, "Abu Dhabi", "R")
s.load(telemetry=True, messages=False, weather=False)

ref = s.laps.pick_drivers("HAM").pick_fastest()
ref_tel = ref.get_telemetry()
ref_xy = np.column_stack([ref_tel["X"].to_numpy(dtype=float),
                          ref_tel["Y"].to_numpy(dtype=float)])
ref_dist = ref_tel["Distance"].to_numpy(dtype=float)

lap_ham = lap_by_number(s, "HAM", 58)
lap_ver = lap_by_number(s, "VER", 58)
print(f"HAM lap 58: {fmt(lap_ham['LapTime'])}   VER lap 58: {fmt(lap_ver['LapTime'])}")

series = {}
for drv, lap in (("HAM", lap_ham), ("VER", lap_ver)):
    tel = lap.get_telemetry()
    along = along_track(tel, ref_xy, ref_dist)
    series[drv] = pd.DataFrame({
        "time": tel["SessionTime"].dt.total_seconds().to_numpy(),
        "along": along,
        "speed": tel["Speed"].to_numpy(dtype=float),
    })
    print(f"  {drv}: {along[0]:.0f} .. {along[-1]:.0f} m")

t0 = max(series["HAM"]["time"].min(), series["VER"]["time"].min())
t1 = min(series["HAM"]["time"].max(), series["VER"]["time"].max())
common = np.linspace(t0, t1, 4000)

ham_pos = np.interp(common, series["HAM"]["time"], series["HAM"]["along"])
ver_pos = np.interp(common, series["VER"]["time"], series["VER"]["along"])
gap = ham_pos - ver_pos
gap_s = pd.Series(gap).rolling(9, center=True, min_periods=1).mean().to_numpy()

print(f"\ngap at lap start: {gap_s[0]:+.1f} m")

# первое устойчивое пересечение нуля
overtake = None
for i in range(1, len(gap_s)):
    if gap_s[i] < -1.0 and gap_s[i - 1] >= -1.0:
        overtake = i
        break

if overtake is not None:
    print(f"\nOVERTAKE at {common[overtake] - t0:.2f} s, track position "
          f"{ham_pos[overtake]:.0f} m, gap {gap_s[overtake]:+.1f} m")
    print(f"  1 s earlier: {gap_s[max(0, overtake - 60)]:+.1f} m")
    print(f"  1 s later:   {gap_s[min(len(gap_s) - 1, overtake + 60)]:+.1f} m")
else:
    print("\nno overtake detected in this window")

print(f"at finish: {gap_s[-1]:+.1f} m (negative = Verstappen ahead)")

fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
axes[0].plot(common - t0, gap_s, color="#1f77b4", linewidth=1.8)
axes[0].axhline(0, color="black", linewidth=1.0)
if overtake is not None:
    axes[0].axvline(common[overtake] - t0, color="#d62728", linestyle="--",
                    label=f"overtake at {ham_pos[overtake]:.0f} m")
    axes[0].legend(loc="upper right", fontsize=8)
axes[0].set_ylabel("Hamilton minus Verstappen (m)")
axes[0].set_title("Abu Dhabi 2021 - final lap - relative track position")
axes[0].grid(alpha=0.3)

axes[1].plot(series["HAM"]["time"] - t0, series["HAM"]["speed"], linewidth=1.4, label="HAM")
axes[1].plot(series["VER"]["time"] - t0, series["VER"]["speed"], linewidth=1.3,
             linestyle="--", label="VER")
if overtake is not None:
    axes[1].axvline(common[overtake] - t0, color="#d62728", linestyle="--", linewidth=1.2)
axes[1].set_xlabel("Time from the start of lap 58 (s)")
axes[1].set_ylabel("Speed (km/h)")
axes[1].grid(alpha=0.3)
axes[1].legend(loc="lower right", fontsize=8)

fig.tight_layout()
out = OUT / "overtake_lap58.png"
fig.savefig(out, dpi=150)
plt.close(fig)
print(f"\nchart: {out}")
