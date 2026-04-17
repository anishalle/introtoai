# myTeam.py
# ---------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
#
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).

from captureAgents import CaptureAgent
from game import Directions
from util import nearestPoint
import util


#################
# Team creation #
#################


def createTeam(firstIndex, secondIndex, isRed,
               first='AttackerAgent', second='FlexAgent'):
  """
  Create the two default team members.
  """
  return [globals()[first](firstIndex), globals()[second](secondIndex)]


######################
# Role configuration #
######################


BASE_MODE_WEIGHTS = {
  'attack': {
    'successorScore': 220,
    'foodEaten': 120,
    'capsuleEaten': 140,
    'foodCarried': 12,
    'targetDistance': -4,
    'foodDistance': -1,
    'homeDistance': 0,
    'ghostDistance': 4,
    'ghostScared': 90,
    'capsuleDistance': -3,
    'escapeRoutes': 16,
    'inDeadEnd': -90,
    'threatPressure': -85,
    'deadEndRisk': -18,
    'timePressure': -20,
    'patrolDistance': 0,
    'lostFoodDistance': 0,
    'stop': -40,
    'reverse': -6,
    'died': -1800,
    'returnedFood': 0,
    'onDefense': 0,
    'numVisibleInvaders': 0,
    'invaderDistance': 0,
    'scoreDiff': 0,
    'oscillation': -30,
    'dangerZone': -60,
    'tunnelEntryRisk': -25,
    'chokepointCoverage': 0,
    'noisyInvaderDist': 0,
    'teammateProximity': -8,
  },
  'return': {
    'successorScore': 260,
    'foodEaten': 0,
    'capsuleEaten': 40,
    'foodCarried': 20,
    'targetDistance': -6,
    'foodDistance': 0,
    'homeDistance': -12,
    'ghostDistance': 6,
    'ghostScared': 80,
    'capsuleDistance': -5,
    'escapeRoutes': 18,
    'inDeadEnd': -120,
    'threatPressure': -95,
    'deadEndRisk': -22,
    'timePressure': -40,
    'patrolDistance': 0,
    'lostFoodDistance': 0,
    'stop': -50,
    'reverse': -8,
    'died': -2200,
    'returnedFood': 260,
    'onDefense': 0,
    'numVisibleInvaders': 0,
    'invaderDistance': 0,
    'scoreDiff': 0,
    'oscillation': -40,
    'dangerZone': -80,
    'tunnelEntryRisk': -35,
    'chokepointCoverage': 0,
    'noisyInvaderDist': 0,
    'teammateProximity': -5,
  },
  'defend': {
    'successorScore': 200,
    'foodEaten': 10,
    'capsuleEaten': 25,
    'foodCarried': 0,
    'targetDistance': -6,
    'foodDistance': 0,
    'homeDistance': 0,
    'ghostDistance': 0,
    'ghostScared': 0,
    'capsuleDistance': 0,
    'escapeRoutes': 0,
    'inDeadEnd': 0,
    'threatPressure': 0,
    'deadEndRisk': 0,
    'timePressure': 0,
    'patrolDistance': -8,
    'lostFoodDistance': -10,
    'stop': -80,
    'reverse': -10,
    'died': -500,
    'returnedFood': 0,
    'onDefense': 130,
    'numVisibleInvaders': -260,
    'invaderDistance': -18,
    'scoreDiff': 0,
    'oscillation': -20,
    'dangerZone': 0,
    'tunnelEntryRisk': 0,
    'chokepointCoverage': 8,
    'noisyInvaderDist': -6,
    'teammateProximity': -10,
  },
  'patrol': {
    'successorScore': 150,
    'foodEaten': 10,
    'capsuleEaten': 20,
    'foodCarried': 0,
    'targetDistance': -4,
    'foodDistance': 0,
    'homeDistance': 0,
    'ghostDistance': 0,
    'ghostScared': 0,
    'capsuleDistance': 0,
    'escapeRoutes': 0,
    'inDeadEnd': 0,
    'threatPressure': 0,
    'deadEndRisk': 0,
    'timePressure': 0,
    'patrolDistance': -12,
    'lostFoodDistance': -6,
    'stop': -35,
    'reverse': -6,
    'died': -400,
    'returnedFood': 0,
    'onDefense': 80,
    'numVisibleInvaders': -120,
    'invaderDistance': -10,
    'scoreDiff': 0,
    'oscillation': -20,
    'dangerZone': 0,
    'tunnelEntryRisk': 0,
    'chokepointCoverage': 10,
    'noisyInvaderDist': -4,
    'teammateProximity': -6,
  },
  'capsule': {
    'successorScore': 220,
    'foodEaten': 30,
    'capsuleEaten': 220,
    'foodCarried': 10,
    'targetDistance': -8,
    'foodDistance': 0,
    'homeDistance': 0,
    'ghostDistance': 5,
    'ghostScared': 120,
    'capsuleDistance': -12,
    'escapeRoutes': 14,
    'inDeadEnd': -80,
    'threatPressure': -70,
    'deadEndRisk': -18,
    'timePressure': -15,
    'patrolDistance': 0,
    'lostFoodDistance': 0,
    'stop': -35,
    'reverse': -6,
    'died': -1700,
    'returnedFood': 0,
    'onDefense': 0,
    'numVisibleInvaders': 0,
    'invaderDistance': 0,
    'scoreDiff': 0,
    'oscillation': -25,
    'dangerZone': -50,
    'tunnelEntryRisk': -20,
    'chokepointCoverage': 0,
    'noisyInvaderDist': 0,
    'teammateProximity': -5,
  },
}


