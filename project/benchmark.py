#!/usr/bin/env python3
"""
Phase 10: Benchmarking script for myTeam.

Runs repeated matches against baseline and other opponents,
reports win rates, average scores, and per-layout performance.

Usage:
  python3 benchmark.py
  python3 benchmark.py --games 20 --opponent baselineTeam
  python3 benchmark.py --games 10 --layouts "defaultCapture,RANDOM,mediumCapture"
  python3 benchmark.py --games 30 --both-sides
"""

import argparse
import subprocess
import sys
import re


def run_games(team, opponent, layout, num_games, as_red=True):
    """Run games and return list of scores."""
    cmd = [sys.executable, 'capture.py', '-q']
    if as_red:
        cmd += ['-r', team, '-b', opponent]
    else:
        cmd += ['-r', opponent, '-b', team]
    cmd += ['-l', layout, '-n', str(num_games)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    stdout = result.stdout

    scores = []
    # Parse individual game scores from output
    for line in stdout.split('\n'):
        if 'wins by' in line:
            pts_match = re.search(r'wins by (\d+)', line)
            if pts_match:
                pts = int(pts_match.group(1))
                if 'Red' in line:
                    scores.append(pts if as_red else -pts)
                else:
                    scores.append(-pts if as_red else pts)
        elif 'Tie' in line.lower() and 'game' in line.lower():
            scores.append(0)

    # If we couldn't parse individual games, try aggregate
    if not scores:
        scores_match = re.search(r'Scores:\s*([\-\d, ]+)', stdout)
        if scores_match:
            raw = scores_match.group(1).split(',')
            for s in raw:
                s = s.strip()
                if s:
                    val = int(s)
                    scores.append(val if as_red else -val)

    return scores


def report(title, scores):
    """Print a performance summary."""
    if not scores:
        print(f"\n{title}: No games completed")
        return

    wins = sum(1 for s in scores if s > 0)
    losses = sum(1 for s in scores if s < 0)
    ties = sum(1 for s in scores if s == 0)
    total = len(scores)
    avg = sum(scores) / total
    win_rate = wins / total * 100

    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")
    print(f"  Games:    {total}")
    print(f"  Wins:     {wins} ({win_rate:.0f}%)")
    print(f"  Losses:   {losses}")
    print(f"  Ties:     {ties}")
    print(f"  Avg Score: {avg:.1f}")
    if scores:
        print(f"  Min Score: {min(scores)}")
        print(f"  Max Score: {max(scores)}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description='Benchmark myTeam agent')
    parser.add_argument('--team', default='myTeam', help='Team to benchmark')
    parser.add_argument('--opponent', default='baselineTeam', help='Opponent team')
    parser.add_argument('--games', type=int, default=10, help='Games per config')
    parser.add_argument('--layouts', default='defaultCapture,RANDOM',
                        help='Comma-separated layouts to test')
    parser.add_argument('--both-sides', action='store_true',
                        help='Test as both red and blue')
    args = parser.parse_args()

    layouts = [l.strip() for l in args.layouts.split(',')]
    all_scores = []

    print(f"Benchmarking {args.team} vs {args.opponent}")
    print(f"Games per config: {args.games}")
    print(f"Layouts: {layouts}")

    for layout in layouts:
        print(f"\nRunning {args.games} games on {layout} (as red)...")
        scores = run_games(args.team, args.opponent, layout, args.games, as_red=True)
        report(f"{layout} — as Red", scores)
        all_scores.extend(scores)

        if args.both_sides:
            print(f"Running {args.games} games on {layout} (as blue)...")
            scores_blue = run_games(args.team, args.opponent, layout, args.games, as_red=False)
            report(f"{layout} — as Blue", scores_blue)
            all_scores.extend(scores_blue)

    report("OVERALL", all_scores)


if __name__ == '__main__':
    main()
