-- ============================================================
-- CROWD MANAGEMENT SYSTEM - COMPLETE SAMPLE DATA
-- PostgreSQL / pgAdmin INSERT Script
-- Run this ENTIRE script in pgAdmin Query Tool
-- ============================================================

-- ============================================================
-- STEP 1: CLEANUP (Optional - run if you want fresh data)
-- ============================================================
/*
TRUNCATE TABLE snapshots, notifications, events, alerts, queue_snapshots,
  rois, face_detection_logs, entry_exit_counts, camera_health, zone_counts,
  queues, cameras, user_roles, role_permissions, audit_logs,
  criminal_watchlist, ai_models, zones, camera_groups, system_settings,
  service_statuses, permissions, roles, users
CASCADE;
*/

-- ============================================================
-- STEP 2: ROLES
-- ============================================================
INSERT INTO roles (id, name, description, is_active, created_at, updated_at)
VALUES
  ('11111111-0000-0000-0000-000000000001', 'SuperAdmin',    'Full system access',              TRUE, NOW(), NOW()),
  ('11111111-0000-0000-0000-000000000002', 'Admin',         'Administrative access',           TRUE, NOW(), NOW()),
  ('11111111-0000-0000-0000-000000000003', 'Operator',      'Camera and zone operations',      TRUE, NOW(), NOW()),
  ('11111111-0000-0000-0000-000000000004', 'Viewer',        'Read-only dashboard access',      TRUE, NOW(), NOW()),
  ('11111111-0000-0000-0000-000000000005', 'SecurityGuard', 'Alert response and monitoring',   TRUE, NOW(), NOW());

-- ============================================================
-- STEP 3: PERMISSIONS
-- ============================================================
INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
VALUES
  ('22222222-0000-0000-0000-000000000001', 'cameras.view',    'cameras',    'READ',   'View cameras',         NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000002', 'cameras.manage',  'cameras',    'WRITE',  'Manage cameras',       NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000003', 'zones.view',      'zones',      'READ',   'View zones',           NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000004', 'zones.manage',    'zones',      'WRITE',  'Manage zones',         NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000005', 'alerts.view',     'alerts',     'READ',   'View alerts',          NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000006', 'alerts.manage',   'alerts',     'WRITE',  'Manage alerts',        NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000007', 'users.view',      'users',      'READ',   'View users',           NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000008', 'users.manage',    'users',      'WRITE',  'Manage users',         NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000009', 'watchlist.view',  'watchlist',  'READ',   'View watchlist',       NOW(), NOW()),
  ('22222222-0000-0000-0000-000000000010', 'watchlist.manage','watchlist',  'WRITE',  'Manage watchlist',     NOW(), NOW());

-- ============================================================
-- STEP 4: ROLE PERMISSIONS (link roles to permissions)
-- ============================================================
-- SuperAdmin gets all
INSERT INTO role_permissions (role_id, permission_id) VALUES
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000001'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000002'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000003'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000004'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000005'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000006'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000007'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000008'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000009'),
  ('11111111-0000-0000-0000-000000000001','22222222-0000-0000-0000-000000000010');
-- Admin gets cameras, zones, alerts, watchlist (not user manage)
INSERT INTO role_permissions (role_id, permission_id) VALUES
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000001'),
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000002'),
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000003'),
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000004'),
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000005'),
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000006'),
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000007'),
  ('11111111-0000-0000-0000-000000000002','22222222-0000-0000-0000-000000000009');
-- Viewer gets view-only
INSERT INTO role_permissions (role_id, permission_id) VALUES
  ('11111111-0000-0000-0000-000000000004','22222222-0000-0000-0000-000000000001'),
  ('11111111-0000-0000-0000-000000000004','22222222-0000-0000-0000-000000000003'),
  ('11111111-0000-0000-0000-000000000004','22222222-0000-0000-0000-000000000005');

