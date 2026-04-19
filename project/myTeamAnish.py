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

# anish reddy alle & purva patel

from captureAgents import CaptureAgent
from game import Directions
import util


TEAM_MEMORY = {}


# sets up our two pacman agents for the game
def createTeam(firstIndex, secondIndex, isRed,
               first='HybridCaptureAgent', second='HybridCaptureAgent'):
  """
  return the two agents that make up the team.
  """
  return [
    loadAgentClass(first)(firstIndex, slot=0),
    loadAgentClass(second)(secondIndex, slot=1),
  ]


def loadAgentClass(className):
  try:
    return globals()[className]
  except KeyError as exc:
    raise ValueError('Unknown agent class: %s' % className) from exc


class HybridCaptureAgent(CaptureAgent):
  """
  shared-belief, intent-switching capture agent.
  """

  def __init__(self, index, slot=0, timeForComputing=.1):
    CaptureAgent.__init__(self, index, timeForComputing=timeForComputing)
    self.slot = slot
    self.start = None
    self.teamKey = None
    self.shared = None
    self.lastDecisionInfo = {}

  # runs once at the start of the game to prep the map and shared memory
  def registerInitialState(self, gameState):
    CaptureAgent.registerInitialState(self, gameState)
    self.start = gameState.getAgentPosition(self.index)
    layoutKey = hash(gameState.getWalls())
    self.teamKey = (self.red, tuple(sorted(self.getTeam(gameState))), layoutKey)
    if self.teamKey not in TEAM_MEMORY:
      TEAM_MEMORY[self.teamKey] = self.buildTeamMemory(gameState)
    self.shared = TEAM_MEMORY[self.teamKey]
    self.shared['agent_slots'][self.index] = self.slot
    self.shared['agent_starts'][self.index] = self.start
    self.shared['last_food_defending'] = set(self.getFoodYouAreDefending(gameState).asList())
    self.shared['last_capsules_defending'] = set(self.getCapsulesYouAreDefending(gameState))

  def getLastDecisionInfo(self):
    return self.lastDecisionInfo

  # decision driver 

  # main loop: figures out what the agent should do this turn
  def chooseAction(self, gameState):
    self.updateSharedState(gameState)

    legalActions = gameState.getLegalActions(self.index)
    if len(legalActions) == 1:
      action = legalActions[0]
      self.recordDecision(gameState, 'forced', None, action, {})
      return action

    modeMap = self.assignRoles(gameState)
    mode = modeMap[self.index]
    target, targetKind = self.pickTarget(gameState, mode)
    plan = self.planToTarget(gameState, target, mode)
    actionScores = self.scoreActions(gameState, legalActions, mode, target, plan)

    if self.shouldUseTacticalSearch(gameState, mode):
      actionScores = self.applyTacticalSearch(gameState, actionScores, mode, target)

    bestScore = max(actionScores.values())
    bestActions = [action for action in legalActions if actionScores[action] == bestScore]
    action = sorted(bestActions)[0]

    self.shared['agent_modes'][self.index] = mode
    self.shared['agent_goals'][self.index] = target
    self.shared['agent_goal_kinds'][self.index] = targetKind
    self.shared['agent_paths'][self.index] = plan
    self.recordDecision(gameState, mode, target, action, actionScores)
    return action

  
  #shared state / beliefs 

  # scans the whole board to figure out distances, borders, and dead ends
  def buildTeamMemory(self, gameState):
    walls = gameState.getWalls()
    width = walls.width
    height = walls.height
    legalPositions = []
    neighbors = {}

    for x in range(width):
      for y in range(height):
        if walls[x][y]:
          continue
        pos = (x, y)
        legalPositions.append(pos)
        neighbors[pos] = self.getStaticNeighbors(pos, walls)

    homePositions = set([pos for pos in legalPositions if self.isHomePosition(pos, width=width)])
    enemyPositions = set(legalPositions) - homePositions
    homeBorder = self.computeBorderCells(legalPositions, width)
    homeDistance = {}
    bestBorder = {}
    for pos in legalPositions:
      border = min(homeBorder, key=lambda cell: self.getMazeDistance(pos, cell))
      bestBorder[pos] = border
      homeDistance[pos] = self.getMazeDistance(pos, border)

    patrolPoints = self.computePatrolPoints(gameState, homeBorder)
    deadEndDepth = self.computeDeadEndDepth(neighbors)

    opponents = self.getOpponents(gameState)
    beliefs = {}
    enemyPacman = {}
    for enemy in opponents:
      beliefs[enemy] = util.Counter()
      beliefs[enemy][gameState.getInitialAgentPosition(enemy)] = 1.0
      enemyPacman[enemy] = gameState.getAgentState(enemy).isPacman

    return {
      'width': width,
      'height': height,
      'neighbors': neighbors,
      'legal_positions': legalPositions,
      'home_positions': homePositions,
      'enemy_positions': enemyPositions,
      'home_border': homeBorder,
      'home_distance': homeDistance,
      'best_border': bestBorder,
      'patrol_points': patrolPoints,
      'dead_end_depth': deadEndDepth,
      'beliefs': beliefs,
      'enemy_pacman': enemyPacman,
      'recent_events': [],
      'agent_goals': {},
      'agent_goal_kinds': {},
      'agent_modes': {},
      'agent_paths': {},
      'agent_slots': {},
      'agent_starts': {},
      'updates': 0,
      'last_food_defending': set(),
      'last_capsules_defending': set(),
      'contest_length': gameState.data.timeleft,
    }

  # syncs what this agent sees with what the teammate sees
  def updateSharedState(self, gameState):
    self.decayRecentEvents()
    self.trackFoodDefenseEvents(gameState)
    self.updateBeliefs(gameState)
    self.shared['updates'] += 1

  # slowly forgets about old events like eaten food over time
  def decayRecentEvents(self):
    kept = []
    for event in self.shared['recent_events']:
      ttl = event['ttl'] - 1
      if ttl > 0:
        kept.append({'pos': event['pos'], 'ttl': ttl, 'kind': event['kind']})
    self.shared['recent_events'] = kept

  # checks if our food disappeared so we know where enemies are
  def trackFoodDefenseEvents(self, gameState):
    currentFood = set(self.getFoodYouAreDefending(gameState).asList())
    currentCapsules = set(self.getCapsulesYouAreDefending(gameState))
    missingFood = self.shared['last_food_defending'] - currentFood
    missingCapsules = self.shared['last_capsules_defending'] - currentCapsules

    for pos in missingFood:
      self.shared['recent_events'].append({'pos': pos, 'ttl': 8, 'kind': 'food'})
    for pos in missingCapsules:
      self.shared['recent_events'].append({'pos': pos, 'ttl': 12, 'kind': 'capsule'})

    self.shared['last_food_defending'] = currentFood
    self.shared['last_capsules_defending'] = currentCapsules

  # guesses where invisible enemies are hiding using probabilities
  def updateBeliefs(self, gameState):
    lastMoved = getattr(gameState.data, '_agentMoved', None)
    teammatePositions = [gameState.getAgentPosition(agent) for agent in self.getTeam(gameState)]
    opponents = self.getOpponents(gameState)

    for enemy in opponents:
      enemyState = gameState.getAgentState(enemy)
      visiblePos = gameState.getAgentPosition(enemy)
      previousWasPacman = self.shared['enemy_pacman'].get(enemy, enemyState.isPacman)

      if visiblePos is not None:
        belief = util.Counter()
        belief[visiblePos] = 1.0
      else:
        belief = self.shared['beliefs'][enemy].copy()

        if self.shared['updates'] > 0 and lastMoved == enemy:
          belief = self.propagateBelief(belief)

        if previousWasPacman and not enemyState.isPacman:
          belief = util.Counter()
          belief[gameState.getInitialAgentPosition(enemy)] = 1.0

        belief = self.filterBelief(gameState, belief, enemyState.isPacman, teammatePositions)
        belief = self.anchorBeliefToEvents(gameState, belief, enemy, enemyState.isPacman)
        if belief.totalCount() == 0:
          belief = self.seedFallbackBelief(gameState, enemyState.isPacman, teammatePositions)

      belief.normalize()
      self.shared['beliefs'][enemy] = belief
      self.shared['enemy_pacman'][enemy] = enemyState.isPacman

  # spreads out our guesses of where the enemy moved
  def propagateBelief(self, belief):
    newBelief = util.Counter()
    for pos, prob in belief.items():
      nextPositions = [pos] + self.shared['neighbors'].get(pos, [])
      split = prob / float(len(nextPositions))
      for nextPos in nextPositions:
        newBelief[nextPos] += split
    return newBelief

  # removes places the enemy definitely can't be
  def filterBelief(self, gameState, belief, enemyIsPacman, teammatePositions):
    allowed = self.shared['home_positions'] if enemyIsPacman else self.shared['enemy_positions']
    filtered = util.Counter()
    for pos, prob in belief.items():
      if pos not in allowed:
        continue
      if any(util.manhattanDistance(pos, teammatePos) <= 5 for teammatePos in teammatePositions if teammatePos is not None):
        continue
      filtered[pos] += prob
    return filtered

  # heavily updates our guesses if we saw them eat something
  def anchorBeliefToEvents(self, gameState, belief, enemy, enemyIsPacman):
    if belief.totalCount() == 0:
      return belief
    if not enemyIsPacman:
      return belief

    eventPositions = [event['pos'] for event in self.shared['recent_events']]
    if not eventPositions:
      return belief

    anchored = belief.copy()
    matched = False
    for pos in eventPositions:
      if pos in anchored:
        anchored[pos] += 4.0
        matched = True
      for neighbor in self.shared['neighbors'].get(pos, []):
        if neighbor in anchored:
          anchored[neighbor] += 1.0
          matched = True
    if matched:
      return anchored
    return belief

  # if we completely lose the enemy, just guess they could be anywhere on their side
  def seedFallbackBelief(self, gameState, enemyIsPacman, teammatePositions):
    allowed = self.shared['home_positions'] if enemyIsPacman else self.shared['enemy_positions']
    belief = util.Counter()
    for pos in allowed:
      if any(util.manhattanDistance(pos, teammatePos) <= 5 for teammatePos in teammatePositions if teammatePos is not None):
        continue
      belief[pos] = 1.0
    if belief.totalCount() == 0:
      for pos in allowed:
        belief[pos] = 1.0
    return belief

  # role assignment

  # decides who attacks and who defends based on the current score and threats
  def assignRoles(self, gameState):
    team = self.getTeam(gameState)
    invaders = [enemy for enemy in self.getOpponents(gameState)
                if gameState.getAgentState(enemy).isPacman]
    visibleInvaders = [enemy for enemy in invaders
                       if gameState.getAgentPosition(enemy) is not None]
    threatTarget = self.primaryThreatTarget(gameState)
    score = self.getScore(gameState)
    ownMovesLeft = self.ownMovesLeft(gameState)
    offensiveWindow = self.maxEnemyScaredTimer(gameState) >= 8
    openingPhase = self.inOpeningPhase(gameState)
    latePhase = self.inLatePhase(gameState)

    needDefenders = 0
    if invaders:
      needDefenders = 1
      if len(invaders) > 1 or (score >= 2 and latePhase):
        needDefenders = 2
    elif self.shared['recent_events'] and not openingPhase:
      needDefenders = 1
    elif latePhase and score >= 2 and not offensiveWindow:
      needDefenders = 1
    elif score >= 5 and ownMovesLeft <= 35:
      needDefenders = 2

    if openingPhase and not invaders and not self.shared['recent_events']:
      needDefenders = 0
    elif score <= -2 and not invaders and not self.shared['recent_events']:
      needDefenders = 0
    if offensiveWindow and score < 6 and not invaders:
      needDefenders = 0

    defenseOrder = sorted(
      team,
      key=lambda agent: self.defensePriority(gameState, agent, visibleInvaders, threatTarget),
    )
    defenders = set()
    if threatTarget is not None and needDefenders > 0:
      defenders.add(defenseOrder[0])
      needDefenders -= 1
    defenders.update(defenseOrder[:needDefenders])

    modes = {}
    for agent in team:
      if self.mustRetreatAgent(gameState, agent) and agent not in defenders:
        modes[agent] = 'retreat'
      elif agent in defenders:
        modes[agent] = 'intercept' if invaders or self.shared['recent_events'] else 'patrol'
      else:
        modes[agent] = 'attack'

    if modes[self.index] == 'attack' and self.slot == 1 and score >= 5 and ownMovesLeft <= 30 and not invaders:
      modes[self.index] = 'patrol'
    return modes

  # scores how urgently this agent needs to go back and defend
  def defensePriority(self, gameState, agentIndex, visibleInvaders, threatTarget=None):
    agentState = gameState.getAgentState(agentIndex)
    agentSlot = self.shared['agent_slots'].get(agentIndex, 0)
    pos = gameState.getAgentPosition(agentIndex)
    carryingPenalty = agentState.numCarrying * 4
    pacmanPenalty = 12 if agentState.isPacman else 0
    homeDist = self.shared['home_distance'].get(pos, 0) if pos is not None else 0
    targetDist = 0

    if visibleInvaders and pos is not None:
      targetDist = min(self.getMazeDistance(pos, gameState.getAgentPosition(enemy))
                       for enemy in visibleInvaders)
    elif threatTarget is not None and pos is not None:
      targetDist = self.getMazeDistance(pos, threatTarget)
    elif self.shared['recent_events'] and pos is not None:
      targetDist = min(self.getMazeDistance(pos, event['pos']) for event in self.shared['recent_events'])

    return carryingPenalty + pacmanPenalty + homeDist + targetDist - (2 if agentSlot == 1 else 0)

  # checks if the agent is carrying too much food or is in danger and needs to run home
  def mustRetreatAgent(self, gameState, agentIndex):
    agentState = gameState.getAgentState(agentIndex)
    pos = gameState.getAgentPosition(agentIndex)
    if pos is None:
      return False

    carrying = agentState.numCarrying
    if carrying <= 0:
      return False

    homeDist = self.shared['home_distance'][pos]
    ownMovesLeft = self.ownMovesLeft(gameState)
    if ownMovesLeft <= homeDist + 2:
      return True

    foodLeft = len(self.getFood(gameState).asList())
    if foodLeft <= 2:
      return True

    visibleThreatDist = self.closestVisibleDangerDistance(gameState, pos)
    score = self.getScore(gameState)
    scaredWindow = self.maxEnemyScaredTimer(gameState)

    threshold = 5 if self.inOpeningPhase(gameState) else 4
    if ownMovesLeft <= 60:
      threshold -= 1
    if ownMovesLeft <= 35:
      threshold -= 1
    if score >= 4:
      threshold -= 1
    if score <= -4 and scaredWindow < 6:
      threshold += 1
    if homeDist >= 7:
      threshold -= 1
    if visibleThreatDist is not None and visibleThreatDist <= 5:
      threshold -= 2
    if scaredWindow >= 8 and visibleThreatDist is None:
      threshold += 1
    threshold = max(2, threshold)

    if carrying >= threshold:
      return True
    if carrying >= 5:
      return True
    if carrying >= 3 and homeDist >= 7:
      return True
    if visibleThreatDist is not None and visibleThreatDist <= 4:
      return True
    if carrying >= 1 and ownMovesLeft <= homeDist + 6:
      return True
    if carrying >= 2 and ownMovesLeft <= (homeDist * 2) + 2:
      return True
    if carrying >= 2 and homeDist >= 6 and visibleThreatDist is not None and visibleThreatDist <= 6:
      return True
    return False

  # target selection

  # routes the agent to the right target depending on their current role
  def pickTarget(self, gameState, mode):
    if mode == 'retreat':
      return self.pickRetreatTarget(gameState), 'border'
    if mode == 'intercept':
      return self.pickInterceptTarget(gameState), 'intercept'
    if mode == 'patrol':
      return self.pickPatrolTarget(gameState), 'patrol'
    return self.pickAttackTarget(gameState)

  # finds the safest way back home to deposit food
  def pickRetreatTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    bestTarget = None
    bestScore = None
    for border in self.shared['home_border']:
      score = self.getMazeDistance(myPos, border) + 2.0 * self.positionRisk(gameState, border)
      if bestScore is None or score < bestScore:
        bestScore = score
        bestTarget = border
    return bestTarget

  # tries to cut off the enemy pacman by guessing where they will go
  def pickInterceptTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    invaders = [enemy for enemy in self.getOpponents(gameState)
                if gameState.getAgentState(enemy).isPacman]

    candidateTargets = []
    for enemy in invaders:
      pos = gameState.getAgentPosition(enemy)
      if pos is not None:
        exitCell = self.shared['best_border'][pos]
        candidateTargets.append((pos, 'visible'))
        candidateTargets.append((exitCell, 'exit'))
      else:
        belief = self.shared['beliefs'][enemy]
        if belief.totalCount() > 0:
          beliefPos = belief.argMax()
          exitCell = self.shared['best_border'][beliefPos]
          candidateTargets.append((beliefPos, 'belief'))
          candidateTargets.append((exitCell, 'exit'))

    if not candidateTargets:
      for event in self.shared['recent_events']:
        candidateTargets.append((event['pos'], event['kind']))

    if not candidateTargets:
      return self.pickPatrolTarget(gameState)

    bestTarget = None
    bestScore = None
    for target, kind in candidateTargets:
      distance = self.getMazeDistance(myPos, target)
      pressure = 0
      if kind == 'visible':
        pressure = -6
      elif kind == 'exit':
        pressure = -2
      elif kind == 'belief':
        pressure = -4
      score = distance + pressure
      if gameState.getAgentState(self.index).scaredTimer > 0 and kind == 'visible':
        score += 4
      if bestScore is None or score < bestScore:
        bestScore = score
        bestTarget = target
    return bestTarget

  # wanders around our side to guard the choke points
  def pickPatrolTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    teammateGoal = self.getTeammateGoal()
    defendedFood = self.getFoodYouAreDefending(gameState).asList()
    preferredUpper = self.preferredUpperLane()

    if defendedFood:
      boundaryX = min(border[0] for border in self.shared['home_border']) if self.red else max(border[0] for border in self.shared['home_border'])
      candidateFood = [food for food in defendedFood if self.matchesPreferredLane(food, preferredUpper)]
      if len(candidateFood) < 2:
        candidateFood = defendedFood

      frontierFood = sorted(
        candidateFood,
        key=lambda food: (abs(food[0] - boundaryX), self.getMazeDistance(myPos, food)),
      )
      if frontierFood:
        return frontierFood[0]

    bestTarget = None
    bestScore = None

    for target in self.shared['patrol_points']:
      score = self.getMazeDistance(myPos, target)
      score -= self.borderPressure(target, gameState)
      if teammateGoal is not None and self.getMazeDistance(target, teammateGoal) <= 3:
        score += 4
      if bestScore is None or score < bestScore:
        bestScore = score
        bestTarget = target
    return bestTarget

  # picks the best food or capsule to eat while avoiding danger
  def pickAttackTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    food = self.getFood(gameState).asList()
    capsules = self.getCapsules(gameState)
    teammateGoal = self.getTeammateGoal()
    carrying = gameState.getAgentState(self.index).numCarrying
    scaredWindow = self.maxEnemyScaredTimer(gameState)
    threatDist = self.closestVisibleDangerDistance(gameState, myPos)
    threatPos = self.closestVisibleDangerPosition(gameState, myPos)
    ownMovesLeft = self.ownMovesLeft(gameState)
    openingPhase = self.inOpeningPhase(gameState)
    preferredUpper = self.preferredUpperLane()
    preferredLaneFoods = [pellet for pellet in food if self.matchesPreferredLane(pellet, preferredUpper)]
    candidateFoods = preferredLaneFoods if len(preferredLaneFoods) >= 3 else food

    bestTarget = None
    bestKind = 'food'
    bestValue = None

    if capsules:
      for capsule in capsules:
        distance = self.getMazeDistance(myPos, capsule)
        if distance > 4 and (threatDist is None or threatDist > 5):
          continue
        value = (
          18
          - 2.2 * distance
          - 3.0 * self.positionRisk(gameState, capsule)
        )
        if threatDist is not None and threatDist <= 5:
          value += 10
        if teammateGoal is not None and self.getMazeDistance(capsule, teammateGoal) <= 2:
          value -= 6
        if bestValue is None or value > bestValue:
          bestValue = value
          bestTarget = capsule
          bestKind = 'capsule'

    openingFrontier = [
      pellet for pellet in candidateFoods
      if self.shared['home_distance'][pellet] <= 4 and self.shared['dead_end_depth'].get(pellet, 0) <= 2
    ]
    if openingPhase and openingFrontier:
      openingFrontier = sorted(
        openingFrontier,
        key=lambda pellet: (
          self.getMazeDistance(myPos, pellet) + 0.6 * self.shared['home_distance'][pellet],
          self.shared['dead_end_depth'].get(pellet, 0),
        ),
      )
      return openingFrontier[0], 'food'

    for pellet in candidateFoods:
      distance = self.getMazeDistance(myPos, pellet)
      homeDist = self.shared['home_distance'][pellet]
      depth = self.shared['dead_end_depth'].get(pellet, 0)
      riskPenalty = 5.0 * self.positionRisk(gameState, pellet)
      depthPenalty = 1.2 * depth if scaredWindow < 4 else 0.4 * depth
      tripCost = distance + homeDist
      lanePenalty = 0.0
      if preferredLaneFoods and len(preferredLaneFoods) >= 3 and not self.matchesPreferredLane(pellet, preferredUpper):
        lanePenalty = 4.5 if openingPhase else 2.0
      shallowBonus = max(0, 5 - homeDist)
      tempoBonus = max(0, 12 - tripCost) if openingPhase else max(0, 9 - tripCost)
      tempoPenalty = 0.0
      if tripCost > ownMovesLeft - 4:
        tempoPenalty += 12.0
      if homeDist >= 8 and scaredWindow < 6:
        tempoPenalty += 3.0
      if threatPos is not None and depth >= 2:
        foodRace = self.getMazeDistance(threatPos, pellet) - distance
        if foodRace <= 1:
          tempoPenalty += 6.0

      value = (
        + shallowBonus
        + 1.5 * tempoBonus
        - 1.8 * distance
        - 0.9 * homeDist
        - riskPenalty
        - depthPenalty
        - lanePenalty
        - tempoPenalty
      )
      if carrying > 0:
        value -= 0.6 * carrying * homeDist
      if threatDist is not None and threatDist <= 4:
        value -= 4
      if threatDist is not None and threatDist <= 6 and depth >= 2:
        value -= 8
      if teammateGoal is not None and self.getMazeDistance(pellet, teammateGoal) <= 3:
        value -= 5
      if self.slot == 0:
        value += 0.5
      if bestValue is None or value > bestValue:
        bestValue = value
        bestTarget = pellet
        bestKind = 'food'

    if bestTarget is None:
      return self.pickRetreatTarget(gameState), 'border'
    return bestTarget, bestKind

  # checks where the teammate is going so we don't crowd them
  def getTeammateGoal(self):
    for teammate in self.teamKey[1]:
      if teammate == self.index:
        continue
      if teammate in self.shared['agent_goals']:
        return self.shared['agent_goals'][teammate]
    return None

  # planning and scoring  
  # builds a path to the target using a*
  def planToTarget(self, gameState, target, mode):
    if target is None:
      return []
    myPos = gameState.getAgentPosition(self.index)
    if myPos == target:
      return []
    return self.weightedAStar(gameState, myPos, set([target]), mode)

  # pathfinding that avoids dangerous spots and dead ends
  def weightedAStar(self, gameState, start, goals, mode):
    frontier = util.PriorityQueue()
    frontier.push((start, [], 0.0), 0.0)
    bestCost = {start: 0.0}
    expansions = 0

    while not frontier.isEmpty() and expansions < 300:
      pos, path, cost = frontier.pop()
      if cost > bestCost.get(pos, 999999):
        continue
      if pos in goals:
        return path

      expansions += 1
      for nextPos in self.shared['neighbors'][pos]:
        stepCost = 1.0 + self.pathCellPenalty(gameState, nextPos, mode)
        newCost = cost + stepCost
        if newCost >= bestCost.get(nextPos, 999999):
          continue
        bestCost[nextPos] = newCost
        action = self.directionFromTo(pos, nextPos)
        heuristic = min(self.getMazeDistance(nextPos, goal) for goal in goals)
        frontier.push((nextPos, path + [action], newCost), newCost + 1.15 * heuristic)
    return []

  # adds extra cost to dangerous tiles so the agent avoids them
  def pathCellPenalty(self, gameState, pos, mode):
    risk = self.positionRisk(gameState, pos)
    penalty = 0.0

    if mode in ('attack', 'retreat'):
      penalty += 4.5 * risk
      if pos in self.shared['enemy_positions']:
        penalty += 0.2 * self.shared['dead_end_depth'].get(pos, 0)
        if mode == 'retreat':
          penalty += 0.25 * self.shared['dead_end_depth'].get(pos, 0)
    else:
      penalty += 1.5 * risk

    teammateGoal = self.getTeammateGoal()
    if teammateGoal is not None and pos == teammateGoal:
      penalty += 2.5
    return penalty

  # gives a numerical score to every possible move we can make right now
  def scoreActions(self, gameState, legalActions, mode, target, plan):
    scores = {}
    plannedAction = plan[0] if plan else None
    currentDirection = gameState.getAgentState(self.index).getDirection()
    currentState = gameState.getAgentState(self.index)

    for action in legalActions:
      successor = gameState.generateSuccessor(self.index, action)
      nextState = successor.getAgentState(self.index)
      nextPos = successor.getAgentPosition(self.index)
      if nextPos is None:
        nextPos = nextState.getPosition()

      score = self.getScore(successor) * 18.0
      if target is not None:
        score -= self.getMazeDistance(nextPos, target)
      if plannedAction == action:
        score += 4.0
      if action == Directions.STOP:
        score -= 6.0
      if action == Directions.REVERSE[currentDirection]:
        score -= 1.5

      if mode == 'attack':
        score += 14.0 * (len(self.getFood(gameState).asList()) - len(self.getFood(successor).asList()))
        score += 18.0 * (nextState.numReturned - currentState.numReturned)
        score -= 10.0 * self.positionRisk(gameState, nextPos)
        if nextPos in self.shared['enemy_positions']:
          score -= 0.7 * self.shared['dead_end_depth'].get(nextPos, 0)
        if currentState.numCarrying > 0:
          score -= 0.7 * currentState.numCarrying * self.shared['home_distance'][nextPos]
        if self.inOpeningPhase(gameState) and self.matchesPreferredLane(nextPos, self.preferredUpperLane()):
          score += 1.5
      elif mode == 'retreat':
        score -= 2.5 * self.shared['home_distance'][nextPos]
        score -= 12.0 * self.positionRisk(gameState, nextPos)
        score += 24.0 * (nextState.numReturned - currentState.numReturned)
      else:
        invaderPos = self.closestInvaderPosition(gameState)
        if invaderPos is not None:
          score -= 3.0 * self.getMazeDistance(nextPos, invaderPos)
        if not nextState.isPacman:
          score += 4.0
        else:
          score -= 10.0
        if nextState.scaredTimer > 0 and invaderPos is not None and self.getMazeDistance(nextPos, invaderPos) <= 1:
          score -= 10.0

      scores[action] = round(score, 6)
    return scores

  # tactical local search  

  # checks if an enemy is really close and we need to think deeper
  def shouldUseTacticalSearch(self, gameState, mode):
    if mode not in ('attack', 'retreat', 'intercept'):
      return False
    myPos = gameState.getAgentPosition(self.index)
    for enemy in self.getOpponents(gameState):
      enemyPos = gameState.getAgentPosition(enemy)
      if enemyPos is None:
        continue
      if self.getMazeDistance(myPos, enemyPos) <= 5:
        return True
    return False

  # simulates enemy moves to avoid getting eaten in close combat
  def applyTacticalSearch(self, gameState, actionScores, mode, target):
    visibleEnemies = []
    myPos = gameState.getAgentPosition(self.index)
    for enemy in self.getOpponents(gameState):
      enemyPos = gameState.getAgentPosition(enemy)
      if enemyPos is None:
        continue
      if self.getMazeDistance(myPos, enemyPos) <= 5:
        visibleEnemies.append(enemy)

    if not visibleEnemies:
      return actionScores

    enemy = min(visibleEnemies, key=lambda idx: self.getMazeDistance(myPos, gameState.getAgentPosition(idx)))
    bestCandidates = sorted(actionScores.items(), key=lambda item: item[1], reverse=True)[:4]
    rescored = dict(actionScores)

    for action, baseScore in bestCandidates:
      successor = gameState.generateSuccessor(self.index, action)
      enemyActions = successor.getLegalActions(enemy)
      if not enemyActions:
        continue

      replyValues = []
      for enemyAction in enemyActions:
        replyState = successor.generateSuccessor(enemy, enemyAction)
        replyValues.append(self.tacticalStateValue(replyState, mode, target))
      rescored[action] = round(0.7 * baseScore + 0.3 * min(replyValues), 6)
    return rescored

  # quickly scores a board state during close combat
  def tacticalStateValue(self, gameState, mode, target):
    myState = gameState.getAgentState(self.index)
    myPos = gameState.getAgentPosition(self.index)
    if myPos is None:
      myPos = myState.getPosition()

    value = self.getScore(gameState) * 20.0
    value -= 7.0 * self.positionRisk(gameState, myPos)

    if mode in ('attack', 'retreat'):
      value -= 1.5 * self.shared['home_distance'].get(myPos, 0) * max(1, myState.numCarrying)
    else:
      invaderPos = self.closestInvaderPosition(gameState)
      if invaderPos is not None:
        value -= 2.5 * self.getMazeDistance(myPos, invaderPos)

    if target is not None:
      value -= 0.4 * self.getMazeDistance(myPos, target)
    return value


  # map utilities 

  # checks if a tile is on our side of the map
  def isHomePosition(self, pos, width=None):
    width = self.shared['width'] if width is None else width
    halfway = width // 2
    if self.red:
      return pos[0] < halfway
    return pos[0] >= halfway

  # finds the midline tiles where we can score food
  def computeBorderCells(self, legalPositions, width):
    halfway = width // 2
    borderX = halfway - 1 if self.red else halfway
    enemyX = borderX + 1 if self.red else borderX - 1
    legalSet = set(legalPositions)

    border = []
    for pos in legalPositions:
      if pos[0] != borderX:
        continue
      if (enemyX, pos[1]) in legalSet:
        border.append(pos)
    return border

  # finds good spots to stand to protect our remaining food
  def computePatrolPoints(self, gameState, homeBorder):
    defendedFood = self.getFoodYouAreDefending(gameState).asList()
    defendedCapsules = self.getCapsulesYouAreDefending(gameState)
    defendedTargets = defendedFood + defendedCapsules
    if not defendedTargets:
      return list(homeBorder)

    scored = []
    for border in homeBorder:
      avgDist = sum(self.getMazeDistance(border, target) for target in defendedTargets) / float(len(defendedTargets))
      scored.append((avgDist, border))
    scored.sort()
    return [border for _, border in scored[:min(5, len(scored))]]

  # figures out how deep every dead end is so we don't get trapped
  def computeDeadEndDepth(self, neighbors):
    degrees = {pos: len(nextPositions) for pos, nextPositions in neighbors.items()}
    depths = dict((pos, 0) for pos in neighbors)
    queue = [(pos, 1) for pos, degree in degrees.items() if degree <= 1]

    while queue:
      pos, depth = queue.pop(0)
      if degrees[pos] == 0:
        continue
      depths[pos] = max(depths[pos], depth)
      degrees[pos] = 0
      for neighbor in neighbors[pos]:
        if degrees.get(neighbor, 0) <= 0:
          continue
        degrees[neighbor] -= 1
        if degrees[neighbor] == 1:
          queue.append((neighbor, depth + 1))
    return depths

  # gets adjacent tiles that aren't walls
  def getStaticNeighbors(self, pos, walls):
    neighbors = []
    x, y = pos
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
      nx, ny = x + dx, y + dy
      if not walls[nx][ny]:
        neighbors.append((nx, ny))
    return neighbors

  def directionFromTo(self, start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 1:
      return Directions.EAST
    if dx == -1:
      return Directions.WEST
    if dy == 1:
      return Directions.NORTH
    if dy == -1:
      return Directions.SOUTH
    return Directions.STOP

  
  # risk, pressure, heuristics #

  # calculates how dangerous a spot is based on where enemies might be
  def positionRisk(self, gameState, pos):
    risk = 0.0
    for enemy in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(enemy)
      if enemyState.isPacman or enemyState.scaredTimer > 2:
        continue

      enemyPos = gameState.getAgentPosition(enemy)
      if enemyPos is not None:
        distance = self.getMazeDistance(pos, enemyPos)
        if distance <= 1:
          risk += 3.5
        elif distance <= 2:
          risk += 2.0
        elif distance <= 4:
          risk += 0.8
        continue

      belief = self.shared['beliefs'][enemy]
      if belief.totalCount() == 0:
        continue

      beliefPos = belief.argMax()
      peakProb = belief[beliefPos]
      if peakProb < 0.2:
        continue

      distance = self.getMazeDistance(pos, beliefPos)
      if distance <= 1:
        risk += 2.0 * peakProb
      elif distance <= 2:
        risk += 1.0 * peakProb
      elif distance <= 4:
        risk += 0.4 * peakProb
    return risk

  def closestDangerDistance(self, gameState, pos):
    distances = []
    for enemy in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(enemy)
      if enemyState.isPacman or enemyState.scaredTimer > 2:
        continue
      enemyPos = gameState.getAgentPosition(enemy)
      if enemyPos is not None:
        distances.append(self.getMazeDistance(pos, enemyPos))
      else:
        belief = self.shared['beliefs'][enemy]
        if belief.totalCount() > 0:
          distances.append(self.getMazeDistance(pos, belief.argMax()))
    if not distances:
      return None
    return min(distances)

  def closestVisibleDangerDistance(self, gameState, pos):
    dangerPos = self.closestVisibleDangerPosition(gameState, pos)
    if dangerPos is None:
      return None
    return self.getMazeDistance(pos, dangerPos)

  def closestVisibleDangerPosition(self, gameState, pos):
    visibleGhosts = []
    for enemy in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(enemy)
      if enemyState.isPacman or enemyState.scaredTimer > 2:
        continue
      enemyPos = gameState.getAgentPosition(enemy)
      if enemyPos is not None:
        visibleGhosts.append(enemyPos)
    if not visibleGhosts:
      return None
    return min(visibleGhosts, key=lambda ghostPos: self.getMazeDistance(pos, ghostPos))

  # finds the most dangerous enemy we need to deal with
  def primaryThreatTarget(self, gameState):
    visibleInvaders = []
    for enemy in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(enemy)
      if not enemyState.isPacman:
        continue
      enemyPos = gameState.getAgentPosition(enemy)
      if enemyPos is not None:
        visibleInvaders.append(enemyPos)
      else:
        belief = self.shared['beliefs'][enemy]
        if belief.totalCount() > 0:
          beliefPos = belief.argMax()
          if belief[beliefPos] >= 0.2:
            visibleInvaders.append(beliefPos)

    if visibleInvaders:
      return min(visibleInvaders, key=lambda pos: self.shared['home_distance'].get(pos, 0))
    if self.shared['recent_events']:
      return max(self.shared['recent_events'], key=lambda event: event['ttl'])['pos']
    return None

  # finds the nearest enemy pacman
  def closestInvaderPosition(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    candidates = []
    for enemy in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(enemy)
      if not enemyState.isPacman:
        continue
      enemyPos = gameState.getAgentPosition(enemy)
      if enemyPos is not None:
        candidates.append(enemyPos)
      else:
        belief = self.shared['beliefs'][enemy]
        if belief.totalCount() > 0:
          candidates.append(belief.argMax())
    if not candidates:
      return None
    return min(candidates, key=lambda pos: self.getMazeDistance(myPos, pos))

  # checks if the enemies are still scared of our power capsule
  def maxEnemyScaredTimer(self, gameState):
    timers = [gameState.getAgentState(enemy).scaredTimer for enemy in self.getOpponents(gameState)]
    if not timers:
      return 0
    return max(timers)

  def borderPressure(self, borderPos, gameState):
    pressure = 0.0
    for event in self.shared['recent_events']:
      pressure += max(0.0, 7.0 - self.getMazeDistance(borderPos, event['pos']))
    defendedFood = self.getFoodYouAreDefending(gameState).asList()
    if defendedFood:
      pressure += 2.5 / (1 + min(self.getMazeDistance(borderPos, food) for food in defendedFood))
    return pressure

  def computeFoodClusterSizes(self, food):
    if not food:
      return {}
    remaining = set(food)
    clusterSizes = {}

    while remaining:
      seed = remaining.pop()
      cluster = [seed]
      frontier = [seed]

      while frontier:
        current = frontier.pop()
        connected = [other for other in list(remaining) if self.getMazeDistance(current, other) <= 4]
        for other in connected:
          remaining.remove(other)
          frontier.append(other)
          cluster.append(other)

      size = len(cluster)
      for pellet in cluster:
        clusterSizes[pellet] = size
    return clusterSizes

  # saving info 

  # saves info about why we made this move for debugging
  def recordDecision(self, gameState, mode, target, action, actionScores):
    topBeliefs = {}
    for enemy in self.getOpponents(gameState):
      belief = self.shared['beliefs'][enemy]
      if belief.totalCount() > 0:
        pos = belief.argMax()
        topBeliefs[str(enemy)] = (pos, round(belief[pos], 3))

    ranked = sorted(actionScores.items(), key=lambda item: item[1], reverse=True)[:4]
    self.lastDecisionInfo = {
      'mode': mode,
      'target': target,
      'action': action,
      'beliefs': topBeliefs,
      'scores': ranked,
      'events': list(self.shared['recent_events']),
    }

  def ownMovesLeft(self, gameState):
    numAgents = max(1, gameState.getNumAgents())
    return (gameState.data.timeleft + numAgents - 1) // numAgents

  def ownTotalMoves(self):
    contestLength = self.shared.get('contest_length', 0)
    return max(1, contestLength // max(1, len(self.getTeam(self.getCurrentObservation() or self.getPreviousObservation())) + len(self.getOpponents(self.getCurrentObservation() or self.getPreviousObservation()))))

  def inOpeningPhase(self, gameState):
    totalOwnMoves = max(1, self.shared.get('contest_length', gameState.data.timeleft) // max(1, gameState.getNumAgents()))
    return self.ownMovesLeft(gameState) >= max(1, totalOwnMoves - 28)

  def inLatePhase(self, gameState):
    totalOwnMoves = max(1, self.shared.get('contest_length', gameState.data.timeleft) // max(1, gameState.getNumAgents()))
    return self.ownMovesLeft(gameState) <= max(25, int(0.25 * totalOwnMoves))

  def preferredUpperLane(self):
    starts = self.shared.get('agent_starts', {})
    teamStarts = [(agent, pos) for agent, pos in starts.items() if agent in self.getTeam(self.getCurrentObservation() or self.getPreviousObservation())]
    if len(teamStarts) < 2:
      return self.slot == 0
    teamStarts.sort(key=lambda item: (item[1][1], item[0]))
    upperAgent = teamStarts[-1][0]
    return self.index == upperAgent

  def matchesPreferredLane(self, pos, preferredUpper):
    midY = self.shared['height'] // 2
    if preferredUpper:
      return pos[1] >= midY
    return pos[1] < midY
