/* Algevia answer marking v1.
   mark(input, q) -> true/false. q is a question from algevia_gcse_question_bank_v1.json.
   Accepts equivalent forms: numbers with units / currency / % / degrees, fractions, mixed numbers,
   standard form, algebra in any equivalent form (checked by evaluating at sample points), coordinates,
   lists, solution sets in any order. Words must match one of the accepted forms (case and spaces ignored). */
(function (global) {
'use strict';
var SUP = {'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9','⁻':'-'};
function supToCaret(s) { return String(s).replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+/g, function (m) { return '^' + m.split('').map(function (c) { return SUP[c]; }).join(''); }); }
function base(s) {
  return supToCaret(String(s)).replace(/[−–—]/g, '-').replace(/\*\*/g, '^').replace(/[×·]/g, '*').replace(/÷/g, '/').replace(/ /g, ' ').trim();
}
function norm(s) { return base(s).toLowerCase().replace(/degrees?/g, '°').replace(/\s+/g, '').replace(/[.,;:]+$/, ''); }
var UNIT = /^(cm|mm|m|km|kg|g|mg|l|ml|s|sec|seconds?|min|minutes?|h|hr|hours?|mph|km\/h|m\/s|km\/hr|p|pence|pounds?|metres?|meters?|centimetres?|millimetres?|kilometres?|litres?|grams?|kilograms?|degrees?|people|students|marks|units)?(\^?[23])?(\/(h|s|min|hr|hour|second|minute))?$/i;

function parseNumber(s) {
  var t = base(s).toLowerCase().replace(/^about\s+|^approximately\s+|^approx\.?\s+|^≈\s*/, '');
  t = t.replace(/^[a-z]{1,2}\s*=\s*/, '');           // "x = 5"
  t = t.replace(/[£$€]/g, '').replace(/%/g, '').replace(/°/g, '').replace(/degrees?/g, '').trim();
  if (/^-?\d{1,3}(,\d{3})+(\.\d+)?/.test(t)) t = t.replace(/,/g, '');
  if (/^-?\d{1,3}( \d{3})+(\.\d+)?(?!\d)/.test(t)) { var m0 = t.match(/^-?\d{1,3}( \d{3})+(\.\d+)?/); t = t.replace(m0[0], m0[0].replace(/ /g, '')); }
  var m;
  if ((m = t.match(/^(-?[\d.]+)\s*[x*]\s*10\^(-?\d+)$/))) return parseFloat(m[1]) * Math.pow(10, parseInt(m[2], 10));
  if ((m = t.match(/^(-?\d+)\s+(\d+)\s*\/\s*(\d+)$/))) { var w = parseInt(m[1], 10), n = parseInt(m[2], 10), d = parseInt(m[3], 10); return d ? (w < 0 || m[1][0] === '-' ? -1 : 1) * (Math.abs(w) + n / d) : NaN; }
  if ((m = t.match(/^(-?\d+)\s*\/\s*(\d+)$/))) return parseInt(m[2], 10) ? parseInt(m[1], 10) / parseInt(m[2], 10) : NaN;
  if ((m = t.match(/^(-?\d*\.?\d+)\s*([a-z][a-z0-9^\/²³ .]*)$/)) && UNIT.test(m[2].replace(/\s+/g, ''))) return parseFloat(m[1]);
  if (/^-?(\d+\.?\d*|\.\d+)(e-?\d+)?$/.test(t)) return parseFloat(t);
  return NaN;
}
function gcd(a, b) { a = Math.abs(a); b = Math.abs(b); while (b) { var t = b; b = a % b; a = t; } return a; }
function lowestTerms(s) {
  var t = base(s).toLowerCase().replace(/[£$€%°]/g, '').trim(), m;
  if ((m = t.match(/(-?\d+)\s+(\d+)\s*\/\s*(\d+)/))) return gcd(+m[2], +m[3]) === 1 && +m[2] < +m[3];
  if ((m = t.match(/(-?\d+)\s*\/\s*(\d+)/))) return gcd(+m[1], +m[2]) === 1;
  return true;
}

/* ---------- small expression evaluator (+ - * / ^, brackets, sqrt/√, pi/π, implicit multiplication) ---------- */
function tokenize(src) {
  var s = base(src).replace(/√/g, ' sqrt ').replace(/π/g, ' pi ').replace(/\^\s*\(/g, '^(');
  var out = [], i = 0, m;
  while (i < s.length) {
    var c = s[i];
    if (c === ' ') { i++; continue; }
    if ((m = s.slice(i).match(/^(\d+\.?\d*|\.\d+)/))) { out.push({t: 'n', v: parseFloat(m[1])}); i += m[1].length; continue; }
    if ((m = s.slice(i).match(/^(sqrt|pi)(?![a-z])/i))) { out.push({t: 'f', v: m[1].toLowerCase()}); i += m[1].length; continue; }
    if (/[a-zA-Z]/.test(c)) { out.push({t: 'v', v: c}); i++; continue; }
    if ('+-*/^()'.indexOf(c) >= 0) { out.push({t: 'o', v: c}); i++; continue; }
    return null;
  }
  return out;
}
function parseExpr(tokens) {
  var p = 0;
  function peek() { return tokens[p]; }
  function startsAtom(t) { return t && (t.t === 'n' || t.t === 'v' || t.t === 'f' || (t.t === 'o' && t.v === '(')); }
  function expr() {
    var left = term();
    while (peek() && peek().t === 'o' && (peek().v === '+' || peek().v === '-')) { var op = tokens[p++].v; var right = term(); left = {k: op, a: left, b: right}; }
    return left;
  }
  function term() {
    var left = unary();
    while (peek()) {
      var t = peek();
      if (t.t === 'o' && (t.v === '*' || t.v === '/')) { p++; var r = unary(); left = {k: t.v, a: left, b: r}; }
      else if (startsAtom(t)) { var r2 = unary(); left = {k: '*', a: left, b: r2}; }
      else break;
    }
    return left;
  }
  function unary() {
    var t = peek();
    if (t && t.t === 'o' && t.v === '-') { p++; return {k: 'neg', a: unary()}; }
    if (t && t.t === 'o' && t.v === '+') { p++; return unary(); }
    return power();
  }
  function power() {
    var b = atom();
    if (peek() && peek().t === 'o' && peek().v === '^') { p++; var e = unary(); return {k: '^', a: b, b: e}; }
    return b;
  }
  function atom() {
    var t = tokens[p++];
    if (!t) throw 0;
    if (t.t === 'n') return {k: 'num', v: t.v};
    if (t.t === 'v') return {k: 'var', v: t.v};
    if (t.t === 'f') {
      if (t.v === 'pi') return {k: 'num', v: Math.PI};
      var arg = atom(); // sqrt applies to the next atom (number, variable or bracket)
      if (peek() && peek().t === 'o' && peek().v === '^') { p++; var ee = unary(); arg = {k: '^', a: arg, b: ee}; }
      return {k: 'sqrt', a: arg};
    }
    if (t.t === 'o' && t.v === '(') { var e = expr(); var c = tokens[p++]; if (!c || c.v !== ')') throw 0; return e; }
    throw 0;
  }
  try { var tree = expr(); return p === tokens.length ? tree : null; } catch (e) { return null; }
}
function evalTree(n, env) {
  switch (n.k) {
    case 'num': return n.v;
    case 'var': if (!(n.v in env)) throw 1; return env[n.v];
    case '+': return evalTree(n.a, env) + evalTree(n.b, env);
    case '-': return evalTree(n.a, env) - evalTree(n.b, env);
    case '*': return evalTree(n.a, env) * evalTree(n.b, env);
    case '/': return evalTree(n.a, env) / evalTree(n.b, env);
    case 'neg': return -evalTree(n.a, env);
    case '^': return Math.pow(evalTree(n.a, env), evalTree(n.b, env));
    case 'sqrt': return Math.sqrt(evalTree(n.a, env));
  }
  throw 1;
}
function stripLhs(s) {
  var t = base(s);
  var m = t.match(/^\s*([a-zA-Z]{1,2}(\^-1)?(\([a-z]\))?)\s*=(?!.*=)/);
  return m ? t.slice(m[0].length) : t;
}
function compileExpr(s) {
  var tk = tokenize(stripLhs(s));
  return tk && tk.length ? parseExpr(tk) : null;
}
function close(a, b) { return isFinite(a) && isFinite(b) && Math.abs(a - b) <= 1e-6 * Math.max(1, Math.abs(b)); }
function checkSamples(tree, nc) {
  try {
    for (var i = 0; i < nc.samples.length; i++) {
      var s = nc.samples[i], env = {};
      nc.variables.forEach(function (v) { env[v] = s[v]; });
      if (!close(evalTree(tree, env), s.value)) return false;
    }
    return true;
  } catch (e) { return false; }
}
function varsOf(n, set) {
  if (n.k === 'var') set[n.v] = 1;
  if (n.a) varsOf(n.a, set);
  if (n.b) varsOf(n.b, set);
  return set;
}
function treeEquiv(a, b) {
  var vs = Object.keys(varsOf(b, varsOf(a, {})));
  var good = 0;
  for (var k = 0; k < 8; k++) {
    var env = {};
    vs.forEach(function (v, i) { env[v] = 2.3 + 1.7 * ((i * 5 + k * 3) % 7) + k * 0.37 + i; });
    var x, y;
    try { x = evalTree(a, env); y = evalTree(b, env); } catch (e) { return false; }
    if (!isFinite(y)) continue;
    if (!close(x, y)) return false;
    good++;
  }
  return good >= 2;
}
function looksMathematical(s) { return /[0-9π√^]/.test(base(s)) && !/[a-z]{3,}/i.test(base(s).replace(/sqrt|pi/gi, '')); }

/* ---------- numbers inside answers ---------- */
function numbersIn(s) {
  var t = base(s).toLowerCase().replace(/[£$€%°]/g, ' ');
  var out = [], re = /(-?\d+\s*\/\s*\d+|-?\d*\.?\d+)/g, m;
  while ((m = re.exec(t))) {
    var v = m[1].replace(/\s+/g, '');
    if (v.indexOf('/') > 0) { var p = v.split('/'); out.push(parseFloat(p[0]) / parseFloat(p[1])); } else out.push(parseFloat(v));
  }
  return out;
}
function segments(s) {
  return base(s).toLowerCase().split(/\bor\b|\band\b|;/).map(function (x) { return numbersIn(x); }).filter(function (a) { return a.length; });
}
function sameArr(a, b) { if (a.length !== b.length) return false; for (var i = 0; i < a.length; i++) if (!close(a[i], b[i])) return false; return true; }
function sameSegs(a, b) {
  if (a.length !== b.length) return false;
  var used = [];
  return a.every(function (sa) { for (var i = 0; i < b.length; i++) if (!used[i] && sameArr(sa, b[i])) { used[i] = 1; return true; } return false; });
}
function flat(segs) { return [].concat.apply([], segs).sort(function (x, y) { return x - y; }); }

function ineq(s) {
  var t = base(s).toLowerCase().replace(/≥|⩾/g, '>=').replace(/≤|⩽/g, '<=').replace(/\s+/g, '');
  var m = t.match(/^([a-z])(<=|>=|<|>)(-?[\d./]+)$/);
  if (m) return m[1] + m[2] + parseNumber(m[3]);
  m = t.match(/^(-?[\d./]+)(<=|>=|<|>)([a-z])$/);
  if (m) { var f = {'<': '>', '>': '<', '<=': '>=', '>=': '<='}[m[2]]; return m[3] + f + parseNumber(m[1]); }
  m = t.match(/^(-?[\d./]+)(<=|<)([a-z])(<=|<)(-?[\d./]+)$/);
  if (m) return m[1 + 0] + m[2] + m[3] + m[4] + m[5];
  return null;
}
function stripUnits(s) { return norm(s).replace(/(cm|mm|km|kg|ml|mph|m)?(\^[23])?$/, ''); }

function mark(input, q) {
  var raw = String(input == null ? '' : input).trim();
  if (!raw) return false;
  var accepts = [q.answer].concat(q.accept || []);
  var ni = norm(raw);
  for (var i = 0; i < accepts.length; i++) if (norm(accepts[i]) === ni) return true;
  var kind = q.answer_kind, val = q.answer_value;
  if (kind === 'number' || kind === 'money' || kind === 'fraction') {
    var x = parseNumber(raw);
    if (isNaN(x)) return false;
    var target = (typeof val === 'number') ? val : parseNumber(q.answer);
    if (isNaN(target)) return false;
    var tol = (q.answer_tolerance != null) ? q.answer_tolerance : Math.max(1e-9, 1e-9 * Math.abs(target));
    if (Math.abs(x - target) > tol + 1e-12) return false;
    if (kind === 'fraction' && !lowestTerms(raw)) return false;
    return true;
  }
  if (kind === 'coordinates' || kind === 'list') {
    for (var j = 0; j < accepts.length; j++) { var a = numbersIn(accepts[j]), b = numbersIn(raw); if (a.length && sameArr(a, b)) return true; }
    return false;
  }
  if (kind === 'set') {
    for (var k = 0; k < accepts.length; k++) {
      var sa = segments(accepts[k]), sb = segments(raw);
      if (!sa.length || !sb.length) continue;
      if (sameSegs(sa, sb)) return true;
      if (!/√/.test(accepts[k]) && sameArr(flat(sa), flat(sb))) return true;
    }
    return false;
  }
  if (kind === 'expression') {
    var tree = compileExpr(raw);
    if (!tree) return false;
    if (q.numeric_check && q.numeric_check.samples) {
      var vs = varsOf(tree, {}), allowed = {};
      q.numeric_check.variables.forEach(function (v) { allowed[v] = 1; });
      if (Object.keys(vs).some(function (v) { return !allowed[v]; })) return false;
      return checkSamples(tree, q.numeric_check);
    }
    var et = compileExpr(q.answer);
    return !!et && treeEquiv(tree, et);
  }
  // inequalities: x>3, 3<x, x ≥ 3 ...
  var ia = ineq(q.answer), ib = ineq(raw);
  if (ia) return !!ib && ia === ib;
  // text answers
  var ui = stripUnits(raw);
  for (var m = 0; m < accepts.length; m++) if (stripUnits(accepts[m]) === ui) return true;
  var d = norm(q.answer);
  if ((d === 'yes' || d === 'no') && new RegExp('^' + d + '(?![a-z])').test(ni)) return true;
  var pk = d.match(/^pack([ab])$/); if (pk && (ni === pk[1] || ni === 'pack' + pk[1])) return true;
  if (looksMathematical(q.answer) && looksMathematical(raw)) {
    var ta = compileExpr(raw), tb = compileExpr(q.answer);
    if (ta && tb && treeEquiv(ta, tb)) return true;
  }
  // ratios such as 1 : 3.5
  if (/^\d+(\.\d+)?:\d+(\.\d+)?/.test(d)) {
    var na = numbersIn(q.answer), nb = numbersIn(raw);
    if (na.length === nb.length && /:/.test(raw) && sameArr(na, nb)) return true;
  }
  return false;
}
global.AlgeviaMarking = {mark: mark, parseNumber: parseNumber};
if (typeof module !== 'undefined') module.exports = global.AlgeviaMarking;
})(typeof window !== 'undefined' ? window : globalThis);
