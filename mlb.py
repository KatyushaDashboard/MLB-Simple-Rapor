import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import itertools # <-- MODULE BARU UNTUK MATCHMAKER ULXRARE

# ====================================================================
# 1. INITIAL SETUP & CONFIG 
# ====================================================================
st.set_page_config(page_title="MLB Ultimate Command Center v2", layout="wide")
st.title("🏆 MLB ULTIMATE COMMAND CENTER v2")
st.caption("Terminal Eksekusi & Audit Taruhan Otomatis Berbasis Konsensus Statcast AI")

st.sidebar.header("⚙️ Kontrol Waktu")
selected_date = st.sidebar.date_input("Pilih Tanggal Pertandingan:", datetime.today())

# ====================================================================
# 2. LOAD DATA CORE & JSON BOT
# ====================================================================
@st.cache_data
def load_base_data():
# ==========================================
# LOAD DATA HITTER
# ==========================================
    try:
        df_hitters = pd.read_csv('master_hitter_2026.csv')
    
    # --- MULAI BAGIAN 1 (PENGAMAN & CUCI KOLOM) ---
        if not df_hitters.empty:
            if 'player' in df_hitters.columns and 'Name' not in df_hitters.columns:
                df_hitters['Name'] = df_hitters['player']
            if 'player_age' in df_hitters.columns and 'Age' not in df_hitters.columns:
                df_hitters['Age'] = df_hitters['player_age']
            
            rename_global = {
                'xwoba': 'xwOBA',
                'xba': 'xBA',
                'xslg': 'xSLG',
                'k_percent': 'K%',
                'bb_percent': 'BB%',
                'barrel_batted_rate': 'Barrel%',
                'avg_best_speed': 'Max EV',
                'hard_hit_percent': 'HardHit%',
                'sweet_spot_percent': 'SweetSpot%',
                'flyballs_percent': 'FB%',
                'oz_swing_percent': 'Chase%',
                'whiff_percent': 'Whiff%',
                'iz_contact_percent': 'ZoneContact%',
                'pull_percent': 'Pull%'
                }
            df_hitters.rename(columns=rename_global, inplace=True)
    # --- AKHIR BAGIAN 1 ---

    except FileNotFoundError: # <--- INI DIA YANG TADI KEHAPUS/KEGESER WAK!
        df_hitters = pd.DataFrame()

    try:
        df_pitchers = pd.read_csv('master_pitcher_2026.csv')
    except FileNotFoundError:
        st.sidebar.error("⚠️ File 'master_pitcher_2026.csv' tidak ditemukan.")
        df_pitchers = pd.DataFrame()

    return df_hitters, df_pitchers

df_hitters, df_pitchers = load_base_data()

def get_pitcher_era(team_name):
    if not df_pitchers.empty and 'Team' in df_pitchers.columns and 'ERA' in df_pitchers.columns:
        team_p = df_pitchers[df_pitchers['Team'] == team_name]
        if not team_p.empty:
            return team_p['ERA'].mean()
    return 4.15 

