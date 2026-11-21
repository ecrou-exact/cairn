/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as M,c as z,f as J}from"./chunk-C3AKBLBA.js";import{a as V,b as R}from"./chunk-MGKI6CHL.js";import{a as x}from"./chunk-BNQD3D4I.js";import{b as L,g as N,h as T,i as B,p as $,r as H}from"./chunk-DUXCLZ3D.js";import{U as A,W as j,_ as E,b as v,ba as I,c as f,e as k,o as a,q as _}from"./chunk-7PAHM2BV.js";import{h,k as C,l as S,m as O}from"./chunk-TUK22DTT.js";var q=`/*\r
 * Notebook: Markdown cells, code cells with their prompts, and outputs (text, errors,\r
 * images, HTML tables). Prompts sit in a column on wide screens and above the cell on\r
 * narrow ones.\r
 */\r
.nb-body {\r
  --_prompt: 11ch;\r
  display: grid;\r
  align-content: start;\r
  gap: var(--_space-3);\r
  padding: var(--_space-4);\r
  background: var(--_surface);\r
  overscroll-behavior: auto;\r
}\r
\r
:host([max-height]) .nb-body,\r
.vt[data-fullscreen] .nb-body {\r
  overscroll-behavior: contain;\r
}\r
\r
.nb-cell {\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
}\r
\r
.nb-markdown,\r
.nb-raw {\r
  padding-inline-start: calc(var(--_prompt) + var(--_space-3));\r
}\r
\r
.nb-input,\r
.nb-output {\r
  display: grid;\r
  grid-template-columns: var(--_prompt) minmax(0, 1fr);\r
  gap: var(--_space-3);\r
  align-items: start;\r
}\r
\r
.nb-prompt {\r
  padding-top: var(--_space-2);\r
  color: var(--_accent-fg);\r
  font: 400 var(--_font-size-small) / var(--_line-height) var(--_font-mono);\r
  text-align: end;\r
  white-space: nowrap;\r
  user-select: none;\r
}\r
\r
.nb-prompt.out {\r
  color: var(--_syntax-type);\r
}\r
\r
.nb-source {\r
  position: relative;\r
  min-width: 0;\r
  overflow-x: auto;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_code-bg);\r
}\r
\r
.nb-source .code {\r
  padding-inline: var(--_space-3);\r
}\r
\r
.nb-source > .btn {\r
  position: absolute;\r
  top: 4px;\r
  right: 4px;\r
  opacity: 0;\r
  background: var(--_surface);\r
  transition: opacity var(--_duration-fast) var(--_easing);\r
}\r
\r
.nb-source:hover > .btn,\r
.nb-source > .btn:focus-visible,\r
.nb-source > .btn.done {\r
  opacity: 1;\r
}\r
\r
@media (pointer: coarse) {\r
  .nb-source > .btn {\r
    opacity: 1;\r
  }\r
}\r
\r
.nb-outputs {\r
  display: grid;\r
  gap: var(--_space-1);\r
}\r
\r
.nb-pre {\r
  max-height: 480px;\r
  margin: 0;\r
  padding: var(--_space-2) 0;\r
  overflow: auto;\r
  color: var(--_fg);\r
  font: 400 var(--_font-size) / var(--_line-height) var(--_font-mono);\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
.nb-pre.stderr {\r
  padding-inline: var(--_space-2);\r
  border-radius: var(--_radius-sm);\r
  background: color-mix(in srgb, var(--_danger) 8%, transparent);\r
}\r
\r
.nb-error .nb-pre {\r
  padding: var(--_space-2) var(--_space-3);\r
  border-inline-start: 3px solid var(--_danger);\r
  border-radius: var(--_radius-sm);\r
  background: color-mix(in srgb, var(--_danger) 6%, transparent);\r
  white-space: pre;\r
}\r
\r
.nb-img {\r
  display: block;\r
  max-width: 100%;\r
  height: auto;\r
  margin-block: var(--_space-1);\r
  border-radius: var(--_radius-sm);\r
  /* Plots are drawn for a white page, often with a transparent background: they keep it\r
     in dark themes, or their black axes and labels could not be read. */\r
  background: #fff;\r
}\r
\r
.nb-html {\r
  min-width: 0;\r
  padding-block: var(--_space-1);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-ui);\r
}\r
\r
/* Tables of outputs (pandas DataFrames) are data, not Markdown tables: compact, names kept\r
   as written, numbers aligned to the end. */\r
.nb-html .table-wrap {\r
  width: fit-content;\r
  max-width: 100%;\r
}\r
\r
.nb-html table {\r
  width: auto;\r
  border-collapse: collapse;\r
  font-size: inherit;\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.nb-html :is(th, td) {\r
  padding: 4px var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  background: none;\r
  color: var(--_fg);\r
  font-size: inherit;\r
  letter-spacing: normal;\r
  text-align: end;\r
  text-transform: none;\r
  white-space: nowrap;\r
}\r
\r
.nb-html thead th {\r
  border-bottom-color: var(--_border-strong);\r
  font-weight: 600;\r
}\r
\r
.nb-html tbody th {\r
  font-weight: 600;\r
}\r
\r
.nb-html tbody tr:nth-child(even) {\r
  background: color-mix(in srgb, var(--_surface-sunken) 60%, transparent);\r
}\r
\r
.nb-hidden {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  padding: var(--_space-2) var(--_space-3);\r
  border: 1px dashed var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.nb-none {\r
  margin: 0;\r
  padding-block: var(--_space-2);\r
  color: var(--_fg-muted);\r
  font: italic 400 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.nb-edit > .editor-body {\r
  max-height: min(40vh, 320px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
@container (max-width: 560px) {\r
  .nb-markdown,\r
  .nb-raw {\r
    padding-inline-start: 0;\r
  }\r
\r
  .nb-input,\r
  .nb-output {\r
    grid-template-columns: minmax(0, 1fr);\r
    gap: 0;\r
  }\r
\r
  .nb-prompt {\r
    padding-top: 0;\r
    text-align: start;\r
  }\r
\r
  .nb-prompt:empty {\r
    display: none;\r
  }\r
}\r
`;var m=class extends Error{},c=n=>typeof n=="object"&&n!==null&&!Array.isArray(n);function g(n){return typeof n=="string"?n:Array.isArray(n)?n.map(e=>typeof e=="string"?e:"").join(""):""}function P(n){if(!n.trim())throw new m("empty");let e;try{e=JSON.parse(n)}catch(t){throw new m(`json:${t instanceof Error?t.message:""}`)}return ee(e)}function ee(n){if(!c(n))throw new m("format");let e=c(n.metadata)?n.metadata:{},t=c(e.kernelspec)?e.kernelspec:{},r=c(e.language_info)?e.language_info:{},i=String(r.name??t.language??e.language??"python").slice(0,40).toLowerCase(),o;if(Array.isArray(n.cells))o=n.cells;else if(Array.isArray(n.worksheets)&&c(n.worksheets[0])&&Array.isArray(n.worksheets[0].cells))o=n.worksheets[0].cells;else throw new m("format");return{cells:o.slice(0,5e3).filter(c).map(te),language:i,kernel:String(t.display_name??"").slice(0,100),format:Number(n.nbformat)||4}}function te(n){let e=n.cell_type==="markdown"||n.cell_type==="heading"?"markdown":n.cell_type==="code"?"code":"raw",t=c(n.metadata)?n.metadata:{},r=c(t.jupyter)?t.jupyter:{},i=Array.isArray(t.tags)?t.tags.filter(u=>typeof u=="string").slice(0,50):[],o=g(n.source??n.input);n.cell_type==="heading"&&(o=`${"#".repeat(Math.min(6,Math.max(1,Number(n.level)||1)))} ${o}`);let s={};if(c(n.attachments))for(let[u,d]of Object.entries(n.attachments).slice(0,100))c(d)&&(s[u]=W(d));let l=n.execution_count??n.prompt_number;return{type:e,source:o,count:typeof l=="number"&&Number.isFinite(l)?l:null,outputs:e==="code"&&Array.isArray(n.outputs)?n.outputs.slice(0,200).filter(c).map(ne):[],attachments:s,hidden:r.source_hidden===!0||t.hide_input===!0||i.includes("hide-input")||i.includes("remove-input"),outputsHidden:r.outputs_hidden===!0||i.includes("hide-output")||i.includes("remove-output"),tags:i}}function W(n){let e={};for(let[t,r]of Object.entries(n).slice(0,30))/^[\w.+-]+\/[\w.+-]+$/.test(t)&&(e[t]=typeof r=="string"||Array.isArray(r)?g(r):JSON.stringify(r)??"");return e}function ne(n){let e=String(n.output_type??""),t={type:"display",name:"",count:null,data:{},text:"",ename:"",evalue:""};if(e==="stream")t.type="stream",t.name=n.name==="stderr"||n.stream==="stderr"?"stderr":"stdout",t.text=g(n.text);else if(e==="error"||e==="pyerr")t.type="error",t.ename=String(n.ename??"").slice(0,200),t.evalue=String(n.evalue??"").slice(0,4e3),t.text=Array.isArray(n.traceback)?n.traceback.map(r=>String(r)).join(`
`):"";else{t.type=e==="execute_result"||e==="pyout"?"result":"display";let r=n.execution_count??n.prompt_number;if(t.count=typeof r=="number"?r:null,c(n.data))t.data=W(n.data);else{let i={text:"text/plain",html:"text/html",png:"image/png",jpeg:"image/jpeg",svg:"image/svg+xml",latex:"text/latex",json:"application/json",markdown:"text/markdown"};for(let[o,s]of Object.entries(i))o in n&&(t.data[s]=g(n[o]))}}return t}var re=Object.freeze(["application/vnd.jupyter.widget-view+json","image/png","image/jpeg","image/gif","image/webp","image/svg+xml","text/html","text/markdown","text/latex","application/json","text/plain"]);function F(n){for(let e of re)if(e in n&&e!=="application/vnd.jupyter.widget-view+json")return e;return Object.keys(n).find(e=>e.startsWith("text/"))??null}function y(n){let e=n.replace(/\s+/g,"");return/^[A-Za-z0-9+/]+={0,2}$/.test(e)&&e.length%4===0?e:null}function U(n){let e=["python","r","julia","ruby","perl","bash","sh","powershell"].includes(n.language)?"# ":n.language==="sql"?"-- ":"// ";return n.cells.filter(t=>t.type!=="raw"&&t.source.trim()).map(t=>t.type==="code"?t.source.replace(/\s+$/,""):t.source.trim().split(`
`).map(r=>`${e}${r}`.trimEnd()).join(`
`)).join(`

`)}var X=Object.freeze({nbIn:"In [{count}]:",nbInEmpty:"In [ ]:",nbOut:"Out [{count}]:",nbCells:"{count} cells",nbCell:"Cell {index}",nbCodeCell:"Code cell {index}",nbOutput:"Output",nbCopyCell:"Copy cell",nbCopyScript:"Copy code",nbShowCode:"Show code",nbHideCode:"Hide code",nbCodeHidden:"Code hidden",nbShowOutput:"Show output",nbOutputHidden:"Output hidden",nbStderr:"Error output",nbWidget:"Interactive widget, shown as text: nothing runs here.",nbImage:"Output image",nbNoOutput:"This output has no type that can be shown.",nbInvalidEmpty:"The notebook is empty.",nbInvalidFormat:"This is not a Jupyter notebook: expected the JSON of an .ipynb file.",nbInvalidJson:"The notebook is not valid JSON: {message}",nbNotRun:"Shown only: no code is run."}),D={nbIn:"Entr\xE9e [{count}] :",nbInEmpty:"Entr\xE9e [ ] :",nbOut:"Sortie [{count}] :",nbCells:"{count} cellules",nbCell:"Cellule {index}",nbCodeCell:"Cellule de code {index}",nbOutput:"Sortie",nbCopyCell:"Copier la cellule",nbCopyScript:"Copier le code",nbShowCode:"Afficher le code",nbHideCode:"Masquer le code",nbCodeHidden:"Code masqu\xE9",nbShowOutput:"Afficher la sortie",nbOutputHidden:"Sortie masqu\xE9e",nbStderr:"Sortie d\u2019erreur",nbWidget:"Widget interactif, affich\xE9 en texte : rien ne s\u2019ex\xE9cute ici.",nbImage:"Image de sortie",nbNoOutput:"Cette sortie n\u2019a aucun type qui puisse \xEAtre affich\xE9.",nbInvalidEmpty:"Le carnet est vide.",nbInvalidFormat:"Ce n\u2019est pas un carnet Jupyter : le JSON d\u2019un fichier .ipynb est attendu.",nbInvalidJson:"Le carnet n\u2019est pas du JSON valide : {message}",nbNotRun:"Affichage seulement : aucun code n\u2019est ex\xE9cut\xE9."};O({en:X,fr:D});var oe=["allow","block","same-origin"],Z=["image/png","image/jpeg","image/gif","image/webp"],G=class extends I{static type="notebook";static componentAttributes=Object.freeze(["code","outputs","prompts","line-numbers","code-toggle","allow-html","images","language"]);static presets={simple:{code:!0,outputs:!0,prompts:!0},full:{header:!0,dot:!0,copy:!0,search:!0,download:!0,fullscreen:!0,code:!0,outputs:!0,prompts:!0,"code-toggle":!0}};static styles=[v,x,M,V,q];constructor(){super(),this.parsed=null,this.codeChoice=null,this.revealed=new Set,this.panelId=_("panel"),this.editor=null,this.previewTimer=void 0}disconnectedCallback(){clearTimeout(this.previewTimer),this.editor?.destroy(),super.disconnectedCallback()}contentChanged(){this.parsed=null,this.revealed.clear()}parse(){let e=this.text??"";if(this.parsed?.text===e)return this.parsed;try{this.parsed={text:e,notebook:P(e),error:null}}catch(t){this.parsed={text:e,notebook:null,error:t instanceof Error?t:new Error(String(t))}}return this.parsed}get notebook(){let e=this.parse().notebook;return e?structuredClone(e):null}flag(e){return f(this.getAttribute(e))!==!1}get showCode(){return this.codeChoice??this.flag("code")}languageOf(e){let t=this.getAttribute("language")?.trim()||e.language,r=N(t)??"plaintext";return r!=="plaintext"&&!T(r)&&B(r).then(i=>i&&this.requestRender()),r}renderContent(e){let t=this.t,{notebook:r,error:i}=this.parse(),o=a("div",{class:"panel",attrs:{id:this.panelId}}),s=a("div",{class:"body nb-body",part:"body"});if(i||!r)s.append(E(this.errorText(i)));else{let p=this.languageOf(r);r.cells.forEach((K,Q)=>{let w=this.cellView(K,Q,p);w&&s.append(w)})}let l=[];if(this.editing){let p=this.createEditor();o.classList.add("nb-edit"),o.append(a("div",{class:"body editor-body",part:"body source"},p.element),s),l=this.historyButtons(p)}else o.append(s);let u=!!r?.cells.some(p=>p.type==="code"&&p.source.trim()),d=[this.searchButton(new A(s)),...l,this.feature("code-toggle")&&u&&!this.editing?j({icon:this.showCode?"eye-off":"code",label:this.showCode?t("nbHideCode"):t("nbShowCode"),key:"code-toggle",part:"code-button",pressed:!this.showCode,onClick:()=>{this.codeChoice=!this.showCode,this.render()}}):null,this.editToggleButton(),this.fullscreenButton(),this.feature("download")?this.downloadButton(()=>this.text??"",this.downloadName("notebook.ipynb"),"application/x-ipynb+json"):null,this.feature("copy")&&r&&u?this.copyButton(()=>U(r),t("nbCopyScript")):null],b=r?r.kernel||r.language:"";e.append(...this.chrome({badge:b,actions:d}),o),this.editor?.align()}errorText(e){let t=this.t;if(e instanceof m){if(e.message==="empty")return t("nbInvalidEmpty");if(e.message.startsWith("json:"))return t("nbInvalidJson",{message:e.message.slice(5)})}return t("nbInvalidFormat")}cellView(e,t,r){let i=this.t;if(e.type==="markdown")return e.source.trim()?a("section",{class:"nb-cell nb-markdown",part:"cell cell-markdown",attrs:{"aria-label":i("nbCell",{index:t+1})}},this.markdownView(ie(e.source,e.attachments))):null;if(e.type==="raw")return e.source.trim()?a("section",{class:"nb-cell nb-raw",part:"cell cell-raw",attrs:{"aria-label":i("nbCell",{index:t+1})}},a("pre",{class:"nb-pre",text:e.source})):null;let o=this.showCode&&e.source.trim()!=="",s=this.flag("outputs")&&e.outputs.length>0;if(!o&&!s)return null;let l=a("section",{class:"nb-cell nb-code",part:"cell cell-code",attrs:{"aria-label":i("nbCodeCell",{index:t+1})}}),u=this.flag("prompts");if(o){let d=a("div",{class:"nb-input"});if(u&&d.append(a("span",{class:"nb-prompt",part:"prompt",text:e.count===null?i("nbInEmpty"):i("nbIn",{count:e.count})})),e.hidden&&!this.revealed.has(t))d.append(this.revealButton(t,i("nbShowCode"),i("nbCodeHidden")));else{let b=$(e.source,{language:r,lineNumbers:this.feature("line-numbers"),startLine:1,highlightRanges:[],diff:!1,highlightLimit:h().highlightLimit}),p=a("div",{class:"nb-source",part:"source"},b.element);this.feature("copy")&&p.append(this.copyButton(()=>e.source,i("nbCopyCell"),`copy-cell-${t}`)),d.append(p)}l.append(d)}if(s){let d=a("div",{class:"nb-outputs",attrs:{"aria-label":i("nbOutput")}}),b=-1-t;if(e.outputsHidden&&!this.revealed.has(b))d.append(a("div",{class:"nb-output"},u?a("span",{class:"nb-prompt"}):null,this.revealButton(b,i("nbShowOutput"),i("nbOutputHidden"))));else for(let p of e.outputs)d.append(this.outputView(p,u));l.append(d)}return l}revealButton(e,t,r){return a("div",{class:"nb-hidden"},a("span",{text:r}),a("button",{class:"text-btn",text:t,attrs:{type:"button","data-focus-key":`reveal-${e}`},on:{click:()=>{this.revealed.add(e),this.render()}}}))}outputView(e,t){let r=this.t,i=t?a("span",{class:"nb-prompt out",part:"prompt",text:e.type==="result"&&e.count!==null?r("nbOut",{count:e.count}):""}):null,o,s=e.type==="stream"?"stream":e.type==="error"?"error":"data";if(e.type==="stream")o=this.ansiBlock(e.text.replace(/\n$/,"")),e.name==="stderr"&&(o.classList.add("stderr"),o.setAttribute("aria-label",r("nbStderr")));else if(e.type==="error")o=this.ansiBlock(e.text||`${e.ename}: ${e.evalue}`),o.setAttribute("role","note");else{let l=this.dataView(e.data);o=l.element,s=l.kind}return a("div",{class:`nb-output nb-${s}`,part:`output output-${s}`},i,o)}dataView(e){let t=this.t,r=F(e),i=(e["text/plain"]??"").slice(0,300)||t("nbImage");if(r&&Z.includes(r)){let o=y(e[r]);if(o)return{element:a("img",{class:"nb-img",attrs:{src:`data:${r};base64,${o}`,alt:i,loading:"lazy",decoding:"async"}}),kind:"image"};r="text/plain"in e?"text/plain":null}if(r==="image/svg+xml")return{element:a("img",{class:"nb-img",attrs:{src:`data:image/svg+xml;base64,${ae(e[r])}`,alt:i}}),kind:"image"};if(r==="text/html"){let o=a("div",{class:"nb-html markdown"});o.append(L(e[r],{images:this.imagePolicy,externalLinks:"new-tab"}));for(let s of Array.from(o.querySelectorAll("table"))){let l=a("div",{class:"table-wrap",attrs:{tabindex:"0",role:"region","aria-label":t("table")}});s.replaceWith(l),l.append(s)}return{element:o,kind:"html"}}if(r==="text/markdown")return{element:this.markdownView(e[r]),kind:"html"};if(r==="application/json"){let o=e[r];try{o=JSON.stringify(JSON.parse(o),null,2)}catch{}return{element:a("pre",{class:"nb-pre",text:o}),kind:"json"}}if(r){let o=this.ansiBlock(e[r].replace(/\n$/,""));return"application/vnd.jupyter.widget-view+json"in e&&o.setAttribute("title",t("nbWidget")),{element:o,kind:"text"}}return{element:a("p",{class:"nb-none",text:t("nbNoOutput")}),kind:"text"}}get imagePolicy(){return k(this.getAttribute("images"),oe,"allow")}markdownView(e){let t=a("div",{class:"markdown",part:"markdown"});try{let{fragment:r}=R(e,{allowHtml:f(this.getAttribute("allow-html"))!==!1,images:this.imagePolicy,externalLinks:"new-tab",anchors:!1,anchorLabel:this.t("anchor"),tableLabel:this.t("table"),highlightLimit:h().highlightLimit,onLanguageLoaded:()=>this.requestRender()});t.append(r)}catch{t.append(a("pre",{class:"nb-pre",text:e}))}return t}ansiBlock(e){let t=a("pre",{class:"nb-pre"});return z(e).forEach((r,i)=>{i&&t.append(`
`);for(let o of r)t.append(J(o))}),t}createEditor(){return this.editor?.destroy(),this.editor=new H({text:this.text??"",language:"json",lineNumbers:!0,wrap:!1,highlightLimit:h().highlightLimit,label:this.heading||this.t("editor"),placeholder:this.getAttribute("placeholder")??void 0,onInput:e=>this.edited(e),onChange:e=>S(this,C.CHANGE,{value:e}),history:this.editHistory??void 0}),this.editor}contentEdited(){clearTimeout(this.previewTimer),this.parsed=null,this.previewTimer=setTimeout(()=>this.render(),300)}};function ie(n,e){return Object.keys(e).length?n.replace(/attachment:([^\s)"'<>]+)/g,(t,r)=>{let i=e[decodeURIComponent(r)]??e[r];if(!i)return t;let o=Z.find(l=>l in i),s=o?y(i[o]):null;return o&&s?`data:${o};base64,${s}`:t}):n}function ae(n){let e=new TextEncoder().encode(n),t="";for(let r=0;r<e.length;r+=32768)t+=String.fromCharCode(...e.subarray(r,r+32768));return btoa(t)}export{G as a};
