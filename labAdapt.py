import time
from backtracking import CSP, forward_checking, ac3
 
 
class SolverTimeout(Exception):
    pass
 
#Since I used the lab i need to adapt it for this situation 
def build_csp(problem):
    p, ov, tight = problem, problem.overlap, problem.tight
    ids = p.course_ids
 
    neighbors = {c: set() for c in ids}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if b in tight[a] or (p.room_set[a] & p.room_set[b]):
                neighbors[a].add(b)
                neighbors[b].add(a)
    
    state = {"deadline": None, "calls": 0}
 
    def constraints(a, va, b, vb):
        if state["deadline"] is not None:            
            state["calls"] += 1
            if state["calls"] & 0xFFFF == 0 and time.time() > state["deadline"]:
                raise SolverTimeout
        sa, ra = va
        sb, rb = vb
        if sb not in ov[sa]:                           
            return True
        if ra == rb:                                  
            return False
        return b not in tight[a]                      
 
    csp = CSP(ids, p.domains, neighbors, constraints)
    csp.state = state
    return csp
 
 
def forward_checking_ac3(csp, var, value, assignment, removals=None):
    """Inference = lab Forward Checking, then lab AC-3 over the unassigned neighbourhood."""
    if not forward_checking(csp, var, value, assignment, removals):
        return False
    queue = [(xk, xi)
             for xi in csp.neighbors[var] if xi not in assignment
             for xk in csp.neighbors[xi] if xk not in assignment and xk != xi]
    return ac3(csp, queue, removals)