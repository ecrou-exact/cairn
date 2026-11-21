/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
var i=`/*\r
 * Code view: used by <vt-code>, the Markdown source tab and the JSON raw view.\r
 */\r
.code-view {\r
  position: relative;\r
}\r
\r
.code {\r
  display: grid;\r
  width: max-content;\r
  min-width: 100%;\r
  margin: 0;\r
  padding: var(--_space-3) 0;\r
  color: var(--_code-fg);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size);\r
  font-variant-ligatures: var(--vt-font-ligatures, none);\r
  line-height: var(--_line-height);\r
  tab-size: var(--_tab-size);\r
}\r
\r
.wrap .code {\r
  width: auto;\r
}\r
\r
.line {\r
  display: flex;\r
  min-width: 0;\r
}\r
\r
/* Long code: off-screen blocks of lines skip layout and paint. */\r
.chunk.revealed {\r
  content-visibility: visible;\r
}\r
\r
.chunk {\r
  display: block;\r
  content-visibility: auto;\r
  contain-intrinsic-block-size: auto\r
    calc(var(--_chunk-lines) * var(--_font-size) * var(--_line-height));\r
}\r
\r
/* A block whose lines are not built yet keeps the height they will take. */\r
.chunk[data-pending] {\r
  block-size: calc(var(--_chunk-lines) * var(--_font-size) * var(--_line-height));\r
}\r
\r
.gutter {\r
  position: sticky;\r
  left: 0;\r
  z-index: 1;\r
  flex: none;\r
  min-width: calc(var(--_digits, 2) * 1ch + 2 * var(--_space-3));\r
  padding: 0 var(--_space-3);\r
  border-right: 1px solid color-mix(in srgb, var(--_code-gutter) 35%, transparent);\r
  background: var(--_code-bg-solid);\r
  color: var(--_code-gutter);\r
  font-size: var(--_font-size-small);\r
  line-height: calc(var(--_font-size) * var(--_line-height));\r
  font-variant-numeric: tabular-nums;\r
  text-align: right;\r
  user-select: none;\r
  -webkit-user-select: none;\r
}\r
\r
.gutter::before {\r
  content: attr(data-n);\r
}\r
\r
.sign {\r
  flex: none;\r
  width: 2ch;\r
  padding-left: var(--_space-2);\r
  color: var(--_fg-muted);\r
  user-select: none;\r
  -webkit-user-select: none;\r
}\r
\r
.content {\r
  flex: 1 1 auto;\r
  min-width: 0;\r
  padding: 0 var(--_space-4);\r
  white-space: pre;\r
}\r
\r
.sign + .content {\r
  padding-left: var(--_space-1);\r
}\r
\r
.wrap .content {\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
.line.highlighted {\r
  background: var(--_line-highlight);\r
}\r
\r
.line.highlighted .gutter {\r
  box-shadow: inset 2px 0 0 var(--_accent);\r
  color: var(--_code-fg);\r
}\r
\r
.line.added {\r
  background: var(--_diff-added);\r
}\r
\r
.line.removed {\r
  background: var(--_diff-removed);\r
}\r
\r
.line.added .sign::before {\r
  content: '+';\r
  color: var(--_success);\r
}\r
\r
.line.removed .sign::before {\r
  content: '\\2212';\r
  color: var(--_danger);\r
}\r
\r
.line.hunk .content {\r
  color: var(--_info);\r
}\r
\r
/* Collapsible: show the first N lines, fade the rest. */\r
.collapsed .code {\r
  max-height: calc(\r
    (var(--_collapse-lines) + 0.6) * var(--_font-size) * var(--_line-height) + var(--_space-3)\r
  );\r
  overflow: hidden;\r
}\r
\r
.collapsed .code-view::after {\r
  content: '';\r
  position: absolute;\r
  inset: auto 0 0;\r
  height: calc(0.9 * var(--_font-size) * var(--_line-height));\r
  background: linear-gradient(transparent, var(--_code-bg-solid));\r
  pointer-events: none;\r
}\r
\r
.more {\r
  display: flex;\r
  justify-content: center;\r
  padding: var(--_space-2);\r
  border-top: 1px solid var(--_border);\r
  background: var(--_surface);\r
}\r
\r
/* ---------- Editor: a transparent textarea laid over the highlighted code ---------- */\r
\r
.editor {\r
  position: relative;\r
  width: max-content;\r
  min-width: 100%;\r
}\r
\r
.editor.wrap {\r
  width: auto;\r
}\r
\r
.editor-layer {\r
  pointer-events: none;\r
}\r
\r
/* Bold or italic tokens can shift characters in some fonts: keep the layer regular. */\r
.editor-layer .code * {\r
  font-style: inherit !important;\r
  font-weight: inherit !important;\r
}\r
\r
/* An empty last line still needs its height under the caret. */\r
.editor-layer .content:empty::before {\r
  content: '\\200b';\r
}\r
\r
.editor-input {\r
  position: absolute;\r
  top: 0;\r
  left: var(--_editor-gutter, 0px);\r
  width: calc(100% - var(--_editor-gutter, 0px));\r
  height: 100%;\r
  margin: 0;\r
  padding: var(--_space-3) var(--_space-4);\r
  overflow: hidden;\r
  border: 0;\r
  outline: none;\r
  background: transparent;\r
  color: transparent;\r
  -webkit-text-fill-color: transparent;\r
  caret-color: var(--_code-fg);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size);\r
  font-variant-ligatures: var(--vt-font-ligatures, none);\r
  line-height: var(--_line-height);\r
  tab-size: var(--_tab-size);\r
  white-space: pre;\r
  overflow-wrap: normal;\r
  resize: none;\r
}\r
\r
.editor.wrap .editor-input {\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
.editor-input::selection {\r
  background: color-mix(in srgb, var(--_accent) 32%, transparent);\r
}\r
\r
.editor-input::placeholder {\r
  color: var(--_fg-muted);\r
  -webkit-text-fill-color: var(--_fg-muted);\r
  opacity: 1;\r
}\r
\r
/* Long text: plain text while typing, highlighting after a pause. */\r
.editor.pending .editor-input {\r
  color: var(--_fg);\r
  -webkit-text-fill-color: var(--_fg);\r
}\r
\r
.editor.pending .editor-layer .content {\r
  visibility: hidden;\r
}\r
\r
.body:has(.editor-input:focus) {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: -2px;\r
}\r
\r
.edit-status {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  padding: var(--_space-2) var(--_space-3);\r
  border-top: 1px solid var(--_border);\r
  background: var(--_surface);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.edit-status.ok {\r
  color: var(--_success);\r
}\r
\r
.edit-status.bad {\r
  color: var(--_danger);\r
}\r
\r
.edit-status .icon {\r
  width: 14px;\r
  height: 14px;\r
  flex: none;\r
}\r
`;export{i as a};
