/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as I}from"./chunk-INCBER5S.js";import{a as $}from"./chunk-NPDHR5SA.js";import{B as d,C as h,D as p,E,O as y,c as w,d as _,e as A,o as c,q as b,s as O,y as S,z as j}from"./chunk-7PAHM2BV.js";import{h as C,k as f,l as g,m as D}from"./chunk-TUK22DTT.js";var z=`/*\r
 * Site search: a button for a menu and its dialog, or a field with its results under it. The\r
 * frame of the other elements is not drawn.\r
 */\r
:host {\r
  display: inline-block;\r
}\r
\r
:host([layout='inline']) {\r
  display: block;\r
}\r
\r
.vt {\r
  overflow: visible;\r
  background: transparent;\r
  border: 0;\r
  border-radius: 0;\r
}\r
\r
/* A theme set on the element is drawn on its own background, so its text stays readable on any page. */\r
:host([theme]:not([theme='auto'])) .vt {\r
  padding: var(--_space-2);\r
  background: var(--_surface);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
/* ---------- Button ---------- */\r
\r
.search-trigger {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  min-height: 36px;\r
  padding: 0 var(--_space-2) 0 var(--_space-3);\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface);\r
  color: var(--_fg-muted);\r
  font: 500 var(--_font-size-ui) / 1 var(--_font-ui);\r
  cursor: pointer;\r
}\r
\r
.search-trigger:hover {\r
  border-color: var(--_accent);\r
  color: var(--_fg);\r
}\r
\r
.search-trigger:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.search-trigger .icon {\r
  width: 16px;\r
  height: 16px;\r
}\r
\r
.search-kbd,\r
.search-hints kbd {\r
  padding: 2px 6px;\r
  border: 1px solid var(--_border);\r
  border-radius: 4px;\r
  background: var(--_surface-sunken);\r
  color: var(--_fg-muted);\r
  font: 500 11px / 1.2 var(--_font-mono);\r
}\r
\r
@media (max-width: 640px) {\r
  .search-trigger-label,\r
  .search-kbd {\r
    display: none;\r
  }\r
\r
  .search-trigger {\r
    padding: 0 var(--_space-2);\r
  }\r
}\r
\r
/* ---------- Dialog ---------- */\r
\r
.search-dialog {\r
  width: min(94vw, 640px);\r
  max-width: none;\r
  margin: 10vh auto auto;\r
  padding: 0;\r
  overflow: hidden;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius);\r
  background: var(--_surface);\r
  color: var(--_fg);\r
  box-shadow: 0 24px 60px rgb(0 0 0 / 28%);\r
}\r
\r
.search-dialog::backdrop {\r
  background: rgb(0 0 0 / 50%);\r
}\r
\r
@media (max-width: 640px) {\r
  .search-dialog {\r
    width: 100vw;\r
    max-height: 100dvh;\r
    margin: 0;\r
    border-radius: 0;\r
  }\r
}\r
\r
.search-box {\r
  position: relative;\r
  display: grid;\r
  min-width: 0;\r
}\r
\r
.search-field {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  padding: 0 var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
.search-box.inline .search-field {\r
  min-height: 40px;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface);\r
}\r
\r
.search-box.inline .search-field:focus-within {\r
  border-color: var(--_accent);\r
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--_accent) 35%, transparent);\r
}\r
\r
.search-field > .icon {\r
  flex: none;\r
  width: 18px;\r
  height: 18px;\r
  color: var(--_fg-muted);\r
}\r
\r
.search-input {\r
  flex: 1;\r
  min-width: 0;\r
  min-height: 52px;\r
  padding: 0;\r
  border: 0;\r
  background: transparent;\r
  color: var(--_fg);\r
  font: 400 16px / 1.4 var(--_font-ui);\r
  outline: none;\r
}\r
\r
.inline .search-input {\r
  min-height: 38px;\r
  font-size: 14px;\r
}\r
\r
.search-input::-webkit-search-cancel-button,\r
.search-input::-webkit-search-decoration {\r
  appearance: none;\r
}\r
\r
.search-esc {\r
  padding: 3px 7px;\r
  border: 1px solid var(--_border);\r
  border-radius: 4px;\r
  background: var(--_surface-sunken);\r
  color: var(--_fg-muted);\r
  font: 500 11px / 1.2 var(--_font-mono);\r
  cursor: pointer;\r
}\r
\r
.search-esc:focus-visible {\r
  outline: 2px solid var(--_accent);\r
}\r
\r
/* ---------- Results ---------- */\r
\r
.search-popup {\r
  display: grid;\r
  min-width: 0;\r
}\r
\r
.search-popup.hidden {\r
  display: none;\r
}\r
\r
.inline .search-popup {\r
  position: absolute;\r
  top: calc(100% + 6px);\r
  right: 0;\r
  left: 0;\r
  z-index: 30;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-raised);\r
  box-shadow: 0 10px 28px rgb(0 0 0 / 16%);\r
}\r
\r
.search-results {\r
  max-height: min(60vh, 460px);\r
  margin: 0;\r
  padding: var(--_space-2);\r
  overflow-y: auto;\r
  list-style: none;\r
}\r
\r
.search-results:empty {\r
  display: none;\r
}\r
\r
.search-section {\r
  display: flex;\r
  align-items: center;\r
  justify-content: space-between;\r
  padding: var(--_space-2) var(--_space-2) 4px;\r
  color: var(--_fg-muted);\r
  font: 600 var(--_font-size-small) / 1.3 var(--_font-ui);\r
  letter-spacing: 0.04em;\r
  text-transform: uppercase;\r
}\r
\r
.search-clear {\r
  min-height: 0;\r
  padding: 0 4px;\r
  text-transform: none;\r
}\r
\r
.search-result {\r
  display: grid;\r
  grid-template-columns: minmax(0, 1fr) 16px;\r
  align-items: center;\r
  gap: 2px var(--_space-2);\r
  padding: var(--_space-2) var(--_space-3);\r
  border-radius: var(--_radius-sm);\r
  color: var(--_fg);\r
  cursor: pointer;\r
}\r
\r
.search-result[aria-selected='true'] {\r
  background: var(--_accent-soft);\r
}\r
\r
.search-result > .icon {\r
  grid-row: 1 / span 3;\r
  grid-column: 2;\r
  width: 16px;\r
  height: 16px;\r
  color: var(--_fg-muted);\r
  opacity: 0;\r
}\r
\r
.search-result[aria-selected='true'] > .icon {\r
  opacity: 1;\r
}\r
\r
.search-title {\r
  font: 600 14px / 1.4 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
.search-extract,\r
.search-where {\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.45 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
mark {\r
  padding: 0 1px;\r
  border-radius: 2px;\r
  background: var(--_highlight);\r
  color: inherit;\r
}\r
\r
.search-empty {\r
  padding: var(--_space-4) var(--_space-3);\r
  color: var(--_fg-muted);\r
  font: 400 14px / 1.5 var(--_font-ui);\r
  text-align: center;\r
}\r
\r
.search-hints {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  gap: 4px;\r
  margin: 0;\r
  padding: var(--_space-2) var(--_space-3);\r
  border-top: 1px solid var(--_border);\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
@media (pointer: coarse) {\r
  .search-result {\r
    padding-block: var(--_space-3);\r
  }\r
\r
  .search-hints {\r
    display: none;\r
  }\r
}\r
`;var Z=2e4,tt=5e3,K=140,et=8;function q(s){return Array.from(s,rt)}var R=new Map;function rt(s){let t=s.charCodeAt(0);if(t<128)return t>=65&&t<=90?String.fromCharCode(t+32):s;let e=R.get(s);if(e===void 0){let r=s.normalize("NFKD").replace(/[̀-ͯ]/g,"");e=(Array.from(r)[0]??s).toLowerCase(),R.size<5e3&&R.set(s,e)}return e}function m(s){return/^[\x00-\x7f]*$/.test(s)?s.toLowerCase():q(s).join("")}function L(s){return m(s).split(/[\s,;:/|"'()[\]{}<>]+/).filter(Boolean).slice(0,et)}function T(s){if(!s.trim())return{ok:!0,entries:[]};let t;try{t=JSON.parse(s)}catch(o){return{ok:!1,error:"json",message:o instanceof Error?o.message:""}}let e=["entries","items","pages","results","documents","hits"],r=Array.isArray(t)?t:d(t)?e.map(o=>t[o]).find(Array.isArray):null;if(!r)return{ok:!1,error:"shape",message:e.map(o=>`"${o}"`).join(", ")};let i=[],a=new Set;for(let o of r){if(i.length>=Z)break;let n=d(o)?st(o):null;!n||a.has(n.id)||(a.add(n.id),i.push(n))}return{ok:!0,entries:i}}function st(s){let t=p(s,["title","name","label","t"],300);if(!t)return null;let e=E(s.url??s.href??s.link??s.u)??"",r=p(s,["id","uuid","slug","key","objectID"],200)||e||t,i=Array.isArray(s.keywords??s.tags)?s.keywords??s.tags:[];return{id:r,title:t,url:e,section:p(s,["section","group","category","type","p"],100),content:p(s,["content","description","summary","excerpt","text","body"],tt),keywords:i.slice(0,50).map(a=>h(a,100)).filter(Boolean),featured:s.featured===!0}}function P(s,t){if(s===t)return!0;if(Math.abs(s.length-t.length)>1)return!1;let e=0;for(;e<s.length&&e<t.length&&s[e]===t[e];)e+=1;return s.length===t.length?s.slice(e+1)===t.slice(e+1)?!0:s[e]===t[e+1]&&s[e+1]===t[e]&&s.slice(e+2)===t.slice(e+2):s.length>t.length?s.slice(e+1)===t.slice(e):s.slice(e)===t.slice(e+1)}function U(s,t){let e=s.join(""),r=[];s.forEach((o,n)=>{for(let l=0;l<o.length;l+=1)r.push(n)});let i=[];for(let o of t)for(let n=e.indexOf(o);n!==-1&&i.length<200;n=e.indexOf(o,n+o.length))i.push([r[n],r[n+o.length-1]+1]);i.sort((o,n)=>o[0]-n[0]);let a=[];for(let o of i){let n=a[a.length-1];n&&o[0]<=n[1]?n[1]=Math.max(n[1],o[1]):a.push([...o])}return a}function it(s,t,e){return t.includes(e)?10:t.some(r=>r.startsWith(e))?8:s.includes(e)?5:e.length>=4&&t.some(r=>P(r,e)||r.length>e.length&&P(r.slice(0,e.length),e))?3:0}var H=new WeakMap;function ot(s){let t=H.get(s);if(!t){let e=m(s.title);t={title:e,parts:e.split(/[^\p{L}\p{N}]+/u).filter(Boolean),keywords:m(s.keywords.join(" ")),section:m(s.section),content:m(s.content)},H.set(s,t)}return t}function at(s,t){let{title:e,parts:r,keywords:i,section:a,content:o}=ot(s),n=0;for(let l of t){let u=Math.max(it(e,r,l),i.includes(l)?6:0,a.includes(l)?3:0,o.includes(l)?2:0);if(!u)return 0;n+=u}return t.length>1&&e.includes(t.join(" "))&&(n+=5),n+(s.featured?1:0)-e.length/500}function nt(s,t){let e=Array.from(s),r=q(s),i=U(r,t);if(!e.length)return{extract:"",ranges:[]};let a=i.length?i[0][0]:0,o=Math.max(0,a-40);for(;o>0&&o>a-60&&e[o-1]!==" ";)o-=1;let n=Math.min(e.length,o+K);for(;n<e.length&&n<o+K+20&&e[n]!==" ";)n+=1;let l=o>0?"\u2026":"",u=n<e.length?"\u2026":"",N=l?1-o:-o,Y=i.filter(([v,k])=>v>=o&&k<=n).map(([v,k])=>[v+N,k+N]);return{extract:`${l}${e.slice(o,n).join("").trim()}${u}`,ranges:Y}}function F(s,t,e=12){let r=L(t);return r.length?s.map(i=>({entry:i,score:at(i,r)})).filter(i=>i.score>0).sort((i,a)=>a.score-i.score).slice(0,e).map(({entry:i,score:a})=>x(i,a,r)):[]}function x(s,t,e){let{extract:r,ranges:i}=nt(s.content,e);return{entry:s,score:t,title:U(q(s.title),e),extract:r,extractRanges:i}}function B(s,t){return s.url?s.url:!t||!t.includes("{id}")?null:E(t.replace(/\{id\}/g,encodeURIComponent(s.id)))}var X=Object.freeze({searchOpen:"Search",searchPlaceholder:"Search\u2026",searchResults:"Results",searchRecent:"Recent searches",searchSuggested:"Suggested",searchClearRecent:"Clear",searchNone:'No results for "{query}".',searchCount:"{count} results",searchOne:"1 result",searchLoading:"Loading\u2026",searchFailed:"The search could not load.",searchHintMove:"to move",searchHintOpen:"to open",searchHintClose:"to close",searchClose:"Close the search",searchOther:"Other"}),G=Object.freeze({searchOpen:"Rechercher",searchPlaceholder:"Rechercher\u2026",searchResults:"R\xE9sultats",searchRecent:"Recherches r\xE9centes",searchSuggested:"Suggestions",searchClearRecent:"Effacer",searchNone:"Aucun r\xE9sultat pour \xAB {query} \xBB.",searchCount:"{count} r\xE9sultats",searchOne:"1 r\xE9sultat",searchLoading:"Chargement\u2026",searchFailed:"La recherche n'a pas pu se charger.",searchHintMove:"pour se d\xE9placer",searchHintOpen:"pour ouvrir",searchHintClose:"pour fermer",searchClose:"Fermer la recherche",searchOther:"Autres"});D({en:X,fr:G});var ct=["dialog","inline"],J=6,lt=220,M=typeof navigator<"u"&&/Mac|iPhone|iPad/.test(navigator.platform),W=class extends ${static type="search";static allowEmpty=!0;static componentAttributes=Object.freeze(["index-src","search-src","url-template","shortcut","layout","limit","recent","group","link-target"]);static presets={simple:{},full:{}};static styles=[I,z];constructor(){super(),this.ids={dialog:b("search"),list:b("results"),input:b("query")},this.query="",this.isOpen=!1,this.results=[],this.active=0,this.loaded=null,this.loading=!1,this.failed=!1,this.cache=null,this.request=null,this.timer=void 0,this.input=null,this.list=null,this.dialogNode=null,this.onShortcut=this.onShortcut.bind(this)}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this.onShortcut)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this.onShortcut),this.request?.abort(),clearTimeout(this.timer)}get layout(){return A(this.getAttribute("layout"),ct,"dialog")}get entries(){let t=this.loaded??this.text??"";if(this.cache?.text!==t){let e=T(t);this.cache={text:t,entries:e.ok?e.entries:[]}}return this.cache.entries}get storageKey(){return`vitrine-search:${this.getAttribute("index-src")??this.getAttribute("search-src")??"default"}`}get shortcuts(){let t=(this.getAttribute("shortcut")??"mod+k /").trim().toLowerCase();return t==="none"||!t?[]:t.split(/\s+/).slice(0,4).map(e=>{let r=e.split("+");return{key:r.pop()??"",mod:r.includes("mod")||r.includes("ctrl")||r.includes("meta"),shift:r.includes("shift"),alt:r.includes("alt")}})}get shortcutLabel(){let t=this.shortcuts[0];if(!t)return"";let e=t.key.length===1?t.key.toUpperCase():t.key;return t.mod?M?`\u2318${e}`:`Ctrl ${e}`:e==="/"?"/":e}onShortcut(t){if(t.defaultPrevented)return;let e=t.composedPath()[0],r=e&&(/^(INPUT|TEXTAREA|SELECT)$/.test(e.tagName)||e.isContentEditable),i=M?t.metaKey:t.ctrlKey;for(let a of this.shortcuts)if(!(t.key.toLowerCase()!==a.key||i!==a.mod||t.altKey!==a.alt)&&!(a.shift!==t.shiftKey&&a.key.length===1&&/[a-z]/.test(a.key))){if(!a.mod&&r)return;t.preventDefault(),this.layout==="inline"?this.input?.focus():this.isOpen?this.close():this.open();return}}open(){if(this.layout==="inline"){this.input?.focus();return}this.isOpen||(this.isOpen=!0,this.query="",this.render(),g(this,f.TOGGLE,{expanded:!0}))}close(){this.isOpen&&(this.isOpen=!1,this.request?.abort(),this.dialogNode?.close(),this.render(),this.root.querySelector('[data-focus-key="trigger"]')?.focus(),g(this,f.TOGGLE,{expanded:!1}))}loadIndex(){let t=this.getAttribute("index-src")?.trim();if(!t||this.loaded!==null||this.loading)return;this.loading=!0,this.failed=!1;let e=C();S(t,{allowRemote:w(this.getAttribute("allow-remote"))===!0,maxSize:e.maxSize,timeout:e.fetchTimeout}).then(r=>{this.loading=!1,this.loaded=r,this.update()},r=>{this.loading=!1,this.failed=!0,console.warn("[vitrine] Could not load index-src.",r),this.update()})}renderContent(t){let e=this.layout==="inline";if(this.input=null,this.list=null,this.dialogNode=null,e){t.append(this.box(!1)),this.update();return}if(t.append(this.trigger()),!this.isOpen)return;let r=c("dialog",{class:"search-dialog",part:"dialog",attrs:{id:this.ids.dialog,"aria-label":this.getAttribute("label")||this.t("searchOpen")},on:{close:()=>this.isOpen&&this.close(),click:i=>i.target===r&&this.close()}},this.box(!0));this.dialogNode=r,t.append(r),typeof this.dialogNode.showModal=="function"?this.dialogNode.showModal():r.setAttribute("open",""),this.loadIndex(),this.update(),this.input?.focus()}trigger(){let t=this.t,e=this.getAttribute("label")||t("searchOpen"),r=this.shortcuts.map(i=>`${i.mod?M?"Meta+":"Control+":""}${i.key.toUpperCase()}`).join(" ");return c("button",{class:"search-trigger",part:"trigger",attrs:{type:"button","aria-haspopup":"dialog","aria-expanded":String(this.isOpen),"aria-keyshortcuts":r||null,"data-focus-key":"trigger"},on:{click:()=>this.open()}},y("search"),c("span",{class:"search-trigger-label",text:e}),this.shortcutLabel?c("kbd",{class:"search-kbd",part:"shortcut",text:this.shortcutLabel,attrs:{"aria-hidden":"true"}}):null)}box(t){let e=this.t,r=c("input",{class:"search-input",part:"input",attrs:{id:this.ids.input,type:"search",value:this.query,placeholder:this.getAttribute("placeholder")||e("searchPlaceholder"),role:"combobox","aria-label":this.getAttribute("label")||e("searchOpen"),"aria-autocomplete":"list","aria-controls":this.ids.list,"aria-expanded":String(t),autocomplete:"off",spellcheck:"false",enterkeyhint:"search","data-focus-key":"input"},on:{input:()=>{this.query=r.value.slice(0,200),this.active=0,this.update()},keydown:a=>this.inputKey(a),focus:()=>{t||(this.loadIndex(),this.showPopup(!0))},blur:()=>!t&&setTimeout(()=>this.showPopup(!1),120)}});this.input=r;let i=c("ul",{class:"search-results",part:"results",attrs:{id:this.ids.list,role:"listbox","aria-label":e("searchResults")}});return this.list=i,c("div",{class:`search-box${t?" in-dialog":" inline"}`},c("div",{class:"search-field"},y("search"),r,t?c("button",{class:"search-esc",text:"Esc",attrs:{type:"button","aria-label":e("searchClose")},on:{click:()=>this.close()}}):null),c("div",{class:`search-popup${t?"":" hidden"}`},i,t?this.hints():null))}hints(){let t=this.t;return c("p",{class:"search-hints",attrs:{"aria-hidden":"true"}},c("kbd",{text:"\u2191"}),c("kbd",{text:"\u2193"}),` ${t("searchHintMove")} `,c("kbd",{text:"\u21B5"}),` ${t("searchHintOpen")} `,c("kbd",{text:"Esc"}),` ${t("searchHintClose")}`)}showPopup(t){this.root.querySelector(".search-popup")?.classList.toggle("hidden",!t||!this.query&&!this.recent().length),this.input?.setAttribute("aria-expanded",String(t))}update(){if(!this.list)return;let t=this.query.trim(),e=this.getAttribute("search-src")?.trim();if(e&&t){clearTimeout(this.timer),this.timer=setTimeout(()=>this.remote(e,t),lt);return}let r=_(this.getAttribute("limit"),{min:1,max:100,fallback:12});this.results=t?F(this.entries,t,r):[],this.show()}remote(t,e){this.request?.abort();let r=new AbortController;this.request=r;let i=C(),a=_(this.getAttribute("limit"),{min:1,max:100,fallback:12});S(t.replace(/\{query\}/g,encodeURIComponent(e)),{allowRemote:w(this.getAttribute("allow-remote"))===!0,maxSize:i.maxSize,timeout:i.fetchTimeout,signal:r.signal}).then(o=>{if(r.signal.aborted)return;let n=T(o),l=L(e);this.results=n.ok?n.entries.slice(0,a).map(u=>x(u,1,l)):[],this.failed=!n.ok,this.show()},o=>{j(o)||(this.failed=!0,this.results=[],this.show())})}show(){let t=this.list,e=this.t,r=this.query.trim();if(t.replaceChildren(),!r)this.results=this.recent().map(i=>x(i,1,[])),this.results.length?this.group(t,this.results,e("searchRecent"),!0):(this.results=this.entries.filter(i=>i.featured).slice(0,8).map(i=>x(i,1,[])),this.results.length&&this.group(t,this.results,e("searchSuggested")));else if(this.results.length){let i=this.flag("group"),a=new Map;for(let o of this.results){let n=i?o.entry.section:"";a.set(n,[...a.get(n)??[],o])}this.results=[...a.values()].flat();for(let[o,n]of a)this.group(t,n,i?o||e("searchOther"):"")}else{let i=this.loading?e("searchLoading"):this.failed?e("searchFailed"):e("searchNone",{query:r});t.append(c("li",{class:"search-empty",text:i,attrs:{role:"presentation"}}))}this.active=Math.min(this.active,Math.max(0,this.results.length-1)),this.mark(),this.layout==="inline"&&this.showPopup(this.root.activeElement===this.input),r&&(this.announce(this.results.length===1?e("searchOne"):e("searchCount",{count:this.results.length})),g(this,f.SEARCH,{query:r,matches:this.results.length}))}group(t,e,r,i=!1){let a=t.querySelectorAll('[role="option"]').length;r&&t.append(c("li",{class:"search-section",attrs:{role:"presentation"}},c("span",{text:r}),i?c("button",{class:"text-btn search-clear",text:this.t("searchClearRecent"),attrs:{type:"button",tabindex:"-1"},on:{mousedown:o=>o.preventDefault(),click:()=>{this.store([]),this.update()}}}):null)),e.forEach((o,n)=>t.append(this.option(o,a+n)))}option(t,e){let{entry:r}=t;return c("li",{class:"search-result",part:"result",attrs:{id:`${this.ids.list}-${e}`,role:"option","aria-selected":"false"},on:{mousedown:i=>i.preventDefault(),click:i=>this.select(t,i.ctrlKey||i.metaKey),pointermove:()=>{this.active!==e&&(this.active=e,this.mark())}}},c("span",{class:"search-title"},...V(r.title,t.title)),t.extract?c("span",{class:"search-extract"},...V(t.extract,t.extractRanges)):null,r.section&&!this.flag("group")?c("span",{class:"search-where",text:r.section}):null,y("arrow-right"))}mark(){let t=this.list?[...this.list.querySelectorAll('[role="option"]')]:[];t.forEach((e,r)=>{e.setAttribute("aria-selected",String(r===this.active)),r===this.active&&e.scrollIntoView({block:"nearest"})}),t[this.active]?this.input?.setAttribute("aria-activedescendant",t[this.active].id):this.input?.removeAttribute("aria-activedescendant")}inputKey(t){let e=this.results.length;if(t.key==="ArrowDown"||t.key==="ArrowUp"){if(t.preventDefault(),!e)return;this.active=(this.active+(t.key==="ArrowDown"?1:-1)+e)%e,this.mark()}else if(t.key==="Enter"){let r=this.results[this.active];if(!r)return;t.preventDefault(),this.select(r,t.ctrlKey||t.metaKey)}else if(t.key==="Escape"){if(t.preventDefault(),this.layout==="dialog"){this.close();return}this.query?(this.query="",this.input.value="",this.update()):this.input?.blur()}}select(t,e){let{entry:r}=t,i=B(r,this.getAttribute("url-template"));this.remember(r,i);let a=g(this,f.SELECT,{id:r.id,url:i,title:r.title,section:r.section,query:this.query.trim()});if(this.layout==="dialog"&&this.close(),!a||!i||!O(i))return;let o=A(this.getAttribute("link-target"),["_self","_blank"],"_self");e||o==="_blank"?window.open(i,"_blank","noopener,noreferrer"):location.assign(i)}recent(){if(!this.flag("recent"))return[];try{let t=JSON.parse(localStorage.getItem(this.storageKey)??"[]");return Array.isArray(t)?t.filter(d).slice(0,J).map(e=>({id:h(e.id,200),title:h(e.title,300),url:h(e.url,2e3),section:h(e.section,100),content:"",keywords:[],featured:!1})).filter(e=>e.id&&e.title&&(!e.url||O(e.url))):[]}catch{return[]}}remember(t,e){if(!this.flag("recent"))return;let r=this.recent().filter(i=>i.id!==t.id);this.store([{id:t.id,title:t.title,url:e??"",section:t.section},...r].slice(0,J))}store(t){try{t.length?localStorage.setItem(this.storageKey,JSON.stringify(t)):localStorage.removeItem(this.storageKey)}catch{}}};function V(s,t){let e=Array.from(s),r=[],i=0;for(let[a,o]of t)a<i||o>e.length||(a>i&&r.push(e.slice(i,a).join("")),r.push(c("mark",{part:"match",text:e.slice(a,o).join("")})),i=o);return i<e.length&&r.push(e.slice(i).join("")),r}export{W as a};
