"""
Lap analysis for MoTeC CSV logs recorded in Assetto Corsa Competizione.

What this script does:
    1. reads a raw MoTeC CSV export (200 Hz, quoted header, metadata lines on top);
    2. rebuilds the distance travelled from the speed channel;
    3. slices the session into laps by distance;
    4. saves a lap table, a speed/throttle/brake plot and an aligned delta plot.

Usage:
    python analyze.py --data data.csv --out docs
    python analyze.py --data data.csv --track-length 4318 --no-compare
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # рисуем в файл, без окна — иначе в терминале и на сервере падает
import matplotlib.pyplot as plt


# Длины трасс в метрах. Нужны, чтобы резать сессию на круги по дистанции,
# а не по времени: круг — это участок длиной ровно в трассу, а не «75 секунд».
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
    """Читает CSV MoTeC. Шапка ищется по строке с колонкой Time, а не по номеру строки."""
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    header_index = None
    for i, line in enumerate(raw_lines[:200]):
        first = line.split(",")[0].strip().strip('"')
        if first.lower() == "time":
            header_index = i
            break
    if header_index is None:
        raise ValueError(f"Не нашёл строку заголовка (колонку Time) в {path.name}")

    meta: dict[str, str] = {}
    for line in raw_lines[:header_index]:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[0]:
            meta[parts[0].lower()] = parts[1]

    df = pd.read_csv(
        path,
        skiprows=header_index,
        sep=",",
        on_bad_lines="skip",
        engine="python",
    )

    df.columns = [str(c).replace('"', "").strip() for c in df.columns]
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Time"]).reset_index(drop=True)
    if df.empty:
        raise ValueError(f"После очистки не осталось данных: {path.name}")

    return df, meta


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Считает время от нуля, дистанцию и переводит скорость в км/ч."""
    out = df.copy()
    out["time_s"] = out["Time"] - out["Time"].iloc[0]

    # Пустые ячейки ломают интегрирование: одна NaN делает всю дистанцию NaN.
    for col in ("SPEED", "THROTTLE", "BRAKE"):
        out[col] = out[col].interpolate().ffill().bfill()

    dt = np.diff(out["time_s"].to_numpy(), prepend=out["time_s"].iloc[0])
    out["distance_m"] = np.cumsum(out["SPEED"].to_numpy() * dt)
    out["speed_kmh"] = out["SPEED"] * 3.6
    return out


def find_laps(df: pd.DataFrame, track_length_m: float) -> pd.DataFrame:
    """Режет сессию на отрезки длиной в круг. Остаток в конце отбрасывается."""
    total_distance = float(df["distance_m"].iloc[-1])
    full_laps = int(total_distance // track_length_m)
    if full_laps < 1:
        raise ValueError(
            f"Пройдено {total_distance / 1000:.2f} км — этого мало на один круг "
            f"({track_length_m / 1000:.2f} км). Проверь длину трассы."
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
    """Возвращает сетку дистанции, время и скорость круга — всё на общей сетке."""
    # lap — это строка Series со смешанными типами, поэтому pandas отдаёт индексы
    # как float. Приводим обратно к int, иначе iloc ругается.
    segment = df.iloc[int(lap["start_idx"]) : int(lap["end_idx"]) + 1]

    distance = segment["distance_m"].to_numpy() - segment["distance_m"].iloc[0]
    time = segment["time_s"].to_numpy() - segment["time_s"].iloc[0]
    speed = segment["speed_kmh"].to_numpy()

    # interp требует строго возрастающий x: убираем повторы.
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
    """Ищет сдвиг по дистанции, при котором профили скорости совпадают лучше всего.

    Зачем это нужно. Границы круга считаются по интегрированной дистанции, а она
    копит ошибку: скорость в логе округлена, поэтому 4300 метров набегают не точно.
    Из-за этого второй круг может начинаться на 30 метров раньше первого. Если
    накладывать их как есть, дельта начинает скакать на ±2 секунды в поворотах —
    это не потеря времени, а ошибка синхронизации.
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


def plot_single_lap(df, lap, out_path, meta):
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

    # Тормоз не сглаживаем: ступеньки — это и есть смысл канала.
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


def plot_compare(df, reference, compared, track_length_m, out_path, meta):
    grid, t_ref, v_ref = lap_profiles(df, reference, track_length_m)
    _, t_cmp, v_cmp = lap_profiles(df, compared, track_length_m)

    shift, rms = align_by_speed(grid, v_ref, v_cmp)

    v_cmp_aligned = np.interp(grid + shift, grid, v_cmp, left=np.nan, right=np.nan)
    t_cmp_aligned = np.interp(grid + shift, grid, t_cmp, left=np.nan, right=np.nan)
    delta_raw = t_cmp_aligned - t_ref  # > 0 — сравниваемый круг медленнее

    # После сдвига дельта перестаёт начинаться с нуля: сравниваемые участки
    # стартуют в разных точках трассы. Нормируем её так, чтобы в начале было 0,
    # а в конце — реальная разница времён кругов. Коррекция линейная, поэтому
    # форма кривой (где именно теряется время) не меняется.
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Lap analysis for MoTeC CSV logs")
    parser.add_argument("--data", required=True, type=Path, help="path to the MoTeC CSV file")
    parser.add_argument("--out", default=Path("docs"), type=Path, help="output folder")
    parser.add_argument("--track-length", type=float, default=None, help="track length in metres")
    parser.add_argument("--no-compare", action="store_true", help="skip the delta plot")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"[error] file not found: {args.data}")
        return 1

    print(f"[1/4] reading {args.data.name} ...")
    raw, meta = read_motec_csv(args.data)
    df = prepare(raw)

    venue = meta.get("venue", "").strip().lower()
    track_length = args.track_length or TRACK_LENGTHS_M.get(venue)
    if track_length is None:
        print(f"[error] unknown track '{venue}'. Pass --track-length explicitly.")
        return 1

    duration = float(df["time_s"].iloc[-1])
    distance_km = float(df["distance_m"].iloc[-1]) / 1000
    print(f"      venue={venue or 'unknown'}  track={track_length:.0f} m")
    print(f"      duration={duration:.1f} s  distance={distance_km:.2f} km  samples={len(df)}")

    print("[2/4] slicing laps by distance ...")
    laps = find_laps(df, track_length)
    if laps.empty:
        print("[error] no complete laps found")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    laps.to_csv(args.out / "laps.csv", index=False)

    display = laps[["lap", "lap_time_s", "avg_speed_kmh", "max_speed_kmh", "full_throttle_pct", "braking_pct"]]
    print(display.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    best = laps.loc[laps["lap_time_s"].idxmin()]
    print(f"[3/4] best lap: {int(best['lap'])} - {best['lap_time_s']:.2f} s ({best['avg_speed_kmh']:.1f} km/h avg)")
    plot_single_lap(df, best, args.out / "best_lap.png", meta)

    if not args.no_compare and len(laps) >= 2:
        others = laps[laps["lap"] != best["lap"]]
        compared = others.loc[others["lap_time_s"].idxmin()]
        delta, shift, rms = plot_compare(df, best, compared, track_length, args.out / "delta.png", meta)
        print(f"[4/4] delta vs lap {int(compared['lap'])}: aligned by {shift:+.0f} m (RMS {rms:.1f} km/h)")
        print(f"      worst loss {np.nanmax(delta):+.3f} s, biggest gain {np.nanmin(delta):+.3f} s")
        print(f"      total difference: {compared['lap_time_s'] - best['lap_time_s']:+.3f} s")
    else:
        print("[4/4] comparison skipped")

    print(f"[done] results saved to {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
