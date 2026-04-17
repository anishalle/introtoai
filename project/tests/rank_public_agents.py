#!/usr/bin/env python3
"""
Rank public Berkeley-style Pacman CTF agents against local reference agents.

This script evaluates each runnable public agent against the local `anish` and
`master` agents across a small layout suite, both color assignments, and two
deterministic starting seeds.  It reports aggregate standings plus unrunnable
repos that could not be normalized into this engine.
"""

from __future__ import annotations

import contextlib
import io
import json
import argparse
import random
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

DEPS = Path('/tmp/pacman-ctf-deps')
if DEPS.exists() and str(DEPS) not in sys.path:
  sys.path.insert(0, str(DEPS))

import capture
import layout as layout_module
import textDisplay
from game import Game


DEFAULT_LAYOUTS = ['defaultCapture', 'strategicCapture', 'fastCapture']
DEFAULT_SEEDS = [0, 1]
DEFAULT_LENGTH = 1200


@dataclass(frozen=True)
class TeamSpec:
  name: str
  factory: str
  args: dict[str, str]
  category: str


@dataclass
class TeamStats:
  name: str
  category: str
  games: int = 0
  wins: int = 0
  losses: int = 0
  ties: int = 0
  margin_sum: float = 0.0
  refs: dict[str, dict[str, float]] | None = None

  def __post_init__(self):
    if self.refs is None:
      self.refs = {}

  def record(self, opponent: str, margin: float):
    self.games += 1
    self.margin_sum += margin
    if margin > 0:
      self.wins += 1
    elif margin < 0:
      self.losses += 1
    else:
      self.ties += 1

    ref = self.refs.setdefault(opponent, {
      'games': 0,
      'wins': 0,
      'losses': 0,
      'ties': 0,
      'margin_sum': 0.0,
    })
    ref['games'] += 1
    ref['margin_sum'] += margin
    if margin > 0:
      ref['wins'] += 1
    elif margin < 0:
      ref['losses'] += 1
    else:
      ref['ties'] += 1

  @property
  def points(self):
    return self.wins + 0.5 * self.ties

  @property
  def win_pct(self):
    if self.games == 0:
      return 0.0
    return self.points / float(self.games)

  @property
  def avg_margin(self):
    if self.games == 0:
      return 0.0
    return self.margin_sum / float(self.games)


RUNNABLE_PUBLIC = [
  TeamSpec(
    name='DarioVajda',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/DarioVajda-pacman-agent/my_team.py',
      'repo_root': '/tmp/pacman-ctf-agents/DarioVajda-pacman-agent',
    },
    category='public',
  ),
  TeamSpec(
    name='LuChenyang3842',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/LuChenyang3842-pacman-contest/pacman-contest/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/LuChenyang3842-pacman-contest/pacman-contest',
    },
    category='public',
  ),
  TeamSpec(
    name='martbojinov',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/martbojinov-Artificial-Intelligence/Contest Submission/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/martbojinov-Artificial-Intelligence/Contest Submission',
    },
    category='public',
  ),
  TeamSpec(
    name='ngacho',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/ngacho-pacman-contest/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/ngacho-pacman-contest',
    },
    category='public',
  ),
  TeamSpec(
    name='vincent916735',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/vincent916735-Pacman-capture-the-flag/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/vincent916735-Pacman-capture-the-flag',
    },
    category='public',
  ),
  TeamSpec(
    name='lzheng1026',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/lzheng1026-Pacman-Capture-The-Flag/src/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/lzheng1026-Pacman-Capture-The-Flag/src',
    },
    category='public',
  ),
  TeamSpec(
    name='jaredjxyz',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/jaredjxyz-Pacman-Tournament-Agent/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/jaredjxyz-Pacman-Tournament-Agent',
    },
    category='public',
  ),
  TeamSpec(
    name='abhinavcreed13',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/abhinavcreed13-ai-capture-the-flag-pacman-contest/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/abhinavcreed13-ai-capture-the-flag-pacman-contest',
    },
    category='public',
  ),
  TeamSpec(
    name='uripont',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/uripont-pacman-agent/my_team.py',
      'repo_root': '/tmp/pacman-ctf-agents/uripont-pacman-agent',
    },
    category='public',
  ),
  TeamSpec(
    name='apattichis',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/apattichis-Contest-Pacman-Capture-the-Flag-EUTOPIA/versions/v2.py',
      'repo_root': '/tmp/pacman-ctf-agents/apattichis-Contest-Pacman-Capture-the-Flag-EUTOPIA/versions',
    },
    category='public',
  ),
  TeamSpec(
    name='kkkkkaran',
    factory='external_team_adapter.py',
    args={
      'target': '/tmp/pacman-ctf-agents/kkkkkaran-Berkeley-PacmanCTF/pacman-contest/myTeam.py',
      'repo_root': '/tmp/pacman-ctf-agents/kkkkkaran-Berkeley-PacmanCTF/pacman-contest',
    },
    category='public',
  ),
]