def load_json_data(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {} if 'results' in filename or 'totals' in filename or 'pitchers' in filename else []
    return {} if 'results' in filename or 'totals' in filename or 'pitchers' in filename else []

today_schedule = load_json_data('today_schedule.json')
yesterday_results = load_json_data('yesterday_results.json')
team_totals_data = load_json_data('team_totals.json') # <-- DATA BARU
l30_pitchers_data = load_json_data('l30_pitchers.json') # <-- DATA BARU

TEAM_MAPPING = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

if isinstance(today_schedule, list):
    for game in today_schedule:
        game['away_team'] = TEAM_MAPPING.get(game['away_team'], game['away_team'])
        game['home_team'] = TEAM_MAPPING.get(game['home_team'], game['home_team'])
        if 'away' in game: game['away'] = TEAM_MAPPING.get(game['away'], game['away'])
        if 'home' in game: game['home'] = TEAM_MAPPING.get(game['home'], game['home'])

PARK_FACTORS = {
    "COL": 1.35, "CIN": 1.15, "BOS": 1.12, "BAL": 1.05, "ATL": 1.04,
    "CWS": 1.02, "LAA": 1.02, "TEX": 1.02, "PHI": 1.01, "ARI": 1.01,
    "HOU": 1.00, "TOR": 1.00, "LAD": 1.00, "NYY": 0.99, "MIN": 0.99,
    "MIL": 0.99, "CHC": 0.98, "KC": 0.98, "TB": 0.97, "PIT": 0.96,
    "WSH": 0.96, "MIA": 0.95, "STL": 0.95, "CLE": 0.94, "SF": 0.94,
    "SD": 0.93, "NYM": 0.92, "DET": 0.91, "OAK": 0.90, "SEA": 0.88
}

def load_betting_history():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'betting_history.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except: pass
    return {"total_bets": 50, "wins": 32, "losses": 18, "total_staked": 5000000, "total_returned": 6850000}

# ====================================================================
# 3. PRE-PROCESSING OTOMATIS: KALIBRASI PARK FACTOR UNTUK SEMUA TAB
# ====================================================================
playing_teams = []
team_to_park = {}
team_to_opp_pitcher = {} # <-- SUNTIKAN BARU UNTUK DETEKSI PITCHER LAWAN

if isinstance(today_schedule, list):
    for game in today_schedule:
        playing_teams.extend([game['away_team'], game['home_team']])
        team_to_park[game['away_team']] = game['home_team']
        team_to_park[game['home_team']] = game['home_team']
        # Petakan siapa SP lawan untuk masing-masing tim hari ini
        team_to_opp_pitcher[game['away_team']] = game.get('home_pitcher', 'TBD')
        team_to_opp_pitcher[game['home_team']] = game.get('away_pitcher', 'TBD')

today_hitters = df_hitters[df_hitters['Team'].isin(playing_teams)].copy() if not df_hitters.empty else pd.DataFrame()

if not today_hitters.empty and 'Barrel%' in today_hitters.columns and 'xwOBA' in today_hitters.columns:
    today_hitters['Home_Park'] = today_hitters['Team'].map(team_to_park)
    today_hitters['PF_Multiplier'] = today_hitters['Home_Park'].map(PARK_FACTORS).fillna(1.00)
    today_hitters['Adj_Barrel'] = today_hitters['Barrel%'] * today_hitters['PF_Multiplier']
    today_hitters['Adj_xwOBA'] = today_hitters['xwOBA'] * today_hitters['PF_Multiplier']

    # Deteksi TB Leader per tim untuk RBI Environment
    if 'TB' in today_hitters.columns:
        today_hitters['Is_Team_TB_Leader'] = today_hitters.groupby('Team')['TB'].transform(lambda x: x == x.max())
    else:
        today_hitters['Is_Team_TB_Leader'] = False

# ====================================================================
# 4. ENGINE BARU: THE MULTI-SCREEN SCORING MATRIX
# ====================================================================
@st.cache_data(ttl=600) 
def run_scoring_matrix(df, _l30_pitchers, _team_to_opp_pitcher):
    if df.empty: return df
    df_matrix = df.copy()

    connection_scores, archetypes = [], []

    for idx, row in df_matrix.iterrows():
        score = 0
        team = row['Team']
        adj_barrel = row.get('Adj_Barrel', row.get('Barrel%', 0))
        adj_xwoba = row.get('Adj_xwOBA', row.get('xwOBA', 0))
        max_ev = row.get('Max EV', 0)
        park_mult = row.get('PF_Multiplier', 1.0)

        # F1: Core Power (+2)
        if adj_barrel >= 7.0 and adj_xwoba >= 0.330: score += 2
        # F2: HR Dept (+1)
        if max_ev >= 106.0: score += 1
        # F3: RBI Environment (+2)
        proj_runs = team_totals_data.get(team, 4.0) if isinstance(team_totals_data, dict) else 4.0
        if row.get('Is_Team_TB_Leader', False) and proj_runs >= 4.5: score += 2
        # F4: Green Park (+1)
        if park_mult > 1.02: score += 1

        # 🔥 F5: DETEKSI PITCHER LEMAH DARI DATA BOT (+1 Poin)
        opp_pitcher_name = _team_to_opp_pitcher.get(team, 'TBD')
        if opp_pitcher_name != 'TBD' and isinstance(_l30_pitchers, dict):
            # Tarik data dari JSON l30_pitchers_data
            p_data = _l30_pitchers.get(opp_pitcher_name, {})
            opp_hr9 = p_data.get('HR/9', 0.0)
            opp_fb = p_data.get('FB%', 0.0)
            
            # Kalau Pitcher musuh hobi lepas HR (>1.3) ATAU sering lempar bola terbang (>40%)
            if opp_hr9 >= 1.3 or opp_fb >= 40.0: 
                score += 1

        # DNA Tagging (Syarat poin ditaikkan sedikit karena ada tambahan F5)
        if score >= 4 and adj_xwoba >= 0.340: tipe = "🌟 SUPERSTAR (Core)"
        elif adj_barrel >= 7.5 and adj_xwoba < 0.330: tipe = "☄️ LONGSHOT (Boom/Bust)"
        else: tipe = "🎯 SOLID BAT"

        connection_scores.append(score)
        archetypes.append(tipe)

    df_matrix['Conn_Score'] = connection_scores
    df_matrix['Archetype'] = archetypes
    return df_matrix.sort_values(by='Conn_Score', ascending=False)

# 🔥 PASTIKAN BARIS PEMANGGILAN INI JUGA BERUBAH (Berikan data l30_pitchers_data)
df_matrix_global = run_scoring_matrix(today_hitters, l30_pitchers_data, team_to_opp_pitcher)

# ====================================================================
# FUNGSI LIVE BOXSCORE (FULL CODE, TINGGAL PASTE)
# ====================================================================
@st.cache_data(ttl=60)
def get_live_boxscore(game_id, away_team, home_team):
    import pandas as pd
    if not game_id or game_id == 0:
        return pd.DataFrame(), pd.DataFrame()

    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()

        hitter_rows = []
        pitcher_rows = []

        teams_data = {
            away_team: data.get('teams', {}).get('away', {}).get('players', {}),
            home_team: data.get('teams', {}).get('home', {}).get('players', {})
        }

        for team_name, players in teams_data.items():
            for p_id, p_info in players.items():
                name = p_info['person']['fullName']
                stats = p_info.get('stats', {})

                # Ekstrak data Hitters (Pemukul)
                if 'batting' in stats and stats['batting'].get('plateAppearances', 0) > 0:
                    b = stats['batting']
                    tb = b.get('hits', 0) + b.get('doubles', 0) + (b.get('triples', 0)*2) + (b.get('homeRuns', 0)*3)
                    hitter_rows.append({
                        'Team': team_name,
                        'Name': name,
                        'H': b.get('hits', 0),
                        'HR': b.get('homeRuns', 0),
                        'R': b.get('runs', 0),
                        'RBI': b.get('rbi', 0),
                        'TB': tb
                    })

                # Ekstrak data Pitchers (Pelempar)
                if 'pitching' in stats and float(stats['pitching'].get('inningsPitched', '0.0')) > 0:
                    p = stats['pitching']
                    pitcher_rows.append({
                        'Team': team_name,
                        'Name': name,
                        'IP': p.get('inningsPitched', '0.0'),
                        'H Allowed': p.get('hits', 0),
                        'R Allowed': p.get('runs', 0),
                        'SO': p.get('strikeOuts', 0)
                    })

        df_h = pd.DataFrame(hitter_rows)
        df_p = pd.DataFrame(pitcher_rows)
        return df_h, df_p

    except Exception as e:
        # Kalau gagal narik data (misal game belum main), balikin tabel kosong biar app nggak crash
        return pd.DataFrame(), pd.DataFrame()

# ====================================================================
# 5. NAVIGASI TABS (Sekarang ada 8 Tab)
# ====================================================================
game_details = today_schedule
tabs = st.tabs([
    "🎯 Tab 1: Sniper Pick", 
    "📊 Tab 2: Hitter Stats", 
    "🏭 Tab 3: SGP Factory", 
    "🔥 Tab 4: Live Report", 
    "🛡️ Tab 5: AI Auditor", 
    "🏪 Tab 6: Team Market", 
    "💸 Tab 7: Cross Parlay",
    "🕸️ Tab 8: Overlap Network",
    "🏭 Tab 9 : Modelling Test",
    " Tab 10 : Pitcher Projection"
])

# ====================================================================
# TAB 1: STARTING PITCHER METRICS (FULL SEASON BASELINE)
# ====================================================================
with tabs[0]:
    st.subheader("🎯 Starting Pitcher Metrics - Full Season Baseline")
    st.caption("Data performa kumulatif musim ini. Di-update otomatis oleh bot github setiap hari.")
    
    if not df_pitchers.empty:
        # 1. Tentukan urutan kolom ideal agar enak dilihat (Nama dan Tim di depan)
        kolom_ideal = ['Name', 'Team', 'ERA', 'WHIP', 'K/9', 'BB/9', 'H/9', 'HR/9', 'FB%', 'IP', 'GS', 'W', 'L']
        # Ambil kolom yang benar-benar ada di CSV lu untuk mencegah crash
        available_cols = [c for c in kolom_ideal if c in df_pitchers.columns]
        df_display = df_pitchers[available_cols].copy()
        
        # 2. SUNTIKAN KAWIN DATA: Ambil label 'Status/Kasta' dari l30_pitchers.json
        if isinstance(l30_pitchers_data, dict) and l30_pitchers_data:
            kasta_list = []
            for idx, row in df_display.iterrows():
                p_name = row.get('Name')
                # Tarik teks status ("Elite", "Vulnerable", "Average") dari sub-objek 'season'
                status_live = l30_pitchers_data.get(p_name, {}).get('season', {}).get('Status', 'Average')
                kasta_list.append(status_live)
                
            df_display['Kasta'] = kasta_list
            
            # Pindahkan kolom 'Kasta' ke urutan ketiga (setelah nama & tim) biar rapi
            cols = list(df_display.columns)
            if 'Kasta' in cols:
                cols.insert(2, cols.pop(cols.index('Kasta')))
                df_display = df_display[cols]

        # 3. RENDER DATAFRAME + GRADASI WARNA (VISUAL AUDIT)
        # - ERA, WHIP, H/9, HR/9, FB%: Makin KECIL makin HIJAU (Bagus buat Pitcher), Makin BESAR makin MERAH (Ampas)
        # - K/9: Makin BESAR makin HIJAU (Raja Strikeout)
        st.dataframe(
            df_display.style.background_gradient(cmap='RdYlGn_r', subset=['ERA', 'WHIP', 'H/9', 'HR/9', 'FB%'])
            .background_gradient(cmap='RdYlGn', subset=['K/9']),
            use_container_width=True,
            height=520,
            hide_index=True
        )
    else:
        st.warning("⚠️ Data 'master_pitcher_2026.csv' kosong. Pastikan workflow github actions lu sudah berjalan sukses malam ini.")

# ====================================================================
# TAB 2: HITTER STATCAST & DISCIPLINE RADAR
# ====================================================================
with tabs[1]:
    st.subheader("🏏 Hitter Statcast & Plate Discipline Radar")
    st.caption("Data performa pukulan. Di-update harian otomatis via Savant.")
    
    if not df_hitters.empty:
        # 1. Kumpulkan list tim yang bertanding hari ini
        playing_teams = []
        if isinstance(today_schedule, list):
            for game in today_schedule:
                if game.get('away_team'): playing_teams.append(game['away_team'])
                if game.get('home_team'): playing_teams.append(game['home_team'])
        
        # 2. Filter data: Hanya tampilkan hitter yang timnya main hari ini
        df_display = df_hitters[df_hitters['Team'].isin(playing_teams)].copy()
        
        # Fallback kalau data kosong (belum rilis jadwal)
        if df_display.empty:
            df_display = df_hitters.head(50).copy()

        # 3. Panggil kolom yang SUDAH DISTANDARISASI di global
        avail_cols = [
            'Name', 'Age', 'Team', 'xwOBA', 'xBA', 'xSLG', 'K%', 'BB%',
            'Barrel%', 'Max EV', 'HardHit%', 'SweetSpot%', 
            'FB%', 'Chase%', 'Whiff%', 'ZoneContact%', 'Pull%'
        ]
        df_display = df_display[[c for c in avail_cols if c in df_display.columns]]

        # 4. ATUR WARNA GRADASI 
        styled_hitters = df_display.style
        
        # Hijau = Makin tinggi makin jago (Power & Kontak)
        hijau = [c for c in ['xwOBA', 'xBA', 'xSLG', 'BB%', 'Barrel%', 'Max EV', 'HardHit%', 'SweetSpot%', 'FB%', 'ZoneContact%', 'Pull%'] if c in df_display.columns]
        
        # Merah = Makin tinggi makin ampas (Strikeout & Buta Huruf)
        merah = [c for c in ['K%', 'Chase%', 'Whiff%'] if c in df_display.columns]
        
        if hijau:
            styled_hitters = styled_hitters.background_gradient(cmap='RdYlGn', subset=hijau)
        if merah:
            styled_hitters = styled_hitters.background_gradient(cmap='RdYlGn_r', subset=merah)
            
        # 5. Render DataFrame ke layar
        st.dataframe(
            styled_hitters,
            use_container_width=True,
            height=520,
            hide_index=True
        )
    else:
        st.warning("⚠️ Data 'master_hitter_2026.csv' kosong atau belum digenerate oleh bot.")

# ====================================================================
# TAB 4: LIVE REPORT & FINAL BOXSCORE (MOBILE OPTIMIZED)
# ====================================================================
with tabs[3]:
    st.header("📡 Live Report & Final Boxscore")
    st.caption("Pantau skor langsung langsung dari lapangan. Dioptimalkan khusus tampilan mobile browser.")

    # 🔄 TOMBOL MANUAL REFRESH (Anti-Lag & Hemat Kuota HP)
    col_ref, _ = st.columns([1, 2])
    with col_ref:
        if st.button("🔄 Sinkronkan Skor Sekarang", use_container_width=True):
            st.cache_data.clear() # Paksa buang cache live report saat diklik
            st.success("Berhasil ditarik ulang!")

    if not game_details:
        st.info("Jadwal pertandingan belum tersedia untuk hari ini.")
    else:
        for game in game_details:
            away_t = game.get('away_team', game.get('away', 'TBD'))
            home_t = game.get('home_team', game.get('home', 'TBD'))
            game_status = game.get('status', 'Scheduled')
            game_id = game.get('game_id', 0)

            if game_status in ['Scheduled', 'Pre-Game', 'Warmup']:
                with st.expander(f"⏳ {away_t} @ {home_t}", expanded=False): 
                    st.info("Pertandingan belum dimulai.")
                continue

            with st.expander(f"🔥 {away_t} @ {home_t} - {game_status}", expanded=False):
                try:
                    live_h, live_p = get_live_boxscore(game_id, away_t, home_t)

                    if not live_h.empty and not live_p.empty:
                        sukses_h = live_h[(live_h['H'] >= 1) | (live_h['HR'] >= 1) | (live_h['R'] >= 1) | (live_h['RBI'] >= 1) | (live_h['TB'] >= 1)]

                        # 📱 LAYOUT HP: Dibuat berurutan ke bawah (Hitter dulu, baru Pitcher)
                        st.markdown("#### 🏏 Hitters (Pencetak Skor)")
                        if not sukses_h.empty: 
                            st.dataframe(sukses_h.sort_values(by=['TB', 'H'], ascending=False), hide_index=True, use_container_width=True)
                        else: 
                            st.write("Belum ada hitter yang pecah telor.")
                            
                        st.divider()
                        
                        st.markdown("#### 🎯 Pitchers (Rapor Lemparan)")
                        st.dataframe(live_p[['Team', 'Name', 'IP', 'H Allowed', 'R Allowed', 'SO']], hide_index=True, use_container_width=True)
                    else: 
                        st.write("Sedang menyinkronkan data boxscore...")
                except Exception as e:
                    st.error(f"Gagal memuat log stats: {e}")

# ====================================================================
# TAB 3: SAME GAME PARLAY (SGP) FACTORY (CONN_SCORE ADJUSTED)
# ====================================================================
with tabs[2]: # Merombak SGP Factory menjadi Today Matchup Matrix
        st.header("🏟️ Tab 3: Today Matchup Matrix")
        st.markdown("Analisis Komparasi Langsung: **Hitter Projections vs Opposing Starting Pitcher**")

        # 1. LOAD SEMUA BAHAN BAKU DATA
        data_siap = True
        try:
            import json
            import numpy as np
            
            # Load Jadwal Hari Ini
            with open('today_schedule.json', 'r') as f:
                jadwal_hari_ini = json.load(f)
                
            # Load Database Platoon
            df_h_lhp = pd.read_csv("hitter_vs_lhp.csv")
            df_h_rhp = pd.read_csv("hitter_vs_rhp.csv")
            df_p_lhb = pd.read_csv("pitcher_vs_lhb.csv")
            df_p_rhb = pd.read_csv("pitcher_vs_rhb.csv")
            
        except Exception as e:
            st.error(f"⚠️ Gagal memuat data pertandingan hari ini: {e}")
            data_siap = False

        if data_siap:
            if not jadwal_hari_ini:
                st.warning("Tidak ada jadwal pertandingan aktif untuk hari ini.")
            else:
                # 2. DROPDOWN PILIHAN PERTANDINGAN
                opsi_match = [f"{g['away_team']} @ {g['home_team']} (ID: {g['game_id']})" for g in jadwal_hari_ini]
                pilihan_user = st.selectbox("🎯 Pilih Pertandingan Hari Ini untuk Dianslisis:", opsi_match, key="sb_match_t3")
                
                # Ambil data game yang dipilih
                idx_match = opsi_match.index(pilihan_user)
                game_terpilih = jadwal_hari_ini[idx_match]
                
                away_team = game_terpilih['away_team']
                home_team = game_terpilih['home_team']
                away_sp = game_terpilih['away_pitcher']
                home_sp = game_terpielder = game_terpilih['home_pitcher'] if 'home_pitcher' in game_terpilih else game_terpilih.get('home_pitcher', 'TBD')
                home_sp = game_terpilih['home_pitcher']

                # --- FUNGSI DETEKSI TANGAN PITCHER (LHP/RHP) ---
                # Mendeteksi otomatis tangan pitcher berdasarkan keberadaan namanya di database platoon pitcher
                def deteksi_tangan_sp(nama_pitcher):
                    if nama_pitcher in df_p_lhb['player_name_std'].values:
                        return "LHP (Kidal)"
                    elif nama_pitcher in df_p_rhb['player_name_std'].values:
                        return "RHP (Kanan)"
                    return "RHP (Kanan)" # Fallback standar jika data rookie/TBD

                away_sp_hand = deteksi_tangan_sp(away_sp)
                home_sp_hand = deteksi_tangan_sp(home_sp)

                # Info Box Ringkasan Matchup
                st.info(f"⚔️ **{away_team}** menghadapi **{home_team}** | SP Lawan: {away_sp} ({away_sp_hand}) vs {home_sp} ({home_sp_hand})")

                # 3. SPLIT LAYAR: COL1 (AWAY) & COL2 (HOME)
                col_away, col_home = st.columns(2)

                # ==========================================
                # KANAL TIM AWAY (Tamu)
                # ==========================================
                with col_away:
                    st.subheader(f"🛡️ {away_team} (Away)")
                    
                    # A. Proyeksi SP Away vs Roster Home
                    st.caption(f"📊 **Proyeksi SP: {away_sp}**")
                    df_sp_away_data = df_p_lhb if away_sp_hand == "LHP (Kidal)" else df_p_rhb
                    df_sp_a = df_sp_away_data[df_sp_away_data['player_name_std'] == away_sp]
                    
                    if not df_sp_a.empty:
                        # Jalankan Math Engine Pitcher (Sesuai Standar Tab 10)
                        expected_pa = 22.5
                        ip_col = 'p_formatted_ip_Full' if 'p_formatted_ip_Full' in df_sp_a.columns else 'p_formatted_ip'
                        pa_col = 'pa_Full' if 'pa_Full' in df_sp_a.columns else 'pa'
                        era_col = 'p_era_Full' if 'p_era_Full' in df_sp_a.columns else 'p_era'
                        
                        df_sp_a['Outs'] = np.floor(df_sp_a[ip_col]) * 3 + np.round((df_sp_a[ip_col] - np.floor(df_sp_a[ip_col])) * 10)
                        proj_outs = round(float((df_sp_a['Outs'] / df_sp_a[pa_col] * expected_pa).fillna(15).iloc[0]), 1)
                        proj_so = round(float((((df_sp_a['k_percent_L60'] / 100) + (df_sp_a['swing_miss_percent'] / 100)) / 2 * expected_pa).fillna(0).iloc[0]), 2)
                        proj_er = round(float((df_sp_a[era_col].iloc[0] / 27) * proj_outs * (df_sp_a['xwoba_L60'].iloc[0] / df_sp_a['xwoba_Full'].iloc[0])), 2)
                        
                        st.metric(label=f"{away_sp} Projections", value=f"{proj_so} K's ┃ {proj_outs} Outs", delta=f"{proj_er} Expected ER", delta_color="inverse")
                    else:
                        st.warning(f"Data statistik {away_sp} belum lengkap di Savant.")

                    # B. Proyeksi Hitter Away vs Pitcher Home (Melihat Tangan Home SP)
                    st.caption(f"🏏 **Hitter {away_team} vs {home_sp_hand}**")
                    df_h_away_source = df_h_lhp if home_sp_hand == "LHP (Kidal)" else df_h_rhp
                    
                    # [AUTO-DETECT] Kolom Tim
                    team_col_a = 'Team_Full' if 'Team_Full' in df_h_away_source.columns else ('Team' if 'Team' in df_h_away_source.columns else None)
                    
                    if team_col_a:
                        df_h_a = df_h_away_source[df_h_away_source[team_col_a] == away_team].copy()
                    else:
                        df_h_a = pd.DataFrame()
                    
                    if not df_h_a.empty:
                        expected_pa_h = 4.25
                        
                        # [AUTO-DETECT] Kolom HardHit Full Season
                        hh_full_col_a = 'hard_hit_percent_Full' if 'hard_hit_percent_Full' in df_h_a.columns else 'hard_hit_percent'
                        
                        df_h_a['SweetSpot_Mod'] = 1 + ((df_h_a['sweet_spot_percent'] - 33) / 100)
                        df_h_a['AirBall_Mod'] = 1 + (((df_h_a['flyballs_percent'] + df_h_a['linedrives_percent']) - 50) / 100)
                        df_h_a['Power_Surge'] = np.where(df_h_a['hardhit_percent'] > df_h_a[hh_full_col_a], 1.15, 1.0)
                        
                        df_h_a['Proj_Hit'] = ((df_h_a['hit']/df_h_a['pa_Full']) * (df_h_a['xba_L30']/df_h_a['xba_Full']) * df_h_a['SweetSpot_Mod'] * expected_pa_h).fillna(0).round(2)
                        df_h_a['Proj_TB'] = ((df_h_a['b_total_bases']/df_h_a['pa_Full']) * (df_h_a['xslg_L30']/df_h_a['xslg_Full']) * df_h_a['AirBall_Mod'] * df_h_a['Power_Surge'] * expected_pa_h).fillna(0).round(2)
                        df_h_a['Proj_HR%'] = ((df_h_a['home_run']/df_h_a['pa_Full']) * (df_h_a['xwoba_L30']/df_h_a['xwoba_Full']) * (1 + ((df_h_a['flyballs_percent'] - 23) / 100)) * df_h_a['Power_Surge'] * expected_pa_h * 100).fillna(0).round(1)
                        
                        # Filter & Tampilkan data Hitter Away
                        df_display_away = df_h_a[df_h_a['pa_Full'] >= 30][['player_name_std', 'Proj_Hit', 'Proj_TB', 'Proj_HR%']].sort_values(by='Proj_TB', ascending=False)
                        df_display_away.rename(columns={'player_name_std': 'Hitter Name', 'Proj_HR%': 'HR %'}, inplace=True)
                        st.dataframe(df_display_away, use_container_width=True, hide_index=True)
                    else:
                        st.warning(f"Roster hitter {away_team} tidak ditemukan.")

                # ==========================================
                # KANAL TIM HOME (Tuan Rumah)
                # ==========================================
                with col_home:
                    st.subheader(f"🏠 {home_team} (Home)")
                    
                    # A. Proyeksi SP Home vs Roster Away
                    st.caption(f"📊 **Proyeksi SP: {home_sp}**")
                    df_sp_home_data = df_p_lhb if home_sp_hand == "LHP (Kidal)" else df_p_rhb
                    df_sp_h = df_sp_home_data[df_sp_home_data['player_name_std'] == home_sp]
                    
                    if not df_sp_h.empty:
                        # Jalankan Math Engine Pitcher
                        expected_pa = 22.5
                        ip_col = 'p_formatted_ip_Full' if 'p_formatted_ip_Full' in df_sp_h.columns else 'p_formatted_ip'
                        pa_col = 'pa_Full' if 'pa_Full' in df_sp_h.columns else 'pa'
                        era_col = 'p_era_Full' if 'p_era_Full' in df_sp_h.columns else 'p_era'
                        
                        df_sp_h['Outs'] = np.floor(df_sp_h[ip_col]) * 3 + np.round((df_sp_h[ip_col] - np.floor(df_sp_h[ip_col])) * 10)
                        proj_outs_h = round(float((df_sp_h['Outs'] / df_sp_h[pa_col] * expected_pa).fillna(15).iloc[0]), 1)
                        proj_so_h = round(float((((df_sp_h['k_percent_L60'] / 100) + (df_sp_h['swing_miss_percent'] / 100)) / 2 * expected_pa).fillna(0).iloc[0]), 2)
                        proj_er_h = round(float((df_sp_h[era_col].iloc[0] / 27) * proj_outs_h * (df_sp_h['xwoba_L60'].iloc[0] / df_sp_h['xwoba_Full'].iloc[0])), 2)
                        
                        st.metric(label=f"{home_sp} Projections", value=f"{proj_so_h} K's ┃ {proj_outs_h} Outs", delta=f"{proj_er_h} Expected ER", delta_color="inverse")
                    else:
                        st.warning(f"Data statistik {home_sp} belum lengkap di Savant.")

                    # B. Proyeksi Hitter Home vs Pitcher Away (Melihat Tangan Away SP)
                    st.caption(f"🏏 **Hitter {home_team} vs {away_sp_hand}**")
                    df_h_home_source = df_h_lhp if away_sp_hand == "LHP (Kidal)" else df_h_rhp
                    
                    # [AUTO-DETECT] Kolom Tim
                    team_col_h = 'Team_Full' if 'Team_Full' in df_h_home_source.columns else ('Team' if 'Team' in df_h_home_source.columns else None)
                    
                    if team_col_h:
                        df_h_h = df_h_home_source[df_h_home_source[team_col_h] == home_team].copy()
                    else:
                        df_h_h = pd.DataFrame()
                    
                    if not df_h_h.empty:
                        expected_pa_h = 4.25
                        
                        # [AUTO-DETECT] Kolom HardHit Full Season
                        hh_full_col_h = 'hard_hit_percent_Full' if 'hard_hit_percent_Full' in df_h_h.columns else 'hard_hit_percent'
                        
                        df_h_h['SweetSpot_Mod'] = 1 + ((df_h_h['sweet_spot_percent'] - 33) / 100)
                        df_h_h['AirBall_Mod'] = 1 + (((df_h_h['flyballs_percent'] + df_h_h['linedrives_percent']) - 50) / 100)
                        df_h_h['Power_Surge'] = np.where(df_h_h['hardhit_percent'] > df_h_h[hh_full_col_h], 1.15, 1.0)
                        
                        df_h_h['Proj_Hit'] = ((df_h_h['hit']/df_h_h['pa_Full']) * (df_h_h['xba_L30']/df_h_h['xba_Full']) * df_h_h['SweetSpot_Mod'] * expected_pa_h).fillna(0).round(2)
                        df_h_h['Proj_TB'] = ((df_h_h['b_total_bases']/df_h_h['pa_Full']) * (df_h_h['xslg_L30']/df_h_h['xslg_Full']) * df_h_h['AirBall_Mod'] * df_h_h['Power_Surge'] * expected_pa_h).fillna(0).round(2)
                        df_h_h['Proj_HR%'] = ((df_h_h['home_run']/df_h_h['pa_Full']) * (df_h_h['xwoba_L30']/df_h_h['xwoba_Full']) * (1 + ((df_h_h['flyballs_percent'] - 23) / 100)) * df_h_h['Power_Surge'] * expected_pa_h * 100).fillna(0).round(1)
                        
                        # Filter & Tampilkan data Hitter Home
                        df_display_home = df_h_h[df_h_h['pa_Full'] >= 30][['player_name_std', 'Proj_Hit', 'Proj_TB', 'Proj_HR%']].sort_values(by='Proj_TB', ascending=False)
                        df_display_home.rename(columns={'player_name_std': 'Hitter Name', 'Proj_HR%': 'HR %'}, inplace=True)
                        st.dataframe(df_display_home, use_container_width=True, hide_index=True)
                    else:
                        st.warning(f"Roster hitter {home_team} tidak ditemukan.")

with tabs[4]:
    st.header("🛡️ AI Auditor & Advanced ROI Tracker")
    history = load_betting_history()
    win_rate = (history['wins'] / history['total_bets'] * 100) if history['total_bets'] > 0 else 0
    profit_loss = history['total_returned'] - history['total_staked']
    roi = (profit_loss / history['total_staked'] * 100) if history['total_staked'] > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="🎯 Win Rate", value=f"{win_rate:.1f}%")
    m2.metric(label=f"💸 Profit/Loss", value=f"Rp {profit_loss:,}")
    m3.metric(label="📊 ROI", value=f"{roi:.1f}%")
    m4.metric(label="🎫 Total Slip", value=f"{history['total_bets']} Tiket")
    st.divider()

    st.subheader("📋 Kunci Jawaban & Log Boxscore H-1")
    if not yesterday_results:
        st.info("Menunggu data pertandingan H-1 disinkronkan.")
    elif isinstance(yesterday_results, dict):
        for g_id, g_data in yesterday_results.items():
            if not isinstance(g_data, dict): continue
            with st.container():
                st.markdown(f"### 📋 {g_data.get('matchup', 'Match')}")
                st.markdown(f"**Skor Akhir:** {g_data.get('away_runs', 0)} - {g_data.get('home_runs', 0)}")
                with st.expander("🔎 Buka Log Statistik"):
                    for p_name, p_stat in g_data.get('players', {}).items():
                        if 'tb' in p_stat and p_stat['tb'] > 0: 
                            st.write(f"⚾ **{p_name}**: Hits: {p_stat['hits']} | TB: {p_stat['tb']} | HR: {p_stat['hr']}")
                        elif 'strikeouts_pitcher' in p_stat:
                            st.write(f"🔥 **{p_name} (SP)**: K: {p_stat['strikeouts_pitcher']}")
                st.divider()

