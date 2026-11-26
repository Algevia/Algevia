import sys,shutil
p=sys.argv[1] if len(sys.argv)>1 else 'learn.html'
s=open(p,encoding='utf-8').read()
if 'hearLesson' in s: sys.exit('Already patched.')
shutil.copy(p,p+'.bak')
def rep(a,b):
    global s
    assert s.count(a)==1,(s.count(a),a[:60]); s=s.replace(a,b)
# 1 button + lesson card
rep('<button class="alt" onclick="workedExample()">Worked Example</button></div><div class="topicIntro" id="topicIntro">Choose a lesson to begin.</div>',
 '<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="alt" onclick="hearLesson()">Hear the lesson</button><button class="alt" onclick="workedExample()">Worked Example</button></div></div><div class="topicIntro" id="topicIntro">Choose a lesson to begin.</div><div id="lessonCard"></div>')
# 2 state + loader
rep('let engine=null, bank=[], examples=[],','let lessons={}, engine=null, bank=[], examples=[],')
rep("  examples=(data.worked_examples||[]).filter(q=>q.skill_id&&q.prompt&&fits(q));",
 "  examples=(data.worked_examples||[]).filter(q=>q.skill_id&&q.prompt&&fits(q));\n  try{const lr=await fetch('algevia_lessons_v1.json');if(lr.ok)lessons=await lr.json();}catch(e){lessons={};}")
# 3 lesson card render
rep("window.workedExample=function(){",
"""function lessonFor(q){return q&&lessons[q.topic]||null;}
function renderLesson(q){
 const L=lessonFor(q),box=el('lessonCard');if(!box)return;
 if(!L){box.innerHTML='';return;}
 const li=a=>'<ul style="margin:4px 0 0 18px;padding:0">'+a.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>';
 const ol=a=>'<ol style="margin:4px 0 0 18px;padding:0">'+a.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ol>';
 box.innerHTML='<div class="topicIntro" style="border-left-color:#0a9b69"><b>The idea</b><br>'+esc(L.concept)+'<div style="margin-top:8px"><b>Rules and formulas</b>'+li(L.rules)+'</div><div style="margin-top:8px"><b>The method</b>'+ol(L.method)+'</div><div style="margin-top:8px"><b>Watch out for</b>'+li(L.mistakes)+'</div></div>';
}
window.hearLesson=function(){
 if(!active)return;const L=lessonFor(active);if(!L)return;
 renderLesson(active);
 const sp=[{speech:L.concept,math:'',why:'',raw:true}];
 sp.push({speech:'Here are the key rules. '+L.rules.join(' '),math:L.rules.join('\\n'),why:'',raw:true});
 sp.push({speech:'The method has '+L.method.length+' steps. '+L.method.map((m,i)=>'Step '+(i+1)+'. '+m).join(' '),math:L.method.map((m,i)=>(i+1)+'. '+m).join('\\n'),why:'',raw:true});
 sp.push({speech:'Two common mistakes. '+L.mistakes.join(' '),math:'',why:'',raw:true});
 runStructuredSteps(sp,'Lesson',true);
};
window.workedExample=function(){""")
rep(" el('topicIntro').textContent=active.area+SEP+active.topic;"," el('topicIntro').textContent=active.area+SEP+active.topic;renderLesson(active);")
# 4 spoken in worked example
rep(""" const list=(q.steps&&q.steps.length?q.steps:String(q.worked_solution).split(/(?<=[.!?])\\s+/)).filter(Boolean);
 const steps=list.map(x=>({speech:x,math:x,why:''}));
 if(q.key_idea)steps.unshift({speech:q.key_idea,math:'',why:''});
 runStructuredSteps(steps,'Worked example',true);""",
""" if(q.spoken&&q.spoken.length){
  const sp=q.spoken.map(x=>({speech:String(x.say||''),math:String(x.board||''),why:'',raw:true}));
  if(q.key_idea)sp.unshift({speech:q.key_idea,math:'',why:'',raw:true});
  if(q.common_mistake)sp.push({speech:'One thing to watch out for. '+q.common_mistake,math:'',why:'',raw:true});
  sp.push({speech:'Now try your own question above. Use the same steps.',math:'',why:'',raw:true});
  runStructuredSteps(sp,'Worked example',true);return;
 }
 const list=(q.steps&&q.steps.length?q.steps:String(q.worked_solution).split(/(?<=[.!?])\\s+/)).filter(Boolean);
 const steps=list.map(x=>({speech:x,math:x,why:''}));
 if(q.key_idea)steps.unshift({speech:q.key_idea,math:'',why:''});
 runStructuredSteps(steps,'Worked example',true);""")
open(p,'w',encoding='utf-8').write(s)
s=open(p,encoding='utf-8').read()
a="examples.filter(q=>q.id!==active.id&&"
if s.count(a)!=1: print("note: skipped same-question guard"); a=None
s=s.replace(a,"examples.filter(q=>q.id!==active.id&&q.prompt!==active.prompt&&") if a else s
open(p,'w',encoding='utf-8').write(s)

print('learn.html patched (backup saved as',p+'.bak)')
