import sys
from collections import defaultdict


NEGATION_PREFIXES = ("~", "∼", "¬")
TRUE_LITERAL = "__TRUE__"
FALSE_LITERAL = "__FALSE__"


class Clause(object):
    __slots__ = ("literals", "literal_set", "parents", "is_contradiction")

    def __init__(self, literals, parents=None, is_contradiction=False):
        self.literals = tuple(literals)
        self.literal_set = frozenset(literals)
        self.parents = parents
        self.is_contradiction = is_contradiction

    def render(self):
        if self.is_contradiction:
            return "Contradiction"
        return " ".join(self.literals)


def complement(literal):
    if literal.startswith("~"):
        return literal[1:]
    return "~" + literal


def normalize_literal(token):
    token = token.strip()
    negated = False

    while token and token[0] in NEGATION_PREFIXES:
        negated = not negated
        token = token[1:]

    if not token:
        return None

    if token == "True":
        return FALSE_LITERAL if negated else TRUE_LITERAL
    if token == "False":
        return TRUE_LITERAL if negated else FALSE_LITERAL

    return ("~" + token) if negated else token


def normalize_clause(tokens):
    ordered = []
    seen = set()

    for token in tokens:
        literal = normalize_literal(token)
        if literal is None:
            continue
        if literal == TRUE_LITERAL:
            return None
        if literal == FALSE_LITERAL:
            continue

        comp = complement(literal)
        if comp in seen:
            return None
        if literal not in seen:
            seen.add(literal)
            ordered.append(literal)

    return tuple(ordered)


def make_resolvents(clause_i, clause_j):
    local_seen = set()
    j_literals = clause_j.literals
    j_set = clause_j.literal_set

    for pivot in clause_i.literals:
        pivot_complement = complement(pivot)
        if pivot_complement not in j_set:
            continue

        merged = []
        merged_seen = set()
        tautology = False

        for literal in clause_i.literals:
            if literal == pivot:
                continue
            merged.append(literal)
            merged_seen.add(literal)

        for literal in j_literals:
            if literal == pivot_complement or literal in merged_seen:
                continue
            if complement(literal) in merged_seen:
                tautology = True
                break
            merged.append(literal)
            merged_seen.add(literal)

        if tautology:
            continue

        signature = frozenset(merged)
        if signature in local_seen:
            continue
        local_seen.add(signature)
        yield tuple(merged)


class KnowledgeBase(object):
    def __init__(self):
        self.clauses = []
        self.seen = set()
        self.literal_index = defaultdict(list)

    def add_clause(self, literals, parents=None):
        signature = frozenset(literals)
        if signature in self.seen:
            return False

        clause = Clause(literals, parents=parents)
        self.clauses.append(clause)
        self.seen.add(signature)

        clause_index = len(self.clauses)
        for literal in clause.literals:
            self.literal_index[literal].append(clause_index)

        return True

    def add_contradiction(self, parents):
        clause = Clause((), parents=parents, is_contradiction=True)
        self.clauses.append(clause)


def load_input(path):
    with open(path, "r") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    if not lines:
        raise ValueError("Input file is empty.")

    return lines[:-1], lines[-1]


def add_line_as_clause(kb, line):
    normalized = normalize_clause(line.split())
    if normalized is None:
        return

    if not normalized:
        kb.add_contradiction(None)
        return

    kb.add_clause(normalized)


def add_negated_query(kb, query_line):
    query_clause = normalize_clause(query_line.split())
    if query_clause is None:
        return True

    for literal in query_clause:
        negated_literal = complement(literal)
        normalized = normalize_clause((negated_literal,))
        if normalized is None:
            continue
        if not normalized:
            kb.add_contradiction(None)
            return False
        kb.add_clause(normalized)

    return False


def run_resolution(kb):
    index = 0

    while index < len(kb.clauses):
        clause_i = kb.clauses[index]
        clause_i_number = index + 1

        if clause_i.is_contradiction:
            return True

        candidate_indices = set()
        for literal in clause_i.literals:
            candidate_indices.update(kb.literal_index.get(complement(literal), ()))

        if candidate_indices:
            for clause_j_number in sorted(x for x in candidate_indices if x < clause_i_number):
                clause_j = kb.clauses[clause_j_number - 1]
                for resolvent in make_resolvents(clause_i, clause_j):
                    if not resolvent:
                        kb.add_contradiction((clause_i_number, clause_j_number))
                        return True
                    kb.add_clause(resolvent, parents=(clause_i_number, clause_j_number))

        index += 1

    return False


def print_output(kb, is_valid):
    for index, clause in enumerate(kb.clauses, start=1):
        if clause.parents is None:
            parent_text = "{}"
        else:
            parent_text = "{{{}, {}}}".format(clause.parents[0], clause.parents[1])
        print("{}. {} {}".format(index, clause.render(), parent_text))

    print("Valid" if is_valid else "Fail")


def main():
    try:
        initial_lines, query_line = load_input(sys.argv[1])
    except Exception as error:
        sys.stderr.write(str(error) + "\n")
        sys.exit(1)

    kb = KnowledgeBase()

    for line in initial_lines:
        add_line_as_clause(kb, line)
        if kb.clauses and kb.clauses[-1].is_contradiction:
            print_output(kb, True)
            return

    tautology_query = add_negated_query(kb, query_line)
    if kb.clauses and kb.clauses[-1].is_contradiction:
        print_output(kb, True)
        return

    if tautology_query:
        print_output(kb, True)
        return

    is_valid = run_resolution(kb)
    print_output(kb, is_valid)


if __name__ == "__main__":
    main()
