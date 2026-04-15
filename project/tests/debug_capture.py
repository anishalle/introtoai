#!/usr/bin/env python3
"""
Step-through debugger for capture-the-flag agents.

Examples:
  uv run tests/debug_capture.py
  uv run tests/debug_capture.py --agent 2 --max-decisions 3 --pause
  uv run tests/debug_capture.py --all-agents --layout tinyCapture --top-k 2
"""

from __future__ import annotations

import argparse
import contextlib
import io
import random
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import capture
import layout as layout_module
import textDisplay
from game import Game


def parse_args():
  parser = argparse.ArgumentParser(
    description='Run capture agents one action at a time with compact debug output.'
  )
  parser.add_argument('--layout', default='tinyCapture',
                      help='Layout name from layouts/, default: tinyCapture')
  parser.add_argument('--red', default='myTeam',
                      help='Red team module name, default: myTeam')
  parser.add_argument('--blue', default='baselineTeam',
                      help='Blue team module name, default: baselineTeam')
  parser.add_argument('--red-opts', default='',
                      help='Comma-separated kwargs passed to red createTeam()')
  parser.add_argument('--blue-opts', default='',
                      help='Comma-separated kwargs passed to blue createTeam()')
  parser.add_argument('--agent', type=int, default=0,
                      help='Only print decisions for this agent index unless --all-agents is set')
  parser.add_argument('--all-agents', action='store_true',
                      help='Print a report for every agent action')
  parser.add_argument('--max-decisions', type=int, default=5,
                      help='Number of inspected decisions to print before stopping')
  parser.add_argument('--max-plies', type=int, default=40,
                      help='Hard cap on total plies simulated before stopping')
  parser.add_argument('--time-limit', type=int, default=1200,
                      help='Initial game timeleft, default matches capture.py')
  parser.add_argument('--seed', type=int, default=0,
                      help='Random seed for reproducibility')
  parser.add_argument('--starter', choices=['red', 'blue', 'random'], default='red',
                      help='Which team acts first')
  parser.add_argument('--top-k', type=int, default=3,
                      help='How many ranked actions to show per inspected decision')
  parser.add_argument('--pause', action='store_true',
                      help='Wait for Enter after each inspected decision')
  parser.add_argument('--delay', type=float, default=0.0,
                      help='Sleep this many seconds after each inspected decision')
  parser.add_argument('--hide-board', action='store_true',
                      help='Do not print the board snapshot for each inspected decision')
  parser.add_argument('--hide-features', action='store_true',
                      help='Do not print feature/weight breakdowns')
  parser.add_argument('--hide-agent-stdout', action='store_true',
                      help='Do not print captured stdout from the acting agent')
  return parser.parse_args()


def load_team(is_red, factory, agent_opts):
  """
  Reuse capture.py's team loader, but suppress its startup prints.
  """
  with contextlib.redirect_stdout(io.StringIO()):
    agents = capture.loadAgents(is_red, factory, True, agent_opts)
  if any(agent is None for agent in agents):
    raise RuntimeError('Failed to load team %s' % factory)
  return agents


