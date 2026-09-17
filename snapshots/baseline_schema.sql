CREATE TABLE cases (
	id SERIAL NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	investigator VARCHAR(255), 
	status VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE evidence (
	id SERIAL NOT NULL, 
	case_id INTEGER NOT NULL, 
	original_filename VARCHAR(512) NOT NULL, 
	storage_path VARCHAR(1024) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	content_type VARCHAR(255), 
	evidence_type VARCHAR(50), 
	metadata_ JSON, 
	extracted_path VARCHAR(1024), 
	uploaded_at TIMESTAMP WITHOUT TIME ZONE, 
	analyzed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id)
);

CREATE TABLE evidence_files (
	id SERIAL NOT NULL, 
	evidence_id INTEGER NOT NULL, 
	relative_path VARCHAR(1024) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	file_size INTEGER, 
	mime_type VARCHAR(255), 
	metadata_ JSON, 
	is_media BOOLEAN, 
	media_type VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE analysis_results (
	id SERIAL NOT NULL, 
	evidence_id INTEGER NOT NULL, 
	analysis_type VARCHAR(50) NOT NULL, 
	status VARCHAR(50), 
	results JSON, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE wa_messages (
	id SERIAL NOT NULL, 
	evidence_id INTEGER, 
	message_id VARCHAR(255), 
	key_remote_jid VARCHAR(255), 
	sender_jid VARCHAR(255), 
	participant_jid VARCHAR(255), 
	body TEXT, 
	timestamp BIGINT, 
	media_type VARCHAR(50), 
	media_path VARCHAR(1024), 
	message_type VARCHAR(50), 
	status VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE wa_contacts (
	id SERIAL NOT NULL, 
	evidence_id INTEGER, 
	jid VARCHAR(255), 
	display_name VARCHAR(512), 
	phone_number VARCHAR(50), 
	status TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE wa_groups (
	id SERIAL NOT NULL, 
	evidence_id INTEGER, 
	group_jid VARCHAR(255), 
	subject VARCHAR(512), 
	creator_jid VARCHAR(255), 
	creation_timestamp BIGINT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE tg_messages (
	id SERIAL NOT NULL, 
	evidence_id INTEGER, 
	message_id INTEGER, 
	dialog_id VARCHAR(255), 
	sender_id INTEGER, 
	body TEXT, 
	timestamp BIGINT, 
	media_type VARCHAR(50), 
	media_path VARCHAR(1024), 
	message_type VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE tg_contacts (
	id SERIAL NOT NULL, 
	evidence_id INTEGER, 
	user_id INTEGER, 
	first_name VARCHAR(255), 
	last_name VARCHAR(255), 
	username VARCHAR(255), 
	phone VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE tg_groups (
	id SERIAL NOT NULL, 
	evidence_id INTEGER, 
	group_id INTEGER, 
	title VARCHAR(512), 
	username VARCHAR(255), 
	type VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE timeline_events (
	id SERIAL NOT NULL, 
	case_id INTEGER, 
	evidence_id INTEGER, 
	event_type VARCHAR(50), 
	source_app VARCHAR(50), 
	timestamp BIGINT, 
	normalized_timestamp TIMESTAMP WITHOUT TIME ZONE, 
	entity_id VARCHAR(255), 
	entity_type VARCHAR(50), 
	description TEXT, 
	metadata_ JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE deleted_messages (
	id SERIAL NOT NULL, 
	case_id INTEGER, 
	evidence_id INTEGER, 
	source_app VARCHAR(50), 
	chat_jid VARCHAR(255), 
	gap_start BIGINT, 
	gap_end BIGINT, 
	missing_count INTEGER, 
	confidence_score FLOAT, 
	detection_method VARCHAR(50), 
	detected_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE media_items (
	id SERIAL NOT NULL, 
	case_id INTEGER, 
	evidence_id INTEGER, 
	file_path VARCHAR(1024), 
	sha256 VARCHAR(64), 
	mime_type VARCHAR(255), 
	media_type VARCHAR(50), 
	file_size INTEGER, 
	width INTEGER, 
	height INTEGER, 
	duration FLOAT, 
	exif_data JSON, 
	is_orphan BOOLEAN, 
	linked_message_id VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE correlation_edges (
	id SERIAL NOT NULL, 
	case_id INTEGER, 
	source_type VARCHAR(50), 
	target_type VARCHAR(50), 
	source_id VARCHAR(255), 
	target_id VARCHAR(255), 
	relation_type VARCHAR(50), 
	metadata_ JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id)
);

CREATE TABLE analysis_logs (
	id SERIAL NOT NULL, 
	evidence_id INTEGER, 
	log_type VARCHAR(50), 
	message TEXT, 
	details JSON, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE activity_logs (
	id SERIAL NOT NULL, 
	case_id INTEGER, 
	action VARCHAR(255), 
	description TEXT, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id)
);

CREATE TABLE error_logs (
	id SERIAL NOT NULL, 
	case_id INTEGER, 
	evidence_id INTEGER, 
	error_type VARCHAR(255), 
	message TEXT, 
	stack_trace TEXT, 
	endpoint VARCHAR(512), 
	method VARCHAR(10), 
	client_ip VARCHAR(50), 
	user_agent VARCHAR(512), 
	metadata_ JSON, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
);

CREATE TABLE generated_reports (
	id SERIAL NOT NULL, 
	report_id VARCHAR(64) NOT NULL, 
	case_id INTEGER NOT NULL, 
	report_type VARCHAR(50) NOT NULL, 
	lead_analyst VARCHAR(255), 
	agency VARCHAR(255), 
	case_notes TEXT, 
	sha256 VARCHAR(64) NOT NULL, 
	total_pages INTEGER, 
	size_bytes INTEGER, 
	filename VARCHAR(255) NOT NULL, 
	generated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES cases (id)
);
