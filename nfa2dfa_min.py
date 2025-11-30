import json
import sys
from collections import defaultdict, deque
from typing import Dict, Set, FrozenSet, Tuple, List

# -------------------- NFA / DFA --------------------

class NFA:
    def __init__(self, states, alphabet, start, accepts, transitions):
        self.states: Set[str] = set(states)
        self.alphabet: Set[str] = set("eps" if a == "ε" else a for a in alphabet)
        self.start: str = start
        self.accepts: Set[str] = set(accepts)
        self.trans: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        for (u, sym), tos in transitions.items():
            sym = "eps" if sym == "ε" else sym
            for v in tos:
                self.trans[(u, sym)].add(v)

    @staticmethod
    def from_json(obj: dict) -> "NFA":
        raw = defaultdict(set)
        for t in obj["transitions"]:
            u, a, v = t["from"], t["symbol"], t["to"]
            raw[(u, a)].add(v)
        return NFA(obj["states"], obj["alphabet"], obj["start"], obj["accepts"], raw)


class DFA:
    def __init__(self, states, alphabet, start, accepts, transitions):
        self.states: Set[str] = set(states)
        self.alphabet: Set[str] = set(alphabet)
        self.start: str = start
        self.accepts: Set[str] = set(accepts)
        self.trans: Dict[Tuple[str, str], str] = dict(transitions)

    def to_json(self) -> dict:
        return {
            "states": sorted(self.states),
            "alphabet": sorted(self.alphabet),
            "start": self.start,
            "accepts": sorted(self.accepts),
            "transitions": [
                {"from": u, "symbol": a, "to": v}
                for (u, a), v in sorted(self.trans.items())
            ],
        }

    def to_dot(self) -> str:
        # 精简 DOT：全 ASCII，去注释；标签合并为 "a,b"
        lines = ['digraph DFA {', 'rankdir=LR;', 'node [shape=circle];']
        lines.append('__start__ [shape=point];')
        lines.append(f'__start__ -> "{self.start}";')

        for s in sorted(self.states):
            shape = "doublecircle" if s in self.accepts else "circle"
            lines.append(f'"{s}" [shape={shape}];')

        grouped = defaultdict(list)
        for (u, a), v in self.trans.items():
            grouped[(u, v)].append("eps" if a == "ε" else a)

        for (u, v), lab in grouped.items():
            label = ",".join(sorted(set(lab)))
            label = label.encode("ascii", "ignore").decode("ascii")
            lines.append(f'"{u}" -> "{v}" [label="{label}"];')
        lines.append("}")
        return "\n".join(lines)

# -------------------- NFA -> DFA (subset) --------------------

EPS = "eps"

def epsilon_closure(nfa: NFA, S: Set[str]) -> Set[str]:
    stack = list(S)
    clo = set(S)
    while stack:
        s = stack.pop()
        for t in nfa.trans.get((s, EPS), []):
            if t not in clo:
                clo.add(t)
                stack.append(t)
    return clo

def move(nfa: NFA, S: Set[str], a: str) -> Set[str]:
    res = set()
    for s in S:
        res.update(nfa.trans.get((s, a), []))
    return res

def nfa_to_dfa_ascii(nfa: NFA):
    start_set = frozenset(epsilon_closure(nfa, {nfa.start}))
    queue = deque([start_set])
    seen: Set[FrozenSet[str]] = {start_set}

    name_of: Dict[FrozenSet[str], str] = {start_set: "D0"}
    next_id = 1

    trans = {}
    states = {"D0"}
    accepts = set()

    while queue:
        S = queue.popleft()
        Sname = name_of[S]
        if any(s in nfa.accepts for s in S):
            accepts.add(Sname)
        for a in nfa.alphabet:
            if a == EPS:
                continue
            U = epsilon_closure(nfa, move(nfa, set(S), a))
            if not U:
                continue  # 允许缺边
            Uf = frozenset(U)
            if Uf not in seen:
                seen.add(Uf)
                name_of[Uf] = f"D{next_id}"
                next_id += 1
                states.add(name_of[Uf])
                queue.append(Uf)
            trans[(Sname, a)] = name_of[Uf]

    dfa = DFA(states, set(x for x in nfa.alphabet if x != EPS), "D0", accepts, trans)
    return dfa

# -------------------- DFA Min (no sink in OUTPUT) --------------------

