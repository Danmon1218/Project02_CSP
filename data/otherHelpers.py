import csv
import fnmatch
import json
import os
import re
import math 
from collections import defaultdict
from dataclasses import dataclass, field





#helper functions/classes here


#helper class to help define the problem we want to handle 
class Problem:
    #consrtuctor 
    def __init__(self, ds): 
        self.ds = ds
        self.w = ds.weights 
        self.slots = ds.slots 
        self.n_slots = len(self.slots)
        #handles the information from the csv 
        self.course = {c.cid: c for c in ds.courses}
        self.course_ids = [c.cid for c in ds.courses]
        self.instructors = ds.instructors 
        self.slot_index = {s.sid: i for i, s in enumerate(self.slots)}


        #slots overlaping in time 
        self.overlap = [] 
        for i in self.slots: 
            self.overlap.append(frozenset(j for j,b in enumerate(self.slots) if i.day == b.day and i.start < b.end and b.start < i.end ))


        #eligible rooms 
        self.rooms = ds.rooms 
        self.eligible = [i for i, r in enumerate(self.rooms)if r.available and r.capacity > 0 and r.rid not in ds.excluded_rooms]
        self.room_index = {r.rid: i for i, r in enumerate(self.rooms)}


        #groups cases 
        self.groups = defaultdict(list) #the course id 
        self.group_keys = {c: [] for c in self.course_ids}


        #loop through for the course ids 
        for c in ds.courses:
            #loop through the instructors 
            for iid in c.instructors:
                self.groups[("I", iid)].append(c.cid)
                self.group_keys[c.cid].append(("I", iid))
            #cohorts case 
            for h in c.cohorts: 
                self.groups[("C", h)].append(c.cid)
                self.group_keys[c.cid].append(("C", h))

        self.tight = {c: set() for c in self.course_ids}
        for members in self.groups.values():
            for a in members:
                for b in members:
                    if a != b:
                        self.tight[a].add(b)

        self.notes = []
        self.domains = {}
        self.room_set = {}
        for c in ds.courses:
            self._build_domain(c)


    #helper to build the domains 
    def _build_domain(self, c):
        elig = self.eligible
        cap = lambda i: self.rooms[i].capacity
        mentioned = [self.room_index[r] for r in c.mentioned_rooms
                     if r in self.room_index and self.room_index[r] in elig]
        cands = [i for i in mentioned if cap(i) >= c.enrollment]
        if not cands:
            wants_lab = "lab" in c.context.lower()
            pool = [i for i in elig if cap(i) >= c.enrollment]
            cands = [i for i in pool if wants_lab or "lab" not in self.rooms[i].rtype.lower()] or pool
            if c.mentioned_rooms:
                self.notes.append(f"{c.cid}: requested rooms {c.mentioned_rooms} cannot hold "
                                  f"{c.enrollment} students; widened to all suitable rooms.")
        if not cands:
            best = max(elig, key=cap)
            cands = [best]
            self.notes.append(f"{c.cid}: no room can hold {c.enrollment}; H2 will be violated.")
        banned = set()
        for iid in c.instructors:
            banned |= {self.slot_index[s] for s in self.instructors[iid].unavailable if s in self.slot_index}
        dom = [(s, r) for s in range(self.n_slots) if s not in banned for r in cands]
        if not dom:
            self.notes.append(f"{c.cid}: instructor unavailability leaves no slot; H4 will be violated.")
            dom = [(s, r) for s in range(self.n_slots) for r in cands]
        self.domains[c.cid] = dom
        self.room_set[c.cid] = set(cands)

    #functions all for the constraints(costs)
    def s1(self, c, s):
        total = 0
        sl = self.slots[s]
        for iid in c.instructors:
            ins = self.instructors[iid]
            if ins.preferred:
                if sl.sid not in ins.preferred:
                    total += self.w["S1"]
            elif sl.start < 9 * 60 or sl.period.lower() == "evening":
                total += self.w["S1"] // 2      # default preference: avoid 8am / evening
        return total

    def s2(self, c, r):
        excess = self.rooms[r].capacity - c.enrollment
        thr = self.w["S2_THRESHOLD"]
        return self.w["S2"] * math.ceil((excess - thr) / 10) if excess > thr else 0

    def room_pref(self, c, r):
        rid = self.rooms[r].rid
        if c.preferred_rooms:
            return 0 if rid in c.preferred_rooms else self.w["ROOM_PREF"]
        if c.mentioned_rooms and rid not in c.mentioned_rooms:
            expanded = set(c.mentioned_rooms)
            return 0 if rid in expanded else self.w["ROOM_PREF"]
        return 0

    def unary_cost(self, cid, s, r):
        c = self.course[cid]
        return self.s1(c, s) + self.s2(c, r) + self.room_pref(c, r)

    def group_penalties(self, items, is_cohort):
        """items: [(slot_idx, room_idx)] -> (S3, S4, S5)."""
        by_day = defaultdict(list)
        for s, r in items:
            sl = self.slots[s]
            by_day[sl.day].append((sl.start, sl.end, self.rooms[r].building))
        s3 = s4 = s5 = 0
        b2b = self.w["BACK_TO_BACK_GAP"]
        for evs in by_day.values():
            evs.sort()
            run = 1
            for a, b in zip(evs, evs[1:]):
                gap = b[0] - a[1]
                if gap < 0:
                    run = 1
                elif gap <= b2b:
                    run += 1
                    if run > 2:
                        s4 += self.w["S4"]
                    if is_cohort and a[2] != b[2]:
                        s5 += self.w["S5"]
                else:
                    run = 1
                    if is_cohort:
                        s3 += self.w["S3"] * max(1, round(gap / 60))
        return s3, s4, s5

    def group_cost(self, key, assign, override=None):
        items = []
        for m in self.groups[key]:
            v = override[1] if override and override[0] == m else assign.get(m)
            if v is not None:
                items.append(v)
        return sum(self.group_penalties(items, key[0] == "C"))

    def partial_soft(self, cid, v, assign):
        cost = self.unary_cost(cid, v[0], v[1])
        for key in self.group_keys[cid]:
            cost += self.group_cost(key, assign, (cid, v))
        return cost






