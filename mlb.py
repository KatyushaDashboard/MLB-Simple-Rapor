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

# ====================================================================
# 4. NAVIGASI TABS
# ====================================================================
tabs = st.tabs([
    "🎯 Tab 1: Sniper Pick", 
    "📊 Tab 2: Hitter Stats", 
    "🏭 Tab 4: SGP Factory", 
    "🔥 Tab 5: Golden HR", 
    "🛡️ Tab 6: AI Auditor", 
    "🏪 Tab 7: Team Market", 
    "💸 Tab 9: Cross Parlay"
])

# !!! PERHATIAN: PASTE KODE TAB 1, 2, 5 LAMA LU DI DALAM BLOK INI !!!
with tabs[0]:
    st.info("👇 PASTE KODE TAB 1 (SNIPER PICK) LAMA LU DI BAWAH INI 👇")
    # Paste kode lu di sini

with tabs[1]:
    st.info("👇 PASTE KODE TAB 2 (HITTER STATS) LAMA LU DI BAWAH INI 👇")
    # Paste kode lu di sini

with tabs[3]:
    st.info("👇 PASTE KODE TAB 5 (GOLDEN HR) LAMA LU DI BAWAH INI 👇")
    # Paste kode lu di sini


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
with tabs[6]:
    st.header("💸 Cross-Game Parlay & SGPx Aggregator")
    st.caption("SOP: Mengawinkan paket SGP terbaik dari tab 4 menjadi tiket raksasa Lintas Pertandingan.")
    
    if len(today_schedule) < 2:
        st.info("Butuh minimal 2 laga berjalan hari ini untuk menyusun tiket Cross-Game.")
    else:
        st.markdown("### 🎫 SLIP 1: MONSTER SGPx (Lintas Match Combo)")
        st.caption("Kombinasi Logika Serangan dari 2 Match berbeda yang memiliki proyeksi Run tertinggi.")
        
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
        st.markdown("### 🎲 SLIP 2: MONEYLINE TRIPLE THREAT")
        st.caption("Kombinasi 3 Tim dengan Win Probability paling mutlak hari ini (Tab 7).")
        st.info("1️⃣ Tim A ML  ✖️  2️⃣ Tim B ML  ✖️  3️⃣ Tim C ML  (Est. Odds +250)")
