"""Project 02, step 1 (v7): corners + locate the lap-1 overtake.

Method for the overtake: for each driver, build the function t(d) — the time at
which he reaches track distance d. The pass is where the two curves cross, i.e.
where one driver starts arriving at each point earlier than the other.
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

# --- повороты по сглаженной траектории ---------------------------------
ref = s.laps.pick_drivers("HAM").pick_fastest()
tel = ref.get_telemetry()
x = tel["X"].to_numpy(dtype=float)
y = tel["Y"].to_numpy(dtype=float)
dist = tel["Distance"].to_numpy(dtype=float)
speed = tel["Speed"].to_numpy(dtype=float)

dx, dy = np.diff(x), np.diff(y)
ds = np.hypot(dx, dy)
ds[ds < 1e-6] = np.nan
theta = np.unwrap(np.arctan2(dy, dx))
kappa = np.nan_to_num(np.diff(theta) / ds[:-1])

step = float(np.nanmedian(ds))
win = max(5, int(40.0 / max(step, 0.1)) | 1)   # шире окно = меньше шума позиции
kappa_s = np.convolve(kappa, np.ones(win) / win, mode="same")

min_gap = max(1, int(60.0 / max(step, 0.1)))
peaks, _ = find_peaks(np.abs(kappa_s), prominence=0.0025, distance=min_gap)
merged = []
for p in peaks:
    if merged and abs(dist[p] - dist[merged[-1]]) < 40.0:
        if abs(kappa_s[p]) > abs(kappa_s[merged[-1]]):
            merged[-1] = p
    else:
        merged.append(p)

print(f"быстрейший круг {ref['LapTime']}   дистанция {dist.max():.0f} м   поворотов {len(merged)}")
print(f"{'#':>3} {'апекс, м':>10} {'скор., км/ч':>12} {'радиус, м':>10}")
for i, p in enumerate(merged, start=1):
    r = 1.0 / abs(kappa_s[p]) if abs(kappa_s[p]) > 1e-6 else float("inf")
    print(f"{i:>3} {dist[p]:>10.0f} {speed[p]:>12.1f} {r:>10.0f}")

# --- обгон: t(d) для двух пилотов --------------------------------------
print()
print("=== Обгон на первом круге ===")
curves = {}
for drv in ("HAM", "VER"):
    lap = s.laps.pick_drivers(drv)
    lap = lap[lap["LapNumber"] == 1].iloc[0]
    t = lap.get_telemetry()
    d = t["Distance"].to_numpy(dtype=float)
    tt = (t["SessionTime"] - t["SessionTime"].iloc[0]).dt.total_seconds().to_numpy()
    keep = np.concatenate([[True], np.diff(d) > 0])
    curves[drv] = (d[keep], tt[keep])
    print(f"{drv}: круг {lap['LapTime']}, старт телеметрии {t['SessionTime'].iloc[0]}, "
          f"дистанция {d[-1]:.0f} м")

GRID_OFFSET = 8.0  # Хэмилтон стартовал на второй позиции, примерно 8 м позади
grid = np.linspace(0, min(curves["HAM"][0].max(), curves["VER"][0].max()) - GRID_OFFSET, 4000)
t_ham = np.interp(grid, curves["HAM"][0], curves["HAM"][1])
t_ver = np.interp(grid + GRID_OFFSET, curves["VER"][0], curves["VER"][1])

delta = t_ham - t_ver          # > 0: Хэмилтон доезжает до этой точки позже
cross = np.where(np.diff(np.sign(delta)) != 0)[0]
print(f"начало: Хэмилтон {'позади' if delta[0] > 0 else 'впереди'} на {abs(delta[0]):.2f} с")
for c in cross:
    print(f"  смена порядка на отметке {grid[c]:.0f} м, разница {delta[c]:+.3f} с")
print(f"конец круга: Хэмилтон {'впереди' if delta[-1] < 0 else 'позади'} на {abs(delta[-1]):.3f} с")

if len(cross):
    c = cross[0]
    print(f"\nвывод: обгон в районе {grid[c]:.0f} м трассы")
