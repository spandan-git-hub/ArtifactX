# ArtifactX — File Format & Schema Technical Notes (R20 Living Document)

> Per `master.md` R20, every file-format or schema fact must be verified from primary sources (reference implementations, official documentation, or verified forensic write-ups). If unverified, mark with `TODO(verify)`.

---

## 1. WhatsApp Android Forensic Artifacts

### 1.1 Overview & Schema Evolution
- **Modern Schema (Android v2.20+ through v2.23+)**:
  The database schema transitioned from single monolithic tables (`messages`) to a normalized schema centered around `message`, `chat`, and `jid` tables.
  Primary database: `msgstore.db`.
  Optional legacy contact database: `wa.db`.

### 1.2 Table Specifications (Modern Schema)

#### Table: `jid`
Maps WhatsApp IDs (JIDs) to internal integer IDs.
- `_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `user`: TEXT NOT NULL (phone number digits in international format without `+` for individual users, e.g. `919876543210`; or group ID timestamp-creator)
- `server`: TEXT NOT NULL:
  - `s.whatsapp.net`: standard individual users
  - `g.us`: standard group chats
  - `broadcast`: status broadcasts
  - `lid`: linked device pseudo-identity
- `agent`: INTEGER DEFAULT 0
- `device_id`: INTEGER DEFAULT 0
- `type`: INTEGER DEFAULT 0 (0 = user, 1 = group, 2 = broadcast)
- `raw_string`: TEXT (denormalized full JID: `{user}@{server}`)

#### Table: `chat`
Represents an individual or group conversation.
- `_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `jid_row_id`: INTEGER NOT NULL REFERENCES `jid(_id)`
- `hidden`: INTEGER DEFAULT 0
- `subject`: TEXT (display name/title for group chats)
- `created_timestamp`: INTEGER (epoch ms)
- `last_message_row_id`: INTEGER (pointer to most recent `message._id`)
- `sort_timestamp`: INTEGER (epoch ms)

