import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

# ====================================================================
# 1. INITIAL SETUP & CONFIG (OPTIMIZED FOR INFINIX NOTE 40 VIEW)
# ====================================================================
st.set_page_config(page_title="MLB Ultimate Command Center v2", layout="wide")
st.title("🏆 MLB ULTIMATE COMMAND CENTER v2")
st.caption("Terminal Eksekusi & Audit Taruhan Otomatis Berbasis Konsensus Statcast AI")

# Load Data Core (Asumsi file CSV utama lu sudah ada di repo)
@st.cache_data
def load_base_data():
    # Mock data / Ganti dengan load CSV asli lu: pd.read_csv('your_data.csv')
    df_hitters = pd.DataFrame({
        'Team': ['NYY', 'LAD', 'HOU', 'ATL', 'CHC', 'BOS', 'SD'],
        'Player': ['Aaron Judge', 'Shohei Ohtani', 'Yordan Alvarez', 'Ronald Acuna', 'Cody Bellinger', 'Rafael Devers', 'Manny Machado'],
        'xwOBA_vs_R': [0.420, 0.410, 0.395, 0.385, 0.340, 0.365, 0.350],
        'xSLG': [0.610, 0.590, 0.560, 0.540, 0.460, 0.510, 0.480],
        'Max_EV': [118.4, 119.2, 116.7, 115.3, 111.2, 114.1, 112.9],
        'Barrel_Pct': [22.1, 19.8, 17.5, 15.2, 10.5, 13.8, 11.4]
    })
    fallback_bullpen_era = {'NYY': 3.20, 'LAD': 3.45, 'HOU': 3.80, 'ATL': 3.10, 'CHC': 4.15, 'BOS': 4.50, 'SD': 3.90}
    return df_hitters, fallback_bullpen_era

df_hitters, fallback_bullpen_era = load_base_data()

# Load Data hasil bot_updater.py (Diperbaiki Path-nya)
def load_json_data(filename):
    # Dapatkan letak folder asli tempat app.py ini berada
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    file_path = os.path.join(base_dir, filename)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error(f"⚠️ File {filename} rusak atau format JSON salah.")
            return []
    else:
        st.warning(f"⚠️ File {filename} tidak ditemukan di path: {file_path}")
        return []

today_schedule = load_json_data('today_schedule.json')
yesterday_results = load_json_data('yesterday_results.json')

today_schedule = load_json_data('today_schedule.json')
yesterday_results = load_json_data('yesterday_results.json')

# ====================================================================
# 2. NAVIGASI TABS BARU (Disederhanakan & Fokus Eksekusi)
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

# --- DUMMY LAYOUT UNTUK TAB 1, 2, 5 (Biar codingan lu yang lama ga keganggu) ---
with tabs[0]:
    st.info("Tab 1: Sniper Engine Aktif (Menggunakan database utama lu).")
with tabs[1]:
    st.info("Tab 2: Visualisasi Tren Statcast Hitter Aktif.")
with tabs[3]:
    st.info("Tab 5: Golden Standard HR & Lotto Momentum Aktif.")

# ====================================================================
# 3. TAB 4: SAME GAME PARLAY (SGP) FACTORY
# ====================================================================
with tabs[2]:
    st.header("🏭 Same Game Parlay (SGP) Factory")
    st.caption("SOP: Memproduksi paket SGP per match secara otomatis berdasarkan Logika Korelasi Narasi (Anti-Kontradiksi).")
    
    if not today_schedule:
        st.warning("Jadwal hari ini belum tersedia atau robot belum berjalan.")
    else:
        for idx, game in enumerate(today_schedule):
            with st.expander(f"🎲 MATCH {idx+1}: {game['away_team']} vs {game['home_team']} (SP: {game['away_pitcher']} vs {game['home_pitcher']})"):
                
                # Filter pemain dari tim yang bertanding
                team_players = df_hitters[df_hitters['Team'].isin([game['away_team'], game['home_team']])]
                
                # --- LOGIKA KORELASI NARASI SGP ---
                # Cari pemukul terbaik untuk opsi OVER
                best_hitters = team_players.sort_values(by='xwOBA_vs_R', ascending=False).head(3)
                
                st.markdown("#### 💣 1. SGP Home Run Special (2-3 Legs)")
                hr_legs = []
                for _, row in best_hitters.head(2).iterrows():
                    if row['Barrel_Pct'] >= 11.0:
                        hr_legs.append(f"🔥 {row['Player']} (Tim {row['Team']}) To Hit A Home Run")
                
                if len(hr_legs) >= 2:
                    st.success(" ➔ ORKESTRASI SLIP SGP HR:")
                    for leg in hr_legs:
                        st.markdown(f"- {leg}")
                else:
                    st.caption("⚠️ Metrik Statcast kurang mencukupi untuk membuat paket SGP HR di laga ini.")
                
                st.markdown("#### 📐 2. SGP Sniper Engine (2-8 Legs Lintas Pasar)")
                # Narasi dibangun: Jika Hitter Diunggulkan, Pitcher lawan kena imbas (Over Hit Allowed)
                if not best_hitters.empty:
                    top_hitter = best_hitters.iloc[0]
                    target_team = top_hitter['Team']
                    opp_team = game['home_team'] if target_team == game['away_team'] else game['away_team']
                    opp_pitcher = game['home_pitcher'] if target_team == game['away_team'] else game['away_pitcher']
                    
                    st.info(f"📋 **Alur Narasi Terpilih:** Serangan Domination oleh {target_team} menghadapi {opp_pitcher}")
                    
                    st.markdown(f"- 🟢 **Leg 1:** {top_hitter['Player']} OVER 1.5 Total Bases (xwOBA: {top_hitter['xwOBA_vs_R']})")
                    st.markdown(f"- 🟢 **Leg 2:** {top_hitter['Player']} OVER 0.5 Runs Scored / RBI")
                    st.markdown(f"- 🟢 **Leg 3:** Pelempar {opp_pitcher} ({opp_team}) OVER 4.5 Hits Allowed")
                    st.markdown(f"- 🟢 **Leg 4:** Pelempar {opp_pitcher} ({opp_team}) UNDER 17.5 Total Outs Recorded")
                else:
                    st.caption("Data statcast tim tidak ditemukan.")

