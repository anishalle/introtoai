#!/usr/bin/env python3
"""
Phase 8: Offline training script for myTeam PARAMS.

Fits ridge regression models on collected training data to estimate
the impact of state features on future success (score_delta_k, died_within_k).
Uses the learned coefficients to adjust the PARAMS dictionary.

Usage:
  python3 train_weights.py --data training_data/training_data.csv
"""

import argparse
import os
import sys
import ast

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Feature names logged in collect_data.py
FEATURE_NAMES = [
    'carrying', 'returned', 'isPacman', 'posX', 'posY',
    'homeDist', 'foodLeft', 'foodDefending', 'movesLeft',
    'positionRisk', 'visibleThreatDist', 'invaderDist'
]

def load_csv(path):
    """Load CSV data into a list of dicts."""
    import csv
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def ridge_regression(X, y, lam=1.0):
    """Fit ridge regression: w = (X^T X + lambda*I)^-1 X^T y"""
    n_features = X.shape[1]
    XtX = X.T @ X + lam * np.eye(n_features)
    Xty = X.T @ y
    try:
        w = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(XtX, Xty, rcond=None)[0]
    return w

def extract_params_from_myteam(filepath):
    """Extract the PARAMS dict from myTeam.py using AST."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Simple text extraction for PARAMS dict to preserve comments and formatting
    start_marker = "PARAMS = {"
    end_marker = "}\n\n\ndef createTeam"
    
    if start_marker in content and end_marker in content:
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)
        dict_str = content[start_idx:end_idx + 1]
        
        # Parse into actual python dict
        try:
            # Safely evaluate the dictionary part
            clean_str = dict_str[dict_str.find('{'):]
            params = ast.literal_eval(clean_str)
            return params, content, start_idx, end_idx + 1
        except Exception as e:
            print(f"Error parsing PARAMS: {e}")
            
    print("Could not find PARAMS dict in myTeam.py")
    return None, content, -1, -1

def format_params(params):
    """Format PARAMS dict as pasteable Python code."""
    lines = ["PARAMS = {"]
    for k, v in params.items():
        if isinstance(v, bool):
            lines.append(f"  '{k}': {v},")
        elif isinstance(v, float):
            lines.append(f"  '{k}': {round(v, 3)},")
        else:
            lines.append(f"  '{k}': {v},")
    lines.append("}")
    return '\n'.join(lines)

def train_and_update(csv_path, myteam_path):
    """Train weights and update myTeam.py."""
    if not HAS_NUMPY:
        print("ERROR: numpy is required for training. Install with: pip install numpy")
        return

    rows = load_csv(csv_path)
    if not rows:
        print("No data found in CSV. Run collect_data.py first.")
        return

    print(f"Loaded {len(rows)} examples from {csv_path}")

    # Load current PARAMS
    params, content, start_idx, end_idx = extract_params_from_myteam(myteam_path)
    if params is None:
        return

    # Define feature mappings for each mode
    mode_configs = [
        {
            'name': 'Attack',
            'modes': ['attack'],
            'target_fn': lambda r: float(r.get('score_delta_k', '') or 0) - 4.0 * float(r.get('died_within_k', '') or 0) + 0.5 * float(r.get('food_eaten_k', '') or 0),
            'features': {
                'feat_distanceToTarget': 'target_distance_coeff',
                'feat_stop': 'stop_penalty',
                'feat_reverse': 'reverse_penalty',
                'feat_foodEaten': 'attack_food_eaten_bonus',
                'feat_foodReturned': 'attack_food_returned_bonus',
                'feat_risk': 'attack_risk_penalty',
                'feat_carryHomeDistance': 'attack_carry_home_penalty',
                'feat_laneMatch': 'attack_lane_bonus',
                'feat_visibleGhostDistance': 'feat_visible_ghost_dist',
                'feat_capsuleDistance': 'feat_capsule_dist',
                'feat_escapeRoutes': 'feat_escape_routes',
                'feat_deadEndFlag': 'feat_dead_end_flag',
                'feat_tripDeadline': 'feat_trip_deadline',
            }
        },
        {
            'name': 'Retreat',
            'modes': ['retreat'],
            'target_fn': lambda r: float(r.get('returned_food_k', '') or 0) - 3.0 * float(r.get('died_within_k', '') or 0),
            'features': {
                'feat_homeDistance': 'retreat_home_coeff',
                'feat_risk': 'retreat_risk_penalty',
                'feat_foodReturned': 'retreat_return_bonus',
                'feat_visibleGhostDistance': 'feat_visible_ghost_dist',
                'feat_capsuleDistance': 'feat_capsule_dist',
                'feat_escapeRoutes': 'feat_escape_routes',
                'feat_deadEndFlag': 'feat_dead_end_flag',
                'feat_tripDeadline': 'feat_trip_deadline',
            }
        },
        {
            'name': 'Defense',
            'modes': ['intercept', 'patrol'],
            'target_fn': lambda r: float(r.get('score_delta_k', '') or 0),
            'features': {
                'feat_invaderDistance': 'defense_invader_chase',
                'feat_stayGhost': 'defense_stay_ghost_bonus',
                'feat_becamePacman': 'defense_become_pacman_penalty',
                'feat_scaredContact': 'defense_scared_contact_penalty',
                'feat_eventDistance': 'feat_intercept_event_dist',
            }
        }
    ]

    alpha = 0.15  # Learning rate

    for config in mode_configs:
        mode_rows = [r for r in rows if r.get('mode') in config['modes']]
        if len(mode_rows) < 50:
            print(f"Skipping {config['name']} (only {len(mode_rows)} examples)")
            continue

        X_cols = list(config['features'].keys())
        X = np.zeros((len(mode_rows), len(X_cols)))
        for i, row in enumerate(mode_rows):
            for j, col in enumerate(X_cols):
                val = row.get(col, '')
                X[i, j] = float(val) if val != '' else 0

        y_vals = [config['target_fn'](r) for r in mode_rows]
        y = np.array(y_vals)

        std = X.std(axis=0)
        std[std == 0] = 1
        X_norm = (X - X.mean(axis=0)) / std
        w = ridge_regression(X_norm, y, lam=5.0)
        w_orig = w / std

        print(f"\n{config['name']} Model Weights:")
        for col, weight in zip(X_cols, w_orig):
            param_key = config['features'][col]
            if param_key in params:
                print(f"  {col} -> {param_key}: {weight:.3f}")
                params[param_key] += alpha * weight
            else:
                print(f"  {col} -> {param_key}: {weight:.3f} (Key not found in PARAMS!)")

    # 3. Write updated PARAMS back to myTeam.py
    new_params_str = format_params(params)
    new_content = content[:start_idx] + new_params_str + content[end_idx:]
    
    with open(myteam_path, 'w') as f:
        f.write(new_content)
        
    print(f"\nSuccessfully updated PARAMS in {myteam_path}")

def main():
    parser = argparse.ArgumentParser(description='Train myTeam PARAMS')
    parser.add_argument('--data', default='training_data/training_data.csv', help='Path to training CSV')
    parser.add_argument('--agent', default='myTeam.py', help='Path to myTeam.py')
    args = parser.parse_args()

    if os.path.exists(args.data):
        train_and_update(args.data, args.agent)
    else:
        print(f"Data file not found: {args.data}")
        print("Run: python3 collect_data.py --games 50 first")

if __name__ == '__main__':
    main()
