"""
Fetch current NBA players (2025-26 season) with 5+ games played
Includes: Name, Team, College/Country, Games Played

Uses official US Department of Education database to identify colleges
"""

import requests
import json
import time
from datetime import datetime

# Global variable to store US colleges (now with conference data)
US_COLLEGES = {}
NBA_CONFERENCES = {}

# All-Stars from last 3 years (2023, 2024, 2025) for Easy mode
ALL_STARS_RECENT = {
    # 2023 All-Stars
    'LeBron James', 'Stephen Curry', 'Luka Doncic', 'Luka Dončić', 'Zion Williamson', 'Nikola Jokic', 'Nikola Jokić',
    'Kyrie Irving', 'Lauri Markkanen', 'Damian Lillard', 'Paul George', 'Shai Gilgeous-Alexander',
    'Kevin Durant', 'Jayson Tatum', 'Donovan Mitchell', 'Joel Embiid', 'Giannis Antetokounmpo',
    'Jaylen Brown', 'Jrue Holiday', 'Bam Adebayo', 'Julius Randle', 'DeMar DeRozan',
    'Tyrese Haliburton', 'Jaren Jackson Jr.', 'De\'Aaron Fox', 'Domantas Sabonis',
    # 2024 All-Stars
    'Anthony Edwards', 'Kawhi Leonard', 'Anthony Davis', 'Devin Booker', 'Nikola Vucevic', 'Nikola Vučević',
    'Trae Young', 'Paolo Banchero', 'Scottie Barnes', 'Tyrese Maxey', 'Jalen Brunson',
    'Karl-Anthony Towns', 'Jimmy Butler', 'Alperen Sengun', 'Alperen Şengün',
    # 2025 All-Stars (projected/current stars)
    'Victor Wembanyama', 'Chet Holmgren', 'Jalen Williams', 'Franz Wagner', 'Evan Mobley',
    'LaMelo Ball', 'Ja Morant', 'Desmond Bane', 'Brandon Ingram', 'Zach LaVine',
    'Rudy Gobert', 'Darius Garland', 'Jarrett Allen', 'Pascal Siakam',
    # Additional clear All-Stars
    'Chris Paul', 'Bradley Beal', 'Khris Middleton', 'Draymond Green', 'Klay Thompson',
    'James Harden', 'Russell Westbrook', 'Kristaps Porzingis', 'Kristaps Porziņģis'
}

def determine_difficulty_tier(player_name, mpg):
    """
    Determine difficulty tier based on All-Star status and MPG
    Easy: All-Stars from last 3 years
    Medium: 20+ MPG
    Hard: All others (10+ games already filtered)
    """
    if player_name in ALL_STARS_RECENT:
        return 'easy'
    elif mpg >= 20:
        return 'medium'
    else:
        return 'hard'

def load_us_colleges_from_file(filename='us_colleges.json'):
    """
    Load US colleges from pre-built JSON file with conference data
    """
    print("Loading US college database from file...")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            colleges_dict = data['colleges']  # Now a dict with conference info
            print(f"✓ Loaded {len(colleges_dict)} US colleges with conference data from {filename}\n")
            return colleges_dict
    except FileNotFoundError:
        print(f"⚠ College database file '{filename}' not found")
        print("  Using built-in college list instead...")
        return get_fallback_colleges()
    except Exception as e:
        print(f"⚠ Error loading college database: {e}")
        print("  Using built-in college list instead...")
        return get_fallback_colleges()

