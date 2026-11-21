/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as c}from"./chunk-46FQDERA.js";import{b as f,c as h}from"./chunk-JRZ3XLAR.js";import{c as s,d as m,i as u,j as b,o as e}from"./chunk-7PAHM2BV.js";var g=`/*\r
 * <vt-progress>: a track and a bar scaled to --_ratio. Indeterminate: a bar sliding across.\r
 * Segments are cut with a repeating mask, so the bar keeps one element.\r
 */\r
:host {\r
  display: block;\r
}\r
\r
.head {\r
  display: flex;\r
  align-items: baseline;\r
  justify-content: space-between;\r
  gap: var(--_space-3);\r
  margin-bottom: var(--_space-1);\r
}\r
\r
.head .indicator-text {\r
  min-width: 0;\r
  overflow: hidden;\r
  opacity: 1;\r
  text-overflow: ellipsis;\r
  white-space: nowrap;\r
}\r
\r
.value {\r
  flex: none;\r
  opacity: var(--_dim);\r
  font-size: var(--_font-size-small);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.track {\r
  position: relative;\r
  height: var(--_thickness, 4px);\r
  overflow: hidden;\r
  border-radius: var(--_radius-full, 999px);\r
  background: var(--_ind-track);\r
}\r
\r
.track.square,\r
.track.square .bar,\r
.track.square .buffer {\r
  border-radius: 0;\r
}\r
\r
.bar,\r
.buffer {\r
  position: absolute;\r
  inset-block: 0;\r
  inset-inline-start: 0;\r
  width: 100%;\r
  border-radius: inherit;\r
  transform-origin: left center;\r
  transition: transform 0.25s ease;\r
}\r
\r
:host(:dir(rtl)) .bar,\r
:host(:dir(rtl)) .buffer {\r
  transform-origin: right center;\r
}\r
\r
.bar {\r
  background-color: var(--_ind-color);\r
  transform: scaleX(var(--_ratio));\r
}\r
\r
.buffer {\r
  background: color-mix(in srgb, var(--_ind-color) 35%, transparent);\r
  transform: scaleX(var(--_buffer));\r
}\r
\r
.track.segmented {\r
  mask: repeating-linear-gradient(\r
    to right,\r
    #000 0 calc(100% / var(--_segments) - 3px),\r
    transparent calc(100% / var(--_segments) - 3px) calc(100% / var(--_segments))\r
  );\r
}\r
\r
/* Stripes are drawn on the bar; scaling would stretch them, so the bar is clipped instead. */\r
.bar.striped {\r
  width: calc(var(--_ratio) * 100%);\r
  transform: none;\r
  background-image: linear-gradient(\r
    45deg,\r
    rgb(255 255 255 / 22%) 25%,\r
    transparent 25% 50%,\r
    rgb(255 255 255 / 22%) 50% 75%,\r
    transparent 75%\r
  );\r
  background-size: calc(var(--_thickness) * 2.5) calc(var(--_thickness) * 2.5);\r
  transition: width 0.25s ease;\r
}\r
\r
.bar.animated {\r
  animation: vt-stripes calc(var(--_ind-duration) * 0.8) linear infinite;\r
}\r
\r
@keyframes vt-stripes {\r
  to {\r
    background-position: calc(var(--_thickness) * 2.5) 0;\r
  }\r
}\r
\r
.track.indeterminate .bar {\r
  width: 40%;\r
  transform: none;\r
  animation: vt-slide calc(var(--_ind-duration) * 1.6) cubic-bezier(0.65, 0, 0.35, 1) infinite;\r
}\r
\r
@keyframes vt-slide {\r
  from {\r
    transform: translateX(-100%);\r
  }\r
\r
  to {\r
    transform: translateX(250%);\r
  }\r
}\r
\r
.indicator[data-motion='reduce'] .track.indeterminate .bar {\r
  width: 100%;\r
  animation-name: vt-fade;\r
}\r
\r
.indicator[data-motion='reduce'] .bar,\r
.indicator[data-motion='reduce'] .buffer {\r
  transition: none;\r
}\r
\r
@media (forced-colors: active) {\r
  .track {\r
    border: 1px solid CanvasText;\r
  }\r
\r
  .bar {\r
    background-color: Highlight;\r
  }\r
}\r
`;var v=Object.freeze({xs:"2px",sm:"4px",md:"8px",lg:"12px",xl:"16px"}),k=class extends c{static type="progress";static componentAttributes=[...c.componentAttributes,"buffer","segments","striped","animated","thickness","square"];static styles=[g];static display="block";draw(r){if(!this.shown){r.replaceChildren();return}this.applyStatusTone();let x=this.getAttribute("thickness")?.trim().toLowerCase()??"";r.style.setProperty("--_thickness",v[x]??u(this.getAttribute("thickness"))??v.sm);let a=this.ratio,l=b(this.getAttribute("text")),i=this.valueLabel(),d=h(this.getAttribute("buffer")),n=d===null?null:Math.min(1,Math.max(0,(d-this.min)/(this.max-this.min))),o=m(this.getAttribute("segments"),{min:2,max:50,fallback:0}),p=s(this.getAttribute("striped"))??!1,_=p&&(s(this.getAttribute("animated"))??!1),t=e("div",{class:`track${a===null?" indeterminate":""}${o?" segmented":""}${s(this.getAttribute("square"))?" square":""}`,part:"track"});this.setProgressAria(t),n!==null&&a!==null&&t.append(e("div",{class:"buffer",part:"buffer"}));let w=e("div",{class:`bar${p?" striped":""}${_?" animated":""}`,part:"bar"});t.append(w),t.style.setProperty("--_ratio",String(a??0)),n!==null&&t.style.setProperty("--_buffer",String(Math.max(n,a??0))),o&&t.style.setProperty("--_segments",String(o)),r.classList.toggle("complete",a!==null&&a>=1),r.replaceChildren(...f([l||i?e("div",{class:"head",part:"head",attrs:{"aria-hidden":"true"}},e("span",{class:"indicator-text",part:"text",text:l}),i?e("span",{class:"value",part:"value",text:i}):null):null,t]))}};export{k as a};