-- ============================================================
-- STEP 5: USERS
-- NOTE: hashed_password below = bcrypt hash of "Password@123"
-- ============================================================
INSERT INTO users (id, username, email, full_name, hashed_password, phone, department, status, is_superuser, last_login, created_at, updated_at)
VALUES
  ('33333333-0000-0000-0000-000000000001', 'admin',       'admin@crowdmgmt.com',    'System Admin',       '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '+91-9876543210', 'IT Security',     'ACTIVE', TRUE,  NOW() - INTERVAL '1 hour',   NOW(), NOW()),
  ('33333333-0000-0000-0000-000000000002', 'john.ops',    'john@crowdmgmt.com',     'John Operator',      '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '+91-9876543211', 'Operations',      'ACTIVE', FALSE, NOW() - INTERVAL '2 hours',  NOW(), NOW()),
  ('33333333-0000-0000-0000-000000000003', 'priya.view',  'priya@crowdmgmt.com',    'Priya Viewer',       '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '+91-9876543212', 'Security',        'ACTIVE', FALSE, NOW() - INTERVAL '30 mins',  NOW(), NOW()),
  ('33333333-0000-0000-0000-000000000004', 'ravi.guard',  'ravi@crowdmgmt.com',     'Ravi Guard',         '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '+91-9876543213', 'Security Guard',  'ACTIVE', FALSE, NOW() - INTERVAL '15 mins',  NOW(), NOW()),
  ('33333333-0000-0000-0000-000000000005', 'meena.admin', 'meena@crowdmgmt.com',    'Meena Admin',        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '+91-9876543214', 'Administration',  'ACTIVE', FALSE, NOW() - INTERVAL '3 hours',  NOW(), NOW()),
  ('33333333-0000-0000-0000-000000000006', 'suresh.ops',  'suresh@crowdmgmt.com',   'Suresh Operator',    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '+91-9876543215', 'Operations',      'INACTIVE', FALSE, NULL,                         NOW(), NOW());

-- ============================================================
-- STEP 6: USER ROLES (link users to roles)
-- ============================================================
INSERT INTO user_roles (user_id, role_id) VALUES
  ('33333333-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000001'), -- admin -> SuperAdmin
  ('33333333-0000-0000-0000-000000000002', '11111111-0000-0000-0000-000000000003'), -- john.ops -> Operator
  ('33333333-0000-0000-0000-000000000003', '11111111-0000-0000-0000-000000000004'), -- priya.view -> Viewer
  ('33333333-0000-0000-0000-000000000004', '11111111-0000-0000-0000-000000000005'), -- ravi.guard -> SecurityGuard
  ('33333333-0000-0000-0000-000000000005', '11111111-0000-0000-0000-000000000002'), -- meena.admin -> Admin
  ('33333333-0000-0000-0000-000000000006', '11111111-0000-0000-0000-000000000003'); -- suresh.ops -> Operator

-- ============================================================
-- STEP 7: ZONES
-- ============================================================
INSERT INTO zones (id, name, description, location, capacity, warning_threshold, critical_threshold, is_active, created_at, updated_at)
VALUES
  ('44444444-0000-0000-0000-000000000001', 'Zone A - Main Entrance', 'Primary entry/exit area',            'Gate 1, North Wing',   500, 400, 460, TRUE,  NOW(), NOW()),
  ('44444444-0000-0000-0000-000000000002', 'Zone B - Food Court',    'Central dining and gathering area',  'Ground Floor Center',  300, 240, 280, TRUE,  NOW(), NOW()),
  ('44444444-0000-0000-0000-000000000003', 'Zone C - Exhibition Hall','Large convention hall',             'Hall B, East Wing',    800, 640, 750, TRUE,  NOW(), NOW()),
  ('44444444-0000-0000-0000-000000000004', 'Zone D - Parking Lobby', 'Parking level entry lobby',         'Basement Level 1',     200, 160, 185, TRUE,  NOW(), NOW()),
  ('44444444-0000-0000-0000-000000000005', 'Zone E - VIP Lounge',    'Restricted VIP area',               '3rd Floor, South',     50,   40,  47, TRUE,  NOW(), NOW()),
  ('44444444-0000-0000-0000-000000000006', 'Zone F - Emergency Exit', 'Emergency evacuation zone',        'Multiple Exits',       1000, 800, 950, FALSE, NOW(), NOW());

-- ============================================================
-- STEP 8: CAMERA GROUPS
-- ============================================================
INSERT INTO camera_groups (id, name, description, location, is_active, created_at, updated_at)
VALUES
  ('55555555-0000-0000-0000-000000000001', 'North Wing Cameras',  'All cameras covering north wing',     'North Wing',      TRUE,  NOW(), NOW()),
  ('55555555-0000-0000-0000-000000000002', 'South Wing Cameras',  'All cameras covering south wing',     'South Wing',      TRUE,  NOW(), NOW()),
  ('55555555-0000-0000-0000-000000000003', 'Entry Gate Cameras',  'Cameras at all entry points',         'Entry Gates',     TRUE,  NOW(), NOW()),
  ('55555555-0000-0000-0000-000000000004', 'Queue Cameras',       'Cameras monitoring queue areas',      'Queue Zones',     TRUE,  NOW(), NOW()),
  ('55555555-0000-0000-0000-000000000005', 'VIP Area Cameras',    'High-security VIP zone cameras',      'VIP Lounge',      FALSE, NOW(), NOW());

-- ============================================================
-- STEP 9: CAMERAS
-- ============================================================
INSERT INTO cameras (id, camera_name, camera_type, rtsp_url, location, description, resolution, fps, status, is_active, stream_enabled, ai_enabled, recording_enabled, last_connected, last_frame_time, last_health_check, zone_id, group_id, created_at, updated_at)
VALUES
  ('66666666-0000-0000-0000-000000000001', 'CAM-01 Main Gate Entry',   'ENTRY',  'rtsp://192.168.1.101:554/stream1', 'Main Gate North',     'Primary entry camera',             '1920x1080', 30, 'ONLINE',      TRUE,  TRUE,  TRUE,  TRUE,  NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '30 secs', NOW() - INTERVAL '1 min',  '44444444-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000003', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000002', 'CAM-02 Main Gate Exit',    'EXIT',   'rtsp://192.168.1.102:554/stream1', 'Main Gate South',     'Primary exit camera',              '1920x1080', 30, 'ONLINE',      TRUE,  TRUE,  TRUE,  TRUE,  NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '30 secs', NOW() - INTERVAL '1 min',  '44444444-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000003', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000003', 'CAM-03 Food Court Zone',   'ZONE',   'rtsp://192.168.1.103:554/stream1', 'Food Court Center',   'Food court crowd monitoring',      '1280x720',  25, 'ONLINE',      TRUE,  TRUE,  TRUE,  TRUE,  NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '1 min',   NOW() - INTERVAL '2 mins', '44444444-0000-0000-0000-000000000002', '55555555-0000-0000-0000-000000000001', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000004', 'CAM-04 Exhibition Hall',   'ZONE',   'rtsp://192.168.1.104:554/stream1', 'Exhibition Hall East', 'Hall crowd density camera',       '1920x1080', 30, 'ONLINE',      TRUE,  TRUE,  TRUE,  TRUE,  NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '30 secs', NOW() - INTERVAL '1 min',  '44444444-0000-0000-0000-000000000003', '55555555-0000-0000-0000-000000000002', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000005', 'CAM-05 Queue Ticket Counter','QUEUE', 'rtsp://192.168.1.105:554/stream1', 'Ticket Counter A',    'Queue management camera',          '1280x720',  25, 'ONLINE',      TRUE,  TRUE,  TRUE,  FALSE, NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '45 secs', NOW() - INTERVAL '1 min',  '44444444-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000004', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000006', 'CAM-06 VIP Face Recognition','FACE', 'rtsp://192.168.1.106:554/stream1', 'VIP Lounge Entry',    'Face recognition at VIP entry',    '1920x1080', 30, 'ONLINE',      TRUE,  TRUE,  TRUE,  TRUE,  NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '30 secs', NOW() - INTERVAL '1 min',  '44444444-0000-0000-0000-000000000005', '55555555-0000-0000-0000-000000000005', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000007', 'CAM-07 Parking Lobby',     'ENTRY',  'rtsp://192.168.1.107:554/stream1', 'Basement Parking',    'Parking entry monitor',            '1280x720',  20, 'ONLINE',      TRUE,  TRUE,  FALSE, TRUE,  NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '1 min',   NOW() - INTERVAL '2 mins', '44444444-0000-0000-0000-000000000004', '55555555-0000-0000-0000-000000000002', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000008', 'CAM-08 South Wing Exit',   'EXIT',   'rtsp://192.168.1.108:554/stream1', 'South Wing Exit B',   'Secondary exit camera',            '1280x720',  25, 'OFFLINE',     FALSE, FALSE, FALSE, FALSE, NOW() - INTERVAL '2 hours', NULL,                        NOW() - INTERVAL '30 mins','44444444-0000-0000-0000-000000000001', '55555555-0000-0000-0000-000000000002', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000009', 'CAM-09 Food Court Queue',  'QUEUE',  'rtsp://192.168.1.109:554/stream1', 'Food Court Queue',    'Queue line camera at food court',  '1280x720',  25, 'MAINTENANCE', FALSE, FALSE, FALSE, FALSE, NOW() - INTERVAL '1 hour',  NULL,                        NOW() - INTERVAL '20 mins','44444444-0000-0000-0000-000000000002', '55555555-0000-0000-0000-000000000004', NOW(), NOW()),
  ('66666666-0000-0000-0000-000000000010', 'CAM-10 Hall B Panoramic',  'ZONE',   'rtsp://192.168.1.110:554/stream1', 'Exhibition Hall West', 'Wide angle hall camera',          '3840x2160', 30, 'ONLINE',      TRUE,  TRUE,  TRUE,  TRUE,  NOW() - INTERVAL '5 mins',  NOW() - INTERVAL '30 secs', NOW() - INTERVAL '1 min',  '44444444-0000-0000-0000-000000000003', '55555555-0000-0000-0000-000000000002', NOW(), NOW());

-- ============================================================
-- STEP 10: AI MODELS
-- ============================================================
INSERT INTO ai_models (id, name, model_type, version, file_path, confidence, iou, input_size, description, is_active, is_loaded, created_at, updated_at)
VALUES
  ('77777777-0000-0000-0000-000000000001', 'YOLOv8-Crowd',       'YOLO',             'v8.0.0', '/models/yolov8_crowd.pt',     0.65, 0.45, '640x640',  'Person detection model for crowd counting',             TRUE,  TRUE,  NOW(), NOW()),
  ('77777777-0000-0000-0000-000000000002', 'FaceNet-Recognition', 'FACE_RECOGNITION', 'v2.1.0', '/models/facenet_v2.pth',      0.80, 0.50, '160x160',  'Face recognition for watchlist matching',               TRUE,  TRUE,  NOW(), NOW()),
  ('77777777-0000-0000-0000-000000000003', 'PoseNet-Queue',       'POSE_ESTIMATION',  'v1.3.0', '/models/posenet_queue.pt',    0.70, 0.40, '256x256',  'Pose estimation for queue behavior analysis',           FALSE, FALSE, NOW(), NOW()),
  ('77777777-0000-0000-0000-000000000004', 'CrowdAnalyzer-v3',   'CROWD_ANALYSIS',   'v3.0.0', '/models/crowd_analyzer.pt',   0.75, 0.45, '512x512',  'Advanced crowd density and flow analysis',              TRUE,  FALSE, NOW(), NOW());

-- ============================================================
-- STEP 11: CRIMINAL WATCHLIST
-- ============================================================
INSERT INTO criminal_watchlist (id, name, alias, description, case_number, face_image_path, threat_level, is_active, added_by, notes, created_at, updated_at)
VALUES
  ('88888888-0000-0000-0000-000000000001', 'Arjun Sharma',    'Arjun S',   'Wanted for theft and pickpocketing in malls',    'CASE-2024-001', '/watchlist/arjun_sharma.jpg',    'HIGH',   TRUE,  'admin', 'Last seen Zone B. Operates in groups.',                          NOW(), NOW()),
  ('88888888-0000-0000-0000-000000000002', 'Ramesh Patel',    'Ram P',     'Suspect in multiple credit card fraud cases',    'CASE-2024-002', '/watchlist/ramesh_patel.jpg',    'MEDIUM', TRUE,  'admin', 'Usually wears a cap. Targets busy queue areas.',                 NOW(), NOW()),
  ('88888888-0000-0000-0000-000000000003', 'Kavita Singh',    'Kavi',      'Known trespasser and vandalism suspect',         'CASE-2024-003', '/watchlist/kavita_singh.jpg',    'LOW',    TRUE,  'admin', 'Frequents food courts and exhibition halls.',                    NOW(), NOW()),
  ('88888888-0000-0000-0000-000000000004', 'Deepak Kumar',    'DK',        'Wanted for assault and public disturbance',      'CASE-2024-004', '/watchlist/deepak_kumar.jpg',    'CRITICAL',TRUE, 'meena.admin', 'Dangerous. Do not approach alone. Alert security immediately.', NOW(), NOW()),
  ('88888888-0000-0000-0000-000000000005', 'Sunita Verma',    'Suni V',    'Suspect in identity forgery and impersonation', 'CASE-2024-005', '/watchlist/sunita_verma.jpg',    'MEDIUM', TRUE,  'admin', 'Often disguises appearance. Compare facial features carefully.', NOW(), NOW()),
  ('88888888-0000-0000-0000-000000000006', 'Mohan Lal',       'Mohan',     'Parole violator - missing from supervision',     'CASE-2024-006', '/watchlist/mohan_lal.jpg',       'HIGH',   TRUE,  'admin', 'Has prior history in this venue. Zone A sightings reported.',   NOW(), NOW()),
  ('88888888-0000-0000-0000-000000000007', 'Priya Das',       NULL,        'Shoplifting suspect with multiple incidents',    'CASE-2024-007', '/watchlist/priya_das.jpg',       'LOW',    TRUE,  'admin', 'Quick mover - usually exits through Gate 2.',                   NOW(), NOW()),
  ('88888888-0000-0000-0000-000000000008', 'Ajay Nair',       'AJ',        'Suspect in illegal street gambling operations',  'CASE-2024-008', '/watchlist/ajay_nair.jpg',       'MEDIUM', FALSE, 'admin', 'Case closed - no longer active threat.',                         NOW(), NOW());

-- ============================================================
-- STEP 12: SYSTEM SETTINGS
-- ============================================================
INSERT INTO system_settings (id, key, value, value_type, description, category, is_public, updated_by, created_at, updated_at)
VALUES
  ('99999999-0000-0000-0000-000000000001', 'zone_warning_threshold',      '80',                      'integer',  'Zone capacity warning percentage',          'crowd',       TRUE,  'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000002', 'zone_critical_threshold',     '90',                      'integer',  'Zone capacity critical percentage',         'crowd',       TRUE,  'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000003', 'alert_email_recipients',      'security@crowdmgmt.com',  'string',   'Email addresses for alert notifications',   'alerts',      FALSE, 'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000004', 'face_match_confidence',       '0.80',                    'float',    'Minimum confidence for face match alert',   'face_recog',  TRUE,  'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000005', 'queue_max_wait_minutes',      '15',                      'integer',  'Max queue wait time in minutes for alert',  'queue',       TRUE,  'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000006', 'dashboard_refresh_interval',  '5',                       'integer',  'Dashboard data refresh in seconds',         'ui',          TRUE,  'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000007', 'recording_storage_path',      '/recordings',             'string',   'Storage path for camera recordings',        'storage',     FALSE, 'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000008', 'max_snapshot_retention_days', '30',                      'integer',  'Number of days to keep snapshots',          'storage',     FALSE, 'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000009', 'maintenance_mode',            'false',                   'boolean',  'Enable system maintenance mode',            'system',      TRUE,  'admin', NOW(), NOW()),
  ('99999999-0000-0000-0000-000000000010', 'websocket_heartbeat_seconds', '30',                      'integer',  'WebSocket keepalive interval in seconds',   'system',      TRUE,  'admin', NOW(), NOW());

-- ============================================================
-- STEP 13: SERVICE STATUSES
-- ============================================================
INSERT INTO service_statuses (id, service_name, status, cpu_usage, memory_usage, gpu_usage, process_id, error_message, started_at, last_heartbeat, updated_at)
VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'PERSON_DETECTION',  'RUNNING',  18.5, 42.3, 35.1, 12345, NULL,                            NOW() - INTERVAL '6 hours', NOW() - INTERVAL '30 secs', NOW()),
  ('aaaaaaaa-0000-0000-0000-000000000002', 'QUEUE_ANALYSIS',    'RUNNING',  12.1, 28.7, 15.6, 12346, NULL,                            NOW() - INTERVAL '6 hours', NOW() - INTERVAL '30 secs', NOW()),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'ZONE_MONITORING',   'RUNNING',  9.3,  21.4, 10.2, 12347, NULL,                            NOW() - INTERVAL '6 hours', NOW() - INTERVAL '30 secs', NOW()),
  ('aaaaaaaa-0000-0000-0000-000000000004', 'FACE_RECOGNITION',  'RUNNING',  22.8, 55.1, 68.4, 12348, NULL,                            NOW() - INTERVAL '6 hours', NOW() - INTERVAL '30 secs', NOW()),
  ('aaaaaaaa-0000-0000-0000-000000000005', 'CAMERA_STREAM',     'RUNNING',  31.2, 48.9, 20.0, 12349, NULL,                            NOW() - INTERVAL '6 hours', NOW() - INTERVAL '30 secs', NOW()),
  ('aaaaaaaa-0000-0000-0000-000000000006', 'ALERT_ENGINE',      'ERROR',    0.0,  5.2,  0.0,  NULL,  'Connection timeout to SMTP server. Retrying...', NULL,                       NOW() - INTERVAL '5 mins',  NOW());

-- ============================================================
-- STEP 14: ZONE COUNTS (crowd count history per zone)
-- ============================================================
INSERT INTO zone_counts (id, zone_id, count, source, recorded_at)
VALUES
  -- Zone A - Main Entrance (current: moderate crowd)
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000001', 120, 'CAMERA', NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000001', 185, 'CAMERA', NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000001', 340, 'CAMERA', NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000001', 412, 'CAMERA', NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000001', 387, 'CAMERA', NOW()),
  -- Zone B - Food Court (near warning threshold)
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000002', 89,  'CAMERA', NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000002', 145, 'CAMERA', NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000002', 220, 'CAMERA', NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000002', 248, 'CAMERA', NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000002', 261, 'CAMERA', NOW()),
  -- Zone C - Exhibition Hall (CRITICAL - over threshold)
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000003', 500, 'CAMERA', NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000003', 620, 'CAMERA', NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000003', 710, 'CAMERA', NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000003', 764, 'CAMERA', NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000003', 792, 'CAMERA', NOW()),
  -- Zone D - Parking Lobby (low crowd)
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000004', 45,  'CAMERA', NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000004', 67,  'CAMERA', NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000004', 72,  'CAMERA', NOW()),
  -- Zone E - VIP Lounge (very low)
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000005', 8,   'CAMERA', NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000005', 12,  'CAMERA', NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), '44444444-0000-0000-0000-000000000005', 15,  'CAMERA', NOW());

-- ============================================================
-- STEP 15: QUEUES
-- ============================================================
INSERT INTO queues (id, name, description, location, max_capacity, is_active, zone_id, camera_id, created_at, updated_at)
VALUES
  ('bbbbbbbb-0000-0000-0000-000000000001', 'Ticket Counter A',    'Main ticket booking queue',        'Zone A - Counter 1', 100, TRUE,  '44444444-0000-0000-0000-000000000001', '66666666-0000-0000-0000-000000000005', NOW(), NOW()),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'Food Court Queue',    'Queue for food ordering',          'Zone B - Food Area', 80,  TRUE,  '44444444-0000-0000-0000-000000000002', '66666666-0000-0000-0000-000000000009', NOW(), NOW()),
  ('bbbbbbbb-0000-0000-0000-000000000003', 'Exhibition Entry Queue','Queue to enter exhibition hall', 'Zone C - Entrance',  150, TRUE,  '44444444-0000-0000-0000-000000000003', '66666666-0000-0000-0000-000000000004', NOW(), NOW()),
  ('bbbbbbbb-0000-0000-0000-000000000004', 'Parking Entry Queue', 'Vehicle entry queue',              'Zone D - Parking',   50,  TRUE,  '44444444-0000-0000-0000-000000000004', '66666666-0000-0000-0000-000000000007', NOW(), NOW()),
  ('bbbbbbbb-0000-0000-0000-000000000005', 'Security Check Queue','Security screening queue',         'Zone A - Gate 1',    60,  TRUE,  '44444444-0000-0000-0000-000000000001', '66666666-0000-0000-0000-000000000001', NOW(), NOW());