#### Table: `message`
Primary table containing chat message events.
- `_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `chat_row_id`: INTEGER NOT NULL REFERENCES `chat(_id)`
- `from_me`: INTEGER NOT NULL (1 = sent by device owner, 0 = received)
- `key_id`: TEXT NOT NULL (WhatsApp message identifier, typically alphanumeric 32-char hex or base64/hex token e.g. `3EB0...`)
- `sender_jid_row_id`: INTEGER REFERENCES `jid(_id)` (actual sender in a group chat; NULL or 0 for 1-on-1 chats where `from_me=0` implies sender is the chat partner)
- `status`: INTEGER DEFAULT 0 (0 = pending/received, 4 = sent, 5 = delivered, 13 = read)
- `broadcast`: INTEGER DEFAULT 0
- `recipient_count`: INTEGER DEFAULT 0
- `participant_hash`: TEXT
- `origination_flags`: INTEGER DEFAULT 0
- `origin`: INTEGER DEFAULT 0
- `timestamp`: INTEGER NOT NULL (epoch in milliseconds)
- `received_timestamp`: INTEGER (epoch in milliseconds when received locally)
- `receipt_server_timestamp`: INTEGER (epoch in milliseconds when server acknowledged)
- `message_type`: INTEGER DEFAULT 0
  - `0`: Plain text message
  - `1`: Image (`message_media`)
  - `2`: Audio note / recording (`message_media`)
  - `3`: Video (`message_media`)
  - `5`: Location / GPS coordinate (`message_location`)
  - `12`: Revoked message ("This message was deleted")
  - `15`: Document / file attachment
- `text_data`: TEXT (message content string for text messages; caption for media)
- `starred`: INTEGER DEFAULT 0
- `lookup_tables`: INTEGER DEFAULT 0
- `sort_id`: INTEGER

#### Table: `message_media`
Detailed metadata for attached media.
- `message_row_id`: INTEGER PRIMARY KEY REFERENCES `message(_id)`
- `chat_row_id`: INTEGER REFERENCES `chat(_id)`
- `file_path`: TEXT (local device file path, e.g., `/sdcard/WhatsApp/Media/WhatsApp Images/...`)
- `file_size`: INTEGER (size in bytes)
- `media_name`: TEXT (original filename)
- `mime_type`: TEXT (e.g., `image/jpeg`, `image/png`, `audio/ogg`, `video/mp4`)
- `media_url`: TEXT (content server URL or placeholder)
- `file_hash`: TEXT (cryptographic hash; WhatsApp uses base64 or hex SHA-256 of the media ciphertext/plaintext)
- `media_duration`: INTEGER (duration in seconds for audio/video)
- `media_width`: INTEGER (pixel width)
- `media_height`: INTEGER (pixel height)

#### Table: `message_location`
Geographical location coordinates.
- `message_row_id`: INTEGER PRIMARY KEY REFERENCES `message(_id)`
- `chat_row_id`: INTEGER REFERENCES `chat(_id)`
- `latitude`: REAL NOT NULL (WGS84 decimal latitude)
- `longitude`: REAL NOT NULL (WGS84 decimal longitude)
- `place_name`: TEXT (name of POI or location)
- `place_address`: TEXT (street / city address)
- `url`: TEXT (map link if applicable)
- `live_location_share_duration`: INTEGER DEFAULT 0

#### Table: `message_quoted`
Replies and quoted message snapshots.
- `message_row_id`: INTEGER PRIMARY KEY REFERENCES `message(_id)` (the message containing the quote)
- `chat_row_id`: INTEGER REFERENCES `chat(_id)`
- `key_id`: TEXT (key_id of the replying message)
- `parent_key_id`: TEXT (key_id of the original message that was quoted)
- `sender_jid_row_id`: INTEGER REFERENCES `jid(_id)` (sender of the quoted snippet)
- `timestamp`: INTEGER (epoch ms of the original message)
- `message_type`: INTEGER (type of original message)
- `text_data`: TEXT (content of the quoted snippet at time of quotation)

#### Table: `message_revoked`
Explicit evidence of revoked messages ("Delete for Everyone").
- `message_row_id`: INTEGER PRIMARY KEY REFERENCES `message(_id)`
- `revoked_key_id`: TEXT NOT NULL (original key_id that was revoked)
- `admin_jid_row_id`: INTEGER DEFAULT 0 (JID of group admin if revoked by admin)

#### Table: `message_edit_info`
Message edit history tracking.
- `message_row_id`: INTEGER PRIMARY KEY REFERENCES `message(_id)`
- `original_key_id`: TEXT NOT NULL
- `edit_type`: INTEGER DEFAULT 1 (1 = standard edit)
- `original_timestamp`: INTEGER (epoch ms timestamp of original unedited message)

#### Table: `group_participants`
Group membership mapping.
- `_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `group_jid_row_id`: INTEGER NOT NULL REFERENCES `jid(_id)`
- `user_jid_row_id`: INTEGER NOT NULL REFERENCES `jid(_id)`
- `rank`: INTEGER DEFAULT 0 (0 = standard member, 1 = admin, 2 = superadmin)
- `pending`: INTEGER DEFAULT 0

---

