/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as D,b as H,c as P,d as h,f as S}from"./chunk-C3AKBLBA.js";import{d as O}from"./chunk-JRUMHT4D.js";import{a as x}from"./chunk-BNQD3D4I.js";import{k as N,n as L,o as b,q as M,r as $}from"./chunk-DUXCLZ3D.js";import{P as k,U as C,W as A,b as w,ba as E,d as f,o as l}from"./chunk-7PAHM2BV.js";import{h as T,k as y,l as g,q as _}from"./chunk-TUK22DTT.js";var B=`/*\r
 * Terminal: commands and ANSI-colored output on the code background.\r
 * The 16 ANSI colors map to theme colors, so every theme keeps its contrast;\r
 * each can be overridden with a public token (--vt-ansi-red\u2026).\r
 */\r
.vt {\r
  --_prompt: var(--vt-terminal-prompt, var(--_accent-fg));\r
}\r
\r
.term-body {\r
  background: var(--_code-bg);\r
}\r
\r
.terminal {\r
  width: max-content;\r
  min-width: 100%;\r
  padding: var(--_space-3) var(--_space-4);\r
  color: var(--_code-fg);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size);\r
  font-variant-ligatures: none;\r
  line-height: var(--_line-height);\r
  tab-size: 8;\r
  white-space: pre;\r
}\r
\r
.terminal.wrapped {\r
  width: auto;\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
.terminal .line {\r
  display: block;\r
}\r
\r
/* ---------- Commands ---------- */\r
\r
.entry.command {\r
  position: relative;\r
  padding-right: calc(var(--_space-5) + 8px);\r
}\r
\r
.entry.command + .entry.command,\r
.entry.output + .entry.command {\r
  margin-top: var(--_space-1);\r
}\r
\r
.prompt {\r
  color: var(--_prompt);\r
  font-weight: 600;\r
  user-select: none;\r
  -webkit-user-select: none;\r
}\r
\r
.cmd {\r
  color: var(--_code-fg);\r
}\r
\r
.cmd-copy {\r
  position: absolute;\r
  top: 50%;\r
  right: 0;\r
  width: 26px;\r
  height: 26px;\r
  margin-top: -13px;\r
  opacity: 0;\r
  transition: opacity var(--_duration-fast) var(--_easing);\r
}\r
\r
.entry.command:hover .cmd-copy,\r
.cmd-copy:focus-visible,\r
.cmd-copy.done {\r
  opacity: 1;\r
}\r
\r
@media (hover: none) {\r
  .cmd-copy {\r
    opacity: 0.7;\r
  }\r
}\r
\r
/* ---------- Output ---------- */\r
\r
.entry.output {\r
  color: color-mix(in srgb, var(--_code-fg) 88%, var(--_code-bg-solid));\r
}\r
\r
.collapsed-lines {\r
  display: none;\r
}\r
\r
.output-more {\r
  display: block;\r
  margin: var(--_space-1) 0 var(--_space-2);\r
  padding: 2px var(--_space-2);\r
  border: 1px dashed color-mix(in srgb, var(--_code-gutter) 60%, transparent);\r
  border-radius: var(--_radius-sm);\r
  background: none;\r
  color: var(--_accent-fg);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-small);\r
  white-space: normal;\r
  cursor: pointer;\r
}\r
\r
.output-more:hover {\r
  border-style: solid;\r
}\r
\r
/* ---------- Typing replay ---------- */\r
\r
.entry.typing-hidden {\r
  visibility: hidden;\r
}\r
\r
.typing-cursor {\r
  display: inline-block;\r
  width: 0.6em;\r
  height: 1.15em;\r
  margin-left: 1px;\r
  vertical-align: text-bottom;\r
  background: var(--_accent);\r
  animation: vt-caret 1s steps(1) infinite;\r
}\r
\r
@keyframes vt-caret {\r
  50% {\r
    opacity: 0;\r
  }\r
}\r
\r
@media (prefers-reduced-motion: reduce) {\r
  .typing-cursor {\r
    animation: none;\r
  }\r
}\r
\r
/* ---------- Edit mode: editor above, live preview below ---------- */\r
\r
.term-edit {\r
  display: grid;\r
  grid-template-rows: auto auto;\r
}\r
\r
.term-edit > .editor-body {\r
  max-height: min(40vh, 360px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
.vt[data-fullscreen] .term-edit {\r
  flex: 1 1 auto;\r
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);\r
  min-height: 0;\r
}\r
\r
.vt[data-fullscreen] .term-edit > .editor-body {\r
  max-height: none;\r
}\r
`;var U=Object.freeze(["$","\u276F"]),q=8;function j(a){if(a===null)return[...U];let t=a.trim();return!t||t.toLowerCase()==="none"?[]:t.split(/\s+/).filter(r=>r.length<=16).slice(0,q)}function G(a){if(!a.length)return()=>null;let t=a.slice().sort((e,n)=>n.length-e.length).map(e=>e.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")),r=new RegExp(`^([\\w@:~./\\\\-]{0,120}?(?:${t.join("|")}))(?: |$)`);return e=>{let n=r.exec(e);return n?{prompt:n[1],rest:e.slice(n[0].length)}:null}}function I(a,t){let r=G(t),e=[],n=null,o=null;return a.forEach((p,s)=>{let c=h(p);if(o){o.lines.push(c),/\\$/.test(c)||(o=null);return}let i=r(c);if(i){n=null;let d={type:"command",prompt:i.prompt,lines:[i.rest],line:s+1};e.push(d),/\\$/.test(i.rest)&&(o=d);return}n||(n={type:"output",lines:[],line:s+1},e.push(n)),n.lines.push(p)}),e}function R(a){return a.filter(t=>t.type==="command").map(t=>t.lines.join(`
`)).join(`
`)}var u=class{constructor(t,r){this.container=t,this.options=r,this.abort=null,this.finals=new Map,this.observer=null,this.playing=!1}start(){this.stop();let t=this.entries();if(t.length){for(let r of t)r.classList.add("typing-hidden");if(this.playing=!0,typeof IntersectionObserver>"u"){this.play();return}this.observer=new IntersectionObserver(r=>{r.some(e=>e.isIntersecting)&&(this.observer?.disconnect(),this.observer=null,this.play())},{threshold:.2}),this.observer.observe(this.container)}}entries(){return Array.from(this.container.querySelectorAll(".entry"))}async play(){let t=new AbortController;this.abort=t;let{signal:r}=t;try{for(let e of this.entries())e.classList.remove("typing-hidden"),e.classList.contains("command")?(await this.type(e,r),await v(350,r)):await v(250,r);this.end()}catch{}}async type(t,r){let e=t.querySelector(".cmd");if(!e)return;let n=Array.from(e.childNodes);this.finals.set(e,n);let o=this.options.commandText(e),p=document.createTextNode(""),s=document.createElement("span");s.className="typing-cursor",s.setAttribute("aria-hidden","true"),e.replaceChildren(p,s);let c=this.options.speed;for(let i=1;i<=o.length;i+=1)p.data=o.slice(0,i),await v(c*(.6+i*7919%10/12),r);e.replaceChildren(...n),this.finals.delete(e)}stop(){this.abort?.abort(),this.abort=null,this.observer?.disconnect(),this.observer=null;for(let[t,r]of this.finals)t.replaceChildren(...r);this.finals.clear();for(let t of this.entries())t.classList.remove("typing-hidden");this.playing&&this.end()}end(){this.playing=!1,this.options.onEnd?.()}};function v(a,t){return new Promise((r,e)=>{if(t.aborted){e(new Error("stopped"));return}let n=setTimeout(r,a);t.addEventListener("abort",()=>{clearTimeout(n),e(new Error("stopped"))},{once:!0})})}var K=2e3,z=class extends E{static type="terminal";static fromData=O;static dataAttributes=Object.freeze(["prompt","label"]);static componentAttributes=Object.freeze(["prompt","escapes","colors","command-copy","collapse-output","typing","typing-speed","wrap"]);static presets={simple:{colors:!0,"command-copy":!0,wrap:!0},full:{header:!0,dot:!0,copy:!0,search:!0,download:!0,fullscreen:!0,colors:!0,"command-copy":!0,wrap:!0}};static styles=[w,x,D,B];static keepCarriageReturns=!0;constructor(){super(),this.parsed=null,this.expanded=new Set,this.player=null,this.editor=null,this.previewHost=null,this.previewTimer=void 0,this.commandTexts=new WeakMap,this.typingDone=!1}disconnectedCallback(){this.player?.stop(),this.player=null,clearTimeout(this.previewTimer),this.editor?.destroy(),super.disconnectedCallback()}contentChanged(){this.parsed=null,this.expanded.clear(),this.typingDone=!1}attributeChangedCallback(t,r,e){(t==="prompt"||t==="escapes")&&(this.parsed=null),t==="typing"&&(this.typingDone=!1),super.attributeChangedCallback(t,r,e)}parse(){let t=this.text??"",r=this.getAttribute("prompt"),e=this.feature("escapes"),n=`${r}\0${e}\0${t}`;if(this.parsed?.key!==n){let o=e?H(t):t;this.parsed={key:n,entries:I(P(o),j(r))}}return this.parsed.entries}get commands(){return this.parse().filter(t=>t.type==="command").map(t=>t.lines.join(`
`))}get entries(){return this.parse().map(t=>t.type==="command"?{type:"command",prompt:t.prompt,text:t.lines.join(`
`)}:{type:"output",text:t.lines.map(h).join(`
`)})}plainText(){return this.parse().map(t=>t.type==="command"?`${t.prompt} ${t.lines.join(`
`)}`:t.lines.map(h).join(`
`)).join(`
`)}renderContent(t){let r=this.t;this.player?.stop(),this.player=null;let e=l("div",{class:"panel"}),n=[],o=null;if(this.editing){let i=this.createEditor();this.previewHost=l("div",{class:"body term-body term-preview",part:"body preview"}),e.classList.add("term-edit"),e.append(l("div",{class:"body editor-body",part:"body source"},i.element),this.previewHost),this.renderPreview(),n=this.historyButtons(i)}else this.previewHost=null,e.append(this.renderTranscript());let p={run:i=>{this.player?.stop();let d=this.root.querySelector(".terminal");return o=d?new C(d,{skip:".prompt, .sr-only, button"}):null,o?o.run(i):{total:0,capped:!1}},go:i=>{let d=o?.go(i)??null,m=d?.closest(".collapsed-lines");m&&m.classList.remove("collapsed-lines"),M(d)},clear:()=>o?.clear()},s=this.feature("typing")&&!this.editing,c=[this.searchButton(p),...n,s?A({icon:"replay",label:r("replay"),key:"replay",part:"replay-button",onClick:()=>this.replay()}):null,this.editToggleButton(),this.fullscreenButton(),this.feature("download")?this.downloadButton(()=>this.plainText(),this.downloadName("session.txt"),"text/plain"):null,this.feature("copy")?this.copyButton(()=>R(this.parse()),r("copyCommands")):null];t.append(...this.chrome({badge:"",actions:c}),e),this.editor?.align(),s&&!this.typingDone&&!V()&&this.replay()}replay(){let t=this.root.querySelector(".terminal");!t||this.editing||(this.typingDone=!0,this.player?.stop(),this.player=new u(t,{speed:f(this.getAttribute("typing-speed"),{min:5,max:200,fallback:35}),commandText:r=>this.commandTexts.get(r)??"",onEnd:()=>g(this,y.TYPING_END,{})}),this.player.start())}renderTranscript(){let t=this.parse(),r=l("div",{class:`terminal${this.feature("wrap")?" wrapped":""}`,part:"terminal"});return(!t.length||t.length===1&&Q(t[0]))&&r.append(l("div",{class:"empty",part:"empty",text:this.t("empty")})),t.forEach((e,n)=>{r.append(e.type==="command"?this.commandRow(e,n):this.outputBlock(e,n))}),l("div",{class:"body term-body",part:"body",attrs:{tabindex:"0",role:"region","aria-label":this.heading||this.t("terminal")}},r)}commandRow(t,r){let e=t.lines.join(`
`),n=l("span",{class:"cmd",part:"command-text"});this.commandTexts.set(n,e),e.length<=K?n.append(N(e,"bash")):n.textContent=e;let o=l("div",{class:"entry command",part:"command",attrs:{"data-line":t.line}},l("span",{class:"sr-only",text:`${this.t("command")}: `}),l("span",{class:"prompt",part:"prompt",text:`${t.prompt} `,attrs:{"aria-hidden":"true"}}),n);if(this.feature("command-copy")&&e.trim()){let p=this.copyButton(()=>e,this.t("copyCommand"),`copy-command-${r}`);p.classList.add("cmd-copy"),p.setAttribute("part","button command-copy"),o.append(p)}return o}outputBlock(t,r){let e=l("div",{class:"entry output",part:"output",attrs:{"data-line":t.line}}),n=t.lines,o=f(this.getAttribute("collapse-output"),{min:0,max:1e5,fallback:0}),p=o>0&&n.length>o+1&&!this.expanded.has(r),s=p?o:n.length;if(this.appendLines(e,n,0,s),p){let c=l("div",{class:"collapsed-lines"});this.appendLines(c,n,s,n.length);let i=l("button",{class:"more output-more",part:"output-more",text:this.t("showMoreLines",{count:_(n.length-s,this.locale)}),attrs:{type:"button","data-focus-key":`output-more-${r}`},on:{click:()=>{this.expanded.add(r),c.classList.remove("collapsed-lines"),i.remove()}}});e.append(c,i)}return e}appendLines(t,r,e,n){let o=this.feature("colors"),p=(s,c,i)=>{let d=document.createDocumentFragment();for(let m=c;m<i;m+=1)d.append(W(r[m],o));s.appendChild(d)};if(n-e<=L){p(t,e,n);return}for(let s=e;s<n;s+=b){let c=Math.min(n,s+b),i=l("span",{class:"chunk",attrs:{"data-count":c-s}});i.style.setProperty("--_chunk-lines",String(c-s)),t.append(i),s===e?p(i,s,c):(i.setAttribute("data-pending",""),k(i,()=>{i.removeAttribute("data-pending"),p(i,s,c)}))}}createEditor(){return this.editor?.destroy(),this.editor=new $({text:this.text??"",language:"plaintext",lineNumbers:!1,wrap:!0,highlightLimit:T().highlightLimit,label:this.heading||this.t("editor"),placeholder:this.getAttribute("placeholder")??void 0,onInput:t=>this.edited(t),onChange:t=>g(this,y.CHANGE,{value:t}),history:this.editHistory??void 0}),this.editor}contentEdited(){this.parsed=null,clearTimeout(this.previewTimer),this.previewTimer=setTimeout(()=>this.renderPreview(),120)}renderPreview(){let t=this.previewHost;if(!t)return;let r=t.scrollTop,e=this.renderTranscript();t.replaceChildren(...Array.from(e.childNodes)),t.scrollTop=r,this.searchOpen&&this.searchQuery&&this.searchBar?.run()}};function Q(a){return a.type==="output"&&a.lines.every(t=>!h(t).trim())}function V(){return typeof matchMedia=="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches}function W(a,t){let r=l("span",{class:"line"});for(let e of a)r.append(t?S(e):document.createTextNode(e.text));return r.append(`
`),r}export{z as a};
