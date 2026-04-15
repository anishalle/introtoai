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

"""
Opinionated starter structure for a capture-the-flag team.

Recommended edit order:
1. Edit ROLE_PRESETS to decide how each teammate should generally behave.
2. Edit getMode() to define when an agent should collect, return, intercept,
   patrol, or do something entirely different.
3. Edit getModeFeatures() and getModeWeights() to score actions.
4. Add helper methods near the bottom when you need new state queries.
5. Replace chooseAction() only if you want a different decision framework
   such as minimax, A*, MCTS, or learned policies.
"""

from captureAgents import CaptureAgent
import random
from game import Directions
import game

#######################
# Algorithmic Helpers #
#######################

class Node:
  def __init__(self, state, parent=None, value=0):
    #node stores a gamestate
    self.state = state
    self.parent = parent
    self.children = []
    self.value = value #the utility value of the node

  def addChild(self, child):
    self.children.append(child)

class MiniMax:
  def __init__(self, depth):
    self.depth = depth

#################
# Team creation #
#################

def createTeam(firstIndex, secondIndex, isRed,
               first='PrimaryAgent', second='SupportAgent'):
  """
  Return the two agents that make up your team.

  Change the default class names above if you want a different pair by default.
  You can also override them from the command line:
    python capture.py -r myTeam --redOpts first=SupportAgent,second=PrimaryAgent
  """
  return [loadAgentClass(first)(firstIndex), loadAgentClass(second)(secondIndex)]


def loadAgentClass(className):
  """
  Resolve a class name string to an agent class.

  If you add a new agent class below, it becomes available automatically as
  long as the class name matches the string passed to createTeam().
  """
  try:
    return globals()[className]
  except KeyError as exc:
    raise ValueError('Unknown agent class: %s' % className) from exc


######################
# Role configuration #
######################

ROLE_PRESETS = {
  'primary': {
    # Change these values first if you want a quick personality shift without
    # touching the rest of the code.
    'default_mode': 'collect',
    'return_food': 4,
    'weight_overrides': {
      'collect': {
        'distanceToFood': -3,
        'carrying': 5,
      },
    },
  },
  'support': {
    # A support agent starts in patrol mode but still switches modes when the
    # situation changes in getMode().
    'default_mode': 'patrol',
    'return_food': 2,
    'weight_overrides': {
      'intercept': {
        'distanceToInvader': -20,
      },
      'patrol': {
        'distanceToPatrol': -4,
      },
    },
  },
}


##########
# Agents #
##########

class MiniMaxAgent(CaptureAgent):
  """
  Minimal base class.

  Keep this class focused on setup only. Put actual decision logic in your
  concrete agents below.
  """

  ROLE_KEY = 'primary'

  def registerInitialState(self, gameState):
    CaptureAgent.registerInitialState(self, gameState)
    self.start = gameState.getAgentPosition(self.index)
    self.roleConfig = ROLE_PRESETS[self.ROLE_KEY]
    self.root = Node(gameState)
    self.red = gameState.isOnRedTeam(self.index)

    #Depth is meant to look ahead in turns, not depth as in the depth of the minimax tree
    self.depth = 2

  def chooseAction(self, gameState):
    value, action = self.minimax(gameState, depth=self.depth, agentIndex = self.index)
    return action
  
  def minimax(self, gameState, depth, agentIndex):
    if depth == 0 or gameState.isOver():
      return self.evaluate(gameState), None
    
    actions = gameState.getLegalActions(agentIndex)
    if not actions:
      return self.evaluate(gameState), None
    
    nextAgent = (agentIndex + 1) % gameState.getNumAgents()

    #we subtract depth - 1 because we now have one less turn to calculate when we get back to me
    nextDepth = depth - 1 if nextAgent == self.index else depth

    results = []
    for action in actions:
      successor = gameState.generateSuccessor 
      score, _ = self.minimax(successor, nextDepth, nextAgent)
      results.append((score, action))

    if self.isMaxAgent(key):
      return max(results, key=lambda x: x[0])
    else:
      return min(results, key=lambda x: x[0])

  def isMaxAgent(self, gameState, agentIndex):
    #no method to check teammate, so just check if the agent and self.red are equal. 
    #a max agent will resolve to true == true or false == false.
    return gameState.isOnRedTeam(agentIndex) == self.red



def chooseDefaultAction(gameState, agentIndex):
  actions = gameState.getLegalActions(agentIndex)
  if not actions:
    return Directions.STOP

  nonStopActions = [action for action in actions if action != Directions.STOP]
  if nonStopActions:
    return random.choice(nonStopActions)
  return random.choice(actions)


class PrimaryAgent(MiniMaxAgent):
  """
  This agent will focus on attacking
  """
  ROLE_KEY = 'primary'

  def evaluate():
    pass


class SupportAgent(MiniMaxAgent):
  """
  A more defensive/support-oriented template agent.

  Put SupportAgent-specific decision logic here.
  """
  ROLE_KEY = 'support'

  def evaluate():
    pass

# Add additional agent classes below if you want more specialized roles.
# Example ideas:
# - class ScoutAgent(StructuredCaptureAgent): ...
# - class TrapAgent(StructuredCaptureAgent): ...
# - class SearchAgent(StructuredCaptureAgent): ...
