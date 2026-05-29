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
    "🏭 Tab 4: SGP Factory", 
    "🔥 Tab 5: Live Report dan Hasil", 
    "🛡️ Tab 6: AI Auditor", 
    "🏪 Tab 7: Team Market", 
    "💸 Tab 9: Cross Parlay"
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
                
                # Filter pemain aktif di laga ini
                team_players = df_hitters[df_hitters['Team'].isin([game['away_team'], game['home_team']])]
                
                if team_players.empty:
                    st.caption(f"⚠️ Data statcast untuk tim {game['away_team']} / {game['home_team']} tidak ditemukan di 'master_hitter_2026.csv'.")
                    continue
                
                # Cek ketersediaan kolom kunci (antisipasi perbedaan nama kolom di CSV lu)
                if 'xwOBA_vs_R' in team_players.columns and 'Barrel_Pct' in team_players.columns:
                    best_hitters = team_players.sort_values(by=['xwOBA_vs_R', 'Barrel_Pct'], ascending=[False, False]).head(3)
                else:
                    best_hitters = team_players.head(3) # Fallback jika nama kolom beda
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 💣 SGP Home Run (2-3 Legs)")
                    hr_legs = []
                    
                    if 'Barrel_Pct' in best_hitters.columns and 'Max_EV' in best_hitters.columns:
                        for _, row in best_hitters.iterrows():
                            if row['Barrel_Pct'] >= 10.0 and row['Max_EV'] >= 108.0:
                                hr_legs.append(f"🔥 {row['Player']} ({row['Team']}) To Hit HR")
                        
                        if len(hr_legs) >= 2:
                            for leg in hr_legs:
                                st.markdown(f"- {leg}")
                            st.success("✅ SGP HR Valid")
                        else:
                            st.caption("Metrik Statcast kurang memenuhi syarat ketat untuk SGP HR.")
                    else:
                        st.caption("Kolom 'Barrel_Pct' atau 'Max_EV' tidak ditemukan di CSV.")

                with col2:
                    st.markdown("#### 📐 SGP Sniper Engine (Logika Berantai)")
                    if not best_hitters.empty:
                        top_hitter = best_hitters.iloc[0]
                        target_team = top_hitter['Team']
                        player_name = top_hitter.get('Player', 'Top Hitter')
                        opp_pitcher = game['home_pitcher'] if target_team == game['away_team'] else game['away_pitcher']
                        
                        st.markdown(f"**Narasi:** Serangan Domination oleh {target_team}")
                        st.markdown(f"- 🟢 **Leg 1:** {player_name} OVER 1.5 Total Bases")
                        st.markdown(f"- 🟢 **Leg 2:** {player_name} OVER 0.5 Runs/RBI")
                        st.markdown(f"- 🟢 **Leg 3:** {opp_pitcher} OVER 4.5 Hits Allowed")
                        st.markdown(f"- 🟢 **Leg 4:** {opp_pitcher} UNDER 17.5 Outs Recorded")