-- ============================================================
-- STEP 16: QUEUE SNAPSHOTS (recent queue measurements)
-- ============================================================
INSERT INTO queue_snapshots (id, queue_id, people, waiting_time, status, captured_at)
VALUES
  -- Ticket Counter A (HEAVY - busy)
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000001', 15,  4.5,  'NORMAL',   NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000001', 38,  9.2,  'MODERATE', NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000001', 65,  16.8, 'HEAVY',    NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000001', 72,  18.5, 'HEAVY',    NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000001', 81,  22.3, 'CRITICAL', NOW()),
  -- Food Court Queue (MODERATE)
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000002', 8,   2.1,  'NORMAL',   NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000002', 22,  6.3,  'MODERATE', NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000002', 31,  8.7,  'MODERATE', NOW()),
  -- Exhibition Entry Queue (CRITICAL)
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000003', 45,  11.2, 'HEAVY',    NOW() - INTERVAL '15 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000003', 88,  22.0, 'CRITICAL', NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000003', 112, 28.5, 'CRITICAL', NOW()),
  -- Security Check Queue (NORMAL)
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000005', 5,   1.2,  'NORMAL',   NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), 'bbbbbbbb-0000-0000-0000-000000000005', 9,   2.5,  'NORMAL',   NOW());

-- ============================================================
-- STEP 17: ROIs (Regions of Interest)
-- ============================================================
INSERT INTO rois (id, name, roi_type, direction, polygon, description, is_active, camera_id, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'Main Entry Line',    'COUNTING_LINE', 'ENTRY', '[{"x":100,"y":400},{"x":1820,"y":400}]',                                      'Horizontal counting line at main entry',    TRUE, '66666666-0000-0000-0000-000000000001', NOW(), NOW()),
  (gen_random_uuid(), 'Exit Counting Line', 'COUNTING_LINE', 'EXIT',  '[{"x":100,"y":600},{"x":1820,"y":600}]',                                      'Horizontal line at exit',                  TRUE, '66666666-0000-0000-0000-000000000002', NOW(), NOW()),
  (gen_random_uuid(), 'Zone A Boundary',    'POLYGON_ZONE',  'BOTH',  '[{"x":50,"y":50},{"x":1870,"y":50},{"x":1870,"y":1030},{"x":50,"y":1030}]',  'Full frame zone boundary',                  TRUE, '66666666-0000-0000-0000-000000000003', NOW(), NOW()),
  (gen_random_uuid(), 'VIP Entry Gate',     'ENTRY_GATE',    'ENTRY', '[{"x":750,"y":300},{"x":1050,"y":300},{"x":1050,"y":780},{"x":750,"y":780}]','VIP access gate ROI',                       TRUE, '66666666-0000-0000-0000-000000000006', NOW(), NOW()),
  (gen_random_uuid(), 'Restricted Area',    'RESTRICTED',    'BOTH',  '[{"x":200,"y":200},{"x":600,"y":200},{"x":600,"y":600},{"x":200,"y":600}]',  'Server room restricted zone',               TRUE, '66666666-0000-0000-0000-000000000004', NOW(), NOW());

