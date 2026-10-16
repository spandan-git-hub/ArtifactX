"""Parsing accuracy metrics evaluation (spec C1.2, master.md R1, R7).

Measures:
1. Message accuracy: correct messages / manifest messages on:
   (id, sender, ts_utc_ms, body, type, chat).
2. Per-field accuracy breakdowns (id, sender, timestamp, body, type, chat).
3. List of missing message identifiers (if any).
4. Telegram unparsed blob count and constructor reasons (honest fallback).
All proportion metrics report exact Wilson 95% confidence intervals and sample size N.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from evaluation.matching import match_message_record
from evaluation.metrics.wilson import WilsonInterval, wilson_score_interval
from forensic.telegram.parser import TelegramParser
from forensic.whatsapp.parser import WhatsAppParser


def evaluate_parsing_metrics(dataset_dirs: List[Path]) -> Dict[str, Any]:
    """Compute WhatsApp and Telegram parsing accuracy across datasets."""
    wa_total = 0
    wa_correct = 0
    wa_field_counts = {"id": 0, "sender": 0, "timestamp": 0, "body": 0, "type": 0, "chat": 0}
    wa_misses: List[str] = []

    tg_total = 0
    tg_correct = 0
    tg_field_counts = {"id": 0, "sender": 0, "timestamp": 0, "body": 0, "type": 0, "chat": 0}
    tg_misses: List[str] = []
    tg_unparsed_count = 0
    tg_unparsed_reasons: Dict[str, int] = {}

    for ds_dir in dataset_dirs:
        m_path = ds_dir / "manifest.json"
        if not m_path.is_file():
            continue
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # 1. WhatsApp evaluation
        if manifest.get("whatsapp") and (ds_dir / "msgstore.db").is_file():
            wa_manifest_msgs = (manifest.get("whatsapp") or {}).get("messages", [])
            wa_db_path = ds_dir / "wa.db" if (ds_dir / "wa.db").is_file() else None
            parser = WhatsAppParser(
                msgstore_source=(ds_dir / "msgstore.db"),
                evidence_id=f"{ds_dir.name}_wa",
                wa_db_source=wa_db_path,
            )
            res = parser.parse()
            parsed_by_key = {m.key_id: m for m in res.messages}

            for exp_m in wa_manifest_msgs:
                wa_total += 1
                k_id = exp_m.get("key_id")
                parsed_m = parsed_by_key.get(k_id)
                if not parsed_m:
                    wa_misses.append(f"{ds_dir.name}:{k_id}")
                    continue

                matches = match_message_record(parsed_m, exp_m, is_whatsapp=True)
                for f_name, is_match in matches.items():
                    if f_name != "all_match" and is_match:
                        wa_field_counts[f_name] += 1
                if matches.get("all_match"):
                    wa_correct += 1

        # 2. Telegram evaluation
        if manifest.get("telegram") and (ds_dir / "cache4.db").is_file():
            tg_manifest_msgs = (manifest.get("telegram") or {}).get("messages", [])
            wal_bytes = (ds_dir / "cache4.db-wal").read_bytes() if (ds_dir / "cache4.db-wal").is_file() else None
            parser = TelegramParser(
                db_source=(ds_dir / "cache4.db").read_bytes(),
                wal_source=wal_bytes,
                evidence_id=f"{ds_dir.name}_tg",
            )
            res = parser.parse()
            parsed_by_mid = {m.mid: m for m in res.messages}

            for exp_m in tg_manifest_msgs:
                tg_total += 1
                mid = exp_m.get("mid")
                parsed_m = parsed_by_mid.get(mid)
                if not parsed_m:
                    tg_misses.append(f"{ds_dir.name}:{mid}")
                    continue

                matches = match_message_record(parsed_m, exp_m, is_whatsapp=False)
                for f_name, is_match in matches.items():
                    if f_name != "all_match" and is_match:
                        tg_field_counts[f_name] += 1
                if matches.get("all_match"):
                    tg_correct += 1

            # Count unparsed blobs
            for unparsed in res.unparsed_blobs:
                tg_unparsed_count += 1
                reason = unparsed.reason or "UNKNOWN_CONSTRUCTOR"
                tg_unparsed_reasons[reason] = tg_unparsed_reasons.get(reason, 0) + 1

    wa_acc_ci = wilson_score_interval(wa_correct, wa_total)
    tg_acc_ci = wilson_score_interval(tg_correct, tg_total)
    overall_total = wa_total + tg_total
    overall_correct = wa_correct + tg_correct
    overall_acc_ci = wilson_score_interval(overall_correct, overall_total)

    # Field-level CIs
    wa_field_cis = {
        field: wilson_score_interval(count, wa_total).to_dict()
        for field, count in wa_field_counts.items()
    }
    tg_field_cis = {
        field: wilson_score_interval(count, tg_total).to_dict()
        for field, count in tg_field_counts.items()
    }

    return {
        "overall_accuracy": overall_acc_ci.to_dict(),
        "overall_accuracy_formatted": overall_acc_ci.format_str(),
        "whatsapp": {
            "accuracy": wa_acc_ci.to_dict(),
            "accuracy_formatted": wa_acc_ci.format_str(),
            "field_accuracies": wa_field_cis,
            "miss_count": len(wa_misses),
            "misses": wa_misses[:10],
        },
        "telegram": {
            "accuracy": tg_acc_ci.to_dict(),
            "accuracy_formatted": tg_acc_ci.format_str(),
            "field_accuracies": tg_field_cis,
            "miss_count": len(tg_misses),
            "misses": tg_misses[:10],
            "unparsed_count": tg_unparsed_count,
            "unparsed_reasons": tg_unparsed_reasons,
        },
    }