UNRUNNABLE_PUBLIC = {
  'DXJ3X1': 'repo does not include a runnable team file',
}

REFERENCES = [
  TeamSpec(
    name='anish',
    factory='myTeam.py',
    args={},
    category='reference',
  ),
  TeamSpec(
    name='master',
    factory='/tmp/introtoai-master-agent/project/myTeam.py',
    args={},
    category='reference',
  ),
]


def load_team(is_red: bool, spec: TeamSpec):
  with contextlib.redirect_stdout(io.StringIO()):
    agents = capture.loadAgents(is_red, spec.factory, True, spec.args)
  if any(agent is None for agent in agents):
    raise RuntimeError('Failed to load team %s' % spec.name)
  return agents


def run_game(red_spec: TeamSpec, blue_spec: TeamSpec, layout_name: str, seed: int, length: int):
  random.seed('%s:%s:%s:%s' % (layout_name, seed, red_spec.name, blue_spec.name))
  layout = layout_module.getLayout(layout_name)
  if layout is None:
    raise ValueError('Unknown layout: %s' % layout_name)

  red_agents = load_team(True, red_spec)
  blue_agents = load_team(False, blue_spec)
  agents = sum([list(pair) for pair in zip(red_agents, blue_agents)], [])

  rules = capture.CaptureRules(quiet=True)
  display = textDisplay.NullGraphics()
  game = Game(
    agents,
    display,
    rules,
    startingIndex=seed % 2,
    muteAgents=True,
    catchExceptions=True,
  )
  init_state = capture.GameState()
  init_state.initialize(layout, len(agents))
  game.state = init_state
  game.length = length
  game.state.data.timeleft = length

  with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    game.run()

  return game.state.getScore()


def evaluate_matrix(public_specs, reference_specs, layouts, seeds, length):
  stats = {}
  for spec in public_specs + reference_specs:
    stats[spec.name] = TeamStats(spec.name, spec.category)

  match_rows = []
  for public in public_specs:
    for reference in reference_specs:
      for layout_name in layouts:
        for seed in seeds:
          print(
            'Running %s vs %s on %s seed=%s (public red)'
            % (public.name, reference.name, layout_name, seed),
            file=sys.stderr,
            flush=True,
          )
          score_public_red = run_game(public, reference, layout_name, seed, length)
          margin_public_red = score_public_red
          stats[public.name].record(reference.name, margin_public_red)
          stats[reference.name].record(public.name, -margin_public_red)
          match_rows.append({
            'public': public.name,
            'reference': reference.name,
            'layout': layout_name,
            'seed': seed,
            'public_color': 'red',
            'margin': margin_public_red,
          })

          print(
            'Running %s vs %s on %s seed=%s (public blue)'
            % (public.name, reference.name, layout_name, seed),
            file=sys.stderr,
            flush=True,
          )
          score_public_blue = run_game(reference, public, layout_name, seed, length)
          margin_public_blue = -score_public_blue
          stats[public.name].record(reference.name, margin_public_blue)
          stats[reference.name].record(public.name, -margin_public_blue)
          match_rows.append({
            'public': public.name,
            'reference': reference.name,
            'layout': layout_name,
            'seed': seed,
            'public_color': 'blue',
            'margin': margin_public_blue,
          })

  for layout_name in layouts:
    for seed in seeds:
      print(
        'Running anish vs master on %s seed=%s (anish red)'
        % (layout_name, seed),
        file=sys.stderr,
        flush=True,
      )
      score_anish_red = run_game(reference_specs[0], reference_specs[1], layout_name, seed, length)
      stats[reference_specs[0].name].record(reference_specs[1].name, score_anish_red)
      stats[reference_specs[1].name].record(reference_specs[0].name, -score_anish_red)

      print(
        'Running master vs anish on %s seed=%s (master red)'
        % (layout_name, seed),
        file=sys.stderr,
        flush=True,
      )
      score_master_red = run_game(reference_specs[1], reference_specs[0], layout_name, seed, length)
      stats[reference_specs[1].name].record(reference_specs[0].name, score_master_red)
      stats[reference_specs[0].name].record(reference_specs[1].name, -score_master_red)

  ranking = sorted(
    stats.values(),
    key=lambda row: (-row.win_pct, -row.avg_margin, -row.wins, row.name.lower()),
  )
  return ranking, match_rows, stats


