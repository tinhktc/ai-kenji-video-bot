-- Video Library Database Schema
-- This file creates the complete database structure for the video processing system

-- Create database (uncomment if needed)
-- CREATE DATABASE IF NOT EXISTS video_library CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE video_library;

-- Source videos table
CREATE TABLE IF NOT EXISTS source_videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    original_url TEXT,
    file_path TEXT NOT NULL,
    uploader VARCHAR(255),
    upload_date VARCHAR(20),
    view_count BIGINT DEFAULT 0,
    description TEXT,
    tags JSON,
    duration FLOAT DEFAULT 0,
    file_size BIGINT DEFAULT 0,
    thumbnail_url TEXT,
    download_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_video_id (video_id),
    INDEX idx_title (title(100)),
    INDEX idx_uploader (uploader),
    INDEX idx_duration (duration)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Video shots table
CREATE TABLE IF NOT EXISTS video_shots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shot_id VARCHAR(255) UNIQUE NOT NULL,
    source_video_id INT,
    video_source TEXT NOT NULL,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    start_frame INT NOT NULL,
    end_frame INT NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    duration FLOAT NOT NULL,
    fps FLOAT NOT NULL,
    shot_index INT NOT NULL,
    file_size BIGINT DEFAULT 0,
    content_hash VARCHAR(64),
    quality_score FLOAT DEFAULT 0,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_video_id) REFERENCES source_videos(id) ON DELETE CASCADE,
    INDEX idx_shot_id (shot_id),
    INDEX idx_source_video (source_video_id),
    INDEX idx_duration (duration),
    INDEX idx_quality (quality_score),
    INDEX idx_content_hash (content_hash),
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Technical metadata table
CREATE TABLE IF NOT EXISTS technical_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shot_id INT NOT NULL,
    fps FLOAT,
    width INT,
    height INT,
    resolution VARCHAR(20),
    aspect_ratio FLOAT,
    frame_count INT,
    codec VARCHAR(10),
    bitrate_kbps FLOAT,
    pixel_count BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shot_id) REFERENCES video_shots(id) ON DELETE CASCADE,
    INDEX idx_resolution (resolution),
    INDEX idx_aspect_ratio (aspect_ratio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Visual metadata table
CREATE TABLE IF NOT EXISTS visual_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shot_id INT NOT NULL,
    avg_brightness FLOAT,
    brightness_category VARCHAR(20),
    avg_contrast FLOAT,
    contrast_category VARCHAR(20),
    avg_motion FLOAT,
    motion_category VARCHAR(20),
    dominant_colors JSON,
    color_diversity INT,
    frames_analyzed INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shot_id) REFERENCES video_shots(id) ON DELETE CASCADE,
    INDEX idx_brightness (avg_brightness),
    INDEX idx_contrast (avg_contrast),
    INDEX idx_motion (avg_motion),
    INDEX idx_brightness_cat (brightness_category),
    INDEX idx_motion_cat (motion_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audio metadata table
CREATE TABLE IF NOT EXISTS audio_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shot_id INT NOT NULL,
    has_audio BOOLEAN DEFAULT FALSE,
    sample_rate INT,
    volume_db FLOAT,
    volume_category VARCHAR(20),
    spectral_centroid_mean FLOAT,
    spectral_centroid_std FLOAT,
    spectral_rolloff_mean FLOAT,
    spectral_rolloff_std FLOAT,
    zero_crossing_rate_mean FLOAT,
    zero_crossing_rate_std FLOAT,
    mfcc_features JSON,
    tempo FLOAT,
    beat_count INT,
    energy_mean FLOAT,
    energy_std FLOAT,
    has_speech BOOLEAN DEFAULT FALSE,
    audio_type VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shot_id) REFERENCES video_shots(id) ON DELETE CASCADE,
    INDEX idx_has_audio (has_audio),
    INDEX idx_has_speech (has_speech),
    INDEX idx_audio_type (audio_type),
    INDEX idx_volume (volume_db)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Content metadata table (AI analysis)
CREATE TABLE IF NOT EXISTS content_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shot_id INT NOT NULL,
    caption TEXT,
    detected_objects JSON,
    scene_type VARCHAR(50),
    analysis_confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shot_id) REFERENCES video_shots(id) ON DELETE CASCADE,
    INDEX idx_scene_type (scene_type),
    FULLTEXT idx_caption (caption)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Keywords table
CREATE TABLE IF NOT EXISTS shot_keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shot_id INT NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shot_id) REFERENCES video_shots(id) ON DELETE CASCADE,
    UNIQUE KEY unique_shot_keyword (shot_id, keyword),
    INDEX idx_keyword (keyword),
    INDEX idx_shot_keyword (shot_id, keyword)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Processing status table
CREATE TABLE IF NOT EXISTS processing_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_path TEXT NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    total_shots INT DEFAULT 0,
    processed_shots INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_video_path (video_path(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;