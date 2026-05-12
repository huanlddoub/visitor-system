CREATE DATABASE IF NOT EXISTS visitor_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE visitor_system;

CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  phone VARCHAR(32),
  role ENUM('admin', 'receptionist') NOT NULL,
  department VARCHAR(64),
  skills JSON,
  available_status VARCHAR(32) NOT NULL DEFAULT 'available',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS visitors (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  company VARCHAR(128) NOT NULL,
  phone VARCHAR(32) NOT NULL,
  visit_time DATETIME NOT NULL,
  people_count INT NOT NULL,
  status ENUM('pending_assignment', 'assigned', 'in_progress', 'completed', 'exception')
    NOT NULL DEFAULT 'pending_assignment',
  remark TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS visitor_requirements (
  id INT PRIMARY KEY AUTO_INCREMENT,
  visitor_id INT NOT NULL,
  type ENUM('general', 'pickup', 'dropoff', 'hotel', 'meal') NOT NULL,
  detail JSON NOT NULL,
  status ENUM('pending_assignment', 'assigned', 'in_progress', 'completed', 'exception')
    NOT NULL DEFAULT 'pending_assignment',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_requirements_visitor
    FOREIGN KEY (visitor_id) REFERENCES visitors(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reception_tasks (
  id INT PRIMARY KEY AUTO_INCREMENT,
  visitor_id INT NOT NULL,
  requirement_id INT NOT NULL UNIQUE,
  task_type ENUM('general', 'pickup', 'dropoff', 'hotel', 'meal') NOT NULL,
  assignee_id INT,
  status ENUM('pending_assignment', 'assigned', 'in_progress', 'completed', 'exception')
    NOT NULL DEFAULT 'pending_assignment',
  deadline DATETIME,
  agent_suggestion JSON,
  remark TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_tasks_visitor
    FOREIGN KEY (visitor_id) REFERENCES visitors(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_tasks_requirement
    FOREIGN KEY (requirement_id) REFERENCES visitor_requirements(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_tasks_assignee
    FOREIGN KEY (assignee_id) REFERENCES users(id)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agent_logs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  agent_name VARCHAR(80) NOT NULL,
  input_payload JSON NOT NULL,
  output_payload JSON NOT NULL,
  decision_reason TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (id, name, phone, role, department, skills, available_status)
VALUES
  (1, '张敏', '13800000001', 'receptionist', '综合接待', JSON_OBJECT('reception', true, 'transport', true, 'pickup', true, 'dropoff', true), 'available'),
  (2, '李航', '13800000002', 'receptionist', '行政保障', JSON_OBJECT('hotel', true, 'meal', true), 'available'),
  (3, '王悦', '13800000003', 'receptionist', '会务服务', JSON_OBJECT('meal', true, 'transport', true), 'busy')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  phone = VALUES(phone),
  department = VALUES(department),
  skills = VALUES(skills),
  available_status = VALUES(available_status);