### 1.3 Legacy Database: `wa.db`
Historically stored address book contacts synchronized with WhatsApp.
#### Table: `wa_contacts`
- `_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `jid`: TEXT NOT NULL UNIQUE (e.g. `919876543210@s.whatsapp.net`)
- `is_whatsapp_user`: INTEGER DEFAULT 1
- `status`: TEXT (user about/status message)
- `number`: TEXT (original address book telephone number)
- `raw_contact_id`: INTEGER
- `display_name`: TEXT NOT NULL (address book saved contact name)
- `phone_label`: TEXT
- `given_name`: TEXT
- `family_name`: TEXT
- `sort_name`: TEXT

---

## 2. Low-Level SQLite Carving & Deletion Semantics (B1.4, B8, B10)

### 2.1 Freelist Traversal (Tier 3)
- When SQLite executes a `DELETE` on a B-tree table and `PRAGMA secure_delete=OFF` (the SQLite default), deleted records are marked free.
- If an entire page is emptied, the page is moved to the SQLite Freelist.
- The SQLite file header (bytes 32–35) stores the 4-byte big-endian page number of the first freelist trunk page, and bytes 36–39 store the count of freelist pages.
- Deleted records in freelist pages remain completely unzeroed until reclaimed by subsequent allocations or an explicit `VACUUM`.

### 2.2 Intra-Page Slack / Freeblocks (Tier 3)
- Within a B-tree leaf page, when a row is deleted without emptying the page, the space previously occupied by the cell is linked into the page's freeblock chain (header bytes 1–2 of the page point to the first freeblock offset).
- If `secure_delete=OFF`, the cell payload (content bytes) remains in unallocated space.
- Forensic carving searches page unallocated space and freeblocks for serialized SQLite record headers and string payloads.

### 2.3 Write-Ahead Log (WAL) Residency (Tier 2)
- In `journal_mode=WAL`, write operations append 4096-byte page frames to `msgstore.db-wal`.
- Each frame begins with a 24-byte frame header:
  - Bytes 0–3: Page number in main DB (big-endian 32-bit int).
  - Bytes 4–7: Commit frame marker (0 if not commit frame, or size of DB in pages after commit).
  - Bytes 8–15: Salt 1 and Salt 2.
  - Bytes 16–23: Cumulative checksums.
- Prior page versions (e.g., messages before deletion or edit) remain in `-wal` until a checkpoint occurs (`PRAGMA wal_checkpoint(TRUNCATE)`).
- Recovering uncheckpointed WAL frames yields Tier 2 temporal deletion and modification evidence.

### 2.4 Control Baselines
- **Vacuumed Control**: Running `VACUUM` defragments the database into a brand new file, leaving 0 freelist pages and zeroing unallocated slack. Records are strictly unrecoverable.
- **Secure Delete Control**: Running `PRAGMA secure_delete=ON` causes SQLite to overwrite cell payloads with zeros upon `DELETE`. Raw-byte carving yields no plaintext.
- **Benign Gap Control**: Natural sequence skips in autoincrement primary keys (`_id`) caused by aborted transactions or explicit ID assignment. Must never be classified as forensic deletion above `weak_hint` confidence.

---

## 3. WhatsApp Encrypted Backup Formats: `crypt14` & `crypt15` (B2, B6)

> Verified against primary source `wa-crypt-tools` v0.2.0 (commit `b16a805a394b8e243334f286dcf30f262e60db4f`, ElDavoo) and round-trip differential tests.

### 3.1 Container Layout
Both `crypt14` and `crypt15` backups share a common 5-part stream structure:
```
+--------------------+-------------------+--------------------+------------------+------------------+
| Varint Length (1-4B)| Protobuf Header   | AES-GCM Ciphertext | GCM Auth Tag     | MD5 Trailer      |
| len(Protobuf)      | BackupPrefix      | (zlib SQLite DB)   | (16 bytes)       | (16 bytes)       |
+--------------------+-------------------+--------------------+------------------+------------------+
```

1. **Varint Length Prefix**: Protobuf unsigned varint encoding the byte length of the serialized `BackupPrefix` protobuf message.
2. **Protobuf Header (`BackupPrefix`)**:
   - `key_type_deprecated`:
     - Value `1` (`WA_PROVIDED`) for `crypt14`.
     - Value `2` (`E2EE_DEPRECATED`) for `crypt15`.
   - In `crypt14`: `wa_provided_key_data` contains:
     - `backup_cipher_header`: 2-byte big-endian cipher version (typically `0x0001`).
     - `key_version`: ASCII string version (typically `"2"`).
     - `server_salt`: 32 bytes binary salt.
     - `google_id_salt`: 16 bytes binary Google ID salt.
     - `encryption_iv`: 16 bytes AES-GCM IV.
   - In `crypt15`: `e2ee_key_data` contains:
     - `encryption_iv`: 16 bytes AES-GCM IV.
   - Both contain `backup_metadata` (`Props`) with app version, backup version, and feature list.
3. **Payload**:
   - Plaintext SQLite `msgstore.db` is zlib-compressed before encryption.
   - Encrypted with AES-256-GCM using the 16-byte IV extracted from the header.
4. **Authentication Tag**:
   - 16 bytes standard AES-GCM authentication tag appended immediately after the ciphertext.
5. **Trailer Checksum**:
   - 16-byte MD5 digest calculated over all preceding bytes: `MD5(varint_len + protobuf_header + ciphertext + tag)`.

### 3.2 Key Derivation & Key Material
- **crypt14**:
  - Key material: Traditional `key` file (Java serialized stream, 158 bytes) extracted from rooted device path `/data/data/com.whatsapp/files/key`.
  - Cipher key: The 32-byte AES key is read directly from the key file (no derivation).
- **crypt15**:
  - Key material: Either a 64-character hexadecimal root key or binary `encrypted_backup.key` (59 bytes).
  - Cipher key derivation: Derived from the 32-byte root key via HKDF-SHA256:
    - `PRK = HMAC-SHA256(salt=b"\x00"*32, IKM=root_key)`
    - `AES_Key = HMAC-SHA256(PRK, info=b"backup encryption" || 0x01)[:32]`
  - Passphrase caveat (DEC-002): Passphrases are verified with WhatsApp cloud servers to retrieve the 64-hex root key; crypt15 cannot be decrypted offline from a password alone.

---

## 4. Telegram Android Forensic Artifacts: `cache4.db` (B3, B9)

> Verified against primary source `MessagesStorage.java` (Telegram for Android upstream / `Telegram-FOSS` v5.x-10.x, `createTables()` method) and Telethon TL schema.

### 4.1 Overview & Database Architecture
- **Primary Database**: `cache4.db` (located at `/data/data/org.telegram.messenger/files/cache4.db`).
- **Journal Mode**: SQLite WAL mode (`cache4.db-wal`, `cache4.db-shm`).
- **Database Version**: `PRAGMA user_version = 155` (`MessagesStorage.LAST_DB_VERSION`).
- **Binary Serialization**: Telegram does NOT store message bodies, sender metadata, or media details in plaintext SQL columns. Instead, message and entity records store binary MTProto Type Language (TL) objects in BLOB columns (`data`).

### 4.2 Verified Table Specifications (`MessagesStorage.java`)

#### Table: `messages_v2`
Primary message storage table:
```sql
CREATE TABLE messages_v2 (
    mid INTEGER,
    uid INTEGER,
    read_state INTEGER,
    send_state INTEGER,
    date INTEGER,
    data BLOB,
    out INTEGER,
    ttl INTEGER,
    media INTEGER,
    replydata BLOB,
    imp INTEGER,
    mention INTEGER,
    forwards INTEGER,
    replies_data BLOB,
    thread_reply_id INTEGER,
    is_channel INTEGER,
    reply_to_message_id INTEGER,
    custom_params BLOB,
    group_id INTEGER,
    reply_to_story_id INTEGER,
    PRIMARY KEY(mid, uid)
);
```
- `mid`: Message ID within the conversation (integer).
- `uid`: Dialog / Peer ID (negative for groups/channels, positive for private user chats).
- `read_state`: Read status flag (0 = unread, 1 = read).
- `send_state`: Send status flag (0 = sent, 1 = sending, 2 = failed).
- `date`: Unix epoch timestamp in seconds.
- `data`: Serialized MTProto TL object `TLRPC.Message` (prefixed with 4-byte little-endian constructor ID).
- `out`: 1 if sent by account owner, 0 if received.
- `media`: Media type indicator (0 = none, 1 = photo, 2 = video/audio/doc, etc.).
- `reply_to_message_id`: ID of parent message if this message is a reply.

#### Table: `dialogs`
Conversation index:
```sql
CREATE TABLE dialogs (
    did INTEGER PRIMARY KEY,
    date INTEGER,
    unread_count INTEGER,
    last_mid INTEGER,
    inbox_max INTEGER,
    outbox_max INTEGER,
    last_mid_i INTEGER,
    unread_count_i INTEGER,
    pts INTEGER,
    date_i INTEGER,
    pinned INTEGER,
    flags INTEGER,
    folder_id INTEGER,
    data BLOB,
    unread_reactions INTEGER,
    last_mid_group INTEGER,
    ttl_period INTEGER
);
```

#### Table: `users`
Cached user profiles:
```sql
CREATE TABLE users (
    uid INTEGER PRIMARY KEY,
    name TEXT,
    status INTEGER,
    data BLOB
);
```
- `data`: Serialized MTProto `TLRPC.User` object.

#### Table: `chats`
Cached group / supergroup / channel profiles:
```sql
CREATE TABLE chats (
    uid INTEGER PRIMARY KEY,
    name TEXT,
    data BLOB
);
```
- `data`: Serialized MTProto `TLRPC.Chat` or `TLRPC.Channel` object.

#### Table: `contacts` & `user_contacts_v7`
Synchronized device contacts:
```sql
CREATE TABLE contacts (
    uid INTEGER PRIMARY KEY,
    mutual INTEGER
);
CREATE TABLE user_contacts_v7 (
    key TEXT PRIMARY KEY,
    uid INTEGER,
    fname TEXT,
    sname TEXT,
    imported INTEGER
);
CREATE TABLE user_phones_v7 (
    key TEXT,
    phone TEXT,
    sphone TEXT,
    deleted INTEGER,
    PRIMARY KEY (key, phone)
);
```

#### Table: `media_v4`
Media attachments cache:
```sql
CREATE TABLE media_v4 (
    mid INTEGER,
    uid INTEGER,
    date INTEGER,
    type INTEGER,
    data BLOB,
    PRIMARY KEY(mid, uid, type)
);
```
- `data`: Serialized MTProto `TLRPC.MessageMedia` object.

#### Auxiliary Tables:
- `enc_chats`: Secret chat keys/state (empty in standard captures; DEC-004 notes secret chats out-of-scope).
- `params`: Synchronization parameters (`seq`, `pts`, `date`, `qts`).
- `messages_holes`: Message sequence hole tracking (`uid`, `start`, `end`).
- `scheduled_messages_v2`: Scheduled message queue.
- `chat_settings_v2`, `user_settings`: Settings blobs and pinned status.

### 4.3 Search Index Remnants: Modelled vs Observed
- **Observed reality**: Telegram Android does not create SQLite FTS3/FTS4 virtual tables in `cache4.db`. Recent searches are stored in `search_recent(did INTEGER PRIMARY KEY, date INTEGER)`, and message searches query `messages_v2` directly with tag indexes (`tag_message_id`).
- **Modelled remnant**: Any synthetic FTS table (such as `messages_search`) added to simulate full-text carving remnants is explicitly tagged as `"modelled, not observed"` in `manifest.json`.


### 4.5 Dialog ID Convention & Peer Mapping (B9.4, R20)
> Verified against Telegram Android `MessagesStorage.java`, `DialogObject.java`, and Telethon `telethon.utils.resolve_id`.
- `did >= 0`: User ID (1-on-1 private chat with peer `user_id = did`).
- `0 > did > -1000000000000`: Basic Group Chat ID (peer `chat_id = -did`).
- `did <= -1000000000000`: Channel or Supergroup ID (peer `channel_id = -did - 1000000000000`).
- Secret Chat Marker: In Telegram Android, encrypted dialogs have `(did & 0xffffffff00000000) != 0 && (did & 0xffffffff) == 0`. The encrypted chat ID is `(did >> 32)`. Per DEC-004 and B9.4, secret chat content is stored in `enc_chats` / on-device ephemeral storage and is out of scope; the parser flags the dialog as `secret_chat_marker` with limitation note.

### 4.6 MTProto TL Primitives & Supported Constructor Registry (B9.2, R20)
> Verified against MTProto schema (core.tl and telegram_api.tl, Telethon Layer 229, and MessagesStorage.java NativeByteBuffer serialization).
- **Numeric Primitives**:
  - `int32`: 4 bytes little-endian signed integer (`<i`).
  - `int64`: 8 bytes little-endian signed integer (`<q`).
  - `double`: 8 bytes IEEE 754 little-endian double (`<d`).
  - `date`: 4 bytes little-endian unsigned/signed integer representing Unix epoch in seconds.
- **Bytes / String Serialization**:
  - If length $L < 254$: 1 byte length $L$, followed by $L$ data bytes, followed by $P = (4 - ((L + 1) \pmod 4)) \pmod 4$ zero padding bytes.
  - If length $L \ge 254$: Byte `0xFE`, followed by 3 bytes little-endian length $L$, followed by $L$ data bytes, followed by $P = (4 - (L \pmod 4)) \pmod 4$ zero padding bytes.
  - Total bytes consumed is strictly aligned to a 4-byte multiple.
- **Vectors & Booleans**:
  - `Vector`: Constructor `0x1cb5c415`, followed by `int32` element count, followed by elements.
  - `boolTrue`: Constructor `0x997275b5`.
  - `boolFalse`: Constructor `0xbc799737`.
- **Supported Constructor Registry**:
  - Messages: `Message` (`0x7600b9d3`), `MessageService` (`0x7a800e0a`), `MessageEmpty` (`0x90a6ca84`).
  - Peers: `PeerUser` (`0x59511722`), `PeerChat` (`0x36c6019a`), `PeerChannel` (`0xa2a5371e`).
  - Users: `User` (`0xb1b8cc83`), `UserEmpty` (`0xd3bc4b7a`).
  - Chats: `Chat` (`0x41cbf256`), `Channel` (`0xd49f34c6`), `ChatEmpty` (`0x29562865`), `ChatForbidden` (`0x6592a1a7`).
  - Media: `MessageMediaPhoto` (`0xe216eb63`), `MessageMediaDocument` (`0x52d8ccd9`), `MessageMediaGeo` (`0x56e0d474`), `MessageMediaEmpty` (`0x3ded6320`).
  - Geo: `GeoPoint` (`0xb2a2f663`).
  - Attachments: `Photo` (`0xfb197a65`), `PhotoSize` (`0x75c78e60`), `ChatPhotoEmpty` (`0x37c1011c`), `Document` (`0x8fd4c4d8`), `DocumentAttributeAudio` (`0x9852f9c6`).
  - Headers: `MessageReplyHeader` (`0x1b97dd66`), `MessageFwdHeader` (`0x4e4df4bb`).
  - Entities: `MessageEntityBold` (`0xbd610bc9`), `MessageEntityItalic` (`0x826f8b60`), `MessageEntityCode` (`0x28a20571`), `MessageEntityPre` (`0x73924be0`), `MessageEntityUrl` (`0x6ed02538`), `MessageEntityTextUrl` (`0x76a6d327`), `MessageEntityMention` (`0xfa04579d`), `MessageEntityHashtag` (`0x6f635b0d`), `MessageEntityBotCommand` (`0x6cef8ac7`), `MessageEntityEmail` (`0x64e475c2`), `MessageEntityPhone` (`0x9b69e34b`), `MessageEntitySpoiler` (`0x32ca960f`), `MessageEntityStrike` (`0xbf0693d4`), `MessageEntityUnderline` (`0x9c4e7e8b`), `MessageEntityBlockquote` (`0xf1ccaaac`), `MessageEntityBankCard` (`0x761e6af4`), `MessageEntityUnknown` (`0xbb92ba95`).
- **Trailing Bytes & Unknown Handling**:
  - Trailing unparsed region after a successfully deserialized object is captured as `trailing_bytes` (length, sha256, first 32 bytes hex) without error.
  - Unknown constructor or mid-stream corruption produces an `UnparsedBlob` record with raw hash, preserving container column metadata.

---

## 5. Cross-Platform Entity Normalization & Checksum Specifications (B4, B12)

> Verified against BIP-173, EIP-55, ISO 7064 Mod 97-10, and standard URL/perceptual-hash specifications.

### 5.1 Bitcoin Base58Check Checksum (B4.1, B12.3)
- **Base58Check Algorithm**:
  - `data = version_byte || payload` (version 0x00 for P2PKH `1...`, 0x05 for P2SH `3...`).
  - `checksum = SHA256(SHA256(data))[:4]` (first 4 bytes of double SHA-256).
  - Encoded with Base58 alphabet `123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz`. Leading zero bytes are preserved as `'1'`.
- **Validation Rule**: Address must decode to bytes, length >= 5, and trailing 4 bytes must equal `SHA256(SHA256(payload))[:4]`.
- **Decoys**: Addresses with 1 mutated character fail checksum verification and produce 0 matches.

### 5.2 Ethereum (EVM) EIP-55 Mixed-Case Checksum (B4.1, B12.3)
- **EIP-55 Specification**:
  - Clean address hex (40 characters without `0x`, lowercased).
  - Compute Keccak-256 (SHA3) of the ASCII hex string: `hash = Keccak256(address_ascii)`.
  - For each i-th character: if `i`-th nibble of `hash >= 8`, capitalize the letter; otherwise leave lowercase.
  - Prefix with `0x`.
- **Validation Rule**: If an EVM address is mixed-case, its casing must strictly match the EIP-55 algorithm. If all-lowercase or all-uppercase, it is accepted as format-valid but flags `format_valid_no_checksum` with lower match certainty.
- **Decoys**: Flipped casing on any letter fails checksum validation and produces 0 links.

### 5.3 ISO 7064 Mod 97-10 IBAN Validation (B4.1, B12.3)
- **Mod-97 Checksum**:
  - Remove spaces and convert to uppercase.
  - Move the first 4 characters (country code + 2 check digits) to the end.
  - Replace each letter with two digits (A=10, B=11, ..., Z=35).
  - Compute integer modulo 97: `int(numeric_string) % 97 == 1`.
- **Validation Rule**: Must satisfy national length (e.g., 22 characters for Germany `DE`) and `mod 97 == 1`.
- **Decoys**: Check digit mutations fail mod-97 and produce 0 links.

### 5.4 URL Canonical Normalization (B4.1, B12.3)
- **Normalization Pipeline**:
  1. Lowercase scheme (`http`, `https`) and hostname.
  2. Strip `www.` subdomain prefix.
  3. Strip default ports (`:80` for http, `:443` for https).
  4. Strip URI fragments (`#...`).
  5. Strip trailing slash on root paths.
  6. Filter out tracking parameters: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `fbclid`, `gclid`, `ref`.
  7. Path and significant query parameters remain strictly preserved.
