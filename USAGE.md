# Usage Guide

## Daily Automated Generation

The system is configured to automatically generate a post every day at 7:00 AM PST.

### How It Works

1. **Cron Job**: Runs daily at 7:00 AM PST (15:00 UTC)
2. **AWS Credentials**: Automatically refreshes before generation
3. **Post Generation**: Creates one post and sends to Telegram
4. **Logs**: All activity logged to `logs/cron.log`

### View Cron Schedule

```bash
crontab -l
```

### View Logs

```bash
# Real-time logs
tail -f logs/cron.log

# Last 50 lines
tail -n 50 logs/cron.log
```

### Manual Generation

To generate a post manually (outside the schedule):

```bash
./run-daily-generation.sh
```

## Processing Telegram Feedback

After you manually post to LinkedIn, you need to tell the system about it.

### Start the Listener

```bash
./run-listener.sh
```

This will:
1. Connect to Telegram
2. Wait for your command (`/posted`, `/skip`, or `/regenerate`)
3. Process the command
4. **Automatically exit** after processing `/posted` or `/skip`

### Telegram Commands

**`/posted`** - Save the draft to your post history
- Moves draft from pending queue to posts.json
- Updates your post count
- System learns from this post

**`/skip`** - Reject the draft
- Saves to rejected_posts.json
- System learns to avoid similar content
- Useful when the angle/topic doesn't resonate

**`/regenerate`** - Keep the topic, generate new version
- Keeps the same content idea/angle
- Generates fresh execution
- Useful when direction is good but wording needs work
- Listener stays open after regeneration (so you can review and then `/posted` or `/skip`)

### Typical Workflow

1. **Morning (7 AM PST)**: System automatically generates post and sends to Telegram
2. **Review**: Check Telegram for the draft
3. **Post to LinkedIn**: Manually copy and post to LinkedIn
4. **Feedback**: Run `./run-listener.sh` and send `/posted` in Telegram
5. **Done**: Listener automatically exits

## Manual Commands

### Generate a Post

```bash
python3 -m linkedin_content_assistant.main generate-once --profile haymang
```

### View Profile Stats

```bash
python3 -m linkedin_content_assistant.main profile-stats --profile haymang
```

### Analyze Content Intelligence

```bash
# Use cached analysis
python3 -m linkedin_content_assistant.main analyze-content --profile haymang

# Refresh with LLM analysis
python3 -m linkedin_content_assistant.main analyze-content --profile haymang --refresh
```

### Import Post History

```bash
python3 -m linkedin_content_assistant.main import-history --profile haymang --file posts.json
```

## Troubleshooting

### Cron Job Not Running

Check if cron job exists:
```bash
crontab -l
```

If empty, run setup again:
```bash
./setup-local-cron.sh
```

### AWS Credentials Expired

The cron job automatically refreshes credentials, but if you run manually:
```bash
ada credentials update --account=271149161064 --provider=isengard --role=admin --once
```

### Listener Not Responding

1. Check if Telegram bot token is correct in `.env`
2. Check if you're sending commands to the correct bot
3. Check logs: `tail -f logs/cron.log`

### No Pending Drafts

If you get "No pending drafts" when running `/posted`:
1. Generate a post first: `./run-daily-generation.sh`
2. Or wait for the daily cron job to run

## File Locations

- **Cron logs**: `logs/cron.log`
- **Application logs**: `logs/linkedin_content_assistant.log`
- **Profile config**: `profiles/active/haymang.yaml`
- **Post history**: `data/memory/haymang/posts.json`
- **Pending drafts**: `data/memory/haymang/pending_drafts.json`
- **Rejected posts**: `data/memory/haymang/rejected_posts.json`
- **Environment**: `.env`

## Tips

1. **Check logs regularly**: `tail -f logs/cron.log` to see if generation is working
2. **Test manually first**: Run `./run-daily-generation.sh` to test before relying on cron
3. **Keep listener short**: The listener exits automatically after `/posted` or `/skip` to save resources
4. **Review before posting**: Always review the generated content before posting to LinkedIn
5. **Use /skip liberally**: If content doesn't feel right, skip it - the system learns from rejections
