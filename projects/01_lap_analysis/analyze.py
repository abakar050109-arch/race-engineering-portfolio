"""
Lap analysis for MoTeC CSV logs recorded in Assetto Corsa Competizione.

Pipeline
--------
1. Read a MoTeC CSV export (200 Hz, quoted header, metadata block on top).
2. Rebuild the distance travelled from the speed channel.
3. Slice the session into laps by distance, not by time.
4. Write a lap table, a speed/throttle/brake plot and an aligned delta plot.

Usage
-----
    python analyze.py                          # every CSV in ./data
    python analyze.py --data a.csv b.csv       # explicit files
    python analyze.py --data logs/             # every CSV in a folder
    python analyze.py --track-length 4318      # override track length

Output goes to ./docs/<venue>/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # write figures to files; no display required
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


# Track lengths in metres. Required because a lap is a distance, not a duration:
# without a length there is no way to tell where one lap ends and the next begins.
TRACK_LENGTHS_M = {
    "red_bull_ring": 4318.0,
    "silverstone": 5891.0,
    "monza": 5793.0,
    "spa": 7004.0,
    "nurburgring": 5148.0,
    "zandvoort": 4252.0,
    "misano": 4226.0,
    "barcelona": 4657.0,
    "hungaroring": 4381.0,
    "imola": 4909.0,
    "paul_ricard": 5842.0,
    "suzuka": 5807.0,
    "cota": 5513.0,
    "mount_panorama": 6193.0,
    "laguna_seca": 3602.0,
    "brands_hatch": 3908.0,
    "donington": 3143.0,
    "oulton_park": 4333.0,
    "kyalami": 4522.0,
    "watkins_glen": 5552.0,
}


def read_motec_csv(path: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """Read a MoTeC CSV.

    The header row is located by content (the row whose first field is ``Time``)
    rather than by a hardcoded line number, so a different export layout does not
    silently shift every column.
    """
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    header_index = None
    for i, line in enumerate(raw_lines[:200]):
        first = line.split(",")[0].strip().strip('"')
        if first.lower() == "time":
            header_index = i
            break
    if header_index is None:
        raise ValueError("no header row found (no 'Time' column)")

    meta: dict[str, str] = {}
    for line in raw_lines[:header_index]:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[0]:
            meta[parts[0].lower()] = parts[1]

    df = pd.read_csv(path, skiprows=header_index, sep=",", on_bad_lines="skip", engine="python")

    df.columns = [str(c).replace('"', "").strip() for c in df.columns]
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Time"]).reset_index(drop=True)
    if df.empty:
        raise ValueError("no usable rows after cleaning")

    return df, meta


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Add relative time, distance and km/h speed."""
    out = df.copy()
    out["time_s"] = out["Time"] - out["Time"].iloc[0]

    # A single empty cell would turn the whole cumulative distance into NaN,
    # so the three channels used downstream are repaired first.
    for col in ("SPEED", "THROTTLE", "BRAKE"):
        out[col] = out[col].interpolate().ffill().bfill()

    dt = np.diff(out["time_s"].to_numpy(), prepend=out["time_s"].iloc[0])
    out["distance_m"] = np.cumsum(out["SPEED"].to_numpy() * dt)
    out["speed_kmh"] = out["SPEED"] * 3.6
    return out


