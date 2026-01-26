from flask import Flask, render_template, jsonify, request
import random
import json
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Database setup
DATABASE_PATH = os.getenv('DATABASE_PATH', '/data/leaderboard.db')

def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Leaderboard table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            game_mode TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            percentage REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # User stats table for tracking practice mode performance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            player_name TEXT NOT NULL,
            player_team TEXT,
            nba_conference TEXT,
            college_conference TEXT,
            correct INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_stats_name 
        ON user_stats(display_name)
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
try:
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()
    print(f"✓ Database initialized at {DATABASE_PATH}")
except Exception as e:
    print(f"⚠ Database initialization error: {e}")
    print("  Leaderboard will not be available")

# Load NBA player data from JSON file
def load_nba_players():
    json_path = os.path.join(os.path.dirname(__file__), 'nba_players.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to sample data if JSON file not found
        return [
            {"name": "LeBron James", "origin": "St. Vincent-St. Mary HS", "type": "High School"},
            {"name": "Stephen Curry", "origin": "Davidson", "type": "College"},
            {"name": "Kevin Durant", "origin": "Texas", "type": "College"},
            {"name": "Giannis Antetokounmpo", "origin": "Greece", "type": "Country"},
            {"name": "Luka Dončić", "origin": "Slovenia", "type": "Country"},
            {"name": "Nikola Jokić", "origin": "Serbia", "type": "Country"},
            {"name": "Joel Embiid", "origin": "Cameroon", "type": "Country"},
            {"name": "Damian Lillard", "origin": "Weber State", "type": "College"},
            {"name": "Jayson Tatum", "origin": "Duke", "type": "College"},
            {"name": "Anthony Davis", "origin": "Kentucky", "type": "College"},
        ]

# Load colleges dictionary for answer matching
def load_colleges_dict():
    json_path = os.path.join(os.path.dirname(__file__), 'us_colleges.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('colleges', {})
    except:
        return {}

NBA_PLAYERS = load_nba_players()
COLLEGES_DICT = load_colleges_dict()
print(f"Loaded {len(NBA_PLAYERS)} NBA players")
print(f"Loaded {len(COLLEGES_DICT)} college variations for answer matching")

# Session storage (in production, you'd use Redis or similar)
game_sessions = {}

# Special programs where we accept both the program name and the player's country
SPECIAL_PROGRAMS = {
    'g league ignite': 'G League Ignite',
    'ignite': 'G League Ignite',
    'overtime elite': 'Overtime Elite',
    'ot elite': 'Overtime Elite'
}

def check_answer(user_answer, correct_answer, player_type, player_data=None):
    """
    Smart answer checking that handles college name variations
    For G League/Overtime Elite international players, accepts both team and country
    """
    user_lower = user_answer.lower().strip()
    correct_lower = correct_answer.lower().strip()
    
    # Exact match
    if user_lower == correct_lower:
        return True
    
    # Check if this is a special program (G League Ignite, Overtime Elite)
    # For these, we accept EITHER the program name OR the country
    if player_data:
        origin_lower = player_data.get('origin', '').lower()
        
        # Check if the correct answer is a special program
        if origin_lower in SPECIAL_PROGRAMS or any(prog in origin_lower for prog in ['ignite', 'overtime elite']):
            # If player has a country (not USA), accept the country as an answer too
            # This is stored in a hypothetical 'country' field, but we can infer from type
            # For now, if correct answer is the program, check if user gave a country name
            # We'd need to pass more player data to do this perfectly
            
            # Accept the program name variations
            if user_lower in SPECIAL_PROGRAMS:
                return True
    
    # For colleges, check if both map to the same school via the dictionary
    if player_type == 'College':
        # Check if user's answer is in the dictionary
        if user_lower in COLLEGES_DICT and correct_lower in COLLEGES_DICT:
            # Get conference for both
            user_conf = COLLEGES_DICT[user_lower]['conference']
            correct_conf = COLLEGES_DICT[correct_lower]['conference']
            
            # They must be in the same conference
            if user_conf != correct_conf:
                return False
            
            # Now check if they're variations of the SAME school
            # Build a list of common keywords that indicate the same school
            user_words = set(user_lower.replace('-', ' ').split())
            correct_words = set(correct_lower.replace('-', ' ').split())
            
            # Remove common words that don't identify the school
            stop_words = {'university', 'of', 'the', 'at', 'state', 'college', 'and', 'a', 'an'}
            user_keywords = user_words - stop_words
            correct_keywords = correct_words - stop_words
            
            # Check if they share significant keywords (same school)
            # Examples: "kentucky" in both, "duke" in both, "california" in both
            shared_keywords = user_keywords & correct_keywords
            
            # If they share at least one significant keyword, they're the same school
            # This handles: "Kentucky" == "University of Kentucky" == "UK"
            # But NOT: "Duke" == "Virginia" (no shared keywords)
            if shared_keywords:
                return True
            
            # Special case: abbreviations
            # UK -> Kentucky, UCLA -> California Los Angeles, etc.
            # Check if one is an abbreviation that appears in our dict for the other school
            if len(user_lower) <= 4 and user_lower in correct_lower:
                return True
            if len(correct_lower) <= 4 and correct_lower in user_lower:
                return True
    
    # For non-colleges (countries, etc.), do fuzzy matching
    # "United States" should match "USA", "US", etc.
    if user_lower in correct_lower or correct_lower in user_lower:
        if len(user_lower) >= 3:  # Avoid matching single letters
            return True
    
    return False


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/new-game', methods=['POST'])
def new_game():
    try:
        data = request.json or {}
        difficulty = data.get('difficulty', 'hard')
        
        # Check if players have difficulty field
        has_difficulty = any('difficulty' in p for p in NBA_PLAYERS[:5])
        
        if not has_difficulty:
            # Fallback: treat all players as hard difficulty
            print("⚠️ Warning: Player data doesn't have difficulty field. Regenerate with fetch_nba_players.py")
            filtered_players = NBA_PLAYERS
        else:
            # Filter players by difficulty
            if difficulty == 'easy':
                filtered_players = [p for p in NBA_PLAYERS if p.get('difficulty') == 'easy']
            elif difficulty == 'medium':
                filtered_players = [p for p in NBA_PLAYERS if p.get('difficulty') in ['easy', 'medium']]
            else:  # hard
                filtered_players = NBA_PLAYERS
        
        if not filtered_players:
            return jsonify({'error': f'No players available for {difficulty} difficulty. Please regenerate player data.'}), 400
        
        session_id = str(random.randint(100000, 999999))
        game_sessions[session_id] = {
            'score': 0,
            'total': 0,
            'used_players': [],
            'difficulty': difficulty,
            'available_players': filtered_players,
            'conference_stats': {
                'nba': {'Eastern': {'correct': 0, 'total': 0}, 'Western': {'correct': 0, 'total': 0}},
                'college': {}
            }
        }
        
        return jsonify({
            'session_id': session_id, 
            'player_count': len(filtered_players),
            'has_difficulty_data': has_difficulty
        })
    except Exception as e:
        print(f"Error in new_game: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/next-question', methods=['POST'])
def next_question():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id not in game_sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = game_sessions[session_id]
    available_players = session.get('available_players', NBA_PLAYERS)
    
    # Get unused players from the filtered pool
    unused_players = [p for p in available_players 
                     if p['name'] not in session['used_players']]
    
    if not unused_players:
        # Reset if all players used
        session['used_players'] = []
        unused_players = available_players
    
    # Select random player
    player = random.choice(unused_players)
    session['used_players'].append(player['name'])
    session['current_player'] = player
    
    return jsonify({
        'player_name': player['name'],
        'team': player.get('team', ''),
        'nba_conference': player.get('nba_conference', ''),
        'question_number': session['total'] + 1
    })

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    data = request.json
    session_id = data.get('session_id')
    answer = data.get('answer', '').strip()
    
    if session_id not in game_sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = game_sessions[session_id]
    current_player = session.get('current_player')
    
    if not current_player:
        return jsonify({'error': 'No active question'}), 400
    
    session['total'] += 1
    
    # Use smart answer checking
    correct = check_answer(answer, current_player['origin'], current_player['type'], current_player)
    
    # Also check alternate answer if it exists (for G League Ignite / Overtime Elite)
    if not correct and current_player.get('alternate_answer'):
        correct = check_answer(answer, current_player['alternate_answer'], 'Country', current_player)
    
    if correct:
        session['score'] += 1
    
    # Update conference statistics
    nba_conf = current_player.get('nba_conference')
    college_conf = current_player.get('college_conference')
    
    # Update NBA conference stats
    if nba_conf and nba_conf in session['conference_stats']['nba']:
        session['conference_stats']['nba'][nba_conf]['total'] += 1
        if correct:
            session['conference_stats']['nba'][nba_conf]['correct'] += 1
    
    # Update college conference stats
    if college_conf:
        if college_conf not in session['conference_stats']['college']:
            session['conference_stats']['college'][college_conf] = {'correct': 0, 'total': 0}
        session['conference_stats']['college'][college_conf]['total'] += 1
        if correct:
            session['conference_stats']['college'][college_conf]['correct'] += 1
    
    # Build answer display (show both if alternate exists)
    answer_display = current_player['origin']
    if current_player.get('alternate_answer'):
        answer_display += f" or {current_player['alternate_answer']}"
    
    return jsonify({
        'correct': correct,
        'answer': answer_display,
        'origin_type': current_player['type'],
        'college_conference': college_conf,
        'nba_conference': nba_conf,
        'score': session['score'],
        'total': session['total'],
        'conference_stats': session['conference_stats']
    })

@app.route('/api/stats', methods=['POST'])
def get_stats():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id not in game_sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = game_sessions[session_id]
    
    return jsonify({
        'score': session['score'],
        'total': session['total'],
        'percentage': round(session['score'] / session['total'] * 100, 1) if session['total'] > 0 else 0
    })

@app.route('/api/leaderboard/save', methods=['POST'])
def save_to_leaderboard():
    data = request.json
    display_name = data.get('display_name', 'Anonymous')
    game_mode = data.get('game_mode')
    difficulty = data.get('difficulty', 'hard')
    score = data.get('score')
    total = data.get('total')
    
    if not all([game_mode, score is not None, total is not None]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Combine mode and difficulty for leaderboard key (e.g., "quick10-easy")
    leaderboard_key = f"{game_mode}-{difficulty}"
    
    percentage = (score / total * 100) if total > 0 else 0
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leaderboard (display_name, game_mode, score, total, percentage)
            VALUES (?, ?, ?, ?, ?)
        ''', (display_name, leaderboard_key, score, total, percentage))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving to leaderboard: {e}")
        return jsonify({'error': 'Failed to save score'}), 500

@app.route('/api/leaderboard/<game_mode>', methods=['GET'])
def get_leaderboard(game_mode):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get top 10 scores for this game mode
        cursor.execute('''
            SELECT display_name, score, total, percentage, timestamp
            FROM leaderboard
            WHERE game_mode = ?
            ORDER BY score DESC, percentage DESC, timestamp ASC
            LIMIT 10
        ''', (game_mode,))
        
        rows = cursor.fetchall()
        conn.close()
        
        leaderboard = [
            {
                'rank': i + 1,
                'display_name': row[0],
                'score': row[1],
                'total': row[2],
                'percentage': round(row[3], 1),
                'timestamp': row[4]
            }
            for i, row in enumerate(rows)
        ]
        
        return jsonify({'leaderboard': leaderboard})
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return jsonify({'error': 'Failed to fetch leaderboard'}), 500

@app.route('/api/user-stats/save', methods=['POST'])
def save_user_stat():
    """Save a single answer for practice mode stats tracking"""
    data = request.json
    display_name = data.get('display_name')
    player_name = data.get('player_name')
    player_team = data.get('player_team')
    nba_conference = data.get('nba_conference')
    college_conference = data.get('college_conference')
    correct = data.get('correct', 0)
    
    if not all([display_name, player_name]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_stats (display_name, player_name, player_team, nba_conference, college_conference, correct)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (display_name, player_name, player_team, nba_conference, college_conference, correct))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving user stat: {e}")
        return jsonify({'error': 'Failed to save stat'}), 500

@app.route('/api/user-stats/<display_name>', methods=['GET'])
def get_user_stats(display_name):
    """Get comprehensive stats for a user"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('''
            SELECT COUNT(*), SUM(correct)
            FROM user_stats
            WHERE display_name = ?
        ''', (display_name,))
        total_questions, total_correct = cursor.fetchone()
        
        # Stats by NBA team
        cursor.execute('''
            SELECT player_team, COUNT(*) as total, SUM(correct) as correct
            FROM user_stats
            WHERE display_name = ? AND player_team IS NOT NULL
            GROUP BY player_team
            HAVING total >= 3
            ORDER BY CAST(correct AS FLOAT) / total DESC
        ''', (display_name,))
        team_stats = cursor.fetchall()
        
        # Stats by college conference
        cursor.execute('''
            SELECT college_conference, COUNT(*) as total, SUM(correct) as correct
            FROM user_stats
            WHERE display_name = ? AND college_conference IS NOT NULL
            GROUP BY college_conference
            HAVING total >= 3
            ORDER BY CAST(correct AS FLOAT) / total DESC
        ''', (display_name,))
        conference_stats = cursor.fetchall()
        
        # Most missed players
        cursor.execute('''
            SELECT player_name, COUNT(*) as attempts, SUM(correct) as correct
            FROM user_stats
            WHERE display_name = ?
            GROUP BY player_name
            HAVING attempts >= 2 AND correct < attempts
            ORDER BY CAST(correct AS FLOAT) / attempts ASC, attempts DESC
            LIMIT 10
        ''', (display_name,))
        missed_players = cursor.fetchall()
        
        # Accuracy over time (last 50 questions)
        cursor.execute('''
            SELECT correct, timestamp
            FROM user_stats
            WHERE display_name = ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (display_name,))
        recent_history = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'overall': {
                'total': total_questions or 0,
                'correct': total_correct or 0,
                'percentage': round((total_correct / total_questions * 100) if total_questions else 0, 1)
            },
            'teams': [
                {
                    'team': row[0],
                    'total': row[1],
                    'correct': row[2],
                    'percentage': round(row[2] / row[1] * 100, 1)
                }
                for row in team_stats
            ],
            'conferences': [
                {
                    'conference': row[0],
                    'total': row[1],
                    'correct': row[2],
                    'percentage': round(row[2] / row[1] * 100, 1)
                }
                for row in conference_stats
            ],
            'missed_players': [
                {
                    'player': row[0],
                    'attempts': row[1],
                    'correct': row[2]
                }
                for row in missed_players
            ],
            'recent_history': [
                {
                    'correct': bool(row[0]),
                    'timestamp': row[1]
                }
                for row in reversed(recent_history)
            ]
        })
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return jsonify({'error': 'Failed to fetch stats'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
