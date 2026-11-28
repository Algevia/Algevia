import sys,shutil
p=sys.argv[1] if len(sys.argv)>1 else 'learn.html'
s=open(p,encoding='utf-8').read()
if 'texClean' in s: sys.exit('Already patched.')
shutil.copy(p,p+'.bak3')
def rep(a,b):
    global s
    assert s.count(a)==1,('not found',a[:70]); s=s.replace(a,b)
# 1. clean LaTeX leftovers in scripts, speech vs board
rep("function vary(q){",
r"""function texClean(t,speech){
 if(typeof t!=='string')return t;
 t=t.replace(/\\text\{([^{}]*)\}/g,'$1').replace(/\\frac\{([^{}]*)\}\{([^{}]*)\}/g,'$1/$2').replace(/\\sqrt\{([^{}]*)\}/g,'√($1)')
  .replace(/\\left|\\right/g,'').replace(/\\[()\[\]]/g,'').replace(/\\circ/g,'°').replace(/\\theta/g,'θ').replace(/\\pi/g,'π')
  .replace(/\\leq?\b/g,'≤').replace(/\\geq?\b/g,'≥').replace(/\\neq\b/g,'≠').replace(/\\pm\b/g,'±').replace(/\\cdot\b/g,'×');
 t=speech?t.replace(/\\times\b/g,' times ').replace(/\\div\b/g,' divided by ').replace(/\s{2,}/g,' ')
         :t.replace(/\\times\b/g,'×').replace(/\\div\b/g,'÷');
 return t.replace(/\\([a-zA-Z]+)/g,'$1');
}
function cleanSpoken(a){return (a||[]).map(x=>({say:texClean(String(x.say||''),true),board:texClean(String(x.board||''),false)}));}
function vary(q){""")
# 2. the colour/name/object swap must also apply to the tutor script
rep(" if(Array.isArray(o.mark_scheme))o.mark_scheme=",
    " if(Array.isArray(o.spoken))o.spoken=o.spoken.map(x=>({say:fin(tag(x.say)),board:fin(tag(x.board))}));\n if(Array.isArray(o.mark_scheme))o.mark_scheme=")
# 3. use cleaned scripts
rep("const sp=active.spoken.map(x=>({speech:String(x.say||''),math:String(x.board||''),why:'',raw:true}));",
    "const sp=cleanSpoken(active.spoken).map(x=>({speech:x.say,math:x.board,why:'',raw:true}));")
rep("const sp=q.spoken.map(x=>({speech:String(x.say||''),math:String(x.board||''),why:'',raw:true}));",
    "const sp=cleanSpoken(q.spoken).map(x=>({speech:x.say,math:x.board,why:'',raw:true}));")
open(p,'w',encoding='utf-8').write(s); print('learn.html updated (backup',p+'.bak3)')
