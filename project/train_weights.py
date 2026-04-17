#!/usr/bin/env python3
"""
Phase 8: Lightweight offline training script for myTeam weights.

Fits ridge regression models on collected training data to produce
optimized weight dictionaries for offensive and defensive modes.

Uses only numpy (no sklearn, no torch).

Usage:
  python3 train_weights.py --data training_data/training_data.csv
  python3 train_weights.py --data training_data/training_data.csv --output learned_weights.py
  python3 train_weights.py --defaults
"""

import argparse
import os
import sys

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# Feature names matching myTeam.py
FEATURE_NAMES = [
    'successorScore', 'foodEaten', 'capsuleEaten', 'foodCarried',
    'targetDistance', 'foodDistance', 'homeDistance', 'ghostDistance',
    'ghostScared', 'capsuleDistance', 'escapeRoutes', 'inDeadEnd',
    'threatPressure', 'deadEndRisk', 'timePressure', 'patrolDistance',
    'lostFoodDistance', 'stop', 'reverse', 'died', 'returnedFood',
    'onDefense', 'numVisibleInvaders', 'invaderDistance',
    'scoreDiff', 'oscillation', 'dangerZone', 'tunnelEntryRisk',
    'chokepointCoverage', 'noisyInvaderDist', 'teammateProximity',
]

MODES = ['attack', 'return', 'defend', 'patrol', 'capsule']

OFFENSIVE_MODES = {'attack', 'return', 'capsule'}
DEFENSIVE_MODES = {'defend', 'patrol'}


def load_csv(path):
    """Load CSV data into a list of dicts."""
    import csv
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def ridge_regression(X, y, lam=0.1):
    """Fit ridge regression: w = (X^T X + lambda*I)^-1 X^T y"""
    n_features = X.shape[1]
    XtX = X.T @ X + lam * np.eye(n_features)
    Xty = X.T @ y
    try:
        w = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(XtX, Xty, rcond=None)[0]
    return w


def train_from_csv(csv_path, output_path):
    """Train weights from collected CSV data."""
    if not HAS_NUMPY:
        print("ERROR: numpy is required for training. Install with: pip install numpy")
        return

    rows = load_csv(csv_path)
    if not rows:
        print("No data found in CSV. Run collect_data.py first.")
        return

    print(f"Loaded {len(rows)} examples from {csv_path}")

    learned = {}
    for mode in MODES:
        mode_rows = [r for r in rows if r.get('mode', '') == mode]
        if len(mode_rows) < 20:
            print(f"  {mode}: only {len(mode_rows)} examples, skipping (need 20+)")
            continue

        # Build feature matrix
        X = np.zeros((len(mode_rows), len(FEATURE_NAMES)))
        for i, row in enumerate(mode_rows):
            for j, fname in enumerate(FEATURE_NAMES):
                try:
                    X[i, j] = float(row.get(fname, 0))
                except (ValueError, TypeError):
                    X[i, j] = 0

        # Build target vector
        if mode in OFFENSIVE_MODES:
            y = np.array([float(r.get('score_delta_5', 0)) for r in mode_rows])
        else:
            y = np.array([
                -float(r.get('invaderDistance', 0)) + float(r.get('onDefense', 0)) * 5
                for r in mode_rows
            ])

        # Normalize features
        std = X.std(axis=0)
        std[std == 0] = 1
        mean = X.mean(axis=0)
        X_norm = (X - mean) / std

        # Fit ridge regression
        w = ridge_regression(X_norm, y, lam=1.0)

        # Convert back to original scale
        w_orig = w / std

        # Build weight dict
        weight_dict = {}
        for j, fname in enumerate(FEATURE_NAMES):
            weight_dict[fname] = round(float(w_orig[j]), 2)

        learned[mode] = weight_dict
        r2 = 1 - np.sum((y - X @ (w / std))**2) / max(np.sum((y - y.mean())**2), 1e-10)
        print(f"  {mode}: {len(mode_rows)} examples, R²={r2:.3f}")

    # Write output
    output_str = format_weights(learned)
    with open(output_path, 'w') as f:
        f.write(output_str)
    print(f"\nWeights written to {output_path}")
    print("Copy the LEARNED_WEIGHTS dict into myTeam.py to use learned weights.")