- **Decoys**: Identical domains with different paths (e.g. `/folder-alpha` vs `/folder-beta`) must NOT link.

### 5.5 Perceptual Image Similarity: dHash (B4.1, B12.4)
- **Difference Hash (dHash) Algorithm**:
  1. Convert image to 8-bit grayscale (`L`).
  2. Resize to 9x8 pixels (72 pixels) using Lanczos downsampling.
  3. Compare adjacent pixels across each 8-pixel row: `pixel[col] > pixel[col + 1]`.
  4. Yields 64-bit boolean hash.
  5. Distance is the Hamming distance (count of differing bits, XOR bit count).
- **Thresholds**:
  - Exact file duplicate: `match_certainty = 1.0` (SHA-256 match).
  - Near-duplicate (resize/re-encode): Hamming distance <= 4.
  - Decoys (dissimilar pattern): Hamming distance >= 10.

### 5.6 GPS Spatiotemporal Rendezvous (B4.1, B12.5)
- **Spatial Metric**: Great-circle Haversine formula on WGS84 decimal latitude and longitude.
- **Rendezvous Window**:
  - Spatial threshold: Distance <= 250 meters.
  - Temporal threshold: Absolute timestamp difference <= 2 hours (120 minutes, 7,200,000 ms).
- **Decoys**:
  - Distance > 250 m at same time -> rejected (decoy reason `rendezvous_distance_exceeded`).
  - Same place at delta > 2 hours -> rejected (decoy reason `rendezvous_time_exceeded`).
  - Different place at exact same time -> rejected (decoy reason `rendezvous_different_place`).


