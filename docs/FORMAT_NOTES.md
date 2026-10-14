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
