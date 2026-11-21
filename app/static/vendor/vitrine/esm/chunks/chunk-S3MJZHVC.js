/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as O,b as _,d as H,e as P,f as z,g as M,h as J,i as x,j as y}from"./chunk-J5BN7I7Q.js";import{a as T,c as q,d as v,f as B}from"./chunk-C3AKBLBA.js";import{a as C}from"./chunk-BNQD3D4I.js";import{r as I}from"./chunk-DUXCLZ3D.js";import{O as m,S as f,T as E,W as j,_ as N,b as S,ba as $,o as r,q as L}from"./chunk-7PAHM2BV.js";import{h as k,k as p,l as c,m as A,q as b}from"./chunk-TUK22DTT.js";var V=Object.freeze({jobInvalid:"This job could not be read: {message}",jobProgress:"Job progress",jobInProgress:"In progress",jobSteps:"{done} of {total} steps",jobNoSteps:"No steps yet.",jobNoMatch:"No log line matches.",jobNoLog:"No output.",jobCopyLog:"Copy log",jobAnnounce:"Job {status}",jobAnnounceStep:"Running: {step}",jobStatusQueued:"Queued",jobStatusRunning:"Running",jobStatusSuccess:"Succeeded",jobStatusFailure:"Failed",jobStatusCancelled:"Cancelled",jobStatusSkipped:"Skipped"}),G={jobInvalid:"Impossible de lire ce job : {message}",jobProgress:"Progression du job",jobInProgress:"En cours",jobSteps:"{done} \xE9tapes sur {total}",jobNoSteps:"Aucune \xE9tape pour l\u2019instant.",jobNoMatch:"Aucune ligne de log ne correspond.",jobNoLog:"Aucune sortie.",jobCopyLog:"Copier le log",jobAnnounce:"Job {status}",jobAnnounceStep:"En cours : {step}",jobStatusQueued:"En attente",jobStatusRunning:"En cours",jobStatusSuccess:"R\xE9ussi",jobStatusFailure:"\xC9chou\xE9",jobStatusCancelled:"Annul\xE9",jobStatusSkipped:"Ignor\xE9"};var R=`/*\r
 * Job: a summary with the status, duration and progress bar, then steps that open to\r
 * show their logs.\r
 */\r
.job-body {\r
  padding: var(--_space-4) var(--_space-5);\r
  background: var(--_surface);\r
  /* Without a height limit the page scrolls, not the job. */\r
  overscroll-behavior: auto;\r
}\r
\r
:host([max-height]) .job-body,\r
.vt[data-fullscreen] .job-body {\r
  overscroll-behavior: contain;\r
}\r
\r
/* ---------- Statuses ---------- */\r
\r
.status-queued,\r
.status-skipped,\r
.status-cancelled {\r
  --_tone: var(--_fg-muted);\r
}\r
\r
.status-running {\r
  --_tone: var(--_info);\r
}\r
\r
.status-success {\r
  --_tone: var(--_success);\r
}\r
\r
.status-failure {\r
  --_tone: var(--_danger);\r
}\r
\r
.job-status {\r
  display: inline-flex;\r
  flex: none;\r
  align-items: center;\r
  gap: 6px;\r
  color: var(--_tone);\r
  font: 600 var(--_font-size-ui) / 1 var(--_font-ui);\r
}\r
\r
.job-status .icon {\r
  width: 16px;\r
  height: 16px;\r
}\r
\r
.job-status.status-running .icon {\r
  animation: vt-job-spin 1s linear infinite;\r
}\r
\r
@keyframes vt-job-spin {\r
  to {\r
    transform: rotate(360deg);\r
  }\r
}\r
\r
/* ---------- Summary ---------- */\r
\r
.job-summary {\r
  display: grid;\r
  gap: var(--_space-2);\r
  padding-bottom: var(--_space-4);\r
  margin-bottom: var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
.job-title {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  gap: var(--_space-3);\r
}\r
\r
.job-title h2 {\r
  margin: 0;\r
  color: var(--_fg);\r
  font: 600 16px / 1.3 var(--_font-ui);\r
}\r
\r
.job-percent {\r
  margin-left: auto;\r
  color: var(--_fg-muted);\r
  font: 500 var(--_font-size-ui) / 1 var(--_font-mono);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.job-facts {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-4);\r
  color: var(--_fg-muted);\r
  font: var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.job-duration {\r
  color: var(--_fg-muted);\r
  font: var(--_font-size-small) / 1 var(--_font-mono);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
/* ---------- Progress bars ---------- */\r
\r
.job-progress {\r
  position: relative;\r
  height: 6px;\r
  overflow: hidden;\r
  border-radius: var(--_radius-full);\r
  background: color-mix(in srgb, var(--_tone, var(--_accent)) 15%, var(--_surface-sunken));\r
}\r
\r
.job-progress-fill {\r
  position: absolute;\r
  inset: 0 auto 0 0;\r
  width: var(--_value, 0%);\r
  border-radius: inherit;\r
  background: var(--_tone, var(--_accent));\r
  transition: width var(--_duration) var(--_easing);\r
}\r
\r
.job-progress.indeterminate .job-progress-fill {\r
  width: 35%;\r
  animation: vt-job-slide 1.4s var(--_easing) infinite;\r
}\r
\r
@keyframes vt-job-slide {\r
  from {\r
    transform: translateX(-100%);\r
  }\r
\r
  to {\r
    transform: translateX(300%);\r
  }\r
}\r
\r
.job-progress.mini {\r
  flex: 0 1 120px;\r
  height: 4px;\r
}\r
\r
@media (prefers-reduced-motion: reduce) {\r
  .job-status.status-running .icon,\r
  .job-progress.indeterminate .job-progress-fill {\r
    animation: none;\r
  }\r
\r
  /* Without motion, an unknown progress reads as a half-filled, faded bar. */\r
  .job-progress.indeterminate .job-progress-fill {\r
    width: 50%;\r
    opacity: 0.6;\r
  }\r
}\r
\r
/* ---------- Steps ---------- */\r
\r
.job-steps {\r
  display: grid;\r
  gap: var(--_space-1);\r
  padding: 0;\r
  margin: 0;\r
  list-style: none;\r
}\r
\r
.job-step {\r
  overflow: hidden;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
.job-step.status-failure {\r
  border-color: color-mix(in srgb, var(--_danger) 40%, var(--_border));\r
}\r
\r
.job-step-head {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  width: 100%;\r
  min-height: 36px;\r
  padding: 0 var(--_space-3);\r
  border: 0;\r
  background: var(--_surface);\r
  color: var(--_fg);\r
  font: 500 var(--_font-size-ui) / 1.3 var(--_font-ui);\r
  text-align: left;\r
  cursor: pointer;\r
  transition: background-color var(--_duration-fast) var(--_easing);\r
}\r
\r
.job-step-head:hover {\r
  background: color-mix(in srgb, var(--_fg) 4%, var(--_surface));\r
}\r
\r
.job-step-head:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: -2px;\r
}\r
\r
.job-step-head > .icon {\r
  width: 14px;\r
  height: 14px;\r
  flex: none;\r
  color: var(--_fg-muted);\r
  transition: transform var(--_duration-fast) var(--_easing);\r
}\r
\r
.job-step-head[aria-expanded='true'] > .icon {\r
  transform: rotate(90deg);\r
}\r
\r
.job-step-name {\r
  flex: 1 1 auto;\r
  min-width: 0;\r
  overflow: hidden;\r
  text-overflow: ellipsis;\r
  white-space: nowrap;\r
}\r
\r
.job-step-word {\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.job-step.status-skipped .job-step-name,\r
.job-step.status-queued .job-step-name {\r
  color: var(--_fg-muted);\r
}\r
\r
/* ---------- Logs ---------- */\r
\r
.job-log {\r
  max-height: min(50vh, 420px);\r
  padding: var(--_space-2) 0;\r
  overflow: auto;\r
  border-top: 1px solid var(--_border);\r
  background: var(--_code-bg);\r
  color: var(--_code-fg);\r
  font: var(--_font-size-small) / var(--_line-height) var(--_font-mono);\r
  overscroll-behavior: contain;\r
  scrollbar-width: thin;\r
}\r
\r
.job-log:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: -2px;\r
}\r
\r
.job-line {\r
  display: flex;\r
  min-width: max-content;\r
}\r
\r
.job-ln {\r
  flex: none;\r
  width: 4.5ch;\r
  padding-right: var(--_space-3);\r
  color: var(--_fg-muted);\r
  text-align: right;\r
  user-select: none;\r
}\r
\r
.job-text {\r
  padding-right: var(--_space-4);\r
  white-space: pre;\r
}\r
\r
.job-log-empty {\r
  padding: 0 var(--_space-4);\r
  color: var(--_fg-muted);\r
}\r
\r
mark.match {\r
  border-radius: 2px;\r
  background: var(--_highlight);\r
  color: inherit;\r
}\r
\r
mark.match.current {\r
  background: var(--_highlight-current);\r
}\r
\r
/* ---------- Edit mode ---------- */\r
\r
.job-edit > .editor-body {\r
  max-height: min(40vh, 360px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
`;A({en:V,fr:G});var D=5e3,F=class extends ${static type="job";static componentAttributes=Object.freeze(["progress","durations","open-failed","follow"]);static presets={simple:{progress:!0,durations:!0,"open-failed":!0},full:{header:!0,dot:!0,copy:!0,search:!0,download:!0,fullscreen:!0,progress:!0,durations:!0,"open-failed":!0}};static styles=[S,C,T,R];constructor(){super(),this.parsed=null,this.toggled=new Map,this.query="",this.matchCount=0,this.panelId=L("panel"),this.listHost=null,this.editor=null,this.previewTimer=void 0,this.lastStatus=""}disconnectedCallback(){clearTimeout(this.previewTimer),this.editor?.destroy(),super.disconnectedCallback()}contentChanged(){this.parsed=null,this.toggled.clear()}parse(){let t=this.text??"";if(this.parsed?.text===t)return this.parsed;try{this.parsed={text:t,job:P(t),error:null}}catch(e){this.parsed={text:t,job:null,error:e instanceof Error?e:new O(String(e))}}return this.parsed}get job(){let t=this.parse().job;return t?structuredClone(t):null}mutate(t){let e=this.parse().job,s=e?structuredClone(e):{name:"",status:"queued",started:"",finished:"",duration:null,progress:null,steps:[]},o=new Map(s.steps.map(n=>[n.name,n.status])),a=s.status;t(s);let i=JSON.stringify(s,null,2);this.text=i,this.error=null,this.parsed={text:i,job:s,error:null};for(let n of s.steps){let l=o.get(n.name);l&&l!==n.status&&c(this,p.JOB_CHANGE,{status:n.status,step:n.name,previous:l})}a!==s.status&&c(this,p.JOB_CHANGE,{status:s.status,step:null,previous:a}),!this.editing&&this.requestRender()}update(t){this.mutate(e=>{Object.assign(e,t),t.status!==void 0&&(e.status=_(t.status,e.status))})}setStep(t,e){this.mutate(s=>{let o=s.steps.find(a=>a.name===t);o||(o={name:t,status:"queued",started:"",finished:"",duration:null,progress:null,log:""},s.steps.push(o)),Object.assign(o,e,{name:t}),e.status!==void 0&&(o.status=_(e.status,o.status)),s.status=H(s.steps)})}appendLog(t,e){this.mutate(s=>{let o=s.steps.find(a=>a.name===t);o||(o={name:t,status:"running",started:"",finished:"",duration:null,progress:null,log:""},s.steps.push(o)),o.log=o.log?`${o.log}
${String(e)}`:String(e)})}isOpen(t){let e=this.toggled.get(t.name);return e!==void 0?e:this.query?t.log.toLowerCase().includes(this.query.toLowerCase()):this.feature("open-failed")&&t.status==="failure"}renderContent(t){let e=this.t,{job:s,error:o}=this.parse(),a=r("div",{class:"panel",attrs:{id:this.panelId}}),i=r("div",{class:"body job-body",part:"body"});o?i.append(N(e("jobInvalid",{message:o.message}))):s?(i.append(this.summary(s)),this.listHost=r("ol",{class:"job-steps",part:"steps"}),i.append(this.listHost),this.renderSteps(),this.announceStatus(s)):i.append(r("div",{class:"empty",part:"empty",text:e("empty")}));let n=[];if(this.editing){let u=this.createEditor();a.classList.add("job-edit"),a.append(r("div",{class:"body editor-body",part:"body source"},u.element),i),n=this.historyButtons(u)}else a.append(i);let l={run:u=>(this.query=u.slice(0,E).trim(),this.toggled.clear(),this.renderSteps(),{total:this.matchCount,capped:this.matchCount>=f}),go:u=>{let w=this.listHost?.querySelectorAll("mark.match")??[];for(let X of w)X.classList.remove("current");let g=w[u];g&&(g.classList.add("current"),g.scrollIntoView({block:"nearest",inline:"nearest"}))},clear:()=>{this.query="",this.renderSteps()}},d=[this.searchButton(l),...n,s&&!this.editing?j({icon:"expand-all",label:e("expandAll"),key:"expand-all",onClick:()=>this.openAll(!0)}):null,s&&!this.editing?j({icon:"collapse-all",label:e("collapseAll"),key:"collapse-all",onClick:()=>this.openAll(!1)}):null,this.editToggleButton(),this.fullscreenButton(),this.feature("download")?this.downloadButton(()=>{let u=this.parse().job;return u?y(u):""},this.downloadName("job.log"),"text/plain"):null,this.feature("copy")?this.copyButton(()=>{let u=this.parse().job;return u?y(u):""},e("jobCopyLog")):null],h=s?this.statusLabel(s.status):"";t.append(...this.chrome({badge:h,actions:d}),a),this.editor?.align()}get heading(){return super.heading||this.parse().job?.name||""}statusLabel(t){let e=`jobStatus${t[0].toUpperCase()}${t.slice(1)}`;return this.t(e)}statusView(t,e=!0){let s=t==="cancelled"?"skipped":t==="queued"?"circle":t;return r("span",{class:`job-status status-${t}`,part:"status"},m(`status-${s}`),r("span",{class:e?"status-word":"sr-only",text:this.statusLabel(t)}))}progressBar(t,e,s=""){let o=r("div",{class:`job-progress ${s}${t===null?" indeterminate":""}`,attrs:{role:"progressbar","aria-label":e,"aria-valuemin":"0","aria-valuemax":"100","aria-valuenow":t===null?null:String(Math.round(t)),"aria-valuetext":t===null?this.t("jobInProgress"):`${Math.round(t)} %`}}),a=r("span",{class:"job-progress-fill"});return t!==null&&a.style.setProperty("--_value",`${t}%`),o.append(a),o}summary(t){let e=this.t,s=t.steps.filter(l=>l.status!=="queued"&&l.status!=="running").length,o=J(t),a=r("div",{class:"job-facts"},r("span",{text:e("jobSteps",{done:b(s,this.locale),total:b(t.steps.length,this.locale)})}));this.feature("durations")&&o!==null&&a.append(r("span",{class:"job-duration",text:x(o)}));let i=M(t),n=r("div",{class:`job-summary status-${t.status}`,part:"summary"},r("div",{class:"job-title"},this.statusView(t.status),t.name?r("h2",{text:t.name}):null,i!==null?r("span",{class:"job-percent",text:`${i} %`}):null),a);if(this.feature("progress")){let l=this.progressBar(t.status==="running"&&t.progress===null&&!t.steps.length?null:i,e("jobProgress"));l.setAttribute("part","progress"),n.append(l)}return n}renderSteps(){let t=this.listHost,e=this.parse().job;if(!(!t||!e)){if(this.matchCount=0,!e.steps.length){t.replaceChildren(r("li",{class:"empty",part:"empty",text:this.t("jobNoSteps")}));return}if(t.replaceChildren(...e.steps.map((s,o)=>this.stepItem(s,o))),this.query&&!this.matchCount&&t.append(r("li",{class:"empty",part:"empty",text:this.t("jobNoMatch")})),this.feature("follow")){let s=t.querySelector(".job-step.status-running .job-log");s&&(s.scrollTop=s.scrollHeight)}}}stepItem(t,e){let s=this.isOpen(t),o=`${this.panelId}-log-${e}`,a=z(t),i=r("button",{class:"job-step-head",part:"step-head",attrs:{type:"button","aria-expanded":String(s),"aria-controls":o,"data-focus-key":`step-${e}`},on:{click:()=>this.toggle(t,!s,e)}},m("chevron-right"),this.statusView(t.status,!1),r("span",{class:"job-step-name",text:t.name}),t.status==="running"?this.progressBar(a,t.name,"mini"):r("span",{class:"job-step-word",text:this.statusLabel(t.status)}),this.feature("durations")&&t.duration!==null?r("span",{class:"job-duration",text:x(t.duration)}):null),n=r("li",{class:`job-step status-${t.status}`,part:`step step-${t.status}`},i),l=this.logView(t,o);return s&&n.append(l),n}logView(t,e){let s=r("div",{class:"job-log ansi",part:"step-log",attrs:{id:e,tabindex:"0",role:"region","aria-label":t.name}});if(!t.log)return s.append(r("div",{class:"job-log-empty",text:this.t("jobNoLog")})),s;let o=q(t.log).slice(0,D),a=this.query.toLowerCase();return o.forEach((i,n)=>{let l=r("div",{class:"job-line"},r("span",{class:"job-ln",attrs:{"aria-hidden":"true"},text:String(n+1)})),d=r("span",{class:"job-text"});if(a&&v(i).toLowerCase().includes(a))this.markLine(d,i,a);else for(let h of i)d.append(B(h));l.append(d),s.append(l)}),s}markLine(t,e,s){let o=v(e),a=o.toLowerCase(),i=0,n=a.indexOf(s);for(;n!==-1&&this.matchCount<f;)t.append(o.slice(i,n),r("mark",{class:"match",text:o.slice(n,n+s.length)})),this.matchCount+=1,i=n+s.length,n=a.indexOf(s,i);t.append(o.slice(i))}toggle(t,e,s){this.toggled.set(t.name,e),this.renderSteps(),this.restoreFocus(`step-${s}`),c(this,p.STEP_TOGGLE,{name:t.name,open:e})}openAll(t){let e=this.parse().job;if(e){for(let s of e.steps)this.toggled.set(s.name,t);this.renderSteps()}}announceStatus(t){let e=t.steps.find(o=>o.status==="running"),s=`${t.status}:${e?.name??""}`;this.lastStatus&&this.lastStatus!==s&&this.announce(e&&t.status==="running"?this.t("jobAnnounceStep",{step:e.name}):this.t("jobAnnounce",{status:this.statusLabel(t.status)})),this.lastStatus=s}createEditor(){this.editor?.destroy();let t=/^\s*[[{]/.test(this.text??"");return this.editor=new I({text:this.text??"",language:t?"json":"markdown",lineNumbers:!0,wrap:!1,highlightLimit:k().highlightLimit,label:this.heading||this.t("editor"),placeholder:this.getAttribute("placeholder")??void 0,onInput:e=>this.edited(e),onChange:e=>c(this,p.CHANGE,{value:e}),history:this.editHistory??void 0}),this.editor}contentEdited(){clearTimeout(this.previewTimer),this.previewTimer=setTimeout(()=>{this.parsed=null,this.render()},400)}};export{F as a};
