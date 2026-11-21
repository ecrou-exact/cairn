/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as M,b as m,c as O,d as f,e as F,f as J,g as Z,j as Q,k as B}from"./chunk-GAW3FMS5.js";import{a as T,c as U}from"./chunk-N35IOOJ4.js";import{a as N}from"./chunk-BNQD3D4I.js";import{p as j,q as D,r as R}from"./chunk-DUXCLZ3D.js";import{U as P,W as $,X as _,_ as V,b as I,ba as G,e as A,o as l,q as z}from"./chunk-7PAHM2BV.js";import{h as y,k as v,l as w,q as b}from"./chunk-TUK22DTT.js";var W=`/*\r
 * HTTP exchange: request and response sections, each with a start line (method and URL,\r
 * or status), small section tabs, and a headers table or a formatted body.\r
 */\r
.http-body {\r
  background: var(--_surface);\r
}\r
\r
.http.stacked,\r
.http.columns {\r
  display: grid;\r
  grid-template-columns: minmax(0, 1fr);\r
}\r
\r
.vt {\r
  container-type: inline-size;\r
}\r
\r
@container (min-width: 760px) {\r
  .http.columns {\r
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);\r
  }\r
\r
  .http.columns > .response {\r
    border-top: 0;\r
    border-left: 1px solid var(--_border);\r
  }\r
}\r
\r
.http-message {\r
  min-width: 0;\r
}\r
\r
.http-message + .http-message {\r
  border-top: 1px solid var(--_border);\r
}\r
\r
/* ---------- Start lines ---------- */\r
\r
.start-line {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  min-height: 44px;\r
  padding: var(--_space-2) var(--_space-2) var(--_space-2) var(--_space-3);\r
}\r
\r
.method,\r
.status {\r
  flex: none;\r
  padding: 2px 8px;\r
  border-radius: var(--_radius-sm);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size-small);\r
  font-weight: 700;\r
  letter-spacing: 0.02em;\r
  line-height: 1.5;\r
  --_tone: var(--_fg-muted);\r
  background: color-mix(in srgb, var(--_tone) 16%, transparent);\r
  /* Mixed toward the text color: the tone stays recognizable and the label keeps AA\r
     contrast on its tinted background, in light and dark themes. */\r
  color: color-mix(in srgb, var(--_tone) 62%, var(--_fg));\r
}\r
\r
.method-get,\r
.method-head,\r
.method-options {\r
  --_tone: var(--_info);\r
}\r
\r
.method-post {\r
  --_tone: var(--_success);\r
}\r
\r
.method-put,\r
.method-patch {\r
  --_tone: var(--_warning);\r
}\r
\r
.method-delete {\r
  --_tone: var(--_danger);\r
}\r
\r
.status-1xx,\r
.status-3xx {\r
  --_tone: var(--_info);\r
}\r
\r
.status-2xx {\r
  --_tone: var(--_success);\r
}\r
\r
.status-4xx {\r
  --_tone: var(--_warning);\r
}\r
\r
.status-5xx {\r
  --_tone: var(--_danger);\r
}\r
\r
.url {\r
  flex: 1 1 auto;\r
  min-width: 0;\r
  color: var(--_fg);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size);\r
  overflow-wrap: anywhere;\r
}\r
\r
.url .origin {\r
  color: var(--_fg-muted);\r
}\r
\r
.url .origin.implied::after {\r
  content: ' ';\r
}\r
\r
.url .param {\r
  border-radius: 3px;\r
  background: var(--_accent-soft);\r
  color: var(--_accent-fg);\r
}\r
\r
.url .query {\r
  color: var(--_syntax-string);\r
}\r
\r
.meta {\r
  margin-left: auto;\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.line-copy {\r
  flex: none;\r
  margin-left: auto;\r
}\r
\r
/* ---------- Section tabs ---------- */\r
\r
.section-tabs {\r
  min-height: 32px;\r
  padding: 0 var(--_space-2);\r
  border-bottom: 1px solid var(--_border);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.section-panel {\r
  min-width: 0;\r
}\r
\r
/* ---------- Tables and bodies ---------- */\r
\r
.pairs {\r
  width: 100%;\r
  border-collapse: collapse;\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.pairs th,\r
.pairs td {\r
  padding: 5px var(--_space-3);\r
  border-bottom: 1px solid color-mix(in srgb, var(--_border) 70%, transparent);\r
  text-align: left;\r
  vertical-align: top;\r
  overflow-wrap: anywhere;\r
}\r
\r
.pairs th {\r
  width: 32%;\r
  max-width: 260px;\r
  color: var(--_fg-muted);\r
  font-weight: 600;\r
}\r
\r
.pairs tr:last-child > * {\r
  border-bottom: 0;\r
}\r
\r
.none {\r
  margin: 0;\r
  padding: var(--_space-3);\r
  color: var(--_fg-muted);\r
  font-style: italic;\r
}\r
\r
.message-body,\r
.snippet {\r
  background: var(--_code-bg);\r
}\r
\r
.message-body .code,\r
.snippet .code {\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
/* ---------- Code view ---------- */\r
\r
.code-head {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
.code-head .section-tabs {\r
  flex: 1 1 auto;\r
  border-bottom: 0;\r
}\r
\r
.snippet-copy {\r
  flex: none;\r
  margin-right: var(--_space-2);\r
}\r
\r
.code-panel .note {\r
  margin: 0;\r
  padding: var(--_space-2) var(--_space-3);\r
  border-top: 1px solid var(--_border);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
/* ---------- Edit mode: editor above, live preview below ---------- */\r
\r
.http-edit > .editor-body {\r
  max-height: min(40vh, 360px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
.vt[data-fullscreen] .http-edit {\r
  display: grid;\r
  flex: 1 1 auto;\r
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);\r
  min-height: 0;\r
}\r
\r
.vt[data-fullscreen] .http-edit > .editor-body {\r
  max-height: none;\r
}\r
\r
.connection tr.expired td {\r
  color: var(--_danger);\r
}\r
\r
.connection .badge {\r
  font-weight: 600;\r
}\r
\r
.image-body {\r
  margin: 0;\r
  padding: var(--_space-3);\r
  display: flex;\r
  flex-direction: column;\r
  align-items: flex-start;\r
  gap: var(--_space-2, 8px);\r
}\r
\r
.image-body .meta {\r
  margin-left: 0;\r
}\r
\r
.body-image {\r
  max-width: 100%;\r
  max-height: 320px;\r
  min-width: 16px;\r
  min-height: 16px;\r
  image-rendering: auto;\r
  background: repeating-conic-gradient(\r
      color-mix(in srgb, var(--_border) 60%, transparent) 0 25%,\r
      transparent 0 50%\r
    )\r
    0 0 / 12px 12px;\r
}\r
\r
.entries {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  padding: var(--_space-2) var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.entries-label {\r
  color: var(--_fg-muted);\r
  font-weight: 600;\r
}\r
\r
.entry-select {\r
  flex: 1 1 240px;\r
  min-width: 0;\r
  max-width: 100%;\r
  padding: 4px var(--_space-2);\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface);\r
  color: inherit;\r
  font: inherit;\r
  font-family: var(--_font-mono);\r
  text-overflow: ellipsis;\r
}\r
\r
.entries .btn:disabled {\r
  opacity: 0.4;\r
  cursor: default;\r
}\r
`;var L=["curl","fetch","python","httpie"],K={curl:"bash",fetch:"javascript",python:"python",httpie:"bash"},nt=new Set(["host","content-length","connection","transfer-encoding"]),rt=/^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/,it=new Set(["accept-charset","accept-encoding","access-control-request-headers","access-control-request-method","connection","content-length","cookie","cookie2","date","dnt","expect","host","keep-alive","origin","referer","te","trailer","transfer-encoding","upgrade","via"]);function x(s){return/^[\w@%+=:,./-]+$/.test(s)?s:`'${s.replace(/'/g,"'\\''")}'`}function u(s){return JSON.stringify(s).replace(/\u2028/g,"\\u2028").replace(/\u2029/g,"\\u2029")}function E(s){return s.headers.filter(([t])=>rt.test(t)&&!nt.has(t.toLowerCase()))}function X(s){let t=f(s);return x(t.startsWith("-")?`/${t}`:t)}function at(s,t){return`${s}:${t.replace(/^[=@]/,"\\$&")}`}function Y(s){if(!s.body)return null;let t=(m(s.headers,"content-type")??"").toLowerCase();if(t&&!t.includes("json"))return null;let e=T(s.body,{maxDepth:512});return e.ok?e.value:null}function S(s,t,e=""){let r=e+(t==="python"?"    ":"  ");switch(s.type){case"string":return u(s.value);case"number":return s.raw;case"boolean":return t==="python"?s.value?"True":"False":String(s.value);case"null":return t==="python"?"None":"null";case"array":return s.items.length?`[
${s.items.map(i=>`${r}${S(i,t,r)},`).join(`
`)}
${e}]`:"[]";case"object":{if(!s.entries.length)return"{}";let i=a=>t==="js"&&/^[A-Za-z_$][\w$]*$/.test(a)?a:u(a);return`{
${s.entries.map(a=>`${r}${i(a.key)}: ${S(a.value,t,r)},`).join(`
`)}
${e}}`}default:return"null"}}function ot(s){let t=["curl"],e=!!s.body;s.method==="HEAD"?t.push("--head"):!(s.method==="GET"&&!e)&&!(s.method==="POST"&&e)&&t.push(`-X ${s.method}`),t.push(X(s));let n=[t.join(" ")];for(let[r,i]of E(s))n.push(`-H ${x(`${r}: ${i}`)}`);return e&&n.push(`--data-raw ${x(s.body)}`),n.join(` \\
  `)}function lt(s,t={}){let e=[];s.method!=="GET"&&e.push(`  method: ${u(s.method)},`);let n=E(s).filter(([a])=>!it.has(a.toLowerCase()));if(n.length){let a=n.map(([h,c])=>`    ${u(h)}: ${u(c)},`);e.push(`  headers: {
${a.join(`
`)}
  },`)}if(m(s.headers,"cookie")&&e.push("  credentials: 'include',"),s.body&&s.method!=="GET"&&s.method!=="HEAD"){let a=Y(s);e.push(a?`  body: JSON.stringify(${S(a,"js","  ")}),`:`  body: ${u(s.body)},`)}let r=u(f(s)),i=e.length?`fetch(${r}, {
${e.join(`
`)}
})`:`fetch(${r})`,o=t.responseType==="json"?"json":"text";return`const response = await ${i};
const data = await response.${o}();`}function ct(s){let t=s.method.toLowerCase(),e=["get","post","put","patch","delete","head","options"].includes(t),n=e?[`    ${u(f(s))},`]:[`    ${u(s.method)},`,`    ${u(f(s))},`],r=Y(s),i=E(s).filter(([a,h])=>!(r&&a.toLowerCase()==="content-type"&&/json/i.test(h)));if(i.length){let a=i.map(([h,c])=>`        ${u(h)}: ${u(c)},`);n.push(`    headers={
${a.join(`
`)}
    },`)}return s.body&&n.push(r?`    json=${S(r,"python","    ")},`:`    data=${u(s.body)},`),`import requests

response = ${e?`requests.${t}`:"requests.request"}(
${n.join(`
`)}
)
response.raise_for_status()`}function ht(s){let t=[`http ${s.method} ${X(s)}`];for(let[e,n]of E(s))t.push(x(at(e,n)));return s.body&&t.push(`--raw ${x(s.body)}`),t.join(` \\
  `)}function q(s,t,e={}){switch(t){case"fetch":return lt(s,e);case"python":return ct(s);case"httpie":return ht(s);default:return ot(s)}}var dt=["exchange","code"],pt=["stacked","columns"],ut={curl:"curl",fetch:"fetch",python:"Python",httpie:"HTTPie"},tt=class extends G{static type="http";static componentAttributes=Object.freeze(["view","tabs","snippets","mask-secrets","layout","entry"]);static presets={simple:{"mask-secrets":!0},full:{header:!0,dot:!0,copy:!0,search:!0,download:!0,fullscreen:!0,tabs:!0,"mask-secrets":!0}};static styles=[I,N,W];static upgradeProperties=["content","exchange"];constructor(){super(),this.parsed=null,this.viewState=null,this.requestTab=null,this.responseTab=null,this.language=null,this.revealed=!1,this.panelId=z("panel"),this.entryState=null,this.editor=null,this.previewHost=null,this.previewTimer=void 0}disconnectedCallback(){clearTimeout(this.previewTimer),this.editor?.destroy(),super.disconnectedCallback()}contentChanged(){this.parsed=null,this.entryState=null,this.requestTab=null,this.responseTab=null}attributeChangedCallback(t,e,n){t==="view"&&(this.viewState=null),t==="snippets"&&(this.language=null),t==="entry"&&(this.entryState=null),super.attributeChangedCallback(t,e,n)}parse(){let t=this.text??"",e=this.entryState??this.getAttribute("entry");if(this.parsed?.text!==t||this.parsed.entry!==e)try{this.parsed={text:t,entry:e,exchange:O(t,{entry:e}),error:null}}catch(n){this.parsed={text:t,entry:e,exchange:null,error:n instanceof Error?n:new M(String(n))}}return this.parsed}get exchange(){let t=this.parse().exchange;return{request:t?.request?structuredClone(t.request):null,response:t?.response?structuredClone(t.response):null}}get entryIndex(){return this.parse().exchange?.entry??null}set entryIndex(t){this.entryState=Number.isInteger(t)&&Number(t)>=0?Number(t):null,this.render()}set exchange(t){let e;try{e=JSON.stringify(t??{})}catch{e="{}"}this.content=e}get masking(){return this.feature("mask-secrets")&&!this.revealed}shown(){let t=this.parse().exchange;return t?this.masking?Q(t):t:null}get languages(){let t=this.getAttribute("snippets");if(t===null)return[...L];let e=t.toLowerCase().split(/[\s,]+/).filter(n=>L.includes(n));return[...new Set(e)]}get view(){return(this.viewState??A(this.getAttribute("view"),dt,"exchange"))==="code"&&this.parse().exchange?.request&&this.languages.length?"code":"exchange"}renderContent(t){let e=this.t,{exchange:n,error:r}=this.parse(),i=l("div",{class:"panel",attrs:{id:this.panelId}}),o=[];if(this.editing){let g=this.createEditor();this.previewHost=l("div",{class:"body http-body http-preview",part:"body preview"}),i.classList.add("http-edit"),i.append(l("div",{class:"body editor-body",part:"body source"},g.element),this.previewHost),this.renderPreview(),o=this.historyButtons(g)}else this.previewHost=null,i.append(l("div",{class:"body http-body",part:"body",attrs:{tabindex:"0",role:"region","aria-label":this.heading||this.t("httpExchange")}},...this.renderView()));let a=this.view,h=!!n?.request&&this.languages.length>0,c=this.feature("tabs")&&!this.editing&&h?_({tabs:[{id:"exchange",label:e("httpExchange"),icon:"list"},{id:"code",label:e("code"),icon:"code"}],selected:a,label:e("tabs"),panelId:this.panelId,onSelect:g=>this.select("view",g)}):null;c&&i.setAttribute("role","tabpanel");let d=null,p={run:g=>{let H=this.root.querySelector(".http");return d=H?new P(H,{skip:"button, .sr-only"}):null,d?d.run(g):{total:0,capped:!1}},go:g=>D(d?.go(g)??null),clear:()=>d?.clear()},k=this.feature("mask-secrets")&&n&&!r&&B(n),et=[this.searchButton(p),...o,k?$({icon:this.revealed?"eye-off":"eye",label:e(this.revealed?"hideSecrets":"showSecrets"),key:"secrets",part:"secrets-button",pressed:this.revealed,onClick:()=>{this.revealed=!this.revealed,this.render(),this.announce(e(this.revealed?"secretsShown":"secretsHidden"))}}):null,this.editToggleButton(),this.fullscreenButton(),this.feature("download")?this.downloadButton(()=>this.rawText(),this.downloadName("exchange.http"),"text/plain"):null,this.feature("copy")?this.copyButton(()=>this.rawText(),e("copy")):null];t.append(...this.chrome({badge:c?"":"HTTP",tabs:c,actions:et}),i),this.editor?.align()}rawText(){let t=this.shown();return t?Z(t):this.text??""}select(t,e){t==="view"?this.viewState=e:t==="request"?this.requestTab=e:t==="response"?this.responseTab=e:this.language=e,this.render(),w(this,v.TAB_CHANGE,{tab:e})}renderView(){let{error:t}=this.parse(),e=this.shown();if(t)return[V(this.t("invalidHttp",{message:t.message}))];if(!e||!e.request&&!e.response)return[l("div",{class:"empty",part:"empty",text:this.t("empty")})];let n=e.entries?this.entriesBar(e.entries,e.entry??0):null;if(this.view==="code"&&e.request)return n?[n,this.codeView(e)]:[this.codeView(e)];let r=A(this.getAttribute("layout"),pt,"stacked"),i=l("div",{class:`http ${r}`});return e.request&&i.append(this.requestSection(e.request)),e.response?i.append(this.responseSection(e.response,e.connection??null)):e.connection&&i.append(this.connectionTable(e.connection)),n?[n,i]:[i]}entriesBar(t,e){let n=this.t,r=`${this.panelId}-entry`,i=c=>{c<0||c>=t.length||c===e||(this.entryState=c,this.requestTab=null,this.responseTab=null,this.render(),this.shadowRoot?.getElementById(r)?.focus(),w(this,v.TAB_CHANGE,{tab:`entry-${c}`}))},o=l("select",{class:"entry-select",attrs:{id:r},on:{change:c=>i(Number(c.target.value))}},...t.map((c,d)=>l("option",{text:`${d+1}. ${c.status??"\u2026"} ${c.method} ${xt(c.url)}${c.mimeType?` (${c.mimeType})`:""}`,attrs:{value:String(d),selected:d===e}}))),a=$({icon:"chevron-left",label:n("httpEntryPrevious"),key:"entry-previous",onClick:()=>i(e-1)}),h=$({icon:"chevron-right",label:n("httpEntryNext"),key:"entry-next",onClick:()=>i(e+1)});return a.disabled=e===0,h.disabled=e===t.length-1,l("div",{class:"entries",part:"entries"},l("label",{class:"entries-label",text:n("httpEntry"),attrs:{for:r}}),a,o,h,l("span",{class:"meta",text:n("httpEntryCount",{index:b(e+1,this.locale),total:b(t.length,this.locale)})}))}requestSection(t){let e=this.t,n=F(t.url),r=[t.body?{id:"body",label:e("httpBody")}:null,{id:"headers",label:`${e("httpHeaders")} ${t.headers.length}`},n.length?{id:"query",label:`${e("httpQuery")} ${n.length}`}:null].filter(d=>d!==null),i=r.some(d=>d.id===this.requestTab)?this.requestTab:r[0].id,o=l("div",{class:"start-line"},l("span",{class:`method method-${t.method.toLowerCase()}`,part:"method",text:t.method}),this.urlNode(t)),a=f(t),h=this.copyButton(()=>a,e("copyUrl"),"copy-url");h.classList.add("line-copy"),o.append(h);let c;return i==="headers"?c=this.table(t.headers,e("httpHeaders")):i==="query"?c=this.table(n,e("httpQuery")):c=this.bodyView(t.body,m(t.headers,"content-type")),l("section",{class:"http-message request",part:"request",attrs:{"aria-label":e("httpRequest")}},o,this.sectionTabs("request",r,i,e("httpRequest")),l("div",{class:"section-panel",attrs:{id:`${this.panelId}-request`}},c))}responseSection(t,e){let n=this.t,r=[{id:"body",label:n("httpBody")},{id:"headers",label:`${n("httpHeaders")} ${t.headers.length}`}];e&&r.push({id:"connection",label:n("httpConnection")});let i=this.responseTab==="headers"||this.responseTab==="connection"&&e?this.responseTab:"body",o=`${Math.floor(t.status/100)}xx`,a=l("div",{class:"start-line"},l("span",{class:`status status-${o}`,part:`status status-${o}`,text:`${t.status}${t.statusText?` ${t.statusText}`:""}`})),h=[];t.time!==null&&h.push(`${b(Math.round(t.time),this.locale)} ms`);let c=e?.contentSize??(t.body?bt(t):null);c!==null&&h.push(C(c,this.locale)),e?.tls?.protocol&&h.push(e.tls.protocol),h.length&&a.append(l("span",{class:"meta",text:h.join(", ")}));let d=m(t.headers,"content-type")??e?.mimeType??null,p;return i==="headers"?p=this.table(t.headers,n("httpHeaders")):i==="connection"&&e?p=this.connectionTable(e):t.encoding==="base64"?p=this.binaryView(t.body,d):p=this.bodyView(t.body,d),l("section",{class:"http-message response",part:"response",attrs:{"aria-label":n("httpResponse")}},a,this.sectionTabs("response",r,i,n("httpResponse")),l("div",{class:"section-panel",attrs:{id:`${this.panelId}-response`}},p))}sectionTabs(t,e,n,r){let i=_({tabs:e.map(o=>({id:`${t}-${o.id}`,label:o.label})),selected:`${t}-${n}`,label:r,panelId:`${this.panelId}-${t}`,onSelect:o=>this.select(t,o.slice(t.length+1))});return i.classList.add("section-tabs"),i.setAttribute("part","section-tabs"),i}urlNode(t){let e=l("code",{class:"url",part:"url"}),{origin:n,path:r,rest:i}=mt(t.url),o=m(t.headers,"host");n?e.append(l("span",{class:"origin",text:n})):o&&e.append(l("span",{class:"origin implied",text:o}));for(let a of gt(r))e.append(a.param?l("span",{class:"param",text:a.text}):a.text);return i&&e.append(l("span",{class:"query",text:i})),e}table(t,e){return t.length?l("table",{class:"pairs",part:"headers",attrs:{"aria-label":e}},l("tbody",{},...t.map(([n,r])=>l("tr",{},l("th",{attrs:{scope:"row"},text:n}),l("td",{text:r}))))):l("p",{class:"none",text:this.t("httpNone")})}connectionTable(t){let e=this.t,n=this.locale,r=[],i=(d,p)=>{p&&r.push([d,p])},o=d=>d===null?null:`${C(d,n)} (${b(d,n)} B)`,a=d=>d?yt(d,n):null;i(e("httpServerIp"),t.serverIp),i(e("httpVersion"),t.httpVersion),i(e("httpMimeType"),t.mimeType),i(e("httpBodySize"),o(t.bodySize)),i(e("httpContentSize"),o(t.contentSize)),i(e("httpTransferSize"),o(t.transferSize));let h=t.tls;h&&(i(e("httpTlsProtocol"),h.protocol),i(e("httpTlsCipher"),h.cipher),i(e("httpTlsSubject"),h.subject),i(e("httpTlsSans"),h.sans.join(", ")),i(e("httpTlsIssuer"),h.issuer),i(e("httpTlsValidFrom"),a(h.validFrom)),i(e("httpTlsValidTo"),a(h.validTo)));let c=this.table(r,e("httpConnection"));if(c.setAttribute("part","connection"),c.classList.add("connection"),h?.validTo&&h.validTo.getTime()<Date.now()){let p=[...c.querySelectorAll("th")].find(k=>k.textContent===e("httpTlsValidTo"))?.parentElement;p?.classList.add("expired"),p?.lastElementChild?.append(l("span",{class:"badge",text:` ${e("httpTlsExpired")}`}))}return c}binaryView(t,e){if(!t)return l("p",{class:"none",text:this.t("httpNoBody")});let n=(e??"").toLowerCase().split(";")[0].trim(),r=t.replace(/\s+/g,"");if(!/^[a-z0-9+/]*={0,2}$/i.test(r))return l("p",{class:"none",text:this.t("httpBinary",{type:n||"?"})});if(n==="image/svg+xml"||/(?:xml|html|css|javascript|json|text)/.test(n)){let o;try{o=new TextDecoder().decode(Uint8Array.from(atob(r),a=>a.charCodeAt(0)))}catch{o=""}if(o)return this.bodyView(o,n)}let i=Math.floor(r.length*3/4)-(r.match(/=+$/)?.[0].length??0);if(ft.has(n)){let o=l("img",{class:"body-image",part:"body-image",attrs:{alt:this.t("httpImage",{type:n}),src:`data:${n};base64,${r}`}});return l("figure",{class:"message-body image-body",part:"message-body"},o,l("figcaption",{class:"meta",text:`${n}, ${C(i,this.locale)}`}))}return l("p",{class:"none",text:`${this.t("httpBinary",{type:n||"?"})} (${C(i,this.locale)})`})}bodyView(t,e){if(!t)return l("p",{class:"none",text:this.t("httpNoBody")});let n=(e??"").toLowerCase();if(n.includes("x-www-form-urlencoded"))return this.table(J(t),this.t("httpBody"));let r=t,i="plaintext";if(n.includes("json")||!n&&/^\s*[[{]/.test(t)){let a=T(t,{maxDepth:y().maxDepth});a.ok&&(r=U(a.value,{indent:2,sortKeys:!1}),i="json")}else/xml|html|svg/.test(n)||!n&&/^\s*</.test(t)?i="xml":/javascript|ecmascript/.test(n)?i="javascript":/yaml/.test(n)?i="yaml":/\bcss\b/.test(n)&&(i="css");let o=j(r,{language:i,lineNumbers:!1,startLine:1,highlightRanges:[],diff:!1,highlightLimit:y().highlightLimit});return l("div",{class:"message-body",part:"message-body"},o.element)}codeView(t){let e=this.t,n=this.languages,r=this.language&&n.includes(this.language)?this.language:n[0],i=t.request,o=/json/i.test(m(t.response?.headers??[],"content-type")??m(i.headers,"accept")??"")?"json":"text",a=q(i,r,{responseType:o}),h=_({tabs:n.map(p=>({id:`code-${p}`,label:ut[p]})),selected:`code-${r}`,label:e("codeLanguage"),panelId:`${this.panelId}-code`,onSelect:p=>this.select("language",p.slice(5))});h.classList.add("section-tabs"),h.setAttribute("part","section-tabs");let c=j(a,{language:K[r],lineNumbers:!1,startLine:1,highlightRanges:[],diff:!1,highlightLimit:y().highlightLimit}),d=this.copyButton(()=>a,e("copyCode"),"copy-snippet");return d.classList.add("snippet-copy"),l("div",{class:"http code-panel"},l("div",{class:"code-head"},h,d),l("div",{class:"snippet",part:"snippet",attrs:{id:`${this.panelId}-code`,role:"tabpanel"}},c.element),this.masking&&B(this.parse().exchange)?l("p",{class:"note",text:e("secretsInCode")}):null)}createEditor(){return this.editor?.destroy(),this.editor=new R({text:this.text??"",language:"plaintext",lineNumbers:!1,wrap:!0,highlightLimit:y().highlightLimit,label:this.heading||this.t("editor"),placeholder:this.getAttribute("placeholder")??void 0,onInput:t=>this.edited(t),onChange:t=>w(this,v.CHANGE,{value:t}),history:this.editHistory??void 0}),this.editor}contentEdited(){clearTimeout(this.previewTimer),this.previewTimer=setTimeout(()=>this.renderPreview(),150)}renderPreview(){let t=this.previewHost;if(!t)return;let e=t.scrollTop;t.replaceChildren(...this.renderView()),t.scrollTop=e,this.searchOpen&&this.searchQuery&&this.searchBar?.run()}};function mt(s){let t=0,e=s.indexOf("://");if(e>0&&/^[a-z][a-z0-9+.-]*$/i.test(s.slice(0,e))){let r=e+3;for(;r<s.length&&!"/?#".includes(s[r]);)r+=1;t=r}let n=t;for(;n<s.length&&s[n]!=="?"&&s[n]!=="#";)n+=1;return{origin:s.slice(0,t),path:s.slice(t,n),rest:s.slice(n)}}function gt(s){let t=[],e=new Array(s.length+1).fill(-1);for(let o=s.length-1;o>=0;o-=1)e[o]=s[o]==="}"||s[o]==="/"?o:e[o+1];let n="",r=0,i=()=>{n&&t.push({text:n,param:!1}),n=""};for(;r<s.length;){let o=s[r];if(o==="{"){let a=e[r+1]??-1;if(a>r+1&&s[a]==="}"){i(),t.push({text:s.slice(r,a+1),param:!0}),r=a+1;continue}}else if(o===":"&&s[r-1]==="/"&&/[A-Za-z_]/.test(s[r+1]??"")){let a=r+2;for(;a<s.length&&/\w/.test(s[a]);)a+=1;i(),t.push({text:s.slice(r,a),param:!0}),r=a;continue}n+=o,r+=1}return i(),t}function C(s,t){if(s<1e3)return`${b(s,t)} B`;let e=["kB","MB","GB"],n=s/1e3,r=0;for(;n>=1e3&&r<e.length-1;)n/=1e3,r+=1;return`${new Intl.NumberFormat(t,{maximumFractionDigits:1}).format(n)} ${e[r]}`}var ft=new Set(["image/png","image/gif","image/jpeg","image/jpg","image/webp","image/avif","image/bmp","image/x-icon","image/vnd.microsoft.icon"]);function bt(s){if(s.encoding==="base64"){let t=s.body.replace(/\s+/g,"");return Math.max(0,Math.floor(t.length*3/4)-(t.match(/=+$/)?.[0].length??0))}return new TextEncoder().encode(s.body).length}function yt(s,t){return new Intl.DateTimeFormat(t,{year:"numeric",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",timeZone:"UTC",timeZoneName:"short"}).format(s)}function xt(s){let t=s.replace(/^https?:\/\//i,"");return t.length>90?`${t.slice(0,60)}\u2026${t.slice(-28)}`:t}export{tt as a};