def minimize_dfa(dfa: DFA) -> DFA:
    """
    使用内部 sink 做 Hopcroft 分割，但最终输出：
    - 去除 sink 及其边
    - 去除不可达/未使用状态
    - 从起点 BFS 重命名为 M0,M1,...
    """
    sink = "_SINK_"
    trans = dict(dfa.trans)
    states = set(dfa.states)
    need_sink = False
    for s in list(states):
        for a in dfa.alphabet:
            if (s, a) not in trans:
                trans[(s, a)] = sink
                need_sink = True
    if need_sink:
        states.add(sink)
        for a in dfa.alphabet:
            trans[(sink, a)] = sink

    # Hopcroft
    P = [set(dfa.accepts), states - set(dfa.accepts)]
    W = [set(dfa.accepts), states - set(dfa.accepts)]

    pred = {a: defaultdict(set) for a in dfa.alphabet}
    for (u, a), v in trans.items():
        pred[a][v].add(u)

    while W:
        A = W.pop()
        for a in dfa.alphabet:
            X = set()
            for q in A:
                X |= pred[a].get(q, set())
            newP = []
            for Y in P:
                i, d = X & Y, Y - X
                if i and d:
                    newP += [i, d]
                    if Y in W:
                        W.remove(Y); W += [i, d]
                    else:
                        W.append(i if len(i) <= len(d) else d)
                else:
                    newP.append(Y)
            P = newP

    # 块代表 → 新状态（先临时命名）
    rep = {}
    for B in P:
        if not B:
            continue
        name = f"TMP_{len({v for v in rep.values()})}"
        for s in B:
            rep[s] = name

    # 生成转移并移除 sink 边/点
    mtrans = {}
    for (u, a), v in trans.items():
        mu = rep[u]; mv = rep[v]
        if sink in (u, v):
            continue  # 移除与 sink 相关
        mtrans[(mu, a)] = mv

    mstart = rep[dfa.start]
    maccepts = {rep[s] for s in dfa.accepts}

    # 仅保留可达（从 mstart 出发）
    reachable = {mstart}
    q = deque([mstart])
    while q:
        u = q.popleft()
        for a in dfa.alphabet:
            v = mtrans.get((u, a))
            if v and v not in reachable:
                reachable.add(v); q.append(v)

    # 只保留使用到的状态与边
    mstates = set(reachable) | maccepts
    mtrans = {(u, a): v for (u, a), v in mtrans.items() if u in mstates and v in mstates}

    # 从起点 BFS 重命名为 M0,M1,...
    order = []
    seen = set()
    q = deque([mstart])
    while q:
        u = q.popleft()
        if u in seen: continue
        seen.add(u); order.append(u)
        for a in sorted(dfa.alphabet):
            v = mtrans.get((u, a))
            if v and v not in seen: q.append(v)
    for u in sorted(mstates):
        if u not in seen:  # 孤立但在接受集，放在后面
            order.append(u)

    rename = {u: f"M{i}" for i, u in enumerate(order)}
    mstates2 = {rename[u] for u in mstates}
    mstart2 = rename[mstart]
    maccepts2 = {rename[u] for u in maccepts}
    mtrans2 = {(rename[u], a): rename[v] for (u, a), v in mtrans.items()}

    return DFA(mstates2, set(dfa.alphabet), mstart2, maccepts2, mtrans2)

# -------------------- CLI --------------------

USAGE = """
terminal 输入:
  python nfa2dfa_min.py input.json out_prefix
  dot -Tpng out_prefix.dfa.dot -o dfa.png
  dot -Tpng out_prefix.min.dot -o dfa_min.png
"""

def main():
    if len(sys.argv) != 3:
        print(USAGE); sys.exit(1)

    src, prefix = sys.argv[1], sys.argv[2]
    with open(src, "r", encoding="utf-8") as f:
        nfa = NFA.from_json(json.load(f))

    dfa = nfa_to_dfa_ascii(nfa)
    with open(prefix + ".dfa.json", "w", encoding="utf-8") as f:
        json.dump(dfa.to_json(), f, ensure_ascii=True, indent=2)
    with open(prefix + ".dfa.dot", "w", encoding="utf-8") as f:
        f.write(dfa.to_dot())

    mdfa = minimize_dfa(dfa)          # ← 输出不带 sink、不带多余节点
    with open(prefix + ".min.json", "w", encoding="utf-8") as f:
        json.dump(mdfa.to_json(), f, ensure_ascii=True, indent=2)
    with open(prefix + ".min.dot", "w", encoding="utf-8") as f:
        f.write(mdfa.to_dot())

    print("Done:",
          prefix + ".dfa.json,",
          prefix + ".dfa.dot,",
          prefix + ".min.json,",
          prefix + ".min.dot")

if __name__ == "__main__":
    main()
