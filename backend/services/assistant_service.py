"""Forensic AI Assistant and Chat Sentiment Analysis Service.

Provides NLP keyword-based sentiment classification, intention marker detection,
suspicion confidence scoring, and natural language query assistance for forensic investigators.

NOTE (LEGAL ISOLATION):
This service is strictly for internal investigative assistance. All outputs are
flagged as non-court admissible and MUST be excluded from judicial court reports.
"""

import re
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.models import (
    Case,
    Evidence,
    EvidenceFile,
    WhatsAppMessage,
    TelegramMessage,
    DeletedMessage,
)

# Forensic Tone Dictionaries & Weighted Keywords
SENTIMENT_KEYWORDS: Dict[str, List[Tuple[str, float]]] = {
    "Aggressive": [
        (r"\bkill\b", 1.0),
        (r"\bdestroy\b", 0.9),
        (r"\bbreak\s+your\b", 0.95),
        (r"\bhurt\b", 0.85),
        (r"\bdead\b", 0.8),
        (r"\bregret\b", 0.75),
        (r"\bpay\s+or\s+else\b", 1.0),
        (r"\bwatch\s+your\s+back\b", 0.95),
        (r"\bpunch\b", 0.7),
        (r"\battack\b", 0.8),
        (r"\bshoot\b", 0.95),
        (r"\bgun\b", 0.8),
        (r"\bweapon\b", 0.85),
        (r"\bwreck\b", 0.75),
        (r"\bthreat\w*\b", 0.85),
        (r"\bfuck\w*\b", 0.6),
        (r"\bshut\s+up\b", 0.65),
    ],
    "Suspicious": [
        (r"\bburner\b", 0.9),
        (r"\bdrop\s*off\b", 0.85),
        (r"\bpackage\b", 0.6),
        (r"\bstash\b", 0.85),
        (r"\bsafe\s*house\b", 0.95),
        (r"\bsecret\b", 0.65),
        (r"\bdon'?t\s+tell\b", 0.8),
        (r"\bcode\s*word\b", 0.85),
        (r"\bmeet\s+me\s+alone\b", 0.85),
        (r"\bcovert\b", 0.9),
        (r"\bclean\s+the\s+trail\b", 0.95),
        (r"\bwire\b", 0.65),
        (r"\boffline\b", 0.6),
        (r"\balibi\b", 0.85),
        (r"\bsmuggling\b", 0.95),
        (r"\bcontraband\b", 0.95),
        (r"\bdeal\b", 0.5),
        (r"\bcached?\b", 0.5),
    ],
    "Deceptive": [
        (r"\bswear\s+to\s+god\b", 0.75),
        (r"\bhonest(?:ly)?\b", 0.55),
        (r"\btrust\s+me\b", 0.6),
        (r"\bwasn'?t\s+me\b", 0.85),
        (r"\bhad\s+nothing\s+to\s+do\b", 0.9),
        (r"\btold\s+the\s+cops\b", 0.85),
        (r"\bpretend\b", 0.8),
        (r"\bcover\s*story\b", 0.95),
        (r"\bact\s+like\b", 0.75),
        (r"\bmake\s+up\b", 0.7),
        (r"\bdeny\b", 0.75),
        (r"\bfake\b", 0.7),
        (r"\blie\b", 0.7),
        (r"\blying\b", 0.7),
    ],
    "Urgent": [
        (r"\bhurry\b", 0.8),
        (r"\basap\b", 0.85),
        (r"\bright\s+now\b", 0.85),
        (r"\bimmediately\b", 0.9),
        (r"\bemergency\b", 0.95),
        (r"\bclock\s+is\s+ticking\b", 0.9),
        (r"\bfast\b", 0.6),
        (r"\bquick(?:ly)?\b", 0.65),
        (r"\brun\b", 0.75),
        (r"\bbefore\s+they\b", 0.85),
        (r"\bout\s+of\s+time\b", 0.9),
        (r"\bdeadline\b", 0.75),
        (r"\bpanic\b", 0.8),
    ],
    "Evasive": [
        (r"\bnot\s+on\s+(?:text|phone|whatsapp)\b", 0.95),
        (r"\bcall\s+me\s+(?:signal|telegram|audio)\b", 0.9),
        (r"\bnot\s+here\b", 0.75),
        (r"\bdelete\s+this\b", 0.95),
        (r"\bface\s+to\s+face\s+only\b", 0.9),
        (r"\bdon'?t\s+type\b", 0.95),
        (r"\btalk\s+later\b", 0.6),
        (r"\bcan'?t\s+say\s+here\b", 0.95),
        (r"\bkeep\s+it\s+quiet\b", 0.85),
        (r"\bswitch\s+to\b", 0.8),
        (r"\bshhh?\b", 0.7),
        (r"\bdon'?t\s+mention\b", 0.85),
    ],
}

