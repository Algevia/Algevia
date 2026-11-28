import sys,shutil
p=sys.argv[1] if len(sys.argv)>1 else 'learn.html'
s=open(p,encoding='utf-8').read()
if 'selTopic' in s: sys.exit('Already patched.')
shutil.copy(p,p+'.bak2')
def rep(a,b):
    global s
    assert s.count(a)==1,('not found',a[:70]); s=s.replace(a,b)
rep("function lessonFor(q){return q&&lessons[q.topic]||null;}",
 "function selTopic(q){let v='';try{v=el('skill').value||''}catch(e){}return v||(q&&q.topic)||'';}\nfunction selArea(q){let v='';try{v=el('skill').value?el('topic').value:''}catch(e){}return v||(q&&q.area)||'';}\nfunction lessonFor(q){return q&&lessons[selTopic(q)]||null;}")
rep(" el('topicIntro').textContent=active.area+SEP+active.topic;renderLesson(active);",
    " el('topicIntro').textContent=selArea(active)+SEP+selTopic(active);renderLesson(active);")
rep(" const me=lessonKey(active),gd=",
    " const me=selArea(active)+'|'+selTopic(active),gd=")
open(p,'w',encoding='utf-8').write(s); print('learn.html updated (backup',p+'.bak2)')
