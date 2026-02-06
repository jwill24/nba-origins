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

# Common school abbreviations mapping to their full names
SCHOOL_ABBREVIATIONS = {
    'uconn': 'connecticut',
    'k state': 'kansas state',
    'k-state': 'kansas state',
    'vt': 'virginia tech',
    'ku': 'kansas',
    'uk': 'kentucky',
    'unlv': 'nevada las vegas',
    'usc': 'southern california',  # Could also be South Carolina, but context will determine
    'fsu': 'florida state',
    'osu': 'ohio state',
    'asu': 'arizona state',
    'lsu': 'louisiana state',
    'tcu': 'texas christian',
    'smu': 'southern methodist',
    'byu': 'brigham young',
    'ucf': 'central florida',
    'vcu': 'virginia commonwealth',
    'ucla': 'california los angeles',
    'ucsb': 'california santa barbara',
    'ucsd': 'california san diego',
    'uci': 'california irvine',
    'ucd': 'california davis',
    'ucr': 'california riverside',
    'unc': 'north carolina',
    'uva': 'virginia',
    'psu': 'penn state',
    'msu': 'michigan state',
    'iu': 'indiana',
    'ttu': 'texas tech',
    'ksu': 'kansas state',
    'wvu': 'west virginia',
    'uga': 'georgia',
    'ua': 'arizona',
    'uf': 'florida',
    'ut': 'texas',
    'ou': 'oklahoma',
    'gw': 'george washington',
    'gmu': 'george mason',
    'sju': 'st johns',
    'bc': 'boston college',
    'nd': 'notre dame',
    'gt': 'georgia tech',
    'wf': 'wake forest',
    'wsu': 'washington state',
    'ul': 'louisville',
    'sdsu': 'san diego state'
}

