"""Project 02, step 3: draw the circuit with numbered corner markers.

Purpose: a visual check. The algorithm numbers corners by distance, but the
official numbering starts where the track map starts — we must confirm they
match before any conclusion mentions "Turn 5".
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
from matplotlib.collections import LineCollection

from f1_corners import corners_of

HERE = Path(__file__).resolve().parent
CACHE = str(HERE / "f1_cache")
OUT = HERE / "docs"
OUT.mkdir(exist_ok=True)

fastf1.Cache.configure(cache_dir=CACHE)

s = fastf1.get_session(2021, "Abu Dhabi", "R")
s.load(telemetry=True, messages=False, weather=False)

ref = s.laps.pick_drivers("HAM").pick_fastest()
tel = ref.get_telemetry()
x = tel["X"].to_numpy(dtype=float)
y = tel["Y"].to_numpy(dtype=float)
v = tel["Speed"].to_numpy(dtype=float)

dist, apex_idx, kappa = corners_of(ref)
# apex_idx indexes the curvature array, which is one sample shorter than the path
rows = np.clip(apex_idx, 0, len(x) - 1)

points = np.column_stack([x, y]).reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)

fig, ax = plt.subplots(figsize=(10, 9))
line = LineCollection(segments, cmap="viridis", linewidth=3.5, alpha=0.9)
line.set_array(v[:-1])
ax.add_collection(line)
ax.autoscale()
ax.set_aspect("equal")

for i, r in enumerate(rows, start=1):
    ax.plot(x[r], y[r], "o", color="white", markeredgecolor="black", markersize=9, zorder=5)
    ax.annotate(str(i), (x[r], y[r]), color="black", fontsize=9, fontweight="bold",
                ha="center", va="center", zorder=6)

ax.plot(x[0], y[0], "s", color="#d62728", markersize=10, zorder=5, label="start / finish")
ax.set_title(f"Abu Dhabi 2021 · HAM fastest lap {ref['LapTime']} · {len(rows)} corners detected")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.grid(alpha=0.2)
ax.legend(loc="upper right")
fig.colorbar(line, ax=ax, label="Speed (km/h)")
fig.tight_layout()

out_file = OUT / "track_map_corners.png"
fig.savefig(out_file, dpi=150)
plt.close(fig)

print(f"поворотов: {len(rows)}")
print(f"карта сохранена: {out_file}")
print()
print(f"{'#':>3} {'апекс, м':>10} {'скор., км/ч':>12}")
for i, p in enumerate(apex_idx, start=1):
    print(f"{i:>3} {float(dist[p]):>10.0f} {float(v[min(p, len(v) - 1)]):>12.1f}")
