#!/usr/bin/env python3
"""
Database Manager Module
Handles database operations for video shots and metadata storage
"""

import mysql.connector
from mysql.connector import Error
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize DatabaseManager
        
        Args:
            config: Database configuration dictionary
        """
        if config is None:
            config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'database': os.getenv('DB_NAME', 'video_library'),
                'user': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', ''),
                'port': int(os.getenv('DB_PORT', 3306)),
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': True,
            }
        
        self.config = config
        self.connection = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                logger.info("Successfully connected to MySQL database")
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise
    
    def _create_tables(self):
        """Create necessary database tables"""
        try:
            cursor = self.connection.cursor()
            
            # Source videos table
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Video shots table
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Technical metadata table
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Visual metadata table
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Audio metadata table
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Content metadata table (AI analysis)
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Keywords table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shot_keywords (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    shot_id INT NOT NULL,
                    keyword VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (shot_id) REFERENCES video_shots(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_shot_keyword (shot_id, keyword),
                    INDEX idx_keyword (keyword),
                    INDEX idx_shot_keyword (shot_id, keyword)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Processing status table
            cursor.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            cursor.close()
            logger.info("Database tables created successfully")
            
        except Error as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def insert_source_video(self, video_info: Dict) -> int:
        """Insert source video information and return video ID"""
        try:
            cursor = self.connection.cursor()
            
            query = """
                INSERT INTO source_videos (
                    video_id, title, original_url, file_path, uploader, upload_date,
                    view_count, description, tags, duration, file_size, thumbnail_url
                ) VALUES (
                    %(video_id)s, %(title)s, %(original_url)s, %(file_path)s, %(uploader)s, %(upload_date)s,
                    %(view_count)s, %(description)s, %(tags)s, %(duration)s, %(file_size)s, %(thumbnail_url)s
                ) ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    original_url = VALUES(original_url),
                    file_path = VALUES(file_path),
                    uploader = VALUES(uploader),
                    upload_date = VALUES(upload_date),
                    view_count = VALUES(view_count),
                    description = VALUES(description),
                    tags = VALUES(tags),
                    duration = VALUES(duration),
                    file_size = VALUES(file_size),
                    thumbnail_url = VALUES(thumbnail_url),
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # Prepare data
            data = {
                'video_id': video_info.get('video_id', ''),
                'title': video_info.get('title', ''),
                'original_url': video_info.get('original_url', ''),
                'file_path': video_info.get('file_path', ''),
                'uploader': video_info.get('uploader', ''),
                'upload_date': video_info.get('upload_date', ''),
                'view_count': video_info.get('view_count', 0),
                'description': video_info.get('description', ''),
                'tags': json.dumps(video_info.get('tags', [])),
                'duration': video_info.get('duration', 0),
                'file_size': video_info.get('file_size', 0),
                'thumbnail_url': video_info.get('thumbnail_url', ''),
            }
            
            cursor.execute(query, data)
            video_db_id = cursor.lastrowid
            
            # If it was an update, get the existing ID
            if video_db_id == 0:
                cursor.execute("SELECT id FROM source_videos WHERE video_id = %s", (video_info.get('video_id'),))
                result = cursor.fetchone()
                video_db_id = result[0] if result else None
            
            cursor.close()
            logger.info(f"Inserted/updated source video: {video_info.get('title', 'Unknown')}")
            return video_db_id
            
        except Error as e:
            logger.error(f"Error inserting source video: {e}")
            raise
    
    def insert_shot_with_metadata(self, shot_metadata: Dict, source_video_db_id: Optional[int] = None) -> int:
        """Insert shot and all its metadata"""
        try:
            cursor = self.connection.cursor()
            
            # Insert main shot record
            shot_query = """
                INSERT INTO video_shots (
                    shot_id, source_video_id, video_source, file_path, thumbnail_path,
                    start_frame, end_frame, start_time, end_time, duration, fps,
                    shot_index, file_size, content_hash, quality_score
                ) VALUES (
                    %(shot_id)s, %(source_video_id)s, %(video_source)s, %(file_path)s, %(thumbnail_path)s,
                    %(start_frame)s, %(end_frame)s, %(start_time)s, %(end_time)s, %(duration)s, %(fps)s,
                    %(shot_index)s, %(file_size)s, %(content_hash)s, %(quality_score)s
                ) ON DUPLICATE KEY UPDATE
                    file_path = VALUES(file_path),
                    thumbnail_path = VALUES(thumbnail_path),
                    file_size = VALUES(file_size),
                    content_hash = VALUES(content_hash),
                    quality_score = VALUES(quality_score),
                    updated_at = CURRENT_TIMESTAMP
            """
            
            shot_data = {
                'shot_id': shot_metadata.get('shot_id', ''),
                'source_video_id': source_video_db_id,
                'video_source': shot_metadata.get('video_source', ''),
                'file_path': shot_metadata.get('file_path', ''),
                'thumbnail_path': shot_metadata.get('thumbnail_path', ''),
                'start_frame': shot_metadata.get('start_frame', 0),
                'end_frame': shot_metadata.get('end_frame', 0),
                'start_time': shot_metadata.get('start_time', 0),
                'end_time': shot_metadata.get('end_time', 0),
                'duration': shot_metadata.get('duration', 0),
                'fps': shot_metadata.get('fps', 0),
                'shot_index': shot_metadata.get('shot_index', 0),
                'file_size': shot_metadata.get('file_size', 0),
                'content_hash': shot_metadata.get('content_hash', ''),
                'quality_score': shot_metadata.get('quality_score', 0),
            }
            
            cursor.execute(shot_query, shot_data)
            shot_db_id = cursor.lastrowid
            
            # If it was an update, get the existing ID
            if shot_db_id == 0:
                cursor.execute("SELECT id FROM video_shots WHERE shot_id = %s", (shot_metadata.get('shot_id'),))
                result = cursor.fetchone()
                shot_db_id = result[0] if result else None
            
            if not shot_db_id:
                raise Exception("Failed to get shot database ID")
            
            # Insert technical metadata
            technical = shot_metadata.get('technical', {})
            if technical and not technical.get('error'):
                self._insert_technical_metadata(cursor, shot_db_id, technical)
            
            # Insert visual metadata
            visual = shot_metadata.get('visual', {})
            if visual and not visual.get('error'):
                self._insert_visual_metadata(cursor, shot_db_id, visual)
            
            # Insert audio metadata
            audio = shot_metadata.get('audio', {})
            if audio:
                self._insert_audio_metadata(cursor, shot_db_id, audio)
            
            # Insert content metadata
            content = shot_metadata.get('content', {})
            if content and not content.get('error'):
                self._insert_content_metadata(cursor, shot_db_id, content)
            
            # Insert keywords
            keywords = shot_metadata.get('keywords', [])
            if keywords:
                self._insert_keywords(cursor, shot_db_id, keywords)
            
            cursor.close()
            logger.info(f"Inserted shot with metadata: {shot_metadata.get('shot_id', 'Unknown')}")
            return shot_db_id
            
        except Error as e:
            logger.error(f"Error inserting shot metadata: {e}")
            raise
    
    def _insert_technical_metadata(self, cursor, shot_db_id: int, technical: Dict):
        """Insert technical metadata"""
        query = """
            INSERT INTO technical_metadata (
                shot_id, fps, width, height, resolution, aspect_ratio,
                frame_count, codec, bitrate_kbps, pixel_count
            ) VALUES (
                %(shot_id)s, %(fps)s, %(width)s, %(height)s, %(resolution)s, %(aspect_ratio)s,
                %(frame_count)s, %(codec)s, %(bitrate_kbps)s, %(pixel_count)s
            ) ON DUPLICATE KEY UPDATE
                fps = VALUES(fps),
                width = VALUES(width),
                height = VALUES(height),
                resolution = VALUES(resolution),
                aspect_ratio = VALUES(aspect_ratio),
                frame_count = VALUES(frame_count),
                codec = VALUES(codec),
                bitrate_kbps = VALUES(bitrate_kbps),
                pixel_count = VALUES(pixel_count)
        """
        
        data = {
            'shot_id': shot_db_id,
            'fps': technical.get('fps', 0),
            'width': technical.get('width', 0),
            'height': technical.get('height', 0),
            'resolution': technical.get('resolution', ''),
            'aspect_ratio': technical.get('aspect_ratio', 0),
            'frame_count': technical.get('frame_count', 0),
            'codec': technical.get('codec', ''),
            'bitrate_kbps': technical.get('bitrate_kbps', 0),
            'pixel_count': technical.get('pixel_count', 0),
        }
        
        cursor.execute(query, data)
    
    def _insert_visual_metadata(self, cursor, shot_db_id: int, visual: Dict):
        """Insert visual metadata"""
        query = """
            INSERT INTO visual_metadata (
                shot_id, avg_brightness, brightness_category, avg_contrast, contrast_category,
                avg_motion, motion_category, dominant_colors, color_diversity, frames_analyzed
            ) VALUES (
                %(shot_id)s, %(avg_brightness)s, %(brightness_category)s, %(avg_contrast)s, %(contrast_category)s,
                %(avg_motion)s, %(motion_category)s, %(dominant_colors)s, %(color_diversity)s, %(frames_analyzed)s
            ) ON DUPLICATE KEY UPDATE
                avg_brightness = VALUES(avg_brightness),
                brightness_category = VALUES(brightness_category),
                avg_contrast = VALUES(avg_contrast),
                contrast_category = VALUES(contrast_category),
                avg_motion = VALUES(avg_motion),
                motion_category = VALUES(motion_category),
                dominant_colors = VALUES(dominant_colors),
                color_diversity = VALUES(color_diversity),
                frames_analyzed = VALUES(frames_analyzed)
        """
        
        brightness = visual.get('brightness', {})
        contrast = visual.get('contrast', {})
        motion = visual.get('motion', {})
        
        data = {
            'shot_id': shot_db_id,
            'avg_brightness': brightness.get('average', 0),
            'brightness_category': brightness.get('category', ''),
            'avg_contrast': contrast.get('average', 0),
            'contrast_category': contrast.get('category', ''),
            'avg_motion': motion.get('average', 0),
            'motion_category': motion.get('category', ''),
            'dominant_colors': json.dumps(visual.get('dominant_colors', [])),
            'color_diversity': visual.get('color_diversity', 0),
            'frames_analyzed': visual.get('frames_analyzed', 0),
        }
        
        cursor.execute(query, data)
    
    def _insert_audio_metadata(self, cursor, shot_db_id: int, audio: Dict):
        """Insert audio metadata"""
        query = """
            INSERT INTO audio_metadata (
                shot_id, has_audio, sample_rate, volume_db, volume_category,
                spectral_centroid_mean, spectral_centroid_std, spectral_rolloff_mean, spectral_rolloff_std,
                zero_crossing_rate_mean, zero_crossing_rate_std, mfcc_features,
                tempo, beat_count, energy_mean, energy_std, has_speech, audio_type
            ) VALUES (
                %(shot_id)s, %(has_audio)s, %(sample_rate)s, %(volume_db)s, %(volume_category)s,
                %(spectral_centroid_mean)s, %(spectral_centroid_std)s, %(spectral_rolloff_mean)s, %(spectral_rolloff_std)s,
                %(zero_crossing_rate_mean)s, %(zero_crossing_rate_std)s, %(mfcc_features)s,
                %(tempo)s, %(beat_count)s, %(energy_mean)s, %(energy_std)s, %(has_speech)s, %(audio_type)s
            ) ON DUPLICATE KEY UPDATE
                has_audio = VALUES(has_audio),
                sample_rate = VALUES(sample_rate),
                volume_db = VALUES(volume_db),
                volume_category = VALUES(volume_category),
                spectral_centroid_mean = VALUES(spectral_centroid_mean),
                spectral_centroid_std = VALUES(spectral_centroid_std),
                spectral_rolloff_mean = VALUES(spectral_rolloff_mean),
                spectral_rolloff_std = VALUES(spectral_rolloff_std),
                zero_crossing_rate_mean = VALUES(zero_crossing_rate_mean),
                zero_crossing_rate_std = VALUES(zero_crossing_rate_std),
                mfcc_features = VALUES(mfcc_features),
                tempo = VALUES(tempo),
                beat_count = VALUES(beat_count),
                energy_mean = VALUES(energy_mean),
                energy_std = VALUES(energy_std),
                has_speech = VALUES(has_speech),
                audio_type = VALUES(audio_type)
        """
        
        spectral_centroid = audio.get('spectral_centroid', {})
        spectral_rolloff = audio.get('spectral_rolloff', {})
        zero_crossing_rate = audio.get('zero_crossing_rate', {})
        energy = audio.get('energy', {})
        
        data = {
            'shot_id': shot_db_id,
            'has_audio': audio.get('has_audio', False),
            'sample_rate': audio.get('sample_rate', 0),
            'volume_db': audio.get('volume_db', -60),
            'volume_category': audio.get('volume_category', ''),
            'spectral_centroid_mean': spectral_centroid.get('mean', 0),
            'spectral_centroid_std': spectral_centroid.get('std', 0),
            'spectral_rolloff_mean': spectral_rolloff.get('mean', 0),
            'spectral_rolloff_std': spectral_rolloff.get('std', 0),
            'zero_crossing_rate_mean': zero_crossing_rate.get('mean', 0),
            'zero_crossing_rate_std': zero_crossing_rate.get('std', 0),
            'mfcc_features': json.dumps(audio.get('mfcc_features', {})),
            'tempo': audio.get('tempo', 0),
            'beat_count': audio.get('beat_count', 0),
            'energy_mean': energy.get('mean', 0),
            'energy_std': energy.get('std', 0),
            'has_speech': audio.get('has_speech', False),
            'audio_type': audio.get('audio_type', ''),
        }
        
        cursor.execute(query, data)
    
    def _insert_content_metadata(self, cursor, shot_db_id: int, content: Dict):
        """Insert content metadata"""
        query = """
            INSERT INTO content_metadata (
                shot_id, caption, detected_objects, scene_type, analysis_confidence
            ) VALUES (
                %(shot_id)s, %(caption)s, %(detected_objects)s, %(scene_type)s, %(analysis_confidence)s
            ) ON DUPLICATE KEY UPDATE
                caption = VALUES(caption),
                detected_objects = VALUES(detected_objects),
                scene_type = VALUES(scene_type),
                analysis_confidence = VALUES(analysis_confidence)
        """
        
        data = {
            'shot_id': shot_db_id,
            'caption': content.get('caption', ''),
            'detected_objects': json.dumps(content.get('detected_objects', [])),
            'scene_type': content.get('scene_type', ''),
            'analysis_confidence': content.get('analysis_confidence', 0),
        }
        
        cursor.execute(query, data)
    
    def _insert_keywords(self, cursor, shot_db_id: int, keywords: List[str]):
        """Insert keywords"""
        # First, delete existing keywords for this shot
        cursor.execute("DELETE FROM shot_keywords WHERE shot_id = %s", (shot_db_id,))
        
        # Insert new keywords
        if keywords:
            query = "INSERT INTO shot_keywords (shot_id, keyword) VALUES (%s, %s)"
            data = [(shot_db_id, keyword) for keyword in keywords]
            cursor.executemany(query, data)
    
    def search_shots(self, filters: Dict = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Search for shots based on various filters"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Base query
            query = """
                SELECT 
                    vs.*,
                    sv.title as source_title,
                    sv.uploader as source_uploader,
                    tm.resolution, tm.fps as tech_fps, tm.aspect_ratio,
                    vm.avg_brightness, vm.brightness_category, vm.avg_motion, vm.motion_category,
                    am.has_audio, am.has_speech, am.audio_type, am.volume_category,
                    cm.caption, cm.scene_type,
                    GROUP_CONCAT(sk.keyword) as keywords
                FROM video_shots vs
                LEFT JOIN source_videos sv ON vs.source_video_id = sv.id
                LEFT JOIN technical_metadata tm ON vs.id = tm.shot_id
                LEFT JOIN visual_metadata vm ON vs.id = vm.shot_id
                LEFT JOIN audio_metadata am ON vs.id = am.shot_id
                LEFT JOIN content_metadata cm ON vs.id = cm.shot_id
                LEFT JOIN shot_keywords sk ON vs.id = sk.shot_id
            """
            
            conditions = []
            params = []
            
            if filters:
                # Duration filter
                if 'min_duration' in filters:
                    conditions.append("vs.duration >= %s")
                    params.append(filters['min_duration'])
                
                if 'max_duration' in filters:
                    conditions.append("vs.duration <= %s")
                    params.append(filters['max_duration'])
                
                # Quality filter
                if 'min_quality' in filters:
                    conditions.append("vs.quality_score >= %s")
                    params.append(filters['min_quality'])
                
                # Resolution filter
                if 'resolution' in filters:
                    conditions.append("tm.resolution = %s")
                    params.append(filters['resolution'])
                
                # Motion filter
                if 'motion_category' in filters:
                    conditions.append("vm.motion_category = %s")
                    params.append(filters['motion_category'])
                
                # Audio filters
                if 'has_audio' in filters:
                    conditions.append("am.has_audio = %s")
                    params.append(filters['has_audio'])
                
                if 'has_speech' in filters:
                    conditions.append("am.has_speech = %s")
                    params.append(filters['has_speech'])
                
                # Scene type filter
                if 'scene_type' in filters:
                    conditions.append("cm.scene_type = %s")
                    params.append(filters['scene_type'])
                
                # Keyword filter
                if 'keywords' in filters:
                    keyword_conditions = []
                    for keyword in filters['keywords']:
                        keyword_conditions.append("sk.keyword LIKE %s")
                        params.append(f"%{keyword}%")
                    if keyword_conditions:
                        conditions.append(f"({' OR '.join(keyword_conditions)})")
                
                # Caption search
                if 'caption_search' in filters:
                    conditions.append("MATCH(cm.caption) AGAINST(%s IN NATURAL LANGUAGE MODE)")
                    params.append(filters['caption_search'])
                
                # Source video filter
                if 'source_video_id' in filters:
                    conditions.append("sv.video_id = %s")
                    params.append(filters['source_video_id'])
            
            # Add conditions to query
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Group by shot
            query += " GROUP BY vs.id"
            
            # Order by quality score and creation date
            query += " ORDER BY vs.quality_score DESC, vs.created_at DESC"
            
            # Add limit and offset
            query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Process results
            for result in results:
                if result['keywords']:
                    result['keywords'] = result['keywords'].split(',')
                else:
                    result['keywords'] = []
            
            cursor.close()
            return results
            
        except Error as e:
            logger.error(f"Error searching shots: {e}")
            return []
    
    def get_shot_by_id(self, shot_id: str) -> Optional[Dict]:
        """Get complete shot information by shot_id"""
        results = self.search_shots({'shot_id': shot_id}, limit=1)
        return results[0] if results else None
    
    def get_statistics(self) -> Dict:
        """Get library statistics"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            stats = {}
            
            # Basic counts
            cursor.execute("SELECT COUNT(*) as count FROM source_videos")
            stats['total_source_videos'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM video_shots")
            stats['total_shots'] = cursor.fetchone()['count']
            
            # Duration statistics
            cursor.execute("SELECT SUM(duration) as total, AVG(duration) as avg FROM video_shots")
            duration_stats = cursor.fetchone()
            stats['total_duration'] = round(duration_stats['total'] or 0, 2)
            stats['average_shot_duration'] = round(duration_stats['avg'] or 0, 2)
            
            # Quality statistics
            cursor.execute("SELECT AVG(quality_score) as avg, MIN(quality_score) as min, MAX(quality_score) as max FROM video_shots")
            quality_stats = cursor.fetchone()
            stats['average_quality'] = round(quality_stats['avg'] or 0, 3)
            stats['min_quality'] = round(quality_stats['min'] or 0, 3)
            stats['max_quality'] = round(quality_stats['max'] or 0, 3)
            
            # Resolution distribution
            cursor.execute("SELECT tm.resolution, COUNT(*) as count FROM technical_metadata tm GROUP BY tm.resolution ORDER BY count DESC LIMIT 10")
            stats['resolution_distribution'] = cursor.fetchall()
            
            # Motion distribution
            cursor.execute("SELECT vm.motion_category, COUNT(*) as count FROM visual_metadata vm GROUP BY vm.motion_category")
            stats['motion_distribution'] = cursor.fetchall()
            
            # Audio statistics
            cursor.execute("SELECT COUNT(*) as count FROM audio_metadata WHERE has_audio = TRUE")
            stats['shots_with_audio'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM audio_metadata WHERE has_speech = TRUE")
            stats['shots_with_speech'] = cursor.fetchone()['count']
            
            # Top keywords
            cursor.execute("SELECT keyword, COUNT(*) as count FROM shot_keywords GROUP BY keyword ORDER BY count DESC LIMIT 20")
            stats['top_keywords'] = cursor.fetchall()
            
            cursor.close()
            return stats
            
        except Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def update_processing_status(self, video_path: str, status: str, **kwargs):
        """Update processing status for a video"""
        try:
            cursor = self.connection.cursor()
            
            # Check if record exists
            cursor.execute("SELECT id FROM processing_status WHERE video_path = %s", (video_path,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                update_fields = ["status = %s"]
                params = [status]
                
                if 'total_shots' in kwargs:
                    update_fields.append("total_shots = %s")
                    params.append(kwargs['total_shots'])
                
                if 'processed_shots' in kwargs:
                    update_fields.append("processed_shots = %s")
                    params.append(kwargs['processed_shots'])
                
                if 'error_message' in kwargs:
                    update_fields.append("error_message = %s")
                    params.append(kwargs['error_message'])
                
                if status == 'processing':
                    update_fields.append("started_at = CURRENT_TIMESTAMP")
                elif status in ['completed', 'failed']:
                    update_fields.append("completed_at = CURRENT_TIMESTAMP")
                
                params.append(video_path)
                
                query = f"UPDATE processing_status SET {', '.join(update_fields)} WHERE video_path = %s"
                cursor.execute(query, params)
                
            else:
                # Insert new record
                query = """
                    INSERT INTO processing_status (video_path, status, total_shots, processed_shots, error_message, started_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = [
                    video_path,
                    status,
                    kwargs.get('total_shots', 0),
                    kwargs.get('processed_shots', 0),
                    kwargs.get('error_message'),
                    datetime.now() if status == 'processing' else None
                ]
                cursor.execute(query, params)
            
            cursor.close()
            
        except Error as e:
            logger.error(f"Error updating processing status: {e}")
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    # Example usage
    db = DatabaseManager()
    
    # Get statistics
    stats = db.get_statistics()
    print("Library Statistics:")
    print(json.dumps(stats, indent=2, default=str))
    
    # Search example
    filters = {
        'min_duration': 2.0,
        'max_duration': 10.0,
        'has_audio': True,
    }
    
    results = db.search_shots(filters, limit=10)
    print(f"\nFound {len(results)} shots matching criteria")
    
    db.close()