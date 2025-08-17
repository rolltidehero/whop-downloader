# Whop Course Downloader (Local version)

**The original required uv\uvx and to download the git repo with each command.**
**This version allows you to clone the repo and run it like you would normally.**

This is a Python script to download video courses from Whop using browser automation. 
Supports both automatic and manual navigation modes depending on the course structure.

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

***

## Installation

Clone the repository and set up your environment:
```sh
git clone https://github.com/mlapping/whop-downloader.git
cd whop-downloader
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
```

Install dependencies:
```sh
pip install -r requirements.txt
playwright install chromium
```

Install or update `yt-dlp` if not present:
```sh
pip install -U yt-dlp
```

## Usage

### Download a Course

```sh
python whop_downloader.py download 
```
Download to a specific directory:
```sh
python whop_downloader.py download  /path/to/save
```
Retry failed downloads (uses cached URLs):
```sh
python whop_downloader.py download 
```
Force re-extraction of URLs:
```sh
python whop_downloader.py download  --force
```

### Test Mode

Test extraction without downloading:
```sh
python whop_downloader.py test 
```

## How it Works

- **Opens browser with saved session:** Login persists between runs
- **Navigates to course:** Uses redirect URL for iframe-based courses
- **Keyboard navigation:** Uses ArrowRight key to go through all lessons (if supported)
- **Manual mode:** You manually click through lessons; script captures video URLs
- **Captures video URLs:** Monitors network traffic for Mux streaming links
- **Downloads with yt-dlp:** High quality video downloads with resume support

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

Browser session data is saved in `.whop_browser_data/` in your current working directory.

## Troubleshooting

- **Login required:** The browser will open for manual login on first run; session will persist.
- **Videos not found:** Make sure the course page loads and shows the first video.
- **Download fails:** Ensure yt-dlp is installed and up to date.
- **Session expired:** Delete `.whop_browser_data` and log in again.
- **No videos found:** Make sure you're logged in and that the course page loads properly; for manual mode, click through all lessons.

## Navigation Modes

**Automatic:** Script detects ArrowRight keyboard navigation for lessons.

**Manual:** If not supported, manually click through lessons; script will capture video URLs.

## Contributing

- Fork the repository
- Create your feature branch (`git checkout -b feature/amazing-feature`)
- Commit your changes (`git commit -m 'Add some amazing feature'`)
- Push to the branch (`git push origin feature/amazing-feature`)
- Open a Pull Request

## License

This project is for educational purposes only. Users are responsible for complying with Whop's terms of service and respecting content creators' rights.

## Disclaimer

This tool is not affiliated with Whop. Use at your own risk and ensure you have the right to download content from courses you've purchased.