# ====================================================================
# TAB 6: MATCH & TEAM MARKET TERMINAL (PYTHAGOREAN ENGINE)
# ====================================================================
with tabs[5]:
    st.header("🏪 Match & Team Market Terminal")
    st.caption("SOP: Proyeksi Moneyline dan O/U menggunakan Pythagorean Expectation, L45 SP ERA, dan Park Factor.")
    
    if isinstance(today_schedule, list) and not df_hitters.empty:
        market_rows = []
        for game in today_schedule:
            away_t = game['away_team']
            home_t = game['home_team']
            
            # 1. Ambil Kualitas Hitter (Murni pakai xwOBA dari pembaruan Savant)
            h_away = df_hitters[df_hitters['Team'] == away_t]
            h_home = df_hitters[df_hitters['Team'] == home_t]
            score_away = h_away['xwOBA'].mean() if not h_away.empty else 0.315
            score_home = h_home['xwOBA'].mean() if not h_home.empty else 0.315

            # 2. Ambil Kualitas Pitching (Integrasi dengan L45 Matrix dari Tab 7)
            team_era_away = get_pitcher_era(away_t)
            team_era_home = get_pitcher_era(home_t)
            
            sp_away_name = game.get('away_pitcher', 'TBD')
            sp_home_name = game.get('home_pitcher', 'TBD')
            
            # Tarik ERA L45 Pitcher (Lebih presisi dari df_pitchers bawaan)
            p_data_away = l30_pitchers_data.get(sp_away_name, {}) if isinstance(l30_pitchers_data, dict) else {}
            p_data_home = l30_pitchers_data.get(sp_home_name, {}) if isinstance(l30_pitchers_data, dict) else {}
            
            sp_era_away = p_data_away.get('l45', {}).get('ERA', team_era_away)
            sp_era_home = p_data_home.get('l45', {}).get('ERA', team_era_home)
            
            # Bobot Pitching: 60% Starter, 40% Bullpen
            true_pitch_away = (sp_era_away * 0.6) + (team_era_away * 0.4)
            true_pitch_home = (sp_era_home * 0.6) + (team_era_home * 0.4)

            # 3. Faktor Lingkungan
            park_mult = PARK_FACTORS.get(home_t, 1.00)

            # 4. Proyeksi Runs (BaseRuns Logic)
            proj_r_a = (score_away / 0.315) * true_pitch_home * park_mult
            proj_r_home = (score_home / 0.315) * true_pitch_away * park_mult
            total_proj = round(proj_r_a + proj_r_home, 1)

            # 5. Pythagorean Win Probability (Eksponen 1.83 adalah standar MLB)
            pyth_away = (proj_r_a**1.83) / (proj_r_a**1.83 + proj_r_home**1.83)
            pyth_home = (proj_r_home**1.83) / (proj_r_a**1.83 + proj_r_home**1.83)
            
            win_prob_away = round(pyth_away * 100, 1)
            win_prob_home = round(pyth_home * 100, 1)
            
            if win_prob_away > win_prob_home:
                fav, dog, wp = away_t, home_t, win_prob_away
            else:
                fav, dog, wp = home_t, away_t, win_prob_home

            # 6. Rekomendasi Handicap (Runline) & Over/Under
            hc_rec = f"{fav} -1.5" if wp >= 58.0 else f"{dog} +1.5"
            
            if total_proj >= 9.0:
                ou_rec = "🟢 OVER"
            elif total_proj <= 7.5:
                ou_rec = "🔴 UNDER"
            else:
                ou_rec = "🟡 PASS"
            
            # 7. Memasukkan ke Tabel Visual
            market_rows.append({
                'Match': f"{away_t} @ {home_t}",
                'SP Duel': f"{sp_away_name} vs {sp_home_name}", 
                '🔥 ML Pick': fav, 
                'WP%': wp, 
                '📐 Runline': hc_rec, 
                '📊 Proj Total': total_proj,
                'O/U Pick': ou_rec
            })
            
        # Rendering dengan Panduan Warna Gradasi
        df_market = pd.DataFrame(market_rows)
        
        # Kolom WP% akan berwarna hijau pekat jika peluang menang di atas 60%
        styled_market = df_market.style.background_gradient(cmap='Greens', subset=['WP%'])
        
        st.dataframe(styled_market, hide_index=True, use_container_width=True)
    else:
        st.warning("Data Hitter atau Jadwal belum siap.")

