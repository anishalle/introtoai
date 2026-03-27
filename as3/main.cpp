#include <array>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>

using namespace std;

array<string, 3> NEGATION_PREFIXES{"~", "∼", "¬"};

typedef struct Literal {
  string name;
  bool negated = false;

  Literal() {}
  Literal(string n, bool neg) : name(n), negated(neg) {}

  Literal complement() const { return Literal{name, !negated}; }
  bool operator==(const Literal &other) const {
    return name == other.name && negated == other.negated;
  }
  // SET NEEDS THIS in order to store it.
  // this is because set operations are ORDERED, and we aren't using unordered
  // set
  bool operator<(const Literal &other) const {
    if (name != other.name) {
      return name < other.name;
    }
    // number values used for boleans ( 0 < 1)
    return negated < other.negated;
  }
  string toString() const { return negated ? "~" + name : name; };
} Literal;

typedef struct Clause {
  set<Literal> literals;
  bool contains(const Literal &literal) const {
    return literals.find(literal) != literals.end();
  }
  bool isEmpty() const { return literals.empty(); }
  bool isTautology() const {
    // const for faster runtimes
    for (const auto &literal : literals) {
      if (contains(literal.complement())) {
        // if our clause contains its complement, then it is a tautology
        return true;
      }
    }
    // if no literals have their complement, our clause is not a tautology
    return false;
  }
  string toString() const {
    if (isEmpty())
      return "Contradiction";
    string res;
    bool first = true;
    // loop through literals, adding spaces between them
    for (const auto &lit : literals) {
      if (!first)
        res += " ";
      res += lit.toString();
      first = false;
    }
    return res;
  }

  bool operator==(const Clause &other) const {
    return literals == other.literals;
  }
  bool operator<(const Clause &other) const {
    return literals < other.literals;
  }
} Clause;

// why do we need a clauseentry?
// easier to keep track of parents this way
typedef struct ClauseEntry {
  Clause clause;
  pair<int, int> parents = {-1, -1}; //-1 -1 means it is the origial clause

  ClauseEntry() {}
  ClauseEntry(const Clause &c, pair<int, int> p) : clause(c), parents(p) {}
} ClauseEntry;

class KnowledgeBase {
private:
  vector<ClauseEntry> entries;
  set<Clause> seen;

public:
  // when we add a clause, if we've seen it, we don't add it
  // otherwise, add it to our entries with its own parents
  // if a clause is not present then it will automaitcally be the original
  // clause
  bool addClause(const Clause &clause, pair<int, int> parents = {-1, -1}) {
    if (seen.count(clause))
      return false;
    seen.insert(clause);
    entries.push_back({clause, parents});
    return true;
  }
  size_t size() const { return entries.size(); }
  const ClauseEntry &operator[](size_t i) const { return entries[i]; }
  ClauseEntry &operator[](size_t i) { return entries[i]; }
  void print() const {
    for (int i = 0; i < entries.size(); i++) {
      const auto &e = entries[i];

      cout << (i + 1) << ". ";
      cout << e.clause.toString() << " ";

      if (e.parents.first == -1) {
        cout << "{}";
      } else {
        cout << "{" << e.parents.first << ", " << e.parents.second << "}";
      }

      cout << "\n";
    }
  }
};
// end class definitions

bool isNegated(const string &literal, string &matchedPrefix) {
  for (const auto &prefix : NEGATION_PREFIXES) {
    // if there's a negation at the beginning
    if (literal.rfind(prefix, 0) == 0) {
      // set reference of matchedprefix to the prefix we matched with
      matchedPrefix = prefix;
      return true;
    }
  }
  return false;
}

Literal parseLiteral(const string &literal) {
  string matchedPrefix;
  if (isNegated(literal, matchedPrefix)) {
    // include string from the END of the matchedPrefix to the end of the string
    return Literal(literal.substr(matchedPrefix.size()), true);
  }
  // otherwise, return the string and that it is not negated
  return Literal(literal, false);
}

Clause parseClause(const string &line) {
  Clause clause;
  string literal;
  stringstream ss(line);
  // while string has tokens
  while (ss >> literal) {
    clause.literals.insert(parseLiteral(literal));
  }
  return clause;
}

/**
 * IO OPS
 */

// each line is a clause
vector<string> readLines(const string &filename) {
  ifstream fin(filename);
  if (!fin) {
    throw runtime_error("Could not open file: " + filename);
  }

  vector<string> lines;
  string line;
  while (getline(fin, line)) {
    if (!line.empty()) {
      lines.push_back(line);
    }
  }
  return lines;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    cerr << "You must input a file name" << endl;
    return 1;
  }

  KnowledgeBase kb;
  vector<string> lines = readLines(argv[1]);

  for (int i = 0; i + 1 < lines.size(); i++) {
    Clause clause = parseClause(lines[i]);
    kb.addClause(clause);
  }
  Clause query = parseClause(lines.back());
  kb.print();

  return 0;
}
