"""Forensic correlation module."""

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