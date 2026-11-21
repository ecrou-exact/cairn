/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
var r=`/*\r
 * JSON tree. Colors reuse the syntax roles so code and JSON look the same.\r
 * Spec: docs/DESIGN_SYSTEM.md \xA72.4 and \xA76 (tree-toggle).\r
 */\r
.tree-body {\r
  padding: var(--_space-2) 0;\r
}\r
\r
.tree,\r
.group {\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.tree {\r
  min-width: 100%;\r
  color: var(--_code-fg);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size);\r
  line-height: var(--_line-height);\r
}\r
\r
.item {\r
  outline: none;\r
}\r
\r
.row {\r
  display: flex;\r
  align-items: baseline;\r
  gap: 0;\r
  min-height: calc(var(--_font-size) * var(--_line-height));\r
  padding: 1px var(--_space-4) 1px calc(var(--_space-3) + var(--_level, 0) * 1.25em);\r
  cursor: default;\r
}\r
\r
.row > * {\r
  flex: none;\r
  white-space: pre;\r
}\r
\r
.row > .key {\r
  flex: 0 0 auto;\r
  max-width: min(50%, 48ch);\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
.row:hover {\r
  background: color-mix(in srgb, var(--_accent-soft) 60%, transparent);\r
}\r
\r
.item[aria-selected='true'] > .row {\r
  background: var(--_accent-soft);\r
}\r
\r
.item:focus-visible > .row {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: -2px;\r
  border-radius: 2px;\r
}\r
\r
.toggle {\r
  display: inline-grid;\r
  flex: none;\r
  place-items: center;\r
  align-self: center;\r
  width: 16px;\r
  height: 16px;\r
  margin-right: 4px;\r
  color: var(--_fg-muted);\r
  cursor: pointer;\r
}\r
\r
.toggle .icon {\r
  width: 14px;\r
  height: 14px;\r
  transition: transform var(--_duration) var(--_easing);\r
}\r
\r
.item[aria-expanded='true'] > .row > .toggle .icon {\r
  transform: rotate(90deg);\r
}\r
\r
.toggle.leaf {\r
  cursor: default;\r
}\r
\r
.vt:not([data-syntax-theme]) .key {\r
  color: var(--_syntax-attr);\r
}\r
\r
.vt:not([data-syntax-theme]) .index {\r
  color: var(--_syntax-meta);\r
}\r
\r
.vt:not([data-syntax-theme]) .punct {\r
  color: var(--_syntax-meta);\r
}\r
\r
.row > .value.string,\r
.row > .value-wrap {\r
  flex: 0 1 auto;\r
  min-width: 0;\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
.vt:not([data-syntax-theme]) .value.string {\r
  color: var(--_syntax-string);\r
}\r
\r
.vt:not([data-syntax-theme]) .value.number {\r
  color: var(--_syntax-number);\r
}\r
\r
.vt:not([data-syntax-theme]) .value.literal {\r
  color: var(--_syntax-keyword);\r
}\r
\r
/* Dates and times of formats that have them (TOML). */\r
.vt:not([data-syntax-theme]) .value.date {\r
  color: var(--_syntax-type);\r
}\r
\r
.count {\r
  margin-left: var(--_space-2);\r
  color: var(--_fg-muted);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.type {\r
  margin-left: var(--_space-2);\r
  padding: 0 5px;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-sunken);\r
  color: var(--_fg-muted);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-small);\r
  line-height: 1.5;\r
}\r
\r
.inline-more,\r
.more-label {\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.inline-more {\r
  margin-left: var(--_space-2);\r
  padding: 0 6px;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface);\r
  color: var(--_accent-fg);\r
  cursor: pointer;\r
}\r
\r
.more-item > .row {\r
  cursor: pointer;\r
}\r
\r
.more-label {\r
  color: var(--_accent-fg);\r
  text-decoration: underline;\r
  text-underline-offset: 3px;\r
}\r
\r
/* ---------- Path bar ---------- */\r
\r
.pathbar {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  min-height: 36px;\r
  padding: 0 var(--_space-2) 0 var(--_space-3);\r
  border-top: 1px solid var(--_border);\r
  background: var(--_surface);\r
}\r
\r
.path-text {\r
  flex: 1 1 auto;\r
  min-width: 0;\r
  overflow: hidden;\r
  color: var(--_fg-muted);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size-small);\r
  white-space: nowrap;\r
  text-overflow: ellipsis;\r
}\r
\r
/* With a syntax theme, badges and counts take the colors of the code area. */\r
.vt[data-syntax-theme] .count {\r
  color: color-mix(in srgb, var(--_code-fg) 80%, var(--_code-bg-solid));\r
}\r
\r
.vt[data-syntax-theme] .type {\r
  border-color: color-mix(in srgb, var(--_code-fg) 30%, transparent);\r
  background: transparent;\r
  color: color-mix(in srgb, var(--_code-fg) 80%, var(--_code-bg-solid));\r
}\r
`;export{r as a};
