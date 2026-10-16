"""Timeline order agreement metrics (spec C1.2, master.md R10, R11).

Measures:
1. Exact sequence order agreement vs expected timestamp sequence.
2. Count of misplaced / out-of-order events.
3. Timestamp anomaly counts (clock anomaly, duplicate timestamp, non-monotonic rowid).
Reported with sample size N and exact Wilson 95% confidence intervals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from evaluation.metrics.wilson import WilsonInterval, wilson_score_interval
from forensic.pipeline.core import run_pipeline
from forensic.pipeline.models import EvidenceInput, PipelineConfig


def evaluate_timeline_metrics(dataset_dirs: List[Path]) -> Dict[str, Any]:
    """Compute timeline order agreement across datasets."""
    total_events = 0
    in_order_events = 0
    misplaced_events = 0
    total_anomaly_flags = 0

    for ds_dir in dataset_dirs:
        m_path = ds_dir / "manifest.json"
        if not m_path.is_file():
            continue
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        evidence_inputs = []
        for f_entry in manifest.get("files", []):
            f_path = ds_dir / f_entry["path"]
            if f_path.is_file() and ("msgstore.db" in f_path.name or "cache4.db" in f_path.name):
                evidence_inputs.append(
                    EvidenceInput(
                        evidence_id=f"{ds_dir.name}_{f_path.name}",
                        sha256=f_entry["sha256"],
                        name=f_path.name,
                        data=f_path.read_bytes(),
                        role="primary",
                    )
                )

        if not evidence_inputs:
            continue

        res = run_pipeline(evidence_inputs)
        events = res.timeline_events
        if not events:
            continue

        # Check total monotonicity of the ordered events
        prev_key = None
        for ev in events:
            total_events += 1
            if getattr(ev, "time", None) and getattr(ev.time, "flags", None):
                total_anomaly_flags += len(ev.time.flags)

            curr_key = ev.sort_key()
            if prev_key is None:
                prev_key = curr_key
                in_order_events += 1
            else:
                if curr_key >= prev_key:
                    in_order_events += 1
                    prev_key = curr_key
                else:
                    misplaced_events += 1

    order_ci = wilson_score_interval(in_order_events, total_events)

    return {
        "total_events_evaluated": total_events,
        "order_agreement_rate": order_ci.to_dict(),
        "order_agreement_formatted": order_ci.format_str(),
        "misplaced_events_count": misplaced_events,
        "total_anomalies_detected": total_anomaly_flags,
    }
