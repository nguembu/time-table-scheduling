"""
INF 4178 - Génie Logiciel I | TP — Projet 1
Génération automatique d'emploi du temps — Modèle mathématique + OR-Tools CP-SAT
Université de Yaoundé I, Département Informatique — Avril 2026
"""

import json
from ortools.sat.python import cp_model

# ── Chargement des données ──────────────────────────────────────────────────
with open("subjects.json") as f:
    subjects_data = json.load(f)
with open("rooms.json") as f:
    rooms_data = json.load(f)

rooms = rooms_data["Informatique"]
ROOMS = [r["num"] for r in rooms]
room_capacity = {r["num"]: int(r["capacite"]) for r in rooms}

niveaux = subjects_data["niveau"]
level_sizes = {"1": 300, "2": 200, "3": 150, "4": 80, "5": 40}

# ── Construction des classes et matières ───────────────────────────────────
CLASSES = []
class_subjects = {}
class_size = {}

for niveau_id, semestres in niveaux.items():
    for sem_id, sem_data in semestres.items():
        subj_list = sem_data.get("subjects", [])
        if not subj_list:
            continue
        cname = f"L{niveau_id}_{sem_id}"
        seen = set()
        codes = []
        for s in subj_list:
            code = s.get("code")
            if not code:
                continue
            name = s.get("name", "")
            # Accepter aussi les matières dont le nom est une liste (données imparfaites)
            if code not in seen:
                seen.add(code)
                codes.append(code)
        if not codes:
            continue
        CLASSES.append(cname)
        class_subjects[cname] = codes
        class_size[cname] = level_sizes.get(niveau_id, 100)

# ── Dictionnaire global des matières ───────────────────────────────────────
# CORRECTION CLÉ : chaque matière sans enseignant reçoit un identifiant unique
# (code_classe) pour éviter de créer un faux conflit "UNKNOWN" global.
ALL_SUBJECTS = {}
_subject_class_map = {}  # Pour construire des teacher_keys contextuels

for niveau_id, semestres in niveaux.items():
    for sem_id, sem_data in semestres.items():
        cname = f"L{niveau_id}_{sem_id}"
        for s in sem_data.get("subjects", []):
            code = s.get("code")
            if not code:
                continue
            name = s.get("name", code)
            if not isinstance(name, str):
                name = code  # Fallback si le nom est une liste/autre type
            lecturers = s.get("Course Lecturer", ["", ""])
            parts = [x.strip() for x in lecturers if isinstance(x, str) and x.strip()]
            if parts:
                teacher_key = "_".join(parts)
            else:
                # Pas d'enseignant renseigné → teacher unique par (code, classe)
                # Cela empêche les faux conflits entre matières sans enseignant
                teacher_key = f"__NO_TEACHER_{code}_{cname}__"
            ALL_SUBJECTS[code] = {"name": name, "teacher": teacher_key}

TEACHERS = list(set(v["teacher"] for v in ALL_SUBJECTS.values()))

# ── Constantes de temps ────────────────────────────────────────────────────
DAYS    = list(range(6))
PERIODS = list(range(5))
DAY_NAMES = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
PERIOD_NAMES = [
    "P1  07:00–09:55",
    "P2  10:05–12:55",
    "P3  13:05–15:55",
    "P4  16:05–18:55",
    "P5  19:05–21:55",
]
# w_p : poids croissant pour maximiser les créneaux matinaux
# Conformément à l'énoncé : w5 > w4 > ... > w1 > 0
WEIGHTS = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1}

# ── Affichage du contexte ──────────────────────────────────────────────────
print("=" * 70)
print("GÉNÉRATEUR D'EMPLOI DU TEMPS — Dép. Informatique, Univ. Yaoundé I")
print("=" * 70)
real_teachers = [t for t in TEACHERS if not t.startswith("__NO_TEACHER_")]
print(f"Classes     : {len(CLASSES)}")
print(f"Séances     : {sum(len(v) for v in class_subjects.values())} (une par matière/classe)")
print(f"Salles      : {len(ROOMS)}")
print(f"Enseignants : {len(real_teachers)} (+ matières sans enseignant)")
print(f"Jours       : {len(DAYS)},  Périodes/jour : {len(PERIODS)}")
print(f"Créneaux totaux disponibles : {len(DAYS)*len(PERIODS)} par classe")
print()

# ── Modèle CP-SAT ──────────────────────────────────────────────────────────
model = cp_model.CpModel()

# Variable de décision : x[c, s, r, d, p] = 1 si la classe c suit la matière s
# dans la salle r, le jour d à la période p.
x = {}
for c in CLASSES:
    for s in class_subjects.get(c, []):
        for r in ROOMS:
            if room_capacity[r] >= class_size[c]:   # Salle suffisamment grande
                for d in DAYS:
                    for p in PERIODS:
                        x[c, s, r, d, p] = model.NewBoolVar(f"x_{c}_{s}_{r}_{d}_{p}")

# ── Contrainte C2 : chaque matière planifiée exactement une fois par semaine ──
for c in CLASSES:
    for s in class_subjects.get(c, []):
        slots = [
            x[c, s, r, d, p]
            for r in ROOMS for d in DAYS for p in PERIODS
            if (c, s, r, d, p) in x
        ]
        if slots:
            model.AddExactlyOne(slots)
        else:
            print(f"  ⚠ Aucune salle éligible pour {c}/{s} (effectif={class_size[c]})")