#section to load the data and proper information into the right places
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DEFAULT_WEIGHTS = {
    "H": 1000, "S1": 10, "S2": 5, "S3": 8, "S4": 12, "S5": 6,
    "ROOM_PREF": 6,           # preferred / requested room not used
    "S2_THRESHOLD": 30,       # unused seats tolerated before S2 applies
    "BACK_TO_BACK_GAP": 20,   # minutes: gap <= this counts as back-to-back
}
DEFAULT_ENROLLMENT = {"graduate": 20, "undergraduate": 30}


@dataclass
class Slot:
    sid: str
    day: str
    start: int
    end: int
    start_s: str
    end_s: str
    period: str


@dataclass
class Room:
    rid: str
    building: str
    capacity: int
    rtype: str
    available: bool
    features: str = ""


@dataclass
class Instructor:
    iid: str
    name: str
    unavailable: set = field(default_factory=set)   # slot ids
    preferred: set = field(default_factory=set)     # slot ids (empty = no declared preference)


@dataclass
class Course:
    cid: str
    level: str
    enrollment: int
    instructors: list
    cohorts: list
    mentioned_rooms: list
    preferred_rooms: set
    context: str


@dataclass
class Dataset:
    courses: list
    rooms: list
    slots: list
    instructors: dict
    cohorts: dict            # cohort_id -> (size, [course ids])
    excluded_rooms: set
    weights: dict
    warnings: list


def _read(path, required=True):
    if not os.path.exists(path):
        if required:
            raise FileNotFoundError(f"Required dataset not found: {path}")
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(f)]


def split_list(text):
    return [t.strip() for t in re.split(r"[;|]", text or "") if t.strip()]


def to_minutes(text):
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*([AaPp][Mm])?", text)
    if not m:
        raise ValueError(f"Bad time value: {text!r}")
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap:
        h = h % 12 + (12 if ap.lower() == "pm" else 0)
    return h * 60 + mi


