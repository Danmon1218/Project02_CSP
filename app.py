"""
UIC CS 411 Project 2: University Class Scheduling (CSP) - Main Entry Point

Instructions for Students:
1. You have complete flexibility in how you design your project folder structure, classes, and helper modules.
2. Implement your scheduling logic inside or called from `studentscheduler()`.
3. Your scheduler should read data dynamically from `data_dir` (default: 'data').
   - If we change or replace the datasets in `data/`, your solution should still work dynamically.
4. Your scheduler must generate the final timetable and save it as `<studentid>_timetable.csv` inside `output_dir` (default: 'data').
5. The function `studentscheduler()` must return the path to the created CSV file.
6. In your report and video presentation, explain how your project directory and architecture are built.
"""

import os
import re
import csv
import time 
import sys 

# TODO: Import your custom modules, solvers, or constraint models here.
# Example: from my_scheduler.csp import CSPSolver
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#imports 
from backtracking import backtracking_search_heuristics, mrv, lcv 
from localsearch import min_conflicts


#import my helper functions 
from otherHelpers import Problem, verify,  load_dataset
from labAdapt import build_csp, forward_checking_ac3, SolverTimeout
from softCon import min_conflicts_soft 



#if the report empty set this as a default value 
default = "dmont21" 

#make sure the program doesnt run too long 
time_limit = 30.0 #seconds 
local_time_limit = 30.0 

SEED = 42 



#fields that will be used from the csvs 

fields = ["course_id", "room_id", "slot_id", "instructor_id", "cohort_id", "day", "start_time", "end_time"]





def get_student_id():
    """
    Helper function to extract your UID (netID) from report.md.
    Alternatively, you may specify your student ID directly.
    """
    report_path = os.path.join(os.path.dirname(__file__), 'report.md')
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check for UID (netID) or NetID or UIN
                match = re.search(r'-\s*\*\*UID \(netID\):\*\*\s*(.*)', content, re.IGNORECASE)
                if not match:
                    match = re.search(r'-\s*\*\*UIN:\*\*\s*(.*)', content, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    if val and not (val.startswith('[') and val.endswith(']')):
                        return re.sub(r'[^a-zA-Z0-9_-]', '_', val)
        except Exception:
            pass
    return default




#function to write to the csv 
def _write_csv(problem, assign, path):
    rows = []
    for cid in problem.course_ids:
        if cid not in assign:
            continue
        s, r = assign[cid]
        c, sl = problem.course[cid], problem.slots[s]
        rows.append({"course_id": cid, "room_id": problem.rooms[r].rid, "slot_id": sl.sid,
                     "instructor_id": ";".join(c.instructors), "cohort_id": ";".join(c.cohorts),
                     "day": sl.day, "start_time": sl.start_s, "end_time": sl.end_s})
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def studentscheduler(data_dir="data", output_dir="data", student_id=None):
    """
    Main entry point for generating university course schedule.

    Args:
        data_dir (str): Directory containing input CSV files (e.g. courses.csv, rooms.csv, instructors.csv, time_slots.csv, student_cohorts.csv).
        output_dir (str): Directory where the output '<studentid>_timetable.csv' will be saved.
        student_id (str, optional): The student ID to use in filename. Defaults to student ID in report.md.

    Returns:
        str: Path to the generated '<studentid>_timetable.csv' file.
    """
    if student_id is None:
        student_id = get_student_id()

    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{student_id}_timetable.csv"
    output_path = os.path.join(output_dir, output_filename)

    # =========================================================================
    # TODO: Implement your CSP / Local Search scheduling solution below.
    #
    # 1. Load data from data_dir (e.g., courses.csv, instructors.csv, rooms.csv, time_slots.csv, student_cohorts.csv).
    # 2. Formulate CSP variables, domains, hard constraints, and soft constraints.
    # 3. Solve the schedule using Backtracking (MRV, LCV, Forward Checking) and/or Local Search.
    # 4. Save the resulting schedule to `output_path`.
    #
    # Expected CSV columns (recommended):
    # course_id, room_id, slot_id, instructor_id, cohort_id, day, start_time, end_time
    # =========================================================================
    problem = Problem(load_dataset(data_dir))

    csp = build_csp(problem)

    # 1. Feasible schedule: lab backtracking with MRV (+Degree), LCV, Forward Checking + AC-3
    csp.state["deadline"] = time.time() + time_limit
    try:
        assign = backtracking_search_heuristics(csp, mrv, lcv, forward_checking_ac3)
    except SolverTimeout:
        assign = None
    csp.state["deadline"] = None
    csp_ok = assign is not None
    nodes, backtracks = csp.nodes_expanded, csp.backtracks
    csp.domains = {v: list(d) for v, d in csp.initial_domains.items()}   # search leaves domains pruned
    if not csp_ok:
        # Fallback: lab Min-Conflicts from a random start repairs hard conflicts
        assign = min_conflicts(csp, max_steps=5000)

    # 2. Min-Conflicts extended with soft penalties (S1-S5) -> better quality schedule
    before = verify(problem, assign)
    assign, steps = min_conflicts_soft(csp, problem, assign, time_limit=time_limit, seed=SEED)
    report = verify(problem, assign)

    _write_csv(problem, assign, output_path)

    for w in problem.ds.warnings + problem.notes:
        print(f"[warning] {w}")
    print(f"[csp] {'solved' if csp_ok else 'FAILED (lab min_conflicts fallback used)'}; "
          f"nodes={nodes} backtracks={backtracks}")
    print(f"[local search] {steps} min-conflicts steps")
    print(f"[soft] penalty {before['soft_total']} -> {report['soft_total']}  {report['soft']}")
    print(f"[hard] violations: {report['hard_total']}  feasible={report['feasible']}")
    for k, v in report["hard"].items():
        for msg in v:
            print(f"   {k}: {msg}")
    return output_path


if __name__ == "__main__":
    generated_file = studentscheduler()
    print(f"Timetable generation completed. Output file: {generated_file}")
