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
# 4. FUNGSI BARU: ADVANCED METRICS (SEASON + L45 DAYS HYBRID ENGINE)
# ==========================================
def update_advanced_metrics(games_list):
    print("⚙️ Menggali Data Pitcher: Full Season Baseline & Last 45 Days Current Form...")
    team_totals = {}
    pitchers_data = {}

    def get_pitcher_hybrid_metrics(pitcher_name):
        default_season = {"ERA": 4.15, "HR/9": 1.0, "FB%": 30.0, "Status": "Average"}
        default_l45 = {"ERA": 4.15, "HR/9": 1.0, "Starts": 0}
        
        if pitcher_name == "TBD" or not pitcher_name: 
            return default_season, default_l45
        
        try:
            players = statsapi.lookup_player(pitcher_name)
            if not players: return default_season, default_l45
            p_id = players[0]['id']
            
            # --- 1. AMBIL DATA FULL SEASON ---
            season_data = statsapi.player_stat_data(p_id, group="pitching", type="season")
            season_stats = default_season.copy()
            
            if season_data and 'stats' in season_data and len(season_data['stats']) > 0:
                p_stats = season_data['stats'][0].get('stats', {})
                era_str = p_stats.get('era', '4.15')
                era = float(era_str) if era_str != '-.--' else 4.15
                
                hr_allowed = int(p_stats.get('homeRuns', 0))
                ip_str = str(p_stats.get('inningsPitched', '0.0'))
                ip_parts = ip_str.split('.')
                ip = float(ip_parts[0]) + (float(ip_parts[1])/3.0 if len(ip_parts) > 1 else 0)
                hr9 = (hr_allowed / ip) * 9 if ip > 0 else 1.0
                
                air_outs = int(p_stats.get('airOuts', 0))
                ground_outs = int(p_stats.get('groundOuts', 0))
                total_outs = air_outs + ground_outs
                fb_pct = (air_outs / total_outs) * 100 if total_outs > 0 else 30.0
                
                season_stats = {
                    "ERA": round(era, 2),
                    "HR/9": round(hr9, 2),
                    "FB%": round(fb_pct, 1),
                    "Status": "Elite" if era < 3.5 else ("Vulnerable" if era > 4.5 else "Average")
                }

            # --- 2. AMBIL DAN FILTER LAST 45 DAYS (KALENDER) ---
            l45_stats = default_l45.copy()
            log_data = statsapi.player_stat_data(p_id, group="pitching", type="gameLog")
            
            if log_data and 'stats' in log_data and len(log_data['stats']) > 0:
                games_log = log_data['stats']
                
                # SUNTIKAN SAKTI: Set batas waktu 45 hari ke belakang dari hari ini
                batas_45_hari = datetime.now() - timedelta(days=45)
                recent_games = []
                
                for game in games_log:
                    g_date_str = game.get('date', today_str) # Format API: 'YYYY-MM-DD'
                    try:
                        g_date = datetime.strptime(g_date_str, '%Y-%m-%d')
                        # Masukkan ke list hanya jika pertandingan masuk dalam jendela 45 hari
                        if g_date >= batas_45_hari:
                            recent_games.append(game)
                    except:
                        pass
                
                total_er = 0
                total_hr = 0
                total_ip = 0.0
                
                # Jika ada pertandingan dalam 45 hari terakhir
                if recent_games:
                    for game in recent_games:
                        g_stats = game.get('stats', {})
                        total_er += int(g_stats.get('earnedRuns', 0))
                        total_hr += int(g_stats.get('homeRuns', 0))
                        
                        ip_str = str(g_stats.get('inningsPitched', '0.0'))
                        ip_parts = ip_str.split('.')
                        g_ip = float(ip_parts[0]) + (float(ip_parts[1])/3.0 if len(ip_parts) > 1 else 0)
                        total_ip += g_ip
                    
                    l45_era = (total_er / total_ip) * 9 if total_ip > 0 else season_stats["ERA"]
                    l45_hr9 = (total_hr / total_ip) * 9 if total_ip > 0 else season_stats["HR/9"]
                    
                    l45_stats = {
                        "ERA": round(l45_era, 2),
                        "HR/9": round(l45_hr9, 2),
                        "Starts": len(recent_games) # Menyimpan total match di l45 days
                    }
                else:
                    # Fallback kalau ga main sama sekali 45 hari ini, pake data season
                    l45_stats = {"ERA": season_stats["ERA"], "HR/9": season_stats["HR/9"], "Starts": 0}
            else:
                l45_stats = {"ERA": season_stats["ERA"], "HR/9": season_stats["HR/9"], "Starts": 0}

            return season_stats, l45_stats
            
        except Exception as e:
            return default_season, default_l45

    for g in games_list:
        away_p = g['away_pitcher']
        home_p = g['home_pitcher']
        away_team = g['away_team']
        home_team = g['home_team']

        away_season, away_l45 = get_pitcher_hybrid_metrics(away_p)
        home_season, home_l45 = get_pitcher_hybrid_metrics(home_p)

        # Simpan dengan anak kunci baru: .season dan .l45
        pitchers_data[away_p] = {"season": away_season, "l45": away_l45}
        pitchers_data[home_p] = {"season": home_season, "l45": home_l45}

        team_totals[away_team] = home_season["ERA"]
        team_totals[home_team] = away_season["ERA"]

    with open('team_totals.json', 'w') as f:
        json.dump(team_totals, f, indent=4)
    with open('l30_pitchers.json', 'w') as f:
        json.dump(pitchers_data, f, indent=4)
    print("✅ Sukses: 'l30_pitchers.json' berhasil dimigrasi ke Last 45 Days Engine!")

