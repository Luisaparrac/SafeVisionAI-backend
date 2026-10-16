-- Fictitious sample data for local development (docker compose loads it after
-- tests/integration/schema.sql). Never load it into the production database.
-- Names, the e-mail (example.com) and the IPs (192.0.2.0/24, reserved for
-- documentation) are made up. Ids are looked up by name, never hard-coded.

INSERT INTO users (name, email, password_hash)
VALUES ('Usuario de ejemplo', 'dev@example.com', 'not-a-real-hash');

INSERT INTO locations (name, description, user_id)
SELECT 'Casa de ejemplo', 'Ubicación ficticia para desarrollo', user_id
FROM users WHERE email = 'dev@example.com';

INSERT INTO cameras (name, ip_address, status, location_id)
SELECT c.name, c.ip::inet, c.status, l.location_id
FROM locations l,
     (VALUES ('Sala', '192.0.2.10', 'active'),
             ('Patio', '192.0.2.11', 'active'),
             ('Cocina', '192.0.2.12', 'maintenance')) AS c(name, ip, status)
WHERE l.name = 'Casa de ejemplo';

INSERT INTO zones (name, description, coordinates, is_active, camera_id)
SELECT 'Escalera', 'Primeros escalones', '[[0, 0], [1, 0], [1, 1], [0, 1]]'::jsonb, true, camera_id
FROM cameras WHERE name = 'Sala';

INSERT INTO subjects (name, subject_type, description, user_id)
SELECT s.name, s.kind, s.description, u.user_id
FROM users u,
     (VALUES ('Rosa', 'elderly', 'Adulta mayor ficticia'),
             ('Max', 'pet', 'Perro ficticio')) AS s(name, kind, description)
WHERE u.email = 'dev@example.com';

INSERT INTO event_types (name, description, severity_level)
VALUES ('Caída', 'Persona en el piso', 4),
       ('Humo', 'Posible incendio', 3),
       ('Merodeo', 'Persona desconocida rondando', 2),
       ('Ruido', 'Ruido fuerte sin causa visible', 1);

INSERT INTO events (occurred_at, description, status, detected_class, confidence,
                    subject_id, event_type_id, camera_id, zone_id)
SELECT now() - e.ago, e.description, e.status, e.class, e.confidence,
       s.subject_id, t.event_type_id, c.camera_id, z.zone_id
FROM (VALUES (interval '5 minutes', 'Caída cerca de la escalera', 'pending', 'person', 0.93, 'Rosa', 'Caída', 'Sala', 'Escalera'),
             (interval '40 minutes', 'Humo en la cocina', 'pending', 'person', 0.81, NULL, 'Humo', 'Cocina', NULL),
             (interval '2 hours', 'Persona rondando el patio', 'resolved', 'person', 0.77, NULL, 'Merodeo', 'Patio', NULL),
             (interval '1 day', 'Ladridos del perro', 'false_alarm', 'dog', 0.65, 'Max', 'Ruido', 'Patio', NULL))
     AS e(ago, description, status, class, confidence, subject, type, camera, zone)
JOIN event_types t ON t.name = e.type
JOIN cameras c ON c.name = e.camera
LEFT JOIN subjects s ON s.name = e.subject
LEFT JOIN zones z ON z.name = e.zone AND z.camera_id = c.camera_id;

-- One alert per event, closed ten minutes later when its event is closed.
INSERT INTO alerts (created_at, level, status, attended_at, event_id)
SELECT e.occurred_at,
       t.severity_level,
       CASE e.status WHEN 'resolved' THEN 'resolved' WHEN 'false_alarm' THEN 'dismissed' ELSE 'active' END,
       CASE WHEN e.status IN ('resolved', 'false_alarm') THEN e.occurred_at + interval '10 minutes' END,
       e.event_id
FROM events e JOIN event_types t USING (event_type_id);