-- ============================================================
-- STEP 18: ENTRY/EXIT COUNTS
-- ============================================================
INSERT INTO entry_exit_counts (id, camera_id, zone_id, entry_count, exit_count, net_count, recorded_at)
VALUES
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', 50,  12, 38,  NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', 78,  25, 53,  NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', 120, 41, 79,  NOW() - INTERVAL '10 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', 145, 58, 87,  NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000002', '44444444-0000-0000-0000-000000000001', 30,  85, -55, NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000002', '44444444-0000-0000-0000-000000000001', 45,  110,-65, NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', 200, 80, 120, NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', 280, 95, 185, NOW() - INTERVAL '15 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000007', '44444444-0000-0000-0000-000000000004', 35,  20, 15,  NOW() - INTERVAL '10 mins');

-- ============================================================
-- STEP 19: CAMERA HEALTH
-- ============================================================
INSERT INTO camera_health (id, camera_id, cpu_usage, memory_usage, gpu_usage, fps, decode_fps, latency_ms, packet_loss, bitrate_kbps, error_message, recorded_at)
VALUES
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000001', 12.5, 28.3, 22.1, 29.8, 29.5, 45.2,  0.1,  4800, NULL,                          NOW() - INTERVAL '2 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000002', 11.2, 26.8, 20.5, 30.0, 29.8, 42.1,  0.0,  4600, NULL,                          NOW() - INTERVAL '2 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000003', 14.8, 32.1, 18.9, 25.1, 24.8, 52.3,  0.3,  3200, NULL,                          NOW() - INTERVAL '2 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000004', 18.3, 41.5, 35.2, 29.5, 29.0, 48.7,  0.1,  8500, NULL,                          NOW() - INTERVAL '2 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000005', 10.1, 22.4, 12.8, 25.0, 24.5, 39.8,  0.2,  2800, NULL,                          NOW() - INTERVAL '2 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000006', 21.5, 48.3, 62.1, 30.0, 29.9, 35.2,  0.0,  5200, NULL,                          NOW() - INTERVAL '2 mins'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000008', 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,   100.0,0,    'Camera offline - no signal',  NOW() - INTERVAL '1 hour'),
  (gen_random_uuid(), '66666666-0000-0000-0000-000000000010', 15.6, 38.2, 28.4, 29.7, 29.2, 55.1,  0.2,  12000,NULL,                          NOW() - INTERVAL '2 mins');