# ==========================================
# 5. FUNGSI BARU: AUTO-GENERATE HITTER CSV (BYPASS FANGRAPHS)
# ==========================================
def generate_master_hitter_csv():
    print("🏏 Menyedot Data Hitter (Raw Savant) + Mapping Tim statsapi...")
    try:
        import pandas as pd
        import requests
        import io
        import statsapi

        # 1. BIKIN KAMUS TIM DARI MLB STATS-API
        print("⏳ Membangun Kamus Roster dari 30 Tim MLB...")
        team_abbr_map = {
            133: "OAK", 134: "PIT", 135: "SD", 136: "SEA", 137: "SF",
            138: "STL", 139: "TB", 140: "TEX", 141: "TOR", 142: "MIN",
            143: "PHI", 144: "ATL", 145: "CWS", 146: "MIA", 147: "NYY",
            158: "MIL", 108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS",
            112: "CHC", 113: "CIN", 114: "CLE", 115: "COL", 116: "DET",
            117: "HOU", 118: "KC", 119: "LAD", 120: "WSH", 121: "NYM"
        }
        player_to_team = {}
        for team_id, team_abbr in team_abbr_map.items():
            try:
                roster = statsapi.get('team_roster', {'teamId': team_id})
                for p in roster['roster']:
                    name = p['person']['fullName']
                    player_to_team[name] = team_abbr
            except:
                continue

        # 2. SEDOT DATA SAVANT DARI LINK LU
        # Note: min=q diganti min=10 agar aman, ditambah &csv=true di belakang
        savant_url = "https://baseballsavant.mlb.com/leaderboard/custom?year=2026&type=batter&filter=&min=10&selections=player_age%2Cpa%2Chome_run%2Ck_percent%2Cbb_percent%2Cbatting_avg%2Cb_rbi%2Cb_total_bases%2Cxba%2Cxslg%2Cwoba%2Cxwoba%2Cwobadiff%2Cblasts_contact%2Cideal_angle_rate%2Cexit_velocity_avg%2Claunch_angle_avg%2Csweet_spot_percent%2Cbarrel%2Cbarrel_batted_rate%2Csolidcontact_percent%2Cpoorlyweak_percent%2Chard_hit_percent%2Cavg_best_speed%2Cavg_hyper_speed%2Cz_swing_percent%2Coz_swing_percent%2Cout_zone_swing%2Cout_zone_percent%2Ciz_contact_percent%2Cin_zone_percent%2Cwhiff_percent%2Cswing_percent%2Cpull_percent%2Cflyballs_percent&chart=false&x=player_age&y=player_age&r=no&chartType=beeswarm&sort=avg_best_speed&sortDir=desc&csv=true"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        print("⏳ Mengunduh File CSV dari Baseball Savant...")
        response = requests.get(savant_url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(response.text))

        # 3. BALIK NAMA & TEMPEL TIM
        # Membalik format "Ohtani, Shohei" jadi "Shohei Ohtani"
        if 'player' in df.columns:
            df['player'] = df['player'].apply(lambda x: ' '.join(x.split(', ')[::-1]) if isinstance(x, str) and ', ' in x else x)
        
        # Mapping nama ke tim, kalau nggak ketemu kasih 'TBD'
        df['Team'] = df['player'].map(player_to_team).fillna('TBD')

        # Dummy untuk Tab Lainnya agar nggak crash
        df['Name'] = df['player'] # Bikin duplikat kolom buat jaga-jaga kalau app.py masih nyari 'Name'
        df['xwOBA_vs_R'] = df['xwoba']
        df['xwOBA_vs_L'] = df['xwoba']
        df['xwOBA_L14'] = df['xwoba']
        df['PA_L14'] = df['pa']
        df['Batting'] = 0

        # Simpan perawan tanpa rename kolom aslinya
        df.to_csv('master_hitter_2026.csv', index=False)
        print("✅ BOOM! master_hitter_2026.csv sukses digenerate secara murni & ter-mapping!")
        
    except Exception as e:
        print(f"❌ Gagal nyedot Savant: {e}")

