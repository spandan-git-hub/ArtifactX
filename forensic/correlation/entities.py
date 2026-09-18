"""
Identity Graph Entity Model and Resolution Engine.
Implements multi-entity resolution with evidence-backed provenance and strict judicial constraints:
Never merges identities solely on display name similarity; records limitations and confidence scores.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import uuid
import re


@dataclass
class PhoneNumber:
    e164: str
    raw: str = ""
    country_code: str = ""


@dataclass
class WhatsAppJID:
    jid: str
    phone_number: str = ""
    display_name: str = ""
    is_group: bool = False


@dataclass
class TelegramUser:
    user_id: str
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    phone: str = ""


@dataclass
class TelegramHandle:
    handle: str
    user_id: Optional[str] = None


@dataclass
class ContactAlias:
    alias: str
    platform: str
    identifier: str


@dataclass
class MediaIdentity:
    media_id: str
    sha256: str
    phash: Optional[str] = None
    dhash: Optional[str] = None


@dataclass
class EvidenceObservation:
    evidence_id: int
    file_id: Optional[int] = None
    message_id: Optional[str] = None
    record_offset: Optional[int] = None
    source_app: str = "unknown"
    detail: str = ""


@dataclass
class EvidenceEdge:
    """An evidence-backed edge connecting entities with provenance and legal limitations."""
    edge_id: str
    source_id: str
    source_type: str
    target_id: str
    target_type: str
    relation_type: str
    strength_score: float
    method: str
    source_observations: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    is_ambiguous: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "relation_type": self.relation_type,
            "strength_score": round(self.strength_score, 4),
            "method": self.method,
            "source_observations": self.source_observations,
            "limitations": self.limitations,
            "provenance": self.provenance,
            "is_ambiguous": self.is_ambiguous,
        }


@dataclass
class Person:
    """
    Hypothesis-backed Person cluster node.
    Not an assertion of real-world physical identity, but an evidentiary link
    grouping accounts, phone numbers, and observed aliases.
    """
    person_id: str
    label: str
    resolved_accounts: List[Dict[str, Any]] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    handles: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    resolution_method: str = "E.164_PHONE_MATCH"
    evidence_links: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    is_ambiguous: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "person_id": self.person_id,
            "label": self.label,
            "resolved_accounts": self.resolved_accounts,
            "phone_numbers": self.phone_numbers,
            "handles": self.handles,
            "aliases": self.aliases,
            "confidence_score": round(self.confidence_score, 4),
            "resolution_method": self.resolution_method,
            "evidence_links": self.evidence_links,
            "limitations": self.limitations,
            "provenance": self.provenance,
            "is_ambiguous": self.is_ambiguous,
        }


def normalize_e164(raw_phone: str) -> str:
    """Normalize raw phone strings or JIDs into canonical E.164 format."""
    if not raw_phone:
        return ""
    clean = str(raw_phone).split("@")[0].split(":")[0].strip()
    digits = "".join(ch for ch in clean if ch.isdigit())
    if not digits:
        return ""
    if str(raw_phone).strip().startswith("+"):
        return f"+{digits}"
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}"


class IdentityResolutionEngine:
    """
    Engine for multi-modal identity resolution across forensic evidence.
    Follows judicial rule: Never merges identities solely on display name similarity.
    """

    def __init__(self):
        self.version = "1.0.0"

    def resolve(
        self,
        wa_contacts: List[Any],
        tg_contacts: List[Any],
        wa_messages: Optional[List[Any]] = None,
        tg_messages: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes identity resolution clustering.

        Returns:
            {
                "persons": [Person.to_dict()],
                "edges": [EvidenceEdge.to_dict()],
                "ambiguous_candidates": [...]
            }
        """
        persons: List[Person] = []
        edges: List[EvidenceEdge] = []
        ambiguous_candidates: List[Dict[str, Any]] = []

        # 1. Map WhatsApp contacts by E.164 phone
        wa_by_phone: Dict[str, List[Any]] = {}
        for wa in wa_contacts:
            phone = normalize_e164(getattr(wa, "phone_number", None) or getattr(wa, "jid", ""))
            if phone:
                wa_by_phone.setdefault(phone, []).append(wa)

        # 2. Map Telegram contacts by E.164 phone
        tg_by_phone: Dict[str, List[Any]] = {}
        for tg in tg_contacts:
            phone = normalize_e164(getattr(tg, "phone", None) or "")
            if phone:
                tg_by_phone.setdefault(phone, []).append(tg)

        matched_phones = set(wa_by_phone.keys()) & set(tg_by_phone.keys())
        processed_wa_jids: Set[str] = set()
        processed_tg_uids: Set[str] = set()

        # Build Person clusters for exact E.164 phone matches (Confidence 1.0)
        for phone in sorted(matched_phones):
            wa_list = wa_by_phone[phone]
            tg_list = tg_by_phone[phone]

            person_id = f"person_{uuid.uuid4().hex[:12]}"
            label = ""
            aliases: Set[str] = set()
            handles: Set[str] = set()
            accounts: List[Dict[str, Any]] = []
            ev_links: List[Dict[str, Any]] = []

            for wa in wa_list:
                jid = getattr(wa, "jid", "")
                display_name = getattr(wa, "display_name", "") or jid
                processed_wa_jids.add(jid)
                if not label and display_name:
                    label = display_name
                if display_name:
                    aliases.add(display_name)
                accounts.append({
                    "platform": "whatsapp",
                    "account_id": jid,
                    "display_name": display_name,
                    "evidence_id": getattr(wa, "evidence_id", None),
                })
                ev_links.append({
                    "platform": "whatsapp",
                    "evidence_id": getattr(wa, "evidence_id", None),
                    "identifier": jid,
                })

            for tg in tg_list:
                uid = str(getattr(tg, "user_id", ""))
                tg_name = f"{getattr(tg, 'first_name', '') or ''} {getattr(tg, 'last_name', '') or ''}".strip()
                username = getattr(tg, "username", "") or ""
                processed_tg_uids.add(uid)
                if not label and (tg_name or username):
                    label = tg_name or username
                if tg_name:
                    aliases.add(tg_name)
                if username:
                    handles.add(f"@{username.lstrip('@')}")
                accounts.append({
                    "platform": "telegram",
                    "account_id": uid,
                    "display_name": tg_name,
                    "username": username,
                    "evidence_id": getattr(tg, "evidence_id", None),
                })
                ev_links.append({
                    "platform": "telegram",
                    "evidence_id": getattr(tg, "evidence_id", None),
                    "identifier": uid,
                })

            if not label:
                label = f"Person {phone}"

            p = Person(
                person_id=person_id,
                label=label,
                resolved_accounts=accounts,
                phone_numbers=[phone],
                handles=sorted(handles),
                aliases=sorted(aliases),
                confidence_score=1.0,
                resolution_method="EXACT_E164_CORROBORATION",
                evidence_links=ev_links,
                limitations=[],
                provenance={
                    "algorithm": "IdentityResolutionEngine",
                    "version": self.version,
                    "basis": "Cryptographic/telecom E.164 equivalence",
                },
                is_ambiguous=False,
            )
            persons.append(p)

            # Create cross-account evidence edges
            for wa in wa_list:
                for tg in tg_list:
                    edge = EvidenceEdge(
                        edge_id=f"edge_{uuid.uuid4().hex[:12]}",
                        source_id=getattr(wa, "jid", ""),
                        source_type="whatsapp_jid",
                        target_id=str(getattr(tg, "user_id", "")),
                        target_type="telegram_user",
                        relation_type="SAME_ENTITY_CORROBORATED",
                        strength_score=1.0,
                        method="E164_PHONE_MATCH",
                        source_observations=[
                            {"evidence_id": getattr(wa, "evidence_id", None), "phone": phone, "platform": "whatsapp"},
                            {"evidence_id": getattr(tg, "evidence_id", None), "phone": phone, "platform": "telegram"},
                        ],
                        limitations=[],
                        provenance={"algorithm": "IdentityResolutionEngine", "version": self.version},
                        is_ambiguous=False,
                    )
                    edges.append(edge)

        # 3. Handle-based matching for unmerged accounts (Confidence 0.85)
        for wa in wa_contacts:
            jid = getattr(wa, "jid", "")
            if jid in processed_wa_jids:
                continue
            wa_name = (getattr(wa, "display_name", "") or "").strip().lower()
            if not wa_name:
                continue

            for tg in tg_contacts:
                uid = str(getattr(tg, "user_id", ""))
                if uid in processed_tg_uids:
                    continue
                username = (getattr(tg, "username", "") or "").strip().lower()
                if username and (username == wa_name or username in jid.lower()):
                    processed_wa_jids.add(jid)
                    processed_tg_uids.add(uid)

                    tg_full = f"{getattr(tg, 'first_name', '') or ''} {getattr(tg, 'last_name', '') or ''}".strip()
                    phone_wa = normalize_e164(getattr(wa, "phone_number", None) or jid)
                    phone_tg = normalize_e164(getattr(tg, "phone", None) or "")
                    phones = [p for p in [phone_wa, phone_tg] if p]

                    person_id = f"person_{uuid.uuid4().hex[:12]}"
                    p = Person(
                        person_id=person_id,
                        label=tg_full or getattr(wa, "display_name", "") or f"@{username}",
                        resolved_accounts=[
                            {"platform": "whatsapp", "account_id": jid, "display_name": getattr(wa, "display_name", "")},
                            {"platform": "telegram", "account_id": uid, "username": username, "display_name": tg_full},
                        ],
                        phone_numbers=phones,
                        handles=[f"@{username}"],
                        aliases=[getattr(wa, "display_name", ""), tg_full],
                        confidence_score=0.85,
                        resolution_method="TELEGRAM_HANDLE_EQUIVALENCE",
                        evidence_links=[
                            {"platform": "whatsapp", "evidence_id": getattr(wa, "evidence_id", None), "identifier": jid},
                            {"platform": "telegram", "evidence_id": getattr(tg, "evidence_id", None), "identifier": uid},
                        ],
                        limitations=[
                            "Linked via public Telegram handle match; telecommunication carrier records not linked."
                        ],
                        provenance={"algorithm": "IdentityResolutionEngine", "version": self.version},
                        is_ambiguous=False,
                    )
                    persons.append(p)

                    edges.append(EvidenceEdge(
                        edge_id=f"edge_{uuid.uuid4().hex[:12]}",
                        source_id=jid,
                        source_type="whatsapp_jid",
                        target_id=uid,
                        target_type="telegram_user",
                        relation_type="HANDLE_CORRELATED_CANDIDATE",
                        strength_score=0.85,
                        method="TELEGRAM_HANDLE_MATCH",
                        source_observations=[
                            {"platform": "whatsapp", "evidence_id": getattr(wa, "evidence_id", None)},
                            {"platform": "telegram", "evidence_id": getattr(tg, "evidence_id", None), "username": username},
                        ],
                        limitations=["Handle match only; requires corroborating ISP/device subscriber records."],
                        provenance={"algorithm": "IdentityResolutionEngine", "version": self.version},
                        is_ambiguous=False,
                    ))

        # 4. Display Name Similarity Check:
        # STRICT FORENSIC RULE: NEVER merge into a single Person node solely because names look similar!
        # Instead, record as AMBIGUOUS_CANDIDATE edge with clear judicial disclaimer.
        for wa in wa_contacts:
            wa_name = (getattr(wa, "display_name", "") or "").strip().lower()
            if not wa_name or len(wa_name) < 3:
                continue

            for tg in tg_contacts:
                uid = str(getattr(tg, "user_id", ""))
                tg_name = f"{getattr(tg, 'first_name', '') or ''} {getattr(tg, 'last_name', '') or ''}".strip().lower()
                if not tg_name or len(tg_name) < 3:
                    continue

                if wa_name == tg_name:
                    # Check if already linked via verified Person
                    already_linked = any(
                        any(acc.get("account_id") == getattr(wa, "jid", "") for acc in p.resolved_accounts) and
                        any(acc.get("account_id") == uid for acc in p.resolved_accounts)
                        for p in persons
                    )
                    if not already_linked:
                        ambiguous_edge = EvidenceEdge(
                            edge_id=f"edge_ambig_{uuid.uuid4().hex[:12]}",
                            source_id=getattr(wa, "jid", ""),
                            source_type="whatsapp_jid",
                            target_id=uid,
                            target_type="telegram_user",
                            relation_type="AMBIGUOUS_NAME_SIMILARITY",
                            strength_score=0.45,
                            method="NAME_STRING_EQUALITY",
                            source_observations=[
                                {"platform": "whatsapp", "name": getattr(wa, "display_name", "")},
                                {"platform": "telegram", "name": tg_name},
                            ],
                            limitations=[
                                "JUDICIAL INVARIANT: Name similarity alone without E.164 phone or cryptographic identifier does NOT establish identity.",
                                "Potential homonym or separate individuals sharing common display name."
                            ],
                            provenance={"algorithm": "IdentityResolutionEngine", "version": self.version},
                            is_ambiguous=True,
                        )
                        edges.append(ambiguous_edge)
                        ambiguous_candidates.append({
                            "wa_jid": getattr(wa, "jid", ""),
                            "wa_name": getattr(wa, "display_name", ""),
                            "tg_user_id": uid,
                            "tg_name": tg_name,
                            "reason": "Exact display name match without telecom corroboration",
                            "limitations": ambiguous_edge.limitations,
                        })

        return {
            "persons": [p.to_dict() for p in persons],
            "edges": [e.to_dict() for e in edges],
            "ambiguous_candidates": ambiguous_candidates,
        }
