"""Confidence calibration evaluation (spec C1.3, master.md R1, R8).

Evaluates whether confidence scores function as calibrated probabilities:
- 10 equal-width bins: [0.0, 0.1), [0.1, 0.2), ..., [0.9, 1.0]
- Reliability table: bin, N, mean predicted confidence, observed empirical accuracy
- Expected Calibration Error (ECE) = sum( (N_b / N_total) * |acc_b - conf_b| )
- Maximum Calibration Error (MCE) = max(|acc_b - conf_b|)
- If ECE > tolerance (0.10) or N per bin is too small, explicitly states:
  "scores are heuristic ordering, not calibrated probabilities".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CalibrationBin:
    bin_index: int
    bin_lower: float
    bin_upper: float
    count: int
    mean_predicted: float
    observed_rate: float
    calibration_gap: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bin_index": self.bin_index,
            "range": f"[{self.bin_lower:.1f}, {self.bin_upper:.1f}{']' if self.bin_index == 9 else ')'}",
            "count": self.count,
            "mean_predicted": round(self.mean_predicted, 4),
            "observed_rate": round(self.observed_rate, 4),
            "calibration_gap": round(self.calibration_gap, 4),
        }


@dataclass(frozen=True)
class CalibrationResult:
    bins: List[CalibrationBin]
    total_samples: int
    ece: float
    mce: float
    tolerance: float
    is_calibrated: bool
    status_label: str
    wording_recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "ece": round(self.ece, 4),
            "mce": round(self.mce, 4),
            "tolerance": round(self.tolerance, 4),
            "is_calibrated": self.is_calibrated,
            "status_label": self.status_label,
            "wording_recommendation": self.wording_recommendation,
            "bins": [b.to_dict() for b in self.bins],
        }


def compute_calibration(
    scores_and_labels: List[Tuple[float, bool]],
    num_bins: int = 10,
    tolerance: float = 0.10,
    min_samples_per_bin: int = 5,
) -> CalibrationResult:
    """Compute calibration bins, ECE, MCE, and calibration status.

    Args:
        scores_and_labels: List of (predicted_confidence, ground_truth_bool).
        num_bins: Number of equal width bins (default 10).
        tolerance: Maximum acceptable ECE threshold (default 0.10).
        min_samples_per_bin: Minimum samples required per populated bin to claim calibration.
    """
    total = len(scores_and_labels)
    if total == 0:
        return CalibrationResult(
            bins=[],
            total_samples=0,
            ece=0.0,
            mce=0.0,
            tolerance=tolerance,
            is_calibrated=False,
            status_label="INSUFFICIENT_DATA",
            wording_recommendation="scores are heuristic ordering, not calibrated probabilities",
        )

    bin_data: List[List[Tuple[float, bool]]] = [[] for _ in range(num_bins)]
    for score, label in scores_and_labels:
        # Clamp score to [0.0, 1.0]
        s = max(0.0, min(1.0, float(score)))
        idx = int(s * num_bins)
        if idx >= num_bins:
            idx = num_bins - 1
        bin_data[idx].append((s, bool(label)))

    bins: List[CalibrationBin] = []
    weighted_ece = 0.0
    mce = 0.0
    all_bins_well_sampled = True

    for i in range(num_bins):
        b_low = i / num_bins
        b_high = (i + 1) / num_bins
        items = bin_data[i]
        n_b = len(items)
        if n_b == 0:
            bins.append(
                CalibrationBin(
                    bin_index=i,
                    bin_lower=b_low,
                    bin_upper=b_high,
                    count=0,
                    mean_predicted=0.0,
                    observed_rate=0.0,
                    calibration_gap=0.0,
                )
            )
            continue

        mean_pred = sum(s for s, _ in items) / n_b
        obs_rate = sum(1 for _, l in items if l) / n_b
        gap = abs(obs_rate - mean_pred)
        weighted_ece += (n_b / total) * gap
        if gap > mce:
            mce = gap
        if n_b < min_samples_per_bin:
            all_bins_well_sampled = False

        bins.append(
            CalibrationBin(
                bin_index=i,
                bin_lower=b_low,
                bin_upper=b_high,
                count=n_b,
                mean_predicted=mean_pred,
                observed_rate=obs_rate,
                calibration_gap=gap,
            )
        )

    is_calibrated = (weighted_ece <= tolerance) and all_bins_well_sampled and (total >= 50)
    if is_calibrated:
        status_label = "EMPIRICALLY_CALIBRATED"
        rec = "scores satisfy calibration tolerance on validation dataset"
    else:
        status_label = "HEURISTIC_ORDERING"
        rec = "scores are heuristic ordering, not calibrated probabilities"

    return CalibrationResult(
        bins=bins,
        total_samples=total,
        ece=weighted_ece,
        mce=mce,
        tolerance=tolerance,
        is_calibrated=is_calibrated,
        status_label=status_label,
        wording_recommendation=rec,
    )