# ── Contrainte C1 : pas de double occupation d'une classe (même créneau) ───
for c in CLASSES:
    for d in DAYS:
        for p in PERIODS:
            concurrent = [
                x[c, s, r, d, p]
                for s in class_subjects.get(c, [])
                for r in ROOMS
                if (c, s, r, d, p) in x
            ]
            if concurrent:
                model.Add(sum(concurrent) <= 1)

# ── Contrainte C4 : pas de conflit enseignant ──────────────────────────────
# On ne construit les contraintes QUE pour les vrais enseignants (pas les NO_TEACHER)
teacher_subjects = {}
for c in CLASSES:
    for s in class_subjects.get(c, []):
        if s in ALL_SUBJECTS:
            t = ALL_SUBJECTS[s]["teacher"]
            if not t.startswith("__NO_TEACHER_"):  # Ignorer les pseudo-teachers
                teacher_subjects.setdefault(t, []).append((c, s))

for t, pairs in teacher_subjects.items():
    for d in DAYS:
        for p in PERIODS:
            teaching_now = [
                x[c, s, r, d, p]
                for (c, s) in pairs
                for r in ROOMS
                if (c, s, r, d, p) in x
            ]
            if teaching_now:
                model.Add(sum(teaching_now) <= 1)

# ── Contrainte C5 : pas de conflit de salle ───────────────────────────────
for r in ROOMS:
    for d in DAYS:
        for p in PERIODS:
            room_use = [
                x[c, s, r, d, p]
                for c in CLASSES
                for s in class_subjects.get(c, [])
                if (c, s, r, d, p) in x
            ]
            if room_use:
                model.Add(sum(room_use) <= 1)

# ── Objectif : maximiser les créneaux matinaux (p=0 et p=1 avant midi) ────
# Conformément à l'énoncé : w_p tel que w5 > w4 > w3 > w2 > w1 > 0
# Note : p=0 (07:00) et p=1 (10:05) sont avant midi → poids les plus élevés
objective_terms = [WEIGHTS[p] * var for (c, s, r, d, p), var in x.items()]
model.Maximize(sum(objective_terms))

# ── Résolution ────────────────────────────────────────────────────────────
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 120.0
solver.parameters.log_search_progress = False
solver.parameters.num_search_workers = 4   # Parallélisme pour accélérer

print("Résolution en cours… (max 120 secondes)")
status = solver.Solve(model)
print(f"Statut     : {solver.StatusName(status)}")

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print(f"Score (objectif) : {solver.ObjectiveValue():.0f}")
    print()

    # ── Affichage de l'emploi du temps ─────────────────────────────────────
    print("=" * 70)
    print("EMPLOI DU TEMPS GÉNÉRÉ")
    print("=" * 70)

    schedule = {c: [] for c in CLASSES}
    for (c, s, r, d, p), var in x.items():
        if solver.Value(var) == 1:
            schedule[c].append((d, p, s, r))

    for c in CLASSES:
        entries = sorted(schedule[c], key=lambda t: (t[0], t[1]))
        if not entries:
            continue
        print(f"\n── Classe : {c}  (effectif ≈ {class_size[c]} étudiants) ──")
        print(f"  {'Jour':<12} {'Période':<20} {'Code':<12} {'Salle':<8}  Intitulé")
        print(f"  {'-'*70}")
        for d, p, s, r in entries:
            subj_name = ALL_SUBJECTS.get(s, {}).get("name", s)
            if not isinstance(subj_name, str):
                subj_name = s
            label = (subj_name[:34] + "…") if len(subj_name) > 35 else subj_name
            print(f"  {DAY_NAMES[d]:<12} {PERIOD_NAMES[p]:<20} {s:<12} {r:<8}  {label}")

    # ── Statistiques ────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("STATISTIQUES")
    print("=" * 70)
    total   = sum(1 for (c, s, r, d, p), var in x.items() if solver.Value(var) == 1)
    morning = sum(1 for (c, s, r, d, p), var in x.items() if solver.Value(var) == 1 and p in (0, 1))
    print(f"Total séances planifiées : {total}")
    print(f"Séances avant midi (P1+P2) : {morning}")
    print(f"Taux matinal             : {morning / max(total, 1) * 100:.1f}%")

    # Vérification des conflits enseignants
    print()
    print("Vérification des contraintes :")
    teacher_slot = {}
    class_slot   = {}
    room_slot    = {}
    conflicts    = 0
    for (c, s, r, d, p), var in x.items():
        if solver.Value(var) == 1:
            t = ALL_SUBJECTS.get(s, {}).get("teacher", "")
            key_t = (t, d, p)
            key_c = (c, d, p)
            key_r = (r, d, p)
            if not t.startswith("__NO_TEACHER_"):
                if key_t in teacher_slot:
                    print(f"  ❌ Conflit enseignant {t} : {teacher_slot[key_t]} et {(c,s)}")
                    conflicts += 1
                teacher_slot[key_t] = (c, s)
            if key_c in class_slot:
                print(f"  ❌ Conflit classe {c} : {class_slot[key_c]} et {s}")
                conflicts += 1
            class_slot[key_c] = s
            if key_r in room_slot:
                print(f"  ❌ Conflit salle {r} : {room_slot[key_r]} et {(c,s)}")
                conflicts += 1
            room_slot[key_r] = (c, s)

    if conflicts == 0:
        print("  ✅ Aucun conflit détecté — toutes les contraintes sont satisfaites.")

else:
    print("❌ Aucune solution trouvée.")
    print("   Vérifiez les données ou augmentez le temps alloué.")