# ====================================================================
# 6. TAB 6: THE AI AUDITOR (Pusat Audit H-1)
# ====================================================================
with tabs[4]:
    st.header("🛡️ AI Auditor & ROI Tracker")
    st.caption("SOP: Membaca 'Kunci Jawaban' pertandingan kemarin dan menilai akurasi pasar.")
    
    if not yesterday_results:
        st.info("Menunggu data pertandingan H-1. Pastikan bot `bot_updater.py` berjalan via GitHub Actions.")
    else:
        st.success(f"✅ Data dari {len(yesterday_results)} pertandingan kemarin berhasil ditarik.")
        
        for g_id, g_data in yesterday_results.items():
            with st.container():
                st.markdown(f"### 📋 {g_data['matchup']}")
                total_runs = g_data['away_runs'] + g_data['home_runs']
                st.markdown(f"**Skor Akhir:** {g_data['away_runs']} - {g_data['home_runs']} (Total: {total_runs} Runs)")
                
                # Expandable Audit Boxscore
                with st.expander("🔎 Buka Log Statistik Individu (Hitter & Pitcher)"):
                    hitters_found = False
                    for p_name, p_stat in g_data['players'].items():
                        if 'tb' in p_stat and p_stat['tb'] > 0: # Hanya tampilkan batter yg nyetak stat
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
# 8. TAB 9: CROSS-GAME PARLAY AGGREGATOR
# ====================================================================
# ====================================================================
# 8. TAB 9: CROSS-GAME PARLAY & THE MASTER SLIPS
# ====================================================================
with tabs[6]:
    st.header("💸 Cross-Game Parlay & Master Slips")
    st.caption("SOP: Eksekusi tiket raksasa Lintas Pertandingan, Pitcher Props, dan Bomb Squad HR.")
    
    if len(today_schedule) < 2:
        st.info("Butuh minimal 2 laga berjalan hari ini untuk menyusun tiket Cross-Game.")
    else:
        # --- SLIP 1: SGPx BARU ---
        st.markdown("### 🎫 SLIP 1: MATCH SGPx (Lintas Match Combo)")
        st.caption("Kombinasi Logika Serangan dari 2 Match berbeda yang memiliki probabilitas tertinggi.")
        
        match1 = today_schedule[0]
        match2 = today_schedule[1]
        
        col1, col2 = st.columns(2)
        with col1:
            st.error(f"🔥 **LEG PART 1:** {match1['away_team']} vs {match1['home_team']}")
            st.markdown(f"1. {match1['home_team']} OVER 3.5 Total Runs")
            st.markdown(f"2. {match1['away_pitcher']} OVER 4.5 Hits Allowed")
            st.markdown(f"3. {match1['home_team']} Moneyline")
        with col2:
            st.info(f"🔥 **LEG PART 2:** {match2['away_team']} vs {match2['home_team']}")
            st.markdown(f"1. {match2['away_team']} To Hit A Home Run")
            st.markdown(f"2. {match2['home_pitcher']} UNDER 17.5 Outs Recorded")
            st.markdown(f"3. Total Match Runs OVER 7.5")
            
        st.divider()

    if len(today_schedule) < 2:
        st.info("Butuh minimal 2 laga berjalan hari ini untuk menyusun tiket Cross-Game.")
    else:
        # --- SLIP 2: MONSTER SGPx HR ---
        st.markdown("### 🎫 SLIP 2: MONSTER SGPx HR (2-3 Legs Lintas Match)")
        st.caption("Kombinasi persilangan murni kandidat Home Run paling mematikan dari 2-3 pertandingan berbeda. Hasil riset presisi mendalam dari Statcast.")
        
        match1 = today_schedule[0]
        match2 = today_schedule[1]
        
        # Deep research filter untuk match 1 & 2
        hitters_m1 = df_hitters[df_hitters['Team'].isin([match1['away_team'], match1['home_team']])] if not df_hitters.empty else pd.DataFrame()
        top_m1 = hitters_m1.sort_values(by=['Barrel_Pct', 'xwOBA_vs_R'], ascending=[False, False]).head(1) if not hitters_m1.empty and 'Barrel_Pct' in hitters_m1.columns else pd.DataFrame()
        
        hitters_m2 = df_hitters[df_hitters['Team'].isin([match2['away_team'], match2['home_team']])] if not df_hitters.empty else pd.DataFrame()
        top_m2 = hitters_m2.sort_values(by=['Barrel_Pct', 'xwOBA_vs_R'], ascending=[False, False]).head(1) if not hitters_m2.empty and 'Barrel_Pct' in hitters_m2.columns else pd.DataFrame()
        
        col1, col2 = st.columns(2)
        with col1:
            st.error(f"🔥 **LEG PART 1:** {match1['away_team']} vs {match1['home_team']}")
            if not top_m1.empty:
                p1 = top_m1.iloc[0]
                p_name = p1.get('Player', 'Top Hitter')
                st.markdown(f"1. **{p_name}** ({p1['Team']})")
                st.write(f"↳ *To Hit a Home Run (Barrel: {p1.get('Barrel_Pct', 0)}%)*")
            else:
                st.write("Data HR tidak memenuhi syarat ketat.")
                
        with col2:
            st.info(f"🔥 **LEG PART 2:** {match2['away_team']} vs {match2['home_team']}")
            if not top_m2.empty:
                p2 = top_m2.iloc[0]
                p_name = p2.get('Player', 'Top Hitter')
                st.markdown(f"1. **{p_name}** ({p2['Team']})")
                st.write(f"↳ *To Hit a Home Run (Barrel: {p2.get('Barrel_Pct', 0)}%)*")
            else:
                st.write("Data HR tidak memenuhi syarat ketat.")
                
        # Tambahan presisi untuk Leg 3 jika ada match ke-3 hari ini
        if len(today_schedule) > 2:
            match3 = today_schedule[2]
            hitters_m3 = df_hitters[df_hitters['Team'].isin([match3['away_team'], match3['home_team']])] if not df_hitters.empty else pd.DataFrame()
            top_m3 = hitters_m3.sort_values(by=['Barrel_Pct', 'xwOBA_vs_R'], ascending=[False, False]).head(1) if not hitters_m3.empty and 'Barrel_Pct' in hitters_m3.columns else pd.DataFrame()
            
            if not top_m3.empty:
                p3 = top_m3.iloc[0]
                p_name = p3.get('Player', 'Top Hitter')
                st.success(f"🔥 **OPTIONAL LEG 3:** {match3['away_team']} vs {match3['home_team']}")
                st.write(f"↳ **{p_name}** ({p3['Team']}) To Hit a Home Run (Barrel: {p3.get('Barrel_Pct', 0)}%)")
            
        st.divider()

        # --- SLIP 2: KEMBALINYA PITCHER PROPS ---
        st.markdown("### ⚾ SLIP 2: PITCHER PROPS PARLAY (K's / Outs / Hits Allowed)")
        st.caption("Mendeteksi peluang Pitcher berdasarkan metrik ERA musiman dari CSV 'master_pitcher_2026.csv'.")
        
        pitcher_list = []
        for game in today_schedule:
            era_away = get_pitcher_era(game['away_team'])
            era_home = get_pitcher_era(game['home_team'])
            
            pitcher_list.append({'Pitcher': game['away_pitcher'], 'Team': game['away_team'], 'Opp': game['home_team'], 'ERA': era_away})
            pitcher_list.append({'Pitcher': game['home_pitcher'], 'Team': game['home_team'], 'Opp': game['away_team'], 'ERA': era_home})
            
        df_today_p = pd.DataFrame(pitcher_list)
        
        if not df_today_p.empty:
            best_pitchers = df_today_p.sort_values('ERA', ascending=True).head(3)
            worst_pitchers = df_today_p.sort_values('ERA', ascending=False).head(3)
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.success("🎯 **TARGET OVER STRIKEOUTS / OUTS** (PITCHER ELIT)")
                for _, p in best_pitchers.iterrows():
                    if p['Pitcher'] != "TBD":
                        st.markdown(f"**{p['Pitcher']}** ({p['Team']}) ➔ ERA: {p['ERA']:.2f}")
                        st.write(f"↳ *Pick: OVER vs {p['Opp']}*")
                    
            with col4:
                st.warning("🩸 **TARGET OVER HITS ALLOWED** (PITCHER RENTAN)")
                for _, p in worst_pitchers.iterrows():
                    if p['Pitcher'] != "TBD":
                        st.markdown(f"**{p['Pitcher']}** ({p['Team']}) ➔ ERA: {p['ERA']:.2f}")
                        st.write(f"↳ *Pick: OVER vs {p['Opp']}*")
        else:
            st.caption("Data Pitcher belum siap untuk dikalkulasi.")
            
        st.divider()
        
        # --- PENCARIAN KANDIDAT BOMB SQUAD HR (LINTAS MATCH) ---
        st.markdown("### 💣 THE BOMB SQUAD (CROSS-GAME HR PARLAY)")
        st.caption("Sistem memindai seluruh laga hari ini untuk mencari Hitter dengan metrik Statcast tertinggi.")
        
        teams_playing_today = []
        for game in today_schedule:
            teams_playing_today.extend([game['away_team'], game['home_team']])
            
        today_hitters = df_hitters[df_hitters['Team'].isin(teams_playing_today)] if not df_hitters.empty else pd.DataFrame()
        
        if not today_hitters.empty and 'Barrel_Pct' in today_hitters.columns and 'xwOBA_vs_R' in today_hitters.columns:
            hr_candidates = today_hitters.sort_values(by=['Barrel_Pct', 'xwOBA_vs_R'], ascending=[False, False])
            
            col5, col6 = st.columns(2)
            
            # KUNCI LOGIKA: Ambil daftar nama top 5 pemain yang masuk Sniper & Lotto agar aman dieksklusi
            taken_players = hr_candidates.head(8)['Player'].tolist()
            
            with col5:
                st.error("🎯 **SLIP 3: SNIPER HR (2-3 Legs)**")
                st.caption("Probabilitas tertinggi. 3 Monster paling elit hari ini.")
                sniper_picks = hr_candidates.head(3)
                for i, row in sniper_picks.iterrows():
                    p_name = row.get('Player', 'Unknown Player')
                    st.markdown(f"🔥 **{p_name}** ({row['Team']})")
                    st.write(f"↳ *To Hit a HR (Barrel: {row['Barrel_Pct']}%)*")
                    
            with col6:
                st.info("🚀 **SLIP 4: LOTTO / LONGSHOT HR (5 Legs)**")
                st.caption("Tiket jackpot odds dewa. 5 Hitter teratas se-MLB hari ini.")
                lotto_picks = hr_candidates.head(5)
                for i, row in lotto_picks.iterrows():
                    p_name = row.get('Player', 'Unknown Player')
                    st.markdown(f"☄️ **{p_name}** ({row['Team']})")
                    st.write(f"↳ *To Hit a HR*")
            
            st.divider()
            
            # --- SLIP NEW: HOT HAND HR (3-5 LEGS) ---
            st.markdown("### 🔥 SLIP 5: HOT HAND HR (3-5 LEGS)")
            st.caption("SOP: Menyaring Hitter yang bersih dari daftar Sniper/Lotto, namun statistik performa 2 minggu terakhir (14D) sedang melonjak tajam.")
            
            # Buat filter pemisah (Pool dikurangi pemain yang sudah diambil di Slip 3 & 4)
            hot_hand_pool = today_hitters[~today_hitters['Player'].isin(taken_players)]
            
            if not hot_hand_pool.empty:
                # Membaca kolom tren dinamis di dalam CSV (misal: wOBA_14D, OPS_14D, atau sejenisnya)
                hot_hand_col = None
                for col in hot_hand_pool.columns:
                    if '14' in col or 'hot' in col.lower() or 'trend' in col.lower():
                        hot_hand_col = col
                        break
                
                # Sorting berdasarkan kolom tren yang ditemukan
                if hot_hand_col:
                    st.caption(f"📊 Metrik deteksi otomatis aktif menggunakan kolom tren: `{hot_hand_col}`")
                    hot_hand_candidates = hot_hand_pool.sort_values(by=hot_hand_col, ascending=False).head(4)
                else:
                    # Fallback jika di CSV belum ada kolom 14D khusus, mesin otomatis ambil lapis kedua (Tier 2) Statcast terkuat
                    st.caption("⚠️ Kolom tren '14D' tidak terdeteksi di CSV. Sistem mengaktifkan filter Lapis Kedua (Tier 2 Momentum Statcast).")
                    hot_hand_candidates = hot_hand_pool.sort_values(by=['xwOBA_vs_R', 'Barrel_Pct'], ascending=[False, False]).head(4)
                
                col_hh1, col_hh2 = st.columns(2)
                with col_hh1:
                    st.success("📈 **Rekomendasi Tiket Hot Hand HR (3-4 Legs)**")
                    for i, row in hot_hand_candidates.iterrows():
                        p_name = row.get('Player', 'Unknown Player')
                        st.markdown(f"⚡ **{p_name}** ({row['Team']})")
                        if hot_hand_col:
                            st.write(f"↳ *Status: On Fire ({hot_hand_col}: {row[hot_hand_col]})*")
                        else:
                            st.write(f"↳ *Status: High Value Tier-2 (Barrel: {row['Barrel_Pct']}%)*")
                with col_hh2:
                    st.info("💡 **Analisis Sistem**")
                    st.write("Daftar di atas murni berisi nama-nama alternatif. Mereka memiliki kecocokan pola ayunan yang sangat tajam dalam rentang waktu pendek belakangan ini tanpa terbebani harga pasar taruhan yang terlalu mahal.")
            else:
                st.caption("Jumlah pool pemain tidak mencukupi untuk membuat slip Hot Hand.")
                    
        else:
            st.caption("⚠️ Data metrik Hitter tidak mencukupi untuk memproses simulasi slip HR.")
            
        st.divider()

        # --- SLIP 6: MONEYLINE ---
        st.markdown("### 🎲 SLIP 6: VEGAS MONEYLINE TRIPLE THREAT")
        st.caption("Kombinasi 3 Tim Fav hari ini (Cek probabilitas di Tab 7).")
        # Ambil data dari tabel pasar yang sudah dihitung di Tab 7
        if 'market_rows' in locals() and len(market_rows) >= 5:
            # Kita bikin DataFrame sementara untuk sort probabilitas
            df_ml = pd.DataFrame(market_rows)
            # Karena format probabilitas di string, kita ekstraksi angkanya dulu
            # (Asumsi format: "TeamName (XX.X%)")
            df_ml['Prob'] = df_ml['🔥 Moneyline Pred'].str.extract(r'\((\d+\.?\d*)%\)').astype(float)
            
            # Ambil 3 tim teratas
            top_5_ml = df_ml.sort_values('Prob', ascending=False).head(5)
            
            st.info("👉 **RACIKAN TIKET OTOMATIS:**")
            ml_names = []
            for _, row in top_5_ml.iterrows():
                # Bersihkan string nama tim dari probabilitas
                team_name = row['🔥 Moneyline Pred'].split(' (')[0]
                ml_names.append(team_name)
                st.markdown(f"✅ **{team_name}** ({row['Prob']}%)")
            
            st.success(f"**Parlay 5 Leg:** { ' ✖️ '.join(ml_names) } ")
        else:
            st.info("Belum cukup data pertandingan untuk merakit Triple Threat ML hari ini.")