def expand_room_token(token):
    """'TECH 201/202/203/204' -> ['TECH 201', ..., 'TECH 204']."""
    m = re.match(r"^(.*?)(\d+(?:\s*/\s*\d+)+)$", token)
    if m:
        return [m.group(1) + n.strip() for n in m.group(2).split("/")]
    return [token]


def _truthy(v):
    return v.strip().lower() in ("yes", "y", "true", "1")


def _slot_tokens(tokens, slots):
    """Resolve slot ids / wildcards / day names / period names to a set of slot ids."""
    out = set()
    for tok in tokens:
        t = tok.lower()
        for s in slots:
            if (fnmatch.fnmatch(s.sid.lower(), t) or s.day.lower() == t
                    or s.period.lower() == t):
                out.add(s.sid)
    return out


def _load_weights(data_dir, warnings):
    weights = dict(DEFAULT_WEIGHTS)
    for name in ("constraints.json", "sample_constraints.json"):
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                spec = json.load(f)
            for item in spec.get("hard_constraints", []):
                weights["H"] = item.get("penalty_weight", weights["H"])
            for item in spec.get("soft_constraints", []):
                m = re.match(r"(S\d)", item.get("id", ""))
                if m and "penalty_weight" in item:
                    weights[m.group(1)] = item["penalty_weight"]
            break
        except Exception as exc:  # pragma: no cover
            warnings.append(f"Could not parse {name}: {exc}")
    return weights


def load_dataset(data_dir):
    warnings = []
    c_rows = _read(os.path.join(data_dir, "courses.csv"))
    i_rows = _read(os.path.join(data_dir, "instructors.csv"))
    r_rows = _read(os.path.join(data_dir, "rooms.csv"))
    t_rows = _read(os.path.join(data_dir, "time_slots.csv"))
    h_rows = _read(os.path.join(data_dir, "student_cohorts.csv"))
    k_rows = _read(os.path.join(data_dir, "constraints.csv"), required=False)

    # ---- time slots (sorted by day then start time)
    slots = [Slot(r["slot_id"], r["day"], to_minutes(r["start_time"]), to_minutes(r["end_time"]),
                  r["start_time"], r["end_time"], r.get("period", "")) for r in t_rows]
    slots.sort(key=lambda s: (DAYS.index(s.day.lower()) if s.day.lower() in DAYS else 99, s.start))

    # ---- rooms
    rooms = []
    for r in r_rows:
        cap = r.get("scheduling_capacity") or r.get("physical_capacity") or r.get("capacity") or "0"
        rooms.append(Room(r["room_id"], r.get("building", ""), int(float(cap)),
                          r.get("room_type", ""), _truthy(r.get("available_for_regular_classes", "yes")),
                          r.get("features_or_constraints", "")))

    # ---- constraints.csv: excluded rooms (hard) and preferred rooms (soft)
    excluded, pref_rooms = set(), {}
    course_ids = {r["course_id"] for r in c_rows}
    for r in k_rows:
        rule, kind = r.get("rule", ""), r.get("constraint_type", "").lower()
        m = re.search(r"room_id\s*!=\s*'([^']+)'", rule)
        if m and kind == "hard":
            excluded.add(m.group(1))
        m = re.search(r"preferred_room\s*=\s*'([^']+)'", rule)
        if m:
            for cid in split_list(r.get("applies_to", "")):
                if cid in course_ids:
                    pref_rooms.setdefault(cid, set()).add(m.group(1))

    # ---- instructors (name -> id; course lists add extra links)
    instructors, by_name, course_link = {}, {}, {}
    for r in i_rows:
        ins = Instructor(r["instructor_id"], r.get("instructor_name", r["instructor_id"]))
        ins.unavailable = _slot_tokens(split_list(r.get("unavailable_slots", "")), slots)
        ins.preferred = _slot_tokens(split_list(r.get("preferred_slots", "")), slots)
        instructors[ins.iid] = ins
        by_name[ins.name.lower()] = ins.iid
        for cid in split_list(r.get("courses", "")):
            course_link.setdefault(cid, []).append(ins.iid)

    # ---- cohorts
    cohorts, course_cohorts = {}, {}
    for r in h_rows:
        courses = split_list(r.get("mandatory_courses", ""))
        cohorts[r["cohort_id"]] = (int(float(r.get("size") or 0)), courses)
        for cid in courses:
            course_cohorts.setdefault(cid, []).append(r["cohort_id"])
    for coh, (_, cl) in cohorts.items():
        for cid in cl:
            if cid not in course_ids:
                warnings.append(f"Cohort {coh} lists unknown course {cid}; ignored.")

    # ---- courses
    courses = []
    for r in c_rows:
        cid = r["course_id"]
        ids = list(course_link.get(cid, []))
        for name in split_list(r.get("instructors", "")):
            iid = by_name.get(name.lower())
            if iid is None:
                iid = "NAME:" + name
                instructors[iid] = Instructor(iid, name)
                by_name[name.lower()] = iid
                warnings.append(f"Instructor '{name}' (course {cid}) not in instructors.csv.")
            ids.append(iid)
        for iid in split_list(r.get("instructor_ids", "")):
            ids.append(iid)
        ids = list(dict.fromkeys(ids))
        coh = [h for h in course_cohorts.get(cid, [])]
        if r.get("enrollment"):
            enroll = int(float(r["enrollment"]))
        elif coh:
            enroll = max(cohorts[h][0] for h in coh)
        else:
            enroll = DEFAULT_ENROLLMENT.get(r.get("level", "").lower(), 30)
        mentioned = []
        for tok in split_list(r.get("rooms_mentioned", "")):
            mentioned.extend(expand_room_token(tok))
        courses.append(Course(cid, r.get("level", ""), enroll, ids, coh, mentioned,
                              pref_rooms.get(cid, set()), r.get("scheduling_context", "")))

    return Dataset(courses, rooms, slots, instructors, cohorts, excluded,
                   _load_weights(data_dir, warnings), warnings)


