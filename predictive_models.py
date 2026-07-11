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
    # Menggunakan kolom 'xwoba' dan 'bb_percent' yang riil ada di master_hitter_2026.csv
    league_avg_woba = global_hitter_df['xwoba'].mean() if 'xwoba' in global_hitter_df.columns else 0.315
    league_avg_bb_pct = global_hitter_df['bb_percent'].mean() if 'bb_percent' in global_hitter_df.columns else 8.5
    
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

    k9 = float(pitcher_row.get('K/9', 0))
    pitcher_k_pct = (k9 / (27 * tbf_ratio)) * 100
    lineup_avg_k_pct = lineup_df['k_percent_Full'].mean() if 'k_percent_Full' in lineup_df.columns else 22.0
    matchup_k_pct = (pitcher_k_pct + lineup_avg_k_pct) / 2
    pred_k = (matchup_k_pct / 100) * pred_tbf

    lineup_avg_ba = lineup_df['batting_avg'].mean() if 'batting_avg' in lineup_df.columns else 0.245
    balls_in_play = pred_tbf - pred_k - (pred_tbf * (lineup_avg_bb_pct / 100))
    pred_hits = max(0.0, balls_in_play * lineup_avg_ba)

    era = float(pitcher_row.get('ERA', 0))
    lineup_woba_l30 = lineup_df['woba_L30'].mean() if 'woba_L30' in lineup_df.columns else lineup_avg_woba
    form_multiplier = lineup_woba_l30 / league_avg_woba
    base_er_per_batter = (era / 9) / 4 
    pred_er = pred_hits * base_er_per_batter * form_multiplier * 1.5

    return {
        "outs": pred_outs,
        "tbf": pred_tbf,
        "k": pred_k,
        "hits": pred_hits,
        "er": pred_er
    }