# ==========================================
# 5. INIT DAILY PICKS LOG
# ==========================================
def init_daily_picks_log():
    if not os.path.exists('daily_picks_log.json'):
        with open('daily_picks_log.json', 'w') as f:
            json.dump({"date": today_str, "sgp_match": {}, "sgp_cross": {}}, f)
        print("✅ Sukses: Inisialisasi 'daily_picks_log.json'")
# ===============================
# 5B. Update CSV Master Pitcher 
# ===============================
def generate_master_pitcher_csv(games_list):
    print("📊 Mengekstrak Advanced Metrics & Membuat master_pitcher_2026.csv...")
    pitcher_rows = []

    def get_full_advanced_stats(pitcher_name, team_name):
        if pitcher_name == "TBD" or not pitcher_name: return None
        try:
            players = statsapi.lookup_player(pitcher_name)
            if not players: return None
            
            p_id = players[0]['id']
            season_data = statsapi.player_stat_data(p_id, group="pitching", type="season")

            if season_data and 'stats' in season_data and len(season_data['stats']) > 0:
                p = season_data['stats'][0].get('stats', {})

                # Parsing Innings Pitched dengan akurat (contoh: 4.1 jadi 4.333)
                ip_str = str(p.get('inningsPitched', '0.0'))
                ip_parts = ip_str.split('.')
                ip = float(ip_parts[0]) + (float(ip_parts[1])/3.0 if len(ip_parts) > 1 else 0)

                if ip == 0: return None # Hindari pembagian dengan nol

                so = int(p.get('strikeOuts', 0))
                bb = int(p.get('baseOnBalls', 0))
                hits = int(p.get('hits', 0))
                hr = int(p.get('homeRuns', 0))
                air_outs = int(p.get('airOuts', 0))
                ground_outs = int(p.get('groundOuts', 0))

                return {
                    'Name': pitcher_name,
                    'Team': team_name,
                    'GS': p.get('gamesStarted', 0), # Tambahin baris ini
                    'W': p.get('wins', 0),
                    'L': p.get('losses', 0),
                    'ERA': float(p.get('era', '4.15') if p.get('era') != '-.--' else 4.15),
                    'IP': round(ip, 1),
                    'K/9': round((so / ip) * 9, 2),
                    'BB/9': round((bb / ip) * 9, 2),
                    'H/9': round((hits / ip) * 9, 2),
                    'HR/9': round((hr / ip) * 9, 2),
                    'WHIP': float(p.get('whip', '1.30') if p.get('whip') != '-.--' else 1.30),
                    'Opp_BA': float(p.get('avg', '.250') if p.get('avg') != '.---' else 0.250),
                    'FB%': round((air_outs / (air_outs + ground_outs) * 100) if (air_outs + ground_outs) > 0 else 30.0, 1)
                }
        except Exception as e:
            print(f"⚠️ Error menarik metrik CSV untuk {pitcher_name}: {e}")
            return None

    # Looping semua SP di jadwal hari ini
    for g in games_list:
        away_p = get_full_advanced_stats(g['away_pitcher'], g['away_team'])
        home_p = get_full_advanced_stats(g['home_pitcher'], g['home_team'])

        if away_p: pitcher_rows.append(away_p)
        if home_p: pitcher_rows.append(home_p)

    # Simpan/Timpa langsung jadi CSV
    if pitcher_rows:
        df = pd.DataFrame(pitcher_rows)
        df.to_csv('master_pitcher_2026.csv', index=False)
        print("✅ BOOM! master_pitcher_2026.csv berhasil di-update secara otomatis!")

# ==========================================
# 6. EKSEKUSI UTAMA (MAIN RUNNER)
# ==========================================
if __name__ == "__main__":
    fetch_yesterday_results(yest_str)
    games = fetch_today_schedule(today_str)
    if games:
        update_advanced_metrics(games)
        generate_master_pitcher_csv(games)
        generate_master_hitter_csv()
    init_daily_picks_log()
    print("🎯 Bot Updater Selesai Dieksekusi. Semua data riil siap di-deploy!")
