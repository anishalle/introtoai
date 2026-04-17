from captureAgents import CaptureAgent
from game import Directions
from util import nearestPoint
import random
import util


def createTeam(firstIndex, secondIndex, isRed,
               first='RaidAgent', second='SentinelAgent'):
  """
  Build a coordinated two-agent team.
  """
  return [globals()[first](firstIndex), globals()[second](secondIndex)]


class StrategicCaptureAgent(CaptureAgent):
  """
  Shared contest agent with fast heuristic planning.
  """

  ROLE = 'raider'
  RETURN_THRESHOLD = 4
  DEFENSE_BIAS = 0

  _dead_end_cache = {}

  def registerInitialState(self, gameState):
    CaptureAgent.registerInitialState(self, gameState)
    self.start = gameState.getAgentPosition(self.index)
    self.teamIndices = self.getTeam(gameState)
    self.teammateIndex = [i for i in self.teamIndices if i != self.index][0]
    self.midX = gameState.data.layout.width // 2
    self.homeBoundary = self._buildBoundary(gameState, home=True)
    self.enemyBoundary = self._buildBoundary(gameState, home=False)
    self.deadEndDepth = self._getDeadEndDepth(gameState.getWalls())

    self.lastEatenFood = None
    self.lastEatenFoodAge = 999
    self.lastSeenInvader = None
    self.lastSeenInvaderAge = 999
    self.lastDecisionInfo = None

  def chooseAction(self, gameState):
    self._updateMemory(gameState)

    actions = gameState.getLegalActions(self.index)
    filtered = [a for a in actions if a != Directions.STOP]
    if filtered:
      actions = filtered

    plan = self._selectPlan(gameState)
    scored = []
    for action in actions:
      features, weights = self._getFeaturesAndWeights(gameState, action, plan)
      score = features * weights
      scored.append({
        'action': action,
        'score': score,
        'features': dict(features),
        'weights': dict(weights),
      })

    bestScore = max(detail['score'] for detail in scored)
    bestActions = [detail['action'] for detail in scored if detail['score'] == bestScore]
    chosen = random.choice(bestActions)

    selected = next(detail for detail in scored if detail['action'] == chosen)
    self.lastDecisionInfo = {
      'mode': plan['mode'],
      'chosenAction': chosen,
      'bestActions': bestActions,
      'bestScore': bestScore,
      'selectedAction': selected,
      'scoredActions': sorted(scored, key=lambda item: (-item['score'], item['action'])),
      'messages': plan['messages'],
    }
    return chosen

  def getLastDecisionInfo(self):
    return self.lastDecisionInfo

  def _getFeaturesAndWeights(self, gameState, action, plan):
    successor = self.getSuccessor(gameState, action)
    myState = successor.getAgentState(self.index)
    myPos = myState.getPosition()
    previousState = gameState.getAgentState(self.index)

    foodBefore = len(self.getFood(gameState).asList())
    foodAfter = len(self.getFood(successor).asList())
    capsulesBefore = len(self.getCapsules(gameState))
    capsulesAfter = len(self.getCapsules(successor))
    invadersAfter = self._getVisibleInvaders(successor)
    invaderDistance = self._distanceToClosest(
      myPos, [pos for _, _, pos in invadersAfter]
    )
    foodDistance = self._distanceToClosest(myPos, self.getFood(successor).asList())
    homeDistance = self._distanceToHome(myPos)
    targetDistance = self._distanceToTarget(myPos, plan.get('target'))
    threatDistance = self._nearestThreatDistance(successor, myPos)
    died = self._didDie(gameState, successor)

    features = util.Counter()
    features['score'] = self.getScore(successor)
    features['foodEaten'] = max(0, foodBefore - foodAfter)
    features['capsuleEaten'] = max(0, capsulesBefore - capsulesAfter)
    features['carrying'] = myState.numCarrying
    features['stop'] = int(action == Directions.STOP)
    features['reverse'] = int(
      action == Directions.REVERSE[gameState.getAgentState(self.index).configuration.direction]
    )
    features['targetDistance'] = targetDistance
    features['foodDistance'] = foodDistance
    features['homeDistance'] = homeDistance
    features['returnPressure'] = myState.numCarrying * homeDistance
    features['escapePressure'] = self._escapePressure(myState, threatDistance)
    features['deadEndRisk'] = self._deadEndRisk(myState, myPos, threatDistance)
    features['onDefense'] = int(not myState.isPacman)
    features['numInvaders'] = len(invadersAfter)
    features['invaderDistance'] = invaderDistance
    features['scaredTrap'] = int(
      myState.scaredTimer > 0 and invaderDistance > 0 and invaderDistance <= 1
    )
    features['died'] = died
    features['returnedFood'] = self._returnedFood(previousState, myState, died)

    if plan['mode'] == 'attack':
      weights = {
        'score': 260,
        'foodEaten': 120,
        'capsuleEaten': 150,
        'carrying': 10,
        'foodDistance': -2,
        'targetDistance': -4,
        'returnPressure': -1.5,
        'escapePressure': -80,
        'deadEndRisk': -28,
        'stop': -35,
        'reverse': -6,
        'died': -1800,
      }
    elif plan['mode'] == 'return':
      weights = {
        'score': 300,
        'returnedFood': 260,
        'carrying': 20,
        'homeDistance': -12,
        'targetDistance': -5,
        'escapePressure': -90,
        'deadEndRisk': -35,
        'stop': -45,
        'reverse': -8,
        'died': -2200,
      }
    elif plan['mode'] == 'capsule':
      weights = {
        'score': 260,
        'capsuleEaten': 220,
        'carrying': 10,
        'targetDistance': -8,
        'escapePressure': -70,
        'deadEndRisk': -30,
        'stop': -40,
        'reverse': -6,
        'died': -1900,
      }
    elif plan['mode'] == 'defend':
      weights = {
        'score': 220,
        'onDefense': 120,
        'numInvaders': -240,
        'invaderDistance': -16,
        'targetDistance': -5,
        'foodEaten': 25,
        'capsuleEaten': 40,
        'scaredTrap': -180,
        'stop': -70,
        'reverse': -10,
        'died': -500,
      }
    else:
      weights = {
        'score': 220,
        'onDefense': 110,
        'targetDistance': -4,
        'foodEaten': 35,
        'capsuleEaten': 40,
        'stop': -35,
        'reverse': -8,
        'died': -600,
      }

    return features, weights

  def _selectPlan(self, gameState):
    myState = gameState.getAgentState(self.index)
    myPos = myState.getPosition()
    invaders = self._getVisibleInvaders(gameState)
    threatDistance = self._nearestThreatDistance(gameState, myPos)
    foodLeft = len(self.getFood(gameState).asList())
    messages = []

    if self._shouldDefend(gameState, invaders):
      target = self._chooseDefenseTarget(gameState, invaders)
      messages.append('defend home territory')
      return {'mode': 'defend', 'target': target, 'messages': messages}

    if self._mustReturn(gameState, threatDistance, foodLeft):
      target = self._closestBoundaryPoint(myPos, self.homeBoundary)
      messages.append('bank carried food')
      return {'mode': 'return', 'target': target, 'messages': messages}

    if myState.isPacman and threatDistance is not None and threatDistance <= 3:
      capsuleTarget = self._chooseCapsuleTarget(gameState)
      if capsuleTarget is not None:
        messages.append('pressure nearest capsule')
        return {'mode': 'capsule', 'target': capsuleTarget, 'messages': messages}
      target = self._closestBoundaryPoint(myPos, self.homeBoundary)
      messages.append('retreat from visible ghost')
      return {'mode': 'return', 'target': target, 'messages': messages}

    if self._preferPatrol(gameState, invaders):
      target = self._choosePatrolTarget(gameState)
      messages.append('hold midfield patrol')
      return {'mode': 'patrol', 'target': target, 'messages': messages}

    target = self._chooseFoodTarget(gameState)
    messages.append('steal food safely')
    return {'mode': 'attack', 'target': target, 'messages': messages}

  def _shouldDefend(self, gameState, invaders):
    myState = gameState.getAgentState(self.index)
    myPos = myState.getPosition()
    teammateState = gameState.getAgentState(self.teammateIndex)
    teammatePos = teammateState.getPosition()

    if self.ROLE == 'sentinel':
      if invaders:
        return True
      if not myState.isPacman and self.lastSeenInvaderAge <= 6:
        return True
      if not myState.isPacman and self.lastEatenFoodAge <= 10:
        return True
      if self._preferPatrol(gameState, invaders):
        return True
      return False

    if not invaders:
      return False
    if myState.isPacman or myState.numCarrying > 0:
      return False

    target = self._chooseDefenseTarget(gameState, invaders)
    myDistance = self.getMazeDistance(myPos, target)
    if teammateState.isPacman or teammatePos is None:
      teammateDistance = 9999
    else:
      teammateDistance = self.getMazeDistance(teammatePos, target)
    return myDistance + 1 < teammateDistance

  def _preferPatrol(self, gameState, invaders):
    if self.ROLE != 'sentinel':
      return False
    myState = gameState.getAgentState(self.index)
    teammateState = gameState.getAgentState(self.teammateIndex)
    if myState.isPacman:
      return False
    if invaders:
      return False
    if self.lastSeenInvaderAge <= 6 or self.lastEatenFoodAge <= 10:
      return True
    if teammateState.isPacman and self.getScore(gameState) >= 0:
      return True
    return self.getScore(gameState) >= 2

  def _mustReturn(self, gameState, threatDistance, foodLeft):
    myState = gameState.getAgentState(self.index)
    myPos = myState.getPosition()
    carrying = myState.numCarrying
    if carrying <= 0:
      return False

    if foodLeft <= 2:
      return True

    homeDistance = self._distanceToHome(myPos)
    pliesNeeded = homeDistance * gameState.getNumAgents() + 6
    if gameState.data.timeleft <= pliesNeeded:
      return True

    threshold = self.RETURN_THRESHOLD
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

  def _chooseFoodTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    teammatePos = gameState.getAgentPosition(self.teammateIndex)
    foods = self.getFood(gameState).asList()
    if not foods:
      return self._closestBoundaryPoint(myPos, self.enemyBoundary)

    threatDistance = self._nearestThreatDistance(gameState, myPos)
    bestScore = None
    bestFood = None
    for food in foods:
      myDistance = self.getMazeDistance(myPos, food)
      teammatePenalty = 0
      if teammatePos is not None:
        teammateDistance = self.getMazeDistance(teammatePos, food)
        if teammateDistance + 1 < myDistance:
          teammatePenalty = 3

      depthPenalty = 0
      if threatDistance is not None:
        depthPenalty = self.deadEndDepth.get(food, 0) * max(0, 5 - threatDistance)

      homePenalty = 0.25 * self._distancePointToHome(food)
      if self.ROLE == 'sentinel':
        homePenalty += 0.35 * self._distancePointToHome(food)

      score = myDistance + teammatePenalty + depthPenalty + homePenalty
      if bestScore is None or score < bestScore:
        bestScore = score
        bestFood = food
    return bestFood

  def _chooseCapsuleTarget(self, gameState):
    myPos = gameState.getAgentPosition(self.index)
    capsules = self.getCapsules(gameState)
    if not capsules:
      return None
    return self._closestBoundaryPoint(myPos, capsules)

  def _chooseDefenseTarget(self, gameState, invaders):
    myPos = gameState.getAgentPosition(self.index)
    if invaders:
      weighted = []
      for _, state, pos in invaders:
        danger = self.getMazeDistance(myPos, pos) - (4 * state.numCarrying)
        weighted.append((danger, pos))
      return min(weighted)[1]

    if self.lastSeenInvader is not None and self.lastSeenInvaderAge <= 6:
      return self.lastSeenInvader
    if self.lastEatenFood is not None and self.lastEatenFoodAge <= 12:
      return self.lastEatenFood
    return self._choosePatrolTarget(gameState)

  def _choosePatrolTarget(self, gameState):
    defendedFood = self.getFoodYouAreDefending(gameState).asList()
    if self.lastEatenFood is not None and self.lastEatenFoodAge <= 12:
      anchor = self.lastEatenFood
    elif defendedFood:
      averageY = sum(pos[1] for pos in defendedFood) / float(len(defendedFood))
      anchor = min(defendedFood, key=lambda pos: abs(pos[1] - averageY))
    else:
      anchor = self.start
    return self._closestBoundaryPoint(anchor, self.homeBoundary)

  def _updateMemory(self, gameState):
    self.lastEatenFoodAge += 1
    self.lastSeenInvaderAge += 1

    invaders = self._getVisibleInvaders(gameState)
    if invaders:
      best = min(
        invaders,
        key=lambda item: (self.getMazeDistance(gameState.getAgentPosition(self.index), item[2]), -item[1].numCarrying)
      )
      self.lastSeenInvader = best[2]
      self.lastSeenInvaderAge = 0

    previous = self.getPreviousObservation()
    if previous is not None:
      previousFood = set(self.getFoodYouAreDefending(previous).asList())
      currentFood = set(self.getFoodYouAreDefending(gameState).asList())
      eaten = list(previousFood - currentFood)
      if eaten:
        myPos = gameState.getAgentPosition(self.index)
        self.lastEatenFood = min(eaten, key=lambda pos: self.getMazeDistance(myPos, pos))
        self.lastEatenFoodAge = 0

    myPos = gameState.getAgentPosition(self.index)
    if self.lastSeenInvader is not None and myPos == self.lastSeenInvader:
      self.lastSeenInvaderAge = 999
    if self.lastEatenFood is not None and myPos == self.lastEatenFood:
      self.lastEatenFoodAge = 999

  def getSuccessor(self, gameState, action):
    successor = gameState.generateSuccessor(self.index, action)
    pos = successor.getAgentState(self.index).getPosition()
    if pos != nearestPoint(pos):
      return successor.generateSuccessor(self.index, action)
    return successor

  def _getVisibleInvaders(self, gameState):
    result = []
    for opponent in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(opponent)
      pos = enemyState.getPosition()
      if enemyState.isPacman and pos is not None:
        result.append((opponent, enemyState, pos))
    return result

  def _nearestThreatDistance(self, gameState, myPos):
    myState = gameState.getAgentState(self.index)
    if not myState.isPacman:
      return None

    threatPositions = []
    for opponent in self.getOpponents(gameState):
      enemyState = gameState.getAgentState(opponent)
      pos = enemyState.getPosition()
      if pos is None:
        continue
      if enemyState.isPacman:
        continue
      if enemyState.scaredTimer > 1:
        continue
      threatPositions.append(pos)

    if not threatPositions:
      return None
    return min(self.getMazeDistance(myPos, pos) for pos in threatPositions)

  def _escapePressure(self, myState, threatDistance):
    if not myState.isPacman or threatDistance is None:
      return 0
    return max(0, 6 - threatDistance)

  def _deadEndRisk(self, myState, myPos, threatDistance):
    if not myState.isPacman or threatDistance is None:
      return 0
    if threatDistance > 4:
      return 0
    return self.deadEndDepth.get(myPos, 0) * max(0, 5 - threatDistance)

  def _returnedFood(self, previousState, myState, died):
    if died:
      return 0
    if previousState.numCarrying <= myState.numCarrying:
      return 0
    if myState.isPacman:
      return 0
    return previousState.numCarrying - myState.numCarrying

  def _didDie(self, gameState, successor):
    previousState = gameState.getAgentState(self.index)
    nextState = successor.getAgentState(self.index)
    previousPos = previousState.getPosition()
    nextPos = nextState.getPosition()

    if nextPos != self.start or previousPos == self.start:
      return 0
    if previousState.isPacman and not nextState.isPacman and self._distanceToHome(previousPos) > 1:
      return 1
    if previousState.numCarrying > 0 and nextState.numCarrying == 0:
      return 1
    return 0

  def _distanceToHome(self, pos):
    if pos is None or self._isHome(pos):
      return 0
    return min(self.getMazeDistance(pos, boundary) for boundary in self.homeBoundary)

  def _distancePointToHome(self, pos):
    return min(self.getMazeDistance(pos, boundary) for boundary in self.homeBoundary)

  def _distanceToClosest(self, source, points):
    if source is None or not points:
      return 0
    return min(self.getMazeDistance(source, point) for point in points)

  def _distanceToTarget(self, source, target):
    if source is None or target is None:
      return 0
    return self.getMazeDistance(source, target)

  def _closestBoundaryPoint(self, source, points):
    if not points:
      return None
    return min(points, key=lambda point: self.getMazeDistance(source, point))

  def _isHome(self, pos):
    if self.red:
      return pos[0] < self.midX
    return pos[0] >= self.midX

  def _buildBoundary(self, gameState, home=True):
    walls = gameState.getWalls()
    x = self.midX - 1 if self.red == home else self.midX
    positions = []
    for y in range(1, walls.height - 1):
      if not walls[x][y]:
        positions.append((x, y))
    return positions

  @classmethod
  def _getDeadEndDepth(cls, walls):
    key = (walls.width, walls.height, tuple(walls.asList()))
    if key in cls._dead_end_cache:
      return cls._dead_end_cache[key]

    openCells = []
    neighbors = {}
    for x in range(walls.width):
      for y in range(walls.height):
        if walls[x][y]:
          continue
        cell = (x, y)
        openCells.append(cell)
        neighbors[cell] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
          nx, ny = x + dx, y + dy
          if 0 <= nx < walls.width and 0 <= ny < walls.height and not walls[nx][ny]:
            neighbors[cell].append((nx, ny))

    degree = {cell: len(adjacent) for cell, adjacent in neighbors.items()}
    original = dict(degree)
    queue = [cell for cell, count in degree.items() if count == 1]
    removed = set(queue)
    depth = {cell: 1 for cell in queue}

    while queue:
      cell = queue.pop(0)
      for neighbor in neighbors[cell]:
        if neighbor in removed:
          continue
        degree[neighbor] -= 1
        if degree[neighbor] == 1 and original[neighbor] == 2:
          depth[neighbor] = depth[cell] + 1
          removed.add(neighbor)
          queue.append(neighbor)

    cls._dead_end_cache[key] = depth
    return depth


class RaidAgent(StrategicCaptureAgent):
  ROLE = 'raider'
  RETURN_THRESHOLD = 5


class SentinelAgent(StrategicCaptureAgent):
  ROLE = 'sentinel'
  RETURN_THRESHOLD = 3
  DEFENSE_BIAS = 1