def load_nba_conferences(filename='nba_conferences.json'):
    """
    Load NBA team to conference mapping
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['nba_conferences']
    except:
        # Fallback NBA conference mapping
        return {
            "ATL": "Eastern", "BOS": "Eastern", "BKN": "Eastern", "CHA": "Eastern",
            "CHI": "Eastern", "CLE": "Eastern", "DET": "Eastern", "IND": "Eastern",
            "MIA": "Eastern", "MIL": "Eastern", "NYK": "Eastern", "ORL": "Eastern",
            "PHI": "Eastern", "TOR": "Eastern", "WAS": "Eastern",
            "DAL": "Western", "DEN": "Western", "GSW": "Western", "HOU": "Western",
            "LAC": "Western", "LAL": "Western", "MEM": "Western", "MIN": "Western",
            "NOP": "Western", "OKC": "Western", "PHX": "Western", "POR": "Western",
            "SAC": "Western", "SAS": "Western", "UTA": "Western"
        }

def get_fallback_colleges():
    """
    Fallback list of common colleges/universities if API fails
    """
    return {
        'duke university', 'university of kentucky', 'university of kansas',
        'university of north carolina', 'ucla', 'university of california los angeles',
        'usc', 'university of southern california', 'southern california',
        'gonzaga university', 'villanova university', 'syracuse university',
        'university of michigan', 'ohio state university', 'university of florida',
        'university of texas', 'university of arizona', 'university of louisville',
        'university of connecticut', 'uconn', 'stanford university',
        'georgetown university', 'wake forest university', 'marquette university',
        'butler university', 'purdue university', 'indiana university',
        'university of wisconsin', 'university of iowa', 'university of illinois',
        'university of memphis', 'temple university', 'university of cincinnati',
        'xavier university', 'university of dayton', 'university of virginia',
        'university of miami', 'university of georgia', 'university of alabama',
        'auburn university', 'louisiana state university', 'lsu',
        'university of arkansas', 'university of tennessee', 'vanderbilt university',
        'university of missouri', 'baylor university', 'texas christian university',
        'tcu', 'university of oklahoma', 'university of oregon',
        'university of washington', 'creighton university', 'depaul university',
        'providence college', 'seton hall university', 'university of notre dame',
        'murray state university', 'davidson college', 'lehigh university',
        'weber state university', 'virginia commonwealth university', 'vcu',
        'wichita state university', 'boston college', 'boston university',
        'harvard university', 'yale university', 'princeton university',
        'university of pennsylvania', 'texas a&m university', 'texas tech university',
        'oklahoma state university', 'kansas state university',
        'florida state university', 'georgia institute of technology', 'georgia tech',
        'clemson university', 'north carolina state university', 'nc state',
        'washington state university', 'arizona state university',
        'university of utah', 'university of colorado', 'iowa state university',
        'west virginia university', 'university of nevada', 'unlv',
        'university of san diego', 'santa clara university', 'pepperdine university',
        'loyola marymount university', 'saint mary\'s college', 'michigan state university',
        'fresno state university', 'san diego state university',
        'st. john\'s university', 'smu', 'southern methodist university',
        'university of south carolina', 'university of richmond',
        'old dominion university', 'james madison university'
    }

def get_college_info(school_name):
    """
    Check if a school name matches a US college/university and return conference
    Returns dict with 'is_college' and 'conference' keys
    """
    if not school_name:
        return {'is_college': False, 'conference': None}
    
    school_lower = school_name.lower().strip()
    
    # Direct lookup in colleges dictionary
    if school_lower in US_COLLEGES:
        return {
            'is_college': True,
            'conference': US_COLLEGES[school_lower]['conference']
        }
    
    # Try partial matching for longer names
    if len(school_lower) > 6:
        for college_name, college_data in US_COLLEGES.items():
            shorter = min(len(school_lower), len(college_name))
            longer = max(len(school_lower), len(college_name))
            if (school_lower in college_name or college_name in school_lower) and shorter / longer >= 0.6:
                return {
                    'is_college': True,
                    'conference': college_data['conference']
                }
    
    return {'is_college': False, 'conference': None}
    """
    Check if a school name matches a US college/university
    """
    if not school_name:
        return False
    
    school_lower = school_name.lower().strip()
    
    # Direct match
    if school_lower in US_COLLEGES:
        return True
    
    # Check common variations and abbreviations
    common_colleges = {
        'kentucky': 'university of kentucky',
        'duke': 'duke university',
        'kansas': 'university of kansas',
        'ucla': 'university of california los angeles',
        'usc': 'university of southern california',
        'california': 'university of california berkeley',
        'cal': 'university of california berkeley',
        'uc berkeley': 'university of california berkeley',
        'berkeley': 'university of california berkeley',
        'gonzaga': 'gonzaga university',
        'villanova': 'villanova university',
        'north carolina': 'university of north carolina',
        'unc': 'university of north carolina',
        'michigan': 'university of michigan',
        'texas': 'university of texas',
        'florida': 'university of florida',
        'arizona': 'university of arizona',
        'louisville': 'university of louisville',
        'stanford': 'stanford university',
        'georgetown': 'georgetown university',
        'syracuse': 'syracuse university',
        'uconn': 'university of connecticut',
        'connecticut': 'university of connecticut',
        'purdue': 'purdue university',
        'indiana': 'indiana university',
        'wisconsin': 'university of wisconsin',
        'iowa': 'university of iowa',
        'illinois': 'university of illinois',
        'ohio state': 'ohio state university',
        'memphis': 'university of memphis',
        'virginia': 'university of virginia',
        'georgia': 'university of georgia',
        'alabama': 'university of alabama',
        'auburn': 'auburn university',
        'lsu': 'louisiana state university',
        'arkansas': 'university of arkansas',
        'tennessee': 'university of tennessee',
        'vanderbilt': 'vanderbilt university',
        'missouri': 'university of missouri',
        'baylor': 'baylor university',
        'oklahoma': 'university of oklahoma',
        'oregon': 'university of oregon',
        'washington': 'university of washington',
        'davidson': 'davidson college',
        'butler': 'butler university',
        'marquette': 'marquette university',
        'creighton': 'creighton university',
        'xavier': 'xavier university',
        'wake forest': 'wake forest university',
        'southern california': 'university of southern california',
        'michigan state': 'michigan state university',
        'florida state': 'florida state university',
        'kansas state': 'kansas state university',
        'oklahoma state': 'oklahoma state university',
        'arizona state': 'arizona state university',
        'iowa state': 'iowa state university',
        'washington state': 'washington state university',
        'oregon state': 'oregon state university',
        'ohio': 'ohio university',
        'miami': 'university of miami',
        'notre dame': 'university of notre dame',
        'boston college': 'boston college',
        'virginia tech': 'virginia polytechnic institute',
        'texas a&m': 'texas a&m university',
        'texas tech': 'texas tech university',
        'tcu': 'texas christian university',
        'smu': 'southern methodist university',
        'colorado': 'university of colorado',
        'utah': 'university of utah',
        'nevada': 'university of nevada',
        'unlv': 'university of nevada las vegas',
        'vcu': 'virginia commonwealth university',
        'murray state': 'murray state university',
        'weber state': 'weber state university',
        'lehigh': 'lehigh university',
        'santa clara': 'santa clara university',
        'st. mary\'s': 'saint mary\'s college',
        'saint mary\'s': 'saint mary\'s college',
        'loyola marymount': 'loyola marymount university',
        'san diego state': 'san diego state university',
        'fresno state': 'california state university fresno',
        'georgia tech': 'georgia institute of technology',
        'clemson': 'clemson university',
        'south carolina': 'university of south carolina',
        'nc state': 'north carolina state university',
        'penn state': 'pennsylvania state university',
        'penn': 'university of pennsylvania',
        'pittsburgh': 'university of pittsburgh',
        'cincinnati': 'university of cincinnati',
        'west virginia': 'west virginia university',
        'louisiana': 'university of louisiana',
        'mississippi': 'university of mississippi',
        'ole miss': 'university of mississippi',
        'mississippi state': 'mississippi state university',
        'toledo': 'university of toledo',
        'dayton': 'university of dayton',
        'temple': 'temple university',
        'st. john\'s': 'st. john\'s university',
        'seton hall': 'seton hall university',
        'providence': 'providence college',
        'depaul': 'depaul university',
        'rhode island': 'university of rhode island',
        'richmond': 'university of richmond',
        'saint joseph\'s': 'saint joseph\'s university',
        'st. joseph\'s': 'saint joseph\'s university',
        'la salle': 'la salle university',
        'fordham': 'fordham university',
        'george mason': 'george mason university',
        'george washington': 'george washington university',
        'massachusetts': 'university of massachusetts',
        'umass': 'university of massachusetts',
        'houston': 'university of houston',
        'wichita state': 'wichita state university',
        'new mexico': 'university of new mexico',
        'san diego': 'university of san diego',
        'saint mary\'s college of california': 'saint mary\'s college',
        'byu': 'brigham young university',
        'brigham young': 'brigham young university',
        'maryland': 'university of maryland',
        'rutgers': 'rutgers university',
        'nebraska': 'university of nebraska',
        'minnesota': 'university of minnesota',
        'northwestern': 'northwestern university',
    }
    
    # Check if it's a known common name/abbreviation
    if school_lower in common_colleges:
        return True
    
    # Partial match with colleges in database (for longer names)
    if len(school_lower) > 6:  # Only do partial matching for longer strings
        for college in US_COLLEGES:
            # More restrictive partial matching
            if school_lower in college or college in school_lower:
                # Additional check: ensure it's a meaningful match
                shorter = min(len(school_lower), len(college))
                longer = max(len(school_lower), len(college))
                # At least 60% overlap in length
                if shorter / longer >= 0.6:
                    return True
    
    return False

def fetch_current_nba_players(min_games=10):
    """
    Fetch active NBA players from the current season with their teams
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nba.com/',
        'Origin': 'https://www.nba.com'
    }
    
    print("Fetching 2025-26 NBA season data...")
    print("=" * 60)
    
    # Step 1: Get all players with their stats for current season
    stats_url = "https://stats.nba.com/stats/leagueLeaders"
    params = {
        'LeagueID': '00',
        'PerMode': 'Totals',
        'Scope': 'S',
        'Season': '2025-26',
        'SeasonType': 'Regular Season',
        'StatCategory': 'PTS'
    }
    
    try:
        print("\n1. Fetching player statistics...")
        response = requests.get(stats_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        stats_data = response.json()
        
        if 'resultSet' not in stats_data or not stats_data['resultSet']['rowSet']:
            print("❌ No player data found in API response")
            return []
        
        headers_list = stats_data['resultSet']['headers']
        
        # Find column indices
        player_idx = headers_list.index('PLAYER')
        player_id_idx = headers_list.index('PLAYER_ID')
        team_idx = headers_list.index('TEAM')
        gp_idx = headers_list.index('GP')  # Games Played
        min_idx = headers_list.index('MIN')  # Total Minutes
        
        print(f"✓ Found {len(stats_data['resultSet']['rowSet'])} total players")
        
        # Filter players with minimum games and calculate MPG
        eligible_players = []
        for row in stats_data['resultSet']['rowSet']:
            games_played = row[gp_idx]
            total_minutes = row[min_idx] if row[min_idx] else 0
            mpg = total_minutes / games_played if games_played > 0 else 0
            
            if games_played >= min_games:
                eligible_players.append({
                    'name': row[player_idx],
                    'player_id': row[player_id_idx],
                    'team': row[team_idx],
                    'games_played': games_played,
                    'mpg': round(mpg, 1)
                })
        
        print(f"✓ Found {len(eligible_players)} players with {min_games}+ games\n")
        
        # Step 2: Get college/country info for each player
        print("2. Fetching player background info...")
        players_data = []
        seen_players = set()  # Track players we've already added
        
        for i, player in enumerate(eligible_players, 1):
            # Skip if we've already processed this player
            if player['name'] in seen_players:
                print(f"   [{i}/{len(eligible_players)}] {player['name']}... ⊘ Duplicate, skipping")
                continue
            
            print(f"   [{i}/{len(eligible_players)}] {player['name']}...", end=' ')
            
            player_info = get_player_background(player['player_id'], headers)
            
            if player_info:
                # Get NBA conference
                nba_conference = NBA_CONFERENCES.get(player['team'], 'Unknown')
                
                # Determine difficulty tier
                difficulty = determine_difficulty_tier(player['name'], player['mpg'])
                
                players_data.append({
                    'name': player['name'],
                    'team': player['team'],
                    'nba_conference': nba_conference,
                    'origin': player_info['origin'],
                    'type': player_info['type'],
                    'college_conference': player_info.get('college_conference'),
                    'alternate_answer': player_info.get('alternate_answer'),
                    'games_played': player['games_played'],
                    'mpg': player['mpg'],
                    'difficulty': difficulty
                })
                seen_players.add(player['name'])  # Mark as seen
                
                # Show conference info in output
                conf_info = f" | NBA: {nba_conference}"
                if player_info.get('college_conference'):
                    conf_info += f" | College: {player_info['college_conference']}"
                conf_info += f" | {player['mpg']} MPG | {difficulty.upper()}"
                print(f"✓ {player_info['origin']} ({player_info['type']}){conf_info}")
            else:
                print("✗ No background info")
            
            # Be respectful to the API - increased delay to avoid rate limiting
            time.sleep(1.2)  # Increased from 0.6 to 1.2 seconds
        
        print(f"\n{'=' * 60}")
        print(f"✓ Successfully fetched {len(players_data)} players")
        
        return players_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        print("\nTroubleshooting:")
        print("- Check your internet connection")
        print("- The NBA API may be temporarily down")
        print("- Try running the script again in a few minutes")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

def get_player_background(player_id, headers):
    """
    Get player's college or country of origin
    """
    info_url = "https://stats.nba.com/stats/commonplayerinfo"
    params = {
        'PlayerID': player_id
    }
    
    # Retry logic for rate limiting
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(info_url, headers=headers, params=params, timeout=15)
            
            # Handle rate limiting
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                    print(f"⚠ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print("✗ Rate limited (max retries)")
                    return None
            
            response.raise_for_status()
            data = response.json()
            
            if 'resultSets' not in data or len(data['resultSets']) == 0:
                return None
            
            result_headers = data['resultSets'][0]['headers']
            row = data['resultSets'][0]['rowSet'][0]
            
            # Get indices
            country_idx = result_headers.index('COUNTRY') if 'COUNTRY' in result_headers else None
            school_idx = result_headers.index('SCHOOL') if 'SCHOOL' in result_headers else None
            
            country = row[country_idx].strip() if country_idx is not None and row[country_idx] else ''
            school = row[school_idx].strip() if school_idx is not None and row[school_idx] else ''
            
            # Special handling for G League Ignite and Overtime Elite
            special_programs = ['g league ignite', 'ignite', 'overtime elite']
            is_special_program = any(prog in school.lower() for prog in special_programs) if school else False
            
            # Determine origin and type using college database
            # PRIORITY:
            # 1. If attended US college → use college (even if international player)
            # 2. If special program (G League/OTE) + international → use program, store country as alternate
            # 3. If international (no US college) → use country
            # 4. If US with no college → use "United States"
            
            college_info = get_college_info(school) if school and school not in ['None', '', 'No College'] else {'is_college': False, 'conference': None}
            
            if college_info['is_college']:
                # Attended US college - use college (regardless of nationality)
                return {
                    'origin': school,
                    'type': 'College',
                    'college_conference': college_info['conference'],
                    'alternate_answer': None
                }
            elif is_special_program and country and country != 'USA':
                # Special case: G League Ignite or Overtime Elite + International player
                # Use the program as origin but store country as alternate
                return {
                    'origin': school,
                    'type': 'Other',
                    'college_conference': 'Other',
                    'alternate_answer': country
                }
            elif country and country != 'USA':
                # International player who didn't attend US college
                return {
                    'origin': country,
                    'type': 'Country',
                    'college_conference': 'Other',
                    'alternate_answer': None
                }
            elif school and school not in ['None', '', 'No College']:
                # Has a school listed but not a US college
                # Likely a foreign team/league, use country if available
                if country and country != 'USA':
                    return {
                        'origin': country,
                        'type': 'Country',
                        'college_conference': 'Other',
                        'alternate_answer': None
                    }
                else:
                    # Edge case: might be prep school, G League, etc.
                    return {
                        'origin': school,
                        'type': 'Other',
                        'college_conference': 'Other',
                        'alternate_answer': None
                    }
            else:
                # US player without college
                return {
                    'origin': 'United States',
                    'type': 'Country',
                    'college_conference': 'Other',
                    'alternate_answer': None
                }
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
        except Exception as e:
            return None
    
    return None

def save_to_json(players, filename='nba_players_full.json'):
    """
    Save players to JSON file
    """
    output = {
        'generated_at': datetime.now().isoformat(),
        'season': '2025-26',
        'total_players': len(players),
        'players': players
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved to {filename}")
    
    # Print statistics
    colleges = sum(1 for p in players if p['type'] == 'College')
    countries = sum(1 for p in players if p['type'] == 'Country')
    other = sum(1 for p in players if p['type'] == 'Other')
    
    print(f"\nStatistics:")
    print(f"  College players: {colleges}")
    print(f"  International players: {countries}")
    print(f"  Other: {other}")
    print(f"  Total: {len(players)}")
    
    # Show team breakdown
    teams = {}
    for p in players:
        teams[p['team']] = teams.get(p['team'], 0) + 1
    
    print(f"\nTeams represented: {len(teams)}")

def create_app_compatible_json(players, filename='nba_players.json'):
    """
    Create a simpler JSON format for direct use in the app
    (just the player array without metadata)
    """
    simple_players = [
        {
            'name': p['name'],
            'team': p['team'],
            'nba_conference': p['nba_conference'],
            'origin': p['origin'],
            'type': p['type'],
            'college_conference': p.get('college_conference'),
            'alternate_answer': p.get('alternate_answer'),
            'mpg': p.get('mpg', 0),
            'difficulty': p.get('difficulty', 'hard')
        }
        for p in players
    ]
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(simple_players, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Also saved app-compatible version to {filename}")

if __name__ == "__main__":
    print("NBA Player Data Fetcher - 2025-26 Season")
    print("=" * 60)
    print()
    
    # Load US college database from file (now with conference data)
    US_COLLEGES = load_us_colleges_from_file('us_colleges.json')
    
    # Load NBA conference mapping
    NBA_CONFERENCES = load_nba_conferences('nba_conferences.json')
    print(f"✓ Loaded NBA conference mappings\n")
    
    # Fetch players with 10+ games
    players = fetch_current_nba_players(min_games=10)
    
    if players:
        # Save both formats
        save_to_json(players, 'nba_players_full.json')
        create_app_compatible_json(players, 'nba_players.json')
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS! Data ready to use.")
        print("\nNext steps:")
        print("1. Copy 'nba_players.json' to your app directory")
        print("2. Run 'fly deploy' to update your game")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Failed to fetch player data")
        print("\nThis could be because:")
        print("1. The NBA API is blocking automated requests")
        print("2. The 2025-26 season hasn't started yet")
        print("3. Network connectivity issues")
        print("\nTry running this script from your local machine with internet access.")
        print("=" * 60)
