"""Unit tests for cryptographic and financial artifact validators (B12.3).

Follows master.md R1, R8, R11, R15, R20 and 10_CORRELATION.md §B12.3:
- Tests Bitcoin Base58Check and Bech32/Bech32m against BIP test vectors.
- Tests EVM addresses with EIP-55 checksum against Ethereum official test vectors.
- Tests IBAN validation with ISO lengths and ISO 7064 Modulo 97-10.
- Tests invalid 1-character mutated decoys produce 0 links.
"""

import pytest

from forensic.correlation.artifacts import (
    validate_btc_address,
    validate_evm_address,
    validate_iban,
    validate_bech32,
)
from forensic.correlation.keccak import keccak_256


# ==============================================================================
# Keccak-256 Primitives
# ==============================================================================

def test_keccak_256_known_vectors():
    """Verify Keccak-256 against known test vectors."""
    assert keccak_256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    # Single character
    h_a = keccak_256(b"a").hex()
    assert len(h_a) == 64
    # Multi-block data (>136 bytes)
    data = b"A" * 300
    h_multi = keccak_256(data).hex()
    assert len(h_multi) == 64


# ==============================================================================
# Bitcoin Address Validation (BIP-13, BIP-173, BIP-350)
# ==============================================================================

@pytest.mark.parametrize("addr, expected_valid", [
    # Legacy P2PKH
    ("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", True),
    ("13meW3hgZ2sodK8Bj82EjscfZoSRrQ8Yf2", True),
    ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", True),
    # Legacy P2SH
    ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", True),
    # Bech32 Segwit (BIP-173)
    ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", True),
    # Bech32m Taproot (BIP-350)
    ("bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0", True),
    # 1-char mutated Base58Check (Decoy)
    ("13meW3hgZ2sodK8Bj82EjscfZoSRrQ8Yf3", False),
    ("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN3", False),
    # 1-char mutated Bech32
    ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5", False),
    # Bad characters
    ("10OIl0OIl0OIl0OIl0OIl0OIl0OIl0OI", False),
    ("", False),
    ("invalid", False),
])
def test_btc_address_validation(addr: str, expected_valid: bool):
    valid, status = validate_btc_address(addr)
    assert valid is expected_valid, f"Address {addr} expected {expected_valid}, got {valid} with status {status}"


# ==============================================================================
# EVM / Ethereum EIP-55 Checksum Validation
# ==============================================================================

@pytest.mark.parametrize("addr, expected_valid, expected_status", [
    # Official EIP-55 test vectors (mixed case)
    ("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", True, "VALIDATED_EIP55_CHECKSUM_OK"),
    ("0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359", True, "VALIDATED_EIP55_CHECKSUM_OK"),
    ("0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB", True, "VALIDATED_EIP55_CHECKSUM_OK"),
    ("0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb", True, "VALIDATED_EIP55_CHECKSUM_OK"),
    ("0xE7f824EA18C65c150982Ddb2d777F59DEf8899ed", True, "VALIDATED_EIP55_CHECKSUM_OK"),
    # All lowercase: valid syntax, no checksum
    ("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed", True, "FORMAT_VALID_NO_CHECKSUM"),
    ("0xe7f824ea18c65c150982ddb2d777f59def8899ed", True, "FORMAT_VALID_NO_CHECKSUM"),
    # All uppercase: valid syntax, no checksum
    ("0x5AAEB6053F3E94C9B9A09F33669435E7EF1BEAED", True, "FORMAT_VALID_NO_CHECKSUM"),
    ("0xE7F824EA18C65C150982DDB2D777F59DEF8899ED", True, "FORMAT_VALID_NO_CHECKSUM"),
    # Mutated casing / bad EIP-55 checksum (Decoy from DS-06)
    ("0xe7f824EA18C65c150982Ddb2d777F59DEf8899ed", False, "INVALID_EIP55_CHECKSUM"),
    ("0x5aaeb6053F3E94C9b9A09f33669435E7Ef1BeAed", False, "INVALID_EIP55_CHECKSUM"),
    # Invalid length / non-hex
    ("0x1234", False, "INVALID_HEX_LENGTH"),
    ("0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ", False, "INVALID_HEX_LENGTH"),
    ("5aaeb6053f3e94c9b9a09f33669435e7ef1beaed", False, "MISSING_0X_PREFIX"),
])
def test_evm_address_validation(addr: str, expected_valid: bool, expected_status: str):
    valid, status, norm = validate_evm_address(addr)
    assert valid is expected_valid
    assert status == expected_status
    if expected_valid:
        assert norm.startswith("0x")
        assert len(norm) == 42


# ==============================================================================
# IBAN Validation (ISO 7064 Modulo 97-10 & Country Registry)
# ==============================================================================

@pytest.mark.parametrize("iban, expected_valid", [
    # Valid German IBANs (22 chars)
    ("DE58 2610 9010 2458 7131 64", True),
    ("DE58261090102458713164", True),
    # Valid British IBAN (22 chars)
    ("GB82 WEST 1234 5698 7654 32", True),
    # Valid French IBAN (27 chars)
    ("FR14 2004 1010 0505 0001 3M02 606", True),
    # 1-char mutated check digits (Decoy from DS-06)
    ("DE58261090102458713165", False),
    # Country length mismatch
    ("DE582610901024587131641", False),
    ("GB82WEST1234569876543", False),
    # Non-alphanumeric / invalid syntax
    ("XX0012345", False),
    ("", False),
])
def test_iban_validation(iban: str, expected_valid: bool):
    valid, status, norm = validate_iban(iban)
    assert valid is expected_valid
    if expected_valid:
        assert " " not in norm
        assert "-" not in norm
        assert norm.isupper()
