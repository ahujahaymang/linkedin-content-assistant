# LinkedIn Post Extraction Tool

This tool helps you extract all your historical LinkedIn posts for content analysis and style learning.

## How to Use

### Step 1: Open the Extractor

1. Open `linkedin_post_extractor.html` in your web browser
2. Click "Copy Extraction Script"

### Step 2: Run on LinkedIn

1. Go to your LinkedIn profile's activity page:
   ```
   https://www.linkedin.com/in/YOUR-USERNAME/recent-activity/all/
   ```

2. Open your browser's developer console:
   - **Chrome/Edge**: Press `F12` or `Ctrl+Shift+J` (Windows) / `Cmd+Option+J` (Mac)
   - **Firefox**: Press `F12` or `Ctrl+Shift+K` (Windows) / `Cmd+Option+K` (Mac)
   - **Safari**: Enable Developer menu first, then `Cmd+Option+C`

3. Paste the copied script into the console and press Enter

4. Wait for the script to:
   - Scroll through your posts
   - Extract content, timestamps, and engagement
   - Download a JSON file

### Step 3: Import into System

Once you have the JSON file, import it:

```bash
python3 -m linkedin_content_assistant.main import-history \
  --profile haymang \
  --file linkedin_posts_2026-04-08.json
```

## What Gets Extracted

- Post content (full text)
- Timestamps
- Engagement metrics (likes, comments)
- Hashtags
- Post length

## What Happens After Import

The system will:

1. **Store all posts** in memory for reference
2. **Analyze your writing style**:
   - Common opening patterns
   - Sentence structure preferences
   - Vocabulary choices
   - Hashtag usage
   - Emoji frequency
   - Post length distribution

3. **Use this knowledge** when generating new posts to match your style

## Troubleshooting

**Script doesn't work?**
- Make sure you're on the LinkedIn activity page
- Ensure you're logged in
- Try refreshing the page and running again

**Not all posts extracted?**
- The script scrolls automatically but may miss some
- Try running it again
- Manually scroll first, then run the script

**Import fails?**
- Check the JSON file is valid
- Ensure the profile ID matches your profile
- Check file path is correct

## Privacy & Safety

- ✅ Runs in YOUR browser with YOUR session
- ✅ Only accesses YOUR OWN posts
- ✅ No credentials needed
- ✅ Data stays local
- ✅ One-time extraction