-- ============================================================
-- STEP 20: ALERTS
-- ============================================================
INSERT INTO alerts (id, title, message, alert_type, severity, status, extra_data, camera_id, zone_id, queue_id, acknowledged_by, acknowledged_at, resolved_at, resolved_by, resolution_note, created_at, updated_at)
VALUES
  ('cccccccc-0000-0000-0000-000000000001',
   'Zone C Critical Capacity',
   'Exhibition Hall has reached 99% capacity (792/800 people). Immediate action required.',
   'ZONE_CAPACITY', 'CRITICAL', 'OPEN',
   '{"current_count":792,"capacity":800,"percentage":99}',
   '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', NULL,
   NULL, NULL, NULL, NULL, NULL,
   NOW() - INTERVAL '3 mins', NOW() - INTERVAL '3 mins'),

  ('cccccccc-0000-0000-0000-000000000002',
   'Queue Critical - Ticket Counter A',
   'Ticket Counter A queue has 81 people with 22+ minute wait time. Queue is critically overloaded.',
   'QUEUE_CRITICAL', 'HIGH', 'ACKNOWLEDGED',
   '{"queue_length":81,"wait_time_minutes":22.3,"max_capacity":100}',
   '66666666-0000-0000-0000-000000000005', '44444444-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001',
   'john.ops', NOW() - INTERVAL '2 mins', NULL, NULL, NULL,
   NOW() - INTERVAL '8 mins', NOW() - INTERVAL '2 mins'),

  ('cccccccc-0000-0000-0000-000000000003',
   'Camera Offline - CAM-08',
   'Camera CAM-08 South Wing Exit has gone offline. No video feed available.',
   'CAMERA_OFFLINE', 'HIGH', 'OPEN',
   '{"camera_name":"CAM-08 South Wing Exit","last_seen":"2 hours ago"}',
   '66666666-0000-0000-0000-000000000008', NULL, NULL,
   NULL, NULL, NULL, NULL, NULL,
   NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours'),

  ('cccccccc-0000-0000-0000-000000000004',
   'Watchlist Match Detected - Arjun Sharma',
   'Criminal watchlist match detected in Zone B Food Court. Suspect: Arjun Sharma (CASE-2024-001). Confidence: 94%',
   'FACE_MATCH', 'CRITICAL', 'OPEN',
   '{"suspect_name":"Arjun Sharma","case_number":"CASE-2024-001","confidence":0.94,"threat_level":"HIGH"}',
   '66666666-0000-0000-0000-000000000003', '44444444-0000-0000-0000-000000000002', NULL,
   NULL, NULL, NULL, NULL, NULL,
   NOW() - INTERVAL '7 mins', NOW() - INTERVAL '7 mins'),

  ('cccccccc-0000-0000-0000-000000000005',
   'Zone B Approaching Warning Threshold',
   'Food Court zone is at 87% capacity (261/300 people). Monitor closely.',
   'CROWD_OVERFLOW', 'MEDIUM', 'ACKNOWLEDGED',
   '{"current_count":261,"capacity":300,"percentage":87}',
   '66666666-0000-0000-0000-000000000003', '44444444-0000-0000-0000-000000000002', NULL,
   'ravi.guard', NOW() - INTERVAL '5 mins', NULL, NULL, NULL,
   NOW() - INTERVAL '12 mins', NOW() - INTERVAL '5 mins'),

  ('cccccccc-0000-0000-0000-000000000006',
   'Alert Engine Service Error',
   'The ALERT_ENGINE service encountered an SMTP connection timeout. Email notifications may be delayed.',
   'SYSTEM_ERROR', 'MEDIUM', 'OPEN',
   '{"service":"ALERT_ENGINE","error":"SMTP connection timeout"}',
   NULL, NULL, NULL,
   NULL, NULL, NULL, NULL, NULL,
   NOW() - INTERVAL '5 mins', NOW() - INTERVAL '5 mins'),

  ('cccccccc-0000-0000-0000-000000000007',
   'Exhibition Queue Critical',
   'Exhibition hall entry queue has 112 people waiting with 28+ minute wait. Entry queue is critically overloaded.',
   'QUEUE_CRITICAL', 'CRITICAL', 'OPEN',
   '{"queue_length":112,"wait_time_minutes":28.5,"max_capacity":150}',
   '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000003',
   NULL, NULL, NULL, NULL, NULL,
   NOW() - INTERVAL '5 mins', NOW() - INTERVAL '5 mins'),

  ('cccccccc-0000-0000-0000-000000000008',
   'CAM-09 Under Maintenance',
   'Food Court Queue camera (CAM-09) is currently under scheduled maintenance.',
   'SYSTEM_ERROR', 'LOW', 'RESOLVED',
   '{"camera_name":"CAM-09 Food Court Queue","maintenance_type":"scheduled"}',
   '66666666-0000-0000-0000-000000000009', '44444444-0000-0000-0000-000000000002', NULL,
   'meena.admin', NOW() - INTERVAL '45 mins', NOW() - INTERVAL '20 mins', 'meena.admin', 'Maintenance scheduled, team notified.',
   NOW() - INTERVAL '1 hour', NOW() - INTERVAL '20 mins');

-- ============================================================
-- STEP 21: FACE DETECTION LOGS
-- ============================================================
INSERT INTO face_detection_logs (id, watchlist_id, camera_id, zone_id, confidence, face_image_path, bounding_box, matched, detected_at)
VALUES
  -- Arjun Sharma matched (HIGH threat)
  (gen_random_uuid(), '88888888-0000-0000-0000-000000000001', '66666666-0000-0000-0000-000000000003', '44444444-0000-0000-0000-000000000002', 0.94, '/detections/face_001.jpg', '{"x":320,"y":120,"w":180,"h":220}', TRUE,  NOW() - INTERVAL '7 mins'),
  -- Deepak Kumar matched (CRITICAL threat)
  (gen_random_uuid(), '88888888-0000-0000-0000-000000000004', '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', 0.88, '/detections/face_002.jpg', '{"x":450,"y":200,"w":160,"h":200}', TRUE,  NOW() - INTERVAL '15 mins'),
  -- Unknown person (no match)
  (gen_random_uuid(), NULL,                                   '66666666-0000-0000-0000-000000000006', '44444444-0000-0000-0000-000000000005', 0.51, '/detections/face_003.jpg', '{"x":600,"y":150,"w":140,"h":180}', FALSE, NOW() - INTERVAL '10 mins'),
  -- Ramesh Patel matched (MEDIUM threat)
  (gen_random_uuid(), '88888888-0000-0000-0000-000000000002', '66666666-0000-0000-0000-000000000005', '44444444-0000-0000-0000-000000000001', 0.82, '/detections/face_004.jpg', '{"x":280,"y":90,"w":170,"h":210}',  TRUE,  NOW() - INTERVAL '25 mins'),
  -- Unknown person (no match)
  (gen_random_uuid(), NULL,                                   '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', 0.62, '/detections/face_005.jpg', '{"x":850,"y":300,"w":130,"h":165}', FALSE, NOW() - INTERVAL '20 mins'),
  -- Kavita Singh matched (LOW threat)
  (gen_random_uuid(), '88888888-0000-0000-0000-000000000003', '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', 0.76, '/detections/face_006.jpg', '{"x":410,"y":180,"w":155,"h":195}', TRUE,  NOW() - INTERVAL '35 mins'),
  -- Unknown (no match)
  (gen_random_uuid(), NULL,                                   '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', 0.43, '/detections/face_007.jpg', '{"x":920,"y":240,"w":145,"h":185}', FALSE, NOW() - INTERVAL '40 mins');

-- ============================================================
-- STEP 22: EVENTS
-- ============================================================
INSERT INTO events (id, event_type, severity, title, description, extra_data, camera_id, zone_id, queue_id, alert_id, is_acknowledged, acknowledged_by, occurred_at)
VALUES
  (gen_random_uuid(), 'ZONE_ALERT',     'CRITICAL', 'Zone C Critically Full',     'Exhibition Hall reached 99% capacity.',                  '{"zone":"Zone C","count":792,"capacity":800}',      '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', NULL,                                      'cccccccc-0000-0000-0000-000000000001', FALSE, NULL,       NOW() - INTERVAL '3 mins'),
  (gen_random_uuid(), 'QUEUE_ALERT',    'ERROR',    'Queue Overload - Ticket A',  'Ticket Counter A queue critically overloaded.',          '{"queue":"Ticket Counter A","length":81}',          '66666666-0000-0000-0000-000000000005', NULL,                                   'bbbbbbbb-0000-0000-0000-000000000001', 'cccccccc-0000-0000-0000-000000000002', TRUE,  'john.ops', NOW() - INTERVAL '8 mins'),
  (gen_random_uuid(), 'CAMERA_OFFLINE', 'ERROR',    'CAM-08 Went Offline',        'South Wing Exit camera lost connection.',                '{"camera":"CAM-08"}',                               '66666666-0000-0000-0000-000000000008', NULL,                                   NULL,                                      'cccccccc-0000-0000-0000-000000000003', FALSE, NULL,       NOW() - INTERVAL '2 hours'),
  (gen_random_uuid(), 'FACE_MATCH',     'CRITICAL', 'Watchlist Match: Arjun',     'High-confidence match for Arjun Sharma (CASE-2024-001).','{"suspect":"Arjun Sharma","confidence":0.94}',     '66666666-0000-0000-0000-000000000003', '44444444-0000-0000-0000-000000000002', NULL,                                      'cccccccc-0000-0000-0000-000000000004', FALSE, NULL,       NOW() - INTERVAL '7 mins'),
  (gen_random_uuid(), 'CROWD_SURGE',    'WARNING',  'Crowd Surge in Zone A',      'Rapid crowd increase detected at main entrance.',        '{"zone":"Zone A","increase_rate":"+87 in 5 mins"}', '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', NULL,                                      NULL,                                   FALSE, NULL,       NOW() - INTERVAL '15 mins'),
  (gen_random_uuid(), 'SYSTEM_START',   'INFO',     'System Started',             'Crowd management system started successfully.',          '{"version":"2.1.0"}',                               NULL,                                   NULL,                                   NULL,                                      NULL,                                   TRUE,  'admin',    NOW() - INTERVAL '6 hours'),
  (gen_random_uuid(), 'AI_MODEL_LOADED','INFO',     'YOLOv8 Model Loaded',        'Person detection model loaded and ready.',               '{"model":"YOLOv8-Crowd","version":"v8.0.0"}',       NULL,                                   NULL,                                   NULL,                                      NULL,                                   TRUE,  'admin',    NOW() - INTERVAL '6 hours'),
  (gen_random_uuid(), 'CAMERA_ONLINE',  'INFO',     'CAM-01 Online',              'Main Gate Entry camera connected and streaming.',        '{"camera":"CAM-01 Main Gate Entry"}',               '66666666-0000-0000-0000-000000000001', NULL,                                   NULL,                                      NULL,                                   TRUE,  'admin',    NOW() - INTERVAL '6 hours'),
  (gen_random_uuid(), 'QUEUE_ALERT',    'CRITICAL', 'Exhibition Queue Critical',  'Exhibition hall entry queue critically overloaded.',     '{"queue":"Exhibition Entry Queue","length":112}',   '66666666-0000-0000-0000-000000000004', '44444444-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000003', 'cccccccc-0000-0000-0000-000000000007', FALSE, NULL,       NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), 'FACE_MATCH',     'ERROR',    'Watchlist Match: Deepak',    'CRITICAL threat Deepak Kumar detected at main entrance.', '{"suspect":"Deepak Kumar","confidence":0.88}',     '66666666-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000001', NULL,                                      NULL,                                   FALSE, NULL,       NOW() - INTERVAL '15 mins');

