/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as y,b as k,c as A}from"./chunk-5CTFTED4.js";import{c as h,d as _}from"./chunk-JRZ3XLAR.js";import{c,e as d,j as s,o as e}from"./chunk-7PAHM2BV.js";import{k as f,l as g,q as x}from"./chunk-TUK22DTT.js";var w=`/*\r
 * <vt-loading-overlay>: the content in a positioned box, the overlay above it. The scrim\r
 * dims (light, dark) or blurs the content; the panel holds the spinner and the message.\r
 */\r
:host {\r
  display: block;\r
}\r
\r
.indicator {\r
  position: relative;\r
  display: block;\r
  --_scrim: var(--vt-overlay-scrim, color-mix(in srgb, var(--_surface, #fff) 72%, transparent));\r
}\r
\r
.indicator[data-shown='true']:not(.fullscreen) {\r
  /* Room for the panel, even over a short content. */\r
  min-height: var(--vt-overlay-min-height, 140px);\r
}\r
\r
.indicator[data-scrim='dark'] {\r
  --_scrim: var(--vt-overlay-scrim, rgb(10 12 16 / 55%));\r
}\r
\r
.indicator[data-scrim='none'] {\r
  --_scrim: transparent;\r
}\r
\r
.overlay {\r
  position: absolute;\r
  inset: 0;\r
  overflow: hidden;\r
  z-index: 10;\r
  display: grid;\r
  place-items: center;\r
  padding: var(--_space-4);\r
  border-radius: inherit;\r
  background: var(--_scrim);\r
  animation: vt-overlay-in 0.18s ease-out;\r
}\r
\r
.indicator[data-scrim='blur'] .overlay {\r
  backdrop-filter: blur(4px) saturate(0.8);\r
}\r
\r
.indicator.fullscreen .overlay {\r
  position: fixed;\r
  z-index: 2147483000;\r
}\r
\r
.panel {\r
  display: grid;\r
  justify-items: center;\r
  gap: var(--_space-3);\r
  max-width: min(360px, 100%);\r
  padding: var(--_space-4) var(--_space-5);\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius, 10px);\r
  /* A solid card: the text keeps its contrast whatever the scrim lets through. */\r
  background: var(--_surface, #fff);\r
  color: var(--_fg);\r
  text-align: center;\r
  outline: none;\r
}\r
\r
.indicator[data-scrim='dark'] .panel,\r
.indicator.fullscreen .panel {\r
  box-shadow: var(--_shadow, 0 8px 24px rgb(0 0 0 / 15%));\r
}\r
\r
.panel .indicator-text {\r
  margin: 0;\r
  opacity: 1;\r
  font-weight: 550;\r
}\r
\r
.overlay-progress {\r
  width: min(240px, 60vw);\r
  height: 6px;\r
  overflow: hidden;\r
  border-radius: 999px;\r
  background: var(--_ind-track);\r
}\r
\r
.overlay-bar {\r
  display: block;\r
  height: 100%;\r
  border-radius: inherit;\r
  background: var(--_ind-color);\r
  transform: scaleX(var(--_ratio));\r
  transform-origin: left center;\r
  transition: transform 0.25s ease;\r
}\r
\r
.overlay-cancel {\r
  padding: 6px 14px;\r
  border: 1px solid var(--_border-strong, var(--_border));\r
  border-radius: var(--_radius-sm, 6px);\r
  background: var(--_surface, #fff);\r
  color: var(--_fg);\r
  font: inherit;\r
  cursor: pointer;\r
}\r
\r
.overlay-cancel:hover {\r
  background: var(--_surface-sunken);\r
}\r
\r
.overlay-cancel:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
@keyframes vt-overlay-in {\r
  from {\r
    opacity: 0;\r
  }\r
}\r
\r
.indicator[data-motion='reduce'] .overlay {\r
  animation: none;\r
}\r
\r
@media (forced-colors: active) {\r
  .overlay {\r
    background: Canvas;\r
    opacity: 0.92;\r
  }\r
}\r
`;var P=["light","dark","blur","none"],C=class extends _{static type="loading-overlay";static componentAttributes=["text","spinner","value","max","scrim","cancelable","cancel-text","fullscreen"];static styles=[y,w];static display="block";static defaultSize="lg";constructor(){super(),this.contentBox=e("div",{class:"content",part:"content"},e("slot",{})),this.madeInert=new Map,this.focusPanel=!1,this.observer=null}connectedCallback(){this.observer=new MutationObserver(()=>{this.shown&&!this.hasAttribute("fullscreen")&&this.setInert(!0)}),this.observer.observe(this,{childList:!0}),super.connectedCallback()}disconnectedCallback(){this.observer?.disconnect(),this.observer=null,super.disconnectedCallback()}started(){this.contains(document.activeElement)&&!this.hasAttribute("fullscreen")&&(this.focusPanel=!0)}stopped(){this.setInert(!1)}setInert(r){if(r){for(let t of this.children)this.madeInert.has(t)||(this.madeInert.set(t,t.hasAttribute("inert")),t.setAttribute("inert",""));return}for(let[t,a]of this.madeInert)a||t.removeAttribute("inert");this.madeInert.clear()}draw(r){let t=this.shown,a=c(this.getAttribute("fullscreen"))??!1;if(r.classList.toggle("fullscreen",a),r.dataset.scrim=d(this.getAttribute("scrim"),P,"light"),this.toggleAttribute("aria-busy",t),this.setInert(t&&!a),!t){r.replaceChildren(this.contentBox);return}let u=this.t,i=s(this.getAttribute("text")),p=this.getAttribute("spinner")==="none"?null:d(this.getAttribute("spinner"),k,"ring"),n=h(this.getAttribute("value")),o=Math.max(1,h(this.getAttribute("max"))??100),l=null;if(n!==null){let m=Math.min(1,Math.max(0,n/o)),S=u("loadingPercent",{percent:x(Math.round(m*100),this.locale)});l=e("div",{class:"overlay-progress",part:"progress",attrs:{role:"progressbar","aria-valuemin":"0","aria-valuemax":String(o),"aria-valuenow":String(Math.min(o,Math.max(0,n))),"aria-valuetext":S,"aria-label":i||this.labelText()}},e("span",{class:"overlay-bar"})),l.style.setProperty("--_ratio",String(m))}let v=c(this.getAttribute("cancelable"))?e("button",{class:"overlay-cancel",part:"cancel",text:s(this.getAttribute("cancel-text"),40)||u("loadingCancel"),attrs:{type:"button"},on:{click:()=>g(this,f.CANCEL,{})}}):null,b=e("div",{class:"panel",part:"panel",attrs:{role:"status","aria-label":s(this.getAttribute("label"))||i||this.labelText(),tabindex:"-1"}},p?A(p):null,i?e("p",{class:"indicator-text",part:"text",text:i}):null,l,v),I=e("div",{class:"overlay",part:"overlay"},b);r.replaceChildren(this.contentBox,I),this.focusPanel&&(this.focusPanel=!1,(v??b).focus())}};export{C as a};
