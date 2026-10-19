import random
import time
 
 
def min_conflicts_soft(csp, problem, initial, time_limit=8.0, seed=0,
                       noise=0.08, max_stale=3000, sample=200):
    rng = random.Random(seed)
    hw = problem.w["H"]
    domains = csp.initial_domains          # full domains (the search leaves csp.domains pruned)
    cur = dict(initial)
 
    def cost(var, val):
        return hw * csp.nconflicts(var, val, cur) + problem.partial_soft(var, val, cur)
 
    def total():
        t = sum(problem.unary_cost(c, *v) for c, v in cur.items())
        t += sum(problem.group_cost(k, cur) for k in problem.groups)
        t += hw * sum(csp.nconflicts(c, v, cur) for c, v in cur.items()) // 2
        return t
 
    best_cost = cur_cost = total()
    best, stale, steps, t0 = dict(cur), 0, 0, time.time()
    variables = list(csp.variables)
    while time.time() - t0 < time_limit and stale < max_stale:
        steps += 1
        conflicted = [v for v in variables if cost(v, cur[v]) > 0]
        if not conflicted:
            break
        var = rng.choice(conflicted)
        old, old_cost = cur[var], cost(var, cur[var])
        dom = domains[var]
        cands = dom if len(dom) <= sample else rng.sample(dom, sample)
        if rng.random() < noise:
            new = rng.choice(cands)
            new_cost = cost(var, new)
        else:
            scored = [(cost(var, v), rng.random(), v) for v in cands]
            new_cost, _, new = min(scored)
        if new != old:
            cur[var] = new
            cur_cost += new_cost - old_cost
        if cur_cost < best_cost:
            best_cost, best, stale = cur_cost, dict(cur), 0
        else:
            stale += 1
    return best, steps