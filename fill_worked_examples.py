#!/usr/bin/env python3
"""Fill lessons that have fewer than 3 worked examples by promoting checked questions.
Usage: python3 fill_worked_examples.py bank_in.json bank_out.json
"""
import json, re, sys, copy, collections
src, dst = sys.argv[1], sys.argv[2]
b = json.load(open(src, encoding='utf-8'))
W = b.setdefault('worked_examples', [])
have = collections.defaultdict(list)
for w in W: have[(w['area'], w['topic'])].append(w)
byt = collections.defaultdict(list)
for q in b['questions']:
    if q.get('proof') or not q.get('answer') or not (q.get('steps') or q.get('worked_solution')): continue
    byt[(q['area'], q['topic'])].append(q)
skel = lambda q: re.sub(r'\d+(\.\d+)?', '#', re.sub(r'\s+', ' ', q['prompt'].lower()))[:60]
added = 0; touched = 0
for key, qs in sorted(byt.items()):
    cur = have.get(key, [])
    if len(cur) >= 3: continue
    want = 4 if len(cur) == 0 else 3
    seen = {skel(w) for w in cur}; used = {w['prompt'] for w in cur}
    qs = sorted(qs, key=lambda q: (q.get('grade') or 5, q['id']))
    grades = sorted({q.get('grade') or 5 for q in qs})
    picks = []
    # spread across grades: take from low, middle, high first
    order = [grades[0], grades[len(grades) // 2], grades[-1]] + grades
    for g in order:
        for q in qs:
            if (q.get('grade') or 5) != g or q in picks: continue
            if skel(q) in seen or q['prompt'] in used: continue
            picks.append(q); seen.add(skel(q)); used.add(q['prompt']); break
        if len(cur) + len(picks) >= want: break
    if picks: touched += 1
    for q in picks:
        w = copy.deepcopy(q); w['id'] = 'WX-' + q['id']; w['mode'] = 'worked_example'
        if not w.get('key_idea'): w['key_idea'] = ''
        W.append(w); added += 1
json.dump(b, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
after = collections.Counter((w['area'], w['topic']) for w in W)
print('added', added, 'worked examples across', touched, 'lessons; total now', len(W))
print('lessons still under 3:', sum(1 for k in byt if after[k] < 3))
