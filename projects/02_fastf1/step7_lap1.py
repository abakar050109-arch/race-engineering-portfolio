"""Project 02, step 7: lap 1, where Hamilton attacked and Verstappen defended.

Both cars start from the grid, so their telemetry distance starts at zero at
different physical points (the grid slots). To compare them we align by track
position: Verstappen started roughly one grid slot (about 8 m) ahead.
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

HERE = Path(__file__).resolve().parent
CACHE = str(HERE / "f1_cache")
OUT = HERE / "docs"
OUT.mkdir(exist_ok=True)
fastf1.Cache.configure(cache_dir=CACHE)

GRID_OFFSET = 8.0


def fmt(td):
    s = td.total_seconds()
    return f"{int(s // 60)}:{s % 60:06.3f}"


def lap1(session, driver):
    laps = session.laps.pick_drivers(driver)
    sel = laps[laps["LapNumber"] == 1]
    return sel.iloc[0]


s = fastf1.get_session(2021, "Abu Dhabi", "R")
s.load(telemetry=True, messages=False, weather=False)

data = {}
for drv in ("HAM", "VER"):
    lap = lap1(s, drv)
    tel = lap.get_telemetry()
    d = tel["Distance"].to_numpy(dtype=float)
    t = (tel["SessionTime"] - tel["SessionTime"].iloc[0]).dt.total_seconds().to_numpy()
    keep = np.concatenate([[True], np.diff(d) > 0])
    data[drv] = {
        "lap": lap,
        "d": d[keep],
        "t": t[keep],
        "v": tel["Speed"].to_numpy(dtype=float)[keep],
        "start": tel["SessionTime"].iloc[0],
    }
    print(f"{drv}: lap {fmt(lap['LapTime'])}, telemetry start {tel['SessionTime'].iloc[0]}, "
          f"distance {d[-1]:.0f} m, compound {lap['Compound']}")

start_diff = (data["HAM"]["start"] - data["VER"]["start"]).total_seconds()
print(f"разница времени старта телеметрии: {start_diff:+.3f} с")

grid = np.linspace(GRID_OFFSET, min(data["HAM"]["d"].max(), data["VER"]["d"].max() + GRID_OFFSET) - 5, 3000)
t_ham = np.interp(grid, data["HAM"]["d"], data["HAM"]["t"])
t_ver = np.interp(grid - GRID_OFFSET, data["VER"]["d"], data["VER"]["t"])

# выравниваем по абсолютному времени: обе телеметрии начинаются на старте
delta = (t_ham + start_diff) - t_ver
delta -= np.interp(60.0, grid, delta)   # нормируем на 60-м метре, где оба уже едут

print(f"\nдельта на 200 м: {np.interp(200, grid, delta):+.3f} с")
print(f"дельта на 1000 м: {np.interp(1000, grid, delta):+.3f} с")
print(f"дельта на 2600 м: {np.interp(2600, grid, delta):+.3f} с")
print(f"дельта на финише: {delta[-1]:+.3f} с (минус = Хэмилтон быстрее)")

cross = np.where(np.diff(np.sign(delta)) != 0)[0]
cross = [c for c in cross if grid[c] > 100]
for c in cross[:5]:
    print(f"  смена знака: {grid[c]:.0f} м, дельта {delta[c]:+.3f} с")

fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
axes[0].plot(data["HAM"]["d"], data["HAM"]["v"], linewidth=1.4, label="HAM lap 1")
axes[0].plot(data["VER"]["d"] + GRID_OFFSET, data["VER"]["v"], linewidth=1.3,
             linestyle="--", label="VER lap 1 (shifted)")
axes[0].set_ylabel("Speed (km/h)")
axes[0].set_title(f"Abu Dhabi 2021 - lap 1 - HAM {fmt(data['HAM']['lap']['LapTime'])} "
                  f"(MEDIUM) vs VER {fmt(data['VER']['lap']['LapTime'])} (SOFT)")
axes[0].grid(alpha=0.3)
axes[0].legend(loc="lower right", fontsize=8)

axes[1].axhline(0, color="black", linewidth=0.8)
axes[1].fill_between(grid, 0, delta, where=delta > 0, color="#d62728", alpha=0.5, label="HAM losing")
axes[1].fill_between(grid, 0, delta, where=delta < 0, color="#2ca02c", alpha=0.5, label="HAM gaining")
for c in cross[:5]:
    axes[1].axvline(grid[c], color="grey", linestyle=":", linewidth=1.0)
axes[1].set_xlabel("Distance (m)")
axes[1].set_ylabel("Delta (s)")
axes[1].grid(alpha=0.3)
axes[1].legend(loc="upper left", fontsize=8)

fig.tight_layout()
out = OUT / "lap1_delta.png"
fig.savefig(out, dpi=150)
plt.close(fig)
print(f"\nграфик: {out}")