def check_answer(user_answer, correct_answer, player_type, player_data=None):
    """
    Smart answer checking that handles college name variations
    For G League/Overtime Elite international players, accepts both team and country
    """
    try:
        user_lower = user_answer.lower().strip()
        correct_lower = correct_answer.lower().strip()
        
        # Normalize spaces for abbreviation matching (remove all spaces)
        user_normalized_spaces = user_lower.replace(' ', '')
        correct_normalized_spaces = correct_lower.replace(' ', '')
        
        # Helper function for fuzzy matching (Levenshtein distance)
        def similarity_ratio(s1, s2):
            """Calculate similarity ratio between two strings (0-1)"""
            # Normalize: remove punctuation and extra spaces
            import re
            s1_norm = re.sub(r'[.\-\'\s]+', '', s1.lower())
            s2_norm = re.sub(r'[.\-\'\s]+', '', s2.lower())
            
            if not s1_norm or not s2_norm:
                return 0
            
            # Simple Levenshtein distance
            if s1_norm == s2_norm:
                return 1.0
            
            # Calculate edit distance
            len1, len2 = len(s1_norm), len(s2_norm)
            if len1 > len2:
                s1_norm, s2_norm = s2_norm, s1_norm
                len1, len2 = len2, len1
            
            distances = range(len1 + 1)
            for i2, c2 in enumerate(s2_norm):
                new_distances = [i2 + 1]
                for i1, c1 in enumerate(s1_norm):
                    if c1 == c2:
                        new_distances.append(distances[i1])
                    else:
                        new_distances.append(1 + min((distances[i1], distances[i1 + 1], new_distances[-1])))
                distances = new_distances
            
            edit_distance = distances[-1]
            max_len = max(len(s1_norm), len(s2_norm))
            return 1 - (edit_distance / max_len)
        
        # Expand abbreviations before comparison (check without spaces)
        if user_normalized_spaces in SCHOOL_ABBREVIATIONS:
            user_expanded = SCHOOL_ABBREVIATIONS[user_normalized_spaces]
        else:
            user_expanded = user_lower
            
        if correct_normalized_spaces in SCHOOL_ABBREVIATIONS:
            correct_expanded = SCHOOL_ABBREVIATIONS[correct_normalized_spaces]
        else:
            correct_expanded = correct_lower
        
        # Exact match (after expansion)
        if user_expanded == correct_expanded:
            return True
        if user_lower == correct_lower:
            return True
        
        # Fuzzy match for typos (80% similarity threshold)
        # "gonaga" vs "gonzaga" = 85.7% match ✓
        # "tecas" vs "texas" = 80% match ✓
        # "st vincent st marys" vs "st vincent st mary" = 95% match ✓
        # Strip parenthetical content first for fair comparison
        import re
        user_for_fuzzy = re.sub(r'\([^)]*\)', '', user_lower).strip()
        correct_for_fuzzy = re.sub(r'\([^)]*\)', '', correct_lower).strip()
        
        similarity = similarity_ratio(user_for_fuzzy, correct_for_fuzzy)
        if similarity >= 0.80:
            return True
        
        # Check if abbreviation matches expanded form
        # e.g., "uconn" (expanded to "connecticut") should match "university of connecticut"
        if user_expanded in correct_lower or correct_expanded in user_lower:
            if len(user_expanded) >= 3:
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
                user_words = set(user_expanded.replace('-', ' ').split())
                correct_words = set(correct_expanded.replace('-', ' ').split())
                
                # Remove common words that don't identify the school
                stop_words = {'university', 'of', 'the', 'at', 'state', 'college', 'and', 'a', 'an'}
                user_keywords = user_words - stop_words
                correct_keywords = correct_words - stop_words
                
                # CRITICAL: Prevent subset matches like "Iowa" matching "Iowa State"
                # Both must have the SAME keywords, not just overlapping ones
                # Exception: if one is clearly an abbreviation (<=4 chars)
                if len(user_lower) > 4 and len(correct_lower) > 4:
                    # Both are full words - they must have identical keywords
                    if user_keywords == correct_keywords:
                        return True
                else:
                    # At least one is an abbreviation - check for overlap
                    shared_keywords = user_keywords & correct_keywords
                    
                    # Special case: "california" alone is not enough (UCLA vs USC)
                    # Need at least 2 shared keywords OR a unique keyword
                    if shared_keywords == {'california'}:
                        # Not enough - UCLA and USC both have "california"
                        return False
                    elif shared_keywords:
                        return True
                
                # Special case: abbreviations
                # UK -> Kentucky, UCLA -> California Los Angeles, etc.
                # Check if one is an abbreviation that appears in our dict for the other school
                if len(user_lower) <= 4 and user_lower in correct_lower:
                    return True
                if len(correct_lower) <= 4 and correct_lower in user_lower:
                    return True
        
        # For non-colleges (countries, high schools, etc.), do fuzzy matching
        # "United States" should match "USA", "US", etc.
        # "St Vincent St Marys" should match "St. Vincent-St. Mary HS (OH)"
        
        # Normalize for comparison: remove punctuation, extra spaces, and parenthetical content
        import re
        
        # Remove parenthetical content first (like "(OH)", "(CA)", etc.)
        user_clean = re.sub(r'\([^)]*\)', '', user_lower).strip()
        correct_clean = re.sub(r'\([^)]*\)', '', correct_lower).strip()
        
        # Then remove punctuation and extra spaces
        user_normalized = re.sub(r'[.\-\']', '', user_clean).strip()
        user_normalized = re.sub(r'\s+', ' ', user_normalized)
        correct_normalized = re.sub(r'[.\-\']', '', correct_clean).strip()
        correct_normalized = re.sub(r'\s+', ' ', correct_normalized)
        
        # Check if one is contained in the other after normalization
        if user_normalized in correct_normalized or correct_normalized in user_normalized:
            # Make sure it's a substantial match (at least 5 characters or 3 words)
            if len(user_normalized) >= 5 or len(user_normalized.split()) >= 3:
                return True
        
        # Only allow very short abbreviations (<=3 chars) for substring matching
        # This handles: "UK", "USC", "Cal" but NOT "Ohio", "Iowa", "Duke"
        shorter = user_lower if len(user_lower) < len(correct_lower) else correct_lower
        longer = correct_lower if len(user_lower) < len(correct_lower) else user_lower
        
        if len(shorter) <= 3 and shorter in longer:
            # Check if it's a meaningful match:
            # 1. If it's at the start of the string (e.g., "cal" in "california")
            # 2. If it's a whole word (e.g., "usa" in "born in usa")
            # 3. NOT if it's in the middle of a word (e.g., "cal" in "southern california")
            
            # Check if it's at the start
            if longer.startswith(shorter):
                return True
            
            # Check if it's a whole word (surrounded by spaces)
            if ' ' + shorter + ' ' in ' ' + longer + ' ':
                return True
        
        return False
    except Exception as e:
        print(f"⚠️ Error in check_answer: {e}")
        print(f"  user_answer: '{user_answer}', correct_answer: '{correct_answer}', type: '{player_type}'")
        import traceback
        traceback.print_exc()
        return False


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check-answer-simple', methods=['POST'])
def check_answer_simple():
    """Simple answer checking endpoint for daily challenge"""
    data = request.json
    user_answer = data.get('user_answer', '')
    correct_answer = data.get('correct_answer', '')
    player_type = data.get('player_type', 'Other')
    
    is_correct = check_answer(user_answer, correct_answer, player_type, None)
    
    return jsonify({'correct': is_correct})

