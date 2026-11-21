/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as F,c as P,d as f,e as k,f as g,g as p,h as b,i as B,k as w}from"./chunk-4SPGN4DN.js";import{c as m,d as V,e as j}from"./chunk-IQIQ3QVD.js";import{a as L}from"./chunk-NPDHR5SA.js";import{a as C}from"./chunk-BNQD3D4I.js";import{O as Z,W as _,X as O,_ as D,b as A,d as v,e as E,k as M,n as I,o as r,q as $}from"./chunk-7PAHM2BV.js";import{k as y,l as x,m as z}from"./chunk-TUK22DTT.js";var J=`/*\r
 * Calendar: a month grid or an agenda, then the events of the selected day. On narrow\r
 * elements the events of a day become dots and the day list carries the text.\r
 */\r
.calendar-body {\r
  display: grid;\r
  gap: var(--_space-4);\r
  padding: var(--_space-4) var(--_space-5);\r
  background: var(--_surface);\r
  container-type: inline-size;\r
  overscroll-behavior: auto;\r
}\r
\r
:host([max-height]) .calendar-body,\r
.vt[data-fullscreen] .calendar-body {\r
  overscroll-behavior: contain;\r
}\r
\r
.data-edit > .editor-body {\r
  max-height: min(40vh, 320px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
/* ---------- Navigation ---------- */\r
\r
.calendar-nav {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  justify-content: space-between;\r
  gap: var(--_space-2) var(--_space-3);\r
}\r
\r
.calendar-period {\r
  margin: 0;\r
  color: var(--_fg);\r
  font: 600 16px / 1.3 var(--_font-ui);\r
}\r
\r
.calendar-buttons {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-1);\r
}\r
\r
/* ---------- Month grid ---------- */\r
\r
.calendar-grid {\r
  width: 100%;\r
  border-collapse: collapse;\r
  table-layout: fixed;\r
}\r
\r
.calendar-grid th {\r
  padding: var(--_space-1);\r
  color: var(--_fg-muted);\r
  font: 600 var(--_font-size-small) / 1.3 var(--_font-ui);\r
  text-align: left;\r
}\r
\r
.calendar-day {\r
  height: 88px;\r
  padding: var(--_space-1);\r
  border: 1px solid var(--_border);\r
  overflow: hidden;\r
  cursor: pointer;\r
  vertical-align: top;\r
}\r
\r
.calendar-day:hover {\r
  background: var(--_accent-soft);\r
}\r
\r
.calendar-day:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: -2px;\r
}\r
\r
.calendar-day.outside {\r
  background: var(--_surface-sunken);\r
}\r
\r
.calendar-day.selected {\r
  box-shadow: inset 0 0 0 2px var(--_accent);\r
}\r
\r
.calendar-number {\r
  display: inline-grid;\r
  place-items: center;\r
  min-width: 22px;\r
  height: 22px;\r
  border-radius: var(--_radius-full);\r
  color: var(--_fg);\r
  font: 500 var(--_font-size-small) / 1 var(--_font-ui);\r
}\r
\r
.calendar-day.outside .calendar-number {\r
  color: var(--_fg-muted);\r
}\r
\r
.calendar-day.today .calendar-number {\r
  background: var(--_accent);\r
  color: var(--_on-accent);\r
  font-weight: 700;\r
}\r
\r
.calendar-chips {\r
  display: grid;\r
  gap: 2px;\r
  margin-top: 2px;\r
}\r
\r
.calendar-chip {\r
  display: flex;\r
  gap: 4px;\r
  min-width: 0;\r
  padding: 1px 4px;\r
  border-radius: 3px;\r
  background: var(--_accent-soft);\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-small) / 1.35 var(--_font-ui);\r
  white-space: nowrap;\r
}\r
\r
.calendar-chip.all-day {\r
  background: var(--_accent);\r
  color: var(--_on-accent);\r
}\r
\r
.calendar-chip.cancelled {\r
  background: transparent;\r
  color: var(--_fg-muted);\r
  text-decoration: line-through;\r
}\r
\r
.calendar-chip-time {\r
  flex: none;\r
  color: var(--_fg-muted);\r
}\r
\r
.calendar-chip-title {\r
  min-width: 0;\r
  overflow: hidden;\r
  text-overflow: ellipsis;\r
}\r
\r
.calendar-more {\r
  padding: 0 4px;\r
  color: var(--_fg-muted);\r
  font: 500 var(--_font-size-small) / 1.3 var(--_font-ui);\r
}\r
\r
@container (max-width: 560px) {\r
  .calendar-day {\r
    height: 52px;\r
    text-align: center;\r
  }\r
\r
  .calendar-grid th {\r
    text-align: center;\r
  }\r
\r
  .calendar-chips {\r
    display: flex;\r
    flex-wrap: wrap;\r
    justify-content: center;\r
    gap: 2px;\r
  }\r
\r
  .calendar-chip {\r
    width: 6px;\r
    height: 6px;\r
    padding: 0;\r
    border-radius: var(--_radius-full);\r
    background: var(--_accent-fg);\r
  }\r
\r
  .calendar-chip.cancelled {\r
    background: var(--_fg-muted);\r
  }\r
\r
  .calendar-chip-time,\r
  .calendar-chip-title,\r
  .calendar-more {\r
    display: none;\r
  }\r
}\r
\r
/* ---------- Lists ---------- */\r
\r
.calendar-list {\r
  display: grid;\r
  gap: var(--_space-3);\r
  min-width: 0;\r
}\r
\r
.calendar-agenda-day {\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
}\r
\r
.calendar-day-title {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 600 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.calendar-none,\r
.calendar-zone {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.45 var(--_font-ui);\r
}\r
\r
.calendar-show-more {\r
  justify-self: start;\r
}\r
\r
.calendar-events {\r
  margin: 0;\r
  padding: 0;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  list-style: none;\r
}\r
\r
.calendar-event + .calendar-event {\r
  border-top: 1px solid var(--_border);\r
}\r
\r
.calendar-event-toggle {\r
  display: grid;\r
  grid-template-columns: minmax(84px, 130px) minmax(0, 1fr) 16px;\r
  align-items: start;\r
  gap: var(--_space-3);\r
  width: 100%;\r
  padding: var(--_space-2) var(--_space-3);\r
  border: 0;\r
  background: transparent;\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-ui) / 1.45 var(--_font-ui);\r
  text-align: left;\r
  cursor: pointer;\r
}\r
\r
.calendar-event-toggle:hover {\r
  background: var(--_accent-soft);\r
}\r
\r
.calendar-event-toggle:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: -2px;\r
}\r
\r
.calendar-event-toggle .icon {\r
  width: 16px;\r
  height: 16px;\r
  margin-top: 2px;\r
  color: var(--_fg-muted);\r
}\r
\r
.calendar-event-when {\r
  color: var(--_fg-muted);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.calendar-event-name {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: baseline;\r
  gap: 2px var(--_space-2);\r
  min-width: 0;\r
}\r
\r
.calendar-event-title {\r
  font-weight: 600;\r
  overflow-wrap: anywhere;\r
}\r
\r
.calendar-event.cancelled .calendar-event-title {\r
  color: var(--_fg-muted);\r
  text-decoration: line-through;\r
}\r
\r
.calendar-tag {\r
  color: var(--_danger);\r
  font: 600 var(--_font-size-small) / 1.3 var(--_font-ui);\r
}\r
\r
.calendar-event-place {\r
  flex-basis: 100%;\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  overflow-wrap: anywhere;\r
}\r
\r
.calendar-details {\r
  display: grid;\r
  gap: var(--_space-2);\r
  padding: 0 var(--_space-3) var(--_space-3);\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-ui) / 1.5 var(--_font-ui);\r
}\r
\r
.calendar-details p {\r
  margin: 0;\r
  overflow-wrap: anywhere;\r
}\r
\r
.calendar-range,\r
.calendar-place {\r
  color: var(--_fg-muted);\r
}\r
\r
.calendar-text {\r
  white-space: pre-wrap;\r
}\r
\r
.calendar-categories {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-1);\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.calendar-categories li {\r
  padding: 1px 8px;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-full);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.calendar-actions {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  gap: var(--_space-3);\r
}\r
\r
.calendar-link {\r
  color: var(--_accent-fg);\r
  font-weight: 500;\r
}\r
\r
@container (max-width: 420px) {\r
  .calendar-event-toggle {\r
    grid-template-columns: minmax(0, 1fr) 16px;\r
  }\r
\r
  .calendar-event-when {\r
    grid-column: 1 / -1;\r
    margin-bottom: -6px;\r
  }\r
}\r
`;var U=Object.freeze({calendarMonth:"Month",calendarAgenda:"Agenda",calendarViews:"View",calendarToday:"Today",calendarPrevious:"Previous month",calendarNext:"Next month",calendarFrom:"From {date}",calendarAllDay:"All day",calendarCancelled:"Cancelled",calendarEventCount:"{count} events",calendarOneEvent:"1 event",calendarNoEvents:"No events",calendarNoEventsMonth:"No events this month.",calendarNoEventsAhead:"No events to come.",calendarMore:"+{count} more",calendarShowMore:"Show more",calendarAdd:"Add to calendar",calendarDetails:"More information",calendarTimeZone:"Times in {zone}",calendarSkipped:"{count} events could not be read and are not shown.",calendarInvalidJson:"This is not valid JSON: {message}",calendarInvalidFormat:"A calendar is an iCalendar file, or JSON with a list of events."}),H=Object.freeze({calendarMonth:"Mois",calendarAgenda:"Agenda",calendarViews:"Vue",calendarToday:"Aujourd'hui",calendarPrevious:"Mois pr\xE9c\xE9dent",calendarNext:"Mois suivant",calendarFrom:"\xC0 partir du {date}",calendarAllDay:"Toute la journ\xE9e",calendarCancelled:"Annul\xE9",calendarEventCount:"{count} \xE9v\xE9nements",calendarOneEvent:"1 \xE9v\xE9nement",calendarNoEvents:"Aucun \xE9v\xE9nement",calendarNoEventsMonth:"Aucun \xE9v\xE9nement ce mois-ci.",calendarNoEventsAhead:"Aucun \xE9v\xE9nement \xE0 venir.",calendarMore:"+{count} autres",calendarShowMore:"Afficher plus",calendarAdd:"Ajouter \xE0 mon agenda",calendarDetails:"Plus d'informations",calendarTimeZone:"Heures en {zone}",calendarSkipped:"{count} \xE9v\xE9nements n'ont pas pu \xEAtre lus et ne sont pas affich\xE9s.",calendarInvalidJson:"Ce n'est pas du JSON valide : {message}",calendarInvalidFormat:"Un calendrier est un fichier iCalendar, ou du JSON avec une liste d'\xE9v\xE9nements."});z({en:U,fr:H});var K=["month","agenda"],N=864e5,W=366,q=class extends L{static type="calendar";static editorLanguage="plaintext";static componentAttributes=Object.freeze(["view","date","timezone","first-day","max-per-day","limit","views","add-to-calendar","now"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,download:!0,fullscreen:!0,views:!0}};static styles=[A,C,J];constructor(){super(),this.panelId=$("panel"),this.viewState=null,this.anchor=null,this.selectedDay=null,this.focusDay=null,this.openId=null,this.agendaLimit=0,this.parsed=null}contentChanged(){this.openId=null,this.agendaLimit=0}get result(){let e=this.text??"";return this.parsed?.text!==e&&(this.parsed={text:e,result:P(e)}),this.parsed.result}get calendar(){let e=this.result;return e.ok?e.calendar:null}get view(){return this.viewState??E(this.getAttribute("view"),K,"month")}get timeZone(){let e=this.getAttribute("timezone")?.trim();return e&&V(e)?e:j()}get today(){return B(this.now,this.timeZone)}get firstDay(){let e=v(this.getAttribute("first-day"),{min:0,max:6,fallback:-1});if(e>=0)return e;try{let t=new Intl.Locale(this.locale),a=t.getWeekInfo?.()??t.weekInfo;return a?a.firstDay%7:1}catch{return 1}}get anchorDay(){return this.anchor??G(this.getAttribute("date"))??this.today}attributeChangedCallback(e,t,a){e==="date"&&t!==a&&(this.anchor=null),e==="view"&&t!==a&&(this.viewState=null),super.attributeChangedCallback(e,t,a)}goTo(e){let t=G(e);t!==null&&this.moveTo(t)}moveTo(e){this.anchor=e,this.agendaLimit=0,this.render();let{year:t,month:a}=p(e);x(this,y.DATE_CHANGE,{date:`${t}-${String(a).padStart(2,"0")}`,view:this.view})}renderContent(e){let t=this.t,a=this.result,n=r("div",{class:"body calendar-body",part:"body"});if(a.ok){let{calendar:l}=a;l.skipped&&n.append(D(t("calendarSkipped",{count:l.skipped}))),n.append(this.navBar()),this.view==="month"?n.append(...this.monthView(l)):n.append(this.agendaView(l)),l.events.some(d=>!d.start.allDay)&&n.append(r("p",{class:"calendar-zone",text:t("calendarTimeZone",{zone:this.timeZone.replace(/_/g," ")})}))}else n.append(D(a.error==="json"?t("calendarInvalidJson",{message:a.message}):t("calendarInvalidFormat")));let{panel:s,history:i}=this.previewPanel(n,this.panelId);e.append(...this.chrome(this.chromeOptions(a,i)),s),this.editor?.align()}chromeOptions(e,t){let a=this.t,n=e.ok?e.calendar:null;return{badge:n?.format==="ics"?"ICS":"JSON",tabs:n&&this.feature("views")?O({tabs:[{id:"month",label:a("calendarMonth")},{id:"agenda",label:a("calendarAgenda")}],selected:this.view,label:a("calendarViews"),panelId:this.panelId,onSelect:s=>this.setView(s)}):null,actions:[...t,this.editToggleButton(),this.fullscreenButton(),this.feature("download")&&n?this.downloadButton(()=>this.icsText(n),this.downloadName("calendar.ics"),"text/calendar"):null,this.feature("copy")?this.copyButton(()=>this.text??""):null]}}icsText(e){return e.format==="ics"?this.text??"":k(e.events,Date.now())}setView(e){e!==this.view&&(this.viewState=e,this.render(),x(this,y.TAB_CHANGE,{tab:e}),this.root.querySelector(`[data-focus-key="tab-${e}"]`)?.focus())}navBar(){let e=this.t;return r("div",{class:"calendar-nav",part:"nav"},r("h3",{class:"calendar-period",part:"period",text:this.periodName()}),r("div",{class:"calendar-buttons"},r("button",{class:"text-btn",text:e("calendarToday"),attrs:{type:"button","data-focus-key":"today"},on:{click:()=>{this.focusDay=this.today,this.moveTo(this.today)}}}),_({icon:"chevron-left",label:e("calendarPrevious"),key:"previous",onClick:()=>this.moveTo(this.shifted(-1))}),_({icon:"chevron-right",label:e("calendarNext"),key:"next",onClick:()=>this.moveTo(this.shifted(1))})))}periodName(){let e=this.anchorDay;return this.view==="agenda"?this.t("calendarFrom",{date:this.dayName(e,"long")}):this.formatDate(e*N,{month:"long",year:"numeric",timeZone:"UTC"})}shifted(e){let{year:t,month:a,day:n}=p(this.anchorDay),s=t*12+a-1+e,i=Math.floor(s/12),l=s%12+1,d=this.view==="agenda"?Math.min(n,m(i,l)):1;return g(i,l,d)}monthView(e){let t=this.t,{year:a,month:n}=p(this.anchorDay),s=g(a,n,1),i=s+m(a,n)-1,l=this.firstDay,d=s-(b(s)-l+7)%7,o=i+(6-(b(i)-l+7)%7),h=w(e.events,d,o,this.timeZone),c=h.some(u=>u.endDay>=s&&u.startDay<=i);return[this.grid(h,{first:s,last:i,gridStart:d,gridEnd:o}),c?null:r("p",{class:"calendar-none",text:t("calendarNoEventsMonth")}),this.selectedDay!==null?this.dayPanel(h,this.selectedDay):null].filter(u=>u!==null)}grid(e,{first:t,last:a,gridStart:n,gridEnd:s}){let i=this.today,l=this.gridFocus(t,a,i),d=[];for(let o=n;o<=s;o+=7){let h=[];for(let c=o;c<o+7;c++){let u=e.filter(S=>S.startDay<=c&&S.endDay>=c);h.push(this.dayCell(c,u,{first:t,last:a,today:i,focus:l}))}d.push(r("tr",{},...h))}return r("table",{class:"calendar-grid",part:"grid",attrs:{role:"grid","aria-label":this.periodName()},on:{click:o=>this.gridClick(o),keydown:o=>this.gridKey(o,l)}},r("thead",{},r("tr",{},...this.weekdayHeads(n))),r("tbody",{},...d))}gridFocus(e,t,a){for(let n of[this.focusDay,this.selectedDay,a])if(n!==null&&n>=e&&n<=t)return n;return e}weekdayHeads(e){let t=[];for(let a=e;a<e+7;a++){let n=a*N;t.push(r("th",{text:this.formatDate(n,{weekday:"short",timeZone:"UTC"}),attrs:{scope:"col",abbr:this.formatDate(n,{weekday:"long",timeZone:"UTC"})}}))}return t}dayCell(e,t,{first:a,last:n,today:s,focus:i}){let l=this.t,d=v(this.getAttribute("max-per-day"),{min:0,max:20,fallback:3}),o=["calendar-day"];(e<a||e>n)&&o.push("outside"),e===s&&o.push("today"),e===this.selectedDay&&o.push("selected");let h=t.length===1?l("calendarOneEvent"):t.length?l("calendarEventCount",{count:t.length}):l("calendarNoEvents"),c=t.length-d;return r("td",{class:o.join(" "),part:"day",attrs:{role:"gridcell",tabindex:e===i?"0":"-1","data-day":String(e),"data-focus-key":`day-${e}`,"aria-selected":String(e===this.selectedDay),"aria-current":e===s?"date":null}},r("span",{class:"calendar-number",text:String(p(e).day),attrs:{"aria-hidden":"true"}}),r("span",{class:"sr-only",text:`${this.dayName(e,"full")}, ${h}`}),t.length?r("div",{class:"calendar-chips"},...t.slice(0,d).map(u=>this.chip(u,e)),c>0?r("span",{class:"calendar-more",text:l("calendarMore",{count:c})}):null):null)}chip(e,t){let a=["calendar-chip"];e.allDay&&a.push("all-day"),e.event.cancelled&&a.push("cancelled");let n=e.allDay||e.startDay!==t?"":this.timeText(e.start);return r("span",{class:a.join(" "),part:"chip",attrs:{"data-occurrence":e.id,title:e.event.title}},n?r("span",{class:"calendar-chip-time",text:n}):null,r("span",{class:"calendar-chip-title",text:e.event.title}))}gridClick(e){let t=e.target,a=t.closest("[data-day]");if(!a)return;let n=t.closest("[data-occurrence]");this.selectDay(Number(a.dataset.day),n?.dataset.occurrence??null)}gridKey(e,t){let a=e.target.closest?.("[data-day]");if(!(a instanceof HTMLElement))return;let n=Number(a.dataset.day);if(e.key==="Enter"||e.key===" "){e.preventDefault(),this.selectDay(n,null);return}let s=this.keyTarget(e.key,n);s!==null&&(e.preventDefault(),this.focusGridDay(s,t))}keyTarget(e,t){let a=(b(t)-this.firstDay+7)%7;if(e==="ArrowLeft")return t-1;if(e==="ArrowRight")return t+1;if(e==="ArrowUp")return t-7;if(e==="ArrowDown")return t+7;if(e==="Home")return t-a;if(e==="End")return t+6-a;if(e==="PageUp"||e==="PageDown"){let{year:n,month:s,day:i}=p(t),l=n*12+s-1+(e==="PageUp"?-1:1),d=Math.floor(l/12),o=l%12+1;return g(d,o,Math.min(i,m(d,o)))}return null}focusGridDay(e,t){this.focusDay=e;let a=p(this.anchorDay),n=p(e);a.year!==n.year||a.month!==n.month?this.moveTo(e):t!==void 0&&(this.root.querySelector(`[data-day="${t}"]`)?.setAttribute("tabindex","-1"),this.root.querySelector(`[data-day="${e}"]`)?.setAttribute("tabindex","0")),this.root.querySelector(`[data-day="${e}"]`)?.focus()}selectDay(e,t){this.selectedDay=e,this.focusDay=e,this.openId=t,this.render(),this.root.querySelector(`[data-day="${e}"]`)?.focus({preventScroll:!0}),t&&this.emitSelect(t)}emitSelect(e){let t=this.calendar;if(!t)return;let a=/^(\d+)-(-?\d+)$/.exec(e),n=a?t.events[Number(a[1])]:null;if(!a||!n)return;let s=Number(a[2]),[i]=w([n],s-1,s+1,this.timeZone).filter(l=>l.id===`0-${s}`);i&&x(this,y.EVENT_SELECT,{uid:n.uid,title:n.title,start:new Date(i.start).toISOString(),end:new Date(i.end).toISOString(),allDay:i.allDay,url:n.url})}dayPanel(e,t){let a=e.filter(n=>n.startDay<=t&&n.endDay>=t);return r("section",{class:"calendar-list",part:"agenda",attrs:{"aria-label":this.dayName(t,"full")}},r("h4",{class:"calendar-day-title",text:this.dayName(t,"full")}),a.length?r("ul",{class:"calendar-events"},...a.map(n=>this.eventView(n))):r("p",{class:"calendar-none",text:this.t("calendarNoEvents")}))}agendaView(e){let t=this.t,a=this.anchorDay,n=v(this.getAttribute("limit"),{min:1,max:F.events,fallback:20}),s=this.agendaLimit||n,i=w(e.events,a,a+W,this.timeZone),l=r("section",{class:"calendar-list",part:"agenda"});if(!i.length)return l.append(r("p",{class:"calendar-none",text:t("calendarNoEventsAhead")})),l;let d=new Map;for(let o of i.slice(0,s)){let h=Math.max(o.startDay,a),c=d.get(h);c?c.push(o):d.set(h,[o])}for(let[o,h]of d)l.append(r("div",{class:"calendar-agenda-day"},r("h4",{class:"calendar-day-title",text:this.dayName(o,"full")}),r("ul",{class:"calendar-events"},...h.map(c=>this.eventView(c)))));return i.length>s&&l.append(r("button",{class:"text-btn calendar-show-more",text:t("calendarShowMore"),attrs:{type:"button","data-focus-key":"show-more"},on:{click:()=>{this.agendaLimit=s+n,this.render()}}})),l}eventView(e){let t=this.t,{event:a,id:n}=e,s=this.openId===n,i=`${this.panelId}-${n}`;return r("li",{class:`calendar-event${a.cancelled?" cancelled":""}`,part:"event"},r("button",{class:"calendar-event-toggle",attrs:{type:"button","aria-expanded":String(s),"aria-controls":s?i:null,"data-focus-key":`event-${n}`},on:{click:()=>this.toggleEvent(n)}},r("span",{class:"calendar-event-when",text:this.whenText(e)}),r("span",{class:"calendar-event-name"},r("span",{class:"calendar-event-title",text:a.title}),a.cancelled?r("span",{class:"calendar-tag",text:t("calendarCancelled")}):null,a.location&&!s?r("span",{class:"calendar-event-place",text:a.location}):null),Z(s?"chevron-up":"chevron-down")),s?this.eventDetails(e,i):null)}toggleEvent(e){let t=this.openId!==e;this.openId=t?e:null,this.render(),t&&this.emitSelect(e)}eventDetails(e,t){let a=this.t,{event:n}=e;return r("div",{class:"calendar-details",part:"event-details",attrs:{id:t}},r("p",{class:"calendar-range",text:this.rangeText(e)}),n.location?r("p",{class:"calendar-place",text:n.location}):null,n.description?r("p",{class:"calendar-text",text:n.description}):null,n.categories.length?r("ul",{class:"calendar-categories"},...n.categories.map(s=>r("li",{text:s}))):null,r("div",{class:"calendar-actions"},this.flag("add-to-calendar")?r("button",{class:"text-btn",text:a("calendarAdd"),attrs:{type:"button","data-focus-key":`add-${e.id}`},on:{click:()=>this.addToCalendar(e)}}):null,n.url?r("a",{class:"calendar-link",text:a("calendarDetails"),attrs:{href:n.url,rel:"noopener noreferrer"}}):null))}addToCalendar({event:e,allDay:t,start:a,end:n}){let s={...e,rule:null,excluded:[],replaces:null,duration:null};s.start=t?{...f(a),allDay:!0,zone:null}:f(a),s.end=t?{...f(n),allDay:!0,zone:null}:f(n),I(k([s],Date.now()),M(`${e.title||"event"}.ics`,"event.ics"),"text/calendar")}dayName(e,t){return this.formatDate(e*N,{dateStyle:t,timeZone:"UTC"})}timeText(e){return this.formatDate(e,{timeStyle:"short",timeZone:this.timeZone})}whenText(e){if(e.allDay)return this.t("calendarAllDay");let t=this.timeText(e.start);return e.end>e.start?`${t} \u2013 ${this.timeText(e.end)}`:t}rangeText(e){let{startDay:t,endDay:a}=e;if(e.allDay){let i=this.dayName(t,"full");return a>t?`${i} \u2013 ${this.dayName(a,"full")}`:i}let n={dateStyle:"full",timeStyle:"short",timeZone:this.timeZone},s=this.formatDate(e.start,n);return e.end<=e.start?s:a>t?`${s} \u2013 ${this.formatDate(e.end,n)}`:`${s} \u2013 ${this.timeText(e.end)}`}};function G(T){let e=/^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(T?.trim()??"");if(!e)return null;let[t,a,n]=[Number(e[1]),Number(e[2]),Number(e[3]??1)];return a<1||a>12||n<1||n>m(t,a)?null:g(t,a,n)}export{q as a};
