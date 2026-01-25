# 🏀 NBA Player Origin Quiz

A fun web-based quiz game where you test your knowledge of which college or country NBA players came from. Play it from any device, including your iPhone!

## Features

- ✅ Random quiz questions about NBA players
- ✅ Track your score and accuracy
- ✅ Mobile-friendly responsive design
- ✅ Clean, modern interface
- ✅ Works in any web browser

## Future Enhancements (Coming Soon)

- [ ] Filter players by minutes played
- [ ] Expanded player database (hundreds of players)
- [ ] Difficulty levels
- [ ] Leaderboard
- [ ] Hints system
- [ ] Multiple choice mode

## Step-by-Step Deployment Guide

### Prerequisites

1. **GitHub Account** - Sign up at [github.com](https://github.com)
2. **Fly.io Account** - Sign up at [fly.io](https://fly.io)
3. **Git installed** on your computer - Download from [git-scm.com](https://git-scm.com)
4. **Fly CLI installed** - Instructions below

### Step 1: Install Fly CLI

**On Mac:**
```bash
brew install flyctl
```

**On Linux:**
```bash
curl -L https://fly.io/install.sh | sh
```

**On Windows:**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

### Step 2: Authenticate with Fly.io

```bash
fly auth login
```

This will open your browser to log in to Fly.io.

### Step 3: Create GitHub Repository

1. Go to [github.com](https://github.com) and click "New repository"
2. Name it `nba-origin-quiz` (or whatever you prefer)
3. Make it public or private (your choice)
4. Don't initialize with README (we already have one)
5. Click "Create repository"

### Step 4: Upload Your Code to GitHub

Open Terminal (Mac) or Command Prompt (Windows) and navigate to where you downloaded these files:

```bash
cd path/to/nba-quiz-game

# Initialize git repository
git init

# Add all files
git add .

# Commit the files
git commit -m "Initial commit - NBA quiz game"

# Add your GitHub repository as remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/nba-origin-quiz.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 5: Deploy to Fly.io

Still in your project directory:

```bash
# Launch the app (this will create and deploy)
fly launch

# When prompted:
# - App name: Press Enter to accept the suggested name, or type your own
# - Region: Choose one close to you (or press Enter for default)
# - PostgreSQL: No
# - Redis: No
# - Deploy now: Yes
```

The deployment will take 1-2 minutes.

### Step 6: Open Your Game!

Once deployed, Fly.io will give you a URL like: `https://your-app-name.fly.dev`

You can also open it directly:
```bash
fly open
```

Add this URL to your iPhone's home screen for easy access:
1. Open the URL in Safari
2. Tap the Share button
3. Tap "Add to Home Screen"
4. Name it "NBA Quiz"

## Making Updates

After making changes to your code:

```bash
# Commit changes to git
git add .
git commit -m "Describe your changes"
git push

# Deploy updated version
fly deploy
```

## Project Structure

```
nba-quiz-game/
├── app.py                 # Flask backend (API endpoints)
├── templates/
│   └── index.html        # Frontend (quiz interface)
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── fly.toml            # Fly.io deployment config
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## How to Expand the Player Database

Currently, the game has 10 sample players. To add more:

1. Edit `app.py`
2. Find the `NBA_PLAYERS` list
3. Add more entries following this format:

```python
{"name": "Player Name", "origin": "College/Country", "type": "College/Country"},
```

Or integrate with a real NBA API (see "Using Real NBA Data" section below).

## Using Real NBA Data

To use a comprehensive NBA database, we can integrate with the NBA API or BallDontLie API:

```python
# Example: Using BallDontLie API (free, no key needed)
import requests

def fetch_nba_players():
    response = requests.get("https://www.balldontlie.io/api/v1/players")
    players = response.json()['data']
    # Process and format player data
    return players
```

I can help you integrate this if you'd like!

## Filtering by Minutes Played

To add the minutes filter you mentioned:

1. Get player stats from an API (including minutes played)
2. Add a filter in `app.py`:

```python
def get_eligible_players(min_minutes=1000):
    return [p for p in NBA_PLAYERS if p.get('career_minutes', 0) >= min_minutes]
```

## Troubleshooting

**Issue: `fly` command not found**
- Make sure Fly CLI is installed and in your PATH
- Try closing and reopening your terminal

**Issue: Deployment fails**
- Check your Fly.io account has available resources
- Verify all files are committed to git
- Check logs: `fly logs`

**Issue: App won't start**
- Check logs: `fly logs`
- Ensure all dependencies are in requirements.txt
- Verify Dockerfile is correct

## Local Development

To run locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open browser to http://localhost:8080
```

## Cost

Fly.io offers a generous free tier that includes:
- 3 shared-cpu VMs
- 3GB storage

This quiz game will easily fit in the free tier!

## Support & Questions

Feel free to:
- Open an issue on GitHub
- Check Fly.io documentation: [fly.io/docs](https://fly.io/docs)
- Modify and customize as you see fit!

## License

This is your project - use it however you want!

---

Built with ❤️ for NBA fans
