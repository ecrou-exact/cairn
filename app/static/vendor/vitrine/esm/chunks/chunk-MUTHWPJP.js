/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
var r=`/*\r
 * Form field: a label row, the control, a hint and a counter, and the error. The frame of\r
 * the other elements is not drawn: a field sits in a form like a native one.\r
 */\r
:host {\r
  margin-block: var(--vt-margin, 0 var(--_space-4));\r
}\r
\r
.vt {\r
  overflow: visible;\r
  background: transparent;\r
  border: 0;\r
  border-radius: 0;\r
}\r
\r
/* A theme set on the element is drawn on its own background, so its text stays readable on any page. */\r
:host([theme]:not([theme='auto'])) .vt {\r
  padding: var(--_space-2);\r
  background: var(--_surface);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
.field {\r
  position: relative;\r
  display: grid;\r
  gap: var(--_space-1);\r
  min-width: 0;\r
  color: var(--_fg);\r
  font: 400 14px / 1.45 var(--_font-ui);\r
}\r
\r
.field-top {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-1);\r
  min-width: 0;\r
}\r
\r
.field-label {\r
  color: var(--_fg);\r
  font-weight: 600;\r
  overflow-wrap: anywhere;\r
}\r
\r
.field-required {\r
  margin-left: 2px;\r
  color: var(--_danger);\r
}\r
\r
.field-optional {\r
  margin-left: var(--_space-2);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-weight: 400;\r
}\r
\r
/* ---------- Help ---------- */\r
\r
.field-tip-button,\r
.field-icon-button {\r
  display: inline-grid;\r
  flex: none;\r
  place-items: center;\r
  width: 28px;\r
  height: 28px;\r
  padding: 0;\r
  border: 0;\r
  border-radius: var(--_radius-full);\r
  background: transparent;\r
  color: var(--_fg-muted);\r
  cursor: pointer;\r
}\r
\r
.field-tip-button .icon,\r
.field-icon-button .icon {\r
  width: 16px;\r
  height: 16px;\r
}\r
\r
.field-tip-button:hover,\r
.field-tip-button[aria-expanded='true'],\r
.field-icon-button:hover {\r
  background: var(--_accent-soft);\r
  color: var(--_fg);\r
}\r
\r
.field-tip-button:focus-visible,\r
.field-icon-button:focus-visible,\r
.field-tip-close:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 1px;\r
}\r
\r
.field-tip {\r
  display: flex;\r
  align-items: flex-start;\r
  gap: var(--_space-2);\r
  padding: var(--_space-2) var(--_space-3);\r
  border: 1px solid var(--_border);\r
  border-left: 3px solid var(--_accent);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-raised);\r
  font-size: var(--_font-size-ui);\r
}\r
\r
.field-tip p {\r
  flex: 1;\r
  margin: 0;\r
  overflow-wrap: anywhere;\r
  white-space: pre-wrap;\r
}\r
\r
.field-tip-close {\r
  flex: none;\r
  width: 24px;\r
  height: 24px;\r
  border: 0;\r
  border-radius: var(--_radius-sm);\r
  background: transparent;\r
  color: var(--_fg-muted);\r
  font-size: 18px;\r
  line-height: 1;\r
  cursor: pointer;\r
}\r
\r
/* ---------- Text inputs ---------- */\r
\r
.field-box {\r
  display: flex;\r
  align-items: center;\r
  min-width: 0;\r
  min-height: 40px;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface);\r
}\r
\r
.field-box:focus-within {\r
  border-color: var(--_accent);\r
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--_accent) 35%, transparent);\r
}\r
\r
.has-error .field-box,\r
.field:has(.field-error:not(:empty)) .field-box {\r
  border-color: var(--_danger);\r
}\r
\r
.field-input {\r
  flex: 1;\r
  min-width: 0;\r
  min-height: 38px;\r
  padding: 0 var(--_space-3);\r
  border: 0;\r
  background: transparent;\r
  color: var(--_fg);\r
  font: inherit;\r
  outline: none;\r
}\r
\r
textarea.field-input {\r
  min-height: 80px;\r
  max-height: 400px;\r
  padding: var(--_space-2) var(--_space-3);\r
  resize: vertical;\r
}\r
\r
.field-input[type='color'] {\r
  min-width: 64px;\r
  padding: 4px;\r
}\r
\r
.field-input[type='range'] {\r
  accent-color: var(--_accent);\r
}\r
\r
.field-input::placeholder {\r
  color: var(--_fg-muted);\r
  opacity: 0.8;\r
}\r
\r
.field-prefix,\r
.field-suffix,\r
.field-output {\r
  flex: none;\r
  padding: 0 var(--_space-2);\r
  color: var(--_fg-muted);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.field-prefix {\r
  padding-left: var(--_space-3);\r
}\r
\r
.field-icon-button {\r
  margin-right: 4px;\r
}\r
\r
.disabled .field-box,\r
.disabled .field-trigger {\r
  opacity: 0.6;\r
  cursor: not-allowed;\r
}\r
\r
/* ---------- Hint, counter, error ---------- */\r
\r
.field-meta {\r
  display: flex;\r
  justify-content: space-between;\r
  gap: var(--_space-3);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.field-meta:empty,\r
.field-meta:has(> span:only-child:empty) {\r
  display: none;\r
}\r
\r
.field-hint {\r
  margin: 0;\r
  overflow-wrap: anywhere;\r
}\r
\r
.field-counter {\r
  flex: none;\r
  margin-left: auto;\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.field-counter.near {\r
  color: var(--_warning);\r
  font-weight: 600;\r
}\r
\r
.field-error {\r
  margin: 0;\r
  color: var(--_danger);\r
  font-size: var(--_font-size-ui);\r
  font-weight: 500;\r
}\r
\r
.field-error:empty {\r
  display: none;\r
}\r
\r
/* ---------- Check box and switch ---------- */\r
\r
.field-check {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-1);\r
}\r
\r
.field-check-label {\r
  position: relative;\r
  display: inline-flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  min-height: 32px;\r
  cursor: pointer;\r
}\r
\r
.field-check-input,\r
.field-choice input {\r
  width: 18px;\r
  height: 18px;\r
  margin: 0;\r
  accent-color: var(--_accent-fg);\r
}\r
\r
.field-check-input:focus-visible,\r
.field-choice input:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.field-switch-input {\r
  position: absolute;\r
  width: 40px;\r
  height: 22px;\r
  margin: 0;\r
  opacity: 0;\r
  cursor: pointer;\r
}\r
\r
.field-switch {\r
  position: relative;\r
  flex: none;\r
  width: 40px;\r
  height: 22px;\r
  border-radius: var(--_radius-full);\r
  background: var(--_border-strong);\r
  transition: background 120ms ease;\r
}\r
\r
.field-switch::after {\r
  position: absolute;\r
  top: 3px;\r
  left: 3px;\r
  width: 16px;\r
  height: 16px;\r
  border-radius: var(--_radius-full);\r
  background: var(--_surface);\r
  content: '';\r
  transition: transform 120ms ease;\r
}\r
\r
.field-switch-input:checked + .field-switch {\r
  background: var(--_accent);\r
}\r
\r
.field-switch-input:checked + .field-switch::after {\r
  transform: translateX(18px);\r
}\r
\r
.field-switch-input:focus-visible + .field-switch {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.field-switch-state {\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
/* ---------- Radio buttons and check boxes ---------- */\r
\r
.field-choices {\r
  display: grid;\r
  gap: var(--_space-1);\r
}\r
\r
.field-choice {\r
  display: flex;\r
  align-items: flex-start;\r
  gap: var(--_space-2);\r
  padding: var(--_space-1) 0;\r
  cursor: pointer;\r
}\r
\r
.field-choice input {\r
  flex: none;\r
  margin-top: 2px;\r
}\r
\r
.field-choice.disabled {\r
  color: var(--_fg-muted);\r
  cursor: not-allowed;\r
}\r
\r
.field-choice-text,\r
.field-option-text {\r
  display: grid;\r
  min-width: 0;\r
  overflow-wrap: anywhere;\r
}\r
\r
.field-option-note {\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
/* ---------- List ---------- */\r
\r
.field-list {\r
  position: relative;\r
  display: grid;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
}\r
\r
.field-trigger {\r
  display: flex;\r
  flex: 1;\r
  align-items: center;\r
  justify-content: space-between;\r
  gap: var(--_space-2);\r
  min-width: 0;\r
  min-height: 38px;\r
  padding: 0 var(--_space-3);\r
  border: 0;\r
  background: transparent;\r
  color: var(--_fg);\r
  font: inherit;\r
  text-align: left;\r
  cursor: pointer;\r
}\r
\r
.field-trigger:focus-visible {\r
  outline: none;\r
}\r
\r
.field-trigger.empty .field-trigger-text {\r
  color: var(--_fg-muted);\r
}\r
\r
.field-trigger-text {\r
  min-width: 0;\r
  overflow: hidden;\r
  text-overflow: ellipsis;\r
  white-space: nowrap;\r
}\r
\r
.field-trigger .icon {\r
  flex: none;\r
  width: 16px;\r
  height: 16px;\r
  color: var(--_fg-muted);\r
}\r
\r
.field-popup {\r
  position: absolute;\r
  top: 44px;\r
  right: 0;\r
  left: 0;\r
  z-index: 20;\r
  display: grid;\r
  gap: var(--_space-2);\r
  padding: var(--_space-2);\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-raised);\r
  box-shadow: 0 8px 24px rgb(0 0 0 / 14%);\r
}\r
\r
.field-listbox {\r
  max-height: 260px;\r
  margin: 0;\r
  padding: 0;\r
  overflow-y: auto;\r
  list-style: none;\r
  outline: none;\r
}\r
\r
.field-listbox:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 1px;\r
}\r
\r
.field-group {\r
  padding: var(--_space-2) var(--_space-2) 2px;\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-weight: 600;\r
  letter-spacing: 0.04em;\r
  text-transform: uppercase;\r
}\r
\r
.field-option {\r
  display: flex;\r
  align-items: flex-start;\r
  gap: var(--_space-2);\r
  padding: 6px var(--_space-2);\r
  border-radius: 4px;\r
  cursor: pointer;\r
}\r
\r
.field-option.active {\r
  background: var(--_accent-soft);\r
}\r
\r
.field-option.disabled {\r
  color: var(--_fg-muted);\r
  cursor: not-allowed;\r
}\r
\r
.field-check-mark {\r
  display: inline-grid;\r
  flex: none;\r
  place-items: center;\r
  width: 16px;\r
  height: 20px;\r
  color: var(--_accent-fg);\r
}\r
\r
.field-check-mark .icon {\r
  width: 16px;\r
  height: 16px;\r
}\r
\r
.field-empty {\r
  padding: var(--_space-2);\r
  color: var(--_fg-muted);\r
}\r
\r
.field-list-actions {\r
  display: flex;\r
  justify-content: space-between;\r
  gap: var(--_space-2);\r
  padding-top: var(--_space-2);\r
  border-top: 1px solid var(--_border);\r
}\r
\r
.field-chips {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-1);\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.field-chip {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: 2px;\r
  padding: 2px 4px 2px 10px;\r
  border-radius: var(--_radius-full);\r
  background: var(--_accent-soft);\r
  color: var(--_fg);\r
  font-size: var(--_font-size-ui);\r
}\r
\r
.field-chip button {\r
  display: inline-grid;\r
  place-items: center;\r
  width: 22px;\r
  height: 22px;\r
  padding: 0;\r
  border: 0;\r
  border-radius: var(--_radius-full);\r
  background: transparent;\r
  color: var(--_fg-muted);\r
  cursor: pointer;\r
}\r
\r
.field-chip button:hover {\r
  background: color-mix(in srgb, var(--_fg) 10%, transparent);\r
  color: var(--_fg);\r
}\r
\r
.field-chip button:focus-visible {\r
  outline: 2px solid var(--_accent);\r
}\r
\r
.field-chip .icon {\r
  width: 14px;\r
  height: 14px;\r
}\r
\r
@media (pointer: coarse) {\r
  .field-tip-button,\r
  .field-icon-button {\r
    width: 44px;\r
    height: 44px;\r
  }\r
\r
  .field-option {\r
    padding-block: 10px;\r
  }\r
}\r
\r
@media (prefers-reduced-motion: reduce) {\r
  .field-switch,\r
  .field-switch::after {\r
    transition: none;\r
  }\r
}\r
`;export{r as a};
