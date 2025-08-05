#!/usr/bin/env python3
"""
Video Downloader Module
Handles downloading videos from various sources including YouTube
"""

import os
import yt_dlp
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_dir: str = "downloads"):
        """
        Initialize VideoDownloader
        
        Args:
            download_dir: Directory to save downloaded videos
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # yt-dlp options for best quality
        self.ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'writeinfojson': True,  # Save metadata
            'writethumbnail': True,  # Save thumbnail
            'writesubtitles': True,  # Save subtitles if available
            'writeautomaticsub': True,  # Save auto-generated subtitles
            'subtitleslangs': ['vi', 'en'],  # Vietnamese and English subtitles
        }
    
    def download_video(self, url: str) -> Dict:
        """
        Download video from URL and return information
        
        Args:
            url: Video URL to download
            
        Returns:
            Dictionary containing download information
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                
                # Generate unique filename based on video ID
                video_id = info.get('id', hashlib.md5(url.encode()).hexdigest())
                title = self.sanitize_filename(info.get('title', 'Unknown'))
                
                # Update output template with unique filename
                unique_opts = self.ydl_opts.copy()
                unique_opts['outtmpl'] = str(self.download_dir / f"{video_id}_{title}.%(ext)s")
                
                # Download the video
                with yt_dlp.YoutubeDL(unique_opts) as ydl_download:
                    ydl_download.download([url])
                
                # Find the downloaded video file
                video_file = None
                for ext in ['mp4', 'webm', 'mkv', 'avi']:
                    potential_file = self.download_dir / f"{video_id}_{title}.{ext}"
                    if potential_file.exists():
                        video_file = potential_file
                        break
                
                if not video_file:
                    raise Exception("Downloaded video file not found")
                
                # Prepare return information
                download_info = {
                    'video_id': video_id,
                    'title': title,
                    'original_url': url,
                    'file_path': str(video_file),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', ''),
                    'tags': info.get('tags', []),
                    'thumbnail_url': info.get('thumbnail', ''),
                    'download_timestamp': datetime.now().isoformat(),
                    'file_size': video_file.stat().st_size if video_file.exists() else 0,
                }
                
                # Save metadata to JSON file
                metadata_file = self.download_dir / f"{video_id}_{title}_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(download_info, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Successfully downloaded: {title}")
                return download_info
                
        except Exception as e:
            logger.error(f"Error downloading video from {url}: {str(e)}")
            raise
    
    def download_playlist(self, playlist_url: str, max_videos: Optional[int] = None) -> List[Dict]:
        """
        Download videos from a playlist
        
        Args:
            playlist_url: Playlist URL
            max_videos: Maximum number of videos to download
            
        Returns:
            List of download information dictionaries
        """
        try:
            playlist_opts = self.ydl_opts.copy()
            if max_videos:
                playlist_opts['playlistend'] = max_videos
            
            with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                downloaded_videos = []
                for entry in playlist_info['entries']:
                    if entry:
                        try:
                            video_info = self.download_video(entry['webpage_url'])
                            downloaded_videos.append(video_info)
                        except Exception as e:
                            logger.error(f"Failed to download video {entry.get('title', 'Unknown')}: {str(e)}")
                            continue
                
                return downloaded_videos
                
        except Exception as e:
            logger.error(f"Error downloading playlist from {playlist_url}: {str(e)}")
            raise
    
    def get_video_info(self, url: str) -> Dict:
        """
        Get video information without downloading
        
        Args:
            url: Video URL
            
        Returns:
            Dictionary containing video information
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'video_id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', ''),
                    'tags': info.get('tags', []),
                    'thumbnail_url': info.get('thumbnail', ''),
                    'formats': [f"{f['format_id']}: {f.get('format_note', 'N/A')}" for f in info.get('formats', [])],
                }
                
        except Exception as e:
            logger.error(f"Error getting video info from {url}: {str(e)}")
            raise
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe file system usage
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:97] + "..."
        
        return filename.strip()
    
    def list_downloaded_videos(self) -> List[Dict]:
        """
        List all downloaded videos with their metadata
        
        Returns:
            List of video information dictionaries
        """
        videos = []
        
        for metadata_file in self.download_dir.glob("*_metadata.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    video_info = json.load(f)
                    
                # Check if video file still exists
                if os.path.exists(video_info['file_path']):
                    videos.append(video_info)
                    
            except Exception as e:
                logger.error(f"Error reading metadata file {metadata_file}: {str(e)}")
                continue
        
        return sorted(videos, key=lambda x: x.get('download_timestamp', ''), reverse=True)


if __name__ == "__main__":
    # Example usage
    downloader = VideoDownloader("downloads/raw_videos")
    
    # Download a single video
    try:
        video_url = input("Enter video URL: ")
        info = downloader.download_video(video_url)
        print(f"Downloaded: {info['title']}")
        print(f"File: {info['file_path']}")
        print(f"Duration: {info['duration']} seconds")
    except Exception as e:
        print(f"Download failed: {e}")