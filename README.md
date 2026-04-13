# 📅 Automatic Timetable Generator — University of Yaoundé I

**INF 4178 — Software Engineering I | Practical Exercise — Project 1**  
Department of Computer Science, Faculty of Science  
*April 2026*

---

## 📌 Problem Statement

The Department of Computer Science of the University of Yaoundé I needs a software system that **automatically generates weekly timetables** for its classes, respecting the following constraints:

| # | Specification |
|---|---------------|
| S1 | No class may be scheduled simultaneously in multiple rooms, for multiple courses, with multiple teachers at the same time slot |
| S2 | Every course in a class's curriculum must be scheduled **exactly once per week** |
| S3 | A class must not be assigned a course outside its own curriculum |
| S4 | The timetable must **maximize sessions scheduled before noon** (periods P1 and P2) |

**Time grid:** 6 days (Monday–Saturday) × 5 periods/day = 30 slots per room per week

| Period | Time | Category |
|--------|------|----------|
| P1 | 07:00 – 09:55 | Morning (before noon) |
| P2 | 10:05 – 12:55 | Morning (before noon) |
| P3 | 13:05 – 15:55 | Afternoon |
| P4 | 16:05 – 18:55 | Afternoon / Evening |
| P5 | 19:05 – 21:55 | Evening |

---

## 🧮 Mathematical Model

### Decision Variable

A single binary variable captures the entire timetable:

```
x[c, s, r, d, p] ∈ {0, 1}
```

`x[c, s, r, d, p] = 1` if and only if class `c` takes course `s` in room `r` on day `d` at period `p`.

> Variables are only created when `cap(r) ≥ size(c)` and `s ∈ Sc`, implicitly encoding constraints C3 and C6 and drastically reducing the search space.

### Constraints

**C1 — No class double-booking** *(S1)*
```
∀c, ∀d, ∀p :   Σ_{s ∈ Sc} Σ_{r ∈ R}  x[c,s,r,d,p]  ≤  1
```

**C2 — Each course scheduled exactly once** *(S2)*
```
∀c, ∀s ∈ Sc :   Σ_{d} Σ_{p} Σ_{r}  x[c,s,r,d,p]  =  1
```

**C3 — Curriculum compliance** *(S3)*  
Encoded implicitly: `x[c,s,r,d,p]` is only instantiated for `s ∈ Sc`.

**C4 — No teacher conflict**
```
∀t, ∀d, ∀p :   Σ_{c} Σ_{s: teacher(s)=t} Σ_{r}  x[c,s,r,d,p]  ≤  1
```

**C5 — No room conflict**
```
∀r, ∀d, ∀p :   Σ_{c} Σ_{s ∈ Sc}  x[c,s,r,d,p]  ≤  1
```

**C6 — Room capacity** *(implicit)*  
`x[c,s,r,d,p]` is only created if `cap(r) ≥ size(c)`.

### Objective Function *(S4)*

```
Maximize  Z = Σ_{c,s,r,d,p}  w_p · x[c,s,r,d,p]

with  w1=5, w2=4, w3=3, w4=2, w5=1   (w1 > w2 > w3 > w4 > w5 > 0)
```

By maximizing `Z`, the solver naturally places the maximum number of sessions in P1 (07:00) and P2 (10:05) before resorting to afternoon slots.

---

## 🏗️ Implementation

### Technology Stack

- **Language:** Python 3
- **Solver:** [Google OR-Tools CP-SAT](https://developers.google.com/optimization/reference/python/sat/python/cp_model)

CP-SAT was chosen for its native support of binary integer programming, efficient constraint propagation, and built-in `AddExactlyOne()` — perfectly matching this model's structure.

### Project Structure

```
time-table-scheduling/
├── timetable_solver.py   # Main solver — model + OR-Tools implementation
├── subjects.json         # Courses, curricula, and lecturer assignments per level
└── rooms.json            # Rooms and amphitheatres with capacities
```

### Input Data

| File | Contents |
|------|----------|
| `subjects.json` | 5 levels × 2 semesters, course codes, names, and assigned lecturers |
| `rooms.json` | 16 rooms/amphitheatres (capacity 36–1 002 seats) across 4 buildings |

**Key data fix applied:** Subjects with no assigned lecturer are given unique internal identifiers per (course, class) pair — preventing false teacher-conflict constraints that would otherwise make the problem artificially infeasible.

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/nguembu/time-table-scheduling.git
cd time-table-scheduling

# 2. Install the dependency
pip install ortools

# 3. Run the solver
python3 timetable_solver.py
```

---

## 📊 Results

| Indicator | Value |
|-----------|-------|
| Solver status | **FEASIBLE** ✅ |
| Total sessions scheduled | **69 / 69** |
| Sessions before noon (P1 + P2) | **65** |
| Morning rate | **94.2 %** |
| Constraint violations | **0** |

The 94.2 % morning rate confirms that the weighted objective function effectively satisfies specification S4.

---

## ⚙️ Model Classification

| Dimension | Classification | Reason |
|-----------|---------------|--------|
| Linear / Non-linear | **Linear** | All constraints and objective are linear combinations of binary variables |
| Static / Dynamic | **Static** | Fixed weekly output; time is an index, not an evolving variable |
| Discrete / Continuous | **Discrete** | All variables are binary; days and periods are finite integer sets |
| Deterministic / Stochastic | **Deterministic** | All parameters (curricula, capacities, teachers) are known with certainty |
| Problem class | **NP-hard (UCTP)** | University Course Timetabling Problem — solved with CP-SAT within a time limit |

---

## 🔭 Possible Extensions

| Current Limitation | Possible Extension |
|--------------------|--------------------|
| Class sizes are estimated | Integrate real enrolment data for exact room allocation |
| Teacher availability not modelled | Add availability constraints: `x[c,s,r,d,p] = 0` if teacher unavailable |
| Labs / practical rooms not distinguished | Add a `room_type` attribute and restrict lab sessions to lab rooms only |
| Static model only | Add real-time rescheduling capability for mid-semester changes |

---

## 📚 References

1. YOUH, Xaveria (2026). *INF 4178: Software Engineering I*. University of Yaoundé I.
2. YOUH, Xaveria (2026). *Introduction to Mathematical Modeling*. University of Yaoundé I.
3. Perron, L. & Furnon, V. (2024). *OR-Tools CP-SAT Solver*. Google LLC. https://developers.google.com/optimization
4. Ajibola, S.O. (2009). *Introduction to Mathematical Modeling*. National University of Nigeria.

---

## 👤 Author

**John Nguembu**  
Department of Computer Science — University of Yaoundé I  
INF 4178 — Software Engineering I | April 2026
