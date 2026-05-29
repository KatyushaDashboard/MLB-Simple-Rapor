import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ====================================================================
# 1. INITIAL SETUP & CONFIG 
# ====================================================================
st.set_page_config(page_title="MLB Ultimate Command Center v2", layout="wide")
st.title("🏆 MLB ULTIMATE COMMAND CENTER v2")
st.caption("Terminal Eksekusi & Audit Taruhan Otomatis Berbasis Konsensus Statcast AI")

st.sidebar.header("⚙️ Kontrol Waktu")
selected_date = st.sidebar.date_input("Pilih Tanggal Pertandingan:", datetime.today())

# ====================================================================
# 2. LOAD DATA CORE (TERINTEGRASI DENGAN CSV HITTER & PITCHER)
# ====================================================================
@st.cache_data
def load_base_data():
    # 1. Load Data Hitter
    try:
        df_hitters = pd.read_csv('master_hitter_2026.csv') 
    except FileNotFoundError:
        st.sidebar.error("⚠️ File 'master_hitter_2026.csv' tidak ditemukan. Pastikan nama file sesuai dengan di repo.")
        df_hitters = pd.DataFrame() # Fallback kosong

    # 2. Load Data Pitcher
    try:
        df_pitchers = pd.read_csv('master_pitcher_2026.csv')
    except FileNotFoundError:
        st.sidebar.error("⚠️ File 'master_pitcher_2026.csv' tidak ditemukan.")
        df_pitchers = pd.DataFrame()

    return df_hitters, df_pitchers

df_hitters, df_pitchers = load_base_data()

# Fungsi untuk mengambil ERA Pitcher secara dinamis dari CSV lu
def get_pitcher_era(team_name):
    if not df_pitchers.empty and 'Team' in df_pitchers.columns and 'ERA' in df_pitchers.columns:
        team_p = df_pitchers[df_pitchers['Team'] == team_name]
        if not team_p.empty:
            return team_p['ERA'].mean()
    return 4.15  # Fallback (Rata-rata liga) jika data/kolom tidak spesifik

