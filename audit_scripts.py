#!/usr/bin/env python3
"""Audit the tutor step scripts ('spoken') against their questions.
Usage:
  python3 audit_scripts.py bank.json report.csv                 # report only
  python3 audit_scripts.py bank.json report.csv --fix bank_clean.json   # also remove flagged scripts
Flagged scripts are removed so the page falls back to the original step text. Nothing else changes.
Checks: (1) colour, object or first-name word in the script that is not in the question
        (2) arithmetic written on the board that is wrong, e.g. 9 - 4 = 6
        (3) the final answer is missing from the last two steps
        (4) leftover LaTeX or odd symbols are counted (the page now cleans these) but not flagged
"""
import json, re, sys, csv
from fractions import Fraction

COLW = 'red|blue|green|yellow|white|black|pink|purple|orange|grey|brown'
OBJW = 'counter|marble|bead|ball|token|button|sweet'
FN = 'Aisha Grace Sofia Joy Ruth Maya Priya Chloe Zara Leah Nina Tara Hannah Olivia Amelia Isla Lily Mia Ella Freya Layla Esme Anika Fatima Amina Dina Rosa Daisy Keira Jade Nia Hana Anya Amara Imani Xena Kira Elsie Poppy Ivy Yasmin Bella Holly Naomi Sana Emily Ayesha Lucy Megan'.split()
MN = 'Idris Isaac Gabriel Arjun Jamal Noah Elijah Kofi Ibrahim Mohammed Yusuf Harry Theo Finn Kwame Felix Ali Callum Carlos Owen Qasim Dev Kai Jamie Sam Leo Max Omar Ravi Tom Ben Luca Hugo Zane Danny Ethan Adam Jacob Samir Tariq Casey Morgan Robin Charlie'.split()
WORDS = re.compile(r'\b(%s|%s)s?\b' % (COLW, OBJW), re.I)
NAMES = re.compile(r'\b(%s)\b' % '|'.join(FN + MN))

def source_text(q):
    parts = [str(q.get(k) or '') for k in ('prompt', 'worked_solution', 'diagram_alt', 'key_idea', 'common_mistake')] + [str(q.get('answer', ''))]
    parts += [str(x) for x in (q.get('steps') or [])]
    parts += [str(x) for x in (q.get('accept') or [])]
    return ' '.join(parts)

def clean(t):
    t = t.replace('\\times', '*').replace('\\div', '/').replace('\u00d7', '*').replace('\u00f7', '/').replace('\u2212', '-')
    t = t.replace('\\cdot', '*').replace('^', '**')
    t = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', t)
    return t.replace(',', '')

TOK = re.compile(r'^[0-9.+\-*/() ]+$')
def val(expr):
    expr = expr.strip()
    if not expr or not TOK.match(expr) or '**' in expr and len(expr) > 12: return None
    if not re.search(r'\d', expr): return None
    try:
        expr = re.sub(r'(\d+\.\d+|\d+)', lambda m: 'F("%s")' % m.group(1), expr)
        return eval(expr, {'F': Fraction, '__builtins__': {}})
    except Exception:
        return None

def arith_errors(board):
    bad = []
    for line in re.split(r'[;\n]', board):
        line = clean(line)
        if line.count('=') < 1: continue
        sides = [s.strip() for s in line.split('=')]
        vals = [val(s) for s in sides]
        known = [(s, v) for s, v in zip(sides, vals) if v is not None]
        if len(known) < 2: continue
        # a number-only side with decimals means it may be rounded
        base = known[0][1]
        for s, v in known[1:]:
            if v == base: continue
            tol = max(abs(float(base)) * 0.006, 0.006)
            if abs(float(v) - float(base)) <= tol and ('.' in s): continue
            bad.append(line.strip()); break
    return bad

def nums(t):
    return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', t.replace(',', ''))]

def check(q):
    why = []
    sp = q['spoken']; src = source_text(q).lower()
    text = ' '.join(x.get('say', '') + ' ' + x.get('board', '') for x in sp)
    qwords = {w.lower().rstrip('s') for w in re.findall(r'\b(?:%s|%s)s?\b' % (COLW, OBJW), src, re.I)}
    for m in WORDS.finditer(text):
        w = m.group(1).lower()
        if w not in qwords and w.rstrip('s') not in qwords:
            why.append('word not in question: ' + w); break
    qnames = set(NAMES.findall(source_text(q)))
    for nm in set(NAMES.findall(text)):
        if nm not in qnames:
            why.append('name not in question: ' + nm); break
    for x in sp:
        e = arith_errors(x.get('board', ''))
        if e: why.append('arithmetic: ' + e[0][:80]); break
    ans = str(q.get('answer', ''))
    tail = ' '.join(x.get('say', '') + ' ' + x.get('board', '') for x in sp[-2:])
    an = nums(ans)
    if an and not all(any(abs(v - a) <= 1e-6 * max(1, abs(a)) for v in nums(tail)) for a in an):
        # allow fractions / words written differently
        if ans.replace(' ', '').lower() not in tail.replace(' ', '').lower():
            why.append('final answer not in last two steps')
    return why

def main():
    src, rep = sys.argv[1], sys.argv[2]
    fix = sys.argv[sys.argv.index('--fix') + 1] if '--fix' in sys.argv else None
    b = json.load(open(src, encoding='utf-8'))
    items = (b['questions'] + b.get('worked_examples', [])) if isinstance(b, dict) else b
    n = flagged = removed = 0; tex = 0
    out = csv.writer(open(rep, 'w', newline='', encoding='utf-8'))
    out.writerow(['id', 'topic', 'reason', 'question', 'script_first_lines'])
    for q in items:
        if not q.get('spoken'): continue
        n += 1
        if any('\\' in (x.get('say', '') + x.get('board', '')) for x in q['spoken']): tex += 1
        why = check(q)
        if why:
            flagged += 1
            out.writerow([q['id'], q.get('topic'), '; '.join(why), q.get('prompt', '')[:140].replace('\n', ' '),
                          ' / '.join(x.get('say', '')[:60] for x in q['spoken'][:2])])
            if fix: q.pop('spoken'); removed += 1
    print(f'{n} scripts checked; {flagged} flagged ({100*flagged/max(n,1):.1f}%); {tex} contain LaTeX (page cleans these)')
    print('report written to', rep)
    if fix:
        json.dump(b, open(fix, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'removed {removed} flagged scripts; clean bank written to {fix}')

if __name__ == '__main__':
    main()
