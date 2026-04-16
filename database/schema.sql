-- Zero-Shot Image Classifier Database Schema
-- =============================================

-- Create Database
CREATE DATABASE IF NOT EXISTS zero_shot_classifier;
USE zero_shot_classifier;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Predictions Table
CREATE TABLE IF NOT EXISTS predictions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    classification_result VARCHAR(100) NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_classification (classification_result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert admin user (email: admin123@gmail.com, password: admin123)
INSERT IGNORE INTO users (email, password_hash) VALUES (
    'admin123@gmail.com',
    'scrypt:32768:8:1$c9kw4R6w8jX5vN2p$1234567890abcdef1234567890abcdef1234567890abcdef'
);

-- Create indexes for better query performance
CREATE INDEX idx_predictions_user_timestamp ON predictions(user_id, timestamp DESC);
CREATE INDEX idx_feedback_user_timestamp ON feedback(user_id, timestamp DESC);

-- (Optional) Insert sample data for testing
INSERT INTO users (email, password_hash) VALUES
('user1@example.com', 'hash1'),
('user2@example.com', 'hash2');

INSERT INTO predictions (user_id, image_path, classification_result, confidence)
VALUES
(1, 'uploads/sample1.jpg', 'cat', 0.98),
(1, 'uploads/sample2.jpg', 'dog', 0.95),
(2, 'uploads/sample3.jpg', 'car', 0.92);

INSERT INTO feedback (user_id, message)
VALUES
(1, 'Great app!'),
(2, 'Needs more categories.');