# --- Phase 9: Learned / expert-tuned weights ---
# Set to True to blend with learned weights. Set to False to use only base + role overrides.
USE_LEARNED_WEIGHTS = True
LEARNED_WEIGHT_ALPHA = 0.6  # 60% learned, 40% hand-tuned

LEARNED_WEIGHTS = {
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



ROLE_PRESETS = {
  'attacker': {
    'return_threshold': 5,
    'food_home_penalty': 0.20,
    'prefer_patrol': False,
    'weight_overrides': {
      'attack': {
        'foodEaten': 30,
        'targetDistance': -1,
        'ghostDistance': 2,
        'capsuleDistance': -1,
      },
      'return': {
        'foodCarried': 5,
        'homeDistance': -2,
        'timePressure': -15,
      },
      'defend': {
        'onDefense': -60,
        'numVisibleInvaders': 80,
      },
      'patrol': {
        'onDefense': -40,
      },
      'capsule': {
        'capsuleEaten': 30,
      },
    },
  },
  'flex': {
    'return_threshold': 3,
    'food_home_penalty': 0.55,
    'prefer_patrol': True,
    'weight_overrides': {
      'attack': {
        'foodCarried': -4,
        'targetDistance': -2,
      },
      'return': {
        'returnedFood': 20,
        'homeDistance': -2,
      },
      'defend': {
        'onDefense': 40,
        'numVisibleInvaders': -80,
        'invaderDistance': -4,
        'lostFoodDistance': -6,
        'patrolDistance': -3,
      },
      'patrol': {
        'onDefense': 30,
        'targetDistance': -2,
        'patrolDistance': -4,
      },
      'capsule': {
        'capsuleEaten': -30,
      },
    },
  },
}


############
# Agents   #
############


class HybridAgent(CaptureAgent):
  """
  Shared one-ply reflex agent with mode switching and role-specific weights.
  """

  ROLE_KEY = 'attacker'
  _dead_end_cache = {}

  def registerInitialState(self, gameState):
    CaptureAgent.registerInitialState(self, gameState)

    self.start = gameState.getAgentPosition(self.index)
    self.roleConfig = ROLE_PRESETS[self.ROLE_KEY]
    self.teamIndices = self.getTeam(gameState)
    self.teammateIndex = [i for i in self.teamIndices if i != self.index][0]
    self.midX = gameState.data.layout.width // 2
    self.mapWidth = gameState.data.layout.width
    self.mapHeight = gameState.data.layout.height
    self.largeDistance = self.mapWidth * self.mapHeight
    self.totalMoves = gameState.data.timeleft
    self.homeBoundary = self.buildBoundary(gameState, home=True)
    self.enemyBoundary = self.buildBoundary(gameState, home=False)
    self.patrolPoints = self.buildPatrolPoints()
    self.deadEndDepth = self.getDeadEndDepth(gameState.getWalls())
    self.tunnelEntrances = self.findTunnelEntrances(gameState.getWalls())
    self.chokepoints = self.findChokepoints(gameState.getWalls())
    self.opponentIndices = self.getOpponents(gameState)
    self.enemyStart = [gameState.getInitialAgentPosition(i) for i in self.opponentIndices]

    # Action history for oscillation detection
    self.actionHistory = []
    self.positionHistory = []

    # Memory for invisible enemy estimation
    self.lastLostFood = None
    self.lastLostFoodAge = 999
    self.lastSeenInvader = None
    self.lastSeenInvaderAge = 999
    self.lastDecisionInfo = None

    # Per-turn cache (reset each turn)
    self._turnCache = {}

  def chooseAction(self, gameState):
    actions = gameState.getLegalActions(self.index)
    if not actions:
      return Directions.STOP

    try:
      self._turnCache = {}
      self.updateMemory(gameState)
      mode, messages = self.chooseMode(gameState)
      target = self.chooseTarget(gameState, mode)
      scored = []

      for action in sorted(actions):
        try:
          score, features, weights = self.evaluateAction(gameState, action, mode, target)
        except Exception:
          score = -999999
          features = {}
          weights = {}
        scored.append({
          'action': action,
          'score': score,
          'features': features,
          'weights': weights,
        })

      if not scored:
        return self.fallbackAction(gameState)

      scored = self.applySafetyOverrides(scored, gameState, mode)

      bestScore = max(item['score'] for item in scored)
      bestActions = sorted([item['action'] for item in scored if item['score'] == bestScore])
      chosen = bestActions[0]
      selected = [item for item in scored if item['action'] == chosen][0]

      # Track history for oscillation detection
      myPos = gameState.getAgentPosition(self.index)
      self.actionHistory.append(chosen)
      self.positionHistory.append(myPos)
      if len(self.actionHistory) > 8:
        self.actionHistory = self.actionHistory[-8:]
        self.positionHistory = self.positionHistory[-8:]

      self.lastDecisionInfo = {
        'mode': mode,
        'chosenAction': chosen,
        'bestActions': bestActions,
        'bestScore': bestScore,
        'selectedAction': selected,
        'scoredActions': sorted(
          scored,
          key=lambda item: (-item['score'], item['action'])
        ),
        'messages': messages,
      }
      return chosen
    except Exception:
      self.lastDecisionInfo = None
      return self.fallbackAction(gameState)

  def getLastDecisionInfo(self):
    return self.lastDecisionInfo

  def evaluateAction(self, gameState, action, mode, target):
    features = self.extractFeatures(gameState, action, mode, target)
    weights = self.getModeWeights(mode)
    return features * weights, dict(features), dict(weights)

  def extractFeatures(self, gameState, action, mode, target):
    successor = self.getSuccessor(gameState, action)
    previousState = gameState.getAgentState(self.index)
    myState = successor.getAgentState(self.index)
    myPos = myState.getPosition()
    walls = successor.getWalls()

    invaders = self.getVisibleInvaders(successor)
    invaderPositions = [pos for _, _, pos in invaders]
    foodBefore = len(self.getFood(gameState).asList())
    foodAfter = len(self.getFood(successor).asList())
    capsulesBefore = len(self.getCapsules(gameState))
    capsulesAfter = len(self.getCapsules(successor))
    threatDistance = self.getNearestThreatDistance(successor, myPos)
    ghostDistance, ghostScared = self.getNearestGhostInfo(successor, myPos)
    capsuleDistance = self.getNearestCapsuleDistance(successor, myPos)
    escapeRoutes = self.countEscapeRoutes(myPos, walls)
    lostFoodDistance = self.getLostFoodDistance(myPos)
    patrolDistance = self.getPatrolDistance(myPos)
    homeDistance = self.distanceToHome(myPos)

    features = util.Counter()
    features['successorScore'] = self.getScore(successor)
    features['foodEaten'] = max(0, foodBefore - foodAfter)
    features['capsuleEaten'] = max(0, capsulesBefore - capsulesAfter)
    features['foodCarried'] = myState.numCarrying
    features['targetDistance'] = self.distanceToTarget(myPos, target)
    features['foodDistance'] = self.distanceToClosest(
      myPos, self.getFood(successor).asList()
    )
    features['homeDistance'] = homeDistance
    features['ghostDistance'] = ghostDistance
    features['ghostScared'] = ghostScared
    features['capsuleDistance'] = capsuleDistance
    features['escapeRoutes'] = escapeRoutes
    features['inDeadEnd'] = int(self.isDeadEndPosition(myPos))
    features['threatPressure'] = self.getThreatPressure(myState, threatDistance)
    features['deadEndRisk'] = self.getDeadEndRisk(myState, myPos, threatDistance)
    features['timePressure'] = self.getTimePressure(successor, myState, homeDistance)
    features['patrolDistance'] = patrolDistance
    features['lostFoodDistance'] = lostFoodDistance
    features['stop'] = int(action == Directions.STOP)
    features['reverse'] = int(
      action == Directions.REVERSE[gameState.getAgentState(self.index).configuration.direction]
    )
    features['died'] = self.didDie(gameState, successor)
    features['returnedFood'] = self.returnedFood(previousState, myState, features['died'])
    features['onDefense'] = int(not myState.isPacman)
    features['numVisibleInvaders'] = len(invaders)
    features['invaderDistance'] = self.distanceToClosest(myPos, invaderPositions)

    # --- New features (Phases 4/6) ---
    features['scoreDiff'] = self.getScore(gameState)
    features['oscillation'] = self.getOscillationPenalty(myPos)
    features['dangerZone'] = self.getDangerZone(myState, threatDistance)
    features['tunnelEntryRisk'] = self.getTunnelEntryRisk(myState, myPos, threatDistance)
    features['chokepointCoverage'] = self.getChokepointCoverage(myPos, mode)
    features['noisyInvaderDist'] = self.getNoisyInvaderDistance(gameState, myPos, mode)
    features['teammateProximity'] = self.getTeammateProximity(gameState, myPos, mode)
    return features

  def getModeWeights(self, mode):
    base = dict(BASE_MODE_WEIGHTS[mode])
    overrides = self.roleConfig['weight_overrides'].get(mode, {})
    for key, value in overrides.items():
      base[key] = base.get(key, 0) + value

    if USE_LEARNED_WEIGHTS and mode in LEARNED_WEIGHTS:
      learned = LEARNED_WEIGHTS[mode]
      alpha = LEARNED_WEIGHT_ALPHA
      blended = {}
      all_keys = set(list(base.keys()) + list(learned.keys()))
      for key in all_keys:
        b = base.get(key, 0)
        l = learned.get(key, 0)
        blended[key] = alpha * l + (1 - alpha) * b
      return blended

    return base

  def chooseMode(self, gameState):
    myState = gameState.getAgentState(self.index)
    invaders = self.getVisibleInvaders(gameState)
    threatDistance = self.getNearestThreatDistance(
      gameState, myState.getPosition()
    )
    foodLeft = len(self.getFood(gameState).asList())
    messages = []
    score = self.getScore(gameState)
    phase = self.getGamePhase(gameState)

    if self.shouldDefend(gameState, invaders):
      messages.append('protect home food')
      return 'defend', messages

    if self.shouldReturn(gameState, threatDistance, foodLeft):
      messages.append('bank carried food')
      return 'return', messages

    if myState.isPacman and threatDistance is not None and threatDistance <= 3:
      if self.getCapsules(gameState):
        messages.append('escape toward capsule')
        return 'capsule', messages
      messages.append('retreat from visible ghost')
      return 'return', messages

    # Late-game: if winning comfortably, prefer defense/patrol
    if phase == 'late' and score >= 3 and not myState.isPacman:
      if self.ROLE_KEY == 'flex' or myState.numCarrying == 0:
        messages.append('protect lead late game')
        return 'patrol', messages

    if self.shouldPatrol(gameState, invaders):
      messages.append('hold midfield')
      return 'patrol', messages

    messages.append('pressure enemy food')
    return 'attack', messages

  def getGamePhase(self, gameState):
    timeleft = gameState.data.timeleft
    if timeleft > self.totalMoves * 0.7:
      return 'early'
    if timeleft > self.totalMoves * 0.2:
      return 'mid'
    return 'late'

  def chooseTarget(self, gameState, mode):
    myPos = gameState.getAgentPosition(self.index)

    if mode == 'attack':
      return self.chooseFoodTarget(gameState)
    if mode == 'return':
      return self.closestPoint(myPos, self.homeBoundary)
    if mode == 'capsule':
      capsuleTarget = self.chooseCapsuleTarget(gameState)
      if capsuleTarget is not None:
        return capsuleTarget
      return self.closestPoint(myPos, self.homeBoundary)
    if mode == 'defend':
      return self.chooseDefenseTarget(gameState)
    if mode == 'patrol':
      return self.choosePatrolTarget(gameState)
    return None

  def shouldDefend(self, gameState, invaders):
    myState = gameState.getAgentState(self.index)
    teammateState = gameState.getAgentState(self.teammateIndex)
    myPos = myState.getPosition()
    teammatePos = teammateState.getPosition()

    if self.ROLE_KEY == 'flex':
      if invaders:
        return True
      if not myState.isPacman and self.lastSeenInvaderAge <= 6:
        return True
      if not myState.isPacman and self.lastLostFoodAge <= 10:
        return True
      if self.shouldPatrol(gameState, invaders):
        return True
      return False

    if not invaders or myState.isPacman or myState.numCarrying > 0:
      return False

    target = self.chooseDefenseTarget(gameState)
    myDistance = self.distanceToTarget(myPos, target)
    if teammateState.isPacman or teammatePos is None:
      teammateDistance = self.largeDistance
    else:
      teammateDistance = self.distanceToTarget(teammatePos, target)
    return myDistance + 1 < teammateDistance

  def shouldReturn(self, gameState, threatDistance, foodLeft):
    myState = gameState.getAgentState(self.index)
    carrying = myState.numCarrying

    if carrying <= 0:
      return False
    if foodLeft <= 2:
      return True

    homeDistance = self.distanceToHome(myState.getPosition())
    pliesNeeded = homeDistance * gameState.getNumAgents() + 6
    if gameState.data.timeleft <= pliesNeeded:
      return True

    threshold = self.roleConfig['return_threshold']
    if self.getScore(gameState) > 0:
      threshold = max(2, threshold - 1)
    if carrying >= threshold + 2:
      return True

    if threatDistance is not None:
      if threatDistance <= 2:
        return True
      if threatDistance <= 4:
        threshold = max(1, threshold - 2)

    return carrying >= threshold

  def shouldPatrol(self, gameState, invaders):
    if not self.roleConfig['prefer_patrol']:
      return False

    myState = gameState.getAgentState(self.index)
    teammateState = gameState.getAgentState(self.teammateIndex)
    if myState.isPacman or invaders:
      return False
    if self.lastSeenInvaderAge <= 6 or self.lastLostFoodAge <= 10:
      return True
    if teammateState.isPacman and self.getScore(gameState) >= 0:
      return True
    return self.getScore(gameState) >= 2

  def chooseFoodTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    teammatePos = gameState.getAgentPosition(self.teammateIndex)
    foods = self.getFood(gameState).asList()

    if not foods:
      return self.closestPoint(myPos, self.enemyBoundary)

    threatDistance = self.getNearestThreatDistance(gameState, myPos)
    bestScore = None
    bestFood = None

    for food in foods:
      myDistance = self.distanceToTarget(myPos, food)
      teammatePenalty = 0
      if teammatePos is not None:
        teammateDistance = self.distanceToTarget(teammatePos, food)
        if teammateDistance + 1 < myDistance:
          teammatePenalty = 3

      homePenalty = self.roleConfig['food_home_penalty'] * self.distancePointToHome(food)
      deadEndPenalty = 0
      if threatDistance is not None:
        deadEndPenalty = self.deadEndDepth.get(food, 0) * max(0, 5 - threatDistance)

      score = myDistance + teammatePenalty + homePenalty + deadEndPenalty
      if bestScore is None or score < bestScore:
        bestScore = score
        bestFood = food

    return bestFood

  def chooseCapsuleTarget(self, gameState):
    capsules = self.getCapsules(gameState)
    if not capsules:
      return None
    return self.closestPoint(gameState.getAgentPosition(self.index), capsules)

  def chooseDefenseTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    invaders = self.getVisibleInvaders(gameState)

    if invaders:
      weighted = []
      for _, state, pos in invaders:
        priority = self.distanceToTarget(myPos, pos) - (4 * state.numCarrying)
        weighted.append((priority, pos))
      weighted.sort()
      return weighted[0][1]

    if self.lastSeenInvader is not None and self.lastSeenInvaderAge <= 6:
      return self.lastSeenInvader
    if self.lastLostFood is not None and self.lastLostFoodAge <= 12:
      return self.lastLostFood
    return self.choosePatrolTarget(gameState)

  def choosePatrolTarget(self, gameState):
    if self.lastLostFood is not None and self.lastLostFoodAge <= 12:
      return self.closestPoint(self.lastLostFood, self.homeBoundary)
    if self.lastSeenInvader is not None and self.lastSeenInvaderAge <= 6:
      return self.closestPoint(self.lastSeenInvader, self.homeBoundary)
    if self.patrolPoints:
      myPos = gameState.getAgentPosition(self.index)
      return self.closestPoint(myPos, self.patrolPoints)
    return self.start

  def updateMemory(self, gameState):
    self.lastLostFoodAge += 1
    self.lastSeenInvaderAge += 1

    invaders = self.getVisibleInvaders(gameState)
    if invaders:
      myPos = gameState.getAgentPosition(self.index)
      invaders.sort(
        key=lambda item: (
          self.distanceToTarget(myPos, item[2]),
          -item[1].numCarrying,
          item[0],
        )
      )
      self.lastSeenInvader = invaders[0][2]
      self.lastSeenInvaderAge = 0

    previous = self.getPreviousObservation()
    if previous is not None:
      previousFood = set(self.getFoodYouAreDefending(previous).asList())
      currentFood = set(self.getFoodYouAreDefending(gameState).asList())
      eaten = list(previousFood - currentFood)
      if eaten:
        myPos = gameState.getAgentPosition(self.index)
        eaten.sort(key=lambda pos: (self.distanceToTarget(myPos, pos), pos))
        self.lastLostFood = eaten[0]
        self.lastLostFoodAge = 0

    myPos = gameState.getAgentPosition(self.index)
    if self.lastSeenInvader is not None and myPos == self.lastSeenInvader:
      self.lastSeenInvaderAge = 999
    if self.lastLostFood is not None and myPos == self.lastLostFood:
      self.lastLostFoodAge = 999

  def fallbackAction(self, gameState):
    actions = gameState.getLegalActions(self.index)
    if not actions:
      return Directions.STOP

    candidates = sorted([action for action in actions if action != Directions.STOP])
    if not candidates:
      candidates = sorted(actions)

    try:
      myState = gameState.getAgentState(self.index)
      if myState.numCarrying > 0:
        ranked = []
        for action in candidates:
          successor = self.getSuccessor(gameState, action)
          pos = successor.getAgentState(self.index).getPosition()
          ranked.append((self.distanceToHome(pos), action))
        ranked.sort()
        return ranked[0][1]
    except Exception:
      pass

    return candidates[0]

  def getSuccessor(self, gameState, action):
    successor = gameState.generateSuccessor(self.index, action)
    pos = successor.getAgentState(self.index).getPosition()
    if pos != nearestPoint(pos):
      return successor.generateSuccessor(self.index, action)
    return successor

  def getVisibleOpponents(self, gameState):
    opponents = []
    for opponent in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(opponent)
      pos = enemyState.getPosition()
      if pos is not None:
        opponents.append((opponent, enemyState, pos))
    return opponents

  def getVisibleInvaders(self, gameState):
    return [
      item for item in self.getVisibleOpponents(gameState)
      if item[1].isPacman
    ]

  def getVisibleThreats(self, gameState):
    threats = []
    for _, enemyState, pos in self.getVisibleOpponents(gameState):
      if enemyState.isPacman:
        continue
      if enemyState.scaredTimer > 1:
        continue
      threats.append(pos)
    return threats

  def getVisibleGhosts(self, gameState):
    ghosts = []
    for _, enemyState, pos in self.getVisibleOpponents(gameState):
      if enemyState.isPacman:
        continue
      ghosts.append((enemyState, pos))
    return ghosts

  def getNearestThreatDistance(self, gameState, myPos):
    myState = gameState.getAgentState(self.index)
    if myPos is None or not myState.isPacman:
      return None

    threats = self.getVisibleThreats(gameState)
    if not threats:
      return None
    return min(self.getMazeDistance(myPos, pos) for pos in threats)

  def getNearestGhostInfo(self, gameState, myPos):
    if myPos is None:
      return 0, 0

    ghosts = self.getVisibleGhosts(gameState)
    if not ghosts:
      return 0, 0

    ranked = []
    for ghostState, pos in ghosts:
      ranked.append((self.getMazeDistance(myPos, pos), ghostState.scaredTimer, pos))
    ranked.sort()
    distance, scaredTimer, _ = ranked[0]
    return min(distance, 8), int(scaredTimer > 1)

  def getNearestCapsuleDistance(self, gameState, myPos):
    capsules = self.getCapsules(gameState)
    if myPos is None or not capsules:
      return 0
    return min(self.getMazeDistance(myPos, capsule) for capsule in capsules)

  def countEscapeRoutes(self, pos, walls):
    if pos is None:
      return 0

    x, y = int(pos[0]), int(pos[1])
    safeNeighbors = 0
    openNeighbors = 0

    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
      nx, ny = x + dx, y + dy
      if nx < 0 or ny < 0 or nx >= walls.width or ny >= walls.height:
        continue
      if walls[nx][ny]:
        continue
      openNeighbors += 1
      if self.deadEndDepth.get((nx, ny), 0) <= 1:
        safeNeighbors += 1

    if safeNeighbors > 0:
      return safeNeighbors
    return openNeighbors

  def isDeadEndPosition(self, pos):
    if pos is None:
      return False
    return self.deadEndDepth.get((int(pos[0]), int(pos[1])), 0) >= 2

  def getThreatPressure(self, myState, threatDistance):
    if not myState.isPacman or threatDistance is None:
      return 0
    return max(0, 6 - threatDistance)

  def getDeadEndRisk(self, myState, myPos, threatDistance):
    if not myState.isPacman or myPos is None or threatDistance is None:
      return 0
    if threatDistance > 4:
      return 0
    return self.deadEndDepth.get(myPos, 0) * max(0, 5 - threatDistance)

  def getTimePressure(self, successor, myState, homeDistance):
    if homeDistance <= 0:
      return 0
    if myState.numCarrying <= 0 and successor.data.timeleft > 80:
      return 0

    requiredPlies = homeDistance * successor.getNumAgents() + 6
    return max(0, requiredPlies - successor.data.timeleft)

  def getLostFoodDistance(self, myPos):
    if myPos is None or self.lastLostFood is None or self.lastLostFoodAge > 12:
      return 0
    return self.distanceToTarget(myPos, self.lastLostFood)

  def getPatrolDistance(self, myPos):
    return self.distanceToClosest(myPos, self.patrolPoints)

  def didDie(self, gameState, successor):
    previousState = gameState.getAgentState(self.index)
    nextState = successor.getAgentState(self.index)
    previousPos = previousState.getPosition()
    nextPos = nextState.getPosition()

    if nextPos != self.start or previousPos == self.start:
      return 0
    if previousState.isPacman and not nextState.isPacman and self.distanceToHome(previousPos) > 1:
      return 1
    if previousState.numCarrying > 0 and nextState.numCarrying == 0:
      return 1
    return 0

  def returnedFood(self, previousState, myState, died):
    if died:
      return 0
    if previousState.numCarrying <= myState.numCarrying:
      return 0
    if myState.isPacman:
      return 0
    return previousState.numCarrying - myState.numCarrying

  def distanceToHome(self, pos):
    if pos is None or self.isHome(pos):
      return 0
    return min(self.getMazeDistance(pos, point) for point in self.homeBoundary)

  def distancePointToHome(self, pos):
    if not self.homeBoundary:
      return 0
    return min(self.getMazeDistance(pos, point) for point in self.homeBoundary)

  def distanceToClosest(self, source, points):
    if source is None or not points:
      return 0
    return min(self.getMazeDistance(source, point) for point in points)

  def distanceToTarget(self, source, target):
    if source is None or target is None:
      return 0
    return self.getMazeDistance(source, target)

  def closestPoint(self, source, points):
    if not points:
      return None
    ranked = []
    for point in points:
      ranked.append((self.distanceToTarget(source, point), point))
    ranked.sort()
    return ranked[0][1]

  def isHome(self, pos):
    if self.red:
      return pos[0] < self.midX
    return pos[0] >= self.midX

  def buildBoundary(self, gameState, home):
    walls = gameState.getWalls()
    x = self.midX - 1 if self.red == home else self.midX
    boundary = []
    for y in range(1, walls.height - 1):
      if not walls[x][y]:
        boundary.append((x, y))
    if not boundary:
      boundary.append(self.start)
    return boundary

  def buildPatrolPoints(self):
    ordered = sorted(self.homeBoundary, key=lambda point: point[1])
    if len(ordered) <= 3:
      return ordered

    indices = [
      len(ordered) // 4,
      len(ordered) // 2,
      (3 * len(ordered)) // 4,
    ]
    points = []
    for index in indices:
      point = ordered[index]
      if point not in points:
        points.append(point)
    return points

  @classmethod
  def getDeadEndDepth(cls, walls):
    key = (walls.width, walls.height, tuple(walls.asList()))
    if key in cls._dead_end_cache:
      return cls._dead_end_cache[key]

    neighbors = {}
    for x in range(walls.width):
      for y in range(walls.height):
        if walls[x][y]:
          continue
        cell = (x, y)
        adjacent = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
          nx, ny = x + dx, y + dy
          if 0 <= nx < walls.width and 0 <= ny < walls.height and not walls[nx][ny]:
            adjacent.append((nx, ny))
        neighbors[cell] = adjacent

    degree = {}
    for cell, adjacent in neighbors.items():
      degree[cell] = len(adjacent)
    originalDegree = dict(degree)

    queue = [cell for cell, count in degree.items() if count == 1]
    removed = set(queue)
    depth = {}
    for cell in queue:
      depth[cell] = 1

    while queue:
      cell = queue.pop(0)
      for neighbor in neighbors[cell]:
        if neighbor in removed:
          continue
        degree[neighbor] -= 1
        if degree[neighbor] == 1 and originalDegree[neighbor] == 2:
          depth[neighbor] = depth[cell] + 1
          removed.add(neighbor)
          queue.append(neighbor)

    cls._dead_end_cache[key] = depth
    return depth

  # --- Phase 3: Precomputation methods ---

  def findTunnelEntrances(self, walls):
    """Find cells that are the entrance to dead-end tunnels (depth >= 2)."""
    entrances = set()
    for cell, depth in self.deadEndDepth.items():
      if depth >= 2:
        x, y = cell
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
          nx, ny = x + dx, y + dy
          neighbor = (nx, ny)
          if neighbor not in self.deadEndDepth or self.deadEndDepth[neighbor] == 0:
            if 0 <= nx < walls.width and 0 <= ny < walls.height and not walls[nx][ny]:
              entrances.add(neighbor)
    return entrances

  def findChokepoints(self, walls):
    """Find narrow corridor positions useful for defensive patrolling."""
    chokepoints = []
    for pos in self.homeBoundary:
      x, y = int(pos[0]), int(pos[1])
      openNeighbors = 0
      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < walls.width and 0 <= ny < walls.height and not walls[nx][ny]:
          openNeighbors += 1
      if openNeighbors <= 2:
        chokepoints.append(pos)
    if not chokepoints:
      chokepoints = list(self.homeBoundary)
    return chokepoints

  # --- Phase 4: New feature helper methods ---

  def getOscillationPenalty(self, myPos):
    """Penalize revisiting recent positions (anti-oscillation)."""
    if myPos is None or len(self.positionHistory) < 2:
      return 0
    count = 0
    for past in self.positionHistory[-4:]:
      if past == myPos:
        count += 1
    return count

  def getDangerZone(self, myState, threatDistance):
    """1 if pacman and within 2 of a non-scared ghost."""
    if not myState.isPacman or threatDistance is None:
      return 0
    return int(threatDistance <= 2)

  def getTunnelEntryRisk(self, myState, myPos, threatDistance):
    """Penalty for entering tunnel-adjacent positions when ghost is near."""
    if not myState.isPacman or myPos is None or threatDistance is None:
      return 0
    if threatDistance > 5:
      return 0
    depth = self.deadEndDepth.get((int(myPos[0]), int(myPos[1])), 0)
    if depth >= 1 and myPos in self.tunnelEntrances:
      return max(0, 6 - threatDistance) * 2
    return depth * max(0, 5 - threatDistance)

  def getChokepointCoverage(self, myPos, mode):
    """Reward being near chokepoints when defending/patrolling."""
    if mode not in ('defend', 'patrol') or myPos is None:
      return 0
    if not self.chokepoints:
      return 0
    return -min(self.getMazeDistance(myPos, cp) for cp in self.chokepoints)

  def getNoisyInvaderDistance(self, gameState, myPos, mode):
    """Estimate distance to closest invisible enemy using noisy distances."""
    if mode not in ('defend', 'patrol') or myPos is None:
      return 0
    agentDistances = gameState.getAgentDistances()
    if agentDistances is None:
      return 0
    bestDist = self.largeDistance
    for idx in self.opponentIndices:
      enemyState = gameState.getAgentState(idx)
      if enemyState.getPosition() is not None:
        continue
      dist = agentDistances[idx]
      if dist is not None and dist < bestDist:
        bestDist = dist
    if bestDist >= self.largeDistance:
      return 0
    return max(0, bestDist)

  def getTeammateProximity(self, gameState, myPos, mode):
    """Penalize being too close to teammate to avoid crowding."""
    if myPos is None:
      return 0
    teammatePos = gameState.getAgentPosition(self.teammateIndex)
    if teammatePos is None:
      return 0
    dist = self.getMazeDistance(myPos, teammatePos)
    if dist >= 6:
      return 0
    return max(0, 6 - dist)

  # --- Phase 5: Safety overrides ---

  def applySafetyOverrides(self, scored, gameState, mode):
    """Apply hard safety rules on top of learned/weighted scores."""
    myState = gameState.getAgentState(self.index)
    myPos = myState.getPosition()
    threatDistance = self.getNearestThreatDistance(gameState, myPos)
    carrying = myState.numCarrying
    phase = self.getGamePhase(gameState)
    score = self.getScore(gameState)

    for item in scored:
      action = item['action']
      try:
        successor = self.getSuccessor(gameState, action)
        succPos = successor.getAgentState(self.index).getPosition()
      except Exception:
        continue

      # 1. Dead-end trap prevention: never enter deep dead ends with ghost nearby
      if myState.isPacman and threatDistance is not None and threatDistance <= 5:
        depth = self.deadEndDepth.get(
          (int(succPos[0]), int(succPos[1])), 0
        ) if succPos else 0
        if depth >= 3 and threatDistance <= depth + 2:
          item['score'] -= 5000

      # 2. Carrying food retreat: strongly prefer going home when loaded + threatened
      if carrying >= 4 and myState.isPacman and threatDistance is not None and threatDistance <= 4:
        succHome = self.distanceToHome(succPos)
        currHome = self.distanceToHome(myPos)
        if succHome < currHome:
          item['score'] += 200
        elif succHome > currHome:
          item['score'] -= 150

      # 3. STOP penalty enforcement
      if action == Directions.STOP:
        if mode in ('attack', 'return', 'capsule'):
          item['score'] -= 100
        if mode == 'defend' and not self.getVisibleInvaders(gameState):
          item['score'] -= 60

      # 4. Oscillation breaker
      if len(self.positionHistory) >= 4:
        if succPos in self.positionHistory[-3:]:
          item['score'] -= 50
        if (len(self.positionHistory) >= 4 and
            succPos == self.positionHistory[-2] and
            myPos == self.positionHistory[-3]):
          item['score'] -= 200

      # 5. Late-game defense: penalize crossing midline when winning
      if phase == 'late' and score >= 5 and self.ROLE_KEY == 'flex':
        succState = successor.getAgentState(self.index)
        if succState.isPacman and not myState.isPacman:
          item['score'] -= 300

      # 6. Late-game aggression when losing
      if phase == 'late' and score <= -3 and mode == 'attack':
        succHome = self.distanceToHome(succPos)
        currHome = self.distanceToHome(myPos)
        foodDist = self.distanceToClosest(
          succPos, self.getFood(gameState).asList()
        )
        if foodDist > 0:
          item['score'] += max(0, 10 - foodDist) * 5

      # 7. Capsule bonus when ghost is close and capsule is reachable
      if myState.isPacman and threatDistance is not None and threatDistance <= 4:
        capsules = self.getCapsules(gameState)
        if capsules:
          capDist = min(
            self.getMazeDistance(succPos, c) for c in capsules
          ) if succPos else 999
          if capDist <= threatDistance:
            item['score'] += 150

    return scored

  # --- Phase 6: Enhanced teammate coordination ---

  def getTeammateZone(self, gameState):
    """Determine which zone (top/bottom) the teammate is targeting."""
    teammatePos = gameState.getAgentPosition(self.teammateIndex)
    if teammatePos is None:
      return None
    midY = self.mapHeight // 2
    return 'top' if teammatePos[1] >= midY else 'bottom'


class AttackerAgent(HybridAgent):
  ROLE_KEY = 'attacker'

  def chooseFoodTarget(self, gameState):
    """Override to prefer food zone away from teammate."""
    myPos = gameState.getAgentPosition(self.index)
    teammatePos = gameState.getAgentPosition(self.teammateIndex)
    foods = self.getFood(gameState).asList()

    if not foods:
      return self.closestPoint(myPos, self.enemyBoundary)

    midY = self.mapHeight // 2
    teammateZone = self.getTeammateZone(gameState)
    threatDistance = self.getNearestThreatDistance(gameState, myPos)
    bestScore = None
    bestFood = None

    for food in foods:
      myDistance = self.distanceToTarget(myPos, food)
      teammatePenalty = 0
      if teammatePos is not None:
        teammateDistance = self.distanceToTarget(teammatePos, food)
        if teammateDistance + 1 < myDistance:
          teammatePenalty = 3

      # Zone-based splitting: prefer food in opposite zone from teammate
      zonePenalty = 0
      if teammateZone is not None:
        foodZone = 'top' if food[1] >= midY else 'bottom'
        if foodZone == teammateZone:
          zonePenalty = 2

      homePenalty = self.roleConfig['food_home_penalty'] * self.distancePointToHome(food)
      deadEndPenalty = 0
      if threatDistance is not None:
        deadEndPenalty = self.deadEndDepth.get(food, 0) * max(0, 5 - threatDistance)

      score = myDistance + teammatePenalty + zonePenalty + homePenalty + deadEndPenalty
      if bestScore is None or score < bestScore:
        bestScore = score
        bestFood = food

    return bestFood


class FlexAgent(HybridAgent):
  ROLE_KEY = 'flex'

  def shouldDefend(self, gameState, invaders):
    """Enhanced defense logic with better teammate awareness."""
    myState = gameState.getAgentState(self.index)
    teammateState = gameState.getAgentState(self.teammateIndex)

    # Always defend if invaders visible
    if invaders:
      # But if teammate is closer to all invaders and not pacman, skip
      if not teammateState.isPacman and teammateState.getPosition() is not None:
        myPos = myState.getPosition()
        tmPos = teammateState.getPosition()
        allCloser = True
        for _, _, iPos in invaders:
          if self.distanceToTarget(myPos, iPos) <= self.distanceToTarget(tmPos, iPos):
            allCloser = False
            break
        if not allCloser:
          return True
      return True

    if not myState.isPacman and self.lastSeenInvaderAge <= 6:
      return True
    if not myState.isPacman and self.lastLostFoodAge <= 10:
      return True

    # Defend more aggressively when teammate is attacking
    if teammateState.isPacman and self.getScore(gameState) >= 0:
      return not myState.isPacman

    return False
