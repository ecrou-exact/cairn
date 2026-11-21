/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as T,c as E}from"./chunk-5CTFTED4.js";import{b as $,d as N}from"./chunk-JRZ3XLAR.js";import{O as A,c as _,e as z,j as C,o}from"./chunk-7PAHM2BV.js";import{k as h,l as f,q as u}from"./chunk-TUK22DTT.js";var L=`/*\r
 * <vt-loading-steps>: an ordered list of steps with a status mark each, joined by a line\r
 * (list), dense (compact) or side by side (horizontal); an overall bar above.\r
 */\r
:host {\r
  display: block;\r
}\r
\r
.indicator {\r
  display: grid;\r
  gap: var(--_space-3);\r
  --_mark: calc(var(--_ind-size) + 8px);\r
}\r
\r
.steps-head {\r
  display: flex;\r
  align-items: center;\r
  justify-content: space-between;\r
  gap: var(--_space-3);\r
}\r
\r
.steps-title {\r
  margin: 0;\r
  font-weight: 650;\r
}\r
\r
.steps-summary {\r
  display: grid;\r
  grid-template-columns: 1fr auto;\r
  gap: var(--_space-1) var(--_space-3);\r
}\r
\r
.steps-count {\r
  opacity: var(--_dim);\r
  font-size: var(--_font-size-small);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.steps-track {\r
  grid-column: 1 / -1;\r
  height: 4px;\r
  overflow: hidden;\r
  border-radius: 999px;\r
  background: var(--_ind-track);\r
}\r
\r
.steps-bar {\r
  display: block;\r
  height: 100%;\r
  border-radius: inherit;\r
  background: var(--_ind-color);\r
  transform: scaleX(var(--_ratio));\r
  transform-origin: left center;\r
  transition: transform 0.3s ease;\r
}\r
\r
.indicator[data-status='error'] .steps-bar {\r
  background: var(--_danger);\r
}\r
\r
.indicator[data-status='done'] .steps-bar {\r
  background: var(--_success);\r
}\r
\r
.steps {\r
  display: grid;\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.step {\r
  position: relative;\r
  display: grid;\r
  grid-template-columns: var(--_mark) 1fr auto;\r
  gap: var(--_space-3);\r
  align-items: start;\r
  padding-bottom: var(--_space-3);\r
}\r
\r
.step:last-child {\r
  padding-bottom: 0;\r
}\r
\r
/* The line joining a mark to the next one. */\r
.indicator[data-layout='list'] .step:not(:last-child)::before {\r
  content: '';\r
  position: absolute;\r
  top: calc(var(--_mark) + 2px);\r
  bottom: 2px;\r
  inset-inline-start: calc(var(--_mark) / 2 - 1px);\r
  border-inline-start: 2px solid var(--_border);\r
}\r
\r
.indicator[data-layout='list'] .step.done:not(:last-child)::before {\r
  border-color: color-mix(in srgb, var(--_success) 55%, var(--_border));\r
}\r
\r
.step-mark {\r
  display: grid;\r
  place-items: center;\r
  width: var(--_mark);\r
  height: var(--_mark);\r
  border: 2px solid var(--_border);\r
  border-radius: 50%;\r
  background: var(--_surface, transparent);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-weight: 650;\r
}\r
\r
.step-mark svg {\r
  width: 60%;\r
  height: 60%;\r
}\r
\r
.step-mark .spinner {\r
  --_ind-size: calc(var(--_mark) - 4px);\r
  border-width: 2px;\r
}\r
\r
.step-mark.running {\r
  border: 0;\r
}\r
\r
.step-mark.done {\r
  border-color: var(--_success);\r
  background: var(--_success);\r
  color: var(--_surface, #fff);\r
}\r
\r
.step-mark.warning {\r
  border-color: var(--_warning);\r
  color: var(--_warning);\r
}\r
\r
.step-mark.error {\r
  border-color: var(--_danger);\r
  background: var(--_danger);\r
  color: var(--_surface, #fff);\r
}\r
\r
.step-mark.skipped {\r
  border-style: dashed;\r
}\r
\r
.step-body {\r
  display: grid;\r
  gap: 2px;\r
  min-width: 0;\r
  padding-top: calc((var(--_mark) - 1.4em) / 2);\r
}\r
\r
.step-label {\r
  line-height: 1.4;\r
}\r
\r
.step.pending .step-label,\r
.step.skipped .step-label {\r
  opacity: var(--_dim);\r
}\r
\r
.step.skipped .step-label {\r
  text-decoration: line-through;\r
}\r
\r
.step.running .step-label {\r
  font-weight: 650;\r
}\r
\r
.step.error .step-label {\r
  font-weight: 650;\r
}\r
\r
.step-detail {\r
  opacity: var(--_dim);\r
  font-size: var(--_font-size-small);\r
  line-height: 1.4;\r
  overflow-wrap: anywhere;\r
}\r
\r
.step-duration {\r
  padding-top: calc((var(--_mark) - 1.4em) / 2);\r
  opacity: var(--_dim);\r
  font-size: var(--_font-size-small);\r
  font-variant-numeric: tabular-nums;\r
  line-height: 1.4;\r
  white-space: nowrap;\r
}\r
\r
.indicator[data-layout='compact'] .step {\r
  padding-bottom: var(--_space-1);\r
}\r
\r
.indicator[data-layout='horizontal'] .steps {\r
  grid-auto-columns: minmax(0, 1fr);\r
  grid-auto-flow: column;\r
}\r
\r
.indicator[data-layout='horizontal'] .step {\r
  grid-template-columns: 1fr;\r
  justify-items: center;\r
  gap: var(--_space-1);\r
  padding: 0 var(--_space-1);\r
  text-align: center;\r
}\r
\r
.indicator[data-layout='horizontal'] .step:not(:last-child)::after {\r
  content: '';\r
  position: absolute;\r
  top: calc(var(--_mark) / 2 - 1px);\r
  inset-inline-start: calc(50% + var(--_mark) / 2 + 4px);\r
  inset-inline-end: calc(-50% + var(--_mark) / 2 + 4px);\r
  border-top: 2px solid var(--_border);\r
}\r
\r
.indicator[data-layout='horizontal'] .step.done:not(:last-child)::after {\r
  border-color: var(--_success);\r
}\r
\r
.indicator[data-layout='horizontal'] .step-body,\r
.indicator[data-layout='horizontal'] .step-duration {\r
  padding-top: 0;\r
}\r
\r
.steps-cancel {\r
  padding: 4px 12px;\r
  border: 1px solid currentColor;\r
  border-radius: var(--_radius-sm, 6px);\r
  background: transparent;\r
  color: inherit;\r
  font: inherit;\r
  cursor: pointer;\r
}\r
\r
.steps-cancel:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.indicator[data-motion='reduce'] .steps-bar {\r
  transition: none;\r
}\r
\r
@media (max-width: 480px) {\r
  .indicator[data-layout='horizontal'] .step-label {\r
    font-size: var(--_font-size-small);\r
  }\r
}\r
`;var j=["pending","running","done","warning","error","skipped"],b={pending:"pending",todo:"pending",waiting:"pending",queued:"pending","[ ]":"pending",running:"running",active:"running",current:"running","in-progress":"running","[~]":"running","[>]":"running",done:"done",ok:"done",success:"done",complete:"done",completed:"done","[x]":"done",warning:"warning",warn:"warning","[!]":"warning",error:"error",failed:"error",fail:"error","[-]":"error",skipped:"skipped",skip:"skipped","[/]":"skipped"},O=200,g=300;function k(n){let t=n.trim().toLowerCase(),e=/^(\d+(?:\.\d+)?)\s*ms$/.exec(t);return e?Number(e[1]):(e=/^(?:(\d+)\s*h\s*)?(?:(\d+)\s*m(?:in)?\s*)?(?:(\d+(?:\.\d+)?)\s*s)?$/.exec(t),e&&(e[1]||e[2]||e[3])?((Number(e[1]??0)*60+Number(e[2]??0))*60+Number(e[3]??0))*1e3:(e=/^(\d+):(\d{2})$/.exec(t),e?(Number(e[1])*60+Number(e[2]))*1e3:null))}function R(n){return b[String(n??"").toLowerCase()]??"pending"}function v(n){let t=n.trim();if(!t)return[];if(/^[[{]/.test(t))try{let r=JSON.parse(t),a=Array.isArray(r)?r:Array.isArray(r?.steps)?r.steps:[],s=[];for(let i of a.slice(0,O)){let l=P(i);l&&s.push(l)}return s}catch{return[]}let e=[];for(let r of t.split(/\r\n|\n|\r/)){if(e.length>=O)break;let a=r.trim().replace(/^[-*]\s+/,"");if(!a)continue;let s="pending",i=/^(\[[ x~>!/-]\])\s*/i.exec(a),l=/^([a-z-]+)(?::|\s)\s*/i.exec(a);i?(s=b[i[1].toLowerCase()]??"pending",a=a.slice(i[0].length)):l&&b[l[1].toLowerCase()]&&(s=b[l[1].toLowerCase()],a=a.slice(l[0].length));let c=null,d=/\s*\(([^()]+)\)\s*$/.exec(a);d&&k(d[1])!==null&&(c=k(d[1]),a=a.slice(0,d.index));let[m,...x]=a.split(/\s+(?:—|–|\|)\s+|\s+--\s+/);e.push({label:m.trim().slice(0,g),status:s,detail:x.join(" \u2014 ").trim().slice(0,g),duration:c})}return e}function P(n){if(typeof n=="string")return{label:n.slice(0,g),status:"pending",detail:"",duration:null};if(!n||typeof n!="object")return null;let t=String(n.label??n.name??n.title??"").slice(0,g);if(!t)return null;let e=typeof n.duration=="number"&&n.duration>=0?n.duration:typeof n.duration=="string"?k(n.duration):null;return{label:t,status:R(n.status??n.state),detail:String(n.detail??n.description??"").slice(0,g),duration:e}}function M(n){return n.some(t=>t.status==="error")?"error":n.length&&n.every(t=>t.status==="done"||t.status==="skipped"||t.status==="warning")?n.some(t=>t.status==="warning")?"warning":"done":n.some(t=>t.status==="running"||t.status==="done")?"running":"pending"}var D={done:"check",warning:"alert",error:"close",skipped:"minus"},X=["list","compact","horizontal"],I=class extends N{static type="loading-steps";static componentAttributes=["text","layout","progress","durations","details","cancelable"];static styles=[T,L];static display="block";static defaultSize="sm";constructor(){super(),this.stepsState=null,this.contentState=null,this.observer=null,this.lastSignature=null}connectedCallback(){this.observer=new MutationObserver(()=>{this.stepsState||this.requestRender()}),this.observer.observe(this,{childList:!0,characterData:!0,subtree:!0}),super.connectedCallback()}disconnectedCallback(){this.observer?.disconnect(),this.observer=null,super.disconnectedCallback()}get steps(){if(this.stepsState)return this.stepsState.map(e=>({...e}));let t=this.querySelector("template");return v(t?t.content.textContent??"":this.textContent??"")}set steps(t){this.stepsState=Array.isArray(t)?v(JSON.stringify(t)):null,this.requestRender()}get content(){return this.contentState??""}set content(t){this.contentState=t==null?null:String(t),this.stepsState=this.contentState===null?null:v(this.contentState),this.requestRender()}setStep(t,e){let r=this.steps,a=typeof t=="number"?t:r.findIndex(i=>i.label===t);if(a<0||a>=r.length)return;let s={...r[a],...e};j.includes(s.status)||(s.status=r[a].status),r[a]=s,this.steps=r}draw(t){if(!this.shown){t.replaceChildren();return}let e=this.t,r=this.steps,a=z(this.getAttribute("layout"),X,"list"),s=p=>_(this.getAttribute(p))??!0,i=r.filter(p=>p.status!=="pending"&&p.status!=="running").length,l=M(r),c=r.findIndex(p=>p.status==="running"),d=C(this.getAttribute("text"));this.notify(r,i,l),t.dataset.layout=a,t.dataset.status=l;let m=null;if(s("progress")&&r.length){let p=i/r.length,y=c>=0?c+1:Math.min(r.length,i+(l==="done"||l==="warning"?0:1)),w=o("div",{class:"steps-track",part:"bar",attrs:{role:"progressbar","aria-label":d||this.labelText("loadingStepsTitle"),"aria-valuemin":"0","aria-valuemax":String(r.length),"aria-valuenow":String(i),"aria-valuetext":e("loadingStepsDone",{done:u(i,this.locale),total:u(r.length,this.locale)})}},o("span",{class:"steps-bar"}));w.style.setProperty("--_ratio",String(p)),m=o("div",{class:"steps-summary",part:"summary"},o("span",{text:l==="done"||l==="warning"?e("loadingComplete"):l==="error"?e("loadingFailed"):e("loadingStepOf",{current:u(y,this.locale),total:u(r.length,this.locale)})}),o("span",{class:"steps-count",text:e("loadingStepsDone",{done:u(i,this.locale),total:u(r.length,this.locale)})}),w)}let x=o("ol",{class:"steps",part:"steps",attrs:{"aria-label":d||this.labelText("loadingStepsTitle")}},...r.map((p,y)=>this.stepView(p,y,a,s("durations"),s("details")))),S=_(this.getAttribute("cancelable"))&&l==="running"?o("button",{class:"steps-cancel",part:"cancel",text:e("loadingCancel"),attrs:{type:"button"},on:{click:()=>f(this,h.CANCEL,{})}}):null;t.replaceChildren(...$([d||S?o("div",{class:"steps-head"},d?o("p",{class:"steps-title",part:"title",text:d}):o("span"),S):null,m,x]))}stepView(t,e,r,a,s){let i=this.t,l=i(`loadingStatus_${t.status}`),c=o("span",{class:`step-mark ${t.status}`,part:"mark",attrs:{"aria-hidden":"true"}});return t.status==="running"?c.append(E("ring")):t.status in D?c.append(A(D[t.status])):c.append(o("span",{class:"step-number",text:String(e+1)})),o("li",{class:`step ${t.status}`,part:`step step-${t.status}`,attrs:t.status==="running"?{"aria-current":"step"}:{}},c,o("span",{class:"step-body"},o("span",{class:"step-label",text:t.label}),o("span",{class:"sr-only",text:`, ${l}`}),s&&t.detail&&r!=="horizontal"?o("span",{class:"step-detail",part:"detail",text:t.detail}):null),a&&t.duration!==null?o("span",{class:"step-duration",part:"duration",text:F(t.duration,this.locale)}):null)}notify(t,e,r){let a=t.map(i=>i.status).join(",");if(a===this.lastSignature)return;let s=this.lastSignature===null;t.length&&(this.lastSignature=a,!s&&(f(this,h.PROGRESS,{value:e,max:t.length,ratio:t.length?e/t.length:0}),(r==="done"||r==="warning"||r==="error")&&f(this,h.COMPLETE,{status:r})))}};function F(n,t){let e=(s,i=0)=>new Intl.NumberFormat(t,{maximumFractionDigits:i}).format(s);if(n<1e3)return`${e(n)} ms`;if(n<6e4)return`${e(n/1e3,1)} s`;let r=Math.floor(n/6e4),a=Math.round(n%6e4/1e3);return r<60?a?`${e(r)} min ${e(a)} s`:`${e(r)} min`:`${e(Math.floor(r/60))} h ${e(r%60)} min`}export{I as a};
