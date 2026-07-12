import math
import pandas as pd

def calculate_poisson_prob(expected_value, sportsbook_line):
    max_under = math.floor(sportsbook_line)
    prob_under = sum(
        (math.exp(-expected_value) * (expected_value ** k)) / math.factorial(k)
        for k in range(max_under + 1)
    )
    return {
        "expected": round(expected_value, 2),
        "prob_under": round(prob_under * 100, 2),
        "prob_over": round((1.0 - prob_under) * 100, 2)
    }

def generate_pitcher_predictions(pitcher_row, lineup_df, global_hitter_df):
    # Adaptasi nama kolom yang sudah di-rename oleh mlb.py Anda
    col_woba = 'xwOBA' if 'xwOBA' in global_hitter_df.columns else 'xwoba'
    col_bb = 'BB%' if 'BB%' in global_hitter_df.columns else 'bb_percent'
    
    league_avg_woba = global_hitter_df[col_woba].mean() if col_woba in global_hitter_df.columns else 0.315
    league_avg_bb_pct = global_hitter_df[col_bb].mean() if col_bb in global_hitter_df.columns else 8.5
    
    # 1. OUTS & TBF
    ip = float(pitcher_row.get('IP', 0))
    gs = float(pitcher_row.get('GS', 0))
    avg_ip_per_start = ip / gs if gs > 0 else 5.0
    baseline_outs = avg_ip_per_start * 3
    
    lineup_avg_woba = lineup_df['woba_Full'].mean() if 'woba_Full' in lineup_df.columns else league_avg_woba
    lineup_avg_bb_pct = lineup_df['bb_percent_Full'].mean() if 'bb_percent_Full' in lineup_df.columns else league_avg_bb_pct
    
    woba_penalty = 1.0 - ((lineup_avg_woba - league_avg_woba) * 1.5)
    bb_penalty = 1.0 - ((lineup_avg_bb_pct - league_avg_bb_pct) / 100)
    
    pred_outs = max(9.0, baseline_outs * woba_penalty * bb_penalty)
    tbf_ratio = 1.35 + (lineup_avg_bb_pct / 100)
    pred_tbf = pred_outs * tbf_ratio

    # 2. STRIKEOUTS (K)
    k9 = float(pitcher_row.get('K/9', 0))
    pitcher_k_pct = (k9 / (27 * tbf_ratio)) * 100
    lineup_avg_k_pct = lineup_df['k_percent_Full'].mean() if 'k_percent_Full' in lineup_df.columns else 22.0
    matchup_k_pct = (pitcher_k_pct + lineup_avg_k_pct) / 2
    pred_k = (matchup_k_pct / 100) * pred_tbf

    # 3. HITS ALLOWED
    lineup_avg_ba = lineup_df['batting_avg'].mean() if 'batting_avg' in lineup_df.columns else 0.245
    balls_in_play = pred_tbf - pred_k - (pred_tbf * (lineup_avg_bb_pct / 100))
    pred_hits = max(0.0, balls_in_play * lineup_avg_ba)

    # 4. EARNED RUNS (ER)
    era = float(pitcher_row.get('ERA', 0))
    # woba_L30 dipakai untuk form/momentum, jika tak ada gunakan woba_Full
    lineup_woba_form = lineup_df['woba_L30'].mean() if 'woba_L30' in lineup_df.columns else lineup_avg_woba
    form_multiplier = lineup_woba_form / league_avg_woba
    pred_er = pred_hits * ((era / 9) / 4) * form_multiplier * 1.5

    return {
        "outs": pred_outs,
        "tbf": pred_tbf,
        "k": pred_k,
        "hits": pred_hits,
        "er": pred_er
    }
