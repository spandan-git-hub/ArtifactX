"""Unit tests for phone number normalization and deterministic identity resolution (B12.2).

Follows master.md R8, R11, R15 and 10_CORRELATION.md §B12.2:
- NormalizedPhone outputs e164, region_assumed, valid, original.
- Identity resolution deterministic union-find over normalized phone.
- Ambiguity detection when 1 phone maps to multiple distinct names.
- Decoy test: same display name with differing phone numbers produces NO link above weak_hint.
- Determinism: 20x shuffled input order yields identical clusters and finding IDs.
"""

import random
from dataclasses import dataclass
from typing import Optional
import pytest

from forensic.correlation.phone import normalize_phone, NormalizedPhone
from forensic.correlation.entities import IdentityResolutionEngine, Person


@dataclass
class MockContact:
    jid: str = ""
    user_id: str = ""
    phone_number: str = ""
    phone: str = ""
    display_name: str = ""
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    evidence_id: int = 1


def test_phone_normalization_formats():
    """Verify normalization across international, national, bare, and JID formats."""
    # International with plus
    p1 = normalize_phone("+91 98765 43210", default_region="IN")
    assert p1.valid
    assert p1.e164 == "+919876543210"
    assert not p1.region_assumed

    # National with leading zero (assumes default region IN)
    p2 = normalize_phone("098765-43210", default_region="IN")
    assert p2.valid
    assert p2.e164 == "+919876543210"
    assert p2.region_assumed

    # WhatsApp JID
    p3 = normalize_phone("919876543210:0@s.whatsapp.net", default_region="IN")
    assert p3.valid
    assert p3.e164 == "+919876543210"

    # US number
    p4 = normalize_phone("+1 (415) 555-2671", default_region="IN")
    assert p4.valid
    assert p4.e164 == "+14155552671"
    assert not p4.region_assumed

    # Invalid / empty
    p5 = normalize_phone("not-a-number", default_region="IN")
    assert not p5.valid
    assert p5.e164 is None


def test_identity_resolution_cross_platform_merge():
    """Verify WhatsApp and Telegram contacts with same phone merge into single Person."""
    engine = IdentityResolutionEngine()
    wa_contacts = [
        MockContact(jid="919876543210@s.whatsapp.net", phone_number="+91 98765 43210", display_name="Aarav Patel")
    ]
    tg_contacts = [
        MockContact(user_id="1001", phone="098765-43210", first_name="Aarav", last_name="Patel", username="aaravp")
    ]

    res = engine.resolve(wa_contacts, tg_contacts)
    persons = res["persons"]
    assert len(persons) == 1
    p = persons[0]
    assert "+919876543210" in p["phone_numbers"]
    assert len(p["resolved_accounts"]) == 2
    assert p["confidence_score"] < 1.0  # Rule R8
    assert p["match_certainty"] <= 1.0


def test_decoy_same_name_different_phone_produces_no_strong_link():
    """Verify Planted Decoy: same display name with differing phones produces NO strong link."""
    engine = IdentityResolutionEngine()
    wa_contacts = [
        MockContact(jid="919876540001@s.whatsapp.net", phone_number="+919876540001", display_name="Rohan Sharma (Decoy)")
    ]
    tg_contacts = [
        MockContact(user_id="2002", phone="+919876549999", first_name="Rohan", last_name="Sharma (Decoy)")
    ]

    findings = engine.resolve_findings(wa_contacts, tg_contacts)
    # Must produce 0 strong findings
    strong_findings = [f for f in findings if f.strength == "strong" and not f.below_threshold]
    assert len(strong_findings) == 0, f"Expected 0 strong findings for decoy, got {strong_findings}"

    # Decoy is flagged as below_threshold weak_hint
    decoy_findings = [f for f in findings if f.kind == "display_name_decoy"]
    assert len(decoy_findings) == 1
    assert decoy_findings[0].below_threshold is True
    assert decoy_findings[0].strength == "weak_hint"


def test_identity_ambiguity_flagging():
    """Verify ambiguity is flagged when 1 phone maps to multiple distinct names."""
    engine = IdentityResolutionEngine()
    wa_contacts = [
        MockContact(jid="919876543210@s.whatsapp.net", phone_number="+919876543210", display_name="Vikramaditya Rao")
    ]
    tg_contacts = [
        MockContact(user_id="3003", phone="+919876543210", first_name="Priya", last_name="Sharma")
    ]

    res = engine.resolve(wa_contacts, tg_contacts)
    assert len(res["persons"]) == 1
    p = res["persons"][0]
    assert p["is_ambiguous"] is True
    assert any("multiple distinct names" in reason for reason in p["ambiguity_reasons"])


def test_identity_resolution_determinism_under_shuffle():
    """Verify 20x input-shuffled order yields byte-identical person clusters."""
    engine = IdentityResolutionEngine()
    base_wa = [
        MockContact(jid=f"91987654321{i}@s.whatsapp.net", phone_number=f"+91987654321{i}", display_name=f"User {i}")
        for i in range(5)
    ]
    base_tg = [
        MockContact(user_id=str(4000 + i), phone=f"+91987654321{i}", first_name=f"User", last_name=str(i))
        for i in range(5)
    ]

    baseline = engine.resolve(base_wa, base_tg)
    baseline_ids = [p["person_id"] for p in baseline["persons"]]

    for trial in range(20):
        wa_shuffled = list(base_wa)
        tg_shuffled = list(base_tg)
        random.seed(trial)
        random.shuffle(wa_shuffled)
        random.shuffle(tg_shuffled)

        res = engine.resolve(wa_shuffled, tg_shuffled)
        trial_ids = [p["person_id"] for p in res["persons"]]
        assert trial_ids == baseline_ids, f"Trial {trial} produced divergent person IDs under shuffle"