# ====================================================================
# TAB 7: CROSS-GAME PARLAY & MASTER SLIPS (THE ULTIMATE BOMB SQUAD)
# ====================================================================
with tabs[6]:
    st.header("💸 Cross-Game Parlay & Master Slips")
    st.caption("SOP: Eksekusi tiket raksasa Lintas Pertandingan, Pitcher Matrix, dan Kombinasi Bertingkat Anti-Overlap.")

    if len(today_schedule) < 2:
        st.info("Butuh minimal 2 laga berjalan hari ini untuk menyusun tiket Cross-Game.")
    elif not df_matrix_global.empty:

        # Penampung global untuk mencegah overlap pemain antar-slip VIP
        taken_vip_players = []

        # ====================================================================
        # 🎫 SLIP 1: VIP ULXRARE PAIRING (2-LEGS)
        # ====================================================================
        st.markdown("### 🎫 SLIP 1: VIP ULXRARE PAIRING (2-LEGS)")
        st.caption("Poros utama parlay hari ini. 2 Pemain terbaik dengan kombinasi Connection + Diversity tertinggi.")

        survivors_s1 = df_matrix_global[df_matrix_global['Conn_Score'] >= 3].to_dict('records')

        best_pair, max_ulx_score = None, -1
        if len(survivors_s1) >= 2:
            for p1, p2 in itertools.combinations(survivors_s1, 2):
                div_score = 0
                if p1['Team'] != p2['Team']: div_score += 1
                if p1.get('Home_Park', '') != p2.get('Home_Park', ''): div_score += 1
                if p1.get('Archetype', '') != p2.get('Archetype', ''): div_score += 2
                if (p1.get('PF_Multiplier', 1.0) > 1.0) != (p2.get('PF_Multiplier', 1.0) > 1.0): div_score += 1

                ulx_score = (p1['Conn_Score'] + p2['Conn_Score']) * div_score
                if ulx_score > max_ulx_score and div_score >= 3:
                    max_ulx_score = ulx_score
                    best_pair = (p1, p2, div_score)

            if best_pair:
                leg1, leg2, d_score = best_pair
                taken_vip_players.extend([leg1['Name'], leg2['Name']]) # Cekal pemain ini

                st.success(f"🔥 **VIP 2-LEGS FOUND** (Score: {max_ulx_score} | Diversity: {d_score}/5)")
                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"**LEG 1: {leg1['Name']}** ({leg1['Team']}) ➔ *{leg1['Archetype']}*")
                with c2:
                    st.info(f"**LEG 2: {leg2['Name']}** ({leg2['Team']}) ➔ *{leg2['Archetype']}*")
            else: st.caption("Tidak ada kombinasi 2-Leg yang memenuhi syarat aman.")
        else: st.caption("Kandidat Hitter terlalu sedikit.")

        st.divider()

        # ====================================================================
        # 🎫 SLIP 1B: LOTTO ULXRARE PAIRING (3-LEGS - NO OVERLAP)
        # ====================================================================
        st.markdown("### 🎫 SLIP 1B: LOTTO ULXRARE PAIRING (3-LEGS)")
        st.caption("Tiket sekunder berisiko menengah. Menggunakan pemain alternatif yang bersih dari Slip 1.")

        # Filter: Buang pemain yang sudah diambil di Slip 1
        survivors_s1b = df_matrix_global[(df_matrix_global['Conn_Score'] >= 2) & (~df_matrix_global['Name'].isin(taken_vip_players))].head(20).to_dict('records')

        best_trio, max_ulx_s1b = None, -1
        if len(survivors_s1b) >= 3:
            for p1, p2, p3 in itertools.combinations(survivors_s1b, 3):
                # Hitung akumulasi keberagaman berpasangan (Pairwise Diversity)
                div_score = 0
                for combo in itertools.combinations([p1, p2, p3], 2):
                    if combo[0]['Team'] != combo[1]['Team']: div_score += 1
                    if combo[0].get('Home_Park', '') != combo[1].get('Home_Park', ''): div_score += 1
                    if combo[0].get('Archetype', '') != combo[1].get('Archetype', ''): div_score += 1

                total_conn = p1['Conn_Score'] + p2['Conn_Score'] + p3['Conn_Score']
                ulx_score = total_conn * div_score

                if ulx_score > max_ulx_s1b:
                    max_ulx_s1b = ulx_score
                    best_trio = (p1, p2, p3, div_score)

            if best_trio:
                l1, l2, l3, d_score_s1b = best_trio
                taken_vip_players.extend([l1['Name'], l2['Name'], l3['Name']]) # Tambah ke daftar cekal

                st.success(f"☄️ **LOTTO 3-LEGS FOUND** (Score: {max_ulx_s1b} | Pairwise Diversity Index: {d_score_s1b})")
                c1, c2, c3 = st.columns(3)
                with c1: st.error(f"**LEG 1: {l1['Name']}** ({l1['Team']})")
                with c2: st.info(f"**LEG 2: {l2['Name']}** ({l2['Team']})")
                with c3: st.warning(f"**LEG 3: {l3['Name']}** ({l3['Team']})")
            else: st.caption("Tidak ada kombinasi 3-Leg yang ideal.")
        else: st.caption("Sisa pemain tidak cukup untuk diracik menjadi 3-Leg Lotto.")

        st.divider()

        # ====================================================================
        # 🎫 SLIP 1C: MEGA LOTTO ULTRA PROPS (4-LEGS - NO OVERLAP)
        # ====================================================================
        st.markdown("### 💣 SLIP 1C: MEGA LOTTO ULXRARE (4-LEGS)")
        st.caption("Tiket High-Risk High-Reward (Boomer Slip). Pemain murni diambil dari sisa database yang belum terjamah.")
        
        # Filter: Buang semua pemain yang sudah dipakai di Slip 1 dan Slip 1B
        survivors_s1c = df_matrix_global[(df_matrix_global['Conn_Score'] >= 2) & (~df_matrix_global['Name'].isin(taken_vip_players))].head(20).to_dict('records')
        
        best_quad, max_ulx_s1c = None, -1
        if len(survivors_s1c) >= 4:
            for p1, p2, p3, p4 in itertools.combinations(survivors_s1c, 4):
                div_score = 0
                for combo in itertools.combinations([p1, p2, p3, p4], 2):
                    if combo[0]['Team'] != combo[1]['Team']: div_score += 1
                    if combo[0].get('Home_Park', '') != combo[1].get('Home_Park', ''): div_score += 1
                    if combo[0].get('Archetype', '') != combo[1].get('Archetype', ''): div_score += 1
                
                total_conn = p1['Conn_Score'] + p2['Conn_Score'] + p3['Conn_Score'] + p4['Conn_Score']
                ulx_score = total_conn * div_score
                
                if ulx_score > max_ulx_s1c:
                    max_ulx_s1c = ulx_score
                    best_quad = (p1, p2, p3, p4, div_score)
                    
            if best_quad:
                q1, q2, q3, q4, d_score_s1c = best_quad
                
                st.success(f"🚀 **MEGA LOTTO 4-LEGS DEPLOYED** (Score: {max_ulx_s1c} | Pairwise Diversity Index: {d_score_s1c})")
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.error(f"**LEG 1: {q1['Name']}** ({q1['Team']})")
                with c2: st.info(f"**LEG 2: {q2['Name']}** ({q2['Team']})")
                with c3: st.warning(f"**LEG 3: {q3['Name']}** ({q3['Team']})")
                with c4: st.success(f"**LEG 4: {q4['Name']}** ({q4['Team']})")
            else: st.caption("Tidak ada kombinasi 4-Leg yang ideal.")
        else: st.caption("Sisa pool data terlalu kritis, tidak aman dipaksakan bikin 4-Leg.")

        st.divider()

        # ====================================================================
        # 2. SLIP KEMBALI: MONSTER SGPx HR (2-3 Legs Lintas Match)
        # ====================================================================
        st.markdown("### 💣 SLIP 2: MONSTER SGPx HR (Lintas Match)")
        st.caption("Mengawinkan kandidat HR terbaik dari dua laga pertama di jadwal.")

        match1 = today_schedule[0]
        match2 = today_schedule[1]

        # Tarik dari matrix yang udah ada Conn_Score
        top_m1 = df_matrix_global[df_matrix_global['Team'].isin([match1['away_team'], match1['home_team']])].sort_values(by=['Conn_Score', 'Adj_Barrel'], ascending=[False, False]).head(2)
        top_m2 = df_matrix_global[df_matrix_global['Team'].isin([match2['away_team'], match2['home_team']])].sort_values(by=['Conn_Score', 'Adj_Barrel'], ascending=[False, False]).head(2)

        col_hr1, col_hr2 = st.columns(2)
        with col_hr1:
            st.error(f"🔥 **MATCH 1:** {match1['away_team']} vs {match1['home_team']}")
            if not top_m1.empty:
                for i, (_, row) in enumerate(top_m1.iterrows(), 1):
                    p_name = row.get('Name', 'Top Hitter') 
                    st.markdown(f"**{i}. {p_name}** ({row['Team']})")
                    st.write(f"↳ *To Hit HR (Conn: {row.get('Conn_Score',0)} | Barrel: {row.get('Adj_Barrel',0):.1f}%)*")
            else: st.write("Data hitter tidak tersedia.")

        with col_hr2:
            st.info(f"🔥 **MATCH 2:** {match2['away_team']} vs {match2['home_team']}")
            if not top_m2.empty:
                for i, (_, row) in enumerate(top_m2.iterrows(), 1):
                    p_name = row.get('Name', 'Top Hitter')
                    st.markdown(f"**{i}. {p_name}** ({row['Team']})")
                    st.write(f"↳ *To Hit HR (Conn: {row.get('Conn_Score',0)} | Barrel: {row.get('Adj_Barrel',0):.1f}%)*")
            else: st.write("Data hitter tidak tersedia.")

        st.divider()

        # ====================================================================
        # 3. FITUR BARU: THE PITCHER MATRIX (SLIP 3 - L45 DAYS OPTIMIZED)
        # ====================================================================
        st.markdown("### ⚾ SLIP 3: THE PITCHER MATRIX PARLAY (45-DAYS FORM)")
        st.caption("Sistem klaster otomatis pelempar berdasarkan tren kalender LAST 45 DAYS, Park Factor, dan Proyeksi Musuh.")

        assassins, workhorses, gas_cans = [], [], []

        for game in today_schedule:
            home_t = game['home_team']
            away_t = game['away_team']
            park_mult = PARK_FACTORS.get(home_t, 1.00)
            
            p_away = game.get('away_pitcher', 'TBD')
            p_home = game.get('home_pitcher', 'TBD')

            # 🔥 TRACKING FORM BERDASARKAN OBJEK .get('l45')
            p_data_away = l30_pitchers_data.get(p_away, {}) if isinstance(l30_pitchers_data, dict) else {}
            p_data_home = l30_pitchers_data.get(p_home, {}) if isinstance(l30_pitchers_data, dict) else {}
            
            # Ganti pancingan kuncinya ke 'l45'
            era_away = p_data_away.get('l45', {}).get('ERA', 4.15)
            starts_away = p_data_away.get('l45', {}).get('Starts', 0)
            
            era_home = p_data_home.get('l45', {}).get('ERA', 4.15)
            starts_home = p_data_home.get('l45', {}).get('Starts', 0)
            
            proj_runs_away = team_totals_data.get(away_t, 4.0) if isinstance(team_totals_data, dict) else 4.0
            proj_runs_home = team_totals_data.get(home_t, 4.0) if isinstance(team_totals_data, dict) else 4.0
            
            # Evaluasi Form Terkini Away Pitcher
            if p_away != "TBD":
                label_a = f"{p_away} (ERA: {era_away:.2f} | L45: {starts_away}G)"
                
                # UPGRADE: Toleransi Proyeksi dinaikkan ke 4.3, Park Factor dilonggarkan ke 1.05
                if era_away < 3.60 and park_mult <= 1.05 and proj_runs_home <= 4.3 and starts_away >= 3:
                    assassins.append((label_a, away_t, "OVER Strikeouts (Form: Hot 🔥)"))
                elif era_away <= 4.30 and starts_away >= 3:
                    workhorses.append((label_a, away_t, "OVER Outs Recorded"))
                elif (era_away > 4.50 or starts_away < 3) and proj_runs_home >= 4.2:
                    # UPGRADE: Park Factor dihapus saringannya. Pitcher busuk ketemu musuh jago = Auto Fade.
                    reason = "OVER Hits Allowed (Form: Cold ❄️)" if starts_away >= 3 else "FADE (Unstable/Sample Kurang)"
                    gas_cans.append((label_a, away_t, reason))

            # Evaluasi Form Terkini Home Pitcher
            if p_home != "TBD":
                label_h = f"{p_home} (ERA: {era_home:.2f} | L45: {starts_home}G)"
                
                if era_home < 3.60 and park_mult <= 1.05 and proj_runs_away <= 4.3 and starts_home >= 3:
                    assassins.append((label_h, home_t, "OVER Strikeouts (Form: Hot 🔥)"))
                elif era_home <= 4.30 and starts_home >= 3:
                    workhorses.append((label_h, home_t, "OVER Outs Recorded"))
                elif (era_home > 4.50 or starts_home < 3) and proj_runs_away >= 4.2:
                    reason = "OVER Hits Allowed (Form: Cold ❄️)" if starts_home >= 3 else "FADE (Unstable/Sample Kurang)"
                    gas_cans.append((label_h, home_t, reason))

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.success("👑 **THE ASSASSINS (Form 45d Hot)**")
            for p, t, rec in assassins[:3]: st.write(f"- **{p}** ({t})\n  ↳ *{rec}*")
            if not assassins: st.caption("Kosong.")
        with col_p2:
            st.info("🛡️ **WORKHORSES (Innings Eater)**")
            for p, t, rec in workhorses[:3]: st.write(f"- **{p}** ({t})\n  ↳ *{rec}*")
            if not workhorses: st.caption("Kosong.")
        with col_p3:
            st.error("🩸 **GAS CANS (Fade Target 45d)**")
            for p, t, rec in gas_cans[:3]: st.write(f"- **{p}** ({t})\n  ↳ *{rec}*")
            if not gas_cans: st.caption("Kosong.")

        st.divider()

        # ====================================================================
        # 4. THE BOMB SQUAD (SLIP 4, 5, 6)
        # ====================================================================
        st.markdown("### 🚀 THE BOMB SQUAD (CROSS-GAME HR PARLAY)")

        col_b1, col_b2 = st.columns(2)
        taken_players = []
        with col_b1:
            st.error("🎯 **SLIP 4: SNIPER HR (2-3 Legs)**")
            # Ambil 3 Alpha tertinggi
            sniper_picks = df_matrix_global.head(3)
            for _, row in sniper_picks.iterrows():
                p_name = row.get('Name', 'Unknown')
                taken_players.append(p_name)
                st.markdown(f"🔥 **{p_name}** ({row['Team']})")
                st.write(f"↳ *Adj Barrel: {row.get('Adj_Barrel',0):.1f}% | Conn: {row.get('Conn_Score',0)}*")

        with col_b2:
            st.info("☄️ **SLIP 5: LOTTO / LONGSHOT HR (5 Legs)**")
            # Ambil klaster Longshot
            lotto_pool = df_matrix_global[df_matrix_global['Archetype'] == "☄️ LONGSHOT (Boom/Bust)"]
            lotto_picks = lotto_pool.head(5) if not lotto_pool.empty else df_matrix_global.iloc[3:8]
            for _, row in lotto_picks.iterrows():
                p_name = row.get('Name', 'Unknown')
                taken_players.append(p_name)
                st.markdown(f"☄️ **{p_name}** ({row['Team']})")
                st.write(f"↳ *Adj Barrel: {row.get('Adj_Barrel',0):.1f}% | Conn: {row.get('Conn_Score',0)}*")

        st.divider()
        st.markdown("### 🔥 SLIP 6: HOT HAND HR (3-5 LEGS)")
        hot_hand_pool = df_matrix_global[~df_matrix_global['Name'].isin(taken_players)]
        if not hot_hand_pool.empty:
            hot_hand_candidates = hot_hand_pool.sort_values(by=['Adj_xwOBA', 'Adj_Barrel'], ascending=[False, False]).head(4)
            for _, row in hot_hand_candidates.iterrows():
                st.markdown(f"⚡ **{row.get('Name', 'Unknown')}** ({row['Team']}) ➔ *Adj Barrel: {row.get('Adj_Barrel',0):.1f}% | Conn: {row.get('Conn_Score',0)}*")

