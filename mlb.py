import streamlit as st
import pandas as pd
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
    try:
        df_hitters = pd.read_csv('master_hitter_2026.csv') 
    except FileNotFoundError:
        st.sidebar.error("⚠️ File 'master_hitter_2026.csv' tidak ditemukan.")
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
# 4. ENGINE BARU: THE MULTI-SCREEN SCORING MATRIX (UPGRADED ULXRARE)
# ====================================================================
@st.cache_data(ttl=600) # Gembok cache 10 menit biar dashboard lu ngebut kenceng!
def run_scoring_matrix(df, _df_pitchers, _team_to_opp_pitcher):
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

        # 🔥 F5: DETEKSI KELEMAHAN PITCHER LAWAN (+1 Poin)
        opp_pitcher_name = _team_to_opp_pitcher.get(team, 'TBD')
        if opp_pitcher_name != 'TBD' and not _df_pitchers.empty:
            pitcher_row = _df_pitchers[_df_pitchers['Name'] == opp_pitcher_name]
            if not pitcher_row.empty:
                opp_hr9 = pitcher_row['HR/9'].values[0] if 'HR/9' in pitcher_row.columns else 0.0
                opp_fb = pitcher_row['FB%'].values[0] if 'FB%' in pitcher_row.columns else 0.0
                
                # Jika Pitcher hobi lepas HR (>1.5) atau gampang kena Flyball (>40%)
                if opp_hr9 >= 1.5 or opp_fb >= 40.0: 
                    score += 1

        # DNA Tagging
        if score >= 4 and adj_xwoba >= 0.340: tipe = "🌟 SUPERSTAR (Core)"
        elif adj_barrel >= 7.5 and adj_xwoba < 0.330: tipe = "☄️ LONGSHOT (Boom/Bust)"
        else: tipe = "🎯 SOLID BAT"

        connection_scores.append(score)
        archetypes.append(tipe)

    df_matrix['Conn_Score'] = connection_scores
    df_matrix['Archetype'] = archetypes
    return df_matrix.sort_values(by='Conn_Score', ascending=False)

# Panggil fungsi dengan parameter baru
df_matrix_global = run_scoring_matrix(today_hitters, df_pitchers, team_to_opp_pitcher)

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
    "🕸️ Tab 8: Overlap Network"
])

with tabs[0]:
    st.subheader("Pitcher Metrics & Team Bullpen ERA Allowed")
    if not df_pitchers.empty:
        df_p_today = df_pitchers[df_pitchers['Team'].isin(playing_teams)].dropna(subset=['Team']).copy()
        if 'Bullpen_ERA' not in df_p_today.columns:
            df_p_today['Bullpen_ERA'] = df_p_today['Team'].apply(get_pitcher_era)
        st.dataframe(df_p_today.style.background_gradient(cmap='RdYlGn_r', subset=['Bullpen_ERA']) if 'Bullpen_ERA' in df_p_today.columns else df_p_today, use_container_width=True, height=500)
    else:
        st.warning("⚠️ Data Pitcher kosong.")