-- ============================================================
-- STEP 23: NOTIFICATIONS
-- ============================================================
INSERT INTO notifications (id, title, message, channel, status, recipient, extra_data, attempts, sent_at, delivered_at, error_message, alert_id, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'CRITICAL: Zone C Full',           'Exhibition Hall 99% capacity. Immediate crowd control needed.',                'DASHBOARD', 'DELIVERED', 'security@crowdmgmt.com', '{"priority":"critical"}', 1, NOW() - INTERVAL '3 mins', NOW() - INTERVAL '3 mins', NULL,                     'cccccccc-0000-0000-0000-000000000001', NOW() - INTERVAL '3 mins', NOW() - INTERVAL '3 mins'),
  (gen_random_uuid(), 'CRITICAL: Zone C Full',           'Exhibition Hall 99% capacity. Immediate crowd control needed.',                'EMAIL',     'FAILED',    'security@crowdmgmt.com', '{"priority":"critical"}', 3, NULL,                       NULL,                       'SMTP connection timeout', 'cccccccc-0000-0000-0000-000000000001', NOW() - INTERVAL '3 mins', NOW() - INTERVAL '3 mins'),
  (gen_random_uuid(), 'Watchlist Alert: Arjun Sharma',   'Face match detected. Threat level: HIGH. Location: Zone B Food Court.',       'DASHBOARD', 'DELIVERED', 'all_security',           '{"suspect_id":"88888888-0000-0000-0000-000000000001"}', 1, NOW() - INTERVAL '7 mins', NOW() - INTERVAL '7 mins', NULL, 'cccccccc-0000-0000-0000-000000000004', NOW() - INTERVAL '7 mins', NOW() - INTERVAL '7 mins'),
  (gen_random_uuid(), 'Watchlist Alert: Arjun Sharma',   'URGENT: Watchlist match in Zone B. Arjun Sharma spotted. Take action.',      'SMS',       'SENT',      '+91-9876543210',         '{"suspect_id":"88888888-0000-0000-0000-000000000001"}', 1, NOW() - INTERVAL '7 mins', NULL,                       NULL,                     'cccccccc-0000-0000-0000-000000000004', NOW() - INTERVAL '7 mins', NOW() - INTERVAL '7 mins'),
  (gen_random_uuid(), 'Queue Alert: Ticket Counter A',   'Ticket Counter A queue at critical level. 81 people, 22 min wait.',           'DASHBOARD', 'DELIVERED', 'operators',              '{"queue_id":"bbbbbbbb-0000-0000-0000-000000000001"}',  1, NOW() - INTERVAL '8 mins', NOW() - INTERVAL '8 mins', NULL, 'cccccccc-0000-0000-0000-000000000002', NOW() - INTERVAL '8 mins', NOW() - INTERVAL '8 mins'),
  (gen_random_uuid(), 'Camera Offline: CAM-08',          'CAM-08 South Wing Exit is offline for 2 hours. Please investigate.',         'EMAIL',     'PENDING',   'admin@crowdmgmt.com',    '{"camera_id":"66666666-0000-0000-0000-000000000008"}', 0, NULL,                       NULL,                       NULL,                     'cccccccc-0000-0000-0000-000000000003', NOW() - INTERVAL '2 hours',NOW() - INTERVAL '2 hours'),
  (gen_random_uuid(), 'CRITICAL: Deepak Kumar Detected', 'DANGEROUS suspect Deepak Kumar at Main Entrance. Security alert CRITICAL.',  'SMS',       'DELIVERED', '+91-9876543213',         '{"suspect_id":"88888888-0000-0000-0000-000000000004"}', 1, NOW() - INTERVAL '14 mins',NOW() - INTERVAL '14 mins',NULL,                     NULL,                                   NOW() - INTERVAL '15 mins',NOW() - INTERVAL '14 mins');

