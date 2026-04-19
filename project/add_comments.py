import re

comments = {
    "createTeam": "# sets up our two pacman agents for the game",
    "registerInitialState": "# runs once at the start of the game to prep the map and shared memory",
    "chooseAction": "# main loop: figures out what the agent should do this turn",
    "buildTeamMemory": "# scans the whole board to figure out distances, borders, and dead ends",
    "updateSharedState": "# syncs what this agent sees with what the teammate sees",
    "decayRecentEvents": "# slowly forgets about old events like eaten food over time",
    "trackFoodDefenseEvents": "# checks if our food disappeared so we know where enemies are",
    "updateBeliefs": "# guesses where invisible enemies are hiding using probabilities",
    "propagateBelief": "# spreads out our guesses of where the enemy moved",
    "filterBelief": "# removes places the enemy definitely can't be",
    "anchorBeliefToEvents": "# heavily updates our guesses if we saw them eat something",
    "seedFallbackBelief": "# if we completely lose the enemy, just guess they could be anywhere on their side",
    "assignRoles": "# decides who attacks and who defends based on the current score and threats",
    "defensePriority": "# scores how urgently this agent needs to go back and defend",
    "mustRetreatAgent": "# checks if the agent is carrying too much food or is in danger and needs to run home",
    "pickTarget": "# routes the agent to the right target depending on their current role",
    "pickRetreatTarget": "# finds the safest way back home to deposit food",
    "pickInterceptTarget": "# tries to cut off the enemy pacman by guessing where they will go",
    "pickPatrolTarget": "# wanders around our side to guard the choke points",
    "pickAttackTarget": "# picks the best food or capsule to eat while avoiding danger",
    "getTeammateGoal": "# checks where the teammate is going so we don't crowd them",
    "planToTarget": "# builds a path to the target using a*",
    "weightedAStar": "# pathfinding that avoids dangerous spots and dead ends",
    "pathCellPenalty": "# adds extra cost to dangerous tiles so the agent avoids them",
    "scoreActions": "# gives a numerical score to every possible move we can make right now",
    "shouldUseTacticalSearch": "# checks if an enemy is really close and we need to think deeper",
    "applyTacticalSearch": "# simulates enemy moves to avoid getting eaten in close combat",
    "tacticalStateValue": "# quickly scores a board state during close combat",
    "isHomePosition": "# checks if a tile is on our side of the map",
    "computeBorderCells": "# finds the midline tiles where we can score food",
    "computePatrolPoints": "# finds good spots to stand to protect our remaining food",
    "computeDeadEndDepth": "# figures out how deep every dead end is so we don't get trapped",
    "getStaticNeighbors": "# gets adjacent tiles that aren't walls",
    "positionRisk": "# calculates how dangerous a spot is based on where enemies might be",
    "primaryThreatTarget": "# finds the most dangerous enemy we need to deal with",
    "closestInvaderPosition": "# finds the nearest enemy pacman",
    "maxEnemyScaredTimer": "# checks if the enemies are still scared of our power capsule",
    "recordDecision": "# saves info about why we made this move for debugging"
}

with open("myTeamAnish.py", "r") as f:
    lines = f.readlines()

out_lines = []
for i, line in enumerate(lines):
    match = re.match(r'^(\s*)def\s+([a-zA-Z0-9_]+)\(', line)
    if match:
        indent = match.group(1)
        func_name = match.group(2)
        if func_name in comments:
            out_lines.append(f"{indent}{comments[func_name]}\n")
    out_lines.append(line)

with open("myTeamAnish.py", "w") as f:
    f.writelines(out_lines)

