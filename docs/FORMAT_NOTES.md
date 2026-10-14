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

### 4.4 TL Binary Serialization & Documented Variants (B3.2, B3.4)
MTProto TL serialization format:
1. **Header**: 4-byte little-endian constructor ID (e.g., `0x7600b9d3` for `Message`).
2. **Payload**: Binary serialized fields per TL schema specification.
3. **Documented Variants**:
   - `exact`: Standard Telethon serialized TL bytes (`bytes(msg)`). Telethon re-reads 100% of these.
   - `trailing_bytes`: Valid TL object followed by extra bookkeeping bytes (e.g., local flags). Telethon parser reads the TL object successfully and reports remaining trailing bytes.
   - `unknown_constructor`: Unregistered constructor ID (e.g. `0xDEADBEEF`), testing `UNPARSED_BLOB` error handling (`TypeNotFoundError`).
   - `older_layer`: Message constructor from a legacy layer (e.g., Layer 133 `0x38114ee2`) to test layer migration/detection.
