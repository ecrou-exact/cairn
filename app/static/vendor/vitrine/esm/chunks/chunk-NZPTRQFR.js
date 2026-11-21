/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as K}from"./chunk-KVX7N5JQ.js";import{a as Z}from"./chunk-INCBER5S.js";import{a as X}from"./chunk-NPDHR5SA.js";import{a as H}from"./chunk-BYF54QDU.js";import{a as L}from"./chunk-BNQD3D4I.js";import{A as B,B as g,C as x,D as $,E as M,G as k,X as W,_ as G,b as F,d as Y,e as I,o as r,q as R}from"./chunk-7PAHM2BV.js";import{k as q,l as P,m as J,q as V}from"./chunk-TUK22DTT.js";var Q=`/*\r
 * Lifecycle: release cycles, their support and its end, as a table and a schedule.\r
 */\r
.lc-body {\r
  display: grid;\r
  gap: var(--_space-4);\r
}\r
\r
.lc-status {\r
  display: inline-block;\r
  padding: 1px var(--_space-2);\r
  border: 1px solid currentColor;\r
  border-radius: var(--_radius-full);\r
  font-size: var(--_font-size-small);\r
  font-weight: 600;\r
  white-space: nowrap;\r
}\r
\r
.lc-status.s-active {\r
  color: var(--_success);\r
}\r
\r
.lc-status.s-security,\r
.lc-status.s-extended {\r
  color: var(--_warning);\r
}\r
\r
.lc-status.s-eol {\r
  color: var(--_danger);\r
}\r
\r
.lc-status.s-upcoming {\r
  color: var(--_info);\r
}\r
\r
/* ---------- The version checked ---------- */\r
\r
.lc-check {\r
  display: grid;\r
  justify-items: start;\r
  gap: var(--_space-1);\r
  padding: var(--_space-3) var(--_space-4);\r
  border: 1px solid var(--_border);\r
  border-inline-start: 4px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
.lc-check p {\r
  margin: 0;\r
  color: var(--_fg);\r
}\r
\r
.lc-check.s-active {\r
  border-inline-start-color: var(--_success);\r
}\r
\r
.lc-check.s-security,\r
.lc-check.s-extended {\r
  border-inline-start-color: var(--_warning);\r
}\r
\r
.lc-check.s-eol,\r
.lc-check.s-unknown {\r
  border-inline-start-color: var(--_danger);\r
}\r
\r
.lc-check .lc-update {\r
  color: var(--_fg-muted);\r
}\r
\r
/* ---------- Table ---------- */\r
\r
.lc-wrap {\r
  overflow-x: auto;\r
}\r
\r
.lc-table th[scope='row'] {\r
  text-align: start;\r
}\r
\r
.lc-table tr.s-eol {\r
  color: var(--_fg-muted);\r
}\r
\r
.lc-table tr.lc-mine th,\r
.lc-table tr.lc-mine td {\r
  background: var(--_accent-soft);\r
}\r
\r
.lc-table a {\r
  color: var(--_accent-fg);\r
}\r
\r
.lc-name {\r
  display: inline-flex;\r
  flex-wrap: wrap;\r
  align-items: baseline;\r
  gap: var(--_space-1) var(--_space-2);\r
}\r
\r
.lc-lts {\r
  padding: 0 var(--_space-1);\r
  border: 1px solid currentColor;\r
  border-radius: var(--_radius-sm);\r
  color: var(--_accent-fg);\r
  font-size: var(--_font-size-small);\r
  font-weight: 600;\r
}\r
\r
.lc-codename {\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-weight: 400;\r
}\r
\r
/* ---------- Schedule ---------- */\r
\r
.lc-schedule {\r
  --_label: 9rem;\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
}\r
\r
.lc-ruler {\r
  position: relative;\r
  height: 1.5em;\r
  margin-inline-start: var(--_label);\r
  border-bottom: 1px solid var(--_border);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.lc-tick {\r
  position: absolute;\r
  inset-inline-start: var(--_at);\r
  translate: -50% 0;\r
}\r
\r
.lc-today {\r
  position: absolute;\r
  inset-inline-start: var(--_at);\r
  top: 0;\r
  height: 100%;\r
  border-inline-start: 2px solid var(--_accent);\r
}\r
\r
.lc-rows {\r
  position: relative;\r
  display: grid;\r
  gap: var(--_space-1);\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.lc-row {\r
  display: grid;\r
  grid-template-columns: var(--_label) 1fr;\r
  align-items: center;\r
  min-height: 28px;\r
}\r
\r
.lc-row.lc-mine {\r
  border-radius: var(--_radius-sm);\r
  background: var(--_accent-soft);\r
}\r
\r
.lc-label {\r
  overflow: hidden;\r
  padding-inline: var(--_space-2);\r
  text-overflow: ellipsis;\r
  white-space: nowrap;\r
}\r
\r
.lc-track {\r
  position: relative;\r
  height: 18px;\r
}\r
\r
.lc-bar {\r
  position: absolute;\r
  inset-inline-start: var(--_start);\r
  top: 0;\r
  width: var(--_width);\r
  height: 100%;\r
}\r
\r
.lc-bar.b-active,\r
.lc-key.b-active::before {\r
  background: var(--_success);\r
}\r
\r
.lc-bar.b-security,\r
.lc-key.b-security::before {\r
  background: var(--_warning);\r
}\r
\r
.lc-bar.b-extended,\r
.lc-key.b-extended::before {\r
  background: var(--_border-strong);\r
}\r
\r
.lc-bar:first-child {\r
  border-start-start-radius: var(--_radius-sm);\r
  border-end-start-radius: var(--_radius-sm);\r
}\r
\r
.lc-bar:last-child {\r
  border-start-end-radius: var(--_radius-sm);\r
  border-end-end-radius: var(--_radius-sm);\r
}\r
\r
/* No end date: the bar fades out. */\r
.lc-bar.open {\r
  mask-image: linear-gradient(to right, #000 70%, transparent);\r
}\r
\r
.lc-row.s-eol .lc-bar {\r
  opacity: 0.45;\r
}\r
\r
.lc-legend {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-4);\r
  margin: 0;\r
  margin-inline-start: var(--_label);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.lc-key::before {\r
  content: '';\r
  display: inline-block;\r
  width: 12px;\r
  height: 8px;\r
  margin-inline-end: var(--_space-1);\r
  border-radius: 2px;\r
}\r
\r
.lc-more {\r
  justify-self: start;\r
}\r
\r
@media (max-width: 520px) {\r
  .lc-schedule {\r
    --_label: 5.5rem;\r
  }\r
\r
  .lc-codename {\r
    display: none;\r
  }\r
}\r
`;var _=class extends Error{};function O(e){return typeof e=="boolean"?{time:null,flag:e}:{time:k(e),flag:null}}function oe(e){let t=$(e,["name","cycle","version","release","branch"],60);if(!t)return null;let l=O(e.eolFrom??e.eol??e.securitySupport??e.security??e.end),a=O(e.eoasFrom??e.support??e.activeSupport??e.active??e.bugfixes),s=O(e.eoesFrom??e.extendedSupport??e.extended),n=g(e.latest)?e.latest:null,o=e.isLts??e.lts,i=e.isEol===!0||l.flag===!0,d=e.supported===!0||e.isEol===!1||l.flag===!1;return{name:t,label:x(e.label,100),codename:x(e.codename,100),released:k(e.releaseDate??e.released??e.date),activeEnd:a.time,eol:l.time,extendedEnd:s.time,lts:o===!0||typeof o=="string"||e.ltsFrom!==void 0&&e.ltsFrom!==null,ended:i&&l.time===null,supported:d&&l.time===null&&e.supported!==!1,latest:n?x(n.name,60):x(e.latest??e.latestVersion,60),latestDate:k(n?n.date:e.latestReleaseDate),link:M(n?.link??e.link??e.url)}}function ee(e){let t=e,l="";if(g(e)){let s=g(e.result)?e.result:e;l=$(s,["label","name","product"],100),t=[s.releases,s.cycles,s.versions,s.items].find(Array.isArray)}if(!Array.isArray(t))throw new _("shape");let a=t.filter(g).slice(0,B).map(oe).filter(s=>s!==null);return{name:l,cycles:a}}function f(e,t){return e.released!==null&&e.released>t?"upcoming":(e.eol!==null?e.eol<=t:e.ended)?e.extendedEnd!==null&&e.extendedEnd>t?"extended":"eol":e.activeEnd!==null&&e.activeEnd<=t?"security":"active"}function te(e,t){let l=t.trim().replace(/^v/i,"");if(!l)return null;let a=null;for(let s of e){let n=s.name.replace(/^v/i,"");(l===n||l.startsWith(`${n}.`)||l.startsWith(`${n}-`))&&(!a||n.length>a.name.length)&&(a=s)}return a}var le=Object.freeze({lifecycleTable:"Table",lifecycleSchedule:"Schedule",lifecycleVersion:"Version",lifecycleStatus:"Status",lifecycleReleased:"Released",lifecycleActive:"Active support",lifecycleSecurity:"Security support",lifecycleLatest:"Latest",lifecycleLts:"LTS",lifecycleToday:"Today",lifecycleStatus_upcoming:"Upcoming",lifecycleStatus_active:"Supported",lifecycleStatus_security:"Security fixes only",lifecycleStatus_extended:"Extended support",lifecycleStatus_eol:"End of life",lifecycleUntil:"until {date}",lifecycleEnded:"ended {date}",lifecycleYes:"Yes",lifecycleNo:"No",lifecycleSupported:"{count} supported",lifecycleCheck_upcoming:"{version} belongs to {cycle}, released on {date}.",lifecycleCheck_active:"{version} is supported: bug and security fixes until {date}.",lifecycleCheck_activeOpen:"{version} is supported.",lifecycleCheck_security:"{version} gets security fixes only, until {date}.",lifecycleCheck_extended:"{version} reached its end of life on {date}; extended support goes on until {until}.",lifecycleCheck_eol:"{version} is no longer supported, since {date}.",lifecycleCheck_eolOpen:"{version} is no longer supported.",lifecycleCheckUnknown:"No release cycle matches {version}.",lifecycleUpdate:"The latest release of {cycle} is {latest}.",lifecycleRow:"{cycle}: {status}.",lifecycleShowEnded:"Show {count} ended",lifecycleCopyCsv:"Copy as CSV",lifecycleEmpty:"No release cycle.",lifecycleShape:"Expected endoflife.date JSON, or a list of release cycles."}),se={lifecycleTable:"Tableau",lifecycleSchedule:"Calendrier",lifecycleVersion:"Version",lifecycleStatus:"\xC9tat",lifecycleReleased:"Sortie",lifecycleActive:"Support actif",lifecycleSecurity:"Support de s\xE9curit\xE9",lifecycleLatest:"Derni\xE8re",lifecycleToday:"Aujourd\u2019hui",lifecycleStatus_upcoming:"\xC0 venir",lifecycleStatus_active:"Support\xE9e",lifecycleStatus_security:"Correctifs de s\xE9curit\xE9 seulement",lifecycleStatus_extended:"Support \xE9tendu",lifecycleStatus_eol:"Fin de vie",lifecycleUntil:"jusqu\u2019au {date}",lifecycleEnded:"termin\xE9 le {date}",lifecycleYes:"Oui",lifecycleNo:"Non",lifecycleSupported:"{count} support\xE9es",lifecycleCheck_upcoming:"{version} appartient \xE0 {cycle}, qui sort le {date}.",lifecycleCheck_active:"{version} est support\xE9e : correctifs et s\xE9curit\xE9 jusqu\u2019au {date}.",lifecycleCheck_activeOpen:"{version} est support\xE9e.",lifecycleCheck_security:"{version} ne re\xE7oit que des correctifs de s\xE9curit\xE9, jusqu\u2019au {date}.",lifecycleCheck_extended:"{version} est en fin de vie depuis le {date} ; le support \xE9tendu dure jusqu\u2019au {until}.",lifecycleCheck_eol:"{version} n\u2019est plus support\xE9e depuis le {date}.",lifecycleCheck_eolOpen:"{version} n\u2019est plus support\xE9e.",lifecycleCheckUnknown:"Aucun cycle de version ne correspond \xE0 {version}.",lifecycleUpdate:"La derni\xE8re version de {cycle} est {latest}.",lifecycleShowEnded:"Afficher {count} termin\xE9es",lifecycleCopyCsv:"Copier en CSV",lifecycleEmpty:"Aucun cycle de version.",lifecycleShape:"Du JSON d\u2019endoflife.date, ou une liste de cycles de version, est attendu."};J({en:le,fr:se});var de=["table","schedule"],ue=864e5,re=365.25*ue,ae=class extends X{static type="lifecycle";static componentAttributes=Object.freeze(["version","view","ended","now","tabs"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,download:!0,fullscreen:!0,tabs:!0}};static styles=[F,L,Z,H,Q];constructor(){super(),this.panelId=R("panel"),this.viewChoice=null,this.showAll=!1}attributeChangedCallback(t,l,a){t==="view"&&(this.viewChoice=null),super.attributeChangedCallback(t,l,a)}read(){try{return{...ee(JSON.parse(this.text??"")),error:null}}catch(t){let l=t instanceof _?this.t("lifecycleShape"):this.t("jsonInvalid",{message:t instanceof Error?t.message:""});return{name:"",cycles:[],error:l}}}get cycles(){return this.read().cycles}get view(){return this.viewChoice??I(this.getAttribute("view"),de,"table")}day(t){return t===null?"":this.formatDate(t,{dateStyle:"medium",timeZone:"UTC"})}renderContent(t){let l=this.t,{cycles:a,error:s}=this.read(),n=this.now,o=r("div",{class:"body data-body lc-body",part:"body"}),i=this.getAttribute("version")?.trim()??"",d=i?te(a,i):null;if(s)o.append(G(s));else if(!a.length)o.append(r("p",{class:"data-none",text:l("lifecycleEmpty")}));else{i&&o.append(this.checkView(i,d,n));let u=this.shownCycles(a,n,d);o.append(this.view==="schedule"?this.scheduleView(u,n,d):this.tableView(u,n,d));let b=a.length-u.length;b>0&&o.append(this.moreButton(b))}let p=this.feature("tabs")&&a.length?W({tabs:[{id:"table",label:l("lifecycleTable"),icon:"table"},{id:"schedule",label:l("lifecycleSchedule"),icon:"calendar"}],selected:this.view,label:l("tabs"),panelId:this.panelId,onSelect:u=>{this.viewChoice=u,this.render(),this.root.querySelector(`[data-tab="${u}"]`)?.focus(),P(this,q.TAB_CHANGE,{tab:u})}}):null,{panel:h,history:y}=this.previewPanel(o,this.panelId);p&&h.setAttribute("role","tabpanel");let w=a.filter(u=>!["eol","upcoming"].includes(f(u,n))).length,v=()=>this.toCsv(a,n);t.append(...this.chrome({badge:a.length?l("lifecycleSupported",{count:V(w,this.locale)}):"",tabs:p,actions:[...y,this.editToggleButton(),this.fullscreenButton(),this.feature("download")&&a.length?this.downloadButton(v,this.downloadName("lifecycle.csv"),"text/csv"):null,this.feature("copy")&&a.length?this.copyButton(v,l("lifecycleCopyCsv")):null]}),h),this.editor?.align()}shownCycles(t,l,a){if(this.showAll)return t;let s=Y(this.getAttribute("ended"),{min:0,max:1e3,fallback:3});return t.filter(n=>f(n,l)!=="eol"||n===a?!0:(s-=1,s>=0))}moreButton(t){return r("button",{class:"text-btn lc-more",text:this.t("lifecycleShowEnded",{count:V(t,this.locale)}),attrs:{type:"button","data-focus-key":"more"},on:{click:()=>{this.showAll=!0,this.render()}}})}statusChip(t){return r("span",{class:`lc-status s-${t}`,part:"status",text:this.t(`lifecycleStatus_${t}`)})}checkView(t,l,a){let s=this.t,n=r("div",{class:"lc-check",part:"check",attrs:{role:"note"}});if(!l)return n.classList.add("s-unknown"),n.append(r("p",{text:s("lifecycleCheckUnknown",{version:t})})),n;let o=f(l,a);n.classList.add(`s-${o}`);let i=o==="active"?l.activeEnd??l.eol:o==="upcoming"?l.released:l.eol,p=`lifecycleCheck_${o}${i===null&&(o==="active"||o==="eol")?"Open":""}`;return n.append(this.statusChip(o),r("p",{text:s(p,{version:t,cycle:l.name,date:this.day(i),until:this.day(l.extendedEnd)})})),l.latest&&l.latest.replace(/^v/i,"")!==t.replace(/^v/i,"")&&n.append(r("p",{class:"lc-update",text:s("lifecycleUpdate",{cycle:l.name,latest:l.latest})})),n}nameView(t){return r("span",{class:"lc-name"},r("strong",{text:t.label&&t.label!==t.name?t.label:t.name}),t.lts?r("span",{class:"lc-lts",text:this.t("lifecycleLts")}):null,t.codename?r("span",{class:"lc-codename",text:t.codename}):null)}endText(t,l,a){let s=this.t;return t===null?a===null?"":s(a?"lifecycleNo":"lifecycleYes"):s(t<=l?"lifecycleEnded":"lifecycleUntil",{date:this.day(t)})}tableView(t,l,a){let s=this.t,n=r("tr",{},...["lifecycleVersion","lifecycleStatus","lifecycleReleased","lifecycleActive","lifecycleSecurity","lifecycleLatest"].map(i=>r("th",{attrs:{scope:"col"},text:s(i)}))),o=r("tbody");for(let i of t){let d=f(i,l),p=i.eol===null?i.ended?!0:i.supported?!1:null:null;o.append(r("tr",{class:`s-${d}${i===a?" lc-mine":""}`,attrs:{"aria-current":i===a?"true":null}},r("th",{attrs:{scope:"row"}},this.nameView(i)),r("td",{},this.statusChip(d)),r("td",{text:this.day(i.released)}),r("td",{text:this.endText(i.activeEnd,l,null)}),r("td",{text:this.endText(i.eol,l,p)}),r("td",{},i.latest?i.link?r("a",{text:i.latest,attrs:{href:i.link,rel:"noopener"}}):i.latest:"")))}return r("div",{class:"lc-wrap",attrs:{tabindex:"0",role:"region","aria-label":s("lifecycleTable")}},r("table",{class:"grid lc-table",part:"table"},r("thead",{},n),o))}scheduleView(t,l,a){let s=this.t,n=t.map(c=>c.released??l),o=t.map(c=>Math.max(c.extendedEnd??0,c.eol??0,c.activeEnd??0,c.released??0)),i=Math.min(l-re,...n),d=Math.max(l+re,...o),p=d-i,h=c=>`${((c-i)/p*100).toFixed(3)}%`,y=r("div",{class:"lc-ruler",attrs:{"aria-hidden":"true"}}),w=new Date(i).getUTCFullYear()+1,v=new Date(d).getUTCFullYear(),u=Math.max(1,Math.ceil((v-w+1)/12));for(let c=w;c<=v;c+=u){let m=r("span",{class:"lc-tick",text:String(c)});m.style.setProperty("--_at",h(Date.UTC(c,0,1))),y.append(m)}let b=r("span",{class:"lc-today",attrs:{title:s("lifecycleToday")}});b.style.setProperty("--_at",h(l)),y.append(b);let N=r("ol",{class:"lc-rows"});for(let c of t){let m=f(c,l),U=r("div",{class:"lc-track",attrs:{"aria-hidden":"true"}}),j=c.released??l,S=c.eol??(c.ended?j:d),C=(D,E,T)=>{if(T<=E)return;let A=r("span",{class:`lc-bar b-${D}${c.eol===null&&!c.ended&&D!=="extended"&&T===d?" open":""}`});A.style.setProperty("--_start",h(E)),A.style.setProperty("--_width",`${((T-E)/p*100).toFixed(3)}%`),U.append(A)},z=c.activeEnd!==null?Math.min(c.activeEnd,S):S;C("active",j,z),C("security",z,S),c.extendedEnd!==null&&C("extended",S,c.extendedEnd);let ne=[s("lifecycleRow",{cycle:c.name,status:s(`lifecycleStatus_${m}`)}),c.released!==null?`${s("lifecycleReleased")}: ${this.day(c.released)}.`:"",c.activeEnd!==null?`${s("lifecycleActive")}: ${this.endText(c.activeEnd,l,null)}.`:"",c.eol!==null?`${s("lifecycleSecurity")}: ${this.endText(c.eol,l,null)}.`:""].filter(Boolean);N.append(r("li",{class:`lc-row s-${m}${c===a?" lc-mine":""}`},r("span",{class:"lc-label",attrs:{"aria-hidden":"true"}},this.nameView(c)),r("span",{class:"sr-only",text:ne.join(" ")}),U))}let ce=r("p",{class:"lc-legend",attrs:{"aria-hidden":"true"}},...["active","security","extended"].map(c=>r("span",{class:`lc-key b-${c}`,text:s(`lifecycleStatus_${c}`)})));return r("div",{class:"lc-schedule",part:"schedule"},y,N,ce)}toCsv(t,l){let a=s=>s===null?"":new Date(s).toISOString().slice(0,10);return K([["version","status","lts","released","active_support","security_support","extended_support","latest"],...t.map(s=>[s.name,f(s,l),s.lts?"yes":"no",a(s.released),a(s.activeEnd),a(s.eol),a(s.extendedEnd),s.latest])])}};export{ae as a};