def summarize(ranking, stats, layouts, seeds, length):
  print('Layouts:', ', '.join(layouts))
  print('Seeds:', ', '.join(str(seed) for seed in seeds))
  print('Length:', length)
  print()
  print('Rank | Team | Category | Record | Win% | Avg Margin')
  for idx, row in enumerate(ranking, start=1):
    print(
      '%d | %s | %s | %d-%d-%d | %.3f | %.3f'
      % (idx, row.name, row.category, row.wins, row.losses, row.ties, row.win_pct, row.avg_margin)
    )

  print()
  print('Per-reference breakdown')
  for row in ranking:
    for opponent, ref in sorted(row.refs.items()):
      avg_margin = ref['margin_sum'] / float(ref['games']) if ref['games'] else 0.0
      print(
        '%s vs %s: %d-%d-%d, avg_margin=%.3f'
        % (row.name, opponent, ref['wins'], ref['losses'], ref['ties'], avg_margin)
      )

  print()
  print('Unrunnable repos')
  for name, reason in sorted(UNRUNNABLE_PUBLIC.items()):
    print('%s: %s' % (name, reason))


def parse_args():
  parser = argparse.ArgumentParser(description='Rank public Pacman CTF agents.')
  parser.add_argument('--layouts', default=','.join(DEFAULT_LAYOUTS),
                      help='Comma-separated capture layouts to use.')
  parser.add_argument('--seeds', default=','.join(str(seed) for seed in DEFAULT_SEEDS),
                      help='Comma-separated deterministic seeds.')
  parser.add_argument('--length', type=int, default=DEFAULT_LENGTH,
                      help='Move limit per game.')
  parser.add_argument('--public', default='all',
                      help='Comma-separated public team names to include, or "all".')
  parser.add_argument('--references', default='all',
                      help='Comma-separated reference team names to include, or "all".')
  return parser.parse_args()


def main():
  args = parse_args()
  layouts = [item for item in args.layouts.split(',') if item]
  seeds = [int(item) for item in args.seeds.split(',') if item]
  public_specs = RUNNABLE_PUBLIC
  reference_specs = REFERENCES

  if args.public != 'all':
    wanted_public = {item for item in args.public.split(',') if item}
    public_specs = [spec for spec in RUNNABLE_PUBLIC if spec.name in wanted_public]

  if args.references != 'all':
    wanted_refs = {item for item in args.references.split(',') if item}
    reference_specs = [spec for spec in REFERENCES if spec.name in wanted_refs]
    if len(reference_specs) != 2:
      raise ValueError('Expected exactly two reference teams, got %s' % len(reference_specs))

  ranking, match_rows, stats = evaluate_matrix(public_specs, reference_specs, layouts, seeds, args.length)
  summarize(ranking, stats, layouts, seeds, args.length)
  payload = {
    'layouts': layouts,
    'seeds': seeds,
    'length': args.length,
    'ranking': [
      {
        'rank': idx,
        **asdict(row),
        'win_pct': row.win_pct,
        'avg_margin': row.avg_margin,
      }
      for idx, row in enumerate(ranking, start=1)
    ],
    'match_rows': match_rows,
    'unrunnable': UNRUNNABLE_PUBLIC,
  }
  print()
  print('JSON_START')
  print(json.dumps(payload, indent=2, sort_keys=True))
  print('JSON_END')


if __name__ == '__main__':
  main()