---

## 6. SQLite Low-Level File Format, B-Tree, and WAL Specifications (B8, R20)

> Verified against primary sources: SQLite File Format documentation (sqlite.org/fileformat2.html) and SQLite Write-Ahead Log documentation (sqlite.org/wal.html). Cross-verified with empirical tests on DS-01 and DS-05 fixtures.

### 6.1 Database Header Offsets (100 Bytes)
- **Offset 0..15**: Magic string `b"SQLite format 3\x00"` (16 bytes).
- **Offset 16..17**: Database page size (2 bytes, big-endian `>H`). Valid powers of 2 from 512 to 32768, or value `1` representing `65536`.
- **Offset 18**: File format write version (1 = legacy journal, 2 = WAL mode).
- **Offset 19**: File format read version (1 = legacy journal, 2 = WAL mode).
- **Offset 20**: Reserved space at end of each page in bytes (typically 0).
- **Offset 21**: Maximum embedded payload fraction (must be 64).
- **Offset 22**: Minimum embedded payload fraction (must be 32).
- **Offset 23**: Leaf payload fraction (must be 32).
- **Offset 24..27**: File change counter (4 bytes big-endian `>I`).
- **Offset 28..31**: Database size in pages (4 bytes big-endian `>I`). Valid if change counter == version-valid-for.
- **Offset 32..35**: Page number of first freelist trunk page (4 bytes big-endian `>I`, 0 if none).
- **Offset 36..39**: Total number of freelist pages (4 bytes big-endian `>I`).
- **Offset 40..43**: Schema cookie (4 bytes big-endian).
- **Offset 44..47**: Schema format number (1, 2, 3, or 4).
- **Offset 48..51**: Suggested page cache size.
- **Offset 52..55**: Largest root b-tree page for auto-vacuum mode (0 if inactive).
- **Offset 56..59**: Database text encoding:
  - `1`: UTF-8
  - `2`: UTF-16LE
  - `3`: UTF-16BE
