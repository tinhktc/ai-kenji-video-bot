#!/usr/bin/env python3
"""
Shot Detection Module
Automatically detects scene changes and splits videos into shots
"""

import cv2
import numpy as np
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging
from tqdm import tqdm
import ffmpeg

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ShotDetector:
    def __init__(self, output_dir: str = "library/shots"):
        """
        Initialize ShotDetector
        
        Args:
            output_dir: Directory to save shot videos and metadata
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Shot detection parameters
        self.threshold = 0.3  # Scene change threshold (0-1)
        self.min_shot_duration = 1.0  # Minimum shot duration in seconds
        self.max_shot_duration = 30.0  # Maximum shot duration in seconds
        
        # Feature extraction parameters
        self.histogram_bins = 256
        self.use_optical_flow = True
        self.use_edge_detection = True
    
    def detect_shots(self, video_path: str, video_info: Dict = None) -> List[Dict]:
        """
        Detect shots in a video and return shot information
        
        Args:
            video_path: Path to input video file
            video_info: Optional video metadata
            
        Returns:
            List of shot dictionaries with timing and metadata
        """
        logger.info(f"Starting shot detection for: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video file: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        logger.info(f"Video properties: {total_frames} frames, {fps} FPS, {duration:.2f}s duration")
        
        shots = []
        shot_boundaries = [0]  # Start with frame 0
        
        # Initialize variables for scene detection
        prev_hist = None
        prev_gray = None
        frame_idx = 0
        
        # Progress bar
        pbar = tqdm(total=total_frames, desc="Detecting shots")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate scene change score
            change_score = self._calculate_scene_change(frame, prev_hist, prev_gray)
            
            # Check if this is a scene boundary
            if change_score > self.threshold and frame_idx > 0:
                # Check minimum duration constraint
                last_boundary = shot_boundaries[-1]
                duration_since_last = (frame_idx - last_boundary) / fps
                
                if duration_since_last >= self.min_shot_duration:
                    shot_boundaries.append(frame_idx)
            
            # Update previous frame data
            prev_hist = self._calculate_histogram(frame)
            prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            frame_idx += 1
            pbar.update(1)
        
        pbar.close()
        cap.release()
        
        # Add final boundary
        shot_boundaries.append(total_frames - 1)
        
        # Create shot metadata
        video_name = Path(video_path).stem
        for i in range(len(shot_boundaries) - 1):
            start_frame = shot_boundaries[i]
            end_frame = shot_boundaries[i + 1]
            
            start_time = start_frame / fps
            end_time = end_frame / fps
            shot_duration = end_time - start_time
            
            # Skip shots that are too short or too long
            if shot_duration < self.min_shot_duration or shot_duration > self.max_shot_duration:
                continue
            
            shot_info = {
                'shot_id': f"{video_name}_shot_{i:04d}",
                'video_source': video_path,
                'start_frame': start_frame,
                'end_frame': end_frame,
                'start_time': start_time,
                'end_time': end_time,
                'duration': shot_duration,
                'fps': fps,
                'shot_index': i,
                'created_at': datetime.now().isoformat(),
            }
            
            # Add original video metadata if available
            if video_info:
                shot_info['source_video'] = {
                    'title': video_info.get('title', ''),
                    'video_id': video_info.get('video_id', ''),
                    'uploader': video_info.get('uploader', ''),
                    'original_url': video_info.get('original_url', ''),
                }
            
            shots.append(shot_info)
        
        logger.info(f"Detected {len(shots)} shots from {len(shot_boundaries)-1} boundaries")
        return shots
    
    def extract_shots(self, video_path: str, shots: List[Dict]) -> List[Dict]:
        """
        Extract shot videos from the source video
        
        Args:
            video_path: Path to source video
            shots: List of shot information dictionaries
            
        Returns:
            Updated list of shots with file paths
        """
        logger.info(f"Extracting {len(shots)} shots from {video_path}")
        
        extracted_shots = []
        
        for shot in tqdm(shots, desc="Extracting shots"):
            try:
                # Generate output filename
                shot_filename = f"{shot['shot_id']}.mp4"
                shot_path = self.output_dir / shot_filename
                
                # Extract shot using ffmpeg
                start_time = shot['start_time']
                duration = shot['duration']
                
                (
                    ffmpeg
                    .input(video_path, ss=start_time, t=duration)
                    .output(str(shot_path), vcodec='libx264', acodec='aac')
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # Update shot info with file path
                shot['file_path'] = str(shot_path)
                shot['file_size'] = shot_path.stat().st_size
                shot['extracted_at'] = datetime.now().isoformat()
                
                # Generate thumbnail
                thumbnail_path = self._generate_thumbnail(str(shot_path), shot['shot_id'])
                shot['thumbnail_path'] = thumbnail_path
                
                extracted_shots.append(shot)
                
            except Exception as e:
                logger.error(f"Failed to extract shot {shot['shot_id']}: {str(e)}")
                continue
        
        logger.info(f"Successfully extracted {len(extracted_shots)} shots")
        return extracted_shots
    
    def _calculate_scene_change(self, frame: np.ndarray, prev_hist: Optional[np.ndarray], 
                              prev_gray: Optional[np.ndarray]) -> float:
        """
        Calculate scene change score between current and previous frame
        
        Args:
            frame: Current frame
            prev_hist: Previous frame histogram
            prev_gray: Previous frame grayscale
            
        Returns:
            Scene change score (0-1)
        """
        if prev_hist is None or prev_gray is None:
            return 0.0
        
        # Calculate histogram difference
        current_hist = self._calculate_histogram(frame)
        hist_diff = cv2.compareHist(prev_hist, current_hist, cv2.HISTCMP_CORREL)
        hist_score = 1.0 - hist_diff  # Convert correlation to difference
        
        # Calculate optical flow if enabled
        flow_score = 0.0
        if self.use_optical_flow:
            current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow_score = self._calculate_optical_flow_change(prev_gray, current_gray)
        
        # Calculate edge difference if enabled
        edge_score = 0.0
        if self.use_edge_detection:
            current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edge_score = self._calculate_edge_change(prev_gray, current_gray)
        
        # Combine scores
        weights = [0.5, 0.3, 0.2]  # hist, flow, edge
        scores = [hist_score, flow_score, edge_score]
        
        total_score = sum(w * s for w, s in zip(weights, scores))
        return min(total_score, 1.0)
    
    def _calculate_histogram(self, frame: np.ndarray) -> np.ndarray:
        """Calculate color histogram for frame"""
        # Convert to HSV for better color representation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Calculate histogram for each channel
        hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [60], [0, 256])
        
        # Concatenate histograms
        hist = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])
        
        # Normalize
        hist = cv2.normalize(hist, hist).flatten()
        return hist
    
    def _calculate_optical_flow_change(self, prev_gray: np.ndarray, current_gray: np.ndarray) -> float:
        """Calculate optical flow magnitude between frames"""
        try:
            # Calculate optical flow
            flow = cv2.calcOpticalFlowPyrLK(
                prev_gray, current_gray, 
                cv2.goodFeaturesToTrack(prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7),
                None
            )[0]
            
            if flow is not None and len(flow) > 0:
                # Calculate average flow magnitude
                flow_magnitude = np.mean(np.sqrt(flow[:, 0]**2 + flow[:, 1]**2))
                return min(flow_magnitude / 50.0, 1.0)  # Normalize
            
        except Exception:
            pass
        
        return 0.0
    
    def _calculate_edge_change(self, prev_gray: np.ndarray, current_gray: np.ndarray) -> float:
        """Calculate edge difference between frames"""
        try:
            # Calculate edges using Canny
            prev_edges = cv2.Canny(prev_gray, 50, 150)
            current_edges = cv2.Canny(current_gray, 50, 150)
            
            # Calculate difference
            edge_diff = cv2.absdiff(prev_edges, current_edges)
            edge_score = np.mean(edge_diff) / 255.0
            
            return edge_score
            
        except Exception:
            return 0.0
    
    def _generate_thumbnail(self, video_path: str, shot_id: str) -> str:
        """Generate thumbnail for shot video"""
        try:
            thumbnail_path = self.output_dir / f"{shot_id}_thumb.jpg"
            
            # Extract frame at 50% of shot duration
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            middle_frame = total_frames // 2
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
            ret, frame = cap.read()
            
            if ret:
                # Resize to standard thumbnail size
                height, width = frame.shape[:2]
                if width > 320:
                    scale = 320 / width
                    new_width = 320
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                cv2.imwrite(str(thumbnail_path), frame)
                cap.release()
                return str(thumbnail_path)
            
            cap.release()
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {shot_id}: {str(e)}")
        
        return ""
    
    def save_shots_metadata(self, shots: List[Dict], video_info: Dict = None) -> str:
        """
        Save shots metadata to JSON file
        
        Args:
            shots: List of shot dictionaries
            video_info: Optional source video information
            
        Returns:
            Path to saved metadata file
        """
        metadata = {
            'video_info': video_info or {},
            'detection_settings': {
                'threshold': self.threshold,
                'min_shot_duration': self.min_shot_duration,
                'max_shot_duration': self.max_shot_duration,
                'use_optical_flow': self.use_optical_flow,
                'use_edge_detection': self.use_edge_detection,
            },
            'shots': shots,
            'total_shots': len(shots),
            'created_at': datetime.now().isoformat(),
        }
        
        # Generate metadata filename
        video_name = video_info.get('video_id', 'unknown') if video_info else 'unknown'
        metadata_path = self.output_dir / f"{video_name}_shots_metadata.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved shots metadata to: {metadata_path}")
        return str(metadata_path)
    
    def process_video(self, video_path: str, video_info: Dict = None) -> Dict:
        """
        Complete shot detection and extraction process
        
        Args:
            video_path: Path to input video
            video_info: Optional video metadata
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"Processing video: {video_path}")
        
        try:
            # Detect shots
            shots = self.detect_shots(video_path, video_info)
            
            if not shots:
                logger.warning("No shots detected in video")
                return {'success': False, 'error': 'No shots detected'}
            
            # Extract shot videos
            extracted_shots = self.extract_shots(video_path, shots)
            
            # Save metadata
            metadata_path = self.save_shots_metadata(extracted_shots, video_info)
            
            result = {
                'success': True,
                'total_shots': len(extracted_shots),
                'shots': extracted_shots,
                'metadata_path': metadata_path,
                'output_directory': str(self.output_dir),
            }
            
            logger.info(f"Successfully processed video: {len(extracted_shots)} shots extracted")
            return result
            
        except Exception as e:
            logger.error(f"Error processing video {video_path}: {str(e)}")
            return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    # Example usage
    detector = ShotDetector("library/shots")
    
    video_path = input("Enter video path: ")
    if os.path.exists(video_path):
        result = detector.process_video(video_path)
        
        if result['success']:
            print(f"Successfully extracted {result['total_shots']} shots")
            print(f"Output directory: {result['output_directory']}")
        else:
            print(f"Processing failed: {result['error']}")
    else:
        print("Video file not found")