def find_laps(df: pd.DataFrame, track_length_m: float) -> pd.DataFrame:
    """Split the session into segments of exactly one track length.

    Any trailing partial segment is dropped.
    """
    total_distance = float(df["distance_m"].iloc[-1])
    full_laps = int(total_distance // track_length_m)
    if full_laps < 1:
        raise ValueError(
            f"only {total_distance / 1000:.2f} km driven - not enough for one lap "
            f"({track_length_m / 1000:.2f} km); check --track-length"
        )

    bounds = [
        np.searchsorted(df["distance_m"].to_numpy(), k * track_length_m)
        for k in range(1, full_laps + 1)
    ]

    laps = []
    start = 0
    for number, end in enumerate(bounds, start=1):
        segment = df.iloc[start:end]
        if len(segment) < 10:
            start = int(end)
            continue
        lap_time = float(segment["time_s"].iloc[-1] - segment["time_s"].iloc[0])
        laps.append(
            {
                "lap": number,
                "start_s": float(segment["time_s"].iloc[0]),
                "lap_time_s": lap_time,
                "avg_speed_kmh": track_length_m / lap_time * 3.6 if lap_time > 0 else np.nan,
                "max_speed_kmh": float(segment["speed_kmh"].max()),
                "full_throttle_pct": float((segment["THROTTLE"] > 95).mean() * 100),
                "braking_pct": float((segment["BRAKE"] > 5).mean() * 100),
                "start_idx": int(segment.index[0]),
                "end_idx": int(segment.index[-1]),
            }
        )
        start = int(end)

    return pd.DataFrame(laps)


def lap_profiles(
    df: pd.DataFrame, lap: pd.Series, track_length_m: float, n: int = 2000
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return distance grid, elapsed time and speed for one lap, on a common grid."""
    # A row of a mixed-dtype Series comes back with float indices; iloc needs ints.
    segment = df.iloc[int(lap["start_idx"]) : int(lap["end_idx"]) + 1]

    distance = segment["distance_m"].to_numpy() - segment["distance_m"].iloc[0]
    time = segment["time_s"].to_numpy() - segment["time_s"].iloc[0]
    speed = segment["speed_kmh"].to_numpy()

    # np.interp requires strictly increasing x, so duplicated distances are dropped.
    unique = np.concatenate([[True], np.diff(distance) > 0])
    distance, time, speed = distance[unique], time[unique], speed[unique]

    grid = np.linspace(0.0, min(track_length_m, float(distance[-1])), n)
    return grid, np.interp(grid, distance, time), np.interp(grid, distance, speed)


def align_by_speed(
    grid: np.ndarray,
    speed_ref: np.ndarray,
    speed_cmp: np.ndarray,
    max_shift_m: float = 250.0,
    step_m: float = 2.0,
) -> tuple[float, float]:
    """Find the distance shift that best matches two speed profiles.

    Why this is needed: lap boundaries come from integrated distance, and that
    integral drifts because the speed channel is rounded. After a few laps, "lap 5"
    starts tens of metres away from "lap 4". Comparing the raw traces then compares
    different parts of the track, and the delta oscillates by seconds instead of
    showing real time loss.

    The search is a plain sweep: try every shift, keep the one with the lowest RMS
    difference between the two speed profiles.
    """
    best_shift, best_error = 0.0, float("inf")
    for shift in np.arange(-max_shift_m, max_shift_m + step_m, step_m):
        shifted = np.interp(grid + shift, grid, speed_cmp, left=np.nan, right=np.nan)
        valid = ~np.isnan(shifted)
        if valid.sum() < 0.5 * len(grid):
            continue
        error = float(np.sqrt(np.mean((speed_ref[valid] - shifted[valid]) ** 2)))
        if error < best_error:
            best_shift, best_error = float(shift), error
    return best_shift, best_error


def reconstruct_track(
    df: pd.DataFrame, lap: pd.Series, g_to_ms2: float = 9.81
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Rebuild the circuit outline from lateral acceleration.

    The log has no GPS and no X/Y position, so the geometry has to be derived.
    Curvature follows from the lateral acceleration: ``kappa = a_lat / v^2``.
    Integrating curvature over distance gives the heading; integrating heading
    gives x and y.

    The result drifts, so the loop is closed in two steps: the heading is scaled
    to exactly one full turn, and the remaining position gap is spread evenly
    over the lap. The shape is representative, not survey-accurate.
    """
    segment = df.iloc[int(lap["start_idx"]) : int(lap["end_idx"]) + 1]
    if "G_LAT" not in segment.columns:
        raise ValueError("channel G_LAT is missing - cannot rebuild the track")

    v = segment["SPEED"].to_numpy()
    dt = np.diff(segment["time_s"].to_numpy(), prepend=segment["time_s"].iloc[0])
    ds = v * dt
    a_lat = segment["G_LAT"].to_numpy()

    # G_LAT comes in g, not m/s^2. Clipping removes kerb strikes and glitches.
    kappa = np.clip(a_lat * g_to_ms2 / np.maximum(v, 5.0) ** 2, -0.25, 0.25)
    dtheta = kappa * ds

    total = float(dtheta.sum())
    if abs(total) < 1e-6:
        raise ValueError("no net rotation detected - check the G_LAT sign")
    dtheta *= (2.0 * np.pi * np.sign(total)) / total

    theta = np.cumsum(dtheta)
    x = np.cumsum(np.cos(theta) * ds)
    y = np.cumsum(np.sin(theta) * ds)

    # How far apart the two ends are before correction: a quality indicator.
    gap_m = float(np.hypot(x[-1], y[-1]))

    # Spread the residual gap over the lap so the outline closes.
    x -= np.linspace(0.0, x[-1], len(x))
    y -= np.linspace(0.0, y[-1], len(y))
    return x, y, v * 3.6, gap_m


def plot_track_map(
    df: pd.DataFrame, lap: pd.Series, out_path: Path, meta: dict[str, str]
) -> None:
    x, y, speed, gap_m = reconstruct_track(df, lap)

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    line = LineCollection(segments, cmap="viridis", linewidth=3)
    line.set_array(speed[:-1])
    ax.add_collection(line)
    ax.autoscale()
    ax.set_aspect("equal")

    ax.plot(x[0], y[0], "o", color="#d62728", markersize=9, label="start / finish")
    fig.colorbar(line, ax=ax, label="Speed (km/h)")

    ax.set_title(
        f"{meta.get('venue', 'unknown track')} · lap {int(lap['lap'])} · "
        f"track rebuilt from G_LAT (closure gap {gap_m:.0f} m)"
    )
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_single_lap(df: pd.DataFrame, lap: pd.Series, out_path: Path, meta: dict[str, str]) -> None:
    segment = df.iloc[int(lap["start_idx"]) : int(lap["end_idx"]) + 1]
    distance = segment["distance_m"].to_numpy() - segment["distance_m"].iloc[0]

    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)

    axes[0].plot(distance, segment["speed_kmh"], color="#1f77b4", linewidth=1.6, label="Speed")
    axes[0].set_ylabel("Speed (km/h)")
    axes[0].set_title(
        f"{meta.get('venue', 'unknown track')} · lap {int(lap['lap'])} · "
        f"{lap['lap_time_s']:.2f} s · avg {lap['avg_speed_kmh']:.1f} km/h"
    )
    axes[0].grid(alpha=0.3)
    axes[0].legend(loc="upper right")

    # Brake is drawn raw: the steps are the signal, not noise.
    axes[1].fill_between(distance, 0, segment["BRAKE"], color="#d62728", alpha=0.45, label="Brake (%)")
    axes[1].plot(distance, segment["THROTTLE"], color="#2ca02c", linewidth=1.2, label="Throttle (%)")
    axes[1].set_ylabel("Pedal (%)")
    axes[1].set_xlabel("Distance (m)")
    axes[1].set_ylim(-2, 105)
    axes[1].grid(alpha=0.3)
    axes[1].legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_compare(
    df: pd.DataFrame,
    reference: pd.Series,
    compared: pd.Series,
    track_length_m: float,
    out_path: Path,
    meta: dict[str, str],
) -> tuple[np.ndarray, float, float]:
    grid, t_ref, v_ref = lap_profiles(df, reference, track_length_m)
    _, t_cmp, v_cmp = lap_profiles(df, compared, track_length_m)

    shift, rms = align_by_speed(grid, v_ref, v_cmp)

    v_cmp_aligned = np.interp(grid + shift, grid, v_cmp, left=np.nan, right=np.nan)
    t_cmp_aligned = np.interp(grid + shift, grid, t_cmp, left=np.nan, right=np.nan)
    delta_raw = t_cmp_aligned - t_ref  # > 0 means the compared lap is slower

    # After shifting, the delta no longer starts at zero, because the compared
    # segments begin at different points on the track. Normalise it so it starts at
    # 0 and ends at the real lap difference. The correction is linear, so the shape
    # of the curve - where time is actually lost - is preserved.
    total_diff = float(compared["lap_time_s"] - reference["lap_time_s"])
    valid_idx = np.flatnonzero(~np.isnan(delta_raw))
    i0, i1 = int(valid_idx[0]), int(valid_idx[-1])
    span = grid[i1] - grid[i0]
    if span > 0:
        slope = (total_diff - (delta_raw[i1] - delta_raw[i0])) / span
        offset = -delta_raw[i0] - slope * grid[i0]
        delta = delta_raw + offset + slope * grid
    else:
        delta = delta_raw

    fig, axes = plt.subplots(
        3, 1, figsize=(13, 10), sharex=True, gridspec_kw={"height_ratios": [2, 2, 1.4]}
    )

    axes[0].plot(grid, v_ref, linewidth=1.5,
                 label=f"lap {int(reference['lap'])} · {reference['lap_time_s']:.2f} s")
    axes[0].plot(grid, v_cmp_aligned, linewidth=1.3, linestyle="dashed",
                 label=f"lap {int(compared['lap'])} · {compared['lap_time_s']:.2f} s (aligned)")
    axes[0].set_ylabel("Speed (km/h)")
    axes[0].set_title(
        f"{meta.get('venue', 'unknown track')} · best lap vs comparison "
        f"· aligned by {shift:+.0f} m (RMS {rms:.1f} km/h)"
    )
    axes[0].grid(alpha=0.3)
    axes[0].legend(loc="upper right")

    for lap, style in ((reference, "solid"), (compared, "dashed")):
        segment = df.iloc[int(lap["start_idx"]) : int(lap["end_idx"]) + 1]
        distance = segment["distance_m"].to_numpy() - segment["distance_m"].iloc[0]
        axes[1].plot(distance, segment["THROTTLE"], linestyle=style, linewidth=1.0,
                     color="#2ca02c", label=f"lap {int(lap['lap'])} throttle")
    axes[1].set_ylabel("Throttle (%)")
    axes[1].grid(alpha=0.3)
    axes[1].legend(loc="upper right", fontsize=8)

    axes[2].axhline(0, color="black", linewidth=0.8)
    axes[2].fill_between(grid, 0, delta, where=delta > 0, color="#d62728", alpha=0.5, label="losing time")
    axes[2].fill_between(grid, 0, delta, where=delta < 0, color="#2ca02c", alpha=0.5, label="gaining time")
    axes[2].set_ylabel("Delta (s)")
    axes[2].set_xlabel("Distance (m)")
    axes[2].grid(alpha=0.3)
    axes[2].legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return delta, shift, rms


def analyze_file(path: Path, out_root: Path) -> dict:
    """Analyse one log and return a one-row summary."""
    raw, meta = read_motec_csv(path)
    df = prepare(raw)

    venue = meta.get("venue", "").strip().lower()
    track_length = TRACK_LENGTHS_M.get(venue)
    if track_length is None:
        raise ValueError(f"unknown track '{venue}' - add it to TRACK_LENGTHS_M or pass --track-length")

    print(f"  track:  {venue} ({track_length:.0f} m)")
    print(f"  length: {df['time_s'].iloc[-1]:.1f} s   distance: {df['distance_m'].iloc[-1] / 1000:.2f} km"
          f"   samples: {len(df)}")

    laps = find_laps(df, track_length)
    if laps.empty:
        raise ValueError("no complete laps found")

    out_dir = out_root / (venue or path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    laps.to_csv(out_dir / "laps.csv", index=False)

    display = laps[["lap", "lap_time_s", "avg_speed_kmh", "max_speed_kmh", "full_throttle_pct", "braking_pct"]]
    print(display.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    best = laps.loc[laps["lap_time_s"].idxmin()]
    print(f"  best lap: {int(best['lap'])} - {best['lap_time_s']:.2f} s")
    plot_single_lap(df, best, out_dir / "best_lap.png", meta)

    try:
        plot_track_map(df, best, out_dir / "track_map.png", meta)
        print("  track map: track_map.png")
    except Exception as exc:  # noqa: BLE001 - the map is optional
        print(f"  track map skipped: {exc}")

    summary = {
        "file": path.name,
        "venue": venue,
        "laps": len(laps),
        "best_lap_s": float(best["lap_time_s"]),
        "best_lap_number": int(best["lap"]),
    }

    if len(laps) >= 2:
        others = laps[laps["lap"] != best["lap"]]
        compared = others.loc[others["lap_time_s"].idxmin()]
        delta, shift, rms = plot_compare(df, best, compared, track_length, out_dir / "delta.png", meta)
        print(f"  delta vs lap {int(compared['lap'])}: shifted {shift:+.0f} m (RMS {rms:.1f} km/h)")
        print(f"  worst loss {np.nanmax(delta):+.3f} s, biggest gain {np.nanmin(delta):+.3f} s")
        summary["delta_vs_lap"] = int(compared["lap"])
        summary["total_diff_s"] = float(compared["lap_time_s"] - best["lap_time_s"])

    print(f"  saved: {out_dir}")
    return summary


def collect_inputs(values: list[str] | None, script_dir: Path) -> list[Path]:
    """Expand CLI values (files or folders) into a list of CSV files.

    With no arguments, every CSV in ./data next to this script is used.
    """
    if not values:
        data_dir = script_dir / "data"
        return sorted(data_dir.glob("*.csv")) if data_dir.is_dir() else []

    files: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            files.extend(sorted(path.glob("*.csv")))
        else:
            files.append(path)
    return files


def main() -> int:
    # The Windows console is not UTF-8 by default and would raise
    # UnicodeEncodeError on the first non-ASCII character printed.
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Lap analysis for MoTeC CSV logs (ACC)")
    parser.add_argument("--data", nargs="*", default=None,
                        help="CSV files or folders; default: every CSV in ./data")
    parser.add_argument("--out", default=None, help="output folder; default: ./docs")
    parser.add_argument("--track-length", type=float, default=None,
                        help="track length in metres, overrides the venue lookup")
    parser.add_argument("--no-compare", action="store_true", help="skip the delta plot")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    out_root = Path(args.out) if args.out else script_dir / "docs"

    files = collect_inputs(args.data, script_dir)
    existing = [f for f in files if f.exists()]

    if not existing:
        print("No CSV files found.")
        print("Put MoTeC exports into ./data next to this script, or pass paths explicitly:")
        print("    python analyze.py --data path/to/log.csv")
        return 1
    for f in files:
        if not f.exists():
            print(f"[skip] not found: {f}")

    summaries = []
    for i, path in enumerate(existing, start=1):
        print(f"\n[{i}/{len(existing)}] {path.name}")
        try:
            summaries.append(analyze_file(path, out_root))
        except Exception as exc:  # noqa: BLE001 - one broken log should not stop the batch
            print(f"  [error] {exc}")

    if len(summaries) > 1:
        print("\n=== SUMMARY ===")
        header = f"{'file':<14} {'track':<16} {'laps':>6} {'best':>9} {'lap #':>6}"
        print(header)
        print("-" * len(header))
        for s in summaries:
            print(f"{s['file']:<14} {s['venue']:<16} {s['laps']:>6} {s['best_lap_s']:>9.2f} {s['best_lap_number']:>6}")

    print(f"\nDone. Results in: {out_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
