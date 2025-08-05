#!/usr/bin/env python3
"""
Library Manager Module
Manages organized file structure and provides high-level interface for video library operations
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from collections import defaultdict
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LibraryManager:
    def __init__(self, library_root: str = "library"):
        """
        Initialize LibraryManager
        
        Args:
            library_root: Root directory for the video library
        """
        self.library_root = Path(library_root)
        self._create_directory_structure()
        
        # Directory structure
        self.dirs = {
            'raw_videos': self.library_root / 'raw_videos',
            'shots': self.library_root / 'shots',
            'thumbnails': self.library_root / 'thumbnails',
            'metadata': self.library_root / 'metadata',
            'temp': self.library_root / 'temp',
            'exports': self.library_root / 'exports',
            'backups': self.library_root / 'backups',
        }
        
        # Subdirectories for organization
        self.shot_dirs = {
            'by_date': self.dirs['shots'] / 'by_date',
            'by_source': self.dirs['shots'] / 'by_source',
            'by_quality': self.dirs['shots'] / 'by_quality',
            'by_duration': self.dirs['shots'] / 'by_duration',
            'by_type': self.dirs['shots'] / 'by_type',
        }
    
    def _create_directory_structure(self):
        """Create the organized directory structure"""
        directories = [
            'raw_videos',
            'shots',
            'shots/by_date',
            'shots/by_source', 
            'shots/by_quality',
            'shots/by_duration',
            'shots/by_type',
            'thumbnails',
            'metadata',
            'temp',
            'exports',
            'backups',
        ]
        
        for dir_path in directories:
            full_path = self.library_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created library directory structure at: {self.library_root}")
    
    def organize_raw_video(self, video_info: Dict) -> str:
        """
        Organize raw video file into structured directory
        
        Args:
            video_info: Video information dictionary
            
        Returns:
            New organized file path
        """
        try:
            original_path = Path(video_info['file_path'])
            
            if not original_path.exists():
                raise FileNotFoundError(f"Original video file not found: {original_path}")
            
            # Create organized filename
            video_id = video_info.get('video_id', 'unknown')
            title = self._sanitize_filename(video_info.get('title', 'untitled'))
            uploader = self._sanitize_filename(video_info.get('uploader', 'unknown'))
            
            # Organize by uploader and date
            upload_date = video_info.get('upload_date', '')
            if upload_date and len(upload_date) >= 8:
                year = upload_date[:4]
                month = upload_date[4:6]
                date_dir = self.dirs['raw_videos'] / uploader / year / month
            else:
                date_dir = self.dirs['raw_videos'] / uploader / 'unknown_date'
            
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate new filename
            file_extension = original_path.suffix
            new_filename = f"{video_id}_{title}{file_extension}"
            new_path = date_dir / new_filename
            
            # Move file if it's not already in the right place
            if original_path != new_path:
                if new_path.exists():
                    # If file already exists, add timestamp to make it unique
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_filename = f"{video_id}_{title}_{timestamp}{file_extension}"
                    new_path = date_dir / new_filename
                
                shutil.move(str(original_path), str(new_path))
                logger.info(f"Moved video to: {new_path}")
            
            return str(new_path)
            
        except Exception as e:
            logger.error(f"Error organizing raw video: {e}")
            return video_info['file_path']  # Return original path if organization fails
    
    def organize_shot(self, shot_metadata: Dict) -> Dict:
        """
        Organize shot file into structured directories with multiple organization methods
        
        Args:
            shot_metadata: Shot metadata dictionary
            
        Returns:
            Updated shot metadata with organized paths
        """
        try:
            original_path = Path(shot_metadata['file_path'])
            
            if not original_path.exists():
                raise FileNotFoundError(f"Shot file not found: {original_path}")
            
            shot_id = shot_metadata['shot_id']
            
            # Determine organization categories
            categories = self._categorize_shot(shot_metadata)
            
            # Primary storage location (by date and source)
            primary_dir = self._get_primary_shot_directory(shot_metadata)
            primary_dir.mkdir(parents=True, exist_ok=True)
            
            primary_path = primary_dir / f"{shot_id}.mp4"
            
            # Move to primary location
            if original_path != primary_path:
                shutil.move(str(original_path), str(primary_path))
                shot_metadata['file_path'] = str(primary_path)
            
            # Create symbolic links for other organization methods
            self._create_organization_links(shot_metadata, categories)
            
            # Organize thumbnail if it exists
            if shot_metadata.get('thumbnail_path'):
                new_thumb_path = self._organize_thumbnail(shot_metadata)
                shot_metadata['thumbnail_path'] = new_thumb_path
            
            logger.info(f"Organized shot: {shot_id}")
            return shot_metadata
            
        except Exception as e:
            logger.error(f"Error organizing shot {shot_metadata.get('shot_id', 'unknown')}: {e}")
            return shot_metadata
    
    def _categorize_shot(self, shot_metadata: Dict) -> Dict:
        """Categorize shot for organization purposes"""
        categories = {}
        
        # Duration category
        duration = shot_metadata.get('duration', 0)
        if duration < 2:
            categories['duration'] = 'very_short'
        elif duration < 5:
            categories['duration'] = 'short'
        elif duration < 15:
            categories['duration'] = 'medium'
        else:
            categories['duration'] = 'long'
        
        # Quality category
        quality = shot_metadata.get('quality_score', 0)
        if quality >= 0.8:
            categories['quality'] = 'high'
        elif quality >= 0.6:
            categories['quality'] = 'medium'
        else:
            categories['quality'] = 'low'
        
        # Content type category
        keywords = shot_metadata.get('keywords', [])
        audio_info = shot_metadata.get('audio', {})
        
        if any('speech' in kw for kw in keywords) or audio_info.get('has_speech'):
            categories['type'] = 'speech'
        elif any('music' in kw for kw in keywords):
            categories['type'] = 'music'
        elif audio_info.get('has_audio'):
            categories['type'] = 'audio'
        else:
            categories['type'] = 'silent'
        
        # Motion category
        visual_info = shot_metadata.get('visual', {})
        motion_cat = visual_info.get('motion', {}).get('category', 'unknown')
        categories['motion'] = motion_cat
        
        # Scene category
        content_info = shot_metadata.get('content', {})
        scene_type = content_info.get('scene_type', 'unknown')
        categories['scene'] = scene_type
        
        return categories
    
    def _get_primary_shot_directory(self, shot_metadata: Dict) -> Path:
        """Get primary directory for shot storage"""
        # Organize by creation date
        created_at = shot_metadata.get('created_at', datetime.now().isoformat())
        try:
            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            year = date_obj.strftime('%Y')
            month = date_obj.strftime('%m')
            day = date_obj.strftime('%d')
        except:
            year = 'unknown'
            month = 'unknown'
            day = 'unknown'
        
        # Get source information
        source_video = shot_metadata.get('source_video', {})
        uploader = self._sanitize_filename(source_video.get('uploader', 'unknown'))
        
        return self.shot_dirs['by_date'] / year / month / day / uploader
    
    def _create_organization_links(self, shot_metadata: Dict, categories: Dict):
        """Create symbolic links for different organization methods"""
        shot_id = shot_metadata['shot_id']
        primary_path = Path(shot_metadata['file_path'])
        
        # By quality
        quality_dir = self.shot_dirs['by_quality'] / categories.get('quality', 'unknown')
        quality_dir.mkdir(parents=True, exist_ok=True)
        quality_link = quality_dir / f"{shot_id}.mp4"
        self._create_safe_symlink(primary_path, quality_link)
        
        # By duration
        duration_dir = self.shot_dirs['by_duration'] / categories.get('duration', 'unknown')
        duration_dir.mkdir(parents=True, exist_ok=True)
        duration_link = duration_dir / f"{shot_id}.mp4"
        self._create_safe_symlink(primary_path, duration_link)
        
        # By type
        type_dir = self.shot_dirs['by_type'] / categories.get('type', 'unknown')
        type_dir.mkdir(parents=True, exist_ok=True)
        type_link = type_dir / f"{shot_id}.mp4"
        self._create_safe_symlink(primary_path, type_link)
        
        # By source
        source_video = shot_metadata.get('source_video', {})
        if source_video:
            uploader = self._sanitize_filename(source_video.get('uploader', 'unknown'))
            source_dir = self.shot_dirs['by_source'] / uploader
            source_dir.mkdir(parents=True, exist_ok=True)
            source_link = source_dir / f"{shot_id}.mp4"
            self._create_safe_symlink(primary_path, source_link)
    
    def _create_safe_symlink(self, target: Path, link: Path):
        """Create symbolic link safely (remove existing if necessary)"""
        try:
            if link.exists() or link.is_symlink():
                link.unlink()
            
            # Create relative symlink for portability
            relative_target = os.path.relpath(target, link.parent)
            link.symlink_to(relative_target)
            
        except Exception as e:
            logger.warning(f"Failed to create symlink {link} -> {target}: {e}")
    
    def _organize_thumbnail(self, shot_metadata: Dict) -> str:
        """Organize thumbnail file"""
        try:
            original_thumb_path = Path(shot_metadata['thumbnail_path'])
            
            if not original_thumb_path.exists():
                return shot_metadata['thumbnail_path']
            
            shot_id = shot_metadata['shot_id']
            
            # Organize thumbnails by date
            created_at = shot_metadata.get('created_at', datetime.now().isoformat())
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                year = date_obj.strftime('%Y')
                month = date_obj.strftime('%m')
            except:
                year = 'unknown'
                month = 'unknown'
            
            thumb_dir = self.dirs['thumbnails'] / year / month
            thumb_dir.mkdir(parents=True, exist_ok=True)
            
            new_thumb_path = thumb_dir / f"{shot_id}_thumb.jpg"
            
            if original_thumb_path != new_thumb_path:
                shutil.move(str(original_thumb_path), str(new_thumb_path))
            
            return str(new_thumb_path)
            
        except Exception as e:
            logger.error(f"Error organizing thumbnail: {e}")
            return shot_metadata.get('thumbnail_path', '')
    
    def save_metadata(self, metadata: Dict, metadata_type: str = 'shot') -> str:
        """
        Save metadata to organized location
        
        Args:
            metadata: Metadata dictionary
            metadata_type: Type of metadata ('shot', 'video', 'processing')
            
        Returns:
            Path to saved metadata file
        """
        try:
            # Organize metadata by type and date
            timestamp = datetime.now()
            year = timestamp.strftime('%Y')
            month = timestamp.strftime('%m')
            
            metadata_dir = self.dirs['metadata'] / metadata_type / year / month
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            if metadata_type == 'shot':
                filename = f"{metadata.get('shot_id', 'unknown')}_metadata.json"
            elif metadata_type == 'video':
                filename = f"{metadata.get('video_id', 'unknown')}_video_metadata.json"
            else:
                filename = f"{metadata_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            
            metadata_path = metadata_dir / filename
            
            # Add library management info
            metadata['library_info'] = {
                'saved_at': timestamp.isoformat(),
                'metadata_path': str(metadata_path),
                'metadata_type': metadata_type,
            }
            
            # Save metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {metadata_type} metadata to: {metadata_path}")
            return str(metadata_path)
            
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            return ''
    
    def create_export_package(self, shot_ids: List[str], export_name: str = None) -> str:
        """
        Create an export package with selected shots and their metadata
        
        Args:
            shot_ids: List of shot IDs to export
            export_name: Name for the export package
            
        Returns:
            Path to created export package
        """
        try:
            if not export_name:
                export_name = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            export_dir = self.dirs['exports'] / export_name
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            shots_dir = export_dir / 'shots'
            thumbs_dir = export_dir / 'thumbnails'
            metadata_dir = export_dir / 'metadata'
            
            for dir_path in [shots_dir, thumbs_dir, metadata_dir]:
                dir_path.mkdir(exist_ok=True)
            
            exported_shots = []
            
            for shot_id in shot_ids:
                try:
                    # Find shot files
                    shot_files = list(self.library_root.rglob(f"{shot_id}.mp4"))
                    thumb_files = list(self.library_root.rglob(f"{shot_id}_thumb.jpg"))
                    metadata_files = list(self.library_root.rglob(f"{shot_id}_metadata.json"))
                    
                    if shot_files:
                        # Copy shot video
                        shot_src = shot_files[0]
                        shot_dst = shots_dir / f"{shot_id}.mp4"
                        shutil.copy2(shot_src, shot_dst)
                        
                        # Copy thumbnail if exists
                        if thumb_files:
                            thumb_src = thumb_files[0]
                            thumb_dst = thumbs_dir / f"{shot_id}_thumb.jpg"
                            shutil.copy2(thumb_src, thumb_dst)
                        
                        # Copy metadata if exists
                        if metadata_files:
                            metadata_src = metadata_files[0]
                            metadata_dst = metadata_dir / f"{shot_id}_metadata.json"
                            shutil.copy2(metadata_src, metadata_dst)
                        
                        exported_shots.append(shot_id)
                        logger.info(f"Exported shot: {shot_id}")
                    
                except Exception as e:
                    logger.error(f"Error exporting shot {shot_id}: {e}")
                    continue
            
            # Create export manifest
            manifest = {
                'export_name': export_name,
                'created_at': datetime.now().isoformat(),
                'total_shots': len(exported_shots),
                'exported_shots': exported_shots,
                'structure': {
                    'shots': 'shots/',
                    'thumbnails': 'thumbnails/',
                    'metadata': 'metadata/',
                }
            }
            
            manifest_path = export_dir / 'manifest.json'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created export package: {export_dir} ({len(exported_shots)} shots)")
            return str(export_dir)
            
        except Exception as e:
            logger.error(f"Error creating export package: {e}")
            return ''
    
    def cleanup_temp_files(self, older_than_hours: int = 24):
        """Clean up temporary files older than specified hours"""
        try:
            cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
            removed_count = 0
            
            for temp_file in self.dirs['temp'].rglob('*'):
                if temp_file.is_file():
                    if temp_file.stat().st_mtime < cutoff_time:
                        temp_file.unlink()
                        removed_count += 1
            
            # Remove empty directories
            for temp_dir in self.dirs['temp'].rglob('*'):
                if temp_dir.is_dir() and not any(temp_dir.iterdir()):
                    temp_dir.rmdir()
            
            logger.info(f"Cleaned up {removed_count} temporary files")
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
    
    def create_backup(self, backup_name: str = None) -> str:
        """
        Create backup of library metadata
        
        Args:
            backup_name: Name for backup
            
        Returns:
            Path to backup file
        """
        try:
            if not backup_name:
                backup_name = f"library_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_dir = self.dirs['backups']
            backup_path = backup_dir / f"{backup_name}.tar.gz"
            
            # Create tar.gz backup of metadata directory
            import tarfile
            
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(self.dirs['metadata'], arcname='metadata')
            
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return ''
    
    def get_library_statistics(self) -> Dict:
        """Get comprehensive library statistics"""
        try:
            stats = {
                'directories': {},
                'file_counts': {},
                'storage_usage': {},
                'organization': {},
            }
            
            # Directory statistics
            for name, path in self.dirs.items():
                if path.exists():
                    stats['directories'][name] = {
                        'path': str(path),
                        'exists': True,
                        'file_count': len(list(path.rglob('*'))),
                    }
                else:
                    stats['directories'][name] = {
                        'path': str(path),
                        'exists': False,
                        'file_count': 0,
                    }
            
            # File type counts
            for ext in ['.mp4', '.jpg', '.json']:
                count = len(list(self.library_root.rglob(f'*{ext}')))
                stats['file_counts'][ext] = count
            
            # Storage usage
            total_size = 0
            for file_path in self.library_root.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            stats['storage_usage'] = {
                'total_bytes': total_size,
                'total_mb': round(total_size / (1024 * 1024), 2),
                'total_gb': round(total_size / (1024 * 1024 * 1024), 2),
            }
            
            # Organization statistics
            for org_name, org_path in self.shot_dirs.items():
                if org_path.exists():
                    categories = [d.name for d in org_path.iterdir() if d.is_dir()]
                    stats['organization'][org_name] = {
                        'categories': categories,
                        'category_count': len(categories),
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting library statistics: {e}")
            return {}
    
    def find_duplicates(self) -> Dict[str, List[str]]:
        """Find potential duplicate shots based on content hash"""
        try:
            hash_groups = defaultdict(list)
            
            # Find all metadata files
            for metadata_file in self.dirs['metadata'].rglob('*_metadata.json'):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    content_hash = metadata.get('content_hash')
                    shot_id = metadata.get('shot_id')
                    
                    if content_hash and shot_id:
                        hash_groups[content_hash].append(shot_id)
                
                except Exception as e:
                    logger.warning(f"Error reading metadata file {metadata_file}: {e}")
                    continue
            
            # Filter to only groups with duplicates
            duplicates = {h: shots for h, shots in hash_groups.items() if len(shots) > 1}
            
            logger.info(f"Found {len(duplicates)} groups of potential duplicates")
            return duplicates
            
        except Exception as e:
            logger.error(f"Error finding duplicates: {e}")
            return {}
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file system usage"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove extra spaces and limit length
        filename = '_'.join(filename.split())
        if len(filename) > 50:
            filename = filename[:47] + "..."
        
        return filename.strip()
    
    def get_temp_path(self, filename: str) -> Path:
        """Get path in temporary directory"""
        return self.dirs['temp'] / filename
    
    def get_shot_path(self, shot_id: str) -> Optional[Path]:
        """Find the primary path for a shot"""
        # Look for the shot file in the library
        shot_files = list(self.library_root.rglob(f"{shot_id}.mp4"))
        
        # Return the first non-symlink file (primary location)
        for shot_file in shot_files:
            if not shot_file.is_symlink():
                return shot_file
        
        # If only symlinks found, return the first one
        return shot_files[0] if shot_files else None


if __name__ == "__main__":
    # Example usage
    library = LibraryManager("library")
    
    # Get library statistics
    stats = library.get_library_statistics()
    print("Library Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Find duplicates
    duplicates = library.find_duplicates()
    if duplicates:
        print(f"\nFound {len(duplicates)} groups of potential duplicates")
        for content_hash, shot_ids in list(duplicates.items())[:5]:  # Show first 5
            print(f"Hash {content_hash[:8]}...: {shot_ids}")
    
    # Cleanup temp files
    library.cleanup_temp_files()
    
    print(f"\nLibrary root: {library.library_root}")
    print("Directory structure created successfully")