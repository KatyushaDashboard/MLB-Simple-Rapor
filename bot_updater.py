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
                # Hanya ambil laga yang sudah berstatus Final (Selesai)
                if g['status']['statusCode'] in ['F', 'O', 'C']:
                    game_pk = g['gamePk']
                    away_team = g['teams']['away']['team']['name']
                    home_team = g['teams']['home']['team']['name']
                    
                    # Tarik Boxscore Laga Ini
                    box_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
                    box_data = requests.get(box_url).json()
                    
                    results_log[game_pk] = {
                        'matchup': f"{away_team} @ {home_team}",
                        'away_runs': g['teams']['away'].get('score', 0),
                        'home_runs': g['teams']['home'].get('score', 0),
                        'players': {}
                    }
                    
                    # Ekstrak metrik individu (Batter & Pitcher)
                    for team_side in ['away', 'home']:
                        players = box_data['teams'][team_side]['players']
                        for p_id, p_stats in players.items():
                            name = p_stats['person']['fullName']
                            stats = p_stats.get('stats', {})
                            
                            # Logika Pemukul (Batter)
                            if 'batting' in stats:
                                b = stats['batting']
                                tb = b.get('hits', 0) + b.get('doubles', 0) + (b.get('triples', 0)*2) + (b.get('homeRuns', 0)*3)
                                results_log[game_pk]['players'][name] = {
                                    'hits': b.get('hits', 0),
                                    'doubles': b.get('doubles', 0),
                                    'triples': b.get('triples', 0),
                                    'hr': b.get('homeRuns', 0),
                                    'tb': tb,
                                    'rbi': b.get('rbi', 0),
                                    'runs': b.get('runs', 0),
                                    'strikeouts_batter': b.get('strikeOuts', 0)
                                }
                            # Logika Pelempar (Pitcher)
                            elif 'pitching' in stats:
                                p = stats['pitching']
                                results_log[game_pk]['players'][name] = {
                                    'strikeouts_pitcher': p.get('strikeOuts', 0),
                                    'outs': p.get('outs', 0),
                                    'hits_allowed': p.get('hits', 0),
                                    'earned_runs': p.get('earnedRuns', 0)
                                }
                                
            # Simpan ke JSON untuk dibaca Tab 6
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
# 3. FUNGSI: SCHEDULE & PROBABLE PITCHERS HARI INI
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
        
    except Exception as e:
        print(f"❌ Gagal menarik jadwal hari ini: {e}")

# ==========================================
# 4. INIT DAILY PICKS LOG (Wadah kosong untuk Tab 4 & 9)
# ==========================================
def init_daily_picks_log():
    # Membuat file log kosong jika belum ada, biar Streamlit nggak error saat mau nulis
    if not os.path.exists('daily_picks_log.json'):
        with open('daily_picks_log.json', 'w') as f:
            json.dump({"date": today_str, "sgp_match": {}, "sgp_cross": {}}, f)
        print("✅ Sukses: Inisialisasi 'daily_picks_log.json'")

# ==========================================
# 5. EKSEKUSI UTAMA (MAIN RUNNER)
# ==========================================
if __name__ == "__main__":
    fetch_yesterday_results(yest_str)
    fetch_today_schedule(today_str)
    init_daily_picks_log()
    print("🎯 Bot Updater Selesai Dieksekusi. Semua data siap digunakan oleh Streamlit!")