with tabs[1]:
    st.subheader("Hitter Advanced, Batting Order & Recent Form (14d)")
    if not df_hitters.empty:
        df_h_today = today_hitters.copy() if not today_hitters.empty else df_hitters[df_hitters['Team'].isin(playing_teams)].copy()
        if 'xwOBA_L14' not in df_h_today.columns: 
            df_h_today['xwOBA_L14'] = df_h_today.get('xwOBA', df_h_today.get('xwOBA_vs_R', 0.300))

        col1, col2 = st.columns(2)
        with col1: search_name = st.text_input("🔍 Ketik Nama Pemain:", "", key="tab2_s")
        with col2: sel_team = st.selectbox("Filter Tim:", ["Semua Tim"] + sorted(df_h_today['Team'].unique().tolist()), key="tab2_t")

        player_col = 'Name' if 'Name' in df_h_today.columns else ('Player' if 'Player' in df_h_today.columns else None)
        if player_col:
            display_df = df_h_today[df_h_today[player_col].str.contains(search_name, case=False, na=False)] if search_name else (df_h_today[df_h_today['Team'] == sel_team] if sel_team != "Semua Tim" else df_h_today.sort_values(by='xwOBA_L14', ascending=False).head(50))
            st.dataframe(display_df, use_container_width=True, height=500)
        else: st.error("❌ Kolom nama pemain tidak ditemukan.")
    else: st.warning("⚠️ Data Hitter kosong.")

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
with tabs[2]:
    st.header("🏭 Same Game Parlay (SGP) Factory")
    st.caption("SOP: Algoritma korelasi narasi untuk mencetak paket SGP anti-kontradiksi berbasis Connection Score.")

    if not isinstance(today_schedule, list) or not today_schedule:
        st.warning("Jadwal hari ini kosong atau bot belum menarik data jadwal.")
    elif 'df_matrix_global' not in locals() or df_matrix_global.empty:
        st.error("Database Hitter Matrix kosong. SGP Factory tidak bisa beroperasi.")
    else:
        for idx, game in enumerate(today_schedule):
            with st.expander(f"🎲 MATCH {idx+1}: {game['away_team']} @ {game['home_team']} | SP: {game['away_pitcher']} vs {game['home_pitcher']}"):

                # Tarik pemain dari Matrix Global yang udah mateng
                team_players = df_matrix_global[df_matrix_global['Team'].isin([game['away_team'], game['home_team']])]
                if team_players.empty:
                    st.caption(f"⚠️ Data statcast tim tidak ditemukan.")
                    continue

                # Sortir Prioritas: Connection Score tertinggi dulu, baru Adj_Barrel
                if 'Conn_Score' in team_players.columns and 'Adj_Barrel' in team_players.columns:
                    best_hitters = team_players.sort_values(by=['Conn_Score', 'Adj_Barrel'], ascending=[False, False]).head(3)
                else:
                    best_hitters = team_players.head(3)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### 💣 1. SGP Home Run (2-3 Legs)")
                    hr_legs = []
                    if 'Adj_Barrel' in best_hitters.columns and 'Max EV' in best_hitters.columns:
                        for _, row in best_hitters.iterrows():
                            # Kita kasih toleransi Barrel >= 8.0 buat SGP HR karena udah difilter Conn_Score
                            if row['Adj_Barrel'] >= 8.0 and row['Max EV'] >= 105.0:
                                p_name = row.get('Name', 'Unknown')
                                hr_legs.append(f"🔥 **{p_name}** ({row['Team']}) To Hit HR *(Conn: {row.get('Conn_Score',0)})*")

                        if len(hr_legs) >= 2:
                            for leg in hr_legs: 
                                st.markdown(f"- {leg}")
                            st.success("✅ SGP HR Valid (High Connection)")
                        else:
                            st.caption("Kandidat HR di match ini kurang solid untuk dirangkai jadi SGP HR murni.")
                    else:
                        st.caption("Data statcast tidak lengkap.")

                with col2:
                    st.markdown("#### 📐 2. SGP Sniper Engine")
                    if not best_hitters.empty:
                        top_hitter = best_hitters.iloc[0]
                        target_team = top_hitter['Team']
                        player_name = top_hitter.get('Name', 'Top Hitter')
                        opp_pitcher = game['home_pitcher'] if target_team == game['away_team'] else game['away_pitcher']

                        st.markdown(f"**Target Alpha:** {player_name} (DNA: {top_hitter.get('Archetype', 'Solid')} | Conn: {top_hitter.get('Conn_Score', 0)})")
                        st.markdown(f"- 🟢 **Leg 1:** {player_name} OVER 1.5 Total Bases")
                        st.markdown(f"- 🟢 **Leg 2:** {player_name} OVER 0.5 Runs/RBI")
                        st.markdown(f"- 🟢 **Leg 3:** {opp_pitcher} OVER 4.5 Hits Allowed")
                        st.markdown(f"- 🟢 **Leg 4:** {opp_pitcher} UNDER 17.5 Outs Recorded")

                st.divider()

                # --- SGP PITCHER DUEL (Original) ---
                st.markdown("#### ⚾ 3. SGP Pitcher Duel Props")
                p_away, p_home = game['away_pitcher'], game['home_pitcher']
                era_away, era_home = get_pitcher_era(game['away_team']), get_pitcher_era(game['home_team'])

                col3, col4 = st.columns(2)
                with col3:
                    st.markdown(f"**{game['away_team']} SP: {p_away}** (ERA: {era_away:.2f})")
                    if era_away < 4.00:
                        st.write(f"- 🟢 OVER Strikeouts / 🟢 OVER 15.5 Outs")
                    else:
                        st.write(f"- 🔴 OVER 4.5 Hits / 🔴 OVER 2.5 Earned Runs")
                with col4:
                    st.markdown(f"**{game['home_team']} SP: {p_home}** (ERA: {era_home:.2f})")
                    if era_home < 4.00:
                        st.write(f"- 🟢 OVER Strikeouts / 🟢 OVER 15.5 Outs")
                    else:
                        st.write(f"- 🔴 OVER 4.5 Hits / 🔴 OVER 2.5 Earned Runs")

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
    st.caption("SOP: Proyeksi Moneyline dan O/U menggunakan Pythagorean Expectation, SP xERA, dan Park Factor.")
    
    if isinstance(today_schedule, list) and not df_hitters.empty:
        market_rows = []
        for game in today_schedule:
            away_t = game['away_team']
            home_t = game['home_team']
            
            # 1. Ambil Kualitas Hitter (xwOBA)
            h_away = df_hitters[df_hitters['Team'] == away_t]
            h_home = df_hitters[df_hitters['Team'] == home_t]
            score_away = h_away['xwOBA_L14'].mean() if 'xwOBA_L14' in h_away.columns else (h_away['xwOBA'].mean() if not h_away.empty else 0.315)
            score_home = h_home['xwOBA_L14'].mean() if 'xwOBA_L14' in h_home.columns else (h_home['xwOBA'].mean() if not h_home.empty else 0.315)

            # 2. Ambil Kualitas Pitching (Pemisahan SP dan Bullpen)
            # Karena belum ada data spesifik per SP di JSON jadwal lu, kita pakai fallback pintar
            # Asumsi: get_pitcher_era mewakili ERA tim keseluruhan (Bullpen proxy)
            team_era_away = get_pitcher_era(away_t)
            team_era_home = get_pitcher_era(home_t)
            
            # Cari ERA SP spesifik dari df_pitchers jika ada
            sp_away_name = game.get('away_pitcher', 'TBD')
            sp_home_name = game.get('home_pitcher', 'TBD')
            
            sp_away_df = df_pitchers[df_pitchers['Name'] == sp_away_name] if not df_pitchers.empty else pd.DataFrame()
            sp_home_df = df_pitchers[df_pitchers['Name'] == sp_home_name] if not df_pitchers.empty else pd.DataFrame()
            
            sp_era_away = sp_away_df['ERA'].values[0] if not sp_away_df.empty else team_era_away
            sp_era_home = sp_home_df['ERA'].values[0] if not sp_home_df.empty else team_era_home
            
            # Bobot Pitching: 60% Starter, 40% Bullpen
            true_pitch_away = (sp_era_away * 0.6) + (team_era_away * 0.4)
            true_pitch_home = (sp_era_home * 0.6) + (team_era_home * 0.4)

            # 3. Faktor Lingkungan
            park_mult = PARK_FACTORS.get(home_t, 1.00)

            # 4. Proyeksi Runs (BaseRuns Logic)
            # Normalisasi rata-rata OBA liga = 0.315, rata-rata ERA = 4.10
            proj_r_a = (score_away / 0.315) * true_pitch_home * park_mult
            proj_r_home = (score_home / 0.315) * true_pitch_away * park_mult

            # 5. Pythagorean Win Probability (Eksponen 1.83 adalah standar MLB)
            pyth_away = (proj_r_a**1.83) / (proj_r_a**1.83 + proj_r_home**1.83)
            pyth_home = (proj_r_home**1.83) / (proj_r_a**1.83 + proj_r_home**1.83)
            
            win_prob_away = round(pyth_away * 100, 1)
            win_prob_home = round(pyth_home * 100, 1)
            
            if win_prob_away > win_prob_home:
                fav, dog, wp = away_t, home_t, win_prob_away
            else:
                fav, dog, wp = home_t, away_t, win_prob_home

            # 6. Rekomendasi Handicap (Runline)
            hc_rec = f"{fav} -1.5" if wp >= 58.0 else f"{dog} +1.5"
            
            market_rows.append({
                'Match': f"{away_t} (SP: {sp_away_name}) @ {home_t} (SP: {sp_home_name})", 
                '🔥 Moneyline Pred': f"{fav} ({wp}%)", 
                '📐 Runline': hc_rec, 
                '📊 Proj Total': round(proj_r_a + proj_r_home, 1),
                '📝 Run Splitz': f"{away_t} {round(proj_r_a, 1)} - {round(proj_r_home, 1)} {home_t}"
            })
            
        st.dataframe(pd.DataFrame(market_rows), hide_index=True, use_container_width=True)
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
        # 3. FITUR BARU: THE PITCHER MATRIX (SLIP 3)
        # ====================================================================
        st.markdown("### ⚾ SLIP 3: THE PITCHER MATRIX PARLAY")
        st.caption("Sistem klaster otomatis untuk pelempar bola berdasarkan ERA, Park Factor, dan Proyeksi Runs Musuh.")

        assassins, workhorses, gas_cans = [], [], []

        for game in today_schedule:
            home_t = game['home_team']
            away_t = game['away_team']
            park_mult = PARK_FACTORS.get(home_t, 1.00)

            # Evaluasi Away Pitcher
            era_away = get_pitcher_era(away_t)
            proj_runs_home = team_totals_data.get(home_t, 4.0) if isinstance(team_totals_data, dict) else 4.0
            if game['away_pitcher'] != "TBD":
                if era_away < 3.60 and park_mult < 1.02 and proj_runs_home < 4.0:
                    assassins.append((game['away_pitcher'], away_t, "OVER Strikeouts"))
                elif era_away < 4.00 and proj_runs_home < 5:
                    workhorses.append((game['away_pitcher'], away_t, "OVER Outs Recorded"))
                elif era_away > 4.60 and park_mult > 1.02 and proj_runs_home > 5:
                    gas_cans.append((game['away_pitcher'], away_t, "OVER Hits / Earned Runs Allowed"))

            # Evaluasi Home Pitcher
            era_home = get_pitcher_era(home_t)
            proj_runs_away = team_totals_data.get(away_t, 4.0) if isinstance(team_totals_data, dict) else 4.0
            if game['home_pitcher'] != "TBD":
                if era_home < 3.60 and park_mult < 1.02 and proj_runs_away < 4.0:
                    assassins.append((game['home_pitcher'], home_t, "OVER Strikeouts"))
                elif era_home < 4.00 and proj_runs_away < 5.0:
                    workhorses.append((game['home_pitcher'], home_t, "OVER Outs Recorded"))
                elif era_home > 4.60 and park_mult > 1.02 and proj_runs_away > 5.0:
                    gas_cans.append((game['home_pitcher'], home_t, "OVER Hits / Earned Runs Allowed"))

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.success("👑 **THE ASSASSINS (K's)**")
            for p, t, rec in assassins[:3]: st.write(f"- **{p}** ({t})\n  ↳ *{rec}*")
            if not assassins: st.caption("Kosong.")
        with col_p2:
            st.info("🛡️ **WORKHORSES (Outs)**")
            for p, t, rec in workhorses[:3]: st.write(f"- **{p}** ({t})\n  ↳ *{rec}*")
            if not workhorses: st.caption("Kosong.")
        with col_p3:
            st.error("🩸 **GAS CANS (Fade)**")
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