def generate_default_weights():
    """Generate reasonable default learned weights based on expert tuning."""
    return {
        'attack': {
            'successorScore': 250, 'foodEaten': 140, 'capsuleEaten': 150,
            'foodCarried': 15, 'targetDistance': -5, 'foodDistance': -2,
            'homeDistance': -1, 'ghostDistance': 5, 'ghostScared': 100,
            'capsuleDistance': -4, 'escapeRoutes': 18, 'inDeadEnd': -100,
            'threatPressure': -90, 'deadEndRisk': -20, 'timePressure': -25,
            'patrolDistance': 0, 'lostFoodDistance': 0, 'stop': -50,
            'reverse': -8, 'died': -2000, 'returnedFood': 50,
            'onDefense': 0, 'numVisibleInvaders': 0, 'invaderDistance': 0,
            'scoreDiff': 5, 'oscillation': -35, 'dangerZone': -70,
            'tunnelEntryRisk': -30, 'chokepointCoverage': 0,
            'noisyInvaderDist': 0, 'teammateProximity': -10,
        },
        'return': {
            'successorScore': 280, 'foodEaten': 10, 'capsuleEaten': 50,
            'foodCarried': 25, 'targetDistance': -8, 'foodDistance': 0,
            'homeDistance': -15, 'ghostDistance': 8, 'ghostScared': 90,
            'capsuleDistance': -6, 'escapeRoutes': 20, 'inDeadEnd': -140,
            'threatPressure': -100, 'deadEndRisk': -25, 'timePressure': -50,
            'patrolDistance': 0, 'lostFoodDistance': 0, 'stop': -60,
            'reverse': -10, 'died': -2500, 'returnedFood': 300,
            'onDefense': 0, 'numVisibleInvaders': 0, 'invaderDistance': 0,
            'scoreDiff': 0, 'oscillation': -45, 'dangerZone': -90,
            'tunnelEntryRisk': -40, 'chokepointCoverage': 0,
            'noisyInvaderDist': 0, 'teammateProximity': -5,
        },
        'defend': {
            'successorScore': 200, 'foodEaten': 10, 'capsuleEaten': 25,
            'foodCarried': 0, 'targetDistance': -8, 'foodDistance': 0,
            'homeDistance': 0, 'ghostDistance': 0, 'ghostScared': 0,
            'capsuleDistance': 0, 'escapeRoutes': 0, 'inDeadEnd': 0,
            'threatPressure': 0, 'deadEndRisk': 0, 'timePressure': 0,
            'patrolDistance': -10, 'lostFoodDistance': -12, 'stop': -90,
            'reverse': -12, 'died': -600, 'returnedFood': 0,
            'onDefense': 150, 'numVisibleInvaders': -300, 'invaderDistance': -20,
            'scoreDiff': 0, 'oscillation': -25, 'dangerZone': 0,
            'tunnelEntryRisk': 0, 'chokepointCoverage': 10,
            'noisyInvaderDist': -8, 'teammateProximity': -12,
        },
        'patrol': {
            'successorScore': 150, 'foodEaten': 10, 'capsuleEaten': 20,
            'foodCarried': 0, 'targetDistance': -5, 'foodDistance': 0,
            'homeDistance': 0, 'ghostDistance': 0, 'ghostScared': 0,
            'capsuleDistance': 0, 'escapeRoutes': 0, 'inDeadEnd': 0,
            'threatPressure': 0, 'deadEndRisk': 0, 'timePressure': 0,
            'patrolDistance': -14, 'lostFoodDistance': -8, 'stop': -40,
            'reverse': -8, 'died': -500, 'returnedFood': 0,
            'onDefense': 100, 'numVisibleInvaders': -150, 'invaderDistance': -12,
            'scoreDiff': 0, 'oscillation': -25, 'dangerZone': 0,
            'tunnelEntryRisk': 0, 'chokepointCoverage': 12,
            'noisyInvaderDist': -5, 'teammateProximity': -8,
        },
        'capsule': {
            'successorScore': 220, 'foodEaten': 30, 'capsuleEaten': 250,
            'foodCarried': 10, 'targetDistance': -10, 'foodDistance': 0,
            'homeDistance': -2, 'ghostDistance': 6, 'ghostScared': 130,
            'capsuleDistance': -15, 'escapeRoutes': 16, 'inDeadEnd': -90,
            'threatPressure': -75, 'deadEndRisk': -20, 'timePressure': -18,
            'patrolDistance': 0, 'lostFoodDistance': 0, 'stop': -40,
            'reverse': -8, 'died': -1800, 'returnedFood': 0,
            'onDefense': 0, 'numVisibleInvaders': 0, 'invaderDistance': 0,
            'scoreDiff': 0, 'oscillation': -30, 'dangerZone': -55,
            'tunnelEntryRisk': -22, 'chokepointCoverage': 0,
            'noisyInvaderDist': 0, 'teammateProximity': -5,
        },
    }


def format_weights(weights):
    """Format weight dicts as pasteable Python code."""
    lines = ["# Learned weights — paste into myTeam.py", ""]
    lines.append("LEARNED_WEIGHTS = {")
    for mode in MODES:
        if mode not in weights:
            continue
        lines.append(f"  '{mode}': {{")
        for fname in FEATURE_NAMES:
            val = weights[mode].get(fname, 0)
            lines.append(f"    '{fname}': {val},")
        lines.append("  },")
    lines.append("}")
    lines.append("")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Train myTeam weights')
    parser.add_argument('--data', default=None, help='Path to training CSV')
    parser.add_argument('--output', default='learned_weights.py', help='Output file')
    parser.add_argument('--defaults', action='store_true',
                        help='Generate expert-tuned default weights')
    args = parser.parse_args()

    if args.defaults or args.data is None:
        print("Generating expert-tuned default weights...")
        weights = generate_default_weights()
        output_str = format_weights(weights)
        with open(args.output, 'w') as f:
            f.write(output_str)
        print(f"Default weights written to {args.output}")
        print("Copy LEARNED_WEIGHTS into myTeam.py to use.")
    elif args.data and os.path.exists(args.data):
        train_from_csv(args.data, args.output)
    else:
        print(f"Data file not found: {args.data}")
        print("Run: python3 collect_data.py --games 50 first")
        print("Or use: python3 train_weights.py --defaults")


if __name__ == '__main__':
    main()