# ====================================================================
# TAB 8: THE OVERLAP NETWORK (PLAYER CLUSTERS)
# ====================================================================
with tabs[7]:
    st.header("🕸️ The Overlap Network (Player Clusters)")
    st.caption("Visualisasi Hitter yang lolos filtrasi mematikan secara bersamaan. (Ditampilkan maksimal 2 pemain terbaik per tim).")

    if not df_matrix_global.empty:

        # 👑 KLASTER 1: THE ALPHAS
        # Note: Pastikan batas skor minimal udah disesuaikan (>= 3) biar nggak kosong
        alphas = df_matrix_global[(df_matrix_global['Conn_Score'] >= 3) & (df_matrix_global['Archetype'] == "🌟 SUPERSTAR (Core)")]
        st.subheader("👑 KLASTER 1: THE ALPHAS (High Floor, High Ceiling)")
        if not alphas.empty:
            # SUNTIKAN LOGIKA BARU: Maksimal 2 nama per tim
            alphas_filtered = alphas.groupby('Team').head(2)
            st.dataframe(alphas_filtered[['Name', 'Team', 'Conn_Score', 'Adj_Barrel', 'Adj_xwOBA', 'Home_Park']], use_container_width=True)
        else: 
            st.caption("Tidak ada Alpha Player hari ini.")

        # 💣 KLASTER 2: MISPRICED LONGSHOTS
        longshots = df_matrix_global[(df_matrix_global['Archetype'] == "☄️ LONGSHOT (Boom/Bust)")]
        st.subheader("💣 KLASTER 2: THE DEEP-SPACE LONGSHOTS (Low Floor, Max Ceiling)")
        if not longshots.empty:
            # SUNTIKAN LOGIKA BARU: Maksimal 2 nama per tim
            longshots_filtered = longshots.groupby('Team').head(2)
            st.dataframe(longshots_filtered[['Name', 'Team', 'Conn_Score', 'Adj_Barrel', 'Max EV', 'Home_Park']], use_container_width=True)
        else: 
            st.caption("Tidak ada Longshot ideal hari ini.")

        # 🏟️ KLASTER 3: ENVIRONMENT KINGS
        env_kings = df_matrix_global[(df_matrix_global['PF_Multiplier'] > 1.05) & (df_matrix_global['Conn_Score'] >= 3)]
        st.subheader("🏟️ KLASTER 3: ENVIRONMENT KINGS (Tertolong Cuaca/Stadion)")
        if not env_kings.empty:
            # SUNTIKAN LOGIKA BARU: Maksimal 2 nama per tim
            env_kings_filtered = env_kings.groupby('Team').head(2)
            st.dataframe(env_kings_filtered[['Name', 'Team', 'Conn_Score', 'PF_Multiplier', 'Home_Park']], use_container_width=True)
        else: 
            st.caption("Tidak ada Environment Kings hari ini.")
    else:
        st.error("Data Matrix belum siap atau kosong.")
        
