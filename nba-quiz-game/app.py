from flask import Flask, render_template, jsonify, request
import random
import json

app = Flask(__name__)

# NBA player data - we'll expand this with real data
# For now, using a subset as example. We'll fetch comprehensive data from an API
NBA_PLAYERS = [
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

# Session storage (in production, you'd use Redis or similar)
game_sessions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/new-game', methods=['POST'])
def new_game():
    session_id = str(random.randint(100000, 999999))
    game_sessions[session_id] = {
        'score': 0,
        'total': 0,
        'used_players': []
    }
    return jsonify({'session_id': session_id})

@app.route('/api/next-question', methods=['POST'])
def next_question():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id not in game_sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = game_sessions[session_id]
    
    # Get unused players
    available_players = [p for p in NBA_PLAYERS 
                        if p['name'] not in session['used_players']]
    
    if not available_players:
        # Reset if all players used
        session['used_players'] = []
        available_players = NBA_PLAYERS
    
    # Select random player
    player = random.choice(available_players)
    session['used_players'].append(player['name'])
    session['current_player'] = player
    
    return jsonify({
        'player_name': player['name'],
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
    correct = answer.lower() == current_player['origin'].lower()
    
    if correct:
        session['score'] += 1
    
    return jsonify({
        'correct': correct,
        'answer': current_player['origin'],
        'origin_type': current_player['type'],
        'score': session['score'],
        'total': session['total']
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
