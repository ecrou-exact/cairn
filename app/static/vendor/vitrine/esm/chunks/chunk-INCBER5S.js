/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
var o=`/*\r
 * Shared by the elements that show a preview of JSON: the body, the editor above it, and the\r
 * small pieces they have in common.\r
 */\r
.data-body {\r
  display: grid;\r
  gap: var(--_space-4);\r
  padding: var(--_space-4) var(--_space-5);\r
  background: var(--_surface);\r
  container-type: inline-size;\r
  overscroll-behavior: auto;\r
}\r
\r
:host([max-height]) .data-body,\r
.vt[data-fullscreen] .data-body {\r
  overscroll-behavior: contain;\r
}\r
\r
.data-edit > .editor-body {\r
  max-height: min(40vh, 320px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
.data-none {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.5 var(--_font-ui);\r
}\r
\r
.data-chips {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-1);\r
}\r
\r
.data-chip {\r
  min-height: 28px;\r
  padding: 2px 10px;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-full);\r
  background: transparent;\r
  color: var(--_fg-muted);\r
  font: 500 var(--_font-size-small) / 1.4 var(--_font-ui);\r
  cursor: pointer;\r
}\r
\r
.data-chip:hover {\r
  background: var(--_accent-soft);\r
  color: var(--_fg);\r
}\r
\r
.data-chip[aria-pressed='true'] {\r
  border-color: var(--_accent);\r
  background: var(--_accent-soft);\r
  color: var(--_fg);\r
}\r
\r
.data-chip:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 1px;\r
}\r
\r
.data-input {\r
  width: 100%;\r
  min-height: 36px;\r
  padding: 0 var(--_space-3);\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-sunken);\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.data-input:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 1px;\r
}\r
\r
@media (pointer: coarse) {\r
  .data-chip {\r
    min-height: 44px;\r
  }\r
}\r
`;export{o as a};
