/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{b as l,d}from"./chunk-JRZ3XLAR.js";import{c as s,e as o,j as n,o as a}from"./chunk-7PAHM2BV.js";import{q as c}from"./chunk-TUK22DTT.js";var u=`/* <vt-typing>: three dots, bouncing (dots, bubble) or rising in a wave. */\r
.dots,\r
.bubble {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: calc(var(--_ind-size) * 0.3);\r
}\r
\r
.bubble {\r
  padding: calc(var(--_ind-size) * 0.65) calc(var(--_ind-size) * 0.9);\r
  border-radius: calc(var(--_ind-size) * 1.2);\r
  border-end-start-radius: calc(var(--_ind-size) * 0.3);\r
  background: var(--vt-typing-bubble, var(--_surface-sunken, #eee));\r
}\r
\r
.dot {\r
  width: calc(var(--_ind-size) * 0.45);\r
  height: calc(var(--_ind-size) * 0.45);\r
  border-radius: 50%;\r
  background: var(--_ind-color);\r
  animation: vt-typing-bounce calc(var(--_ind-duration) * 1.3) ease-in-out infinite;\r
}\r
\r
.dot:nth-child(2) {\r
  animation-delay: calc(var(--_ind-duration) * 0.18);\r
}\r
\r
.dot:nth-child(3) {\r
  animation-delay: calc(var(--_ind-duration) * 0.36);\r
}\r
\r
@keyframes vt-typing-bounce {\r
  0%,\r
  60%,\r
  100% {\r
    opacity: 0.45;\r
    transform: translateY(0);\r
  }\r
\r
  30% {\r
    opacity: 1;\r
    transform: translateY(-40%);\r
  }\r
}\r
\r
.indicator[data-type='wave'] .dot {\r
  animation-name: vt-typing-wave;\r
}\r
\r
@keyframes vt-typing-wave {\r
  0%,\r
  100% {\r
    opacity: 0.4;\r
    transform: scale(0.7);\r
  }\r
\r
  50% {\r
    opacity: 1;\r
    transform: scale(1.15);\r
  }\r
}\r
\r
.indicator[data-motion='reduce'] .dot {\r
  animation-name: vt-fade;\r
}\r
\r
.indicator-text {\r
  font-style: italic;\r
}\r
`;var h=["dots","wave","bubble"],b=class extends d{static type="typing";static componentAttributes=["type","name","show-text","text"];static styles=[u];static defaultSize="sm";sentence(){let t=n(this.getAttribute("text"));if(t)return t;let e=(this.getAttribute("name")??"").split(",").map(i=>n(i,60)).filter(Boolean);return e.length?e.length===1?this.t("loadingTyping",{name:e[0]}):e.length===2?this.t("loadingTypingTwo",{names:new Intl.ListFormat(this.locale,{type:"conjunction"}).format(e)}):this.t("loadingTypingMany",{count:c(e.length,this.locale)}):this.t("loadingTypingSomeone")}draw(t){if(this.hasAttribute("tone")||(t.dataset.tone="neutral"),!this.shown){t.replaceChildren(),t.removeAttribute("role");return}let e=o(this.getAttribute("type"),h,"bubble"),i=this.sentence();t.dataset.type=e,t.setAttribute("role","status"),t.setAttribute("aria-label",n(this.getAttribute("label"))||i);let r=Array.from({length:3},()=>a("span",{class:"dot",part:"dot"})),p=e==="bubble"?a("span",{class:"bubble",part:"bubble",attrs:{"aria-hidden":"true"}},...r):a("span",{class:"dots",attrs:{"aria-hidden":"true"}},...r);t.replaceChildren(...l([p,s(this.getAttribute("show-text"))?a("span",{class:"indicator-text",part:"text",text:i,attrs:{"aria-hidden":"true"}}):null]))}};export{b as a};
