#!/usr/bin/env python3
"""
Phase 7: Offline data collection for training myTeam weights.

Runs multiple games and logs per-turn feature vectors + outcome labels to CSV.
Uses only stdlib + subprocess to drive capture.py.

Usage:
  python3 collect_data.py --games 50 --opponent baselineTeam --output training_data
  python3 collect_data.py --games 20 --opponent baselineTeam --output training_data --layout RANDOM
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import random


# Feature names must match those in myTeam.py extractFeatures
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


def run_game(game_id, opponent, layout, seed=None):
    """Run a single game and capture the score output."""
    cmd = [
        sys.executable, 'capture.py',
        '-r', 'myTeam', '-b', opponent,
        '-q', '-n', '1',
    ]
    if layout:
        if layout == 'RANDOM' and seed is not None:
            cmd += ['-l', f'RANDOM{seed}']
        else:
            cmd += ['-l', layout]

    env = dict(os.environ)
    env['PACMAN_LOG'] = f'game_{game_id}.jsonl'
    env['PACMAN_LOG_DIR'] = os.path.join(os.getcwd(), '_log_tmp')

    os.makedirs(env['PACMAN_LOG_DIR'], exist_ok=True)

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout, env['PACMAN_LOG_DIR'], env['PACMAN_LOG']


def parse_score(stdout):
    """Extract final score from capture.py output."""
    for line in stdout.split('\n'):
        if 'wins by' in line:
            parts = line.split()
            for i, word in enumerate(parts):
                if word == 'by':
                    try:
                        pts = int(parts[i + 1])
                        if 'Red' in line:
                            return pts
                        return -pts
                    except (ValueError, IndexError):
                        pass
        if 'Tie' in line:
            return 0
    return 0


def collect_log_data(log_dir, log_file):
    """Read JSONL log file if it exists and return rows."""
    path = os.path.join(log_dir, log_file)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def compute_outcomes(rows):
    """Add outcome labels to each row based on future turns."""
    K = 5
    for i, row in enumerate(rows):
        agent_idx = row.get('agentIndex', -1)
        # Look ahead K turns for this agent
        future = [r for r in rows[i+1:i+K*4+1] if r.get('agentIndex') == agent_idx]

        died_within_k = 0
        returned_food_within_k = 0
        score_start = row.get('score', 0)
        score_end = score_start

        for fr in future[:K]:
            if fr.get('features', {}).get('died', 0) > 0:
                died_within_k = 1
            if fr.get('features', {}).get('returnedFood', 0) > 0:
                returned_food_within_k = 1
            score_end = fr.get('score', score_end)

        row['died_within_5'] = died_within_k
        row['returned_food_within_5'] = returned_food_within_k
        row['score_delta_5'] = score_end - score_start

    return rows


def rows_to_csv(all_rows, output_path):
    """Write all collected rows to a single CSV file."""
    fieldnames = (
        ['game_id', 'turn', 'agentIndex', 'mode', 'action', 'score']
        + FEATURE_NAMES
        + ['died_within_5', 'returned_food_within_5', 'score_delta_5']
    )

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for row in all_rows:
            flat = {
                'game_id': row.get('game_id', 0),
                'turn': row.get('turn', 0),
                'agentIndex': row.get('agentIndex', 0),
                'mode': row.get('mode', ''),
                'action': row.get('action', ''),
                'score': row.get('score', 0),
                'died_within_5': row.get('died_within_5', 0),
                'returned_food_within_5': row.get('returned_food_within_5', 0),
                'score_delta_5': row.get('score_delta_5', 0),
            }
            features = row.get('features', {})
            for fname in FEATURE_NAMES:
                flat[fname] = features.get(fname, 0)
            writer.writerow(flat)


def main():
    parser = argparse.ArgumentParser(description='Collect training data for myTeam')
    parser.add_argument('--games', type=int, default=50, help='Number of games to run')
    parser.add_argument('--opponent', default='baselineTeam', help='Opponent team file')
    parser.add_argument('--output', default='training_data', help='Output directory')
    parser.add_argument('--layout', default='RANDOM', help='Layout to use')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    all_rows = []

    print(f"Running {args.games} games against {args.opponent}...")
    for i in range(args.games):
        seed = random.randint(0, 99999) if args.layout == 'RANDOM' else None
        side = 'red' if i % 2 == 0 else 'blue'

        stdout, log_dir, log_file = run_game(i, args.opponent, args.layout, seed)
        final_score = parse_score(stdout)
        log_rows = collect_log_data(log_dir, log_file)

        if log_rows:
            log_rows = compute_outcomes(log_rows)
            for row in log_rows:
                row['game_id'] = i
            all_rows.extend(log_rows)

        win = 'W' if final_score > 0 else ('L' if final_score < 0 else 'T')
        print(f"  Game {i+1}/{args.games}: score={final_score} ({win})")

    csv_path = os.path.join(args.output, 'training_data.csv')
    rows_to_csv(all_rows, csv_path)
    print(f"\nSaved {len(all_rows)} examples to {csv_path}")

    print("\nNote: For full feature logging, add PACMAN_LOG support to myTeam.py")
    print("The current version collects game outcomes for score-based analysis.")


if __name__ == '__main__':
    main()
