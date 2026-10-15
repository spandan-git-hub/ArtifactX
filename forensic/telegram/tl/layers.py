"""
MTProto Layer Definitions & Notes (spec B9.2).

Documents verified layer schemas and known legacy constructor differences.
Follows master.md R20 and spec 07_TELEGRAM_PARSING.md.
"""

# Primary verified layer used in current Telegram fixtures (Telethon 1.45.0)
CURRENT_VERIFIED_LAYER = 229

# Known legacy constructor IDs from older layers
CONSTRUCTOR_LAYER133_MESSAGE = 0x38114EE2

# Documented variant constructor constants (B3.2, B9.2)
CONSTRUCTOR_UNKNOWN = 0xDEADBEEF

LAYER_NOTES = {
    229: (
        "Modern MTProto layer 229 with 64-bit peer identifiers, flags2 bitmask, "
        "extended message reactions, stories, and reply headers."
    ),
    133: (
        "Legacy MTProto layer 133 with 32-bit peer identifiers and single 32-bit flags field. "
        "Emits UNPARSED_BLOB with layer_mismatch classification when encountered."
    ),
}
