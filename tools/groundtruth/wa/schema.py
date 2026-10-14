"""Modern WhatsApp SQLite database schema DDL.

Follows master.md R20, docs/FORMAT_NOTES.md, and 02_GROUND_TRUTH_DATASETS.md B1.2.
"""

# Schema DDL for modern WhatsApp Android msgstore.db
MSGSTORE_SCHEMA_SQL = """
PRAGMA foreign_keys = OFF;
PRAGMA page_size = 4096;
PRAGMA user_version = 223507;

CREATE TABLE IF NOT EXISTS jid (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT NOT NULL,
    server TEXT NOT NULL,
    agent INTEGER DEFAULT 0,
    device_id INTEGER DEFAULT 0,
    type INTEGER DEFAULT 0,
    raw_string TEXT
);

CREATE TABLE IF NOT EXISTS chat (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    jid_row_id INTEGER NOT NULL REFERENCES jid(_id),
    hidden INTEGER DEFAULT 0,
    subject TEXT,
    created_timestamp INTEGER,
    last_message_row_id INTEGER,
    sort_timestamp INTEGER
);

CREATE TABLE IF NOT EXISTS message (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_row_id INTEGER NOT NULL REFERENCES chat(_id),
    from_me INTEGER NOT NULL,
    key_id TEXT NOT NULL,
    sender_jid_row_id INTEGER REFERENCES jid(_id),
    status INTEGER DEFAULT 0,
    broadcast INTEGER DEFAULT 0,
    recipient_count INTEGER DEFAULT 0,
    participant_hash TEXT,
    origination_flags INTEGER DEFAULT 0,
    origin INTEGER DEFAULT 0,
    timestamp INTEGER NOT NULL,
    received_timestamp INTEGER,
    receipt_server_timestamp INTEGER,
    message_type INTEGER DEFAULT 0,
    text_data TEXT,
    starred INTEGER DEFAULT 0,
    lookup_tables INTEGER DEFAULT 0,
    sort_id INTEGER,
    extra_guest_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS message_media (
    message_row_id INTEGER PRIMARY KEY REFERENCES message(_id),
    chat_row_id INTEGER REFERENCES chat(_id),
    file_path TEXT,
    file_size INTEGER,
    media_name TEXT,
    mime_type TEXT,
    media_url TEXT,
    file_hash TEXT,
    media_duration INTEGER,
    media_width INTEGER,
    media_height INTEGER
);

CREATE TABLE IF NOT EXISTS message_location (
    message_row_id INTEGER PRIMARY KEY REFERENCES message(_id),
    chat_row_id INTEGER REFERENCES chat(_id),
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    place_name TEXT,
    place_address TEXT,
    url TEXT,
    live_location_share_duration INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS message_quoted (
    message_row_id INTEGER PRIMARY KEY REFERENCES message(_id),
    chat_row_id INTEGER REFERENCES chat(_id),
    key_id TEXT,
    parent_key_id TEXT,
    sender_jid_row_id INTEGER REFERENCES jid(_id),
    timestamp INTEGER,
    message_type INTEGER,
    text_data TEXT
);

CREATE TABLE IF NOT EXISTS message_revoked (
    message_row_id INTEGER PRIMARY KEY REFERENCES message(_id),
    revoked_key_id TEXT NOT NULL,
    admin_jid_row_id INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS message_edit_info (
    message_row_id INTEGER PRIMARY KEY REFERENCES message(_id),
    original_key_id TEXT NOT NULL,
    edit_type INTEGER DEFAULT 1,
    original_timestamp INTEGER
);

CREATE TABLE IF NOT EXISTS group_participants (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_jid_row_id INTEGER NOT NULL REFERENCES jid(_id),
    user_jid_row_id INTEGER NOT NULL REFERENCES jid(_id),
    rank INTEGER DEFAULT 0,
    pending INTEGER DEFAULT 0
);

-- Realistic modern WhatsApp indices
CREATE INDEX IF NOT EXISTS message_key_id_index ON message (key_id);
CREATE INDEX IF NOT EXISTS message_chat_row_id_index ON message (chat_row_id);
CREATE INDEX IF NOT EXISTS message_timestamp_index ON message (timestamp);
CREATE INDEX IF NOT EXISTS jid_raw_string_index ON jid (raw_string);
CREATE INDEX IF NOT EXISTS chat_jid_row_id_index ON chat (jid_row_id);
"""

# Schema DDL for legacy WhatsApp Android wa.db
WA_DB_SCHEMA_SQL = """
PRAGMA foreign_keys = OFF;
PRAGMA page_size = 4096;

CREATE TABLE IF NOT EXISTS android_metadata (
    locale TEXT
);

CREATE TABLE IF NOT EXISTS wa_contacts (
    _id INTEGER PRIMARY KEY AUTOINCREMENT,
    jid TEXT NOT NULL UNIQUE,
    is_whatsapp_user INTEGER DEFAULT 1,
    status TEXT,
    number TEXT,
    raw_contact_id INTEGER,
    display_name TEXT NOT NULL,
    phone_label TEXT,
    given_name TEXT,
    family_name TEXT,
    sort_name TEXT
);

CREATE INDEX IF NOT EXISTS wa_contacts_jid_index ON wa_contacts (jid);
"""