class DebugCaptureSession:
  def __init__(self, args):
    self.args = args
    random.seed(args.seed)

    self.layout = layout_module.getLayout(args.layout)
    if self.layout is None:
      raise ValueError('Unknown layout: %s' % args.layout)

    red_agents = load_team(True, args.red, capture.parseAgentArgs(args.red_opts))
    blue_agents = load_team(False, args.blue, capture.parseAgentArgs(args.blue_opts))
    self.agents = sum([list(pair) for pair in zip(red_agents, blue_agents)], [])

    self.rules = capture.CaptureRules(quiet=True)
    self.display = textDisplay.NullGraphics()
    self.game = self._create_game(args.time_limit)
    self.current_agent_index = self.game.startingIndex
    self.agent_output_offsets = [0 for _ in self.game.agents]

  def _create_game(self, time_limit):
    init_state = capture.GameState()
    init_state.initialize(self.layout, len(self.agents))

    if self.args.starter == 'red':
      starting_index = 0
    elif self.args.starter == 'blue':
      starting_index = 1
    else:
      starting_index = random.randint(0, 1)

    game = Game(
      self.agents,
      self.display,
      self.rules,
      startingIndex=starting_index,
      muteAgents=True,
      catchExceptions=False,
    )
    game.state = init_state
    game.length = time_limit
    game.state.data.timeleft = time_limit
    return game

  def initialize(self):
    self.game.display.initialize(self.game.state.data)
    red_team = self.game.state.getRedTeamIndices()
    blue_team = self.game.state.getBlueTeamIndices()

    for index, agent in enumerate(self.game.agents):
      team = red_team if index in red_team else blue_team
      if 'registerTeam' in dir(agent):
        self._call_agent(index, agent.registerTeam, team)
      if 'registerInitialState' in dir(agent):
        self._call_agent(index, agent.registerInitialState, self.game.state.deepCopy())

  def _call_agent(self, agent_index, func, *args):
    self.game.mute(agent_index)
    try:
      return func(*args)
    finally:
      self.game.unmute()

  def _collect_observation(self, agent_index, agent):
    if 'observationFunction' in dir(agent):
      return self._call_agent(agent_index, agent.observationFunction, self.game.state.deepCopy())
    return self.game.state.deepCopy()

  def _read_new_agent_output(self, agent_index):
    output = self.game.agentOutput[agent_index].getvalue()
    offset = self.agent_output_offsets[agent_index]
    self.agent_output_offsets[agent_index] = len(output)
    return output[offset:]

  def step(self):
    if self.game.gameOver:
      return None

    agent_index = self.current_agent_index
    agent = self.game.agents[agent_index]
    state_before = self.game.state.deepCopy()
    observation = self._collect_observation(agent_index, agent)
    action = self._call_agent(agent_index, agent.getAction, observation)
    debug_info = None
    if hasattr(agent, 'getLastDecisionInfo'):
      debug_info = agent.getLastDecisionInfo()

    agent_stdout = self._read_new_agent_output(agent_index)

    self.game.moveHistory.append((agent_index, action))
    self.game.state = self.game.state.generateSuccessor(agent_index, action)
    self.game.display.update(self.game.state.data)
    self.game.rules.process(self.game.state, self.game)

    record = {
      'ply': len(self.game.moveHistory),
      'agentIndex': agent_index,
      'observation': observation,
      'stateBefore': state_before,
      'stateAfter': self.game.state.deepCopy(),
      'action': action,
      'debugInfo': debug_info,
      'agentStdout': agent_stdout,
    }

    self.current_agent_index = (agent_index + 1) % len(self.game.agents)
    return record


def should_print(record, args):
  return args.all_agents or record['agentIndex'] == args.agent


def team_name(state, agent_index):
  return 'Red' if state.isOnRedTeam(agent_index) else 'Blue'


def format_visible_opponents(observation, agent_index):
  visible = []
  acting_team = set(observation.getRedTeamIndices() if observation.isOnRedTeam(agent_index)
                    else observation.getBlueTeamIndices())
  for opponent_index in range(observation.getNumAgents()):
    if opponent_index in acting_team:
      continue
    opponent_state = observation.getAgentState(opponent_index)
    position = opponent_state.getPosition()
    if position is None:
      continue
    visible.append(
      '%d@%s pacman=%s scared=%d' % (
        opponent_index,
        position,
        opponent_state.isPacman,
        opponent_state.scaredTimer,
      )
    )
  return visible or ['none']


def format_state_header(record):
  observation = record['observation']
  agent_index = record['agentIndex']
  agent_state = observation.getAgentState(agent_index)
  return (
    'Ply {ply} | Agent {agent} ({team}) | Pos {pos} | Pacman={pacman} | '
    'Carrying={carrying} | Score={score} | TimeLeft={timeleft}'
  ).format(
    ply=record['ply'],
    agent=agent_index,
    team=team_name(observation, agent_index),
    pos=agent_state.getPosition(),
    pacman=agent_state.isPacman,
    carrying=agent_state.numCarrying,
    score=record['stateBefore'].getScore(),
    timeleft=record['stateBefore'].data.timeleft,
  )


