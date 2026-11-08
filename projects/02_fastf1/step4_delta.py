"""Project 02, step 4: time delta on the final lap (Abu Dhabi 2021, lap 58).

For each driver we build t(d), the time at which he reaches track distance d.
The delta is t(HAM) - t(VER): positive means Hamilton reached that point later,
i.e. he was losing time there. The overtake shows up as a jump in the curve.
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
import fastf1

from f1_corners import corners_of

HERE = Path(__file__).resolve().parent
CACHE = str(HERE / "f1_cache")
OUT = HERE / "docs"
OUT.mkdir(exist_ok=True)
fastf1.Cache.configure(cache_dir=CACHE)


def fmt(td) -> str:
    s = td.total_seconds()
    return f"{int(s // 60)}:{s % 60:06.3f}"


def lap_by_number(session, driver, number):
    laps = session.laps.pick_drivers(driver)
    sel = laps[laps["LapNumber"] == number]
    return sel.iloc[0] if len(sel) else None


def time_curve(lap):
    tel = lap.get_telemetry()
    d = tel["Distance"].to_numpy(dtype=float)
    t = (tel["SessionTime"] - tel["SessionTime"].iloc[0]).dt.total_seconds().to_numpy()
    keep = np.concatenate([[True], np.diff(d) > 0])
    return d[keep], t[keep], tel


s = fastf1.get_session(2021, "Abu Dhabi", "R")
s.load(telemetry=True, messages=False, weather=False)

ham = lap_by_number(s, "HAM", 58)
ver = lap_by_number(s, "VER", 58)

print(f"HAM круг 58: {fmt(ham['LapTime'])}   {ham['Compound']}, износ {int(ham['TyreLife'])}")
print(f"VER круг 58: {fmt(ver['LapTime'])}   {ver['Compound']}, износ {int(ver['TyreLife'])}")

d_ham, t_ham, tel_ham = time_curve(ham)
d_ver, t_ver, tel_ver = time_curve(ver)

ref = s.laps.pick_drivers("HAM").pick_fastest()
dist, apex_idx, _ = corners_of(ref)
apexes = dist[apex_idx]

grid = np.linspace(0, min(d_ham.max(), d_ver.max()), 4000)
th = np.interp(grid, d_ham, t_ham)
tv = np.interp(grid, d_ver, t_ver)
delta = th - tv
delta -= delta[0]

# --- где дельта растёт быстрее всего -----------------------------------
grad = np.gradient(delta, grid)
seg = 60
smooth = np.convolve(grad, np.ones(seg) / seg, mode="same")
worst = int(np.argmax(smooth))
best = int(np.argmin(smooth))

print()
print(f"итог круга: Хэмилтон медленнее на {delta[-1]:+.3f} с")
print(f"быстрее всего терял на {grid[worst]:.0f} м ({smooth[worst] * 1000:.1f} мс/м)")
print(f"отбивал на {grid[best]:.0f} м ({smooth[best] * 1000:.1f} мс/м)")

print()
print("=== дельта по поворотам ===")
print(f"{'#':>3} {'апекс, м':>10} {'дельта, с':>10} {'прирост':>9}")
prev = 0.0
for i, apex in enumerate(apexes, start=1):
    val = float(np.interp(apex, grid, delta))
    print(f"{i:>3} {apex:>10.0f} {val:>+10.3f} {val - prev:>+9.3f}")
    prev = val

# --- график -------------------------------------------------------------
fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True,
                         gridspec_kw={"height_ratios": [2, 2, 1.6]})

axes[0].plot(tel_ham["Distance"], tel_ham["Speed"], label=f"HAM {fmt(ham['LapTime'])} HARD 45", linewidth=1.4)
axes[0].plot(tel_ver["Distance"], tel_ver["Speed"], label=f"VER {fmt(ver['LapTime'])} SOFT 8",
             linewidth=1.3, linestyle="--")
axes[0].set_ylabel("Speed (km/h)")
axes[0].set_title("Abu Dhabi 2021 · final lap · Hamilton defending, Verstappen attacking")
axes[0].legend(loc="lower right", fontsize=8)
axes[0].grid(alpha=0.3)

axes[1].plot(tel_ham["Distance"], tel_ham["Throttle"], linewidth=1.0, color="#2ca02c", label="HAM throttle")
axes[1].plot(tel_ver["Distance"], tel_ver["Throttle"], linewidth=1.0, color="#2ca02c",
             linestyle="--", alpha=0.8, label="VER throttle")
axes[1].plot(tel_ham["Distance"], tel_ham["Brake"].astype(float) * 100, linewidth=1.0,
             color="#d62728", alpha=0.6, label="HAM brake")
axes[1].plot(tel_ver["Distance"], tel_ver["Brake"].astype(float) * 100, linewidth=1.0,
             color="#d62728", linestyle="--", alpha=0.6, label="VER brake")
axes[1].set_ylabel("Pedals")
axes[1].legend(loc="upper right", fontsize=7, ncol=2)
axes[1].grid(alpha=0.3)

axes[2].axhline(0, color="black", linewidth=0.8)
axes[2].fill_between(grid, 0, delta, where=delta > 0, color="#d62728", alpha=0.5, label="Hamilton losing")
axes[2].fill_between(grid, 0, delta, where=delta < 0, color="#2ca02c", alpha=0.5, label="Hamilton gaining")
axes[2].set_ylabel("Delta (s)")
axes[2].set_xlabel("Distance (m)")
axes[2].legend(loc="upper left", fontsize=8)
axes[2].grid(alpha=0.3)

for ax in axes:
    for apex in apexes:
        ax.axvline(apex, color="grey", linewidth=0.5, alpha=0.35)

fig.tight_layout()
out = OUT / "delta_lap58.png"
fig.savefig(out, dpi=150)
plt.close(fig)
print()
print(f"график: {out}")
