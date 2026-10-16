-- Structure of the production database, without data, roles or credentials.
-- Used to verify the ORM mapping and to build the PostgreSQL test database.
CREATE TABLE users (
  user_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  email varchar NOT NULL CONSTRAINT chk_users_email CHECK (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  password_hash varchar NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE locations (
  location_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  description text,
  user_id bigint NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT uq_locations_user_name UNIQUE (user_id, name)
);
CREATE TABLE cameras (
  camera_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  ip_address inet NOT NULL,
  status varchar NOT NULL DEFAULT 'active'
    CONSTRAINT chk_cameras_status CHECK (status IN ('active','inactive','disconnected','maintenance')),
  location_id bigint NOT NULL REFERENCES locations(location_id) ON DELETE CASCADE
);
CREATE TABLE zones (
  zone_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  description text,
  coordinates jsonb NOT NULL
    CONSTRAINT chk_zones_coordinates CHECK (jsonb_typeof(coordinates) = 'array' AND jsonb_array_length(coordinates) >= 3),
  is_active boolean NOT NULL DEFAULT true,
  camera_id bigint NOT NULL REFERENCES cameras(camera_id) ON DELETE CASCADE,
  CONSTRAINT uq_zones_camera_name UNIQUE (camera_id, name)
);
CREATE TABLE subjects (
  subject_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL,
  subject_type varchar NOT NULL
    CONSTRAINT chk_subjects_type CHECK (subject_type IN ('person','child','elderly','pet')),
  description text,
  user_id bigint NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE event_types (
  event_type_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name varchar NOT NULL UNIQUE,
  description text,
  severity_level smallint NOT NULL
    CONSTRAINT chk_event_types_severity CHECK (severity_level BETWEEN 1 AND 4)
);
CREATE TABLE events (
  event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  description text,
  status varchar NOT NULL DEFAULT 'pending'
    CONSTRAINT chk_events_status CHECK (status IN ('pending','in_review','resolved','false_alarm')),
  detected_class varchar NOT NULL DEFAULT 'person'
    CONSTRAINT chk_events_class CHECK (detected_class IN ('person','dog','cat','other_animal')),
  confidence numeric CONSTRAINT chk_events_confidence CHECK (confidence >= 0 AND confidence <= 1),
  evidence_url varchar,
  subject_id bigint REFERENCES subjects(subject_id) ON DELETE SET NULL,
  event_type_id bigint NOT NULL REFERENCES event_types(event_type_id) ON DELETE RESTRICT,
  camera_id bigint NOT NULL REFERENCES cameras(camera_id) ON DELETE CASCADE,
  zone_id bigint REFERENCES zones(zone_id) ON DELETE SET NULL
);
CREATE TABLE alerts (
  alert_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now(),
  level smallint NOT NULL CONSTRAINT chk_alerts_level CHECK (level BETWEEN 1 AND 4),
  status varchar NOT NULL DEFAULT 'active'
    CONSTRAINT chk_alerts_status CHECK (status IN ('active','seen','resolved','dismissed')),
  attended_at timestamptz,
  attended_by_user_id bigint REFERENCES users(user_id) ON DELETE SET NULL,
  event_id bigint NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  CONSTRAINT chk_alerts_attended CHECK (attended_at IS NULL OR attended_at >= created_at),
  CONSTRAINT chk_alerts_closed CHECK (status NOT IN ('resolved','dismissed') OR attended_at IS NOT NULL)
);