# ====================================================================
# 4. TAB 6: THE AI AUDITOR (Pusat Penilaian Otomatis H-1)
# ====================================================================
with tabs[4]:
    st.header("🛡️ AI Auditor & ROI Tracker")
    st.caption("SOP: Membuka 'Kunci Jawaban' dari API MLB kemarin dan mengaudit otomatis keakuratan rekomendasi mesin.")
    
    if not yesterday_results:
        st.info("Hari ini belum ada data audit. Data akan muncul otomatis setelah bot_updater.py merampungkan laga kemarin.")
    else:
        st.success("✅ Database Hasil Pertandingan Kemarin Berhasil Dimuat.")
        
        # Ringkasan Makro Audit
        total_games_audited = len(yesterday_results)
        st.metric(label="Total Pertandingan Berhasil Diaudit", value=total_games_audited)
        
        # Tampilkan boxscore hasil audit per laga
        for g_id, g_data in yesterday_results.items():
            with st.container():
                st.markdown(f"### 📋 Matchup: {g_data['matchup']}")
                st.markdown(f"**Skor Akhir:** {g_data['away_runs']} - {g_data['home_runs']}")
                
                # Contoh simulasi audit otomatis match market
                st.markdown("**Status Audit Makro (Tab 7):**")
                # Logika sederhana membandingkan prediksi vs realita
                if g_data['away_runs'] + g_data['home_runs'] > 8:
                    st.write("📈 Pasaran Total Match Runs ➔ 🔴 *LOSS* (Prediksi Under, Hasil Over)")
                else:
                    st.write("📈 Pasaran Total Match Runs ➔ 🟢 *WIN* (Prediksi Under, Hasil Under)")
                
                # Tampilkan data performa pemain yang dicatat kemarin
                with st.expander("🔎 Lihat Rapor Statistik Player Terkait"):
                    for p_name, p_stat in g_data['players'].items():
                        if 'tb' in p_stat: # Batter
                            st.write(f"⚾ **{p_name}**: Hits: {p_stat['hits']} | TB: {p_stat['tb']} | HR: {p_stat['hr']} | RBI: {p_stat['rbi']}")
                        else: # Pitcher
                            st.write(f"🔥 **{p_name} (SP)**: K: {p_stat['strikeouts_pitcher']} | Outs: {p_stat['outs']} | Hits Allowed: {p_stat['hits_allowed']}")
                st.markdown("---")

