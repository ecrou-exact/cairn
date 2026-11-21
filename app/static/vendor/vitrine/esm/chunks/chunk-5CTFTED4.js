/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{o as n}from"./chunk-7PAHM2BV.js";var d=`/*\r
 * Spinner shapes (components/loading/shapes.js). Everything scales with --_ind-size and\r
 * runs at --_ind-duration; the color is --_ind-color, the track --_ind-track.\r
 */\r
.spinner {\r
  position: relative;\r
  display: inline-block;\r
  flex: none;\r
  width: var(--_ind-size);\r
  height: var(--_ind-size);\r
}\r
\r
/* A full track with one colored quarter. */\r
.spinner.ring {\r
  border: max(2px, calc(var(--_ind-size) / 9)) solid var(--_ind-track);\r
  border-top-color: var(--_ind-color);\r
  border-radius: 50%;\r
  animation: vt-rotate calc(var(--_ind-duration) * 0.8) linear infinite;\r
}\r
\r
/* A fading tail, drawn with a conic gradient masked to a ring. */\r
.spinner.arc {\r
  border-radius: 50%;\r
  background: conic-gradient(from 0deg, transparent 0 10%, var(--_ind-color));\r
  mask: radial-gradient(\r
    farthest-side,\r
    transparent calc(100% - max(2px, var(--_ind-size) / 8) - 0.5px),\r
    #000 calc(100% - max(2px, var(--_ind-size) / 8))\r
  );\r
  animation: vt-rotate calc(var(--_ind-duration) * 0.9) linear infinite;\r
}\r
\r
/* Two arcs turning in opposite directions. */\r
.spinner.dual-ring .spinner-part {\r
  position: absolute;\r
  inset: 0;\r
  border: max(2px, calc(var(--_ind-size) / 10)) solid transparent;\r
  border-radius: 50%;\r
}\r
\r
.spinner.dual-ring .p1 {\r
  border-top-color: var(--_ind-color);\r
  border-bottom-color: var(--_ind-color);\r
  animation: vt-rotate calc(var(--_ind-duration) * 1.1) linear infinite;\r
}\r
\r
.spinner.dual-ring .p2 {\r
  inset: 22%;\r
  border-left-color: color-mix(in srgb, var(--_ind-color) 55%, transparent);\r
  border-right-color: color-mix(in srgb, var(--_ind-color) 55%, transparent);\r
  animation: vt-rotate calc(var(--_ind-duration) * 0.8) linear infinite reverse;\r
}\r
\r
/* Three dots fading in turn. */\r
.spinner.dots {\r
  display: inline-flex;\r
  align-items: center;\r
  justify-content: space-between;\r
  width: calc(var(--_ind-size) * 1.6);\r
}\r
\r
.spinner.dots .spinner-part {\r
  width: 26%;\r
  aspect-ratio: 1;\r
  border-radius: 50%;\r
  background: var(--_ind-color);\r
  animation: vt-pulse var(--_ind-duration) ease-in-out infinite;\r
}\r
\r
.spinner.dots .p2 {\r
  animation-delay: calc(var(--_ind-duration) * 0.16);\r
}\r
\r
.spinner.dots .p3 {\r
  animation-delay: calc(var(--_ind-duration) * 0.32);\r
}\r
\r
/* Four bars rising in turn, as an equalizer. */\r
.spinner.bars {\r
  display: inline-flex;\r
  align-items: center;\r
  justify-content: space-between;\r
}\r
\r
.spinner.bars .spinner-part {\r
  width: 16%;\r
  height: 100%;\r
  border-radius: 2px;\r
  background: var(--_ind-color);\r
  transform-origin: center;\r
  animation: vt-bar var(--_ind-duration) ease-in-out infinite;\r
}\r
\r
.spinner.bars .p2 {\r
  animation-delay: calc(var(--_ind-duration) * 0.12);\r
}\r
\r
.spinner.bars .p3 {\r
  animation-delay: calc(var(--_ind-duration) * 0.24);\r
}\r
\r
.spinner.bars .p4 {\r
  animation-delay: calc(var(--_ind-duration) * 0.36);\r
}\r
\r
@keyframes vt-bar {\r
  0%,\r
  100% {\r
    transform: scaleY(0.35);\r
    opacity: 0.5;\r
  }\r
\r
  50% {\r
    transform: scaleY(1);\r
    opacity: 1;\r
  }\r
}\r
\r
/* Two waves growing from the center. */\r
.spinner.pulse .spinner-part {\r
  position: absolute;\r
  inset: 0;\r
  border-radius: 50%;\r
  background: var(--_ind-color);\r
  opacity: 0;\r
  animation: vt-wave calc(var(--_ind-duration) * 1.4) cubic-bezier(0.2, 0.6, 0.4, 1) infinite;\r
}\r
\r
.spinner.pulse .p2 {\r
  animation-delay: calc(var(--_ind-duration) * 0.7);\r
}\r
\r
@keyframes vt-wave {\r
  from {\r
    opacity: 0.85;\r
    transform: scale(0.1);\r
  }\r
\r
  to {\r
    opacity: 0;\r
    transform: scale(1);\r
  }\r
}\r
\r
/* A dot circling a faint track. */\r
.spinner.orbit {\r
  border: max(1px, calc(var(--_ind-size) / 16)) solid var(--_ind-track);\r
  border-radius: 50%;\r
  animation: vt-rotate calc(var(--_ind-duration) * 1.2) linear infinite;\r
}\r
\r
.spinner.orbit .spinner-part {\r
  position: absolute;\r
  top: -12%;\r
  left: 50%;\r
  width: 26%;\r
  aspect-ratio: 1;\r
  border-radius: 50%;\r
  background: var(--_ind-color);\r
  transform: translateX(-50%);\r
}\r
\r
/* Reduced motion: no turning or sliding, a slow fade instead. */\r
.indicator[data-motion='reduce'] .spinner,\r
.indicator[data-motion='reduce'] .spinner-part {\r
  animation-name: vt-fade !important;\r
}\r
\r
/* <vt-spinner>: text under the shape. */\r
.indicator.below {\r
  flex-direction: column;\r
  gap: var(--_space-2);\r
}\r
`;var l=["ring","arc","dual-ring","dots","bars","pulse","orbit"],e={ring:0,arc:0,"dual-ring":2,dots:3,bars:4,pulse:2,orbit:1};function p(r){let i=e[r];return n("span",{class:`spinner ${r}`,part:"spinner",attrs:{"aria-hidden":"true"}},...Array.from({length:i},(o,a)=>n("span",{class:`spinner-part p${a+1}`})))}export{d as a,l as b,p as c};
