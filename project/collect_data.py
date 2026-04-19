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

FEATURE_NAMES = [
    'carrying', 'returned', 'isPacman', 'posX', 'posY',
    'homeDist', 'foodLeft', 'foodDefending', 'movesLeft',
    'positionRisk', 'visibleThreatDist', 'invaderDist'
] + [
    'feat_teamScore', 'feat_distanceToTarget', 'feat_plannedAction', 'feat_stop', 'feat_reverse',
    'feat_foodEaten', 'feat_foodReturned', 'feat_risk', 'feat_homeDistance', 'feat_carrying',
    'feat_carryHomeDistance', 'feat_visibleGhostDistance', 'feat_capsuleDistance',
    'feat_escapeRoutes', 'feat_deadEndFlag', 'feat_tripDeadline', 'feat_laneMatch',
    'feat_invaderDistance', 'feat_eventDistance', 'feat_stayGhost', 'feat_becamePacman', 'feat_scaredContact'
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
    log_path = os.path.join(env['PACMAN_LOG_DIR'], env['PACMAN_LOG'])
    if os.path.exists(log_path):
        os.remove(log_path)

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
    K = 10
    for i, row in enumerate(rows):
        agent_idx = row.get('agent', -1)
        future = [r for r in rows[i+1:i+K*4+1] if r.get('agent') == agent_idx]

        score_start = row.get('score', 0)
        returned_start = row.get('returned', 0)
        carrying_start = row.get('carrying', 0)
        food_left_start = row.get('foodLeft', 0)

        score_end = score_start
        returned_end = returned_start
        carrying_end = carrying_start
        food_left_end = food_left_start
        died = 0

        for fr in future[:K]:
            if fr.get('posX') == 1 and fr.get('posY') == 1:
                 # Poor proxy for death but best we can do easily with this format
                 if carrying_start > 0 and fr.get('carrying', 0) == 0 and fr.get('returned', 0) == returned_start:
                     died = 1
            score_end = fr.get('score', score_end)
            returned_end = fr.get('returned', returned_end)
            carrying_end = fr.get('carrying', carrying_end)
            food_left_end = fr.get('foodLeft', food_left_end)

        row['died_within_k'] = died
        row['returned_food_k'] = returned_end - returned_start
        row['food_eaten_k'] = food_left_start - food_left_end
        row['score_delta_k'] = score_end - score_start

    return rows

def rows_to_csv(all_rows, output_path):
    """Write all collected rows to a single CSV file."""
    fieldnames = (
        ['game_id', 'turn', 'agent', 'mode', 'action', 'score', 'bestActionScore', 'numActions']
        + FEATURE_NAMES
        + ['died_within_k', 'returned_food_k', 'food_eaten_k', 'score_delta_k']
    )

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

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

if __name__ == '__main__':
    main()
