# Leaderboard Deployment Guide

## New Features Added
✅ SQLite leaderboard for all game modes (except Unlimited)
✅ Display name entry after completing a game
✅ Top 10 leaderboard display
✅ Different behavior for correct/wrong answers:
   - Correct: Auto-advance after 2 seconds
   - Wrong: Show "Next Question" button (must click to continue)
✅ Persistent storage using Fly.io volumes (FREE)

## Deployment Steps

### 1. Create the Persistent Volume (ONE TIME ONLY)

Run this command once to create a 1GB volume for the leaderboard:

```bash
fly volumes create leaderboard_data --size 1 --region iad
```

**Cost: $0** (included in free tier - 3GB free)

### 2. Deploy the App

```bash
fly deploy
```

That's it! The volume will automatically mount to `/data` and the leaderboard database will be created there.

## How It Works

### Game Flow

**Correct Answer:**
- Shows green checkmark
- Auto-advances to next question after 2 seconds

**Wrong Answer:**
- Shows red X with correct answer
- Must click "Next Question" button to continue
- Perfect Run: Game ends immediately
- Other modes: Continue until question limit

### Leaderboard

**At Game End:**
1. User sees final score
2. Prompted: "Would you like to save your score to the leaderboard?"
3. If Yes: Enter display name (or use "Anonymous")
4. Shows top 10 leaderboard for that game mode
5. Returns to mode selection menu

**Game Modes with Leaderboards:**
- Quick Quiz (10) - Top 10 by score
- Standard (25) - Top 10 by score
- Challenge (50) - Top 10 by score
- Perfect Run - Top 10 by streak length
- Unlimited - No leaderboard (practice mode)

### Database

- **Location:** `/data/leaderboard.db`
- **Type:** SQLite
- **Persistence:** Survives app restarts/redeployments
- **Backups:** You can download with `fly ssh console` then `cp /data/leaderboard.db /tmp/` and `fly sftp get /tmp/leaderboard.db`

## Verifying It Works

After deployment:

1. Play a game mode (not Unlimited)
2. Complete the game
3. Choose to save your score
4. Enter a name
5. View the leaderboard
6. Redeploy the app (`fly deploy`)
7. Play again - your previous scores should still be there!

## Troubleshooting

**"Volume already exists" error:**
This is fine! The volume persists. Just run `fly deploy`.

**Leaderboard not persisting:**
Check that the volume is mounted:
```bash
fly ssh console
ls -la /data
```
You should see `leaderboard.db` file there.

**Database errors in logs:**
Check logs: `fly logs`
The app will print database initialization status on startup.

## Future Enhancements

Could add:
- View all leaderboards from main menu
- Filter by date range
- Personal stats tracking
- Global leaderboard across all modes