#final checks to make sure that the problem is able to be solved 
def verify(problem, assign):
    p, w = problem, problem.w
    hard = {k: [] for k in ("H1", "H2", "H3", "H4", "H5", "H6")}
    ids = list(p.course_ids)

    for cid in ids:
        if cid not in assign:
            hard["H6"].append(f"{cid} is not scheduled")
    placed = [c for c in ids if c in assign]

    for cid in placed:
        s, r = assign[cid]
        c, room = p.course[cid], p.rooms[r]
        if room.capacity < c.enrollment:
            hard["H2"].append(f"{cid}: enrollment {c.enrollment} > capacity {room.capacity} ({room.rid})")
        if (not room.available) or room.rid in p.ds.excluded_rooms:
            hard["H2"].append(f"{cid}: room {room.rid} not available for regular classes")
        for iid in c.instructors:
            if p.slots[s].sid in p.instructors[iid].unavailable:
                hard["H4"].append(f"{cid}: {iid} unavailable in {p.slots[s].sid}")

    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            (sa, ra), (sb, rb) = assign[a], assign[b]
            if sb not in p.overlap[sa]:
                continue
            if ra == rb:
                hard["H1"].append(f"{a} & {b} share room {p.rooms[ra].rid} at overlapping times")
            for iid in set(p.course[a].instructors) & set(p.course[b].instructors):
                hard["H3"].append(f"{a} & {b} share instructor {iid} at overlapping times")
            for h in set(p.course[a].cohorts) & set(p.course[b].cohorts):
                hard["H5"].append(f"{a} & {b} clash for cohort {h}")

    soft = {"S1": 0, "S2": 0, "S3": 0, "S4": 0, "S5": 0, "ROOM_PREF": 0}
    for cid in placed:
        s, r = assign[cid]
        c = p.course[cid]
        soft["S1"] += p.s1(c, s)
        soft["S2"] += p.s2(c, r)
        soft["ROOM_PREF"] += p.room_pref(c, r)
    for key, members in p.groups.items():
        items = [assign[m] for m in members if m in assign]
        s3, s4, s5 = p.group_penalties(items, key[0] == "C")
        soft["S3"] += s3
        soft["S4"] += s4
        soft["S5"] += s5
    return {"hard": hard, "soft": soft,
            "hard_total": sum(len(v) for v in hard.values()),
            "soft_total": sum(soft.values()),
            "feasible": all(not v for v in hard.values())}