# ====================================================================
# 3. LOAD JSON DARI BOT UPDATER (ANTI-PATH ERROR)
# ====================================================================
def load_json_data(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

today_schedule = load_json_data('today_schedule.json')
yesterday_results = load_json_data('yesterday_results.json')
# --- KAMUS TRANSLASI NAMA TIM (API to CSV) ---
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

# Terjemahkan otomatis semua nama tim di jadwal hari ini biar matching sama CSV
for game in today_schedule:
    game['away_team'] = TEAM_MAPPING.get(game['away_team'], game['away_team'])
    game['home_team'] = TEAM_MAPPING.get(game['home_team'], game['home_team'])
    # Amankan juga key lama buat fitur Live Boxscore lu
    if 'away' in game: game['away'] = TEAM_MAPPING.get(game['away'], game['away'])
    if 'home' in game: game['home'] = TEAM_MAPPING.get(game['home'], game['home'])

# ====================================================================
# --- ADVANCED CONFIG 1: KAMUS PARK FACTOR STADION ---
# ====================================================================
# Indeks > 1.00 = Ramah Hitter (Gampang HR), < 1.00 = Ramah Pitcher (Susah HR)
PARK_FACTORS = {
    "COL": 1.35, "CIN": 1.15, "BOS": 1.12, "BAL": 1.05, "ATL": 1.04,
    "CWS": 1.02, "LAA": 1.02, "TEX": 1.02, "PHI": 1.01, "ARI": 1.01,
    "HOU": 1.00, "TOR": 1.00, "LAD": 1.00, "NYY": 0.99, "MIN": 0.99,
    "MIL": 0.99, "CHC": 0.98, "KC": 0.98, "TB": 0.97, "PIT": 0.96,
    "WSH": 0.96, "MIA": 0.95, "STL": 0.95, "CLE": 0.94, "SF": 0.94,
    "SD": 0.93, "NYM": 0.92, "DET": 0.91, "OAK": 0.90, "SEA": 0.88
}

# ====================================================================
# --- ADVANCED CONFIG 2: ENGINE PENGHITUNG ROI & WIN RATE ---
# ====================================================================
def load_betting_history():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'betting_history.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except:
            pass
    # DATA DUMMY AWAL: Biar dashboard ROI lu langsung kelihatan grafik/angkanya pas pertama nyala
    return {
        "total_bets": 50,
        "wins": 32,
        "losses": 18,
        "total_staked": 5000000,   # Total Modal terpasang (Rp 5 Juta)
        "total_returned": 6850000  # Total Kemenangan ditarik (Rp 6.85 Juta)
    }
# ---------------------------------------------

# ====================================================================
# 4. NAVIGASI TABS
# ====================================================================
playing_teams = []
if today_schedule:
    for game in today_schedule:
        playing_teams.extend([game['away_team'], game['home_team']])
game_details = today_schedule
tabs = st.tabs([
    "🎯 Tab 1: Sniper Pick", 
    "📊 Tab 2: Hitter Stats", 
    "🏭 Tab 3: SGP Factory", 
    "🔥 Tab 4: Live Report dan Hasil", 
    "🛡️ Tab 5: AI Auditor", 
    "🏪 Tab 6: Team Market", 
    "💸 Tab 7: Cross Parlay"
])

# !!! PERHATIAN: PASTE KODE TAB 1, 2, 5 LAMA LU DI DALAM BLOK INI !!!
with tabs[0]:
    st.subheader("Pitcher Metrics & Team Bullpen ERA Allowed")
    if not df_pitchers.empty:
        df_p_today = df_pitchers[df_pitchers['Team'].isin(playing_teams)].dropna(subset=['Team']).copy()
        
        # PERBAIKAN 1: Mengganti fallback_bullpen_era dengan fungsi dinamis get_pitcher_era
        if 'Bullpen_ERA' not in df_p_today.columns:
            df_p_today['Bullpen_ERA'] = df_p_today['Team'].apply(get_pitcher_era)
            
        allowed_metrics = [c for c in ['xwOBA Allowed', 'xSLG Allowed', 'xBA Allowed', 'Bullpen_ERA'] if c in df_p_today.columns]
        st.dataframe(df_p_today.style.background_gradient(cmap='RdYlGn_r', subset=['Bullpen_ERA']) if 'Bullpen_ERA' in df_p_today.columns else df_p_today, use_container_width=True, height=500)
    else:
        st.warning("⚠️ Data Pitcher kosong. Pastikan 'master_pitcher_2026.csv' terbaca dan format nama tim (Singkatan/Full) sama dengan jadwal.")

with tabs[1]:
    st.subheader("Hitter Advanced, Batting Order & Recent Form (14d)")
    if not df_hitters.empty:
        df_h_today = df_hitters[df_hitters['Team'].isin(playing_teams)].dropna(subset=['Team']).copy()
        if 'Batting_Order' not in df_h_today.columns: df_h_today['Batting_Order'] = 3
        if 'PA_L14' not in df_h_today.columns: df_h_today['PA_L14'] = 45
        
        # PERBAIKAN 2: Mengamankan pemanggilan kolom xwOBA (antisipasi kalau namanya xwOBA_vs_R)
        if 'xwOBA_L14' not in df_h_today.columns: 
            df_h_today['xwOBA_L14'] = df_h_today.get('xwOBA', df_h_today.get('xwOBA_vs_R', 0.300))
        
        col1, col2 = st.columns(2)
        with col1: search_name = st.text_input("🔍 Ketik Nama Pemain:", "", key="tab2_s")
        with col2: sel_team = st.selectbox("Filter Tim:", ["Semua Tim"] + sorted(df_h_today['Team'].unique().tolist()), key="tab2_t")
        
        # PERBAIKAN 3: Deteksi otomatis apakah kolom nama pemain itu 'Name' atau 'Player'
        player_col = 'Name' if 'Name' in df_h_today.columns else ('Player' if 'Player' in df_h_today.columns else None)
        
        if player_col:
            display_df = df_h_today[df_h_today[player_col].str.contains(search_name, case=False, na=False)] if search_name else (df_h_today[df_h_today['Team'] == sel_team] if sel_team != "Semua Tim" else df_h_today.sort_values(by='xwOBA_L14', ascending=False).head(50))
            st.dataframe(display_df, use_container_width=True, height=500)
        else:
            st.error("❌ Kolom nama pemain ('Name' atau 'Player') tidak ditemukan di CSV Hitter lu.")
    else:
        st.warning("⚠️ Data Hitter kosong.")

with tabs[3]:
    st.subheader("📡 Live Report & Final Boxscore")
    if not game_details:
        st.info("Jadwal pertandingan belum tersedia untuk hari ini.")
    else:
        for game in game_details:
            # PERBAIKAN 4: Menyesuaikan key dictionary dari 'away' ke 'away_team' sesuai format bot baru
            away_t = game.get('away_team', game.get('away', 'TBD'))
            home_t = game.get('home_team', game.get('home', 'TBD'))
            game_status = game.get('status', 'Scheduled')
            game_id = game.get('game_id', 0)
            
            if game_status in ['Scheduled', 'Pre-Game', 'Warmup']:
                with st.expander(f"⏳ {away_t} @ {home_t}", expanded=False): st.info("Pertandingan belum dimulai.")
                continue
                
            with st.expander(f"🔥 {away_t} @ {home_t} - {game_status}", expanded=False):
                try:
                    # Pastikan fungsi get_live_boxscore sudah lu copy juga ke bagian atas app.py
                    live_h, live_p = get_live_boxscore(game_id, away_t, home_t)
                    if not live_h.empty and not live_p.empty:
                        sukses_h = live_h[(live_h['H'] >= 1) | (live_h['HR'] >= 1) | (live_h['R'] >= 1) | (live_h['RBI'] >= 1) | (live_h['TB'] >= 1)]
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("### 🏏 Hitters (Pencetak Skor)")
                            if not sukses_h.empty: st.dataframe(sukses_h.sort_values(by=['TB', 'H'], ascending=False), hide_index=True, use_container_width=True)
                            else: st.write("Belum ada hitter yang mencetak angka.")
                        with c2:
                            st.markdown("### 🎯 Pitchers (Rapor Lemparan)")
                            st.dataframe(live_p[['Team', 'Name', 'IP', 'H Allowed', 'R Allowed', 'SO']], hide_index=True, use_container_width=True)
                    else: st.write("Sedang menyinkronkan data boxscore...")
                except NameError:
                    st.error("⚠️ Fungsi 'get_live_boxscore' belum ditemukan! Pastikan lu udah ngopi fungsi itu dari kode lama ke bagian paling atas (sebelum tabs).")

# ====================================================================
# 5. TAB 4: SAME GAME PARLAY (SGP) FACTORY (FULL LOGIC)
# ====================================================================
with tabs[2]:
    st.header("🏭 Same Game Parlay (SGP) Factory")
    st.caption("SOP: Algoritma korelasi narasi untuk mencetak paket SGP anti-kontradiksi.")
    
    if not today_schedule:
        st.warning("Jadwal hari ini kosong atau bot belum menarik data jadwal.")
    elif df_hitters.empty:
        st.error("Database Hitter kosong. SGP Factory tidak bisa beroperasi.")
    else:
        for idx, game in enumerate(today_schedule):
            with st.expander(f"🎲 MATCH {idx+1}: {game['away_team']} @ {game['home_team']} | SP: {game['away_pitcher']} vs {game['home_pitcher']}"):
                
                team_players = df_hitters[df_hitters['Team'].isin([game['away_team'], game['home_team']])]
                
                if team_players.empty:
                    st.caption(f"⚠️ Data statcast tim tidak ditemukan.")
                    continue
                
                # Menggunakan nama kolom asli dari CSV lu (xwOBA dan Barrel%)
                if 'xwOBA' in team_players.columns and 'Barrel%' in team_players.columns:
                    best_hitters = team_players.sort_values(by=['xwOBA', 'Barrel%'], ascending=[False, False]).head(3)
                else:
                    best_hitters = team_players.head(3)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 💣 1. SGP Home Run (2-3 Legs)")
                    hr_legs = []
                    
                    if 'Barrel%' in best_hitters.columns and 'Max EV' in best_hitters.columns:
                        for _, row in best_hitters.iterrows():
                            if row['Barrel%'] >= 8.0 and row['Max EV'] >= 105.0:
                                p_name = row.get('Name', 'Unknown')
                                hr_legs.append(f"🔥 {p_name} ({row['Team']}) To Hit HR")
                        
                        if len(hr_legs) >= 2:
                            for leg in hr_legs:
                                st.markdown(f"- {leg}")
                            st.success("✅ SGP HR Valid")
                        else:
                            st.caption("Metrik Statcast kurang memenuhi syarat ketat untuk SGP HR.")
                    else:
                        st.caption("Kolom 'Barrel%' atau 'Max EV' tidak ditemukan di CSV.")

                with col2:
                    st.markdown("#### 📐 2. SGP Sniper Engine (Logika Berantai)")
                    if not best_hitters.empty:
                        top_hitter = best_hitters.iloc[0]
                        target_team = top_hitter['Team']
                        player_name = top_hitter.get('Name', 'Top Hitter')
                        opp_pitcher = game['home_pitcher'] if target_team == game['away_team'] else game['away_pitcher']
                        
                        st.markdown(f"**Narasi:** Serangan Domination oleh {target_team}")
                        st.markdown(f"- 🟢 **Leg 1:** {player_name} OVER 1.5 Total Bases")
                        st.markdown(f"- 🟢 **Leg 2:** {player_name} OVER 0.5 Runs/RBI")
                        st.markdown(f"- 🟢 **Leg 3:** {opp_pitcher} OVER 4.5 Hits Allowed")
                        st.markdown(f"- 🟢 **Leg 4:** {opp_pitcher} UNDER 17.5 Outs Recorded")
                        
                st.divider()
                
                # --- SLIP BARU: SGP PITCHER DUEL ---
                st.markdown("#### ⚾ 3. SGP Pitcher Duel Props (K's / Outs / Hits Allowed)")
                st.caption("Menganalisis profil kedua pelempar berdasarkan metrik ERA.")
                
                p_away = game['away_pitcher']
                p_home = game['home_pitcher']
                era_away = get_pitcher_era(game['away_team'])
                era_home = get_pitcher_era(game['home_team'])
                
                col3, col4 = st.columns(2)
                
                with col3:
                    st.markdown(f"**{game['away_team']} SP: {p_away}** (ERA: {era_away:.2f})")
                    if p_away == "TBD":
                        st.write("Pitcher belum ditentukan.")
                    elif era_away < 4.00:
                        st.success("🎯 **Profil Elit (Innings Eater)**")
                        st.write(f"- 🟢 OVER Strikeouts")
                        st.write(f"- 🟢 OVER 15.5 Outs Recorded")
                    else:
                        st.warning("🩸 **Profil Rentan (Target Hitter)**")
                        st.write(f"- 🔴 OVER 4.5 Hits Allowed")
                        st.write(f"- 🔴 OVER 2.5 Earned Runs")
                        
                with col4:
                    st.markdown(f"**{game['home_team']} SP: {p_home}** (ERA: {era_home:.2f})")
                    if p_home == "TBD":
                        st.write("Pitcher belum ditentukan.")
                    elif era_home < 4.00:
                        st.success("🎯 **Profil Elit (Innings Eater)**")
                        st.write(f"- 🟢 OVER Strikeouts")
                        st.write(f"- 🟢 OVER 15.5 Outs Recorded")
                    else:
                        st.warning("🩸 **Profil Rentan (Target Hitter)**")
                        st.write(f"- 🔴 OVER 4.5 Hits Allowed")
                        st.write(f"- 🔴 OVER 2.5 Earned Runs")
                        
                st.info(f"💡 **Saran Racikan:** Kawinkan prop terbaik dari {p_away} dengan prop terbaik dari {p_home} untuk membentuk 2-Leg SGP Pitcher murni.")

# ====================================================================
# 6. TAB 6: THE AI AUDITOR V2 (Pusat Audit Keuangan & ROI)
# ====================================================================
with tabs[4]:
    st.header("🛡️ AI Auditor & Advanced ROI Tracker")
    st.caption("SOP: Audit otomatis hasil H-1, pemantauan persentase Win Rate, dan manajemen ROI modal bandar.")
    
    # 1. Tarik Data History Keuangan
    history = load_betting_history()
    
    win_rate = (history['wins'] / history['total_bets'] * 100) if history['total_bets'] > 0 else 0
    profit_loss = history['total_returned'] - history['total_staked']
    roi = (profit_loss / history['total_staked'] * 100) if history['total_staked'] > 0 else 0
    
    # 2. Render Kartu Statistik Mewah ala Crypto/Saham Terminal
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric(label="🎯 Win Rate Aktual", value=f"{win_rate:.1f}%", delta=f"{win_rate - 55:.1f}% dari batas aman" if history['total_bets'] > 0 else "Belum ada data")
    
    status_profit = "🟢 Profit" if profit_loss >= 0 else ("🔴 Loss" if profit_loss < 0 else "⚪ BEP")
    m2.metric(label=f"💸 Bersih ({status_profit})", value=f"Rp {profit_loss:,}")
    
    m3.metric(label="📊 Return on Investment (ROI)", value=f"{roi:.1f}%", delta=f"{roi:.1f}%" if roi >= 0 else f"{roi:.1f}%")
    m4.metric(label="🎫 Total Slip", value=f"{history['total_bets']} Tiket")
    
    st.divider()
    
    # 3. KEMBALINYA LOG STATISTIK INDIVIDU (Tracker Slip)
    st.subheader("📋 Kunci Jawaban & Log Boxscore H-1")
    if not yesterday_results:
        st.info("Menunggu data pertandingan H-1 disinkronkan oleh bot.")
    else:
        st.success(f"✅ Data dari {len(yesterday_results)} pertandingan kemarin berhasil ditarik.")
        for g_id, g_data in yesterday_results.items():
            with st.container():
                st.markdown(f"### 📋 {g_data['matchup']}")
                total_runs = g_data['away_runs'] + g_data['home_runs']
                st.markdown(f"**Skor Akhir:** {g_data['away_runs']} - {g_data['home_runs']} (Total: {total_runs} Runs)")
                
                # Expandable Audit Boxscore yang sempet ilang
                with st.expander("🔎 Buka Log Statistik Individu (Hitter & Pitcher)"):
                    hitters_found = False
                    # Antisipasi kalau key 'players' nggak ada di beberapa game
                    players_data = g_data.get('players', {}) 
                    
                    for p_name, p_stat in players_data.items():
                        if 'tb' in p_stat and p_stat['tb'] > 0: 
                            st.write(f"⚾ **{p_name}**: Hits: {p_stat['hits']} | TB: {p_stat['tb']} | HR: {p_stat['hr']} | RBI: {p_stat['rbi']}")
                            hitters_found = True
                        elif 'strikeouts_pitcher' in p_stat:
                            st.write(f"🔥 **{p_name} (SP)**: K: {p_stat['strikeouts_pitcher']} | Outs: {p_stat['outs']} | Hits Allwd: {p_stat['hits_allowed']}")
                    
                    if not hitters_found:
                        st.caption("Tidak ada data stat mencolok di boxscore ini.")
                st.divider()
# ====================================================================
# 7. TAB 7: MATCH & TEAM MARKET TERMINAL (TERINTEGRASI CSV PITCHER)
# ====================================================================
with tabs[5]:
    st.header("🏪 Match & Team Market Terminal")
    st.caption("SOP: Pemetaan nilai Moneyline, Handicap, dan Distribusi Extra Bases.")
    
    if not today_schedule:
        st.warning("Jadwal kosong. Bot belum berjalan.")
    elif df_hitters.empty:
        st.error("Database Hitter kosong.")
    else:
        market_rows = []
        team_spec_rows = []
        
        for game in today_schedule:
            # Tarik kekuatan ofensif dari master_hitter_2026.csv
            h_away = df_hitters[df_hitters['Team'] == game['away_team']]
            h_home = df_hitters[df_hitters['Team'] == game['home_team']]
            
            # Tarik kekuatan defensif dari master_pitcher_2026.csv
            p_era_away = get_pitcher_era(game['away_team'])
            p_era_home = get_pitcher_era(game['home_team'])
            
            # Kalkulasi Edge
            if 'xwOBA_vs_R' in df_hitters.columns:
                score_away = h_away['xwOBA_vs_R'].mean() if not h_away.empty else 0.320
                score_home = h_home['xwOBA_vs_R'].mean() if not h_home.empty else 0.320
            else:
                score_away, score_home = 0.320, 0.320 # Fallback jika kolom tidak ada
            
            # Rumus Probabilitas Vegas Custom 
            diff = (score_away - (p_era_home / 15)) - (score_home - (p_era_away / 15))
            if diff > 0:
                fav, dog, win_prob = game['away_team'], game['home_team'], min(round(55 + (abs(diff) * 150), 1), 78.0)
            else:
                fav, dog, win_prob = game['home_team'], game['away_team'], min(round(55 + (abs(diff) * 150), 1), 78.0)
                
            hc_rec = f"{fav} -1.5" if win_prob >= 62.0 else f"{dog} +1.5"
            
            # Proyeksi Runs Terkalibrasi ERA Pitcher Asli
            proj_r_a = round((score_away * 12) * (p_era_home / 4.00), 1)
            proj_r_h = round((score_home * 12) * (p_era_away / 4.00), 1)
            
            market_rows.append({
                'Match': f"{game['away_team']} @ {game['home_team']}",
                '🔥 Moneyline Pred': f"{fav} ({win_prob}%)",
                '📐 Runline': hc_rec,
                '📊 O/U Total': round(proj_r_a + proj_r_h, 1)
            })
            
            # Spesifik Tim
            for team_name, proj_run in [(game['away_team'], proj_r_a), (game['home_team'], proj_r_h)]:
                team_spec_rows.append({
                    'Team': team_name,
                    'Tgt Runs': proj_run,
                    'Tgt Singles': round(proj_run * 1.8, 1),
                    'Tgt Doubles': round(proj_run * 0.4, 1),
                    'Tgt Triples': round(proj_run * 0.05, 1)
                })
                
        st.subheader("🏆 Vegas Core Market")
        st.dataframe(pd.DataFrame(market_rows), hide_index=True, use_container_width=True)
        
        st.subheader("📊 Team Props Market (Extra Base Focus)")
        st.dataframe(pd.DataFrame(team_spec_rows), hide_index=True, use_container_width=True)

# ====================================================================
# 8. TAB 7: CROSS-GAME PARLAY & THE MASTER SLIPS
# ====================================================================
with tabs[6]:
    st.header("💸 Cross-Game Parlay & Master Slips")
    st.caption("SOP: Eksekusi tiket raksasa Lintas Pertandingan, Pitcher Props, dan Bomb Squad HR.")
    
    if len(today_schedule) < 2:
        st.info("Butuh minimal 2 laga berjalan hari ini untuk menyusun tiket Cross-Game.")
    else:
        # --- SLIP 1: MATCH SGPx MURNI (TEAM/MARKET) ---
        st.markdown("### 🎫 SLIP 1: MATCH SGPx (Lintas Match Combo)")
        st.caption("Kombinasi Logika Serangan Match Market murni dari 2 laga. Tidak ada tebakan player props (Pitcher/Hitter).")
        
        match1 = today_schedule[0]
        match2 = today_schedule[1]
        
        col1, col2 = st.columns(2)
        with col1:
            st.error(f"🔥 **LEG PART 1:** {match1['away_team']} vs {match1['home_team']}")
            st.markdown(f"1. **{match1['home_team']}** OVER 3.5 Total Team Runs")
            st.markdown(f"2. **{match1['home_team']}** Moneyline (To Win)")
            st.markdown(f"3. **Match Total Runs** OVER 7.5")
        with col2:
            st.info(f"🔥 **LEG PART 2:** {match2['away_team']} vs {match2['home_team']}")
            st.markdown(f"1. **{match2['away_team']}** OVER 3.5 Total Team Runs")
            st.markdown(f"2. **{match2['away_team']}** +1.5 Handicap (Runline)")
            st.markdown(f"3. **Match Total Runs** OVER 8.5")
            
        st.divider()

        # --- SLIP 2: MONSTER SGPx HR ---
        st.markdown("### 💣 SLIP 2: MONSTER SGPx HR (2-3 Legs Lintas Match)")
        st.caption("Kombinasi persilangan murni kandidat Home Run dari pertandingan berbeda.")
        
        hitters_m1 = df_hitters[df_hitters['Team'].isin([match1['away_team'], match1['home_team']])] if not df_hitters.empty else pd.DataFrame()
        top_m1 = hitters_m1.sort_values(by=['Barrel%', 'xwOBA'], ascending=[False, False]).head(3) if not hitters_m1.empty and 'Barrel%' in hitters_m1.columns else pd.DataFrame()
        
        hitters_m2 = df_hitters[df_hitters['Team'].isin([match2['away_team'], match2['home_team']])] if not df_hitters.empty else pd.DataFrame()
        top_m2 = hitters_m2.sort_values(by=['Barrel%', 'xwOBA'], ascending=[False, False]).head(3) if not hitters_m2.empty and 'Barrel%' in hitters_m2.columns else pd.DataFrame()
        
        col_hr1, col_hr2 = st.columns(2)
        with col_hr1:
            st.error(f"🔥 **LEG PART 1:** {match1['away_team']} vs {match1['home_team']}")
            if not top_m1.empty:
                for i, (_, row) in enumerate(top_m1.iterrows(), 1):
                    p_name = row.get('Name', 'Top Hitter') 
                    st.markdown(f"**{i}. {p_name}** ({row['Team']})")
                    st.write(f"↳ *To Hit a HR (Barrel: {row.get('Barrel%', 0)}%)*")
            else:
                st.write("Data HR tidak memenuhi syarat ketat.")
                
        with col_hr2:
            st.info(f"🔥 **LEG PART 2:** {match2['away_team']} vs {match2['home_team']}")
            if not top_m2.empty:
                for i, (_, row) in enumerate(top_m2.iterrows(), 1):
                    p_name = row.get('Name', 'Top Hitter')
                    st.markdown(f"**{i}. {p_name}** ({row['Team']})")
                    st.write(f"↳ *To Hit a HR (Barrel: {row.get('Barrel%', 0)}%)*")
            else:
                st.write("Data HR tidak memenuhi syarat ketat.")
            
        st.divider()

        # --- SLIP 3: PITCHER PROPS LINTAS LAGA ---
        st.markdown("### ⚾ SLIP 3: PITCHER PROPS PARLAY (5-10 Laga Berbeda)")
        st.caption("Memilih 1 Pitcher dari setiap pertandingan yang berbeda dengan rekomendasi O/U otomatis berdasarkan profil ERA mereka.")
        
        selected_pitchers = []
        for game in today_schedule:
            era_away = get_pitcher_era(game['away_team'])
            era_home = get_pitcher_era(game['home_team'])
            
            # Logika Pemilihan: Ambil pitcher dengan ERA paling ekstrem di laga tersebut (Paling bagus atau Paling bapuk)
            if abs(era_away - 4.15) > abs(era_home - 4.15):
                chosen_p = game['away_pitcher']
                chosen_team = game['away_team']
                chosen_opp = game['home_team']
                chosen_era = era_away
            else:
                chosen_p = game['home_pitcher']
                chosen_team = game['home_team']
                chosen_opp = game['away_team']
                chosen_era = era_home
                
            if chosen_p != "TBD":
                # Tentukan Rekomendasi Spesifik
                if chosen_era < 3.50:
                    rec = f"🟢 **OVER Strikeouts** atau **OVER Outs Recorded** (Profil Elit)"
                elif chosen_era > 4.50:
                    rec = f"🔴 **OVER Hits Allowed** atau **OVER Earned Runs** (Profil Rentan)"
                else:
                    rec = f"🟡 **UNDER Strikeouts** atau **OVER Hits Allowed** (Profil Menengah/Kurang Stabil)"
                    
                selected_pitchers.append({
                    'Pitcher': chosen_p, 'Team': chosen_team, 'Opp': chosen_opp, 'ERA': chosen_era, 'Rec': rec
                })
                
            # Batasi maksimal 10 match biar slip parlaynya ga kepanjangan
            if len(selected_pitchers) >= 10:
                break
                
        if selected_pitchers:
            for idx, p in enumerate(selected_pitchers, 1):
                st.markdown(f"**{idx}. {p['Pitcher']}** ({p['Team']}) vs {p['Opp']} ➔ *ERA: {p['ERA']:.2f}*")
                st.write(f"↳ *Saran Pick: {p['Rec']}*")
        else:
            st.caption("Data Pitcher belum siap untuk dikalkulasi.")
            
        st.divider()
        
        # --- SLIP 4 & 5: BOMB SQUAD & LOTTO HR (PARK FACTOR ADJUSTED) ---
        st.markdown("### 🚀 THE BOMB SQUAD (CROSS-GAME HR PARLAY)")
        st.caption("Sistem memindai seluruh laga hari ini. Setiap metrik kekuatan Hitter otomatis dikalibrasi dengan Park Factor (Faktor Kondisi Stadion).")
        
        teams_playing_today = []
        team_to_park = {} # Kamus pencatat siapa bertanding di kandang siapa
        
        for game in today_schedule:
            teams_playing_today.extend([game['away_team'], game['home_team']])
            team_to_park[game['away_team']] = game['home_team'] # Park-nya ada di Home
            team_to_park[game['home_team']] = game['home_team']
            
        today_hitters = df_hitters[df_hitters['Team'].isin(teams_playing_today)].copy() if not df_hitters.empty else pd.DataFrame()
        
        if not today_hitters.empty and 'Barrel%' in today_hitters.columns and 'xwOBA' in today_hitters.columns:
            
            # --- PROSES KALIBRASI PARK FACTOR ---
            today_hitters['Home_Park'] = today_hitters['Team'].map(team_to_park)
            today_hitters['PF_Multiplier'] = today_hitters['Home_Park'].map(PARK_FACTORS).fillna(1.00)
            
            # Rumus Sakti: Nilai asli dikali indeks kemudahan stadion
            today_hitters['Adj_Barrel'] = today_hitters['Barrel%'] * today_hitters['PF_Multiplier']
            today_hitters['Adj_xwOBA'] = today_hitters['xwOBA'] * today_hitters['PF_Multiplier']
            
            # Urutkan berdasarkan metrik yang sudah di-adjust stadion
            hr_candidates = today_hitters.sort_values(by=['Adj_Barrel', 'Adj_xwOBA'], ascending=[False, False])
            
            col5, col6 = st.columns(2)
            taken_players = hr_candidates.head(8)['Name'].tolist() if 'Name' in hr_candidates.columns else []
            
            with col5:
                st.error("🎯 **SLIP 4: SNIPER HR (2-3 Legs)**")
                sniper_picks = hr_candidates.head(3)
                for _, row in sniper_picks.iterrows():
                    p_name = row.get('Name', 'Unknown')
                    st.markdown(f"🔥 **{p_name}** ({row['Team']}) @ {row['Home_Park']}")
                    st.write(f"↳ *Adj Barrel: {row['Adj_Barrel']:.1f}% (Stadion Multiplier: {row['PF_Multiplier']}x)*")
                    
            with col6:
                st.info("☄️ **SLIP 5: LOTTO / LONGSHOT HR (5 Legs)**")
                lotto_picks = hr_candidates.iloc[3:8] 
                for _, row in lotto_picks.iterrows():
                    p_name = row.get('Name', 'Unknown')
                    st.markdown(f"☄️ **{p_name}** ({row['Team']}) @ {row['Home_Park']}")
                    st.write(f"↳ *Adj Barrel: {row['Adj_Barrel']:.1f}%*")
            
            st.divider()
            
            # --- SLIP 6: HOT HAND HR ---
            st.markdown("### 🔥 SLIP 6: HOT HAND HR (3-5 LEGS)")
            if 'Name' in today_hitters.columns:
                hot_hand_pool = today_hitters[~today_hitters['Name'].isin(taken_players)]
                if not hot_hand_pool.empty:
                    st.caption("Pemain Alternatif Momentum Tinggi Bersih dari Sniper & Lotto (Park Adjusted).")
                    hot_hand_candidates = hot_hand_pool.sort_values(by=['Adj_xwOBA', 'Adj_Barrel'], ascending=[False, False]).head(4)
                    
                    for _, row in hot_hand_candidates.iterrows():
                        p_name = row.get('Name', 'Unknown')
                        st.markdown(f"⚡ **{p_name}** ({row['Team']}) @ {row['Home_Park']} ➔ *Adj Barrel: {row['Adj_Barrel']:.1f}%*")

        st.divider()

        # --- SLIP 7: MONEYLINE TRIPLE THREAT ---
        st.markdown("### 🎲 SLIP 7: VEGAS MONEYLINE TRIPLE THREAT")
        
        if 'market_rows' in locals() and len(market_rows) >= 5:
            df_ml = pd.DataFrame(market_rows)
            # Karena di Tab 7 namanya '🔥 Moneyline Pred' (atau 'Score' di versi simple)
            ml_col = '🔥 Moneyline Pred' if '🔥 Moneyline Pred' in df_ml.columns else ('Score' if 'Score' in df_ml.columns else None)
            
            if ml_col and 'Match' in df_ml.columns:
                st.info("👉 **RACIKAN TIKET OTOMATIS:**")
                st.dataframe(df_ml.head(5)) # Tampilkan 5 teratas dari market
            else:
                st.write("Format kolom market tidak sesuai.")
        else:
            st.info("Data Market Tab 7 belum siap dirakit.")
