/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
var a=`/*\r
 * CSV table. Header names are data: their case is kept (no uppercase label style).\r
 */\r
.table-host {\r
  display: flex;\r
  flex-direction: column;\r
  min-height: 0;\r
}\r
\r
.table-body {\r
  background: var(--_surface);\r
}\r
\r
.grid {\r
  min-width: 100%;\r
  border-collapse: separate;\r
  border-spacing: 0;\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-ui);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.grid th,\r
.grid td {\r
  max-width: 40ch;\r
  padding: 6px var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  text-align: start;\r
  vertical-align: top;\r
  white-space: pre-wrap;\r
  overflow-wrap: anywhere;\r
}\r
\r
.grid thead th {\r
  position: sticky;\r
  top: 0;\r
  z-index: 2;\r
  background: var(--_surface-sunken);\r
  color: var(--_fg);\r
  font-weight: 600;\r
  white-space: nowrap;\r
}\r
\r
.grid tbody tr:hover > * {\r
  background: color-mix(in srgb, var(--_accent-soft) 60%, transparent);\r
}\r
\r
.grid .col-number {\r
  text-align: end;\r
}\r
\r
.grid .row-number {\r
  position: sticky;\r
  left: 0;\r
  z-index: 1;\r
  width: 1%;\r
  background: var(--_surface);\r
  color: var(--_fg-muted);\r
  font-weight: 400;\r
  text-align: end;\r
  white-space: nowrap;\r
}\r
\r
.grid thead .row-number {\r
  z-index: 3;\r
  background: var(--_surface-sunken);\r
}\r
\r
.grid .sort {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: 6px;\r
  max-width: 100%;\r
  padding: 0;\r
  border: 0;\r
  background: none;\r
  color: inherit;\r
  font: inherit;\r
  cursor: pointer;\r
}\r
\r
.grid .col-number .sort {\r
  flex-direction: row-reverse;\r
}\r
\r
.grid .sort .name {\r
  overflow: hidden;\r
  text-overflow: ellipsis;\r
}\r
\r
.grid .sort .icon {\r
  flex: none;\r
  width: 14px;\r
  height: 14px;\r
  color: var(--_fg-muted);\r
}\r
\r
.grid [aria-sort='ascending'] .icon,\r
.grid [aria-sort='descending'] .icon {\r
  color: var(--_accent-fg);\r
}\r
\r
.grid .no-rows {\r
  padding: var(--_space-5);\r
  color: var(--_fg-muted);\r
  text-align: center;\r
}\r
\r
.pager {\r
  display: flex;\r
  align-items: center;\r
  justify-content: space-between;\r
  gap: var(--_space-3);\r
  min-height: 40px;\r
  padding: 0 var(--_space-2) 0 var(--_space-3);\r
  border-top: 1px solid var(--_border);\r
  background: var(--_surface);\r
  color: var(--_fg-muted);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-small);\r
}\r
`;export{a};