@app.route('/api/daily-challenge', methods=['GET'])
def get_daily_challenge():
    """Get today's daily challenge - same 5 players for everyone"""
    try:
        import datetime
        import random
        from zoneinfo import ZoneInfo
        
        # Get current time in ET
        et_tz = ZoneInfo('America/New_York')
        now_et = datetime.datetime.now(et_tz)
        
        # If it's before 3am ET, use yesterday's date
        if now_et.hour < 3:
            challenge_date = (now_et - datetime.timedelta(days=1)).date()
        else:
            challenge_date = now_et.date()
        
        # Use challenge date as seed so everyone gets same players
        seed = int(challenge_date.strftime('%Y%m%d'))
        
        print(f"📅 Daily Challenge: Current ET time={now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}, Challenge date={challenge_date}, Seed={seed}")
        print(f"📊 Total players available: {len(NBA_PLAYERS)}")
        
        # Create a seeded random generator
        rng = random.Random(seed)
        
        # Filter players by difficulty
        easy_players = [p for p in NBA_PLAYERS if p.get('difficulty') == 'easy']
        medium_players = [p for p in NBA_PLAYERS if p.get('difficulty') == 'medium']
        hard_players = [p for p in NBA_PLAYERS if p.get('difficulty') == 'hard']
        
        print(f"Available: Easy={len(easy_players)}, Medium={len(medium_players)}, Hard={len(hard_players)}")
        
        # Smart selection with MPG ranges:
        # Q1: Easy multiple choice (household name, any MPG)
        # Q2: Easy text (household name, any MPG)
        # Q3: 25+ MPG (starter/star level)
        # Q4: 20-25 MPG (solid rotation player)
        # Q5: 10-20 MPG (bench/role player)
        
        daily_players = []
        question_types = []
        
        # Q1: Easy player for multiple choice
        if easy_players and len(easy_players) >= 2:
            q1 = rng.choice(easy_players)
            daily_players.append(q1)
            question_types.append('multiplechoice')
            
            # Q2: Different easy player for text input
            remaining_easy = [p for p in easy_players if p['name'] != q1['name']]
            if remaining_easy:
                daily_players.append(rng.choice(remaining_easy))
                question_types.append('text')
        elif easy_players:
            # Not enough easy players, use what we have
            daily_players.append(rng.choice(easy_players))
            question_types.append('multiplechoice')
            daily_players.append(rng.choice(easy_players))
            question_types.append('text')
        
        # Q3: 25+ MPG player (starter/star level)
        selected_names = [p['name'] for p in daily_players]
        high_mpg = [p for p in NBA_PLAYERS if p.get('mpg', 0) >= 25 and p['name'] not in selected_names]
        
        if high_mpg:
            q3 = rng.choice(high_mpg)
            daily_players.append(q3)
            question_types.append('text')
            print(f"Q3 (25+ MPG): {q3['name']} - {q3.get('mpg')}mpg ({q3.get('difficulty')})")
        else:
            # Fallback to medium pool
            medium_pool = [p for p in NBA_PLAYERS if p.get('difficulty') in ['easy', 'medium']]
            available = [p for p in medium_pool if p['name'] not in selected_names]
            if available:
                q3 = rng.choice(available)
                daily_players.append(q3)
                question_types.append('text')
                print(f"Q3 (fallback): {q3['name']}")
        
        # Q4: 20-25 MPG player (rotation player)
        selected_names = [p['name'] for p in daily_players]
        mid_mpg = [p for p in NBA_PLAYERS if 20 <= p.get('mpg', 0) < 25 and p['name'] not in selected_names]
        
        if mid_mpg:
            q4 = rng.choice(mid_mpg)
            daily_players.append(q4)
            question_types.append('text')
            print(f"Q4 (20-25 MPG): {q4['name']} - {q4.get('mpg')}mpg ({q4.get('difficulty')})")
        else:
            # Fallback
            medium_pool = [p for p in NBA_PLAYERS if p.get('difficulty') in ['easy', 'medium']]
            available = [p for p in medium_pool if p['name'] not in selected_names]
            if available:
                q4 = rng.choice(available)
                daily_players.append(q4)
                question_types.append('text')
                print(f"Q4 (fallback): {q4['name']}")
        
        # Q5: 10-20 MPG player (bench/role player)
        selected_names = [p['name'] for p in daily_players]
        low_mpg = [p for p in NBA_PLAYERS if 10 <= p.get('mpg', 0) < 20 and p['name'] not in selected_names]
        
        if low_mpg:
            q5 = rng.choice(low_mpg)
            daily_players.append(q5)
            question_types.append('text')
            print(f"Q5 (10-20 MPG): {q5['name']} - {q5.get('mpg')}mpg ({q5.get('difficulty')})")
        else:
            # Fallback to hard
            available_hard = [p for p in hard_players if p['name'] not in selected_names]
            if available_hard:
                q5 = rng.choice(available_hard)
                daily_players.append(q5)
                question_types.append('text')
                print(f"Q5 (fallback hard): {q5['name']}")
        
        print(f"✅ Selected {len(daily_players)} players")
        print(f"✅ Question types: {question_types}")
        print(f"✅ Players in order:")
        for i, p in enumerate(daily_players, 1):
            print(f"   Q{i}: {p['name']} ({p.get('difficulty', 'unknown')})")
        
        # Ensure we have exactly 5
        while len(daily_players) < 5:
            available = [p for p in NBA_PLAYERS if p not in daily_players]
            if available:
                daily_players.append(rng.choice(available))
                question_types.append('text')
            else:
                break
        
        # Make sure players are JSON serializable
        clean_players = []
        for p in daily_players[:5]:
            clean_players.append({
                'name': p['name'],
                'team': p.get('team', ''),
                'origin': p.get('origin', ''),
                'type': p.get('type', 'Other'),
                'nba_conference': p.get('nba_conference', ''),
                'college_conference': p.get('college_conference')
            })
        
        response_data = {
            'date': challenge_date.isoformat(),
            'players': clean_players,
            'question_types': question_types[:5],
            'challenge_number': (challenge_date - datetime.date(2026, 1, 27)).days + 1  # Day #1 = Jan 27, 2026
        }
        
        print(f"✅ Returning {len(clean_players)} players with types: {question_types[:5]}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error in get_daily_challenge: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/new-game', methods=['POST'])
def new_game():
    try:
        data = request.json or {}
        difficulty = data.get('difficulty', 'hard')
        is_multiple_choice = data.get('is_multiple_choice', False)
        
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
        
        # Shuffle the filtered players for better randomness
        random.shuffle(filtered_players)
        
        session_id = str(random.randint(100000, 999999))
        game_sessions[session_id] = {
            'score': 0,
            'total': 0,
            'used_players': [],
            'difficulty': difficulty,
            'is_multiple_choice': is_multiple_choice,
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
        unused_players = list(available_players)  # Make a copy
        random.shuffle(unused_players)  # Shuffle when resetting
    
    # Shuffle the unused players list for maximum randomness
    random.shuffle(unused_players)
    
    # Select random player (now from a shuffled list)
    player = unused_players[0]
    session['used_players'].append(player['name'])
    session['current_player'] = player
    
    return jsonify({
        'player_name': player['name'],
        'team': player.get('team', ''),
        'nba_conference': player.get('nba_conference', ''),
        'question_number': session['total'] + 1,
        'multiple_choice_options': generate_multiple_choice_options(player, available_players) if session.get('is_multiple_choice') else None,
        'correct_answer': player['origin'] if session.get('is_multiple_choice') else None
    })

def generate_multiple_choice_options(correct_player, all_players):
    """Generate 4 multiple choice options with 1 correct and 3 wrong answers"""
    correct_origin = correct_player['origin']
    
    # Get 3 wrong answers from other players
    wrong_options = []
    other_players = [p for p in all_players if p['name'] != correct_player['name']]
    random.shuffle(other_players)
    
    for other in other_players:
        if other['origin'] != correct_origin and other['origin'] not in wrong_options:
            wrong_options.append(other['origin'])
        if len(wrong_options) >= 3:
            break
    
    # If not enough unique wrong answers, add generic options
    if len(wrong_options) < 3:
        generic_options = [
            'Duke', 'Kentucky', 'North Carolina', 'Kansas', 'UCLA',
            'France', 'Serbia', 'Spain', 'Australia', 'Canada',
            'Michigan State', 'Villanova', 'Connecticut', 'Syracuse', 'Louisville'
        ]
        for option in generic_options:
            if len(wrong_options) >= 3:
                break
            if option != correct_origin and option not in wrong_options:
                wrong_options.append(option)
    
    # Combine and shuffle
    all_options = [correct_origin] + wrong_options[:3]
    random.shuffle(all_options)
    return all_options

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
    
    # Debug logging
    print(f"Player: {current_player.get('name', 'UNKNOWN')}, Origin: {current_player.get('origin', 'MISSING')}, Type: {current_player.get('type', 'MISSING')}")
    
    # Check if player has required data
    if not current_player.get('origin'):
        print(f"⚠️ Warning: Player {current_player.get('name', 'Unknown')} missing origin data")
        print(f"Current player data: {current_player}")
        return jsonify({
            'error': f"Player data incomplete for {current_player.get('name', 'this player')}. Please regenerate player data."
        }), 500
    
    session['total'] += 1
    
    # Use smart answer checking
    correct = check_answer(answer, current_player['origin'], current_player.get('type', 'Other'), current_player)
    
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
    answer_display = current_player.get('origin', 'Unknown')
    if current_player.get('alternate_answer'):
        answer_display += f" or {current_player['alternate_answer']}"
    
    response_data = {
        'correct': correct,
        'answer': answer_display,
        'origin_type': current_player.get('type', 'Other'),
        'college_conference': college_conf,
        'nba_conference': nba_conf,
        'player_name': current_player.get('name'),
        'player_team': current_player.get('team'),
        'score': session['score'],
        'total': session['total'],
        'conference_stats': session['conference_stats']
    }
    
    print(f"Returning response: answer='{response_data['answer']}', type='{response_data['origin_type']}'")
    
    return jsonify(response_data)

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
        
        # Most missed players (only show if < 50% correct)
        cursor.execute('''
            SELECT player_name, COUNT(*) as attempts, SUM(correct) as correct
            FROM user_stats
            WHERE display_name = ?
            GROUP BY player_name
            HAVING attempts >= 2 AND CAST(correct AS FLOAT) / attempts <= 0.5
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
