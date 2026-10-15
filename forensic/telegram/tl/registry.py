"""
MTProto Supported TL Constructor Registry & Deserializers (spec B9.2).

Dispatches 4-byte constructor IDs to specialized deserializer functions.
Follows master.md R4, R12 (hostile-input hardening), and R18.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from forensic.telegram.tl.reader import TLBoundsError, TLConstructorNotFoundError, TLReader
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


def _parse_peer_user(reader: TLReader) -> TgPeer:
    user_id = reader.read_long()
    return TgPeer(peer_kind="user", peer_id=user_id)


def _parse_peer_chat(reader: TLReader) -> TgPeer:
    chat_id = reader.read_long()
    return TgPeer(peer_kind="chat", peer_id=chat_id)


def _parse_peer_channel(reader: TLReader) -> TgPeer:
    channel_id = reader.read_long()
    return TgPeer(peer_kind="channel", peer_id=channel_id)


def _parse_geo_point(reader: TLReader) -> TgMediaGeo:
    flags = reader.read_int()
    longitude = reader.read_double()
    latitude = reader.read_double()
    _access_hash = reader.read_long()
    accuracy = reader.read_int() if (flags & 1) else None
    return TgMediaGeo(latitude=latitude, longitude=longitude, accuracy_radius=accuracy)


def _parse_photo_size(reader: TLReader) -> Tuple[int, int, int]:
    _ptype = reader.read_string()
    w = reader.read_int()
    h = reader.read_int()
    sz = reader.read_int()
    return (w, h, sz)


def _parse_photo(reader: TLReader) -> TgMediaPhoto:
    flags = reader.read_int()
    _has_stickers = bool(flags & 1)
    photo_id = reader.read_long()
    access_hash = reader.read_long()
    file_reference = reader.read_bytes()
    _date = reader.read_date()
    sizes = reader.read_object()
    if flags & 2:
        _video_sizes = reader.read_object()
    _dc_id = reader.read_int()

    width, height, file_size = None, None, None
    if isinstance(sizes, list) and sizes:
        for s in sizes:
            if isinstance(s, tuple) and len(s) == 3:
                width, height, file_size = s

    return TgMediaPhoto(
        photo_id=photo_id,
        access_hash=access_hash,
        file_reference=file_reference,
        width=width,
        height=height,
        file_size=file_size,
    )


def _parse_doc_attr_audio(reader: TLReader) -> Dict[str, Any]:
    flags = reader.read_int()
    voice = bool(flags & 1024)
    duration = reader.read_int()
    title = reader.read_string() if (flags & 1) else None
    _performer = reader.read_string() if (flags & 2) else None
    _waveform = reader.read_bytes() if (flags & 4) else None
    return {"voice": voice, "duration": duration, "title": title}


def _parse_doc_attr_filename(reader: TLReader) -> Dict[str, Any]:
    file_name = reader.read_string()
    return {"file_name": file_name}


def _parse_doc_attr_image_size(reader: TLReader) -> Dict[str, Any]:
    w = reader.read_int()
    h = reader.read_int()
    return {"width": w, "height": h}


def _parse_doc_attr_video(reader: TLReader) -> Dict[str, Any]:
    flags = reader.read_int()
    round_msg = bool(flags & 1)
    duration = int(reader.read_double())
    w = reader.read_int()
    h = reader.read_int()
    if flags & 4:
        _preload = reader.read_int()
    if flags & 16:
        _codec = reader.read_string()
    return {"round": round_msg, "duration": duration, "width": w, "height": h}


def _parse_document(reader: TLReader) -> TgMediaDocument:
    flags = reader.read_int()
    doc_id = reader.read_long()
    access_hash = reader.read_long()
    file_reference = reader.read_bytes()
    _date = reader.read_date()
    mime_type = reader.read_string()
    size = reader.read_long()
    if flags & 1:
        _thumbs = reader.read_object()
    if flags & 2:
        _vthumbs = reader.read_object()
    _dc_id = reader.read_int()
    attributes = reader.read_object()

    voice = False
    duration = None
    file_name = None
    if isinstance(attributes, list):
        for attr in attributes:
            if isinstance(attr, dict):
                if attr.get("voice"):
                    voice = True
                if "duration" in attr and attr["duration"] is not None:
                    duration = int(attr["duration"])
                if "file_name" in attr and attr["file_name"] is not None:
                    file_name = attr["file_name"]

    return TgMediaDocument(
        doc_id=doc_id,
        access_hash=access_hash,
        file_reference=file_reference,
        mime_type=mime_type,
        file_size=size,
        voice=voice,
        duration=duration,
        file_name=file_name,
    )


def _parse_media_photo(reader: TLReader) -> TgMediaPhoto:
    flags = reader.read_int()
    _spoiler = bool(flags & 8)
    _live_photo = bool(flags & 16)
    photo = reader.read_object() if (flags & 1) else None
    _ttl = reader.read_int() if (flags & 4) else None
    if flags & 16:
        _video = reader.read_object()
    if isinstance(photo, TgMediaPhoto):
        return photo
    return TgMediaPhoto()


def _parse_media_document(reader: TLReader) -> TgMediaDocument:
    flags = reader.read_int()
    _nopremium = bool(flags & 8)
    _spoiler = bool(flags & 16)
    _video = bool(flags & 64)
    _round = bool(flags & 128)
    voice = bool(flags & 256)
    document = reader.read_object() if (flags & 1) else None
    if flags & 32:
        _alts = reader.read_object()
    if flags & 512:
        _cover = reader.read_object()
    if flags & 1024:
        _ts = reader.read_int()
    if flags & 4:
        _ttl = reader.read_int()

    if isinstance(document, TgMediaDocument):
        if voice and not document.voice:
            document = TgMediaDocument(
                doc_id=document.doc_id,
                access_hash=document.access_hash,
                file_reference=document.file_reference,
                mime_type=document.mime_type,
                file_size=document.file_size,
                voice=True,
                duration=document.duration,
                file_name=document.file_name,
            )
        return document
    return TgMediaDocument(voice=voice)


def _parse_media_geo(reader: TLReader) -> TgMediaGeo:
    geo = reader.read_object()
    if isinstance(geo, TgMediaGeo):
        return geo
    return TgMediaGeo(0.0, 0.0)


def _parse_media_empty(reader: TLReader) -> TgMediaEmpty:
    return TgMediaEmpty()


def _parse_reply_header(reader: TLReader) -> TgReplyHeader:
    flags = reader.read_int()
    _reply_to_scheduled = bool(flags & 4)
    _forum_topic = bool(flags & 8)
    _quote = bool(flags & 512)
    _reply_to_ephemeral = bool(flags & 8192)
    reply_to_msg_id = reader.read_int() if (flags & 16) else None
    reply_to_peer_id = reader.read_object() if (flags & 1) else None
    _reply_from = reader.read_object() if (flags & 32) else None
    _reply_media = reader.read_object() if (flags & 256) else None
    _reply_to_top_id = reader.read_int() if (flags & 2) else None
    quote_text = reader.read_string() if (flags & 64) else None
    if flags & 128:
        _quote_entities = reader.read_object()
    if flags & 1024:
        _quote_offset = reader.read_int()
    if flags & 2048:
        _todo_id = reader.read_int()
    if flags & 4096:
        _poll_opt = reader.read_bytes()

    peer_obj = reply_to_peer_id if isinstance(reply_to_peer_id, TgPeer) else None
    return TgReplyHeader(
        reply_to_msg_id=reply_to_msg_id,
        reply_to_peer=peer_obj,
        quote_text=quote_text,
    )


def _parse_fwd_header(reader: TLReader) -> TgForward:
    flags = reader.read_int()
    _imported = bool(flags & 128)
    _saved_out = bool(flags & 2048)
    from_id = reader.read_object() if (flags & 1) else None
    from_name = reader.read_string() if (flags & 32) else None
    date = reader.read_date()
    channel_post = reader.read_int() if (flags & 4) else None
    _post_author = reader.read_string() if (flags & 8) else None
    if flags & 16:
        _saved_peer = reader.read_object()
        _saved_mid = reader.read_int()
    if flags & 256:
        _saved_from_id = reader.read_object()
    if flags & 512:
        _saved_from_name = reader.read_string()
    if flags & 1024:
        _saved_date = reader.read_date()
    if flags & 64:
        _psa = reader.read_string()

    peer_obj = from_id if isinstance(from_id, TgPeer) else None
    return TgForward(
        date=date,
        from_peer=peer_obj,
        from_name=from_name,
        channel_post=channel_post,
    )


def _parse_entity_simple(entity_type: str) -> Callable[[TLReader], TgEntity]:
    def parser(reader: TLReader) -> TgEntity:
        offset = reader.read_int()
        length = reader.read_int()
        return TgEntity(entity_type=entity_type, offset=offset, length=length)
    return parser


def _parse_entity_pre(reader: TLReader) -> TgEntity:
    offset = reader.read_int()
    length = reader.read_int()
    _lang = reader.read_string()
    return TgEntity(entity_type="pre", offset=offset, length=length)


def _parse_entity_text_url(reader: TLReader) -> TgEntity:
    offset = reader.read_int()
    length = reader.read_int()
    url = reader.read_string()
    return TgEntity(entity_type="text_url", offset=offset, length=length, url=url)


def _parse_entity_mention_name(reader: TLReader) -> TgEntity:
    offset = reader.read_int()
    length = reader.read_int()
    uid = reader.read_long()
    return TgEntity(entity_type="mention_name", offset=offset, length=length, user_id=uid)


def _parse_message(reader: TLReader) -> TgMessage:
    flags = reader.read_int()
    out = bool(flags & 2)
    _mentioned = bool(flags & 16)
    _media_unread = bool(flags & 32)
    _silent = bool(flags & 8192)
    _post = bool(flags & 16384)
    _from_scheduled = bool(flags & 262144)
    _legacy = bool(flags & 524288)
    _edit_hide = bool(flags & 2097152)
    _pinned = bool(flags & 16777216)
    _noforwards = bool(flags & 67108864)
    _invert_media = bool(flags & 134217728)

    flags2 = reader.read_int()
    _offline = bool(flags2 & 2)
    _video_proc = bool(flags2 & 16)
    _paid_stars = bool(flags2 & 256)
    _paid_ton = bool(flags2 & 512)

    msg_id = reader.read_int()
    from_id = reader.read_object() if (flags & 256) else None
    if flags & 536870912:
        _boosts = reader.read_int()
    if flags2 & 4096:
        _rank = reader.read_string()
    peer_id = reader.read_object()
    if flags & 268435456:
        _saved_peer = reader.read_object()
    fwd_from = reader.read_object() if (flags & 4) else None
    if flags & 2048:
        _via_bot = reader.read_long()
    if flags2 & 1:
        _via_biz_bot = reader.read_long()
    if flags2 & 524288:
        _guestchat = reader.read_object()
    reply_to = reader.read_object() if (flags & 8) else None
    date = reader.read_date()
    message = reader.read_string()
    media = reader.read_object() if (flags & 512) else None
    if flags & 64:
        _reply_markup = reader.read_object()
    entities = reader.read_object() if (flags & 128) else None
    if flags & 1024:
        _views = reader.read_int()
        _forwards = reader.read_int()
    if flags & 8388608:
        _replies = reader.read_object()
    edit_date = reader.read_date() if (flags & 32768) else None
    if flags & 65536:
        _author = reader.read_string()
    grouped_id = reader.read_long() if (flags & 131072) else None
    if flags & 1048576:
        _reactions = reader.read_object()
    if flags & 4194304:
        _restr = reader.read_object()
    if flags & 33554432:
        _ttl = reader.read_int()
    if flags & 1073741824:
        _shortcut = reader.read_int()
    if flags2 & 4:
        _effect = reader.read_long()
    if flags2 & 8:
        _factcheck = reader.read_object()
    if flags2 & 32:
        _report_deliv = reader.read_date()
    if flags2 & 64:
        _paid_msg_stars = reader.read_long()
    if flags2 & 128:
        _suggested_post = reader.read_object()
    if flags2 & 1024:
        _schedule_repeat = reader.read_int()
    if flags2 & 2048:
        _summary = reader.read_string()
    if flags2 & 8192:
        _rich_msg = reader.read_object()

    # Capture any trailing bookkeeping bytes (B9.2)
    trailing = reader.remaining_bytes() if reader.remaining() > 0 else None

    peer_obj = peer_id if isinstance(peer_id, TgPeer) else TgPeer("user", 0)
    from_peer_obj = from_id if isinstance(from_id, TgPeer) else None
    reply_obj = reply_to if isinstance(reply_to, TgReplyHeader) else None
    fwd_obj = fwd_from if isinstance(fwd_from, TgForward) else None
    ent_list = tuple(entities) if isinstance(entities, list) else None

    return TgMessage(
        id=msg_id,
        peer=peer_obj,
        from_peer=from_peer_obj,
        date=date,
        message=message,
        out=out,
        media=media,
        reply_to=reply_obj,
        entities=ent_list,
        fwd_from=fwd_obj,
        edit_date=edit_date,
        grouped_id=grouped_id,
        trailing_bytes=trailing,
        flags=flags,
        flags2=flags2,
    )


def _parse_message_service(reader: TLReader) -> TgMessageService:
    flags = reader.read_int()
    out = bool(flags & 2)
    _mentioned = bool(flags & 16)
    _media_unread = bool(flags & 32)
    _reactions_poss = bool(flags & 512)
    _silent = bool(flags & 8192)
    _post = bool(flags & 16384)
    _legacy = bool(flags & 524288)
    msg_id = reader.read_int()
    from_id = reader.read_object() if (flags & 256) else None
    peer_id = reader.read_object()
    if flags & 268435456:
        _saved_peer = reader.read_object()
    if flags & 8:
        _reply_to = reader.read_object()
    date = reader.read_date()
    action = reader.read_object()
    if flags & 1048576:
        _reactions = reader.read_object()
    if flags & 33554432:
        _ttl = reader.read_int()

    trailing = reader.remaining_bytes() if reader.remaining() > 0 else None
    peer_obj = peer_id if isinstance(peer_id, TgPeer) else TgPeer("user", 0)
    from_peer_obj = from_id if isinstance(from_id, TgPeer) else None
    action_type = str(action) if action is not None else "service"

    return TgMessageService(
        id=msg_id,
        peer=peer_obj,
        from_peer=from_peer_obj,
        date=date,
        out=out,
        action_type=action_type,
        trailing_bytes=trailing,
    )


def _parse_message_empty(reader: TLReader) -> TgMessageEmpty:
    flags = reader.read_int()
    msg_id = reader.read_int()
    peer_id = reader.read_object() if (flags & 1) else None
    peer_obj = peer_id if isinstance(peer_id, TgPeer) else None
    return TgMessageEmpty(id=msg_id, peer=peer_obj)


def _parse_user(reader: TLReader) -> TgUser:
    flags = reader.read_int()
    is_self = bool(flags & 1024)
    contact = bool(flags & 2048)
    _mutual_contact = bool(flags & 4096)
    deleted = bool(flags & 8192)
    bot = bool(flags & 16384)
    flags2 = reader.read_int()

    user_id = reader.read_long()
    _access_hash = reader.read_long() if (flags & 1) else None
    first_name = reader.read_string() if (flags & 2) else None
    last_name = reader.read_string() if (flags & 4) else None
    username = reader.read_string() if (flags & 8) else None
    phone = reader.read_string() if (flags & 16) else None
    if flags & 32:
        _photo = reader.read_object()
    if flags & 64:
        _status = reader.read_object()
    if flags & 16384:
        _bot_info = reader.read_int()
    if flags & 262144:
        _restr = reader.read_object()
    if flags & 524288:
        _placeholder = reader.read_string()
    if flags & 4194304:
        _lang = reader.read_string()
    if flags & 1073741824:
        _emoji = reader.read_object()
    if flags2 & 1:
        _usernames = reader.read_object()
    if flags2 & 32:
        _stories = reader.read_object()
    if flags2 & 256:
        _color = reader.read_object()
    if flags2 & 512:
        _pcolor = reader.read_object()
    if flags2 & 4096:
        _active = reader.read_int()
    if flags2 & 16384:
        _vicon = reader.read_long()
    if flags2 & 32768:
        _paid_stars = reader.read_long()
    if flags2 & 2097152:
        _comm_id = reader.read_long()

    trailing = reader.remaining_bytes() if reader.remaining() > 0 else None

    return TgUser(
        id=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        phone=phone,
        is_self=is_self,
        contact=contact,
        deleted=deleted,
        bot=bot,
        trailing_bytes=trailing,
    )


def _parse_user_empty(reader: TLReader) -> TgUserEmpty:
    user_id = reader.read_long()
    return TgUserEmpty(id=user_id)


def _parse_chat(reader: TLReader) -> TgChat:
    flags = reader.read_int()
    creator = bool(flags & 1)
    left = bool(flags & 4)
    deactivated = bool(flags & 32)
    chat_id = reader.read_long()
    title = reader.read_string()
    _photo = reader.read_object()
    participants_count = reader.read_int()
    date = reader.read_date()
    _version = reader.read_int()
    if flags & 64:
        _migrated = reader.read_object()
    if flags & 16384:
        _admin_rights = reader.read_object()
    if flags & 262144:
        _default_banned = reader.read_object()

    trailing = reader.remaining_bytes() if reader.remaining() > 0 else None

    return TgChat(
        id=chat_id,
        title=title,
        participants_count=participants_count,
        date=date,
        creator=creator,
        left=left,
        deactivated=deactivated,
        trailing_bytes=trailing,
    )


def _parse_channel(reader: TLReader) -> TgChannel:
    flags = reader.read_int()
    creator = bool(flags & 1)
    left = bool(flags & 4)
    broadcast = bool(flags & 32)
    _verified = bool(flags & 128)
    megagroup = bool(flags & 256)
    _restricted = bool(flags & 512)
    flags2 = reader.read_int()

    channel_id = reader.read_long()
    if flags & 8192:
        _access_hash = reader.read_long()
    title = reader.read_string()
    username = reader.read_string() if (flags & 64) else None
    _photo = reader.read_object()
    date = reader.read_date()
    if flags & 512:
        _restr = reader.read_object()
    if flags & 16384:
        _admin_rights = reader.read_object()
    if flags & 32768:
        _banned_rights = reader.read_object()
    if flags & 262144:
        _default_banned = reader.read_object()
    participants_count = reader.read_int() if (flags & 131072) else None
    if flags2 & 1:
        _usernames = reader.read_object()
    if flags2 & 16:
        _stories = reader.read_object()
    if flags2 & 128:
        _color = reader.read_object()
    if flags2 & 256:
        _pcolor = reader.read_object()
    if flags2 & 512:
        _emoji = reader.read_object()
    if flags2 & 1024:
        _level = reader.read_int()
    if flags2 & 2048:
        _sub_until = reader.read_date()
    if flags2 & 8192:
        _vicon = reader.read_long()
    if flags2 & 16384:
        _paid_stars = reader.read_long()
    if flags2 & 262144:
        _monoforum = reader.read_long()
    if flags2 & 1048576:
        _comm_id = reader.read_long()

    trailing = reader.remaining_bytes() if reader.remaining() > 0 else None

    return TgChannel(
        id=channel_id,
        title=title,
        username=username,
        participants_count=participants_count,
        date=date,
        creator=creator,
        left=left,
        broadcast=broadcast,
        megagroup=megagroup,
        trailing_bytes=trailing,
    )


def _parse_chat_empty(reader: TLReader) -> TgChatEmpty:
    chat_id = reader.read_long()
    return TgChatEmpty(id=chat_id)


def _parse_chat_forbidden(reader: TLReader) -> TgChatForbidden:
    chat_id = reader.read_long()
    title = reader.read_string()
    return TgChatForbidden(id=chat_id, title=title)


def _parse_generic_action(action_name: str) -> Callable[[TLReader], str]:
    def parser(reader: TLReader) -> str:
        return action_name
    return parser


def build_supported_registry() -> Dict[int, Callable[[TLReader], Any]]:
    """Build the dictionary of supported MTProto constructor deserializers."""
    registry: Dict[int, Callable[[TLReader], Any]] = {
        # Peers
        0x59511722: _parse_peer_user,
        0x36C6019A: _parse_peer_chat,
        0xA2A5371E: _parse_peer_channel,
        # Geo
        0xB2A2F663: _parse_geo_point,
        # Photos & Sizes
        0x75C78E60: _parse_photo_size,
        0x37C1011C: lambda r: None,  # ChatPhotoEmpty
        0xFB197A65: _parse_photo,
        # Documents & Attributes
        0x9852F9C6: _parse_doc_attr_audio,
        0x15590068: _parse_doc_attr_filename,
        0x6C37C15C: _parse_doc_attr_image_size,
        0x43C57C48: _parse_doc_attr_video,
        0x11B58939: lambda r: {},     # DocumentAttributeAnimated
        0x8FD4C4D8: _parse_document,
        # Media Attachments
        0xE216EB63: _parse_media_photo,
        0x52D8CCD9: _parse_media_document,
        0x56E0D474: _parse_media_geo,
        0x3DED6320: _parse_media_empty,
        # Headers
        0x1B97DD66: _parse_reply_header,
        0x4E4DF4BB: _parse_fwd_header,
        # Messages
        0x7600B9D3: _parse_message,
        0x7A800E0A: _parse_message_service,
        0x90A6CA84: _parse_message_empty,
        # Users
        0xB1B8CC83: _parse_user,
        0xD3BC4B7A: _parse_user_empty,
        # Chats & Channels
        0x41CBF256: _parse_chat,
        0xD49F34C6: _parse_channel,
        0x29562865: _parse_chat_empty,
        0x6592A1A7: _parse_chat_forbidden,
        # Message Entities
        0xBD610BC9: _parse_entity_simple("bold"),
        0x826F8B60: _parse_entity_simple("italic"),
        0x28A20571: _parse_entity_simple("code"),
        0x73924BE0: _parse_entity_pre,
        0x6ED02538: _parse_entity_simple("url"),
        0x76A6D327: _parse_entity_text_url,
        0xFA04579D: _parse_entity_simple("mention"),
        0xDC7B1140: _parse_entity_mention_name,
        0x6F635B0D: _parse_entity_simple("hashtag"),
        0x6CEF8AC7: _parse_entity_simple("bot_command"),
        0x64E475C2: _parse_entity_simple("email"),
        0x9B69E34B: _parse_entity_simple("phone"),
        0x32CA960F: _parse_entity_simple("spoiler"),
        0xBF0693D4: _parse_entity_simple("strike"),
        0x9C4E7E8B: _parse_entity_simple("underline"),
        0xF1CCAAAC: _parse_entity_simple("blockquote"),
        0x761E6AF4: _parse_entity_simple("bank_card"),
        0xBB92BA95: _parse_entity_simple("unknown"),
        # Message Actions (Common)
        0xB6AEF7B0: _parse_generic_action("empty"),
        0xBD47CBAD: _parse_generic_action("chat_create"),
        0xB5A1CE5A: _parse_generic_action("chat_edit_title"),
        0x94BD38ED: _parse_generic_action("pin_message"),
        0x95D2AC92: _parse_generic_action("channel_create"),
        0x15CEFD00: _parse_generic_action("chat_add_user"),
        0xA43F30CC: _parse_generic_action("chat_delete_user"),
    }
    return registry


# Module-level default registry instance
SUPPORTED_REGISTRY = build_supported_registry()


def deserialize_tl_blob(
    data: bytes,
    registry: Optional[Dict[int, Callable[[TLReader], Any]]] = None,
) -> Any:
    """
    Convenience function to deserialize a TL blob buffer into a typed dataclass.
    Raises TLError if corrupted or unknown constructor.
    """
    reg = registry if registry is not None else SUPPORTED_REGISTRY
    reader = TLReader(data, registry=reg)
    return reader.read_object()
