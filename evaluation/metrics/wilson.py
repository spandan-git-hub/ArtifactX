"""Wilson score confidence interval calculation for binomial proportions.

Follows master.md R1 (truth over appearance): report Wilson 95% intervals
next to every proportion, state N, and never report bare 100% without N and interval.
"""

from __future__ import annotations

import math
from typing import NamedTuple


class WilsonInterval(NamedTuple):
    proportion: float
    ci_lower: float
    ci_upper: float
    successes: int
    total: int

    def format_str(self) -> str:
        """Format as: '100.0% (N=24, 95% CI [86.2%, 100.0%])'"""
        pct = self.proportion * 100.0
        low = self.ci_lower * 100.0
        high = self.ci_upper * 100.0
        return f"{pct:.1f}% (N={self.total}, 95% CI [{low:.1f}%, {high:.1f}%])"

    def to_dict(self) -> dict[str, float | int]:
        return {
            "proportion": round(self.proportion, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
            "successes": self.successes,
            "total": self.total,
        }


def wilson_score_interval(
    k: int,
    n: int,
    confidence: float = 0.95,
) -> WilsonInterval:
    """Compute the Wilson score confidence interval for binomial proportion k/n.

    Args:
        k: Number of successes (0 <= k <= n).
        n: Total number of trials (n >= 0).
        confidence: Confidence level (default 0.95 -> z ~ 1.95996).

    Returns:
        WilsonInterval with (proportion, ci_lower, ci_upper, successes, total).
    """
    if n <= 0:
        return WilsonInterval(0.0, 0.0, 0.0, k, n)

    k = max(0, min(k, n))
    p = k / n

    # Standard normal quantile z for two-sided confidence
    # For 0.95: z ~ 1.959963984540054
    alpha = 1.0 - confidence
    if abs(confidence - 0.95) < 1e-4:
        z = 1.959963984540054
    elif abs(confidence - 0.99) < 1e-4:
        z = 2.5758293035489004
    elif abs(confidence - 0.90) < 1e-4:
        z = 1.6448536269514722
    else:
        z = math.sqrt(2.0) * _erfinv(1.0 - alpha)

    z2 = z * z
    denom = 1.0 + (z2 / n)
    center = p + (z2 / (2.0 * n))
    margin = z * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * (n * n))))

    ci_lower = max(0.0, (center - margin) / denom)
    ci_upper = min(1.0, (center + margin) / denom)

    return WilsonInterval(
        proportion=p,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        successes=k,
        total=n,
    )


def _erfinv(x: float) -> float:
    """Winitzki approximation of the inverse error function."""
    a = 0.147
    sgn = 1.0 if x >= 0 else -1.0
    x = max(-0.9999999, min(0.9999999, x))
    ln1_x2 = math.log(1.0 - x * x)
    term1 = 2.0 / (math.pi * a) + ln1_x2 / 2.0
    inner = term1 * term1 - ln1_x2 / a
    return sgn * math.sqrt(math.sqrt(inner) - term1)