- **Offset 60..63**: User version (`PRAGMA user_version`).
- **Offset 64..67**: Incremental vacuum mode flag.
- **Offset 68..71**: Application ID (`PRAGMA application_id`).
- **Offset 72..91**: Reserved for expansion (must be zero).
- **Offset 92..95**: Version-valid-for number.
- **Offset 96..99**: SQLite version number.

### 6.2 B-Tree Page Header
- Page 1 b-tree header begins at byte offset 100 (immediately following the 100-byte database header).
- For all other pages (page_num >= 2), the b-tree header begins at byte offset 0.
- **Header Fields**:
  - Byte 0: Page type flag:
    - `0x02`: Interior index page (header length 12 bytes).
    - `0x05`: Interior table page (header length 12 bytes).
    - `0x0A`: Leaf index page (header length 8 bytes).
    - `0x0D`: Leaf table page (header length 8 bytes).
  - Bytes 1..2: Byte offset of first freeblock (2 bytes big-endian, 0 if none).
  - Bytes 3..4: Number of cells stored on this page (2 bytes big-endian).
  - Bytes 5..6: Byte offset of the start of cell content area (2 bytes big-endian, value 0 means 65536).
  - Byte 7: Number of fragmented free bytes within the cell content area.
  - Bytes 8..11 (interior pages only): Page number of right-most child page (4 bytes big-endian).