INTENTION_PATTERNS: Dict[str, List[str]] = {
    "financial_demand": [
        r"\b(?:wire|transfer|payment|crypto|bitcoin|btc|usdt|monero|xmr)\b",
        r"\b(?:ransom|funds|cash|dollars|euros|inr|rupees)\b",
        r"\b(?:bank\s+account|routing|iban|wallet\s+address)\b",
        r"\b(?:pay\s+up|pay\s+me|send\s+the\s+money|where\s+is\s+the\s+money)\b",
        r"[\$€£₹]\s*\d+[\d,]*",
        r"\b\d+[\d,]*\s*(?:k|thousand|hundred|grand|bucks|usd)\b",
    ],
    "coercion": [
        r"\bor\s+else\b",
        r"\bconsequences\b",
        r"\bexpose\s+you\b",
        r"\bleak\s+your\b",
        r"\bruin\s+you\b",
        r"\bcall\s+the\s+(?:police|cops|feds)\b",
        r"\bblackmail\b",
        r"\bdo\s+as\s+i\s+say\b",
        r"\byou\s+have\s+no\s+choice\b",
        r"\bi\s+know\s+where\s+you\s+live\b",
        r"\byour\s+family\b",
    ],
    "deletion_awareness": [
        r"\bdelete\s*(?:this|chat|messages?|history)\b",
        r"\bclear\s+chat\b",
        r"\bdisappearing\s+messages?\b",
        r"\berase\s*(?:everything|evidence|all)\b",
        r"\bwipe\s+(?:the\s+phone|it)\b",
        r"\bburn\s+(?:this|the\s+sim)\b",
        r"\bauto[- ]delete\b",
        r"\bleave\s+no\s+trace\b",
        r"\btrash\s+the\s+phone\b",
    ],
    "covert_communication": [
        r"\b(?:signal|telegram\s+secret|session|wickr|threema)\b",
        r"\b(?:burner\s+phone|sim\s+card|code\s*name)\b",
        r"\b(?:in\s+person|face\s+to\s+face|meet\s+at)\b",
        r"\b(?:destroy\s+device|throw\s+away\s+sim)\b",
    ],
}


