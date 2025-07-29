#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "playwright",
#   "yt-dlp",
# ]
# ///
"""
Whop Course Downloader - uvx script
Downloads courses from Whop using Playwright iframe navigation

Usage:
    uvx whop_downloader.py download <course_url> [target_directory]
    uvx whop_downloader.py test <course_url>
    
Commands:
    download - Extract and download all videos from the course
    test     - Extract video URLs only (no downloading)
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright


class WhopDownloader:
    def __init__(self, course_url, target_dir=None):
        self.course_url = course_url
        self.target_dir = Path(target_dir) if target_dir else Path.cwd()
        self.setup_logging()
        self.setup_directories()
        
    def setup_logging(self):
        """Setup logging configuration"""
        self.log_dir = self.target_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / "whop_downloader.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_directories(self):
        """Create necessary directories"""
        self.base_dir = self.target_dir
        self.downloads_dir = self.base_dir / "downloads"
        self.videos_dir = self.downloads_dir / "videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        
        # Browser data directory in current working directory
        self.browser_data_dir = Path.cwd() / ".whop_browser_data"
        self.browser_data_dir.mkdir(exist_ok=True)

    async def extract_video_urls(self, force_reextract=False):
        """Extract video URLs using iframe navigation approach"""
        urls_file = self.downloads_dir / "video_urls.json"
        
        # Check if we already have extracted URLs
        if urls_file.exists() and not force_reextract:
            self.logger.info("Found existing video URLs file, loading...")
            try:
                with open(urls_file, 'r') as f:
                    video_data = json.load(f)
                if video_data:
                    self.logger.info(f"Loaded {len(video_data)} videos from cache")
                    return video_data
            except Exception as e:
                self.logger.warning(f"Could not load cached URLs: {e}")
                self.logger.info("Will re-extract video URLs...")
        
        self.logger.info("Starting URL extraction with iframe navigation...")
        
        # Check if playwright browsers are installed
        try:
            subprocess.run(['playwright', 'install', 'chromium'], 
                         capture_output=True, text=True, check=False)
        except:
            self.logger.warning("Could not auto-install Chromium. You may need to run: playwright install chromium")
        
        async with async_playwright() as p:
            # Launch browser with minimal flags for iframe access
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.browser_data_dir),
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ],
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # Track all video URLs found
            all_video_urls = {}
            video_data = []
            
            # Monitor network for Mux video URLs
            async def handle_response(response):
                url = response.url
                if 'stream.mux.com' in url and '.m3u8' in url:
                    # Extract video ID and save
                    video_id = url.split('/')[-1].split('.m3u8')[0].split('?')[0]
                    if video_id not in all_video_urls:
                        all_video_urls[video_id] = url
                        self.logger.info(f"✓ Video #{len(all_video_urls)}: {video_id}")
            
            page.on('response', handle_response)
            
            # Navigate to course
            await page.goto(self.course_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Check if we need to navigate to iframe content
            current_url = page.url
            self.logger.info(f"Initial URL: {current_url}")
            
            # Look for course iframe
            iframe_url = await page.evaluate("""
                () => {
                    const iframe = document.querySelector('iframe[src*="courses.apps.whop.com"]');
                    if (iframe) {
                        return iframe.src;
                    }
                    // Also check for redirect URLs
                    const redirectIframe = document.querySelector('iframe[src*="/core/app/launch/?redirect="]');
                    if (redirectIframe) {
                        return redirectIframe.src;
                    }
                    return null;
                }
            """)
            
            if iframe_url:
                self.logger.info(f"Found course iframe: {iframe_url[:100]}...")
                
                # If it's a relative URL, make it absolute
                if iframe_url.startswith('/'):
                    iframe_url = f"https://whop.com{iframe_url}"
                
                # Navigate to the iframe URL
                self.logger.info("Navigating to iframe content...")
                await page.goto(iframe_url, wait_until='networkidle')
                await page.wait_for_timeout(3000)
                
                self.logger.info(f"Now at: {page.url}")
            
            # Wait for page to stabilize
            await page.wait_for_timeout(5000)
            
            # Check for login requirement
            current_url = page.url
            if 'login' in current_url or 'signin' in current_url:
                self.logger.info("Login required. Please log in manually in the browser window.")
                self.logger.info("Waiting for login completion...")
                
                # Wait for navigation away from login page
                max_wait = 300  # 5 minutes
                elapsed = 0
                while elapsed < max_wait:
                    await page.wait_for_timeout(2000)
                    elapsed += 2
                    
                    current_url = page.url
                    if 'login' not in current_url and 'signin' not in current_url:
                        self.logger.info("Login detected, proceeding...")
                        break
                    
                    if elapsed % 30 == 0:
                        self.logger.info(f"Still waiting for login... ({elapsed}s / {max_wait}s)")
                
                if elapsed >= max_wait:
                    self.logger.error("Login timeout. Please run again after logging in.")
                    await browser.close()
                    return []
            
            # Wait for first video to load
            self.logger.info("Waiting for course content to load...")
            await page.wait_for_timeout(5000)
            
            # Detect navigation method
            self.logger.info("Detecting navigation method...")
            
            # Test if ArrowRight works
            initial_url = page.url
            await page.keyboard.press('ArrowRight')
            await page.wait_for_timeout(3000)
            
            keyboard_nav_works = page.url != initial_url
            if keyboard_nav_works:
                self.logger.info("✓ Keyboard navigation (ArrowRight) detected")
                # Go back to start
                await page.keyboard.press('ArrowLeft')
                await page.wait_for_timeout(2000)
            else:
                self.logger.info("✗ Keyboard navigation not working")
            
            # Start navigation
            self.logger.info("Starting video extraction...")
            
            urls_file = self.downloads_dir / "video_urls.json"
            navigation_count = 0
            no_new_videos_count = 0
            last_video_count = 0
            max_attempts = 150
            
            # If keyboard nav works, use it
            if keyboard_nav_works:
                self.logger.info("Using keyboard navigation (ArrowRight key)")
                
                for attempt in range(max_attempts):
                    navigation_count += 1
                    
                    # Wait for video to load
                    await page.wait_for_timeout(2000)
                    
                    # Check if we found new videos
                    if len(all_video_urls) > last_video_count:
                        last_video_count = len(all_video_urls)
                        no_new_videos_count = 0
                        self.logger.info(f"Navigation {navigation_count}: Found {len(all_video_urls)} videos")
                    else:
                        no_new_videos_count += 1
                        if no_new_videos_count % 10 == 0:
                            self.logger.info(f"Navigation {navigation_count}: {len(all_video_urls)} videos found (no new for {no_new_videos_count} attempts)")
                    
                    # Stop if we haven't found new videos in many attempts
                    if no_new_videos_count > 30 and len(all_video_urls) > 0:
                        self.logger.info(f"Completed extraction after {no_new_videos_count} attempts without new videos")
                        self.logger.info(f"✓ Found {len(all_video_urls)} total videos")
                        break
                    
                    # Navigate to next lesson
                    await page.keyboard.press('ArrowRight')
                    
                    # If stuck for too long, try alternative navigation
                    if no_new_videos_count > 15:
                        self.logger.info("Trying alternative navigation...")
                        
                        # Try clicking on video area to focus it
                        try:
                            video_area = await page.query_selector('video, mux-player, [class*="video"], [class*="player"]')
                            if video_area:
                                await video_area.click()
                                await page.wait_for_timeout(500)
                        except:
                            pass
                        
                        # Try Space key as alternative
                        await page.keyboard.press('Space')
                        await page.wait_for_timeout(2000)
                        
                        # Reset counter to continue trying
                        no_new_videos_count = 10
            else:
                # Keyboard navigation doesn't work - use manual mode
                self.logger.info("\n" + "="*60)
                self.logger.info("MANUAL NAVIGATION MODE")
                self.logger.info("="*60)
                self.logger.info("Automatic navigation is not available for this course.")
                self.logger.info("Please manually click through all lessons in the browser.")
                self.logger.info("The script will automatically capture video URLs.")
                self.logger.info("When done, close the browser window.")
                self.logger.info("="*60 + "\n")
                
                # Monitor for manual navigation
                self.logger.info("Monitoring for videos...")
                start_time = asyncio.get_event_loop().time()
                
                try:
                    while True:
                        await page.wait_for_timeout(2000)
                        
                        # Check if we found new videos
                        if len(all_video_urls) > last_video_count:
                            last_video_count = len(all_video_urls)
                            self.logger.info(f"✓ Found video #{len(all_video_urls)}")
                        
                        # Check if browser is still open
                        try:
                            await page.evaluate("1")
                        except:
                            self.logger.info("Browser closed by user")
                            break
                        
                        # Status update every 30 seconds
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                            self.logger.info(f"Still monitoring... ({len(all_video_urls)} videos found)")
                        
                        # Timeout after 10 minutes
                        if elapsed > 600:
                            self.logger.info("Timeout after 10 minutes")
                            break
                except Exception as e:
                    # Handle any errors gracefully (like browser being closed)
                    if "Target closed" in str(e) or "Target page" in str(e):
                        self.logger.info("Browser window closed - extraction complete")
                    else:
                        self.logger.error(f"Unexpected error during monitoring: {e}")
                    # Continue with the videos we've collected
            
            # Convert collected URLs to video_data format
            for index, (video_id, url) in enumerate(all_video_urls.items(), 1):
                video_info = {
                    'title': f'Lesson {index:02d}',
                    'url': url,
                    'video_id': video_id,
                    'index': index
                }
                video_data.append(video_info)
            
            # Save all video URLs
            with open(urls_file, 'w') as f:
                json.dump(video_data, f, indent=2)
            
            try:
                await browser.close()
            except:
                pass  # Browser might already be closed
            
            self.logger.info(f"\nExtraction complete! Found {len(video_data)} videos")
            return video_data

    def download_video(self, video_info, index, total):
        """Download a single video using yt-dlp"""
        title = video_info['title']
        url = video_info['url']
        
        # Create safe filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        
        output_path = self.videos_dir / f"{index:03d}_{safe_title}.mp4"
        
        # Skip if already downloaded
        if output_path.exists():
            self.logger.info(f"[{index}/{total}] Already downloaded: {title}")
            return True
        
        self.logger.info(f"[{index}/{total}] Downloading: {title}")
        
        # Try different format options in order of preference
        format_options = [
            'best[ext=mp4]/best',  # Original format
            'best',                # Any best format
            'bestvideo+bestaudio/best',  # Best video+audio
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # MP4 preferred
            'bestvideo*+bestaudio/best',  # Any video+audio format
        ]
        
        for format_option in format_options:
            # Build command with current format option
            cmd = [
                'yt-dlp',
                '--no-warnings',
                '--quiet',
                '--progress',
                '--no-check-certificate',
                '--referer', 'https://whop.com/',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-f', format_option,
                '-o', str(output_path),
                url
            ]
            
            # For m3u8 streams, add appropriate options
            if '.m3u8' in url:
                cmd.extend(['--concurrent-fragments', '4'])
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.logger.info(f"[{index}/{total}] ✓ Downloaded: {title}")
                    return True
                elif "Requested format is not available" in result.stderr:
                    # Try next format
                    if format_option != format_options[-1]:
                        self.logger.debug(f"Format '{format_option}' not available, trying next...")
                        continue
                else:
                    # Other error, log and continue
                    self.logger.error(f"[{index}/{total}] ✗ Failed with format '{format_option}': {title}")
                    self.logger.error(f"  Error: {result.stderr.strip()}")
                    continue
            except Exception as e:
                self.logger.error(f"[{index}/{total}] ✗ Exception: {title} - {e}")
                continue
        
        # If all formats failed, try one more time with the most permissive settings
        self.logger.info(f"[{index}/{total}] Attempting fallback download...")
        fallback_cmd = [
            'yt-dlp',
            '--no-warnings',
            '--quiet',
            '--progress',
            '--no-check-certificate',
            '--referer', 'https://whop.com/',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--merge-output-format', 'mp4',
            '-o', str(output_path),
            url
        ]
        
        try:
            result = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"[{index}/{total}] ✓ Downloaded (fallback): {title}")
                return True
        except:
            pass
        
        self.logger.error(f"[{index}/{total}] ✗ Failed all download attempts: {title}")
        return False

    async def run_download(self, force_reextract=False):
        """Extract and download all videos"""
        self.logger.info("=== Whop Course Downloader ===")
        self.logger.info(f"Course URL: {self.course_url}")
        self.logger.info(f"Target directory: {self.target_dir}")
        
        # Extract video URLs
        video_data = await self.extract_video_urls(force_reextract)
        
        if not video_data:
            self.logger.error("No videos found. Exiting.")
            return False
        
        # Check which videos already exist
        already_downloaded = []
        to_download = []
        
        for i, video_info in enumerate(video_data, 1):
            title = video_info['title']
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')
            output_path = self.videos_dir / f"{i:03d}_{safe_title}.mp4"
            
            if output_path.exists():
                already_downloaded.append(video_info)
            else:
                to_download.append((i, video_info))
        
        # Show summary
        self.logger.info(f"\n=== Download Summary ===")
        self.logger.info(f"Total videos: {len(video_data)}")
        self.logger.info(f"Already downloaded: {len(already_downloaded)}")
        self.logger.info(f"To download: {len(to_download)}")
        
        if len(to_download) == 0:
            self.logger.info("\nAll videos already downloaded!")
            return True
        
        # Download videos
        self.logger.info(f"\nStarting download of {len(to_download)} videos...")
        
        failed_downloads = []
        for i, video_info in to_download:
            success = self.download_video(video_info, i, len(video_data))
            if not success:
                failed_downloads.append(video_info)
            
            # Small delay between downloads
            time.sleep(1)
        
        # Final summary
        self.logger.info("\n=== Final Results ===")
        self.logger.info(f"Total videos: {len(video_data)}")
        self.logger.info(f"Previously downloaded: {len(already_downloaded)}")
        self.logger.info(f"Newly downloaded: {len(to_download) - len(failed_downloads)}")
        self.logger.info(f"Failed: {len(failed_downloads)}")
        
        if failed_downloads:
            self.logger.info("\nFailed downloads:")
            for video in failed_downloads:
                self.logger.info(f"  - {video['title']}")
        
        self.logger.info(f"\nVideos saved to: {self.videos_dir}")
        return len(failed_downloads) == 0

    async def run_test(self, force_reextract=False):
        """Test extraction only (no downloads)"""
        self.logger.info("=== Whop Course Downloader - Test Mode ===")
        self.logger.info(f"Course URL: {self.course_url}")
        self.logger.info("\nExtracting video URLs only (no downloads)...")
        
        # Extract video URLs (uses cache if available)
        video_data = await self.extract_video_urls(force_reextract)
        
        if not video_data:
            self.logger.error("No videos found.")
            return False
        
        # Display results
        self.logger.info(f"\n✓ Extraction complete!")
        self.logger.info(f"Total videos found: {len(video_data)}")
        
        if video_data:
            self.logger.info("\nFirst 5 videos:")
            for video in video_data[:5]:
                self.logger.info(f"  {video['index']}. {video['title']} - ID: {video['video_id']}")
            
            if len(video_data) > 10:
                self.logger.info("\nLast 5 videos:")
                for video in video_data[-5:]:
                    self.logger.info(f"  {video['index']}. {video['title']} - ID: {video['video_id']}")
        
        # Save URLs for inspection
        urls_file = self.downloads_dir / "video_urls.json"
        self.logger.info(f"\nVideo URLs saved to: {urls_file}")
        
        return len(video_data) > 0


def download_command(course_url, target_dir=None, force_reextract=False):
    """Download all videos from a course"""
    downloader = WhopDownloader(course_url, target_dir)
    success = asyncio.run(downloader.run_download(force_reextract))
    return 0 if success else 1


def test_command(course_url, force_reextract=False):
    """Test extraction without downloading"""
    downloader = WhopDownloader(course_url, target_dir=None)  # Use current directory like download
    success = asyncio.run(downloader.run_test(force_reextract))
    return 0 if success else 1


def main():
    """Main entry point for uvx"""
    if len(sys.argv) < 3:
        print("Whop Course Downloader")
        print("\nUsage:")
        print("  uvx whop_downloader.py download <course_url> [target_directory] [--force]")
        print("  uvx whop_downloader.py test <course_url> [--force]")
        print("\nCommands:")
        print("  download - Extract and download all videos from the course")
        print("  test     - Extract video URLs only (no downloading)")
        print("\nOptions:")
        print("  --force  - Force re-extraction of video URLs even if cache exists")
        print("\nExamples:")
        print("  uvx whop_downloader.py download https://whop.com/course-name")
        print("  uvx whop_downloader.py download https://whop.com/course-name /path/to/save")
        print("  uvx whop_downloader.py download https://whop.com/course-name --force")
        print("  uvx whop_downloader.py test https://courses.apps.whop.com/experience/exp_xxx/")
        print("  uvx whop_downloader.py test https://whop.com/course-name --force")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    course_url = sys.argv[2]
    
    if command == "download":
        # Parse arguments
        target_dir = None
        force_reextract = False
        
        for arg in sys.argv[3:]:
            if arg == "--force":
                force_reextract = True
            elif not arg.startswith("--"):
                target_dir = arg
        
        sys.exit(download_command(course_url, target_dir, force_reextract))
    elif command == "test":
        # Parse --force flag for test command
        force_reextract = "--force" in sys.argv[3:]
        sys.exit(test_command(course_url, force_reextract))
    else:
        print(f"Unknown command: {command}")
        print("Use 'download' or 'test'")
        sys.exit(1)


if __name__ == "__main__":
    main()