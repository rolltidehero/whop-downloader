# Whop Course Downloader

A Python script to download video courses from Whop using browser automation. Supports both automatic and manual navigation modes depending on the course structure.

## Features

- 🎯 **Smart Navigation Detection** - Automatically detects if keyboard navigation works
- 🤖 **Automatic Mode** - Uses ArrowRight key for courses that support it
- 🖱️ **Manual Mode** - Captures videos as you click through lessons
- 🔗 **Iframe Support** - Handles courses.apps.whop.com iframe architecture
- 📹 **Mux Video Support** - Downloads HLS streams with authentication
- ⏸️ **Resume Downloads** - Skips already downloaded videos
- 💾 **URL Caching** - Saves extracted URLs to avoid re-extraction
- 🔄 **Smart Retries** - Automatically tries different video formats
- 🧪 **Test Mode** - Verify extraction works before downloading

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/whop-downloader.git
cd whop-downloader

# Install Playwright browser (first time only)
playwright install chromium
```

## Usage

### Download a Course

```bash
# Basic usage
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader download <course_url>

# Download to specific directory
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader download <course_url> "/path/to/save"

# Example with full URL
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader download https://courses.apps.whop.com/customer-v2/experience/exp_xxx/

# Example with Whop course page
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader download https://whop.com/your-course-name/

# Retry failed downloads (uses cached URLs)
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader download https://whop.com/your-course-name/

# Force re-extraction of URLs
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader download https://whop.com/your-course-name/ --force
```

### Test Mode

Test extraction without downloading:

```bash
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader test <course_url>
```

## How it Works

1. **Opens browser with saved session** - Login persists between runs
2. **Navigates to course** - Uses redirect URL for iframe-based courses
3. **Keyboard navigation** - Uses ArrowRight key to go through all lessons
4. **Captures video URLs** - Monitors network traffic for Mux streaming URLs
5. **Downloads with yt-dlp** - High quality video downloads with resume support

## Commands

### `download` - Download entire course
```bash
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader download <course_url> [target_directory] [--force]
```
- Uses cached video URLs if available (skip extraction)
- Downloads videos to `target_directory/downloads/videos/`
- Skips already downloaded files
- Saves progress to `video_urls.json`
- Use `--force` to re-extract URLs even if cache exists

### `test` - Test extraction only
```bash
uvx --from git+https://github.com/mlapping/whop-downloader.git whop-downloader test <course_url> [--force]
```
- Extracts all video URLs without downloading
- Useful for verifying the script works with your course
- Saves URLs to `downloads/video_urls.json` (same as download command)

## Output Structure

```
target_directory/
├── logs/
│   └── whop_downloader.log
└── downloads/
    ├── video_urls.json
    └── videos/
        ├── 001_Lesson_01.mp4
        ├── 002_Lesson_02.mp4
        └── ...
```

Browser session data is saved in `.whop_browser_data/` in your current directory.

## Troubleshooting

- **Login required**: The browser will open for manual login on first run
- **Videos not found**: Make sure the course page loads and shows the first video
- **Download fails**: Check that yt-dlp is installed and up to date
- **Session expired**: Delete `.whop_browser_data` folder and log in again

## Navigation Modes

### Automatic Mode
Some courses support keyboard navigation. The script will automatically detect this and use ArrowRight to navigate through lessons:

```
✓ Keyboard navigation (ArrowRight) detected
Using keyboard navigation (ArrowRight key)
Navigation 1: Found 1 videos
Navigation 2: Found 2 videos
...
```

### Manual Mode
For courses that don't support keyboard navigation, the script will prompt you to navigate manually:

```
============================================================
MANUAL NAVIGATION MODE
============================================================
Automatic navigation is not available for this course.
Please manually click through all lessons in the browser.
The script will automatically capture video URLs.
When done, close the browser window.
============================================================
```

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (for uvx command)
- Dependencies (automatically installed by uvx):
  - playwright
  - yt-dlp

## Troubleshooting

### "Command not found: uvx"
Install uv first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### "Playwright browser not installed"
```bash
playwright install chromium
```

### "Login required"
The browser will open for manual login on first run. Your session is saved for future runs.

### "No videos found"
- Make sure you're logged in
- Check that the course page loads properly
- For manual mode, ensure you click through all lessons

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is for educational purposes only. Users are responsible for complying with Whop's terms of service and respecting content creators' rights.

## Disclaimer

This tool is not affiliated with Whop. Use at your own risk and ensure you have the right to download content from courses you've purchased.