class AssistantService:
    """Forensic AI Assistant and Sentiment Classification Service."""

    @staticmethod
    def classify_message(
        text: str,
        deletion_proximity: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Classify message emotional tone, extract intention markers, and compute suspicion score.
        """
        if not text:
            return {
                "tone": "Neutral",
                "tone_scores": {"Neutral": 1.0},
                "suspicion_score": 0,
                "confidence_level": "Low",
                "intentions": [],
                "highlights": [],
            }

        cleaned_text = text.strip()
        lower_text = cleaned_text.lower()

        scores: Dict[str, float] = {
            "Aggressive": 0.0,
            "Suspicious": 0.0,
            "Deceptive": 0.0,
            "Urgent": 0.0,
            "Evasive": 0.0,
        }
        highlights = []

        # 1. Match Sentiment Keywords
        for category, patterns in SENTIMENT_KEYWORDS.items():
            for pattern, weight in patterns:
                matches = list(re.finditer(pattern, lower_text, re.IGNORECASE))
                if matches:
                    scores[category] += weight * len(matches)
                    for m in matches:
                        match_word = cleaned_text[m.start():m.end()]
                        if match_word not in highlights:
                            highlights.append(match_word)

        # 2. Match Intention Markers
        intentions = []
        for intention_type, patterns in INTENTION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower_text, re.IGNORECASE):
                    if intention_type not in intentions:
                        intentions.append(intention_type)
                    # Add intention matches to highlights
                    for m in re.finditer(pat, lower_text, re.IGNORECASE):
                        snippet = cleaned_text[m.start():m.end()]
                        if snippet not in highlights:
                            highlights.append(snippet)
                    break

        # 3. Determine Dominant Tone
        max_category = max(scores, key=scores.get)
        max_score = scores[max_category]

        if max_score < 0.4:
            tone = "Neutral"
        else:
            tone = max_category

        # 4. Calculate Normalized Suspicion Score (0 - 100)
        # Base from sentiment weights
        sentiment_component = min(
            (scores["Suspicious"] * 28)
            + (scores["Aggressive"] * 32)
            + (scores["Deceptive"] * 24)
            + (scores["Evasive"] * 22)
            + (scores["Urgent"] * 14),
            65.0,
        )

        # Intention marker boost
        intention_component = min(len(intentions) * 15.0, 30.0)

        # Proximity to forensic deletion gaps boost
        deletion_component = min(deletion_proximity * 15.0, 15.0)

        # Exclamation / uppercase urgency cue
        caps_count = sum(1 for c in cleaned_text if c.isupper())
        caps_ratio = caps_count / max(len(cleaned_text), 1)
        urgency_cue = 8.0 if caps_ratio > 0.4 and len(cleaned_text) > 8 else 0.0

        raw_suspicion = sentiment_component + intention_component + deletion_component + urgency_cue
        # Clamp to 0-100
        suspicion_score = int(min(max(raw_suspicion, 0), 100))

        # Confidence Level
        if suspicion_score >= 70:
            confidence_level = "High"
        elif suspicion_score >= 40:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

        # Normalized tone scores for radar/breakdown
        total_raw = sum(scores.values())
        if total_raw > 0:
            norm_scores = {k: round(v / total_raw, 2) for k, v in scores.items()}
        else:
            norm_scores = {k: 0.0 for k in scores}
            norm_scores["Neutral"] = 1.0

        return {
            "tone": tone,
            "tone_scores": norm_scores,
            "suspicion_score": suspicion_score,
            "confidence_level": confidence_level,
            "intentions": intentions,
            "highlights": highlights[:8],
        }

    @classmethod
    def analyze_case_sentiment(
        cls,
        db: Session,
        case_id: int,
        jid: Optional[str] = None,
        message_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze sentiment, tones, and intentions for messages in a case or thread.
        """
        evidence_ids = [ev.id for ev in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()]
        if not evidence_ids:
            return {
                "messages": {},
                "aggregate": {
                    "total_analyzed": 0,
                    "average_suspicion_score": 0,
                    "highest_suspicion_score": 0,
                    "tone_distribution": {},
                    "intention_counts": {},
                    "high_risk_message_count": 0,
                },
                "disclaimer": "Internal Investigative Aid Only — Excluded from Legal Court Reports",
            }

        # Check deletion count for thread/case
        deletion_count = db.query(DeletedMessage).filter(DeletedMessage.case_id == case_id).count()
        deletion_proximity = min(deletion_count / 10.0, 1.0)

        results: Dict[str, Any] = {}
        tone_counts: Dict[str, int] = {
            "Aggressive": 0,
            "Suspicious": 0,
            "Deceptive": 0,
            "Urgent": 0,
            "Evasive": 0,
            "Neutral": 0,
        }
        intention_counts: Dict[str, int] = {
            "financial_demand": 0,
            "coercion": 0,
            "deletion_awareness": 0,
            "covert_communication": 0,
        }
        suspicion_scores: List[int] = []

        # 1. Fetch WhatsApp messages
        wa_query = db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id.in_(evidence_ids))
        if jid:
            wa_query = wa_query.filter(WhatsAppMessage.key_remote_jid == jid)
        if message_ids:
            wa_msg_int_ids = [int(m.replace("wa_", "")) for m in message_ids if m.startswith("wa_") and m.replace("wa_", "").isdigit()]
            if wa_msg_int_ids:
                wa_query = wa_query.filter(WhatsAppMessage.id.in_(wa_msg_int_ids))

        wa_messages = wa_query.order_by(WhatsAppMessage.timestamp.asc()).all()

        for msg in wa_messages:
            key = f"wa_{msg.id}"
            body = msg.body or ""
            classification = cls.classify_message(body, deletion_proximity=deletion_proximity)
            results[key] = {
                "id": key,
                "message_id": str(msg.message_id),
                "sender": msg.sender_jid,
                "timestamp": msg.timestamp,
                "app": "whatsapp",
                **classification,
            }
            tone_counts[classification["tone"]] = tone_counts.get(classification["tone"], 0) + 1
            for intent in classification["intentions"]:
                intention_counts[intent] = intention_counts.get(intent, 0) + 1
            suspicion_scores.append(classification["suspicion_score"])

        # 2. Fetch Telegram messages
        tg_query = db.query(TelegramMessage).filter(TelegramMessage.evidence_id.in_(evidence_ids))
        if jid:
            tg_query = tg_query.filter(TelegramMessage.dialog_id == jid)
        if message_ids:
            tg_msg_int_ids = [int(m.replace("tg_", "")) for m in message_ids if m.startswith("tg_") and m.replace("tg_", "").isdigit()]
            if tg_msg_int_ids:
                tg_query = tg_query.filter(TelegramMessage.id.in_(tg_msg_int_ids))

        tg_messages = tg_query.order_by(TelegramMessage.timestamp.asc()).all()

        for msg in tg_messages:
            key = f"tg_{msg.id}"
            body = msg.body or ""
            classification = cls.classify_message(body, deletion_proximity=deletion_proximity)
            results[key] = {
                "id": key,
                "message_id": str(msg.message_id),
                "sender": str(msg.sender_id),
                "timestamp": msg.timestamp,
                "app": "telegram",
                **classification,
            }
            tone_counts[classification["tone"]] = tone_counts.get(classification["tone"], 0) + 1
            for intent in classification["intentions"]:
                intention_counts[intent] = intention_counts.get(intent, 0) + 1
            suspicion_scores.append(classification["suspicion_score"])

        total = len(results)
        avg_score = int(sum(suspicion_scores) / total) if total > 0 else 0
        max_score = max(suspicion_scores) if suspicion_scores else 0
        high_risk = sum(1 for s in suspicion_scores if s >= 70)

        return {
            "messages": results,
            "aggregate": {
                "total_analyzed": total,
                "average_suspicion_score": avg_score,
                "highest_suspicion_score": max_score,
                "tone_distribution": tone_counts,
                "intention_counts": intention_counts,
                "high_risk_message_count": high_risk,
            },
            "disclaimer": "Internal Investigative Aid Only — Excluded from Legal Court Reports",
        }

    @classmethod
    def query_case_copilot(
        cls,
        db: Session,
        case_id: int,
        query: str,
        jid: Optional[str] = None,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Process investigator natural language questions over case messages and evidence.
        """
        evidence_ids = [ev.id for ev in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()]
        if not evidence_ids or not query.strip():
            return {
                "query": query,
                "summary": "No case evidence or search terms provided.",
                "risk_level": "LOW",
                "findings": [],
                "total_matches": 0,
                "recommended_actions": ["Ingest evidence files or select a valid case."],
                "disclaimer": "Internal Investigative Aid Only — Excluded from Legal Court Reports",
            }

        q_lower = query.lower()
        q_tokens = [w for w in re.findall(r"\w+", q_lower) if len(w) > 2]

        # Gather messages
        wa_query = db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id.in_(evidence_ids))
        if jid:
            wa_query = wa_query.filter(WhatsAppMessage.key_remote_jid == jid)
        wa_msgs = wa_query.all()

        tg_query = db.query(TelegramMessage).filter(TelegramMessage.evidence_id.in_(evidence_ids))
        if jid:
            tg_query = tg_query.filter(TelegramMessage.dialog_id == jid)
        tg_msgs = tg_query.all()

        candidate_findings = []

        # Score messages against investigator query
        for msg in wa_msgs:
            body = msg.body or ""
            if not body:
                continue
            match_score = 0
            b_lower = body.lower()

            for token in q_tokens:
                if token in b_lower:
                    match_score += 15

            # Semantic match for common intent queries
            if any(w in q_lower for w in ["money", "cash", "financial", "wire", "crypto", "pay"]):
                for p in INTENTION_PATTERNS["financial_demand"]:
                    if re.search(p, b_lower):
                        match_score += 25
            if any(w in q_lower for w in ["threat", "aggressive", "blackmail", "coerce", "force"]):
                for p in INTENTION_PATTERNS["coercion"]:
                    if re.search(p, b_lower):
                        match_score += 30
            if any(w in q_lower for w in ["delete", "deleted", "erase", "wipe", "disappear", "gap"]):
                for p in INTENTION_PATTERNS["deletion_awareness"]:
                    if re.search(p, b_lower):
                        match_score += 30
            if any(w in q_lower for w in ["secret", "suspicious", "covert", "burner", "safe"]):
                for p in INTENTION_PATTERNS["covert_communication"]:
                    if re.search(p, b_lower):
                        match_score += 25

            if match_score > 0:
                cls_data = cls.classify_message(body)
                candidate_findings.append({
                    "id": f"wa_{msg.id}",
                    "message_id": str(msg.message_id),
                    "sender": msg.sender_jid,
                    "chat_jid": msg.key_remote_jid,
                    "app": "whatsapp",
                    "timestamp": msg.timestamp,
                    "body": body,
                    "relevance_score": match_score + cls_data["suspicion_score"] // 4,
                    "tone": cls_data["tone"],
                    "suspicion_score": cls_data["suspicion_score"],
                    "intentions": cls_data["intentions"],
                    "highlights": cls_data["highlights"],
                })

        for msg in tg_msgs:
            body = msg.body or ""
            if not body:
                continue
            match_score = 0
            b_lower = body.lower()

            for token in q_tokens:
                if token in b_lower:
                    match_score += 15

            if any(w in q_lower for w in ["money", "cash", "financial", "wire", "crypto", "pay"]):
                for p in INTENTION_PATTERNS["financial_demand"]:
                    if re.search(p, b_lower):
                        match_score += 25
            if any(w in q_lower for w in ["threat", "aggressive", "blackmail", "coerce", "force"]):
                for p in INTENTION_PATTERNS["coercion"]:
                    if re.search(p, b_lower):
                        match_score += 30
            if any(w in q_lower for w in ["delete", "deleted", "erase", "wipe", "disappear", "gap"]):
                for p in INTENTION_PATTERNS["deletion_awareness"]:
                    if re.search(p, b_lower):
                        match_score += 30
            if any(w in q_lower for w in ["secret", "suspicious", "covert", "burner", "safe"]):
                for p in INTENTION_PATTERNS["covert_communication"]:
                    if re.search(p, b_lower):
                        match_score += 25

            if match_score > 0:
                cls_data = cls.classify_message(body)
                candidate_findings.append({
                    "id": f"tg_{msg.id}",
                    "message_id": str(msg.message_id),
                    "sender": str(msg.sender_id),
                    "chat_jid": msg.dialog_id,
                    "app": "telegram",
                    "timestamp": msg.timestamp,
                    "body": body,
                    "relevance_score": match_score + cls_data["suspicion_score"] // 4,
                    "tone": cls_data["tone"],
                    "suspicion_score": cls_data["suspicion_score"],
                    "intentions": cls_data["intentions"],
                    "highlights": cls_data["highlights"],
                })

        # Sort findings by relevance score descending
        candidate_findings.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_findings = candidate_findings[:limit]
        total_matches = len(candidate_findings)

        # Risk level determination
        max_suspicion = max([f["suspicion_score"] for f in top_findings], default=0)
        coercion_count = sum(1 for f in top_findings if "coercion" in f["intentions"])
        financial_count = sum(1 for f in top_findings if "financial_demand" in f["intentions"])
        deletion_count = sum(1 for f in top_findings if "deletion_awareness" in f["intentions"])

        if max_suspicion >= 80 or coercion_count >= 2:
            risk_level = "CRITICAL"
        elif max_suspicion >= 60 or financial_count >= 2 or deletion_count >= 2:
            risk_level = "HIGH"
        elif total_matches > 0:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        # Generate structured forensic assessment
        if total_matches == 0:
            summary = f"No message patterns or forensic indicators matching '{query}' were detected in this case."
            actions = [
                "Refine search query or broaden keyword parameters.",
                "Verify that evidence files are parsed and extracted.",
            ]
        else:
            summary_parts = [
                f"Identified {total_matches} message record(s) relevant to '{query}'.",
                f"Risk assessment evaluated at {risk_level} (Peak Suspicion: {max_suspicion}%).",
            ]
            if coercion_count > 0:
                summary_parts.append(f"Detected {coercion_count} instance(s) of coercion or intimidation.")
            if financial_count > 0:
                summary_parts.append(f"Detected {financial_count} instance(s) of financial demands or transaction cues.")
            if deletion_count > 0:
                summary_parts.append(f"Detected {deletion_count} reference(s) to message deletion or chat wiping.")

            summary = " ".join(summary_parts)

            actions = []
            if coercion_count > 0 or max_suspicion >= 75:
                actions.append("Review cited messages for hostile intent and cross-reference with timeline timestamps.")
            if financial_count > 0:
                actions.append("Correlate extracted phone numbers and JIDs with banking or transaction records.")
            if deletion_count > 0:
                actions.append("Cross-check deletion gap table in Deleted Messages tab to confirm sequence gaps.")
            actions.append("Inspect sender cryptographic SHA-256 signatures in Chat Viewer.")

        return {
            "query": query,
            "summary": summary,
            "risk_level": risk_level,
            "findings": top_findings,
            "total_matches": total_matches,
            "recommended_actions": actions,
            "disclaimer": "Internal Investigative Aid Only — Excluded from Legal Court Reports",
        }
