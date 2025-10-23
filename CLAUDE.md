# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube history collection tool that:
1. Connects to an existing Chrome browser instance using Selenium
2. Scrapes YouTube watch history links
3. Fetches video subtitles using pytubefix
4. Stores data in a Supabase database

## Development Commands

### Running the Application

**Main script (collects YouTube history and fetches subtitles):**
```bash
python main.py
# Or via PowerShell:
powershell.exe -ExecutionPolicy Bypass -File run_youtube_script.ps1
# Or via batch file:
launch_visible.bat
```

**Batch subtitle processing (processes unprocessed URLs from Supabase):**
```bash
python batch_ytsubs_to_supabase.py [--lang de|en] [--source vm-cron] [--priority 0]
```

### Environment Setup

Required environment variable:
- `SUPABASE_SERVICE_KEY`: Service role key for Supabase authentication

Python version: 3.13 (as specified in `run_youtube_script.ps1`)

### Installing Dependencies

```bash
pip install -r requirements.txt
```

## Architecture & Key Components

### Configuration
- **Chrome Debug Mode**: Uses port 9222 for remote debugging
- **Chrome User Data**: Located at `C:\ChromeData\chromeprofile`
- **Supabase URL**: `http://148.230.71.150:8000/rest/v1`
- **Table**: `youtube_urls`

### Data Flow
1. Chrome browser launched in debug mode → Selenium connects to existing instance
2. YouTube history page scraped for video URLs
3. URLs deduplicated against existing Supabase entries
4. For new URLs: pytubefix fetches subtitles (tries ANDROID client, falls back to WEB)
5. Data upserted to Supabase with subtitle text

### Database Schema (inferred)
- `url` (primary/unique): YouTube video URL
- `processed`: Boolean flag for subtitle processing status
- `processed_at`: Timestamp when processed
- `subtitles`: Cleaned subtitle text (SRT timestamps removed)
- `source`: Origin of the entry (e.g., "vm-cron")
- `priority`: Integer priority value
- `added_at`: Timestamp when added

### Key Functions
- `clean_subtitle_text()` / `clean_srt_to_text()`: Removes SRT formatting, creates flowing text
- `fetch_with_pytubefix()`: Fetches subtitles for a single video
- `extract_video_id()`: Parses YouTube URLs to extract video ID
- `upsert_urls()`: Batch inserts/updates URLs in Supabase
- `fetch_existing_urls()`: Gets all existing URLs from database for deduplication

### Error Handling
- Fallback from ANDROID to WEB client for pytubefix when fetching fails
- Timeout handling for Chrome debug port connection
- Request timeout (30s) for Supabase operations