# ====================================================================
# TAB 9: MODELLING TEST
# ===================================================================
with tabs[8]: # Sesuaikan nama variabel tab lu, misal tab9 atau tabs[8]
        st.header("⚾ Tab 9: The Ultimate Hitter Matrix")
        st.caption("Modelling Projected Hitter")
    
        st.markdown("Proyeksi Presisi: **Hits, TB, HR, Run, RBI, & SO**")

        # 1. LOAD DATA (Tanpa Return, pakai Flagging)
        data_aman = True
        try:
            df_lhp = pd.read_csv("hitter_vs_lhp.csv")
            df_rhp = pd.read_csv("hitter_vs_rhp.csv")
        except Exception as e:
            st.error(f"⚠️ Menunggu data bot_updater.py: {e}")
            data_aman = False

        if data_aman:
            # 2. UI FILTERS
            col1, col2 = st.columns([1, 2])
            with col1:
                pitcher_hand = st.radio("Lawan Pitcher:", ["vs RHP (Kanan)", "vs LHP (Kidal)"], horizontal=True, key="radio_pitcher_t9")
            
            df = df_lhp if pitcher_hand == "vs LHP (Kidal)" else df_rhp

            if df.empty:
                st.warning("Data belum tersedia. Pastikan bot_updater.py sudah dieksekusi hari ini.")
            else:
                with col2:
                    # Deteksi otomatis nama kolom tim yang habis bermutasi
                    kolom_tim = 'Team_Full' if 'Team_Full' in df.columns else ('Team' if 'Team' in df.columns else None)
                    
                    if kolom_tim:
                        # Panggil daftar tim dari kolom_tim
                        daftar_tim = ['Semua Tim'] + sorted([t for t in df[kolom_tim].unique() if str(t) != 'nan' and str(t) != 'TBD'])
                        pilih_tim = st.selectbox("🔍 Filter Tim Hitter:", daftar_tim, key="filter_tim_t9")
                    else:
                        st.info("⚠️ Kolom Tim tidak ditemukan di CSV.")
                        pilih_tim = 'Semua Tim'

                if pilih_tim != 'Semua Tim' and kolom_tim:
                    # Filter dataframe berdasarkan pilihan
                    df = df[df[kolom_tim] == pilih_tim]

                # 3. THE ADVANCED MATH ENGINE
                expected_pa = 4.25 # Asumsi jatah PA per game

                # Amankan dari pembagian dengan nol
                kolom_wajib = ['pa_Full', 'xba_Full', 'xslg_Full', 'woba_Full', 'hard_hit_percent']
                for col in kolom_wajib:
                    if col in df.columns:
                        df[col] = df[col].replace(0, np.nan)
                        
                # --- MODIFIER & MOMENTUM ---
                df['SweetSpot_Mod'] = 1 + ((df['sweet_spot_percent'] - 33) / 100)
                df['AirBall_Mod'] = 1 + (((df['flyballs_percent'] + df['linedrives_percent']) - 50) / 100)
                
                # Power Surge: Membandingkan L30 HardHit vs Full Season HardHit
                df['Power_Surge'] = np.where(df['hardhit_percent'] > df['hard_hit_percent'], 1.15, 1.0)

                # --- A. PROYEKSI HITS & TB ---
                base_hit_rate = df['hit'] / df['pa_Full']
                df['Proj_Hit'] = (base_hit_rate * (df['xba_L30'] / df['xba_Full']) * df['SweetSpot_Mod'] * expected_pa).fillna(0).round(2)

                base_tb_rate = df['b_total_bases'] / df['pa_Full']
                df['Proj_TB'] = (base_tb_rate * (df['xslg_L30'] / df['xslg_Full']) * df['AirBall_Mod'] * df['Power_Surge'] * expected_pa).fillna(0).round(2)

                # --- B. PROBABILITAS HOME RUN ---
                base_hr_rate = df['home_run'] / df['pa_Full']
                fb_boost = 1 + ((df['flyballs_percent'] - 23) / 100)
                df['Proj_HR_Pct'] = (base_hr_rate * (df['xwoba_L30'] / df['xwoba_Full']) * fb_boost * df['Power_Surge'] * expected_pa * 100).fillna(0).round(1)

                # --- C. PROYEKSI RUN & RBI (PASARAN BARU) ---
                base_run_rate = df['r_run'] / df['pa_Full']
                obp_momentum = df['xobp'] / (df['batting_avg'] + (df['bb_percent_Full']/100)) 
                df['Proj_Run'] = (base_run_rate * obp_momentum * expected_pa).fillna(0).round(2)

                base_rbi_rate = df['b_rbi'] / df['pa_Full']
                rbi_momentum = df['woba_L30'] / df['woba_Full']
                df['Proj_RBI'] = (base_rbi_rate * rbi_momentum * df['Power_Surge'] * expected_pa).fillna(0).round(2)

                # --- D. PROYEKSI STRIKEOUT ---
                df['Proj_SO'] = (((df['k_percent_L30'] / 100) + (df['swing_miss_percent'] / 100)) / 2 * expected_pa * 1.5).fillna(0).round(2)

                # 4. RECOMMENDATION ENGINE (Diurutkan Kiri ke Kanan)
                def get_recommendation(row):
                    picks = []
                    
                    # 1. Total Bases Edge (Prioritas SGP tertinggi)
                    if row['Proj_TB'] >= 1.90: picks.append("🟢 O 1.5 TB")
                    elif row['Proj_TB'] <= 1.10 and row['groundballs_percent'] > 45: picks.append("🔴 U 1.5 TB")
                        
                    # 2. Hits Edge
                    if row['Proj_Hit'] >= 0.90: picks.append("🟢 O 0.5 Hit")
                    
                    # 3. Runs & RBI Edge
                    if row['Proj_RBI'] >= 0.85: picks.append("🟢 O 0.5 RBI")
                    if row['Proj_Run'] >= 0.85: picks.append("🟢 O 0.5 Run")
                        
                    # 4. Strikeout Edge
                    if row['Proj_SO'] >= 1.35: picks.append("🔴 O 0.5 SO")
                    elif row['Proj_SO'] <= 0.40: picks.append("🟢 U 0.5 SO")
                        
                    # 5. Hot Bat / SGP Bomb
                    if row['Proj_HR_Pct'] >= 25.0: picks.append("💣 SGP HR!")
                    elif row['Power_Surge'] == 1.15 and row['Proj_TB'] >= 1.5: picks.append("🔥 HOT BAT")
                        
                    return " ┃ ".join(picks) if picks else "🟡 Pass Semua"

                df['🎯 Priority Picks (Kiri->Kanan)'] = df.apply(get_recommendation, axis=1)

                # 5. RENDER TABEL FINAL
                display_cols = [
                    'player_name_std', 'Proj_Hit', 'Proj_TB', 'Proj_HR_Pct', 'Proj_RBI', 'Proj_Run', 'Proj_SO', 
                    'hardhit_percent', '🎯 Priority Picks (Kiri->Kanan)'
                ]
                
                # Filter pemain inti (PA > 50), urutkan dari probabilitas TB tertinggi
                df_clean = df[df['pa_Full'] >= 50][display_cols].sort_values(by='Proj_TB', ascending=False)
                
                df_clean.rename(columns={
                    'player_name_std': 'Hitter Name',
                    'hardhit_percent': 'HardHit% (L30)',
                    'Proj_HR_Pct': 'Proj HR (%)'
                }, inplace=True)

                st.data_editor(df_clean, use_container_width=True, hide_index=True, disabled=True)