-- ============================================================
-- STEP 24: SNAPSHOTS
-- ============================================================
INSERT INTO snapshots (id, snapshot_type, file_path, file_size_bytes, width, height, snapshot_metadata, captured_at, is_archived, camera_id, alert_id, event_id)
VALUES
  (gen_random_uuid(), 'FACE_DETECTION', '/snapshots/face_arjun_sharma.jpg',   245800, 1280, 720,  '{"suspect":"Arjun Sharma","confidence":0.94}', NOW() - INTERVAL '7 mins',  FALSE, '66666666-0000-0000-0000-000000000003', 'cccccccc-0000-0000-0000-000000000004', NULL),
  (gen_random_uuid(), 'ZONE_ALERT',     '/snapshots/zone_c_critical.jpg',     512300, 1920, 1080, '{"zone":"Zone C","count":792}',               NOW() - INTERVAL '3 mins',  FALSE, '66666666-0000-0000-0000-000000000004', 'cccccccc-0000-0000-0000-000000000001', NULL),
  (gen_random_uuid(), 'CROWD_ALERT',    '/snapshots/zone_a_surge.jpg',        389100, 1920, 1080, '{"zone":"Zone A","alert":"surge"}',           NOW() - INTERVAL '15 mins', FALSE, '66666666-0000-0000-0000-000000000001', NULL,                                   NULL),
  (gen_random_uuid(), 'FACE_DETECTION', '/snapshots/face_deepak_kumar.jpg',   198700, 1280, 720,  '{"suspect":"Deepak Kumar","confidence":0.88}',NOW() - INTERVAL '15 mins', FALSE, '66666666-0000-0000-0000-000000000001', NULL,                                   NULL),
  (gen_random_uuid(), 'CAMERA_HEALTH',  '/snapshots/cam08_offline_snap.jpg',  102400, 640,  360,  '{"camera":"CAM-08","status":"offline"}',      NOW() - INTERVAL '2 hours', TRUE,  '66666666-0000-0000-0000-000000000008', 'cccccccc-0000-0000-0000-000000000003', NULL);

