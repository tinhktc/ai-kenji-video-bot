#!/usr/bin/env python3
"""
Video Processor - Main Pipeline
Orchestrates the complete video processing workflow:
1. Download videos from URLs
2. Detect and extract shots
3. Extract comprehensive metadata
4. Store in organized library structure
5. Save to database
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging
from tqdm import tqdm

# Add core modules to path
sys.path.append(str(Path(__file__).parent / 'core'))

from core.video_downloader import VideoDownloader
from core.shot_detector import ShotDetector
from core.metadata_extractor import MetadataExtractor
from core.database_manager import DatabaseManager
from core.library_manager import LibraryManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize VideoProcessor with all components
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or self._load_default_config()
        
        # Initialize components
        logger.info("Initializing video processing components...")
        
        try:
            self.downloader = VideoDownloader(
                download_dir=self.config.get('download_dir', 'downloads/raw_videos')
            )
            
            self.shot_detector = ShotDetector(
                output_dir=self.config.get('shots_temp_dir', 'temp/shots')
            )
            
            self.metadata_extractor = MetadataExtractor(
                use_ai_analysis=self.config.get('use_ai_analysis', True)
            )
            
            self.library_manager = LibraryManager(
                library_root=self.config.get('library_root', 'library')
            )
            
            self.database_manager = DatabaseManager(
                config=self.config.get('database', None)
            )
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _load_default_config(self) -> Dict:
        """Load default configuration"""
        return {
            'download_dir': 'downloads/raw_videos',
            'shots_temp_dir': 'temp/shots',
            'library_root': 'library',
            'use_ai_analysis': True,
            'shot_detection': {
                'threshold': 0.3,
                'min_shot_duration': 1.0,
                'max_shot_duration': 30.0,
            },
            'processing': {
                'batch_size': 5,
                'max_concurrent': 2,
            }
        }
    
    def process_video_url(self, url: str, options: Optional[Dict] = None) -> Dict:
        """
        Process a single video URL through the complete pipeline
        
        Args:
            url: Video URL to process
            options: Processing options
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"Starting video processing pipeline for: {url}")
        
        try:
            # Step 1: Download video
            logger.info("Step 1: Downloading video...")
            video_info = self.downloader.download_video(url)
            
            # Organize raw video
            organized_path = self.library_manager.organize_raw_video(video_info)
            video_info['file_path'] = organized_path
            
            # Save to database
            video_db_id = self.database_manager.insert_source_video(video_info)
            
            # Step 2: Process the video
            result = self.process_video_file(video_info['file_path'], video_info, video_db_id)
            
            return {
                'success': True,
                'video_info': video_info,
                'processing_result': result,
                'video_db_id': video_db_id,
            }
            
        except Exception as e:
            logger.error(f"Error processing video URL {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
            }
    
    def process_video_file(self, video_path: str, video_info: Optional[Dict] = None, 
                          video_db_id: Optional[int] = None) -> Dict:
        """
        Process a video file through shot detection and metadata extraction
        
        Args:
            video_path: Path to video file
            video_info: Optional video information
            video_db_id: Optional database ID for source video
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"Processing video file: {video_path}")
        
        # Update processing status
        self.database_manager.update_processing_status(
            video_path, 'processing'
        )
        
        try:
            # Step 1: Shot detection and extraction
            logger.info("Step 1: Detecting and extracting shots...")
            shot_result = self.shot_detector.process_video(video_path, video_info)
            
            if not shot_result['success']:
                raise Exception(f"Shot detection failed: {shot_result.get('error', 'Unknown error')}")
            
            shots = shot_result['shots']
            logger.info(f"Extracted {len(shots)} shots")
            
            # Update processing status
            self.database_manager.update_processing_status(
                video_path, 'processing', 
                total_shots=len(shots), 
                processed_shots=0
            )
            
            # Step 2: Process each shot
            logger.info("Step 2: Processing shots with metadata extraction...")
            processed_shots = []
            
            for i, shot in enumerate(tqdm(shots, desc="Processing shots")):
                try:
                    # Extract comprehensive metadata
                    shot_metadata = self.metadata_extractor.extract_shot_metadata(shot)
                    
                    # Organize shot in library
                    organized_shot = self.library_manager.organize_shot(shot_metadata)
                    
                    # Save metadata to library
                    metadata_path = self.library_manager.save_metadata(
                        organized_shot, 'shot'
                    )
                    organized_shot['metadata_path'] = metadata_path
                    
                    # Save to database
                    shot_db_id = self.database_manager.insert_shot_with_metadata(
                        organized_shot, video_db_id
                    )
                    organized_shot['db_id'] = shot_db_id
                    
                    processed_shots.append(organized_shot)
                    
                    # Update progress
                    self.database_manager.update_processing_status(
                        video_path, 'processing',
                        processed_shots=i + 1
                    )
                    
                    logger.debug(f"Processed shot {i+1}/{len(shots)}: {shot['shot_id']}")
                    
                except Exception as e:
                    logger.error(f"Error processing shot {shot.get('shot_id', 'unknown')}: {e}")
                    continue
            
            # Step 3: Final processing
            logger.info("Step 3: Finalizing processing...")
            
            # Clean up temporary files
            self.library_manager.cleanup_temp_files()
            
            # Update final processing status
            self.database_manager.update_processing_status(
                video_path, 'completed',
                processed_shots=len(processed_shots)
            )
            
            result = {
                'success': True,
                'total_shots_detected': len(shots),
                'shots_processed': len(processed_shots),
                'processed_shots': processed_shots,
                'metadata_path': shot_result.get('metadata_path', ''),
            }
            
            logger.info(f"Successfully processed video: {len(processed_shots)} shots saved")
            return result
            
        except Exception as e:
            logger.error(f"Error processing video file {video_path}: {e}")
            
            # Update error status
            self.database_manager.update_processing_status(
                video_path, 'failed',
                error_message=str(e)
            )
            
            return {
                'success': False,
                'error': str(e),
                'video_path': video_path,
            }
    
    def process_video_list(self, urls: List[str], options: Optional[Dict] = None) -> List[Dict]:
        """
        Process multiple video URLs
        
        Args:
            urls: List of video URLs
            options: Processing options
            
        Returns:
            List of processing results
        """
        logger.info(f"Processing {len(urls)} videos...")
        
        results = []
        
        for i, url in enumerate(urls):
            logger.info(f"Processing video {i+1}/{len(urls)}: {url}")
            
            try:
                result = self.process_video_url(url, options)
                results.append(result)
                
                # Log progress
                if result['success']:
                    shots_count = result['processing_result']['shots_processed']
                    logger.info(f"✓ Video {i+1} completed: {shots_count} shots processed")
                else:
                    logger.error(f"✗ Video {i+1} failed: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"Unexpected error processing video {i+1}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'url': url,
                })
        
        # Summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        total_shots = sum(r['processing_result']['shots_processed'] 
                         for r in results if r['success'])
        
        logger.info(f"Batch processing completed: {successful} successful, {failed} failed, {total_shots} total shots")
        
        return results
    
    def search_library(self, filters: Dict = None, limit: int = 50) -> List[Dict]:
        """
        Search the video library
        
        Args:
            filters: Search filters
            limit: Maximum results to return
            
        Returns:
            List of matching shots
        """
        return self.database_manager.search_shots(filters, limit)
    
    def get_library_stats(self) -> Dict:
        """Get comprehensive library statistics"""
        db_stats = self.database_manager.get_statistics()
        file_stats = self.library_manager.get_library_statistics()
        
        return {
            'database': db_stats,
            'files': file_stats,
            'generated_at': datetime.now().isoformat(),
        }
    
    def export_shots(self, shot_ids: List[str], export_name: str = None) -> str:
        """
        Export selected shots to a package
        
        Args:
            shot_ids: List of shot IDs to export
            export_name: Name for export package
            
        Returns:
            Path to export package
        """
        return self.library_manager.create_export_package(shot_ids, export_name)
    
    def find_duplicates(self) -> Dict:
        """Find potential duplicate shots"""
        return self.library_manager.find_duplicates()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.database_manager.close()
            self.library_manager.cleanup_temp_files()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Video Processing Pipeline')
    
    parser.add_argument('--url', type=str, help='Single video URL to process')
    parser.add_argument('--urls-file', type=str, help='File containing video URLs (one per line)')
    parser.add_argument('--video-file', type=str, help='Local video file to process')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--search', action='store_true', help='Search library')
    parser.add_argument('--stats', action='store_true', help='Show library statistics')
    parser.add_argument('--export', type=str, help='Export shots (comma-separated shot IDs)')
    parser.add_argument('--find-duplicates', action='store_true', help='Find duplicate shots')
    parser.add_argument('--output', type=str, help='Output file for results')
    
    # Search filters
    parser.add_argument('--min-duration', type=float, help='Minimum shot duration')
    parser.add_argument('--max-duration', type=float, help='Maximum shot duration')
    parser.add_argument('--min-quality', type=float, help='Minimum quality score')
    parser.add_argument('--has-audio', action='store_true', help='Filter shots with audio')
    parser.add_argument('--has-speech', action='store_true', help='Filter shots with speech')
    parser.add_argument('--keywords', type=str, help='Keywords to search (comma-separated)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = None
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Initialize processor
    try:
        processor = VideoProcessor(config)
    except Exception as e:
        logger.error(f"Failed to initialize processor: {e}")
        return 1
    
    try:
        # Process single URL
        if args.url:
            result = processor.process_video_url(args.url)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result['success'] else 1
        
        # Process URLs from file
        elif args.urls_file:
            if not os.path.exists(args.urls_file):
                logger.error(f"URLs file not found: {args.urls_file}")
                return 1
            
            with open(args.urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            results = processor.process_video_list(urls)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"Results saved to: {args.output}")
            else:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            
            return 0
        
        # Process local video file
        elif args.video_file:
            if not os.path.exists(args.video_file):
                logger.error(f"Video file not found: {args.video_file}")
                return 1
            
            result = processor.process_video_file(args.video_file)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result['success'] else 1
        
        # Search library
        elif args.search:
            filters = {}
            
            if args.min_duration:
                filters['min_duration'] = args.min_duration
            if args.max_duration:
                filters['max_duration'] = args.max_duration
            if args.min_quality:
                filters['min_quality'] = args.min_quality
            if args.has_audio:
                filters['has_audio'] = True
            if args.has_speech:
                filters['has_speech'] = True
            if args.keywords:
                filters['keywords'] = [kw.strip() for kw in args.keywords.split(',')]
            
            results = processor.search_library(filters)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"Search results saved to: {args.output}")
            else:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            
            return 0
        
        # Show statistics
        elif args.stats:
            stats = processor.get_library_stats()
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
            else:
                print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
            
            return 0
        
        # Export shots
        elif args.export:
            shot_ids = [sid.strip() for sid in args.export.split(',')]
            export_path = processor.export_shots(shot_ids)
            
            if export_path:
                print(f"Export package created: {export_path}")
                return 0
            else:
                logger.error("Export failed")
                return 1
        
        # Find duplicates
        elif args.find_duplicates:
            duplicates = processor.find_duplicates()
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(duplicates, f, indent=2, ensure_ascii=False)
            else:
                print(json.dumps(duplicates, indent=2, ensure_ascii=False))
            
            return 0
        
        else:
            parser.print_help()
            return 0
    
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    finally:
        processor.cleanup()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)