- **Cell Pointer Array**: Follows immediately after the page header (`hdr_offset + hdr_size`), containing `2 * cell_count` bytes of 2-byte big-endian cell start offsets.

### 6.3 Leaf Table Cell & Spill Thresholds (§1.6)
- **Cell Layout**:
  - Varint: Payload length `P`.
  - Varint: Rowid (signed 64-bit integer; negative values converted from two's complement).
  - Local payload bytes: `local_len` bytes.
  - Optional 4-byte big-endian pointer to first overflow page if `has_overflow`.
- **Spill Formulas**:
  Let usable page size `U = page_size - reserved`.
  - `X = U - 35` (maximum payload before spill).
  - `M = ((U - 12) * 32 // 255) - 23` (minimum local payload).
  - If `P <= X`: all `P` bytes local, no overflow pointer.
  - If `P > X`:
    - `K = M + ((P - M) % (U - 4))`
    - `local_len = K if K <= X else M`
    - Remaining `P - local_len` bytes stored in linked overflow pages.
- **Overflow Page Structure**:
  - Bytes 0..3: Next overflow page number (4 bytes big-endian, 0 if last).
  - Bytes 4..`U`: Up to `U - 4` bytes of payload slice.

### 6.4 Record Decoding & Serial Types (§2.1)
- **Record Header**: Varint `H` (header size including `H` itself), followed by column serial type varints.
- **Serial Types**:
  - `0`: NULL (`None`, 0 bytes)
  - `1`: 8-bit signed int (1 byte)
  - `2`: 16-bit signed big-endian int (2 bytes)
  - `3`: 24-bit signed big-endian int with sign extension (3 bytes)
  - `4`: 32-bit signed big-endian int (4 bytes)
  - `5`: 48-bit signed big-endian int with sign extension (6 bytes)
  - `6`: 64-bit signed big-endian int (8 bytes)
  - `7`: 64-bit IEEE 754 float (8 bytes)
  - `8`: Constant integer 0 (0 bytes)
  - `9`: Constant integer 1 (0 bytes)
  - `>= 12` and even: BLOB of length `(N - 12) // 2` bytes.
  - `>= 13` and odd: TEXT of length `(N - 13) // 2` bytes, decoded per database text encoding (UTF-8, UTF-16LE, UTF-16BE); invalid bytes replaced with `\ufffd` and `has_encoding_errors=True`.

### 6.5 Freelist Traversal & Freeblocks
- **Trunk Page**:
  - Bytes 0..3: Next trunk page (4 bytes big-endian, 0 if last).
  - Bytes 4..7: Number of leaf pointers on this trunk page `L` (4 bytes big-endian).
  - Bytes 8..`8 + 4*L`: Array of 4-byte big-endian leaf page numbers.
- **Freeblock**:
  - Bytes 0..1: Next freeblock offset (2 bytes big-endian, 0 if last).
  - Bytes 2..3: Size of freeblock (2 bytes big-endian, >= 4).

### 6.6 Write-Ahead Log (WAL) Format & Views
- **WAL Header (32 bytes)**:
  - Magic: `0x377F0682` (little-endian checksums) or `0x377F0683` (big-endian checksums).
  - Version: 3007000 (`WAL_VERSION`).
  - Page size, sequence number, salt-1, salt-2 (big-endian 32-bit integers).
  - Checksum-1, Checksum-2 (stored in byte order matching magic).
- **Frame Header (24 bytes)**:
  - Page number (4 bytes big-endian).
  - Commit size (4 bytes big-endian; non-zero indicates a commit frame).
  - Salt-1, Salt-2 (must match header; mismatch indicates stale generation from earlier WAL cycle).
  - Checksum-1, Checksum-2 (cumulative running checksum).
- **Checksum Algorithm**:
  - Evaluated in 8-byte steps (`>II` if big-endian magic, `<II` if little-endian magic).
  - `s1 = (s1 + v0 + s2) & 0xFFFFFFFF`, `s2 = (s2 + v1 + s1) & 0xFFFFFFFF`.
  - Frame input: First 8 bytes of frame header (`page_number` + `commit_size`) concatenated with all `page_size` bytes of page payload.
- **Views**:
  - `main_view`: Main database file bytes alone.
  - `post_wal_view`: Main database with latest committed valid WAL frames applied in-memory, updating database size in pages if commits grew the table.