def print_board(record):
  print('Board:')
  print(record['observation'])


def print_state_summary(record):
  observation = record['observation']
  agent_index = record['agentIndex']
  food_to_eat = len(
    observation.getBlueFood().asList()
    if observation.isOnRedTeam(agent_index)
    else observation.getRedFood().asList()
  )
  defended_food = len(
    observation.getRedFood().asList()
    if observation.isOnRedTeam(agent_index)
    else observation.getBlueFood().asList()
  )
  visible_opponents = format_visible_opponents(observation, agent_index)

  print(format_state_header(record))
  print(
    'FoodToEat=%d | DefendedFood=%d | VisibleOpponents=%s' % (
      food_to_eat,
      defended_food,
      ', '.join(visible_opponents),
    )
  )


def print_ranked_actions(debug_info, top_k):
  print(
    'Mode=%s | Chosen=%s | BestPool=%s | BestScore=%s' % (
      debug_info['mode'],
      debug_info['chosenAction'],
      ', '.join(debug_info['bestActions']) or 'none',
      debug_info['bestScore'],
    )
  )
  ranked = debug_info['scoredActions'][:top_k]
  if not ranked:
    print('RankedActions=none')
    return

  print('Top actions:')
  for detail in ranked:
    print('  %-5s score=%s' % (detail['action'], detail['score']))


def print_feature_breakdown(debug_info):
  selected = debug_info.get('selectedAction')
  if not selected:
    return

  print('Chosen action features:')
  for name, value in sorted(selected['features'].items()):
    weight = selected['weights'].get(name, 0)
    print('  %-24s value=%-8s weight=%s' % (name, value, weight))

  unused_weights = sorted(
    name for name in selected['weights']
    if name not in selected['features']
  )
  if unused_weights:
    print('Unused weights: %s' % ', '.join(unused_weights))


def print_debug_messages(debug_info):
  messages = debug_info.get('messages', [])
  if not messages:
    return

  print('Debug messages:')
  for message in messages:
    print('  %s' % message)


def print_agent_stdout(stdout_text):
  cleaned = stdout_text.rstrip()
  if not cleaned:
    return

  print('Agent stdout:')
  for line in cleaned.splitlines():
    print('  %s' % line)


def print_report(record, args):
  print('=' * 72)
  print_state_summary(record)

  if not args.hide_board:
    print_board(record)

  debug_info = record['debugInfo']
  if debug_info is not None:
    print_ranked_actions(debug_info, args.top_k)
    if not args.hide_features:
      print_feature_breakdown(debug_info)
    print_debug_messages(debug_info)
  else:
    print('Chosen=%s | Debug breakdown unavailable for this agent class' % record['action'])

  if not args.hide_agent_stdout:
    print_agent_stdout(record['agentStdout'])


def main():
  args = parse_args()
  if not args.all_agents and args.agent not in range(4):
    raise ValueError('--agent must be between 0 and 3')
  if args.max_decisions <= 0:
    raise ValueError('--max-decisions must be positive')
  if args.max_plies <= 0:
    raise ValueError('--max-plies must be positive')

  session = DebugCaptureSession(args)
  session.initialize()

  printed_decisions = 0
  total_plies = 0

  while not session.game.gameOver and total_plies < args.max_plies:
    record = session.step()
    if record is None:
      break
    total_plies += 1

    if not should_print(record, args):
      continue

    print_report(record, args)
    printed_decisions += 1

    if args.pause:
      input('Press Enter for the next inspected decision...')
    elif args.delay > 0:
      time.sleep(args.delay)

    if printed_decisions >= args.max_decisions:
      break

  print('=' * 72)
  print(
    'Stopped after %d plies and %d inspected decisions. GameOver=%s Score=%s'
    % (
      total_plies,
      printed_decisions,
      session.game.gameOver,
      session.game.state.getScore(),
    )
  )


if __name__ == '__main__':
  main()
