"""
Compatibility aliases for Berkeley-style capture code.

Several public contest repos use snake_case APIs from a closely related fork of
the Berkeley contest framework.  This module installs a minimal alias layer so
those agents can run against the local camelCase engine without modifying the
third-party sources.
"""

_INSTALLED = False


def _alias_method(cls, alias, target):
  if not hasattr(cls, alias) and hasattr(cls, target):
    setattr(cls, alias, getattr(cls, target))


def _alias_property(cls, alias, target):
  if hasattr(cls, alias):
    return

  def getter(self):
    return getattr(self, target)

  def setter(self, value):
    setattr(self, target, value)

  setattr(cls, alias, property(getter, setter))


def _resolve_capture_module():
  import sys
  main_module = sys.modules.get('__main__')
  if main_module is not None and hasattr(main_module, 'GameState') and hasattr(main_module, 'SONAR_NOISE_VALUES'):
    return main_module

  import capture
  return capture


def install_aliases():
  global _INSTALLED
  if _INSTALLED:
    return

  import captureAgents
  import game
  import util
  import random
  capture = _resolve_capture_module()

  util.nearest_point = util.nearestPoint
  _alias_method(util.Stack, 'is_empty', 'isEmpty')
  _alias_method(util.Queue, 'is_empty', 'isEmpty')
  _alias_method(util.PriorityQueue, 'is_empty', 'isEmpty')
  _alias_method(util.Counter, 'arg_max', 'argMax')
  _alias_method(util.Counter, 'sorted_keys', 'sortedKeys')
  _alias_method(util.Counter, 'total_count', 'totalCount')
  _alias_method(util.Counter, 'increment_all', 'incrementAll')
  _alias_method(util.Counter, 'divide_all', 'divideAll')

  _alias_method(game.Grid, 'as_list', 'asList')
  _alias_method(game.Actions, 'get_legal_neighbors', 'getLegalNeighbors')
  _alias_method(game.Actions, 'get_possible_actions', 'getPossibleActions')
  _alias_method(game.Actions, 'direction_to_vector', 'directionToVector')
  _alias_method(game.Actions, 'vector_to_direction', 'vectorToDirection')

  _alias_method(game.AgentState, 'get_position', 'getPosition')
  _alias_method(game.AgentState, 'get_direction', 'getDirection')
  _alias_property(game.AgentState, 'is_pacman', 'isPacman')
  _alias_property(game.AgentState, 'scared_timer', 'scaredTimer')
  _alias_property(game.AgentState, 'num_carrying', 'numCarrying')
  _alias_property(game.AgentState, 'num_returned', 'numReturned')

  _alias_method(capture.GameState, 'get_legal_actions', 'getLegalActions')
  _alias_method(capture.GameState, 'generate_successor', 'generateSuccessor')
  _alias_method(capture.GameState, 'get_agent_state', 'getAgentState')
  _alias_method(capture.GameState, 'get_agent_position', 'getAgentPosition')
  _alias_method(capture.GameState, 'get_num_agents', 'getNumAgents')
  _alias_method(capture.GameState, 'get_score', 'getScore')
  _alias_method(capture.GameState, 'get_red_food', 'getRedFood')
  _alias_method(capture.GameState, 'get_blue_food', 'getBlueFood')
  _alias_method(capture.GameState, 'get_red_capsules', 'getRedCapsules')
  _alias_method(capture.GameState, 'get_blue_capsules', 'getBlueCapsules')
  _alias_method(capture.GameState, 'get_walls', 'getWalls')
  _alias_method(capture.GameState, 'has_food', 'hasFood')
  _alias_method(capture.GameState, 'has_wall', 'hasWall')
  _alias_method(capture.GameState, 'is_over', 'isOver')
  if not hasattr(capture.GameState, 'isWin'):
    capture.GameState.isWin = lambda self: self.isOver()
  if not hasattr(capture.GameState, 'isLose'):
    capture.GameState.isLose = lambda self: self.isOver()
  _alias_method(capture.GameState, 'get_red_team_indices', 'getRedTeamIndices')
  _alias_method(capture.GameState, 'get_blue_team_indices', 'getBlueTeamIndices')
  _alias_method(capture.GameState, 'is_on_red_team', 'isOnRedTeam')
  _alias_method(capture.GameState, 'get_agent_distances', 'getAgentDistances')
  _alias_method(capture.GameState, 'get_initial_agent_position', 'getInitialAgentPosition')
  _alias_property(capture.GameState, 'red_team', 'redTeam')
  _alias_property(capture.GameState, 'blue_team', 'blueTeam')
  _alias_property(capture.GameState, 'agent_distances', 'agentDistances')

  if not hasattr(capture.GameState, 'getDistanceProb'):
    def getDistanceProb(self, trueDistance, noisyDistance):
      if noisyDistance is None:
        return 0.0
      delta = noisyDistance - trueDistance
      if delta in capture.SONAR_NOISE_VALUES:
        return 1.0 / float(len(capture.SONAR_NOISE_VALUES))
      return 0.0
    capture.GameState.getDistanceProb = getDistanceProb

  _alias_method(capture.GameState, 'get_distance_prob', 'getDistanceProb')

  if not hasattr(capture, 'noisyDistance'):
    def noisyDistance(pos1, pos2):
      return util.manhattanDistance(pos1, pos2) + random.choice(capture.SONAR_NOISE_VALUES)
    capture.noisyDistance = noisyDistance

  _alias_method(captureAgents.CaptureAgent, 'register_initial_state', 'registerInitialState')
  _alias_method(captureAgents.CaptureAgent, 'get_food', 'getFood')
  _alias_method(captureAgents.CaptureAgent, 'get_food_you_are_defending', 'getFoodYouAreDefending')
  _alias_method(captureAgents.CaptureAgent, 'get_capsules', 'getCapsules')
  _alias_method(captureAgents.CaptureAgent, 'get_capsules_you_are_defending', 'getCapsulesYouAreDefending')
  _alias_method(captureAgents.CaptureAgent, 'get_opponents', 'getOpponents')
  _alias_method(captureAgents.CaptureAgent, 'get_team', 'getTeam')
  _alias_method(captureAgents.CaptureAgent, 'get_score', 'getScore')
  _alias_method(captureAgents.CaptureAgent, 'get_maze_distance', 'getMazeDistance')
  _alias_method(captureAgents.CaptureAgent, 'get_previous_observation', 'getPreviousObservation')
  _alias_method(captureAgents.CaptureAgent, 'get_current_observation', 'getCurrentObservation')
  _alias_method(captureAgents.CaptureAgent, 'debug_draw', 'debugDraw')
  _alias_method(captureAgents.CaptureAgent, 'debug_clear', 'debugClear')

  if not hasattr(captureAgents.CaptureAgent, '_snake_case_dispatch_installed'):
    original_register = captureAgents.CaptureAgent.registerInitialState
    original_choose = captureAgents.CaptureAgent.chooseAction
    captureAgents.CaptureAgent._original_registerInitialState = original_register
    captureAgents.CaptureAgent._original_chooseAction = original_choose

    def registerInitialState(self, gameState):
      handler = getattr(type(self), 'register_initial_state', None)
      if handler is not None and handler is not captureAgents.CaptureAgent.register_initial_state:
        return handler(self, gameState)
      return original_register(self, gameState)

    def chooseAction(self, gameState):
      handler = getattr(type(self), 'choose_action', None)
      if handler is not None:
        return handler(self, gameState)
      return original_choose(self, gameState)

    captureAgents.CaptureAgent.registerInitialState = registerInitialState
    captureAgents.CaptureAgent.chooseAction = chooseAction
    captureAgents.CaptureAgent._snake_case_dispatch_installed = True

  _INSTALLED = True
