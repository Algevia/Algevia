/* Algevia V47 draft adaptive engine. Standalone data layer; does not change learn.html.
   Questions require curriculum/answer review before student-facing production use. */
(function (global) {
'use strict';
const STORAGE = 'algevia_adaptive_v47_progress';
const unique = a => [...new Set(a)];
const clamp = (x,a,b) => Math.max(a,Math.min(b,x));
class AdaptiveEngine {
  constructor(questions, settings={}) {
    if (!Array.isArray(questions)) throw new Error('Question bank must contain a questions array');
    this.questions=questions.filter(q=>q && q.id && q.skill_id && Number.isFinite(Number(q.grade)));
    this.settings={currentGrade:4,targetGrade:6,extension:false,progression:'student',...settings};
    this.state={skills:{},questionHistory:{},active:null,revisionQueue:[],lastSkill:null};
    try {const saved=JSON.parse(localStorage.getItem(STORAGE)||'null');if(saved&&saved.skills)this.state={...this.state,...saved,active:null};}catch(e){}
  }
  save(){try{localStorage.setItem(STORAGE,JSON.stringify(this.state))}catch(e){}}
  configure(settings){this.settings={...this.settings,...settings};this.state.active=null;this.save();}
  gradeBounds(){const current=clamp(+this.settings.currentGrade||4,1,9),target=clamp(+this.settings.targetGrade||6,current,9);return {current,target,max:Math.min(9,target+(this.settings.extension?1:0))};}
  skill(skillId){return this.state.skills[skillId] ||= {streak:0,correct:0,wrong:0,skipped:0,attempts:0,unlocked:false,reviewDue:0,misconceptions:{}};}
  available(){const {current,max}=this.gradeBounds();return this.questions.filter(q=>+q.grade>=current&&+q.grade<=max);}
  skills(area,topic){return unique(this.available().filter(q=>(!area||q.area===area)&&(!topic||q.topic===topic)).map(q=>q.skill_id));}
  chooseQuestion({area=null,topic=null,skillId=null,revision=false}={}){
    let available=this.available().filter(q=>(!area||q.area===area)&&(!topic||q.topic===topic));
    if(skillId)available=available.filter(q=>q.skill_id===skillId);
    if(!available.length)return {error:'No questions available for these grade/topic filters.'};
    const bySkill=new Map();for(const q of available){if(!bySkill.has(q.skill_id))bySkill.set(q.skill_id,[]);bySkill.get(q.skill_id).push(q);}
    const due=[...bySkill.keys()].filter(k=>this.skill(k).reviewDue&&this.skill(k).reviewDue<=Date.now());
    if(revision||(!skillId&&due.length&&Math.random()<0.2)){
      const k=due[0];if(k)available=bySkill.get(k);
    } else if(!skillId){
      const entries=[...bySkill.entries()].sort((a,b)=>{const aa=this.skill(a[0]),bb=this.skill(b[0]);return (aa.unlocked?1:0)-(bb.unlocked?1:0)||Math.min(...a[1].map(q=>+q.grade))-Math.min(...b[1].map(q=>+q.grade));});
      available=entries[0][1];
    }
    const unseen=available.filter(q=>!this.state.questionHistory[q.id]);
    const pool=unseen.length?unseen:available.slice().sort((a,b)=>(this.state.questionHistory[a.id]?.lastSeen||0)-(this.state.questionHistory[b.id]?.lastSeen||0));
    const question=pool[Math.floor(Math.random()*Math.min(pool.length,Math.max(1,Math.min(5,pool.length))))];
    this.state.active={id:question.id,skillId:question.skill_id,answered:false};this.save();
    return {question,skill:this.skill(question.skill_id),poolSize:available.length,uniqueRemaining:unseen.length,insufficientPool:available.length<4};
  }
  record({questionId,kind,misconception=null}){
    const a=this.state.active;if(!a||a.id!==questionId||a.answered)throw new Error('Question is not active or has already been recorded');
    if(!['correct','incorrect','skip'].includes(kind))throw new Error('Invalid outcome');
    const s=this.skill(a.skillId);const hist=this.state.questionHistory[questionId]||{seen:0};
    hist.seen++;hist.lastSeen=Date.now();hist.lastOutcome=kind;this.state.questionHistory[questionId]=hist;
    if(kind==='correct'){s.correct++;s.attempts++;s.streak++;if(s.streak>=2){s.unlocked=true;s.reviewDue=Date.now()+24*3600*1000;}}
    if(kind==='incorrect'){s.wrong++;s.attempts++;s.streak=0;if(misconception)s.misconceptions[misconception]=(s.misconceptions[misconception]||0)+1;}
    if(kind==='skip'){s.skipped++;/* no mastery credit and no penalty */}
    a.answered=true;this.state.lastSkill=a.skillId;this.save();
    return {skillId:a.skillId,streak:s.streak,unlocked:s.unlocked,masteryEvidence:s.correct,revisionDue:s.reviewDue,kind};
  }
  nextAfter(outcome,options={}){
    const last=this.state.lastSkill;
    if(outcome==='correct'&&last&&this.skill(last).unlocked){
      const available=this.skills(options.area,options.topic);
      const i=available.indexOf(last);
      if(i>=0&&i+1<available.length)return this.chooseQuestion({...options,skillId:available[i+1]});
    }
    return this.chooseQuestion({...options,skillId:last||options.skillId||null});
  }
  getProgress(){return JSON.parse(JSON.stringify(this.state.skills));}
}
async function loadBank(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error('Bank unavailable (HTTP '+response.status+')');const data=await response.json();if(!Array.isArray(data.questions))throw new Error('Invalid question bank');return data;}
global.AlgeviaAdaptive={AdaptiveEngine,loadBank};
})(window);