-- ============================================================
-- STEP 25: AUDIT LOGS
-- ============================================================
INSERT INTO audit_logs (id, user_id, username, action, resource_type, resource_id, old_value, new_value, ip_address, user_agent, status, error_message, logged_at)
VALUES
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000001', 'admin',       'LOGIN',           'auth',       NULL,                                     NULL, '{"login_time":"now"}',                              '192.168.1.10', 'Mozilla/5.0 Chrome/125', 'success', NULL, NOW() - INTERVAL '6 hours'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000001', 'admin',       'CREATE',          'camera',     '66666666-0000-0000-0000-000000000010',   NULL, '{"camera_name":"CAM-10 Hall B Panoramic"}',         '192.168.1.10', 'Mozilla/5.0 Chrome/125', 'success', NULL, NOW() - INTERVAL '5 hours'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000005', 'meena.admin', 'CREATE',          'watchlist',  '88888888-0000-0000-0000-000000000004',   NULL, '{"name":"Deepak Kumar","threat_level":"CRITICAL"}',  '192.168.1.20', 'Mozilla/5.0 Firefox/120','success', NULL, NOW() - INTERVAL '4 hours'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000002', 'john.ops',    'ACKNOWLEDGE',     'alert',      'cccccccc-0000-0000-0000-000000000002',   '{"status":"OPEN"}','{"status":"ACKNOWLEDGED"}',              '192.168.1.30', 'Mozilla/5.0 Chrome/125', 'success', NULL, NOW() - INTERVAL '2 mins'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000004', 'ravi.guard',  'ACKNOWLEDGE',     'alert',      'cccccccc-0000-0000-0000-000000000005',   '{"status":"OPEN"}','{"status":"ACKNOWLEDGED"}',              '192.168.1.40', 'Mozilla/5.0 Mobile',     'success', NULL, NOW() - INTERVAL '5 mins'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000005', 'meena.admin', 'RESOLVE',         'alert',      'cccccccc-0000-0000-0000-000000000008',   '{"status":"ACKNOWLEDGED"}','{"status":"RESOLVED"}',          '192.168.1.20', 'Mozilla/5.0 Firefox/120','success', NULL, NOW() - INTERVAL '20 mins'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000001', 'admin',       'UPDATE',          'zone',       '44444444-0000-0000-0000-000000000003',   '{"capacity":750}','{"capacity":800}',                       '192.168.1.10', 'Mozilla/5.0 Chrome/125', 'success', NULL, NOW() - INTERVAL '3 hours'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000003', 'priya.view',  'LOGIN',           'auth',       NULL,                                     NULL, '{"login_time":"now"}',                              '192.168.1.50', 'Mozilla/5.0 Edge/120',   'success', NULL, NOW() - INTERVAL '30 mins'),
  (gen_random_uuid(), '33333333-0000-0000-0000-000000000001', 'admin',       'UPDATE_SETTINGS', 'settings',   '99999999-0000-0000-0000-000000000001',   '{"value":"75"}', '{"value":"80"}',                         '192.168.1.10', 'Mozilla/5.0 Chrome/125', 'success', NULL, NOW() - INTERVAL '2 hours'),
  (gen_random_uuid(), NULL,                                   NULL,          'FAILED_LOGIN',    'auth',       NULL,                                     NULL, '{"username":"hacker123"}',                          '10.0.0.99',    'curl/7.81.0',            'failed',  'Invalid credentials', NOW() - INTERVAL '1 hour');

-- ============================================================
-- VERIFICATION QUERIES - Run these to confirm data inserted
-- ============================================================
SELECT 'users'              AS table_name, COUNT(*) AS record_count FROM users
UNION ALL
SELECT 'roles',                COUNT(*) FROM roles
UNION ALL
SELECT 'permissions',          COUNT(*) FROM permissions
UNION ALL
SELECT 'zones',                COUNT(*) FROM zones
UNION ALL
SELECT 'camera_groups',        COUNT(*) FROM camera_groups
UNION ALL
SELECT 'cameras',              COUNT(*) FROM cameras
UNION ALL
SELECT 'ai_models',            COUNT(*) FROM ai_models
UNION ALL
SELECT 'criminal_watchlist',   COUNT(*) FROM criminal_watchlist
UNION ALL
SELECT 'system_settings',      COUNT(*) FROM system_settings
UNION ALL
SELECT 'service_statuses',     COUNT(*) FROM service_statuses
UNION ALL
SELECT 'zone_counts',          COUNT(*) FROM zone_counts
UNION ALL
SELECT 'queues',               COUNT(*) FROM queues
UNION ALL
SELECT 'queue_snapshots',      COUNT(*) FROM queue_snapshots
UNION ALL
SELECT 'rois',                 COUNT(*) FROM rois
UNION ALL
SELECT 'entry_exit_counts',    COUNT(*) FROM entry_exit_counts
UNION ALL
SELECT 'camera_health',        COUNT(*) FROM camera_health
UNION ALL
SELECT 'alerts',               COUNT(*) FROM alerts
UNION ALL
SELECT 'face_detection_logs',  COUNT(*) FROM face_detection_logs
UNION ALL
SELECT 'events',               COUNT(*) FROM events
UNION ALL
SELECT 'notifications',        COUNT(*) FROM notifications
UNION ALL
SELECT 'snapshots',            COUNT(*) FROM snapshots
UNION ALL
SELECT 'audit_logs',           COUNT(*) FROM audit_logs
ORDER BY table_name;
