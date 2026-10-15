"""
MTProto Type Language (TL) Deserialization Subpackage (spec B9.2).
"""

from forensic.telegram.tl.reader import (
    TLBoundsError,
    TLConstructorNotFoundError,
    TLError,
    TLReader,
    TLRecursionLimitError,
)
from forensic.telegram.tl.registry import (
    SUPPORTED_REGISTRY,
    build_supported_registry,
    deserialize_tl_blob,
)
from forensic.telegram.tl.types import (
    TgChannel,
    TgChat,
    TgChatEmpty,
    TgChatForbidden,
    TgEntity,
    TgForward,
    TgMediaDocument,
    TgMediaEmpty,
    TgMediaGeo,
    TgMediaPhoto,
    TgMessage,
    TgMessageEmpty,
    TgMessageService,
    TgPeer,
    TgReplyHeader,
    TgUser,
    TgUserEmpty,
)

__all__ = [
    "TLBoundsError",
    "TLConstructorNotFoundError",
    "TLError",
    "TLReader",
    "TLRecursionLimitError",
    "SUPPORTED_REGISTRY",
    "build_supported_registry",
    "deserialize_tl_blob",
    "TgChannel",
    "TgChat",
    "TgChatEmpty",
    "TgChatForbidden",
    "TgEntity",
    "TgForward",
    "TgMediaDocument",
    "TgMediaEmpty",
    "TgMediaGeo",
    "TgMediaPhoto",
    "TgMessage",
    "TgMessageEmpty",
    "TgMessageService",
    "TgPeer",
    "TgReplyHeader",
    "TgUser",
    "TgUserEmpty",
]
