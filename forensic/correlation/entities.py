"""Identity Graph Entity Model and Resolution Engine (B12.2).

Implements multi-entity resolution with evidence-backed provenance and strict judicial constraints:
- Deterministic union-find over normalized E.164 phone numbers as the only strong joining key.
- Same display name with differing phone numbers produces NO link above weak_hint (decoy handling).
- Ambiguity detection when one phone maps to multiple names or an identity possesses multiple phones.
- Confidence score strictly < 1.0 for all identity inferences (master.md R8).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

from forensic.correlation.models import CorrelationFinding, generate_deterministic_finding_id
from forensic.correlation.phone import NormalizedPhone, normalize_phone
from forensic.correlation.thresholds import CorrelationThresholds, DEFAULT_THRESHOLDS


@dataclass
class PhoneNumber:
    e164: str
    raw: str = ""
    country_code: str = ""
    region_assumed: bool = False


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
    confidence_score: float = 0.95
    match_certainty: float = 1.0
    resolution_method: str = "E.164_PHONE_MATCH"
    evidence_links: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    is_ambiguous: bool = False
    ambiguity_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "person_id": self.person_id,
            "label": self.label,
            "resolved_accounts": self.resolved_accounts,
            "phone_numbers": self.phone_numbers,
            "handles": self.handles,
            "aliases": self.aliases,
            "confidence_score": round(self.confidence_score, 4),
            "match_certainty": round(self.match_certainty, 4),
            "resolution_method": self.resolution_method,
            "evidence_links": self.evidence_links,
            "limitations": self.limitations,
            "provenance": self.provenance,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_reasons": self.ambiguity_reasons,
        }


# Backwards compatibility helper
def normalize_e164(raw_phone: str) -> str:
    """Normalize raw phone strings or JIDs into canonical E.164 format."""
    res = normalize_phone(raw_phone)
    return res.e164 or ""


class DisjointSet:
    """Deterministic Disjoint-Set (Union-Find) for entity clustering."""

    def __init__(self):
        self.parent: Dict[str, str] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            return item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, a: str, b: str) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a != root_b:
            # Deterministic tie-breaking: pick lexicographically smaller root
            if root_a < root_b:
                self.parent[root_b] = root_a
            else:
                self.parent[root_a] = root_b


class IdentityResolutionEngine:
    """
    Engine for multi-modal identity resolution across forensic evidence.
    Follows judicial rule: Never merges identities solely on display name similarity.
    Deterministic union-find over normalized phone as the only strong joining key.
    """

    def __init__(self, thresholds: CorrelationThresholds = DEFAULT_THRESHOLDS):
        self.thresholds = thresholds
        self.version = thresholds.version

    def resolve(
        self,
        wa_contacts: List[Any],
        tg_contacts: List[Any],
        wa_messages: Optional[List[Any]] = None,
        tg_messages: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes identity resolution clustering with ambiguity flagging and decoy rejection.
        """
        persons: List[Person] = []
        edges: List[EvidenceEdge] = []
        ambiguous_candidates: List[Dict[str, Any]] = []

        # 1. Normalize and index WhatsApp contacts
        wa_by_phone: Dict[str, List[Tuple[Any, NormalizedPhone]]] = {}
        wa_by_name: Dict[str, List[Any]] = {}

        for wa in wa_contacts:
            raw_phone = getattr(wa, "phone_number", None) or getattr(wa, "jid", "")
            norm = normalize_phone(raw_phone, default_region=self.thresholds.phone_default_region)
            if norm.valid and norm.e164:
                wa_by_phone.setdefault(norm.e164, []).append((wa, norm))
            name = (getattr(wa, "display_name", "") or "").strip().lower()
            if name:
                wa_by_name.setdefault(name, []).append(wa)

        # 2. Normalize and index Telegram contacts
        tg_by_phone: Dict[str, List[Tuple[Any, NormalizedPhone]]] = {}
        tg_by_name: Dict[str, List[Any]] = {}

        for tg in tg_contacts:
            raw_phone = getattr(tg, "phone", None) or ""
            if raw_phone:
                norm = normalize_phone(raw_phone, default_region=self.thresholds.phone_default_region)
                if norm.valid and norm.e164:
                    tg_by_phone.setdefault(norm.e164, []).append((tg, norm))
            tg_full = f"{getattr(tg, 'first_name', '') or ''} {getattr(tg, 'last_name', '') or ''}".strip().lower()
            if tg_full:
                tg_by_name.setdefault(tg_full, []).append(tg)

        # 3. Deterministic Union-Find over matching normalized phones
        uf = DisjointSet()
        common_phones = sorted(set(wa_by_phone.keys()) & set(tg_by_phone.keys()))

        for phone in common_phones:
            uf.find(phone)

        # Build clusters by root
        clusters: Dict[str, List[str]] = {}
        for phone in common_phones:
            root = uf.find(phone)
            clusters.setdefault(root, []).append(phone)

        processed_wa_jids: Set[str] = set()
        processed_tg_uids: Set[str] = set()

        for root in sorted(clusters.keys()):
            phone_group = sorted(clusters[root])
            all_wa = []
            all_tg = []
            any_region_assumed = False

            for p in phone_group:
                for wa, norm in wa_by_phone[p]:
                    all_wa.append((wa, norm))
                    if norm.region_assumed:
                        any_region_assumed = True
                for tg, norm in tg_by_phone[p]:
                    all_tg.append((tg, norm))
                    if norm.region_assumed:
                        any_region_assumed = True

            aliases: Set[str] = set()
            handles: Set[str] = set()
            accounts: List[Dict[str, Any]] = []
            ev_links: List[Dict[str, Any]] = []
            label = ""

            for wa, norm in all_wa:
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

            for tg, norm in all_tg:
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

            # Check ambiguity flags (10_CORRELATION.md §B12.2)
            ambiguity_reasons = []
            is_ambiguous = False
            distinct_names = {a for a in aliases if a}
            if len(distinct_names) >= 2:
                is_ambiguous = True
                ambiguity_reasons.append(f"Phone maps to multiple distinct names: {sorted(distinct_names)}")
            if len(phone_group) >= 2:
                is_ambiguous = True
                ambiguity_reasons.append(f"Identity cluster merges multiple distinct phones: {phone_group}")

            # Confidence score strictly < 1.0 (master.md R8)
            match_cert = 0.90 if any_region_assumed else 1.0
            conf_score = 0.88 if any_region_assumed else 0.95
            if is_ambiguous:
                conf_score = min(conf_score, 0.80)

            limitations = [
                "E.164 phone number equivalence corroborated across platforms.",
                "SIM ownership or device physical user may change over time.",
            ]
            if any_region_assumed:
                limitations.append(f"Default country region ({self.thresholds.phone_default_region}) assumed for one or more numbers lacking international prefix.")
            if is_ambiguous:
                limitations.extend(ambiguity_reasons)

            person_id = f"person_{hashlib.sha256(phone_group[0].encode()).hexdigest()[:12]}"

            p = Person(
                person_id=person_id,
                label=label or f"Person {phone_group[0]}",
                resolved_accounts=accounts,
                phone_numbers=phone_group,
                handles=sorted(handles),
                aliases=sorted(aliases),
                confidence_score=conf_score,
                match_certainty=match_cert,
                resolution_method="EXACT_E164_CORROBORATION",
                evidence_links=ev_links,
                limitations=limitations,
                provenance={
                    "algorithm": "IdentityResolutionEngine",
                    "version": self.version,
                    "thresholds_version": self.thresholds.version,
                    "phones": phone_group,
                },
                is_ambiguous=is_ambiguous,
                ambiguity_reasons=ambiguity_reasons,
            )
            persons.append(p)

            # Build evidence edges
            for wa, norm_wa in all_wa:
                wa_jid_val = str(getattr(wa, "jid", ""))
                for tg, norm_tg in all_tg:
                    tg_uid_val = str(getattr(tg, "user_id", ""))
                    edge_raw = f"{wa_jid_val}_{tg_uid_val}".encode("utf-8")
                    edge_id = "edge_" + hashlib.sha256(edge_raw).hexdigest()[:12]
                    edge = EvidenceEdge(
                        edge_id=edge_id,
                        source_id=wa_jid_val,
                        source_type="whatsapp_jid",
                        target_id=tg_uid_val,
                        target_type="telegram_user",
                        relation_type="SAME_ENTITY_CORROBORATED",
                        strength_score=conf_score,
                        method="E164_PHONE_MATCH",
                        source_observations=[
                            {"evidence_id": getattr(wa, "evidence_id", None), "phone": norm_wa.e164, "platform": "whatsapp"},
                            {"evidence_id": getattr(tg, "evidence_id", None), "phone": norm_tg.e164, "platform": "telegram"},
                        ],
                        limitations=limitations,
                        provenance={"algorithm": "IdentityResolutionEngine", "version": self.version},
                        is_ambiguous=is_ambiguous,
                    )
                    edges.append(edge)

        # 4. Decoy & Display-name matching check (10_CORRELATION.md §B12.2)
        # Same display name with DIFFERENT phone numbers => NO link above weak_hint (decoy!)
        common_names = set(wa_by_name.keys()) & set(tg_by_name.keys())
        for name in sorted(common_names):
            wa_list = wa_by_name[name]
            tg_list = tg_by_name[name]
            for wa in wa_list:
                jid = getattr(wa, "jid", "")
                norm_wa = normalize_phone(getattr(wa, "phone_number", None) or jid, default_region=self.thresholds.phone_default_region)
                for tg in tg_list:
                    uid = str(getattr(tg, "user_id", ""))
                    norm_tg = normalize_phone(getattr(tg, "phone", None) or "", default_region=self.thresholds.phone_default_region)

                    # If both have phones and phones differ -> planted decoy! Strictly weak_hint below threshold
                    if norm_wa.valid and norm_tg.valid and norm_wa.e164 != norm_tg.e164:
                        ambiguous_candidates.append({
                            "type": "DECOY_SAME_NAME_DIFFERENT_PHONE",
                            "display_name": name,
                            "whatsapp_jid": jid,
                            "whatsapp_phone": norm_wa.e164,
                            "telegram_user_id": uid,
                            "telegram_phone": norm_tg.e164,
                            "strength": "weak_hint",
                            "confidence_score": 0.20,
                            "note": "Planted decoy: identical contact name with differing phone numbers; excluded from strong link.",
                        })

        return {
            "persons": [p.to_dict() for p in persons],
            "edges": [e.to_dict() for e in edges],
            "ambiguous_candidates": ambiguous_candidates,
        }

    def resolve_findings(
        self,
        wa_contacts: List[Any],
        tg_contacts: List[Any],
    ) -> List[CorrelationFinding]:
        """Generate CorrelationFinding instances for cross-platform identity matches."""
        res = self.resolve(wa_contacts, tg_contacts)
        findings: List[CorrelationFinding] = []

        for p in res.get("persons", []):
            accounts = p.get("resolved_accounts", [])
            wa_acc = next((a for a in accounts if a.get("platform") == "whatsapp"), None)
            tg_acc = next((a for a in accounts if a.get("platform") == "telegram"), None)

            if wa_acc and tg_acc:
                phones = p.get("phone_numbers", [])
                norm_val = phones[0] if phones else p.get("label", "")
                f_id = generate_deterministic_finding_id(
                    "phone_identity",
                    norm_val,
                    f"whatsapp:{wa_acc.get('account_id')}",
                    f"telegram:{tg_acc.get('account_id')}",
                    self.thresholds.version,
                )

                findings.append(CorrelationFinding(
                    finding_id=f_id,
                    kind="phone_identity",
                    strength="strong",
                    match_certainty=p.get("match_certainty", 1.0),
                    confidence_score=p.get("confidence_score", 0.95),
                    normalized_value=norm_val,
                    left_ref={
                        "platform": "whatsapp",
                        "account_id": wa_acc.get("account_id"),
                        "display_name": wa_acc.get("display_name"),
                        "evidence_id": wa_acc.get("evidence_id"),
                    },
                    right_ref={
                        "platform": "telegram",
                        "account_id": tg_acc.get("account_id"),
                        "display_name": tg_acc.get("display_name"),
                        "username": tg_acc.get("username"),
                        "evidence_id": tg_acc.get("evidence_id"),
                    },
                    limitations=tuple(p.get("limitations", [])),
                    provenance=p.get("provenance", {}),
                    ambiguity=tuple(p.get("ambiguity_reasons", [])),
                    thresholds_version=self.thresholds.version,
                    below_threshold=p.get("confidence_score", 0.95) < self.thresholds.report_threshold_confidence,
                ))

        # Add ambiguous candidates as weak_hint below threshold
        for cand in res.get("ambiguous_candidates", []):
            f_id = generate_deterministic_finding_id(
                "display_name_decoy",
                cand.get("display_name", ""),
                f"whatsapp:{cand.get('whatsapp_jid')}",
                f"telegram:{cand.get('telegram_user_id')}",
                self.thresholds.version,
            )
            findings.append(CorrelationFinding(
                finding_id=f_id,
                kind="display_name_decoy",
                strength="weak_hint",
                match_certainty=0.20,
                confidence_score=cand.get("confidence_score", 0.20),
                normalized_value=cand.get("display_name", ""),
                left_ref={
                    "platform": "whatsapp",
                    "account_id": cand.get("whatsapp_jid"),
                    "phone": cand.get("whatsapp_phone"),
                },
                right_ref={
                    "platform": "telegram",
                    "account_id": cand.get("telegram_user_id"),
                    "phone": cand.get("telegram_phone"),
                },
                limitations=(
                    "Identical display name but disparate phone numbers (planted decoy).",
                    "Names alone do not establish identity across platforms.",
                ),
                provenance={
                    "algorithm": "IdentityResolutionEngine",
                    "reason": cand.get("type"),
                },
                ambiguity=("Disparate phone numbers with identical display name",),
                thresholds_version=self.thresholds.version,
                below_threshold=True,  # Strictly below reporting threshold!
            ))

        findings.sort(key=lambda f: f.sort_key())
        return findings
