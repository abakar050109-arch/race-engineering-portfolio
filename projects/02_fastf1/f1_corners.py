"""Shared helpers for project 02: track corners from the driven path."""

import numpy as np
from scipy.signal import find_peaks


def corners_of(lap, window_m: float = 40.0, prominence: float = 0.0025, merge_m: float = 40.0):
    """Return the distance along the lap where each corner apex sits.

    Curvature is computed from the X/Y path, smoothed over `window_m` metres and
    then peak-picked. Peaks closer than `merge_m` are merged, keeping the
    strongest one: the hairpin otherwise produces three peaks a few metres apart.
    """
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
    win = max(5, int(window_m / max(step, 0.1)) | 1)
    kappa = np.convolve(kappa, np.ones(win) / win, mode="same")

    min_gap = max(1, int(60.0 / max(step, 0.1)))
    peaks, _ = find_peaks(np.abs(kappa), prominence=prominence, distance=min_gap)

    merged = []
    for p in peaks:
        if merged and abs(d[p] - d[merged[-1]]) < merge_m:
            if abs(kappa[p]) > abs(kappa[merged[-1]]):
                merged[-1] = p
        else:
            merged.append(p)

    return d, np.array(merged), kappa
