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
OBJW = 'counter|marble|bead|ball|token|sweet'
FN = 'Aisha Grace Sofia Joy Ruth Maya Priya Chloe Zara Leah Nina Tara Hannah Olivia Amelia Isla Lily Mia Ella Freya Layla Esme Anika Fatima Amina Dina Rosa Daisy Keira Jade Nia Hana Anya Amara Imani Xena Kira Elsie Poppy Ivy Yasmin Bella Holly Naomi Sana Emily Ayesha Lucy Megan'.split()
MN = 'Idris Isaac Gabriel Arjun Jamal Noah Elijah Kofi Ibrahim Mohammed Yusuf Harry Theo Finn Kwame Felix Ali Callum Carlos Owen Qasim Dev Kai Jamie Sam Leo Omar Ravi Tom Ben Luca Hugo Zane Danny Ethan Adam Jacob Samir Tariq Casey Morgan Robin Charlie'.split()
WORDS = re.compile(r'\b(%s|%s)s?\b' % (COLW, OBJW), re.I)
NAMES = re.compile(r'\b(%s)\b' % '|'.join(FN + MN))

def source_text(q):
    parts = [str(q.get(k) or '') for k in ('prompt', 'worked_solution', 'diagram_alt', 'key_idea', 'common_mistake')] + [str(q.get('answer', ''))]
    parts += [str(x) for x in (q.get('steps') or [])]
    parts += [str(x) for x in (q.get('accept') or [])]
    return ' '.join(parts)

DIV = '\u00a7'
def clean(t):
    t = re.sub(r'\s*(?:\\div|\u00f7)\s*', DIV, t)
    t = t.replace('\\times', '*').replace('\u00d7', '*').replace('\u2212', '-')
    t = t.replace('\\cdot', '*').replace('^', '**')
    t = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', t)
    return t.replace(',', '')

TOK = re.compile(r'^[0-9.+\-*/() ]+$')
def val1(expr):
    expr = expr.strip()
    if not expr or not TOK.match(expr) or not re.search(r'\d', expr): return None
    if '**' in expr and len(expr) > 12: return None
    try:
        e = re.sub(r'(\d+\.\d+|\d+)', lambda m: 'F("%s")' % m.group(1), expr)
        return eval(e, {'F': Fraction, '__builtins__': {}})
    except Exception:
        return None

def val(expr):
    if DIV in expr and ' / ' in expr and '(' not in expr:
        vs = [val(p) for p in expr.split(' / ')]
        if any(v is None for v in vs) or any(v == 0 for v in vs[1:]): return None
        r = vs[0]
        for v in vs[1:]: r = r / v
        return r
    if DIV in expr:
        if '(' in expr: return val1(re.sub(r'(\([^()]*\)/\([^()]*\))', r'(\1)', expr).replace(DIV, '/'))
        parts = expr.split(DIV)
        vs = [val1(p) for p in parts]
        if any(v is None for v in vs): return None
        r = vs[0]
        for v in vs[1:]:
            if v == 0: return None
            r = r / v
        return r
    # long mixed chains like 16*16/14*16 are ambiguous written flat: skip
    if ' / ' in expr and '*' in expr and expr.count('*') + expr.count('/') >= 3 and '(' not in expr: return None
    return val1(expr)

def dp(t):
    m = re.search(r'\.(\d+)\s*$', t.strip())
    return len(m.group(1)) if m else 0

def same(a, b, rhs_text='', lhs_text=''):
    if a is None or b is None: return True
    if a == b: return True
    fa, fb = float(a), float(b)
    if abs(fa - fb) <= 1e-9 * max(1, abs(fa)): return True
    # standard form: same digits, different power of ten (e.g. 0.00073 = 7.3 x 10^-4)
    if fa != 0 and fb != 0:
        import math
        r = abs(fa / fb); l = math.log10(r)
        if abs(l - round(l)) < 1e-9 and ('10' in rhs_text or '10' in lhs_text or True) and re.fullmatch(r'[\d.]+', rhs_text.strip() or 'x'):
            if abs(round(l)) >= 1: return True
    if '.' in rhs_text or '.' in lhs_text or abs(fa) >= 1000:
        tol = 0.75 * 10 ** (-dp(rhs_text)) + 0.002 * abs(fb)
        if abs(fa - fb) <= tol: return True
    return False

def eq_ok(parts):
    if len(parts) == 2: return same(val(parts[0]), val(parts[1]), parts[1], parts[0])
    # chain a = b = c ... or several equations written on one line
    vs = [val(p) for p in parts]
    if all(same(vs[0], v, p, parts[0]) for v, p in zip(vs[1:], parts[1:])): return True
    mid = parts[1]
    for m in re.finditer(r'\s+', mid):
        r, l = mid[:m.start()], mid[m.end():]
        if same(val(parts[0]), val(r), r, parts[0]) and eq_ok([l] + parts[2:]): return True
    return False

SEP = re.compile(r'\\quad|\\\\|;|\n|\\Rightarrow|=>|\s{2,}')
ANDOR = re.compile(r'\b(?:and|or)\b')
def arith_errors(board):
    bad = []
    segs = []
    for sg in SEP.split(clean(board)):
        if re.search(r'=.*\b(?:and|or)\b.*=', sg): segs += ANDOR.split(sg)
        else: segs.append(sg)
    for seg in segs:
        if '=' not in seg: continue
        parts = [p.strip() for p in seg.split('=')]
        if len(parts) < 2 or any(p == '' for p in parts): continue
        if re.fullmatch(r'[a-zA-Z](?:_\d)?', parts[0]): parts = parts[1:]   # 'x = 515/900 = ...' -> check the numbers
        if len(parts) < 2 or any(re.search(r'[A-Za-z_\\?]', p) for p in parts): continue   # algebra, labels, blanks
        if re.fullmatch(r'\(\d+\)', parts[0]): continue                                  # table labels like (11)=2
        try:
            if not eq_ok(parts): bad.append(seg.strip())
        except Exception:
            pass
    return bad

def nums(t):
    return [abs(float(x)) for x in re.findall(r'-?\d+(?:\.\d+)?', t.replace(',', '').replace('\u2212', '-'))]

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
    plain = re.fullmatch(r'[-\u2212\s\d.,%£$]+(?:\s*[a-zA-Z²³/]{0,6})?', ans.strip()) is not None and '/' not in ans
    if an and plain and not all(any(abs(v - a) <= 1e-6 * max(1, abs(a)) for v in nums(tail)) for a in an):
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
