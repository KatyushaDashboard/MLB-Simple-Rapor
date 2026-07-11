import math
import pandas as pd

def calculate_poisson_prob(expected_value, sportsbook_line):
    max_under = math.floor(sportsbook_line)
    prob_under = 0.0
    for k in range(max_under + 1):
        prob_k = (math.exp(-expected_value) * (expected_value ** k)) / math.factorial(k)
        prob_under += prob_k
    
    return {
        "expected": round(expected_value, 2),
        "prob_under": round(prob_under * 100, 2),
        "prob_over": round((1.0 - prob_under) * 100, 2)
    }

def generate_pitcher_predictions(pitcher_row, lineup_df, global_hitter_df):
    """
    Menghitung prediksi K, Outs, Hits, dan ER berdasarkan data RIIL dari DataFrame.
    """
    # ==========================================
    # 0. KALKULASI BASELINE (RATA-RATA LIGA) DARI CSV ANDA
    # ==========================================
    # Menghitung standar liga langsung dari seluruh pemain di dataset (bukan hardcode)
    league_avg_woba = global_hitter_df['xwOBA'].mean() if 'xwOBA' in global_hitter_df.columns else 0.315
    league_avg_bb_pct = global_hitter_df['BB%'].mean() if 'BB%' in global_hitter_df.columns else 8.5
    
    # ==========================================
    # 1. PREDIKSI OUTS & TBF (Total Batters Faced)
    # ==========================================
    ip = float(pitcher_row.get('IP', 0))
    gs = float(pitcher_row.get('GS', 0))
    
    # Rata-rata Inning per Start dari Pitcher ini
    avg_ip_per_start = ip / gs if gs > 0 else 5.0
    baseline_outs = avg_ip_per_start * 3
    
    # Menghitung kekuatan Lineup Lawan Hari Ini vs Rata-rata Liga
    lineup_avg_woba = lineup_df['woba_Full'].mean() if 'woba_Full' in lineup_df.columns else league_avg_woba
    lineup_avg_bb_pct = lineup_df['bb_percent_Full'].mean() if 'bb_percent_Full' in lineup_df.columns else league_avg_bb_pct
    
    # Penalty Multiplier (Jika lineup lebih jago dari rata-rata liga, penalti Pitcher Outs bertambah)
    woba_penalty = 1.0 - ((lineup_avg_woba - league_avg_woba) * 1.5)
    bb_penalty = 1.0 - ((lineup_avg_bb_pct - league_avg_bb_pct) / 100)
    
    pred_outs = max(9.0, baseline_outs * woba_penalty * bb_penalty) 
    
    # Kalkulasi rasio Batters Faced per Out dari data lineup lawan
    # (AVG liga 1.4, tapi kita sesuaikan dengan tingkat BB% lawan)
    tbf_ratio = 1.35 + (lineup_avg_bb_pct / 100)
    pred_tbf = pred_outs * tbf_ratio

    # ==========================================
    # 2. PREDIKSI STRIKEOUTS (K)
    # ==========================================
    k9 = float(pitcher_row.get('K/9', 0))
    
    # Mengonversi K/9 ke probabilitas persen (%) murni matematika
    # Rumus = (K/9) / (Estimasi Plate Appearances dalam 9 Inning)
    pitcher_k_pct = (k9 / (27 * tbf_ratio)) * 100
    
    # Menarik K% spesifik milik Hitter Lawan dari CSV Splits
    lineup_avg_k_pct = lineup_df['k_percent_Full'].mean() if 'k_percent_Full' in lineup_df.columns else 22.0
    
    # Prediksi K murni berdasarkan kekuatan matchup dikali jumlah pemukul yang dihadapi
    matchup_k_pct = (pitcher_k_pct + lineup_avg_k_pct) / 2
    pred_k = (matchup_k_pct / 100) * pred_tbf

    # ==========================================
    # 3. PREDIKSI HITS ALLOWED
    # ==========================================
    lineup_avg_ba = lineup_df['batting_avg'].mean() if 'batting_avg' in lineup_df.columns else 0.245
    
    # Bola yang aktif dipukul (Bukan K dan Bukan Walk)
    balls_in_play = pred_tbf - pred_k - (pred_tbf * (lineup_avg_bb_pct / 100))
    pred_hits = max(0.0, balls_in_play * lineup_avg_ba)

    # ==========================================
    # 4. PREDIKSI EARNED RUNS (ER)
    # ==========================================
    era = float(pitcher_row.get('ERA', 0))
    lineup_woba_l30 = lineup_df['woba_L30'].mean() if 'woba_L30' in lineup_df.columns else lineup_avg_woba
    
    # Form lineup lawan bulan ini dibandingkan standar liga
    form_multiplier = lineup_woba_l30 / league_avg_woba
    
    # (ERA / 9) / rasio base-runner menghasilkan ekspektasi ER per Batter murni
    base_er_per_batter = (era / 9) / 4 
    pred_er = pred_hits * base_er_per_batter * form_multiplier * 1.5

    return {
        "outs": pred_outs,
        "tbf": pred_tbf,
        "k": pred_k,
        "hits": pred_hits,
        "er": pred_er
    }
