# Stats Dashboard Implementation Guide

## What's Been Added

### Backend (app.py)
✅ New database table: `user_stats`
✅ New endpoint: `/api/user-stats/save` - Save each answer in practice mode
✅ New endpoint: `/api/user-stats/<name>` - Get comprehensive stats

### Database Schema
```sql
user_stats table:
- id (primary key)
- display_name
- player_name
- player_team
- nba_conference  
- college_conference
- correct (0 or 1)
- timestamp
```

### Stats Tracked
1. **Overall accuracy** - Total questions and percentage
2. **Best/Worst NBA teams** - Teams you're strongest/weakest at
3. **Best/Worst college conferences** - Conferences you excel/struggle with
4. **Most missed players** - Players you've gotten wrong multiple times
5. **Recent accuracy trend** - Last 50 questions visualized

## Frontend Changes Needed

### 1. Add "My Stats" button to homepage
Already added: 📊 My Stats (Practice Mode)

### 2. Add Stats Dashboard Screen
Need to add after leaderboard screen:
- Input for display name
- Stats display with charts
- Back button

### 3. Update Unlimited Mode Flow
- Prompt for display name at start
- Save each answer to user_stats table
- Option to view stats mid-game

### 4. Add Stats Visualization
Options:
- Simple text + CSS bars (easiest)
- Chart.js library (better looking)
- Canvas-based custom charts

## Next Steps

1. **Fix homepage bug** - Check:
   - Browser console for JavaScript errors
   - Hard refresh (Ctrl+Shift+R)
   - Redeploy with `fly deploy`

2. **Complete stats dashboard UI** - Need to add:
   - Stats screen HTML
   - JavaScript to fetch/display stats
   - Chart visualization

3. **Update Unlimited mode** - Need to:
   - Prompt for name
   - Save answers to database
   - Link to stats view

## Bug Debug Checklist

Homepage buttons not working:
□ Open browser console (F12)
□ Check for JavaScript errors
□ Try hard refresh
□ Check if it's on latest deployment
□ Verify onclick handlers are present in HTML

Most likely: Browser cached old version. Solution: Hard refresh or incognito mode.
