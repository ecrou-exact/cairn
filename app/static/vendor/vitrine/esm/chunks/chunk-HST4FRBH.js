/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{r as S}from"./chunk-DUXCLZ3D.js";import{U as E,_ as M,ba as C,c as w,o as l,q as x}from"./chunk-7PAHM2BV.js";import{f as y,h as f,k as v,l as k,m as T,q as g}from"./chunk-TUK22DTT.js";var A=`/*\r
 * Math: display equations, numbers, inline math in text, and TeX that could not be read.\r
 * The rules for <math> come from Temml's own stylesheet (Temml-Latin-Modern.css, MIT\r
 * License), without its web fonts: browsers draw MathML with a math font of the system.\r
 */\r
:host([inline]) {\r
  display: inline;\r
  vertical-align: baseline;\r
}\r
\r
.vt.inline-math {\r
  display: inline;\r
  border: 0;\r
  border-radius: 0;\r
  background: none;\r
  color: inherit;\r
  font: inherit;\r
}\r
\r
.math-body {\r
  display: grid;\r
  gap: var(--_space-3);\r
  padding: var(--_space-4) var(--_space-5);\r
  overflow-x: auto;\r
  background: var(--_surface);\r
  color: var(--_fg);\r
  font-size: var(--vt-math-size, 1.15em);\r
  line-height: 1.6;\r
}\r
\r
.math-body.inline {\r
  display: inline;\r
  padding: 0;\r
  overflow: visible;\r
  background: none;\r
  color: inherit;\r
  font-size: inherit;\r
  line-height: inherit;\r
}\r
\r
/* Text with math: a single flow, paragraphs at blank lines. */\r
:host([delimiters]) .math-body:not(.inline) {\r
  display: block;\r
  font-family: var(--vt-font-body, inherit);\r
  font-size: var(--vt-font-size-body, inherit);\r
  line-height: 1.65;\r
  white-space: pre-line;\r
}\r
\r
:host([delimiters]) .math-display {\r
  margin-block: var(--_space-3);\r
  white-space: normal;\r
}\r
\r
.math-break {\r
  display: block;\r
  height: var(--_space-3);\r
}\r
\r
.math-display {\r
  position: relative;\r
  min-width: 0;\r
  overflow-x: auto;\r
  overflow-y: hidden;\r
  text-align: center;\r
}\r
\r
.math-display.numbered {\r
  padding-inline: 4em;\r
}\r
\r
.math-number {\r
  position: absolute;\r
  top: 50%;\r
  inset-inline-end: 0;\r
  transform: translateY(-50%);\r
  color: var(--_fg-muted);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-ui);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.math-tex {\r
  color: var(--_code-fg);\r
  font: 400 var(--_font-size) / var(--_line-height) var(--_font-mono);\r
  overflow-wrap: anywhere;\r
  white-space: pre-wrap;\r
}\r
\r
.math-display .math-tex {\r
  display: block;\r
  text-align: start;\r
}\r
\r
.math-display.error {\r
  display: grid;\r
  gap: var(--_space-1);\r
  padding: var(--_space-2) var(--_space-3);\r
  border-inline-start: 3px solid var(--_danger);\r
  border-radius: var(--_radius-sm);\r
  background: color-mix(in srgb, var(--_danger) 6%, transparent);\r
  text-align: start;\r
}\r
\r
.math-error {\r
  color: var(--_danger);\r
  font: 400 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.math-inline.error .math-error {\r
  margin-inline-start: 0.5ch;\r
}\r
\r
.math-edit > .editor-body {\r
  max-height: min(40vh, 320px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
/* ---------- MathML: Temml-Latin-Modern.css of Temml 0.14.0 (MIT License), without its fonts ---------- */\r
\r
math {\r
  font-style: normal;\r
  font-weight: normal;\r
  line-height: normal;\r
  font-size-adjust: none;\r
  text-indent: 0;\r
  text-transform: none;\r
  letter-spacing: normal;\r
  word-wrap: normal;\r
  direction: ltr;\r
  /* Prevent Firefox from omitting the dot on i or j. */\r
  font-feature-settings: 'dtls' off;\r
}\r
\r
math * {\r
  border-color: currentColor;\r
}\r
\r
math {\r
  font-family: var(--vt-font-math, 'Latin Modern Math', 'STIX Two Math', 'Cambria Math', math);\r
}\r
\r
/* display: block is necessary in Firefox and Safari.\r
 * Not in Chromium, which recognizes display: "block math" written inline. */\r
math.tml-display {\r
  display: block;\r
  width: 100%;\r
}\r
\r
/* Cramped superscripts in WebKit */\r
mfrac > :nth-child(2),\r
msqrt,\r
mover > :first-child {\r
  math-shift: compact;\r
}\r
\r
.menclose {\r
  display: inline-block;\r
  position: relative;\r
  padding: 0.5ex 0ex;\r
}\r
.tml-cancelto {\r
  display: inline-block;\r
  position: absolute;\r
  top: 0;\r
  left: 0;\r
  padding: 0.5ex 0ex;\r
  background-color: currentColor;\r
  /* Use the SVG as an alpha mask (painted by background-color) */\r
  -webkit-mask-image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'><defs><marker id='a' markerHeight='5' markerUnits='strokeWidth' markerWidth='7' orient='auto' refX='7' refY='2.5'><path fill='black' d='m0 0 7 2.5L0 5z'/></marker></defs><line x2='100%25' y1='100%25' stroke='black' stroke-width='.06em' marker-end='url(%23a)' vector-effect='non-scaling-stroke'/></svg>");\r
  mask-image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'><defs><marker id='a' markerHeight='5' markerUnits='strokeWidth' markerWidth='7' orient='auto' refX='7' refY='2.5'><path fill='black' d='m0 0 7 2.5L0 5z'/></marker></defs><line x2='100%25' y1='100%25' stroke='black' stroke-width='.06em' marker-end='url(%23a)' vector-effect='non-scaling-stroke'/></svg>");\r
  -webkit-mask-repeat: no-repeat;\r
  mask-repeat: no-repeat;\r
  -webkit-mask-size: 100% 100%;\r
  mask-size: 100% 100%;\r
  -webkit-mask-position: 0 0;\r
  mask-position: 0 0;\r
}\r
\r
@supports (-moz-appearance: none) {\r
  /* \\vec w/o italic correction for Firefox */\r
  .tml-vec {\r
    transform: scale(0.75);\r
  }\r
  /* Fix \\cancelto in Firefox */\r
  .ff-narrow {\r
    width: 0em;\r
  }\r
  .ff-nudge-left {\r
    margin-left: -0.2em;\r
  }\r
  /* Squash hidden mrows in \\bordermatrix. Messes with centering, but necessary to squash. */\r
  .ff-squash mtd {\r
    display: block;\r
    height: 0;\r
  }\r
}\r
\r
@supports (not (-moz-appearance: none)) {\r
  /* Chromium and WebKit */\r
  /* prime vertical alignment */\r
  /* Italic correction on superscripts */\r
  .tml-sml-pad {\r
    padding-left: 0.05em;\r
  }\r
  .tml-med-pad {\r
    padding-left: 0.1em;\r
  }\r
  .tml-lrg-pad {\r
    padding-left: 0.15em;\r
  }\r
}\r
\r
@supports (-webkit-backdrop-filter: blur(1px)) {\r
  /* WebKit vertical & italic correction on accents */\r
  .wbk-acc {\r
    /* lower by x-height distance */\r
    transform: translate(0em, 0.431em);\r
  }\r
  .wbk-sml {\r
    transform: translate(0.07em, 0);\r
  }\r
  .wbk-sml-acc {\r
    transform: translate(0.07em, 0.431em);\r
  }\r
  .wbk-sml-vec {\r
    transform: scale(0.75) translate(0.07em, 0);\r
  }\r
  .wbk-med {\r
    transform: translate(0.14em, 0);\r
  }\r
  .wbk-med-acc {\r
    transform: translate(0.14em, 0.431em);\r
  }\r
  .wbk-med-vec {\r
    transform: scale(0.75) translate(0.14em, 0);\r
  }\r
  .wbk-lrg {\r
    transform: translate(0.21em, 0);\r
  }\r
  .wbk-lrg-acc {\r
    transform: translate(0.21em, 0.431em);\r
  }\r
  .wbk-lrg-vec {\r
    transform: scale(0.75) translate(0.21em, 0);\r
  }\r
}\r
\r
/* \\cancel & \\phase use background images. Get them to print. */\r
menclose {\r
  -webkit-print-color-adjust: exact; /* Chrome & Edge */\r
  print-color-adjust: exact;\r
}\r
\r
/* Array cell justification in Firefox & WebKit */\r
.tml-right {\r
  text-align: right;\r
}\r
.tml-left {\r
  text-align: left;\r
}\r
\r
/* For CD labels that grow to the left in Firefox and WebKit */\r
.tml-shift-left {\r
  margin-left: -200%;\r
}\r
\r
/* Styles for Chromium only */\r
@supports (not (-webkit-backdrop-filter: blur(1px))) and (not (-moz-appearance: none)) {\r
  /* Italic correction on accents */\r
  .chr-sml {\r
    transform: translate(0.07em, 0);\r
  }\r
  .chr-sml-vec {\r
    transform: scale(0.75) translate(0.07em, 0);\r
  }\r
  .chr-med {\r
    transform: translate(0.14em, 0);\r
  }\r
  .chr-med-vec {\r
    transform: scale(0.75) translate(0.14em, 0);\r
  }\r
  .chr-lrg {\r
    transform: translate(0.21em, 0);\r
  }\r
  .chr-lrg-vec {\r
    transform: scale(0.75) translate(0.21em, 0);\r
  }\r
\r
  /* For CD labels that grow to the left */\r
  .tml-shift-left {\r
    margin-left: -100%;\r
  }\r
\r
  /* MathML Core & Chromium do not support the MathML 3.0 element <menclose> attributes. */\r
  /* So use styles. */\r
  menclose {\r
    position: relative;\r
    padding: 0.5ex 0ex;\r
  }\r
\r
  .tml-overline {\r
    padding: 0.1em 0 0 0;\r
    border-top: 0.065em solid;\r
  }\r
\r
  .tml-underline {\r
    padding: 0 0 0.1em 0;\r
    border-bottom: 0.065em solid;\r
  }\r
\r
  .tml-cancel {\r
    display: inline-block;\r
    position: absolute;\r
    left: 0.5px;\r
    bottom: 0;\r
    width: 100%;\r
    height: 100%;\r
    background-color: currentColor;\r
  }\r
  .upstrike {\r
    clip-path: polygon(0.05em 100%, 0em calc(100% - 0.05em), calc(100% - 0.05em) 0em, 100% 0.05em);\r
  }\r
  .downstrike {\r
    clip-path: polygon(0em 0.05em, 0.05em 0em, 100% calc(100% - 0.05em), calc(100% - 0.05em) 100%);\r
  }\r
  .sout {\r
    clip-path: polygon(\r
      0em calc(55% + 0.0333em),\r
      0em calc(55% - 0.0333em),\r
      100% calc(55% - 0.0333em),\r
      100% calc(55% + 0.0333em)\r
    );\r
  }\r
  .tml-xcancel {\r
    clip-path: polygon(\r
      0.05em 0em,\r
      0em 0.05em,\r
      calc(50% - 0.05em) 50%,\r
      0em calc(100% - 0.05em),\r
      0.05em 100%,\r
      50% calc(50% + 0.05em),\r
      calc(100% - 0.05em) 100%,\r
      100% calc(100% - 0.05em),\r
      calc(50% + 0.05em) 50%,\r
      100% 0.05em,\r
      calc(100% - 0.05em) 0%,\r
      50% calc(50% - 0.05em)\r
    );\r
  }\r
\r
  .longdiv-top {\r
    border-top: 0.067em solid;\r
    padding: 0.1em 0.2em 0.2em 0.433em;\r
  }\r
  .longdiv-arc {\r
    position: absolute;\r
    top: 0;\r
    bottom: 0.1em;\r
    left: -0.4em;\r
    width: 0.7em;\r
    border: 0.067em solid;\r
    transform: translateY(-0.067em);\r
    border-radius: 70%;\r
    clip-path: inset(0 0 0 0.4em);\r
    box-sizing: border-box;\r
  }\r
  .menclose {\r
    display: inline-block;\r
    text-align: left;\r
    position: relative;\r
  }\r
\r
  .phasor-bottom {\r
    border-bottom: 0.067em solid;\r
    padding: 0.2em 0.2em 0.1em 0.6em;\r
  }\r
  .phasor-angle {\r
    display: inline-block;\r
    position: absolute;\r
    left: 0.5px;\r
    bottom: -0.04em;\r
    height: 100%;\r
    aspect-ratio: 0.5;\r
    background-color: currentColor;\r
    clip-path: polygon(0.05em 100%, 0em calc(100% - 0.05em), calc(100% - 0.05em) 0em, 100% 0.05em);\r
  }\r
\r
  .tml-fbox {\r
    padding: 3pt;\r
    border: 1px solid;\r
  }\r
\r
  .circle-pad {\r
    padding: 0.267em;\r
  }\r
  .textcircle {\r
    position: absolute;\r
    top: 0;\r
    bottom: 0;\r
    right: 0;\r
    left: 0;\r
    border: 0.067em solid;\r
    border-radius: 50%;\r
  }\r
\r
  .actuarial {\r
    padding: 0.03889em 0.03889em 0 0.03889em;\r
    border-width: 0.08em 0.08em 0em 0em;\r
    border-style: solid;\r
    margin-right: 0.03889em;\r
  }\r
\r
  /* Stretch \\widetilde */\r
  .tml-tilde-2 {\r
    transform: scale(2, 1.1);\r
  }\r
  .tml-tilde-3 {\r
    transform: scale(3, 1.3);\r
  }\r
  .tml-tilde-4 {\r
    transform: scale(4, 1.4);\r
  }\r
  /* Stretch \\widehat */\r
  .tml-hat-1 {\r
    transform: scale(1.8, 1.1);\r
  }\r
  .tml-hat-2 {\r
    transform: scale(3.5, 1.1);\r
  }\r
  .tml-hat-3 {\r
    transform: scale(5.4, 1.3);\r
  }\r
  .tml-hat-4 {\r
    transform: scale(7.2, 1.4);\r
  }\r
\r
  /* set array cell justification */\r
  .tml-right {\r
    text-align: -webkit-right;\r
  }\r
  .tml-left {\r
    text-align: -webkit-left;\r
  }\r
}\r
\r
.special-fraction {\r
  font-family: 'Times New Roman', Times, 'STIX TWO', Tinos, serif;\r
}\r
\r
/* flex-wrap for line-breaking in Chromium */\r
math {\r
  display: inline-flex;\r
  flex-wrap: wrap;\r
  align-items: baseline;\r
}\r
math > mrow {\r
  padding: 0.5ex 0ex;\r
}\r
\r
/* Default mtd top padding is 0.5ex per MathML-Core and user-agent CSS */\r
/* We adjust for jot and small */\r
mtable.tml-jot > mtr > mtd {\r
  padding-top: 0.7ex;\r
  padding-bottom: 0.7ex;\r
}\r
mtable.tml-small mtd {\r
  padding-top: 0.35ex;\r
  padding-bottom: 0.35ex;\r
}\r
\r
/* Firefox */\r
@supports (-moz-appearance: none) {\r
  /* Avoid flex-wrap */\r
  math {\r
    display: inline;\r
  }\r
  math > mrow {\r
    padding: 0;\r
  }\r
  /* Adjust Firefox spacing between array rows */\r
  mtd,\r
  mtable.tml-small mtd {\r
    padding-top: 0;\r
    padding-bottom: 0;\r
  }\r
  mtable.tml-jot > mtr > mtd {\r
    padding-top: 0.2ex;\r
    padding-bottom: 0.2ex;\r
  }\r
}\r
\r
/* AMS environment auto-numbering via CSS counter. */\r
.tml-eqn::before {\r
  counter-increment: tmlEqnNo;\r
  content: '(' counter(tmlEqnNo) ')';\r
}\r
\r
.math-body {\r
  counter-reset: tmlEqnNo;\r
}\r
`;function _(a){let e=[],t="",r=0;for(let i of a.split(`
`)){if(r+=(i.match(/\\begin\{/g)??[]).length-(i.match(/\\end\{/g)??[]).length,!i.trim()&&r<=0){t.trim()&&e.push(t.trim()),t="",r=0;continue}t+=`${t?`
`:""}${i}`}return t.trim()&&e.push(t.trim()),e.slice(0,500).map(i=>i.replace(/^\$\$([\s\S]*)\$\$$|^\\\[([\s\S]*)\\\]$/,(n,o,s)=>(o??s).trim()))}function q(a){let e=[],t="",r=0,i=()=>{t&&e.push({type:"text",text:t.replace(/\\\$/g,"$")}),t=""};for(;r<a.length;){let n=a.slice(r,r+2),o=n==="$$"?["$$","$$",!0]:n==="\\["?["\\[","\\]",!0]:n==="\\("?["\\(","\\)",!1]:a[r]==="$"&&a[r-1]!=="\\"&&!/\s/.test(a[r+1]??" ")?["$","$",!1]:null;if(!o||a[r]==="\\"&&a[r-1]==="\\"){t+=a[r],r+=1;continue}let[s,c,h]=o,d=K(a,r+s.length,c);if(d<0){t+=a[r],r+=1;continue}let u=a.slice(r+s.length,d);i(),e.push({type:"math",tex:u.trim(),display:h}),r=d+c.length}return i(),e}function K(a,e,t){for(let r=e;r<a.length&&r-e<=2e4;r+=1){if(a[r]==="\\"&&t!=="\\]"&&t!=="\\)"){r+=1;continue}if(a.startsWith(t,r)&&!(t==="$"&&(/\s/.test(a[r-1]??"")||/\d/.test(a[r+1]??"")))&&!((t==="\\]"||t==="\\)")&&a[r-1]==="\\"))return r}return-1}function z(a){if(!a?.trim())return{};try{let e=JSON.parse(a);if(typeof e!="object"||e===null||Array.isArray(e))return{};let t=Object.create(null);for(let[r,i]of Object.entries(e).slice(0,200))/^\\[A-Za-z]{1,40}$/.test(r)&&typeof i=="string"&&(t[r]=i.slice(0,2e3));return t}catch{return{}}}var R=new Set(`math semantics annotation mrow mi mn mo ms mtext mspace mpadded mphantom mfrac msqrt mroot
  msub msup msubsup munder mover munderover mmultiscripts mprescripts none mtable mtr mtd
  menclose mstyle merror maction mlabeledtr`.split(/\s+/)),Y=new Set(`display displaystyle scriptlevel mathvariant mathsize mathcolor mathbackground dir class
  stretchy symmetric largeop movablelimits fence separator form lspace rspace minsize maxsize
  width height depth voffset linethickness notation encoding columnalign rowalign columnspan
  rowspan columnlines rowlines columnspacing rowspacing frame framespacing accent accentunder
  linebreak xmlns`.split(/\s+/)),D=new Set(`width height padding padding-top padding-right padding-bottom padding-left padding-inline-start
  padding-inline-end margin margin-left margin-right margin-top margin-bottom text-align
  font-weight font-style font-family color background-color border border-top border-right
  border-bottom border-left border-color border-style border-width position top right bottom
  left transform white-space math-depth math-style display vertical-align min-width`.split(/\s+/));function L(a){for(let e of Array.from(a.querySelectorAll("*"))){if(!e.isConnected&&!a.contains(e))continue;let t=e.localName;if(!R.has(t)&&t!=="span"){e.replaceWith(document.createTextNode(e.textContent??""));continue}for(let r of Array.from(e.attributes)){let i=r.name.toLowerCase();i!=="style"&&(!Y.has(i)||!$(r.value))&&e.removeAttribute(r.name)}e.localName==="annotation"&&e.getAttribute("encoding")!=="application/x-tex"&&e.remove(),H(e)}}function $(a){return a.length<=200&&!/[<>"'`\\]|url\s*\(|expression\s*\(|javascript:|@/i.test(a)}function H(a){let e=a.style;if(e)for(let t of Array.from(e)){let r=e.getPropertyValue(t);(!D.has(t)||!$(r))&&e.removeProperty(t)}}function j(a){return new XMLSerializer().serializeToString(a)}var p=null;function X(){if(p)return p;let a=f().vendorUrl||y(),e={ready:!1,engine:null,promise:Promise.resolve(null)};return e.promise=import(new URL("temml.js",a||location.href).href).then(t=>(e.engine={render:t.render,ParseError:t.ParseError},e.ready=!0,e.engine),t=>{throw p=null,t}),p=e,e}function F(a){if(!a||typeof a.render!="function")throw new TypeError("[vitrine] useMathEngine(): expected Temml (an object with render()).");let e={render:a.render.bind(a),ParseError:a.ParseError};p={ready:!0,engine:e,promise:Promise.resolve(e)}}var N=Object.freeze({mathEquation:"Equation {index}",mathEquations:"{count} equations",mathCopyTex:"Copy TeX",mathCopyMathml:"Copy MathML",mathError:"This TeX could not be read: {message}",mathLoadFailed:"The math renderer could not be loaded: the TeX is shown as it is written."}),W={mathEquation:"\xC9quation {index}",mathEquations:"{count} \xE9quations",mathCopyTex:"Copier le TeX",mathCopyMathml:"Copier le MathML",mathError:"Ce TeX n\u2019a pas pu \xEAtre lu : {message}",mathLoadFailed:"Le moteur de formules n\u2019a pas pu \xEAtre charg\xE9 : le TeX est affich\xE9 tel qu\u2019il est \xE9crit."};T({en:N,fr:W});var V=class extends C{static type="math";static componentAttributes=Object.freeze(["inline","delimiters","numbered","macros","copy-mathml"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,search:!0,fullscreen:!0,"copy-mathml":!0}};static styles=[A];static useEngine(e){F(e)}constructor(){super(),this.panelId=x("panel"),this.editor=null,this.previewTimer=void 0,this.loadFailed=!1}disconnectedCallback(){clearTimeout(this.previewTimer),this.editor?.destroy(),super.disconnectedCallback()}get inline(){return w(this.getAttribute("inline"))===!0}engine(){let e=X();return e.ready?e.engine:(this.loadFailed||e.promise.then(()=>this.requestRender(),()=>{this.loadFailed=!0,this.requestRender()}),null)}renderContent(e){let t=this.t,r=this.text??"",i=this.engine(),n=this.inline;e.classList.toggle("inline-math",n);let o=l(n?"span":"div",{class:`body math-body${n?" inline":""}`,part:"body"});this.loadFailed&&!i&&o.append(M(t("mathLoadFailed")));let s=[];if(this.feature("delimiters"))for(let m of q(r))m.type==="text"?o.append(this.textView(m.text)):(s.push(m.tex),o.append(this.mathView(m.tex,m.display,i,null)));else if(n)s.push(r.trim()),o.append(this.mathView(r.trim(),!1,i,null));else{let m=_(r),O=this.feature("numbered");m.forEach((b,P)=>{s.push(b),o.append(this.mathView(b,!0,i,O?P+1:null))})}if(n){e.append(o);return}let c=l("div",{class:"panel",attrs:{id:this.panelId}}),h=[];if(this.editing){let m=this.createEditor();c.classList.add("math-edit"),c.append(l("div",{class:"body editor-body",part:"body source"},m.element),o),h=this.historyButtons(m)}else c.append(o);let d=this.feature("delimiters")?r:s.join(`

`),u=[this.feature("delimiters")?this.searchButton(new E(o)):null,...h,this.editToggleButton(),this.fullscreenButton(),this.feature("copy-mathml")&&i?this.copyTextButton(()=>Array.from(o.querySelectorAll("math"),j).join(`
`),t("mathCopyMathml"),"copy-mathml"):null,this.feature("copy")?this.copyButton(()=>d,t("mathCopyTex")):null],B=s.length>1&&!this.feature("delimiters")?t("mathEquations",{count:g(s.length,this.locale)}):"TeX";e.append(...this.chrome({badge:B,actions:u}),c),this.editor?.align()}textView(e){let t=document.createDocumentFragment();return e.split(/\n[^\S\n]*\n/).forEach((r,i)=>{i&&t.append(l("span",{class:"math-break",attrs:{"aria-hidden":"true"}})),t.append(r)}),t}mathView(e,t,r,i){let n=l(t?"div":"span",{class:t?"math-display":"math-inline",part:t?"equation":void 0});if(!r||!e)return n.append(l("code",{class:"math-tex",text:e})),n;let o=l("span",{class:"math-target"});try{if(e.length>2e4)throw new Error(`more than ${2e4} characters`);r.render(e,o,{displayMode:t,throwOnError:!0,trust:!1,annotate:!0,maxExpand:1e3,maxSize:50,macros:{...z(this.getAttribute("macros"))},xml:!1,wrap:t?"none":"tex"}),L(o);for(let s of Array.from(o.querySelectorAll("math")))s.setAttribute("part","math");n.append(...Array.from(o.childNodes))}catch(s){let c=s instanceof Error?s.message.replace(/^Temml parse error: /,"").slice(0,500):String(s);return n.classList.add("error"),n.setAttribute("part","tex-error"),n.append(l("code",{class:"math-tex",text:e}),l("span",{class:"math-error",attrs:{role:"note"},text:this.t("mathError",{message:c})})),n}return i!==null&&(n.classList.add("numbered"),n.append(l("span",{class:"math-number",part:"number",text:`(${g(i,this.locale)})`}))),n}createEditor(){return this.editor?.destroy(),this.editor=new S({text:this.text??"",language:"latex",lineNumbers:!1,wrap:!0,highlightLimit:f().highlightLimit,label:this.heading||this.t("editor"),placeholder:this.getAttribute("placeholder")??void 0,onInput:e=>this.edited(e),onChange:e=>k(this,v.CHANGE,{value:e}),history:this.editHistory??void 0}),this.editor}contentEdited(){clearTimeout(this.previewTimer),this.previewTimer=setTimeout(()=>this.render(),150)}};export{V as a};
