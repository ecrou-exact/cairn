/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as L}from"./chunk-NPDHR5SA.js";import{a as M}from"./chunk-BNQD3D4I.js";import{O as S,_ as A,b as O,c as B,d as b,o as r,q as N,s as P,y as z,z as R}from"./chunk-7PAHM2BV.js";import{h as E,k as w,l as y,m as U}from"./chunk-TUK22DTT.js";var $=`/*\r
 * Status page: an overall banner, incidents, and components with a bar per day.\r
 * States are always shown with a word and an icon, and the bars of a bad day are taller.\r
 */\r
.status-body {\r
  display: grid;\r
  gap: var(--_space-5);\r
  padding: var(--_space-4) var(--_space-5);\r
  background: var(--_surface);\r
  overscroll-behavior: auto;\r
}\r
\r
:host([max-height]) .status-body,\r
.vt[data-fullscreen] .status-body {\r
  overscroll-behavior: contain;\r
}\r
\r
.data-edit > .editor-body {\r
  max-height: min(40vh, 320px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
/* ---------- Tones ---------- */\r
\r
.tone-operational {\r
  --_tone: var(--_success);\r
}\r
\r
.tone-degraded,\r
.tone-partial {\r
  --_tone: var(--_warning);\r
}\r
\r
.tone-major {\r
  --_tone: var(--_danger);\r
}\r
\r
.tone-maintenance {\r
  --_tone: var(--_info);\r
}\r
\r
.tone-unknown,\r
.tone-resolved,\r
.tone-none {\r
  --_tone: var(--_fg-muted);\r
}\r
\r
/* ---------- Banner ---------- */\r
\r
.status-banner {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  gap: var(--_space-3);\r
  padding: var(--_space-3) var(--_space-4);\r
  border: 1px solid color-mix(in srgb, var(--_tone) 45%, var(--_border));\r
  border-radius: var(--_radius-sm);\r
  background: color-mix(in srgb, var(--_tone) 9%, var(--_surface));\r
  color: var(--_fg);\r
}\r
\r
.status-banner > .icon {\r
  flex: none;\r
  width: 22px;\r
  height: 22px;\r
  color: var(--_tone);\r
}\r
\r
.status-banner-text {\r
  flex: 1 1 200px;\r
  min-width: 0;\r
}\r
\r
.status-banner-title {\r
  margin: 0;\r
  font: 600 16px / 1.3 var(--_font-ui);\r
}\r
\r
.status-banner-text p {\r
  margin: 2px 0 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.45 var(--_font-ui);\r
}\r
\r
.status-updated {\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.3 var(--_font-ui);\r
}\r
\r
/* ---------- Sections ---------- */\r
\r
.status-section {\r
  display: grid;\r
  gap: var(--_space-3);\r
  min-width: 0;\r
}\r
\r
.status-group {\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
}\r
\r
.status-title {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 600 var(--_font-size-small) / 1.3 var(--_font-ui);\r
  letter-spacing: 0.04em;\r
  text-transform: uppercase;\r
}\r
\r
.status-none {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.45 var(--_font-ui);\r
}\r
\r
.status-more {\r
  justify-self: start;\r
}\r
\r
/* ---------- Components ---------- */\r
\r
.status-components {\r
  margin: 0;\r
  padding: 0;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  list-style: none;\r
}\r
\r
.status-component {\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
  padding: var(--_space-3);\r
}\r
\r
.status-component + .status-component {\r
  border-top: 1px solid var(--_border);\r
}\r
\r
.status-component-head {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: baseline;\r
  justify-content: space-between;\r
  gap: var(--_space-1) var(--_space-3);\r
}\r
\r
.status-name {\r
  min-width: 0;\r
  color: var(--_fg);\r
  font: 500 14px / 1.4 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
.status-name a,\r
.status-link {\r
  color: var(--_accent-fg);\r
}\r
\r
.status-description {\r
  margin: 2px 0 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
.status-state {\r
  display: inline-flex;\r
  flex: none;\r
  align-items: center;\r
  gap: 5px;\r
  color: var(--_tone);\r
  font: 600 var(--_font-size-small) / 1.3 var(--_font-ui);\r
}\r
\r
.status-state .icon {\r
  width: 14px;\r
  height: 14px;\r
}\r
\r
/* ---------- Days ---------- */\r
\r
.status-days {\r
  display: flex;\r
  align-items: flex-end;\r
  gap: 1px;\r
  height: 28px;\r
  border-radius: 2px;\r
  cursor: default;\r
  touch-action: pan-y;\r
}\r
\r
.status-days:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.status-day {\r
  flex: 1 1 0;\r
  min-width: 0;\r
  height: 100%;\r
  border-radius: 1px;\r
  background: var(--_tone);\r
}\r
\r
.status-day.tone-operational {\r
  height: 62%;\r
}\r
\r
.status-day.tone-none {\r
  height: 62%;\r
  background: var(--_border-strong);\r
}\r
\r
.status-day.current {\r
  outline: 1px solid var(--_fg);\r
}\r
\r
.status-days-foot {\r
  display: flex;\r
  justify-content: space-between;\r
  gap: var(--_space-3);\r
  margin-top: var(--_space-1);\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
.status-days-foot > span:first-child,\r
.status-days-foot > span:last-child {\r
  flex: none;\r
}\r
\r
.status-day-info {\r
  min-width: 0;\r
  color: var(--_fg);\r
  text-align: center;\r
  overflow-wrap: anywhere;\r
}\r
\r
/* ---------- Incidents ---------- */\r
\r
.status-incident {\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
  padding: var(--_space-3);\r
  border: 1px solid var(--_border);\r
  border-left: 3px solid var(--_tone);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
.status-incident-head {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: baseline;\r
  justify-content: space-between;\r
  gap: var(--_space-1) var(--_space-3);\r
}\r
\r
.status-incident h4 {\r
  margin: 0;\r
  color: var(--_fg);\r
  font: 600 14px / 1.4 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
.status-tag {\r
  flex: none;\r
  color: var(--_fg-muted);\r
  font: 600 var(--_font-size-small) / 1.3 var(--_font-ui);\r
}\r
\r
.status-facts {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.45 var(--_font-ui);\r
}\r
\r
.status-updates {\r
  display: grid;\r
  gap: var(--_space-2);\r
  margin: 0;\r
  padding: 0 0 0 var(--_space-3);\r
  border-left: 1px solid var(--_border);\r
  list-style: none;\r
}\r
\r
.status-update-head {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: baseline;\r
  gap: var(--_space-2);\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
.status-update-head time {\r
  color: var(--_fg-muted);\r
}\r
\r
.status-update p {\r
  margin: 2px 0 0;\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-ui) / 1.5 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
  white-space: pre-wrap;\r
}\r
\r
.status-link {\r
  justify-self: start;\r
  font: 500 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
`;var h=Object.freeze({components:200,incidents:200,updates:50,history:1e3,days:365,text:4e3}),at=864e5,nt=864e13,H={operational:"operational",ok:"operational",up:"operational",none:"operational",degraded:"degraded",degraded_performance:"degraded",minor:"degraded",partial:"partial",partial_outage:"partial",major:"major",major_outage:"major",outage:"major",down:"major",critical:"major",maintenance:"maintenance",under_maintenance:"maintenance"},J=["unknown","operational","maintenance","degraded","partial","major"],V={none:"operational",minor:"degraded",major:"partial",critical:"major"},f=e=>typeof e=="object"&&e!==null&&!Array.isArray(e);function u(e,t=h.text){return typeof e=="number"?String(e):typeof e=="string"?e.trim().slice(0,t):""}function x(e){let t=u(e,40).toLowerCase().replace(/[\s-]+/g,"_");return Object.hasOwn(H,t)?H[t]:"unknown"}function j(e){let t=u(e,2e3);return t&&P(t)?t:null}function g(e){if(typeof e=="number"&&Number.isFinite(e)){let s=Math.abs(e)>1e11?e:e*1e3;return Math.abs(s)<=nt?s:null}if(typeof e!="string")return null;let t=Date.parse(e);return Number.isNaN(t)?null:t}function I(e){return new Date(e).toISOString().slice(0,10)}function q(e){let t=g(e);return t===null?null:I(t)}function rt(e){let t=[];Array.isArray(e)?t=e:f(e)&&(t=Object.entries(e).map(([a,n])=>f(n)?{...n,date:a}:{date:a,status:n}));let s=new Map;for(let a of t.slice(0,h.history)){if(!f(a))continue;let n=q(a.date);if(!n)continue;let i=Number(a.minutes);s.set(n,{state:x(a.status??a.state),minutes:a.minutes!==void 0&&i>=0?i:null,note:u(a.note,300)})}return s}function it(e,t){let s=Number(e.uptime);return{name:u(e.name,200),description:u(e.description,500),group:u(e.group,200)||t,state:x(e.status??e.state),url:j(e.url),uptime:e.uptime!==void 0&&s>=0&&s<=100?s:null,since:q(e.since),history:rt(e.history)}}function ot(e){if(!Array.isArray(e))return[];let t=e.filter(f),s=new Map(t.filter(a=>a.group===!0).map(a=>[a.id,u(a.name)]));return t.filter(a=>a.group!==!0).slice(0,h.components).map(a=>it(a,s.get(a.group_id)??"")).filter(a=>a.name)}function Y(e){let t=u(e,40).toLowerCase();return Object.hasOwn(V,t)?V[t]:x(t)}function ut(e){return Array.isArray(e)?e.filter(f).slice(0,h.updates).map(t=>({time:g(t.time??t.display_at??t.created_at),state:u(t.status??t.state,40).toLowerCase(),text:u(t.text??t.body)})).sort((t,s)=>(s.time??0)-(t.time??0)):[]}function lt(e){let t=Array.isArray(e.components)?e.components:[];return{title:u(e.title??e.name,300),state:u(e.status??e.state,40).toLowerCase(),impact:Y(e.impact),start:g(e.start??e.started??e.scheduled_for??e.created_at),end:g(e.end??e.resolved??e.scheduled_until??e.resolved_at),url:j(e.url??e.shortlink),components:t.slice(0,h.components).map(s=>u(f(s)?s.name:s,200)).filter(Boolean),updates:ut(e.updates??e.incident_updates)}}function F(e){return Array.isArray(e)?e.filter(f).slice(0,h.incidents).map(lt).filter(t=>t.title):[]}function ct(e){if(e==null)return null;let t=f(e)?Y(e.indicator):x(e);return t==="unknown"?null:t}function k(e){let t;try{t=JSON.parse(e)}catch(a){return{ok:!1,error:"json",message:a instanceof Error?a.message:""}}if(Array.isArray(t)&&(t={components:t}),!f(t)||!(Array.isArray(t.components)||Array.isArray(t.services)))return{ok:!1,error:"shape",message:""};let s=f(t.page)?t.page:{};return{ok:!0,page:{title:u(t.title??s.name,200),url:j(t.url??s.url),updated:g(t.updated??s.updated_at),state:ct(t.status),message:u(t.message??(f(t.status)?t.status.description:"")),components:ot(t.components??t.services),incidents:F(t.incidents).sort((a,n)=>(n.start??0)-(a.start??0)),maintenances:F(t.maintenances??t.scheduled_maintenances).sort((a,n)=>(a.start??0)-(n.start??0))}}}function dt(e){return e.reduce((t,s)=>J.indexOf(s)>J.indexOf(t)?s:t,"unknown")}function v(e){return e.end===null&&!["resolved","postmortem","completed"].includes(e.state)}function C(e,t){return e.state==="completed"||e.end!==null&&e.end<=t?"past":e.state==="in_progress"?"active":e.start!==null&&e.start>t?"upcoming":"active"}function D(e,t){return e.state?e.state:dt([...e.components.map(s=>s.state),...e.incidents.filter(v).map(s=>s.impact),...e.maintenances.filter(s=>C(s,t)==="active").map(()=>"maintenance")])}function Z(e,t,s){let a=I(s),n=[];for(let i=t-1;i>=0;i--){let o=I(s-i*at),l=e.history.get(o),d="none";e.since&&o>=e.since&&(d=o===a?e.state:"operational"),n.push(l?{date:o,...l}:{date:o,state:d,minutes:null,note:""})}return n}function pt(e){return e.state==="none"||e.state==="unknown"||e.state==="maintenance"?null:e.minutes!==null?Math.max(0,1-e.minutes/1440):e.state==="major"?0:e.state==="partial"?.7:1}function G(e,t){if(e.uptime!==null)return e.uptime;let s=t.map(pt).filter(a=>a!==null);return s.length?s.reduce((a,n)=>a+n,0)/s.length*100:null}var X=Object.freeze({statusBanner_operational:"All systems operational",statusBanner_degraded:"Degraded performance",statusBanner_partial:"Partial outage",statusBanner_major:"Major outage",statusBanner_maintenance:"Maintenance in progress",statusBanner_unknown:"Status unknown",statusState_operational:"Operational",statusState_degraded:"Degraded",statusState_partial:"Partial outage",statusState_major:"Major outage",statusState_maintenance:"Maintenance",statusState_unknown:"Unknown",statusState_none:"No data",statusUpdated:"Updated {relative}",statusStale:"This page could not be refreshed: it shows the last status received.",statusComponents:"Services",statusOpenIncidents:"Open incidents",statusMaintenance:"Scheduled maintenance",statusPastIncidents:"Past incidents",statusNoIncidents:"No incidents reported.",statusShowAll:"Show all {count} incidents",statusHistory:"History of {name}",statusDaysAgo:"{count} days ago",statusToday:"Today",statusUptime:"{percent} uptime",statusDowntime:"{minutes} min down",statusAffected:"Affects: {names}",statusStarts:"Starts {date}",statusEnds:"Until {date}",statusResolvedAt:"Resolved {date}",statusDetails:"Details",statusInvalidJson:"This is not valid JSON: {message}",statusInvalidShape:'A status page is an object with a "components" list.'}),K=Object.freeze({statusBanner_operational:"Tous les syst\xE8mes sont op\xE9rationnels",statusBanner_degraded:"Performances d\xE9grad\xE9es",statusBanner_partial:"Panne partielle",statusBanner_major:"Panne majeure",statusBanner_maintenance:"Maintenance en cours",statusBanner_unknown:"\xC9tat inconnu",statusState_operational:"Op\xE9rationnel",statusState_degraded:"D\xE9grad\xE9",statusState_partial:"Panne partielle",statusState_major:"Panne majeure",statusState_maintenance:"Maintenance",statusState_unknown:"Inconnu",statusState_none:"Pas de donn\xE9es",statusUpdated:"Mis \xE0 jour {relative}",statusStale:"Cette page n'a pas pu \xEAtre actualis\xE9e : elle montre le dernier \xE9tat re\xE7u.",statusComponents:"Services",statusOpenIncidents:"Incidents en cours",statusMaintenance:"Maintenance planifi\xE9e",statusPastIncidents:"Incidents pass\xE9s",statusNoIncidents:"Aucun incident signal\xE9.",statusShowAll:"Afficher les {count} incidents",statusHistory:"Historique de {name}",statusDaysAgo:"il y a {count} jours",statusToday:"Aujourd'hui",statusUptime:"{percent} de disponibilit\xE9",statusDowntime:"{minutes} min de panne",statusAffected:"Concerne : {names}",statusStarts:"D\xE9but : {date}",statusEnds:"Jusqu'au {date}",statusResolvedAt:"R\xE9solu le {date}",statusDetails:"D\xE9tails",statusInvalidJson:"Ce n'est pas du JSON valide : {message}",statusInvalidShape:"Une page de statut est un objet avec une liste \xAB components \xBB."});U({en:X,fr:K});var ft=15,Q={operational:"status-success",degraded:"alert",partial:"alert",major:"status-failure",maintenance:"status-circle",unknown:"status-circle"},W=class extends L{static type="status";static componentAttributes=Object.freeze(["days","refresh","max-incidents","bars","incidents","now"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,download:!0,fullscreen:!0}};static styles=[O,M,$];constructor(){super(),this.panelId=N("panel"),this.lastState=null,this.stale=!1,this.showAllIncidents=!1,this.refreshTimer=void 0,this.refreshAbort=null}get page(){let t=k(this.text??"");return t.ok?t.page:null}get state(){let t=this.page;return t?D(t,this.now):null}connectedCallback(){super.connectedCallback(),this.startRefresh()}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.refreshTimer),this.refreshAbort?.abort(),this.refreshAbort=null}attributeChangedCallback(t,s,a){super.attributeChangedCallback(t,s,a),s!==a&&(t==="refresh"||t==="src")&&this.isConnected&&this.startRefresh()}startRefresh(){clearInterval(this.refreshTimer),this.refreshAbort?.abort();let t=b(this.getAttribute("refresh"),{min:ft,max:86400,fallback:0});t&&this.getAttribute("src")?.trim()&&(this.refreshTimer=setInterval(()=>this.refresh(),t*1e3))}async refresh(){let t=this.getAttribute("src")?.trim();if(!t||this._content!==void 0||this.editing||document.hidden)return;this.refreshAbort?.abort();let s=new AbortController;this.refreshAbort=s;let a=E();try{let n=await z(t,{allowRemote:B(this.getAttribute("allow-remote"))===!0,maxSize:a.maxSize,timeout:a.fetchTimeout,signal:s.signal});this.stale=!1,n.replace(/\r\n?/g,`
`)!==this.text?this.setText(n):this.requestRender()}catch(n){if(R(n))return;this.stale=!0,this.requestRender(),y(this,w.ERROR,{message:this.t("statusStale"),cause:n})}}renderContent(t){let s=this.t,a=k(this.text??""),n=r("div",{class:"body status-body",part:"body"}),i="JSON";if(a.ok){let d=D(a.page,this.now);i=s(`statusState_${d}`),this.noteState(d),this.stale&&n.append(A(s("statusStale"))),n.append(this.banner(a.page,d)),this.flag("incidents")&&n.append(...this.openSections(a.page)),n.append(this.componentList(a.page)),this.flag("incidents")&&n.append(this.pastIncidents(a.page))}else n.append(A(a.error==="json"?s("statusInvalidJson",{message:a.message}):s("statusInvalidShape")));let{panel:o,history:l}=this.previewPanel(n,this.panelId);t.append(...this.chrome({badge:i,actions:[...l,this.editToggleButton(),this.fullscreenButton(),this.feature("download")?this.downloadButton(()=>this.text??"",this.downloadName("status.json"),"application/json"):null,this.feature("copy")?this.copyButton(()=>this.text??""):null]}),o),this.editor?.align()}noteState(t){let s=this.lastState;this.lastState=t,!(s===null||s===t)&&(this.announce(this.t(`statusBanner_${t}`)),y(this,w.STATUS_CHANGE,{status:t,previous:s}))}banner(t,s){let a=this.t,n=a(`statusBanner_${s}`);return r("div",{class:`status-banner tone-${s}`,part:"banner"},S(Q[s]),r("div",{class:"status-banner-text"},r("h3",{class:"status-banner-title",text:n}),t.message?r("p",{text:t.message}):null),t.updated!==null?r("time",{class:"status-updated",text:a("statusUpdated",{relative:this.relativeTime(t.updated)}),attrs:{datetime:new Date(t.updated).toISOString()}}):null)}openSections(t){let s=this.now,a=t.incidents.filter(v),n=t.maintenances.filter(i=>C(i,s)!=="past");return[a.length?this.section("statusOpenIncidents",a):null,n.length?this.section("statusMaintenance",n,!0):null].filter(i=>i!==null)}section(t,s,a=!1){return r("section",{class:"status-section",attrs:{"aria-label":this.t(t)}},r("h3",{class:"status-title",text:this.t(t)}),...s.map(n=>this.incidentView(n,a)))}pastIncidents(t){let s=this.t,a=t.incidents.filter(l=>!v(l)),n=b(this.getAttribute("max-incidents"),{min:0,max:h.incidents,fallback:5}),i=this.showAllIncidents?a:a.slice(0,n),o=r("section",{class:"status-section",attrs:{"aria-label":s("statusPastIncidents")}},r("h3",{class:"status-title",text:s("statusPastIncidents")}),...i.map(l=>this.incidentView(l)));return a.length||o.append(r("p",{class:"status-none",text:s("statusNoIncidents")})),i.length<a.length&&o.append(r("button",{class:"text-btn status-more",text:s("statusShowAll",{count:a.length}),attrs:{type:"button","data-focus-key":"show-all"},on:{click:()=>{this.showAllIncidents=!0,this.render()}}})),o}incidentView(t,s=!1){let a=this.t,n=s?"maintenance":v(t)?t.impact:"resolved",i=this.incidentFacts(t,s);return r("article",{class:`status-incident tone-${n}`,part:"incident"},r("div",{class:"status-incident-head"},r("h4",{text:t.title}),t.state?r("span",{class:"status-tag",text:tt(t.state)}):null),i.length?r("p",{class:"status-facts",text:i.join(" \xB7 ")}):null,t.components.length?r("p",{class:"status-facts",text:a("statusAffected",{names:t.components.join(", ")})}):null,t.updates.length?r("ol",{class:"status-updates"},...t.updates.map(o=>this.updateView(o))):null,t.url?et(t.url,a("statusDetails"),"status-link"):null)}incidentFacts(t,s){let a=this.t,n=[];if(t.start!==null){let i=this.formatDate(t.start);n.push(s?a("statusStarts",{date:i}):i)}if(t.end!==null){let i=this.formatDate(t.end);n.push(a(s?"statusEnds":"statusResolvedAt",{date:i}))}return n}updateView(t){return r("li",{class:"status-update",part:"update"},r("div",{class:"status-update-head"},t.state?r("strong",{text:tt(t.state)}):null,t.time!==null?r("time",{text:this.formatDate(t.time),attrs:{datetime:new Date(t.time).toISOString()}}):null),t.text?r("p",{text:t.text}):null)}componentList(t){let s=new Map;for(let i of t.components){let o=s.get(i.group);o?o.push(i):s.set(i.group,[i])}let a=0,n=r("section",{class:"status-section",attrs:{"aria-label":this.t("statusComponents")}});for(let[i,o]of s)n.append(r("div",{class:"status-group",part:"group"},i?r("h3",{class:"status-title",text:i}):null,r("ul",{class:"status-components"},...o.map(l=>this.componentView(l,a++)))));return n}componentView(t,s){let a=b(this.getAttribute("days"),{min:1,max:h.days,fallback:90}),n=this.flag("bars");return r("li",{class:"status-component",part:"component"},r("div",{class:"status-component-head"},r("div",{class:"status-name"},t.url?et(t.url,t.name):r("span",{text:t.name}),t.description?r("p",{class:"status-description",text:t.description}):null),r("span",{class:`status-state tone-${t.state}`},S(Q[t.state]),this.t(`statusState_${t.state}`))),n?this.dayBars(t,Z(t,a,this.now),s):null)}dayBars(t,s,a){let n=this.t,i=G(t,s),o=i===null?"":n("statusUptime",{percent:this.percent(i)}),l=r("span",{class:"status-day-info",part:"uptime",text:o}),d=s.length-1,p=r("div",{class:"status-days",part:"days",attrs:{role:"slider",tabindex:"0","data-focus-key":`days-${a}`,"aria-label":n("statusHistory",{name:t.name}),"aria-valuemin":"0","aria-valuemax":String(s.length-1),"aria-valuenow":String(d),"aria-valuetext":this.dayText(s[d])}},...s.map((c,m)=>r("span",{class:`status-day tone-${c.state}`,part:"day",attrs:{"data-index":String(m)}}))),_=c=>{d=c,p.setAttribute("aria-valuenow",String(c)),p.setAttribute("aria-valuetext",this.dayText(s[c])),l.textContent=this.dayText(s[c]);for(let m of p.children)m.classList.remove("current");p.children[c].classList.add("current")},T=()=>{l.textContent=o;for(let c of p.children)c.classList.remove("current")};return p.addEventListener("pointermove",c=>{let m=c.target;m.dataset.index&&_(Number(m.dataset.index))}),p.addEventListener("pointerleave",()=>{this.root.activeElement===p?_(d):T()}),p.addEventListener("focus",()=>_(d)),p.addEventListener("blur",T),p.addEventListener("keydown",c=>{let m=mt(c.key,d,s.length);m!==null&&(c.preventDefault(),_(m))}),r("div",{class:"status-history"},p,r("div",{class:"status-days-foot"},r("span",{text:n("statusDaysAgo",{count:s.length})}),l,r("span",{text:n("statusToday")})))}dayText(t){let s=this.t;return[this.formatDate(Date.parse(`${t.date}T00:00:00Z`),{dateStyle:"medium",timeZone:"UTC"}),s(`statusState_${t.state}`),t.minutes?s("statusDowntime",{minutes:t.minutes}):"",t.note].filter(Boolean).join(" \xB7 ")}percent(t){let s=Math.floor(t*100)/1e4;try{return new Intl.NumberFormat(this.locale,{style:"percent",maximumFractionDigits:2}).format(s)}catch{return`${s*100}%`}}};function mt(e,t,s){return e==="ArrowLeft"||e==="ArrowDown"?Math.max(0,t-1):e==="ArrowRight"||e==="ArrowUp"?Math.min(s-1,t+1):e==="PageDown"?Math.max(0,t-7):e==="PageUp"?Math.min(s-1,t+7):e==="Home"?0:e==="End"?s-1:null}function tt(e){let t=e.replace(/_/g," ");return t.charAt(0).toUpperCase()+t.slice(1)}function et(e,t,s){return r("a",{class:s,text:t,attrs:{href:e,rel:"noopener noreferrer"}})}export{W as a};
