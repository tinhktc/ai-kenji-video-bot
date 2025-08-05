#!/usr/bin/env python3
"""
Metadata Extraction Module
Extracts comprehensive metadata from video shots including technical info,
content analysis, and AI-generated descriptions
"""

import cv2
import numpy as np
import os
import json
import hashlib
import librosa
import speech_recognition as sr
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from PIL import Image, ImageStat
import imagehash
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from collections import Counter
import requests
from transformers import pipeline, BlipProcessor, BlipForConditionalGeneration
import torch

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataExtractor:
    def __init__(self, use_ai_analysis: bool = True):
        """
        Initialize MetadataExtractor
        
        Args:
            use_ai_analysis: Whether to use AI models for content analysis
        """
        self.use_ai_analysis = use_ai_analysis
        
        # Initialize AI models if enabled
        self.image_captioning_model = None
        self.image_captioning_processor = None
        
        if use_ai_analysis:
            try:
                # Load BLIP model for image captioning
                self.image_captioning_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                self.image_captioning_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
                logger.info("AI models loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load AI models: {e}")
                self.use_ai_analysis = False
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
    
    def extract_shot_metadata(self, shot_info: Dict) -> Dict:
        """
        Extract comprehensive metadata for a video shot
        
        Args:
            shot_info: Shot information dictionary
            
        Returns:
            Enhanced shot metadata dictionary
        """
        logger.info(f"Extracting metadata for shot: {shot_info['shot_id']}")
        
        video_path = shot_info['file_path']
        metadata = shot_info.copy()
        
        try:
            # Technical metadata
            technical_data = self._extract_technical_metadata(video_path)
            metadata['technical'] = technical_data
            
            # Visual analysis
            visual_data = self._analyze_visual_content(video_path)
            metadata['visual'] = visual_data
            
            # Audio analysis
            audio_data = self._analyze_audio_content(video_path)
            metadata['audio'] = audio_data
            
            # Content analysis with AI
            if self.use_ai_analysis:
                content_data = self._analyze_content_with_ai(video_path)
                metadata['content'] = content_data
            
            # Generate keywords and tags
            keywords = self._generate_keywords(metadata)
            metadata['keywords'] = keywords
            
            # Generate content hash for deduplication
            content_hash = self._generate_content_hash(video_path)
            metadata['content_hash'] = content_hash
            
            # Quality assessment
            quality_score = self._assess_quality(metadata)
            metadata['quality_score'] = quality_score
            
            metadata['metadata_extracted_at'] = datetime.now().isoformat()
            
            logger.info(f"Successfully extracted metadata for {shot_info['shot_id']}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata for {shot_info['shot_id']}: {str(e)}")
            metadata['metadata_error'] = str(e)
            return metadata
    
    def _extract_technical_metadata(self, video_path: str) -> Dict:
        """Extract technical video properties"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return {'error': 'Cannot open video file'}
        
        # Basic properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # Codec information
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
        
        # File size
        file_size = os.path.getsize(video_path)
        
        # Bitrate estimation
        bitrate = (file_size * 8) / (duration * 1000) if duration > 0 else 0  # kbps
        
        cap.release()
        
        return {
            'fps': fps,
            'width': width,
            'height': height,
            'resolution': f"{width}x{height}",
            'aspect_ratio': round(width / height, 2) if height > 0 else 0,
            'frame_count': frame_count,
            'duration': duration,
            'codec': codec,
            'file_size': file_size,
            'bitrate_kbps': round(bitrate, 2),
            'pixel_count': width * height,
        }
    
    def _analyze_visual_content(self, video_path: str) -> Dict:
        """Analyze visual content of the video"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return {'error': 'Cannot open video file'}
        
        # Sample frames for analysis
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_frames = min(10, frame_count)  # Sample up to 10 frames
        frame_indices = np.linspace(0, frame_count - 1, sample_frames, dtype=int)
        
        # Initialize analysis variables
        brightness_values = []
        contrast_values = []
        color_histograms = []
        dominant_colors = []
        motion_scores = []
        
        prev_frame = None
        
        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Brightness analysis
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            brightness_values.append(brightness)
            
            # Contrast analysis
            contrast = np.std(gray)
            contrast_values.append(contrast)
            
            # Color analysis
            hist = self._calculate_color_histogram(frame)
            color_histograms.append(hist)
            
            # Dominant colors
            colors = self._extract_dominant_colors(frame)
            dominant_colors.append(colors)
            
            # Motion analysis
            if prev_frame is not None:
                motion = self._calculate_motion_score(prev_frame, frame)
                motion_scores.append(motion)
            
            prev_frame = gray.copy()
        
        cap.release()
        
        # Calculate statistics
        avg_brightness = np.mean(brightness_values) if brightness_values else 0
        avg_contrast = np.mean(contrast_values) if contrast_values else 0
        avg_motion = np.mean(motion_scores) if motion_scores else 0
        
        # Overall dominant colors
        all_colors = [color for colors in dominant_colors for color in colors]
        overall_dominant = self._get_most_common_colors(all_colors)
        
        return {
            'brightness': {
                'average': round(avg_brightness, 2),
                'min': round(min(brightness_values), 2) if brightness_values else 0,
                'max': round(max(brightness_values), 2) if brightness_values else 0,
                'category': self._categorize_brightness(avg_brightness),
            },
            'contrast': {
                'average': round(avg_contrast, 2),
                'category': self._categorize_contrast(avg_contrast),
            },
            'motion': {
                'average': round(avg_motion, 2),
                'category': self._categorize_motion(avg_motion),
            },
            'dominant_colors': overall_dominant,
            'color_diversity': len(set(all_colors)),
            'frames_analyzed': len(frame_indices),
        }
    
    def _analyze_audio_content(self, video_path: str) -> Dict:
        """Analyze audio content of the video"""
        try:
            # Extract audio features using librosa
            y, sr = librosa.load(video_path, sr=None)
            
            # Basic audio properties
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
            
            # MFCC features
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            
            # Tempo and beat
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            # RMS energy
            rms = librosa.feature.rms(y=y)[0]
            
            # Speech detection (basic)
            has_speech = self._detect_speech_basic(y, sr)
            
            # Volume analysis
            volume_db = 20 * np.log10(np.sqrt(np.mean(y**2)))
            
            return {
                'duration': round(duration, 2),
                'sample_rate': sr,
                'has_audio': True,
                'volume_db': round(volume_db, 2) if not np.isnan(volume_db) else -60,
                'volume_category': self._categorize_volume(volume_db),
                'spectral_centroid': {
                    'mean': round(np.mean(spectral_centroids), 2),
                    'std': round(np.std(spectral_centroids), 2),
                },
                'spectral_rolloff': {
                    'mean': round(np.mean(spectral_rolloff), 2),
                    'std': round(np.std(spectral_rolloff), 2),
                },
                'zero_crossing_rate': {
                    'mean': round(np.mean(zero_crossing_rate), 4),
                    'std': round(np.std(zero_crossing_rate), 4),
                },
                'mfcc_features': {
                    'mean': [round(x, 4) for x in np.mean(mfccs, axis=1)],
                    'std': [round(x, 4) for x in np.std(mfccs, axis=1)],
                },
                'tempo': round(tempo, 2),
                'beat_count': len(beats),
                'energy': {
                    'mean': round(np.mean(rms), 4),
                    'std': round(np.std(rms), 4),
                },
                'has_speech': has_speech,
                'audio_type': self._classify_audio_type(tempo, has_speech, np.mean(spectral_centroids)),
            }
            
        except Exception as e:
            logger.error(f"Error analyzing audio: {str(e)}")
            return {
                'has_audio': False,
                'error': str(e),
            }
    
    def _analyze_content_with_ai(self, video_path: str) -> Dict:
        """Analyze content using AI models"""
        if not self.use_ai_analysis:
            return {'ai_analysis_disabled': True}
        
        try:
            # Extract middle frame for analysis
            cap = cv2.VideoCapture(video_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            middle_frame_idx = frame_count // 2
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return {'error': 'Cannot extract frame for analysis'}
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Generate caption
            caption = self._generate_image_caption(pil_image)
            
            # Object detection (simplified)
            objects = self._detect_objects_simple(frame)
            
            # Scene classification
            scene_type = self._classify_scene(frame)
            
            return {
                'caption': caption,
                'detected_objects': objects,
                'scene_type': scene_type,
                'analysis_confidence': 0.8,  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error in AI content analysis: {str(e)}")
            return {'error': str(e)}
    
    def _generate_image_caption(self, image: Image.Image) -> str:
        """Generate caption for image using BLIP model"""
        try:
            if self.image_captioning_model is None or self.image_captioning_processor is None:
                return "AI captioning not available"
            
            inputs = self.image_captioning_processor(image, return_tensors="pt")
            out = self.image_captioning_model.generate(**inputs, max_length=50)
            caption = self.image_captioning_processor.decode(out[0], skip_special_tokens=True)
            
            return caption
            
        except Exception as e:
            logger.error(f"Error generating caption: {str(e)}")
            return "Caption generation failed"
    
    def _calculate_color_histogram(self, frame: np.ndarray) -> np.ndarray:
        """Calculate color histogram for frame"""
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Calculate histogram
        hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [60], [0, 256])
        
        # Concatenate and normalize
        hist = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])
        return cv2.normalize(hist, hist).flatten()
    
    def _extract_dominant_colors(self, frame: np.ndarray, k: int = 5) -> List[str]:
        """Extract dominant colors from frame"""
        try:
            # Reshape frame to be a list of pixels
            data = frame.reshape((-1, 3))
            
            # Use KMeans to find dominant colors
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(data)
            
            # Get colors and convert to hex
            colors = []
            for center in kmeans.cluster_centers_:
                # Convert BGR to RGB
                rgb = center[::-1]
                hex_color = '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
                colors.append(hex_color)
            
            return colors
            
        except Exception:
            return ['#000000']  # Default to black if extraction fails
    
    def _get_most_common_colors(self, colors: List[str], top_n: int = 5) -> List[str]:
        """Get most common colors from a list"""
        color_counts = Counter(colors)
        return [color for color, count in color_counts.most_common(top_n)]
    
    def _calculate_motion_score(self, prev_frame: np.ndarray, current_frame: np.ndarray) -> float:
        """Calculate motion score between frames"""
        try:
            current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate optical flow
            flow = cv2.calcOpticalFlowPyrLK(
                prev_frame, current_gray,
                cv2.goodFeaturesToTrack(prev_frame, maxCorners=100, qualityLevel=0.3, minDistance=7),
                None
            )[0]
            
            if flow is not None and len(flow) > 0:
                flow_magnitude = np.mean(np.sqrt(flow[:, 0]**2 + flow[:, 1]**2))
                return min(flow_magnitude / 10.0, 1.0)  # Normalize to 0-1
            
        except Exception:
            pass
        
        return 0.0
    
    def _detect_speech_basic(self, audio_data: np.ndarray, sample_rate: int) -> bool:
        """Basic speech detection using energy and spectral features"""
        try:
            # Calculate spectral centroid
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate))
            
            # Calculate zero crossing rate
            zcr = np.mean(librosa.feature.zero_crossing_rate(audio_data))
            
            # Calculate RMS energy
            rms = np.mean(librosa.feature.rms(y=audio_data))
            
            # Simple heuristic for speech detection
            # Speech typically has moderate spectral centroid, moderate ZCR, and sufficient energy
            has_speech = (
                1000 < spectral_centroid < 4000 and  # Typical speech frequency range
                0.01 < zcr < 0.15 and  # Moderate zero crossing rate
                rms > 0.01  # Sufficient energy
            )
            
            return has_speech
            
        except Exception:
            return False
    
    def _detect_objects_simple(self, frame: np.ndarray) -> List[str]:
        """Simple object detection using basic computer vision"""
        objects = []
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Face detection
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                objects.append('face')
            
            # Edge detection for general objects
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Classify contours by size and shape
            large_objects = [c for c in contours if cv2.contourArea(c) > 1000]
            if len(large_objects) > 5:
                objects.append('multiple_objects')
            elif len(large_objects) > 0:
                objects.append('objects')
            
        except Exception:
            pass
        
        return objects if objects else ['unknown']
    
    def _classify_scene(self, frame: np.ndarray) -> str:
        """Classify scene type based on visual features"""
        try:
            # Calculate basic features
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Edge density
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Color variance
            color_variance = np.var(frame)
            
            # Brightness
            brightness = np.mean(gray)
            
            # Simple scene classification
            if edge_density > 0.1:
                return 'complex_scene'
            elif brightness > 200:
                return 'bright_scene'
            elif brightness < 50:
                return 'dark_scene'
            elif color_variance > 1000:
                return 'colorful_scene'
            else:
                return 'simple_scene'
                
        except Exception:
            return 'unknown_scene'
    
    def _generate_keywords(self, metadata: Dict) -> List[str]:
        """Generate keywords based on extracted metadata"""
        keywords = []
        
        # Technical keywords
        tech = metadata.get('technical', {})
        resolution = tech.get('resolution', '')
        if resolution:
            keywords.append(f"resolution_{resolution}")
        
        fps = tech.get('fps', 0)
        if fps >= 60:
            keywords.append('high_fps')
        elif fps >= 30:
            keywords.append('standard_fps')
        else:
            keywords.append('low_fps')
        
        # Visual keywords
        visual = metadata.get('visual', {})
        brightness_cat = visual.get('brightness', {}).get('category', '')
        if brightness_cat:
            keywords.append(f"brightness_{brightness_cat}")
        
        motion_cat = visual.get('motion', {}).get('category', '')
        if motion_cat:
            keywords.append(f"motion_{motion_cat}")
        
        # Audio keywords
        audio = metadata.get('audio', {})
        if audio.get('has_audio', False):
            keywords.append('has_audio')
            if audio.get('has_speech', False):
                keywords.append('has_speech')
            
            audio_type = audio.get('audio_type', '')
            if audio_type:
                keywords.append(f"audio_{audio_type}")
        else:
            keywords.append('no_audio')
        
        # Content keywords
        content = metadata.get('content', {})
        objects = content.get('detected_objects', [])
        keywords.extend([f"object_{obj}" for obj in objects])
        
        scene_type = content.get('scene_type', '')
        if scene_type:
            keywords.append(f"scene_{scene_type}")
        
        # Duration keywords
        duration = metadata.get('duration', 0)
        if duration < 3:
            keywords.append('very_short')
        elif duration < 10:
            keywords.append('short')
        elif duration < 30:
            keywords.append('medium')
        else:
            keywords.append('long')
        
        return list(set(keywords))  # Remove duplicates
    
    def _generate_content_hash(self, video_path: str) -> str:
        """Generate content hash for deduplication"""
        try:
            # Extract a few frames and create hash
            cap = cv2.VideoCapture(video_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Sample 5 frames
            sample_indices = np.linspace(0, frame_count - 1, 5, dtype=int)
            frames_data = []
            
            for idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    # Resize to small size for hashing
                    small_frame = cv2.resize(frame, (64, 64))
                    frames_data.append(small_frame.tobytes())
            
            cap.release()
            
            # Create hash from combined frame data
            combined_data = b''.join(frames_data)
            content_hash = hashlib.md5(combined_data).hexdigest()
            
            return content_hash
            
        except Exception:
            # Fallback to file hash
            return hashlib.md5(open(video_path, 'rb').read()).hexdigest()
    
    def _assess_quality(self, metadata: Dict) -> float:
        """Assess overall quality score (0-1)"""
        score = 0.0
        factors = 0
        
        # Technical quality
        tech = metadata.get('technical', {})
        resolution = tech.get('pixel_count', 0)
        if resolution > 2000000:  # > 1080p
            score += 0.3
        elif resolution > 900000:  # > 720p
            score += 0.2
        else:
            score += 0.1
        factors += 1
        
        fps = tech.get('fps', 0)
        if fps >= 30:
            score += 0.2
        elif fps >= 24:
            score += 0.15
        else:
            score += 0.1
        factors += 1
        
        # Visual quality
        visual = metadata.get('visual', {})
        contrast = visual.get('contrast', {}).get('average', 0)
        if contrast > 50:
            score += 0.2
        elif contrast > 30:
            score += 0.15
        else:
            score += 0.1
        factors += 1
        
        # Audio quality
        audio = metadata.get('audio', {})
        if audio.get('has_audio', False):
            volume_db = audio.get('volume_db', -60)
            if volume_db > -20:
                score += 0.2
            elif volume_db > -40:
                score += 0.15
            else:
                score += 0.1
        else:
            score += 0.05  # Lower score for no audio
        factors += 1
        
        # Duration appropriateness
        duration = metadata.get('duration', 0)
        if 2 <= duration <= 15:  # Ideal for short-form content
            score += 0.1
        else:
            score += 0.05
        factors += 1
        
        return min(score / factors if factors > 0 else 0.0, 1.0)
    
    # Helper methods for categorization
    def _categorize_brightness(self, brightness: float) -> str:
        if brightness > 200:
            return 'very_bright'
        elif brightness > 150:
            return 'bright'
        elif brightness > 100:
            return 'normal'
        elif brightness > 50:
            return 'dark'
        else:
            return 'very_dark'
    
    def _categorize_contrast(self, contrast: float) -> str:
        if contrast > 60:
            return 'high'
        elif contrast > 30:
            return 'medium'
        else:
            return 'low'
    
    def _categorize_motion(self, motion: float) -> str:
        if motion > 0.7:
            return 'high'
        elif motion > 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _categorize_volume(self, volume_db: float) -> str:
        if np.isnan(volume_db) or volume_db < -50:
            return 'very_quiet'
        elif volume_db < -30:
            return 'quiet'
        elif volume_db < -10:
            return 'normal'
        elif volume_db < 0:
            return 'loud'
        else:
            return 'very_loud'
    
    def _classify_audio_type(self, tempo: float, has_speech: bool, spectral_centroid: float) -> str:
        if has_speech:
            return 'speech'
        elif tempo > 120:
            return 'music_fast'
        elif tempo > 80:
            return 'music_medium'
        elif tempo > 0:
            return 'music_slow'
        elif spectral_centroid > 2000:
            return 'ambient_high'
        else:
            return 'ambient_low'


if __name__ == "__main__":
    # Example usage
    extractor = MetadataExtractor(use_ai_analysis=True)
    
    shot_info = {
        'shot_id': 'test_shot_001',
        'file_path': input("Enter shot video path: "),
        'duration': 5.0,
    }
    
    if os.path.exists(shot_info['file_path']):
        metadata = extractor.extract_shot_metadata(shot_info)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))