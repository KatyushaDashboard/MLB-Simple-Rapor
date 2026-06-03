import statsapi
import pandas as pd
from datetime import datetime, timedelta
import json
import requests
import os

# ==========================================
# 1. SETUP TANGGAL (WAKTU SERVER / UTC)
# ==========================================
now = datetime.now()
today_str = now.strftime('%Y-%m-%d')
yesterday = now - timedelta(days=1)
yest_str = yesterday.strftime('%Y-%m-%d')

print(f"🚀 Memulai Bot Updater - Tanggal: {today_str}")

# ==========================================
# 2. FUNGSI: THE AUDITOR (TARIK HASIL KEMARIN)
# ==========================================
def fetch_yesterday_results(date_str):
    print(f"🔍 Menarik data hasil pertandingan kemarin: {date_str}...")
    url_schedule = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
    
    try:
        resp = requests.get(url_schedule)
        data = resp.json()
        
        results_log = {}
        if data.get('totalGames', 0) > 0:
            games = data['dates'][0]['games']
            for g in games:
                if g['status']['statusCode'] in ['F', 'O', 'C']:
                    game_pk = g['gamePk']
                    away_team = g['teams']['away']['team']['name']
                    home_team = g['teams']['home']['team']['name']
                    
                    box_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
                    box_data = requests.get(box_url).json()
                    
                    results_log[game_pk] = {
                        'matchup': f"{away_team} @ {home_team}",
                        'away_runs': g['teams']['away'].get('score', 0),
                        'home_runs': g['teams']['home'].get('score', 0),
                        'players': {}
                    }
                    
                    for team_side in ['away', 'home']:
                        players = box_data['teams'][team_side]['players']
                        for p_id, p_stats in players.items():
                            name = p_stats['person']['fullName']
                            stats = p_stats.get('stats', {})
                            
                            if 'batting' in stats:
                                b = stats['batting']
                                tb = b.get('hits', 0) + b.get('doubles', 0) + (b.get('triples', 0)*2) + (b.get('homeRuns', 0)*3)
                                results_log[game_pk]['players'][name] = {
                                    'hits': b.get('hits', 0),
                                    'hr': b.get('homeRuns', 0),
                                    'tb': tb,
                                    'rbi': b.get('rbi', 0),
                                    'strikeouts_batter': b.get('strikeOuts', 0)
                                }
                            elif 'pitching' in stats:
                                p = stats['pitching']
                                results_log[game_pk]['players'][name] = {
                                    'strikeouts_pitcher': p.get('strikeOuts', 0),
                                    'hits_allowed': p.get('hits', 0)
                                }
                                
            with open('yesterday_results.json', 'w') as f:
                json.dump(results_log, f, indent=4)
            print("✅ Sukses: Data hasil kemarin disimpan ke 'yesterday_results.json'")
        else:
            print("ℹ️ Tidak ada pertandingan kemarin.")
            with open('yesterday_results.json', 'w') as f:
                json.dump({}, f)
                
    except Exception as e:
        print(f"❌ Gagal menarik hasil kemarin: {e}")

# ==========================================
# 3. FUNGSI: SCHEDULE & PROBABLE PITCHERS
# ==========================================
def fetch_today_schedule(date_str):
    print(f"📅 Menarik jadwal pertandingan hari ini: {date_str}...")
    try:
        sched = statsapi.schedule(date=date_str)
        games_list = []
        
        for g in sched:
            games_list.append({
                'game_id': g['game_id'],
                'away_team': g['away_name'],
                'home_team': g['home_name'],
                'away_pitcher': g.get('away_probable_pitcher', 'TBD'),
                'home_pitcher': g.get('home_probable_pitcher', 'TBD'),
                'status': g['status']
            })
            
        with open('today_schedule.json', 'w') as f:
            json.dump(games_list, f, indent=4)
        print("✅ Sukses: Jadwal hari ini disimpan ke 'today_schedule.json'")
        return games_list
        
    except Exception as e:
        print(f"❌ Gagal menarik jadwal hari ini: {e}")
        return []

# ==========================================
# 4. FUNGSI BARU: ADVANCED METRICS (REAL DATA)
# ==========================================
def update_advanced_metrics(games_list):
    print("⚙️ Mengekstrak Data Pitcher ERA & Proyeksi Team Total (Real API)...")
    team_totals = {}
    pitchers_data = {}

    def get_real_era(pitcher_name):
        if pitcher_name == "TBD" or not pitcher_name: return 4.00
        try:
            players = statsapi.lookup_player(pitcher_name)
            if players:
                p_id = players[0]['id']
                stats = statsapi.player_stat_data(p_id, group="pitching", type="season")
                era_str = stats.get('stats', [{}])[0].get('stats', {}).get('era', '4.00')
                if era_str == '-.--': return 4.00
                return float(era_str)
        except:
            pass
        return 4.00 # Default kalau API gagal narik nama

    for g in games_list:
        away_p = g['away_pitcher']
        home_p = g['home_pitcher']
        away_team = g['away_team']
        home_team = g['home_team']

        # Tarik ERA aktual
        away_era = get_real_era(away_p)
        home_era = get_real_era(home_p)

        pitchers_data[away_p] = {"ERA": away_era, "Status": "Elite" if away_era < 3.5 else ("Vulnerable" if away_era > 4.5 else "Average")}
        pitchers_data[home_p] = {"ERA": home_era, "Status": "Elite" if home_era < 3.5 else ("Vulnerable" if home_era > 4.5 else "Average")}

        # Proyeksi Team Totals berdasarkan ERA Pitcher lawan
        team_totals[away_team] = home_era
        team_totals[home_team] = away_era

    with open('team_totals.json', 'w') as f:
        json.dump(team_totals, f, indent=4)
    with open('l30_pitchers.json', 'w') as f:
        json.dump(pitchers_data, f, indent=4)
    print("✅ Sukses: File Advanced Metrics riil berhasil di-generate!")

# ==========================================
# 5. INIT DAILY PICKS LOG
# ==========================================
def init_daily_picks_log():
    if not os.path.exists('daily_picks_log.json'):
        with open('daily_picks_log.json', 'w') as f:
            json.dump({"date": today_str, "sgp_match": {}, "sgp_cross": {}}, f)
        print("✅ Sukses: Inisialisasi 'daily_picks_log.json'")

# ==========================================
# 6. EKSEKUSI UTAMA (MAIN RUNNER)
# ==========================================
if __name__ == "__main__":
    fetch_yesterday_results(yest_str)
    games = fetch_today_schedule(today_str)
    if games:
        update_advanced_metrics(games)
    init_daily_picks_log()
    print("🎯 Bot Updater Selesai Dieksekusi. Semua data riil siap di-deploy!")
