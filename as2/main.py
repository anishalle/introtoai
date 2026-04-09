import sys
import copy
from enum import Enum

class OPS(Enum):
    EQUAL = "="
    NOT_EQUAL = "!"
    LESS_THAN = "<"
    GREATER_THAN = ">"

def check_constraint(first, op, second):
    if op == "=": return first == second
    if op == "!": return first != second
    if op == ">": return first > second
    if op == '<': return first < second 
    #if we get here, we shouldn't...
    return False

def get_constraining(var, unassigned, constraints):
    count = 0
    for first, _, second in constraints:
        if first == var and second in unassigned:
            count += 1
        elif second == var and first in unassigned:
            count += 1
    return count

def mcv(vars, unassigned, constraints):
    collisions = []
    m = min(len(vars[v]) for v in unassigned)
    candidates = [v for v in unassigned if len(vars[v]) == m]

    if len(candidates) == 1:
        return candidates[0]

    candidate_counts = []
    for var in candidates:
        constrained_count = get_constraining(var, unassigned, constraints) 
        candidate_counts.append((constrained_count, var))

    #finally sort by alphabetical. sort by degree firstw
    candidate_counts.sort(key=lambda x: (-x[0], x[1]))
    return candidate_counts[0][1]

def lcv(var, vars, unassigned, constraints):
    values = []
    for val in vars[var]:
        m = 0
        for first, op, second in constraints:
            if first == var and second in unassigned :
                for n in vars[second]:
                    if not check_constraint(val, op, n):
                        m += 1
            elif second == var and first in unassigned:
                for n in vars[first]:
                    if not check_constraint(n, op, val):
                        m += 1
        values.append((m, val))

    #sort by value first, and then alphabetical, like for mcv
    values.sort(key = lambda x: (x[0], x[1]))
    return [val for m, val in values]

def is_consistent(var, val, assignment, constraints):
    for first, op, second in constraints:
        if first == var and second in assignment:
            if not check_constraint(val, op, assignment[second]): return False
        elif second == var and first in assignment:
            if not check_constraint(assignment[first], op, val): return False
    return True

def forward_check(var, val, vars, unassigned, constraints):
    new_vars = copy.deepcopy(vars)
    for first, op, second in constraints:
        if first == var and second in unassigned:
            new_vars[second] = [n for n in new_vars[second] if check_constraint(val, op, n)]
            if not new_vars[second]: return None
        elif second == var and first in unassigned:
            new_vars[first] = [n for n in new_vars[first] if check_constraint(n, op, val)]
            if not new_vars[first]: return None

    return new_vars

def out(assignment_order, assignment, status, branch_num):
    parts = [f"{v}={assignment[v]}" for v in assignment_order]
    return f"{branch_num}. {', '.join(parts)}  {status}"


def backtrack(assignment, assignment_ord, unassigned, vars, constraints, fc, state):
    if not unassigned:
        print(out(assignment_ord, assignment, "solution", state['branch']))
        return True
    
    var = mcv(vars, unassigned, constraints)
    ordered_values = lcv(var, vars, unassigned, constraints)

    unassigned.remove(var)
    assignment_ord.append(var)
    
    for val in ordered_values:
        assignment[var] = val
        if is_consistent(var, val, assignment, constraints):
            if fc:
                new_vars = forward_check(var, val, vars, unassigned, constraints)
                if new_vars is None:
                    print(out(assignment_ord, assignment, "failure", state['branch']))
                    state['branch'] += 1
                else:
                    result = backtrack(assignment, assignment_ord, unassigned, new_vars, constraints, fc, state)
                    if result: return True
            else:
                result = backtrack(assignment, assignment_ord, unassigned, vars, constraints, fc, state)
                if result: return True
        else:
            print(out(assignment_ord, assignment, "failure", state['branch']))
            state['branch'] += 1
        del assignment[var]

    unassigned.append(var)
    assignment_ord.pop()
    return False


def solve(vars, constraints, fc):
    #all values are unassigned first
    unassigned = [var for var in vars]

    use_fc = (fc == 'fc')
    state = {'branch': 1}

    backtrack({}, [], unassigned, vars, constraints, use_fc, state)

def main():
    var_file, con_file, fc = sys.argv[1:]

    vars = {}
    constraints = []

    with open(var_file, mode="r") as f: 
        var_file_txt = f.readlines()
        for line in var_file_txt:
            line = line.strip()
            if not line: continue
            line_split = line.split()
            vars[line_split[0][:1]] = [int(x) for x in line_split[1:]]

    with open(con_file, mode="r") as f:
        con_file_txt = f.readlines()
        for line in con_file_txt:
            line = line.strip()
            if not line: continue
            constraints.append(line.split())

    solve(vars, constraints, fc)

    


if __name__ == "__main__":
    main()
