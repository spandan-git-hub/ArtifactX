"""Forensic cross-platform correlation module (B12)."""

from forensic.correlation.thresholds import (
    THRESHOLDS_VERSION,
    CorrelationThresholds,
    DEFAULT_THRESHOLDS,
)
from forensic.correlation.models import (
    CorrelationFinding,
    generate_deterministic_finding_id,
)
from forensic.correlation.phone import (
    NormalizedPhone,
    normalize_phone,
)
from forensic.correlation.keccak import keccak_256
from forensic.correlation.entities import (
    Person,
    PhoneNumber,
    WhatsAppJID,
    TelegramUser,
    TelegramHandle,
    ContactAlias,
    MediaIdentity,
    EvidenceEdge,
    IdentityResolutionEngine,
    normalize_e164,
)
from forensic.correlation.handover import (
    PlatformHandoverCandidate,
    PlatformHandoverDetector,
)
from forensic.correlation.media_hash import (
    compute_dhash,
    compute_phash,
    hamming_distance,
    compute_image_entropy,
    PerceptualMediaCorrelator,
)
from forensic.correlation.artifacts import (
    ExtractedArtifact,
    ArtifactStitcher,
    validate_btc_address,
    validate_evm_address,
    validate_tron_address,
    validate_monero_address,
    validate_iban,
    validate_luhn,
    validate_swift_bic,
    validate_upi_handle,
    normalize_url,
)
from forensic.correlation.rendezvous import (
    LocationObservation,
    RendezvousCandidate,
    SpatiotemporalRendezvousDetector,
    haversine_distance_meters,
)
from forensic.correlation.matcher import (
    WhatsAppMessage,
    WhatsAppContact,
    TelegramMessage,
    TelegramContact,
    MediaItem,
    correlate_all,
)

__all__ = [
    "THRESHOLDS_VERSION",
    "CorrelationThresholds",
    "DEFAULT_THRESHOLDS",
    "CorrelationFinding",
    "generate_deterministic_finding_id",
    "NormalizedPhone",
    "normalize_phone",
    "keccak_256",
    "Person",
    "PhoneNumber",
    "WhatsAppJID",
    "TelegramUser",
    "TelegramHandle",
    "ContactAlias",
    "MediaIdentity",
    "EvidenceEdge",
    "IdentityResolutionEngine",
    "normalize_e164",
    "PlatformHandoverCandidate",
    "PlatformHandoverDetector",
    "compute_dhash",
    "compute_phash",
    "hamming_distance",
    "compute_image_entropy",
    "PerceptualMediaCorrelator",
    "ExtractedArtifact",
    "ArtifactStitcher",
    "validate_btc_address",
    "validate_evm_address",
    "validate_tron_address",
    "validate_monero_address",
    "validate_iban",
    "validate_luhn",
    "validate_swift_bic",
    "validate_upi_handle",
    "normalize_url",
    "LocationObservation",
    "RendezvousCandidate",
    "SpatiotemporalRendezvousDetector",
    "haversine_distance_meters",
    "WhatsAppMessage",
    "WhatsAppContact",
    "TelegramMessage",
    "TelegramContact",
    "MediaItem",
    "correlate_all",
]