with tabs[9]: # Sesuaikan nama variabel tab lu, misal tab10 atau tabs[9]
        st.header("🎯 Tab 10: Pitcher Platoon Matrix")
        st.markdown("Proyeksi Spesifik vs Lineup Kanan/Kidal: **Outs, SO, Hits Allowed, & Earned Runs**")

        # 1. LOAD DATA 
        data_aman_p = True
        try:
            df_p_lhb = pd.read_csv("pitcher_vs_lhb.csv")
            df_p_rhb = pd.read_csv("pitcher_vs_rhb.csv")
        except Exception as e:
            st.error(f"⚠️ Menunggu data bot_updater.py: {e}")
            data_aman_p = False

        if data_aman_p:
            # 2. UI FILTERS
            col1, col2 = st.columns([1, 2])
            with col1:
                # Karena Pitcher menghadapi lineup campuran, filter ini ibarat "Fokus Analisa Melawan Dominasi Lineup"
                lineup_lawan = st.radio("Dominasi Lineup Lawan:", ["vs LHB (Kidal)", "vs RHB (Kanan)"], horizontal=True, key="radio_lineup_t10")
            
            df_p = df_p_lhb if lineup_lawan == "vs LHB (Kidal)" else df_p_rhb

            if df_p.empty:
                st.warning("Data belum tersedia. Pastikan bot_updater.py sudah dieksekusi hari ini.")
            else:
                with col2:
                    # Deteksi otomatis nama kolom tim
                    kolom_tim = 'Team_Full' if 'Team_Full' in df_p.columns else ('Team' if 'Team' in df_p.columns else None)
                    
                    if kolom_tim:
                        daftar_tim = ['Semua Tim'] + sorted([t for t in df_p[kolom_tim].unique() if str(t) != 'nan' and str(t) != 'TBD'])
                        pilih_tim = st.selectbox("🔍 Filter Tim Pitcher:", daftar_tim, key="filter_tim_t10")
                    else:
                        st.info("⚠️ Kolom Tim tidak ditemukan di CSV.")
                        pilih_tim = 'Semua Tim'

                if pilih_tim != 'Semua Tim' and kolom_tim:
                    df_p = df_p[df_p[kolom_tim] == pilih_tim]

                # 3. THE PITCHER MATH ENGINE
                expected_pa = 22.5 # Rata-rata PA yang dihadapi Starting Pitcher per game

                # [AUTO-DETECT KOLOM YANG BERMUTASI / TIDAK BERMUTASI]
                ip_col = 'p_formatted_ip_Full' if 'p_formatted_ip_Full' in df_p.columns else 'p_formatted_ip'
                pa_full_col = 'pa_Full' if 'pa_Full' in df_p.columns else 'pa'
                hh_full_col = 'hard_hit_percent_Full' if 'hard_hit_percent_Full' in df_p.columns else 'hard_hit_percent'
                era_col = 'p_era_Full' if 'p_era_Full' in df_p.columns else 'p_era'

                # A. Konversi Inning Pitched (IP) ke Outs
                if ip_col in df_p.columns:
                    df_p['Outs_Full'] = np.floor(df_p[ip_col]) * 3 + np.round((df_p[ip_col] - np.floor(df_p[ip_col])) * 10)
                else:
                    df_p['Outs_Full'] = 150 # Fallback

                # Amankan dari pembagian dengan nol
                for col in [pa_full_col, 'pa_L60', 'xwoba_Full']:
                    if col in df_p.columns:
                        df_p[col] = df_p[col].replace(0, np.nan)

                # B. Proyeksi Outs (Berapa lama dia bertahan di mound)
                base_outs_rate = df_p['Outs_Full'] / df_p[pa_full_col]
                df_p['Proj_Outs'] = (base_outs_rate * expected_pa).fillna(15).round(1)

                # C. Proyeksi Strikeout (SO)
                df_p['Proj_SO'] = (((df_p['k_percent_L60'] / 100) + (df_p['swing_miss_percent'] / 100)) / 2 * expected_pa).fillna(0).round(2)

                # D. Proyeksi Hits Allowed
                base_hit_rate = df_p['hits'] / df_p['pa_L60']
                # Bandingkan HardHit form terkini dengan DNA Full Season
                if hh_full_col in df_p.columns and 'hardhit_percent' in df_p.columns:
                    power_surge_allowed = np.where(df_p['hardhit_percent'] > df_p[hh_full_col], 1.15, 0.90)
                else:
                    power_surge_allowed = 1.0
                df_p['Proj_Hit_Allowed'] = (base_hit_rate * power_surge_allowed * expected_pa).fillna(0).round(2)

                # E. Proyeksi Earned Runs (ER)
                if era_col in df_p.columns:
                    er_per_out = df_p[era_col] / 27 
                else:
                    er_per_out = 4.15 / 27 # Fallback rata-rata liga
                    
                xwoba_momentum = df_p['xwoba_L60'] / df_p['xwoba_Full']
                df_p['Proj_ER'] = (er_per_out * df_p['Proj_Outs'] * xwoba_momentum).fillna(0).round(2)

                # 4. RECOMMENDATION ENGINE (Prioritas Kiri -> Kanan)
                def get_pitcher_recommendation(row):
                    picks = []
                    
                    # 1. Outs Edge (Garis pasaran biasanya 17.5 atau 15.5)
                    if row['Proj_Outs'] >= 18.0: picks.append("🟢 O 17.5 Outs")
                    elif row['Proj_Outs'] <= 14.0: picks.append("🔴 U 15.5 Outs")
                        
                    # 2. Strikeout Edge (Garis pasaran 4.5 s/d 6.5)
                    if row['Proj_SO'] >= 6.8: picks.append("🟢 O 5.5 SO")
                    elif row['Proj_SO'] <= 3.5: picks.append("🔴 U 4.5 SO")
                        
                    # 3. Hits Allowed (Target FADE)
                    if row['Proj_Hit_Allowed'] >= 6.5: picks.append("🔴 O 5.5 Hits")
                    elif row['Proj_Hit_Allowed'] <= 3.5: picks.append("🟢 U 4.5 Hits")
                        
                    # 4. Earned Runs (Target FADE)
                    if row['Proj_ER'] >= 3.5: picks.append("🔴 O 2.5 ER (FADE!)")
                    elif row['Proj_ER'] <= 1.5: picks.append("🛡️ U 2.5 ER (ACE)")
                        
                    return " ┃ ".join(picks) if picks else "🟡 Pass Semua"

                df_p['🎯 Priority Picks (Kiri->Kanan)'] = df_p.apply(get_pitcher_recommendation, axis=1)

                # 5. RENDER TABEL FINAL
                display_cols = [
                    'player_name_std', 'Proj_Outs', 'Proj_SO', 'Proj_Hit_Allowed', 'Proj_ER', 
                    'xwoba_L60', 'hardhit_percent', '🎯 Priority Picks (Kiri->Kanan)'
                ]
                
                # Filter agar yang tampil hanya pitcher aktif (PA > 50), urutkan dari SO tertinggi
                df_clean_p = df_p[df_p['pa_Full'] >= 50][display_cols].sort_values(by='Proj_SO', ascending=False)
                
                df_clean_p.rename(columns={
                    'player_name_std': 'Pitcher Name',
                    'xwoba_L60': 'xwOBA Allw (L60)',
                    'hardhit_percent': 'HardHit% Allw'
                }, inplace=True)

                st.data_editor(df_clean_p, use_container_width=True, hide_index=True, disabled=True)