# ====================================================================
# 5. TAB 7: MATCH & TEAM MARKET TERMINAL
# ====================================================================
with tabs[5]:
    st.header("🏪 Match & Team Market Terminal")
    st.caption("SOP: Memetakan bursa taruhan utama Moneyline, Handicap, dan Proyeksi Pasar Spesifik Hit Tim (Single/Double/Triple).")
    
    if not today_schedule:
        st.warning("Tidak ada jadwal pasar yang bisa diproyeksikan hari ini.")
    else:
        market_rows = []
        team_spec_rows = []
        
        for game in today_schedule:
            # Tarik data hit pangkat tim
            h_away = df_hitters[df_hitters['Team'] == game['away_team']]
            h_home = df_hitters[df_hitters['Team'] == game['home_team']]
            
            b_era_away = fallback_bullpen_era.get(game['away_team'], 4.15)
            b_era_home = fallback_bullpen_era.get(game['home_team'], 4.15)
            
            score_away = h_away['xwOBA_vs_R'].mean() if not h_away.empty else 0.300
            score_home = h_home['xwOBA_vs_R'].mean() if not h_home.empty else 0.300
            
            # Perhitungan Baku Moneyline & Handicap
            diff = (score_away - (b_era_home / 15)) - (score_home - (b_era_away / 15))
            if diff > 0:
                fav_team, dog_team, win_prob = game['away_team'], game['home_team'], min(round(55 + (abs(diff) * 150), 1), 78.0)
            else:
                fav_team, dog_team, win_prob = game['home_team'], game['away_team'], min(round(55 + (abs(diff) * 150), 1), 78.0)
                
            hc_rec = f"{fav_team} -1.5" if win_prob >= 60.0 and b_era_home >= 4.00 else f"{dog_team} +1.5"
            
            # Proyeksi Total Runs
            proj_r_a = round((score_away * 12) * (b_era_home / 4.00), 1)
            proj_r_h = round((score_home * 12) * (b_era_away / 4.00), 1)
            total_match_runs = round(proj_r_a + proj_r_h, 1)
            
            # Masukkan ke tabel utama
            market_rows.append({
                'Pertandingan': f"{game['away_team']} @ {game['home_team']}",
                '🔮 Moneyline (Win Prob)': f"{fav_team} ({win_prob}%)",
                'Spread / Runline': hc_rec,
                '📊 Proyeksi Total O/U': total_match_runs
            })
            
            # Pembuatan Pasar Spesifik Tim (Singles, Doubles, Triples)
            team_spec_rows.append({
                'Nama Tim': game['away_team'],
                '📐 Proyeksi Singles': round(proj_r_a * 1.8, 1),
                '📐 Proyeksi Doubles': round(proj_r_a * 0.4, 1),
                '📐 Proyeksi Triples': round(proj_r_a * 0.05, 1)
            })
            team_spec_rows.append({
                'Nama Tim': game['home_team'],
                '📐 Proyeksi Singles': round(proj_r_h * 1.8, 1),
                '📐 Proyeksi Doubles': round(proj_r_h * 0.4, 1),
                '📐 Proyeksi Triples': round(proj_r_h * 0.05, 1)
            })
            
        st.subheader("🏆 1. Core Match Market (ML, Runline, O/U)")
        st.dataframe(pd.DataFrame(market_rows), hide_index=True, use_container_width=True)
        
        st.subheader("📊 2. Team Hits Market Spec (Singles / Doubles / Triples)")
        st.dataframe(pd.DataFrame(team_spec_rows), hide_index=True, use_container_width=True)

# ====================================================================
# 6. TAB 9: CROSS-GAME PARLAY AGGREGATOR
# ====================================================================
with tabs[6]:
    st.header("💸 Cross-Game Parlay & SGPx Aggregator")
    st.caption("SOP: Mengambil paket SGP terbaik dari pabrik Tab 4 lalu mengawinkannya menjadi tiket raksasa Lintas Pertandingan.")
    
    if len(today_schedule) < 2:
        st.info("Butuh minimal 2 pertandingan berjalan hari ini untuk merakit tiket Cross-Game Parlay.")
    else:
        st.markdown("### 🏆 SLIP 1: HIGH-VALUE SGPx (Lintas Match Combo)")
        st.caption("Kombinasi SGP Sniper Match 1 dan SGP Home Run Match 2 dengan probabilitas hit tertinggi.")
        
        match1 = today_schedule[0]
        match2 = today_schedule[1]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**🔥 LEG PART 1 ({match1['away_team']} @ {match1['home_team']})**")
            st.markdown(f"- Opsi: *SGP Sniper Pack*")
            st.write(f"1. {match1['away_pitcher']} OVER 4.5 Hits Allowed")
            st.write(f"2. {match1['home_team']} OVER 3.5 Total Runs")
        with col2:
            st.markdown(f"**🔥 LEG PART 2 ({match2['away_team']} @ {match2['home_team']})**")
            st.markdown(f"- Opsi: *SGP HR Power Pack*")
            # Ambil sampel hitter top
            st.write(f"1. Pemukul Elit To Hit A Home Run 🚀")
            st.write(f"2. Total Match Runs OVER 7.5")
            
        st.markdown("---")
        st.markdown("### 🎲 SLIP 2: VEGAS SLATE MATRIX (Moneyline Combo)")
        st.caption("Menyatukan 3 tim terkuat hari ini berdasarkan Win Probability tertinggi di Tab 7.")
        st.info("👉 Racikan Tiket: Tim Fav 1 ML x Tim Fav 2 ML x Tim Fav 3 ML (Estimasi Odds: +240)")
