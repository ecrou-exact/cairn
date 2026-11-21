/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as p,c as w,f as N,g as S,h as k,i as A,j as L}from"./chunk-MSSSOVCM.js";import{n as C}from"./chunk-JRUMHT4D.js";import{r as T}from"./chunk-DUXCLZ3D.js";import{W as _,_ as u,ba as x,c as d,f as h,o as t,q as v}from"./chunk-7PAHM2BV.js";import{h as g,k as m,l as y,m as b}from"./chunk-TUK22DTT.js";var z=`/*\r
 * Indicators of compromise: type filters, then a table per type.\r
 */\r
.ioc-body {\r
  display: grid;\r
  gap: var(--_space-4);\r
  padding: var(--_space-4);\r
  background: var(--_surface);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-ui);\r
}\r
\r
.ioc-note {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.ioc-filters {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-2);\r
}\r
\r
.ioc-filter {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  min-height: 32px;\r
  padding: 4px var(--_space-3);\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-full);\r
  background: var(--_surface);\r
  color: var(--_fg);\r
  font: inherit;\r
  cursor: pointer;\r
}\r
\r
.ioc-filter:hover {\r
  border-color: var(--_border-strong);\r
}\r
\r
.ioc-filter[aria-pressed='true'] {\r
  border-color: var(--_accent);\r
  background: var(--_accent-soft);\r
  color: var(--_accent-fg);\r
  font-weight: 600;\r
}\r
\r
.ioc-filter:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.ioc-count {\r
  min-width: 2ch;\r
  padding: 0 6px;\r
  border-radius: var(--_radius-full);\r
  background: var(--_surface-sunken);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-variant-numeric: tabular-nums;\r
  text-align: center;\r
}\r
\r
.ioc-group {\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
}\r
\r
.ioc-title {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-weight: 600;\r
  letter-spacing: 0.04em;\r
  text-transform: uppercase;\r
}\r
\r
.ioc-scroll {\r
  max-height: var(--vt-ioc-group-height, 360px);\r
  overflow: auto;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
.ioc-table {\r
  width: 100%;\r
  border-collapse: collapse;\r
}\r
\r
.ioc-table th,\r
.ioc-table td {\r
  padding: 6px var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  text-align: start;\r
  vertical-align: top;\r
}\r
\r
.ioc-table tbody tr:last-child > * {\r
  border-bottom: 0;\r
}\r
\r
.ioc-table thead th {\r
  position: sticky;\r
  top: 0;\r
  background: var(--_surface-sunken);\r
  font-weight: 600;\r
}\r
\r
.ioc-table .ioc-num {\r
  width: 1%;\r
  color: var(--_fg-muted);\r
  font-variant-numeric: tabular-nums;\r
  text-align: end;\r
  white-space: nowrap;\r
}\r
\r
.ioc-value code {\r
  color: var(--_code-fg);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size);\r
  overflow-wrap: anywhere;\r
  word-break: break-all;\r
}\r
\r
.ioc-tag {\r
  display: inline-block;\r
  padding: 0 var(--_space-2);\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-full);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  white-space: nowrap;\r
}\r
\r
.ioc-edit > .editor-body {\r
  max-height: min(35vh, 280px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
`;var D=Object.freeze({iocCount:"{count} indicators",iocCountOne:"1 indicator",iocNone:"No indicator found.",iocCapped:"Only the first {count} indicators are shown.",iocAll:"All",iocFilter:"Indicator types",iocValue:"Indicator",iocSeen:"Seen",iocLine:"Line",iocNoteHeader:"Note",iocDefanged:"Defanged: links and addresses cannot be opened by accident. Nothing is resolved or fetched.",iocDefang:"Defang",iocRefang:"Show as found",iocCopyList:"Copy list",iocCopyCsv:"CSV",iocCopyStix:"STIX",iocCopyMisp:"MISP",iocType_url:"URLs",iocType_domain:"Domains",iocType_ipv4:"IPv4 addresses",iocType_ipv6:"IPv6 addresses",iocType_email:"E-mail addresses",iocType_md5:"MD5",iocType_sha1:"SHA-1",iocType_sha256:"SHA-256",iocType_sha512:"SHA-512",iocType_cve:"CVE",iocType_attack:"ATT&CK techniques",iocNote_private:"Private",iocNote_loopback:"Loopback","iocNote_link-local":"Link-local",iocNote_shared:"Shared (CGNAT)",iocNote_multicast:"Multicast",iocNote_reserved:"Reserved or documentation"}),I={iocCount:"{count} indicateurs",iocCountOne:"1 indicateur",iocNone:"Aucun indicateur trouv\xE9.",iocCapped:"Seuls les {count} premiers indicateurs sont affich\xE9s.",iocAll:"Tous",iocFilter:"Types d\u2019indicateurs",iocValue:"Indicateur",iocSeen:"Vu",iocLine:"Ligne",iocNoteHeader:"Note",iocDefanged:"Neutralis\xE9s : liens et adresses ne peuvent pas \xEAtre ouverts par accident. Rien n\u2019est r\xE9solu ni t\xE9l\xE9charg\xE9.",iocDefang:"Neutraliser",iocRefang:"Afficher tels quels",iocCopyList:"Copier la liste",iocType_url:"URL",iocType_domain:"Domaines",iocType_ipv4:"Adresses IPv4",iocType_ipv6:"Adresses IPv6",iocType_email:"Adresses e-mail",iocType_attack:"Techniques ATT&CK",iocNote_private:"Priv\xE9e",iocNote_loopback:"Boucle locale","iocNote_link-local":"Lien local",iocNote_shared:"Partag\xE9e (CGNAT)",iocNote_multicast:"Multidiffusion",iocNote_reserved:"R\xE9serv\xE9e ou documentation"};b({en:D,fr:I});var V=class extends x{static type="ioc";static fromData=C;static componentAttributes=Object.freeze(["types","defang","private","filters"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,fullscreen:!0}};static styles=[z];static upgradeProperties=["content"];constructor(){super(),this.panelId=v("panel"),this.only=null,this.defangState=null,this.editor=null,this.previewTimer=void 0}scan(){let o=h(this.getAttribute("types"),p),e=d(this.getAttribute("private"))!==!1,i=N(this.text??"");return{indicators:i.indicators.filter(s=>(!o?.length||o.includes(s.type))&&(e||!s.note)),capped:i.capped}}get indicators(){return this.scan().indicators}get defanged(){return this.defangState??d(this.getAttribute("defang"))!==!1}export(o){let e=this.visible(this.indicators),i=this.heading||void 0;return o==="csv"?k(e,this.defanged):o==="stix"?A(e,{name:i}):o==="misp"?L(e,{info:i}):S(e,this.defanged)}visible(o){return this.only?o.filter(e=>e.type===this.only):o}renderContent(o){let e=this.t,{indicators:i,capped:c}=this.scan();this.only&&!i.some(n=>n.type===this.only)&&(this.only=null);let s=t("div",{class:"body ioc-body",part:"body"});if(!i.length)s.append(u(e("iocNone")));else{this.defanged&&s.append(t("p",{class:"ioc-note",text:e("iocDefanged")})),c&&s.append(u(e("iocCapped",{count:i.length}))),d(this.getAttribute("filters"))!==!1&&s.append(this.filtersView(i));for(let n of p){if(this.only&&n!==this.only)continue;let f=i.filter(E=>E.type===n);f.length&&s.append(this.groupView(n,f))}}let r=t("div",{class:"panel",attrs:{id:this.panelId}}),a=[];if(this.editing){let n=this.createEditor();r.classList.add("ioc-edit"),r.append(t("div",{class:"body editor-body",part:"body source"},n.element),s),a=this.historyButtons(n)}else r.append(s);let l=this.feature("copy")&&i.length>0,B=[...a,this.editToggleButton(),i.length?_({icon:this.defanged?"eye":"shield-check",label:this.defanged?e("iocRefang"):e("iocDefang"),key:"defang",pressed:this.defanged,onClick:()=>{this.defangState=!this.defanged,this.render()}}):null,this.fullscreenButton(),l?this.copyTextButton(()=>this.export("csv"),e("iocCopyCsv"),"copy-csv"):null,l?this.copyTextButton(()=>this.export("stix"),e("iocCopyStix"),"copy-stix"):null,l?this.copyTextButton(()=>this.export("misp"),e("iocCopyMisp"),"copy-misp"):null,l?this.copyButton(()=>this.export("text"),e("iocCopyList")):null],P=i.length===1?e("iocCountOne"):e("iocCount",{count:i.length});o.append(...this.chrome({badge:P,actions:B}),r),this.editor?.align()}filtersView(o){let e=this.t,i=(s,r,a)=>t("button",{class:"ioc-filter",attrs:{type:"button","aria-pressed":String(this.only===s),"data-focus-key":`filter-${s??"all"}`},on:{click:()=>{this.only=s;let l=this.activeFocusKey();this.render(),l&&this.restoreFocus(l)}}},t("span",{text:r}),t("span",{class:"ioc-count",text:String(a)})),c=p.filter(s=>o.some(r=>r.type===s));return t("div",{class:"ioc-filters",part:"filters",attrs:{role:"group","aria-label":e("iocFilter")}},i(null,e("iocAll"),o.length),...c.map(s=>i(s,e(`iocType_${s}`),o.filter(r=>r.type===s).length)))}groupView(o,e){let i=this.t,c=i(`iocType_${o}`),s=o==="ipv4"||o==="ipv6",r=e.map(a=>t("tr",{},t("td",{class:"ioc-value"},t("code",{part:"indicator",text:this.defanged?w(a.type,a.value):a.value})),t("td",{class:"ioc-num",text:String(a.count)}),t("td",{class:"ioc-num",text:String(a.line)}),s?t("td",{},a.note?t("span",{class:"ioc-tag",part:"note",text:i(`iocNote_${a.note}`)}):null):null));return t("section",{class:`ioc-group type-${o}`,part:"group",attrs:{"aria-label":c}},t("h3",{class:"ioc-title"},t("span",{text:c}),t("span",{class:"ioc-count",text:String(e.length)})),t("div",{class:"ioc-scroll"},t("table",{class:"ioc-table",part:"table"},t("thead",{},t("tr",{},t("th",{attrs:{scope:"col"},text:i("iocValue")}),t("th",{class:"ioc-num",attrs:{scope:"col"},text:i("iocSeen")}),t("th",{class:"ioc-num",attrs:{scope:"col"},text:i("iocLine")}),s?t("th",{attrs:{scope:"col"},text:i("iocNoteHeader")}):null)),t("tbody",{},...r))))}createEditor(){return this.editor?.destroy(),this.editor=new T({text:this.text??"",language:"plaintext",lineNumbers:!0,wrap:!0,highlightLimit:g().highlightLimit,label:this.heading||this.t("editor"),placeholder:this.getAttribute("placeholder")??void 0,onInput:o=>this.edited(o),onChange:o=>y(this,m.CHANGE,{value:o}),history:this.editHistory??void 0}),this.editor}contentEdited(){clearTimeout(this.previewTimer),this.previewTimer=setTimeout(()=>this.render(),250)}};export{V as a};
