/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as O}from"./chunk-NPDHR5SA.js";import{a as P}from"./chunk-BNQD3D4I.js";import{O as _,_ as N,b as C,e as y,o as n,q as v,s as S}from"./chunk-7PAHM2BV.js";import{k as b,l as x,m as A}from"./chunk-TUK22DTT.js";var z=`/*\r
 * Pricing: controls, then plan cards that wrap to the width of the element, then a table\r
 * comparing the plans that scrolls on its own on narrow elements.\r
 */\r
.pricing-body {\r
  display: grid;\r
  gap: var(--_space-5);\r
  padding: var(--_space-4) var(--_space-5);\r
  background: var(--_surface);\r
  overscroll-behavior: auto;\r
}\r
\r
:host([max-height]) .pricing-body,\r
.vt[data-fullscreen] .pricing-body {\r
  overscroll-behavior: contain;\r
}\r
\r
.data-edit > .editor-body {\r
  max-height: min(40vh, 320px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
/* ---------- Controls ---------- */\r
\r
.pricing-controls {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: center;\r
  justify-content: center;\r
  gap: var(--_space-3);\r
}\r
\r
.pricing-periods {\r
  display: inline-flex;\r
  flex-wrap: wrap;\r
  gap: 2px;\r
  min-width: 0;\r
  margin: 0;\r
  padding: 2px;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-sunken);\r
}\r
\r
.pricing-period {\r
  position: relative;\r
  display: inline-flex;\r
  align-items: baseline;\r
  gap: var(--_space-1);\r
  padding: 5px 12px;\r
  border-radius: 4px;\r
  color: var(--_fg-muted);\r
  font: 500 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
  cursor: pointer;\r
}\r
\r
.pricing-period:hover {\r
  color: var(--_fg);\r
}\r
\r
.pricing-period.active {\r
  background: var(--_surface);\r
  box-shadow: 0 0 0 1px var(--_border-strong);\r
  color: var(--_fg);\r
}\r
\r
.pricing-period input {\r
  position: absolute;\r
  inset: 0;\r
  width: 100%;\r
  height: 100%;\r
  margin: 0;\r
  border-radius: inherit;\r
  opacity: 0;\r
  cursor: pointer;\r
}\r
\r
.pricing-period:has(input:focus-visible) {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 1px;\r
}\r
\r
.pricing-period-note {\r
  color: var(--_accent-fg);\r
  font-size: var(--_font-size-small);\r
  font-weight: 600;\r
}\r
\r
.pricing-currency select {\r
  min-height: 32px;\r
  padding: 0 var(--_space-2);\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-sunken);\r
  color: var(--_fg);\r
  font: 500 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.pricing-currency select:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 1px;\r
}\r
\r
/* ---------- Cards ---------- */\r
\r
.pricing-plans {\r
  display: grid;\r
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));\r
  gap: var(--_space-4);\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.pricing-plan {\r
  position: relative;\r
  display: flex;\r
  flex-direction: column;\r
  gap: var(--_space-3);\r
  min-width: 0;\r
  padding: var(--_space-4);\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius);\r
}\r
\r
.pricing-plan.highlight {\r
  border-color: var(--_accent);\r
  box-shadow: inset 0 0 0 1px var(--_accent);\r
}\r
\r
.pricing-badge {\r
  align-self: flex-start;\r
  padding: 2px 8px;\r
  border-radius: var(--_radius-full);\r
  background: var(--_accent);\r
  color: var(--_on-accent);\r
  font: 600 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
.pricing-name {\r
  margin: 0;\r
  color: var(--_fg);\r
  font: 600 16px / 1.3 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
.pricing-description,\r
.pricing-note {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.5 var(--_font-ui);\r
}\r
\r
.pricing-price {\r
  display: flex;\r
  flex-wrap: wrap;\r
  align-items: baseline;\r
  gap: 2px var(--_space-1);\r
  color: var(--_fg);\r
}\r
\r
.pricing-amount {\r
  font: 700 30px / 1.15 var(--_font-ui);\r
  font-variant-numeric: tabular-nums;\r
}\r
\r
.pricing-amount.small {\r
  font-size: 20px;\r
  font-weight: 600;\r
}\r
\r
.pricing-unit {\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.pricing-billed {\r
  flex-basis: 100%;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
.pricing-saving {\r
  margin: calc(var(--_space-2) * -1) 0 0;\r
  color: var(--_accent-fg);\r
  font: 600 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
.pricing-cta {\r
  display: block;\r
  min-height: 36px;\r
  padding: 8px 12px;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: transparent;\r
  color: var(--_fg);\r
  font: 600 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
  text-align: center;\r
  text-decoration: none;\r
  cursor: pointer;\r
}\r
\r
.pricing-cta:hover {\r
  background: var(--_accent-soft);\r
}\r
\r
.pricing-cta:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.pricing-cta.primary {\r
  border-color: var(--_accent);\r
  background: var(--_accent);\r
  color: var(--_on-accent);\r
}\r
\r
.pricing-cta.primary:hover {\r
  background: color-mix(in srgb, var(--_accent) 85%, var(--_fg));\r
  color: var(--_on-accent);\r
}\r
\r
.pricing-features {\r
  display: grid;\r
  gap: var(--_space-2);\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.pricing-features li {\r
  display: flex;\r
  align-items: flex-start;\r
  gap: var(--_space-2);\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-ui) / 1.45 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
.pricing-features li.excluded {\r
  color: var(--_fg-muted);\r
}\r
\r
.pricing-features .icon,\r
.pricing-mark .icon {\r
  flex: none;\r
  width: 16px;\r
  height: 16px;\r
  margin-top: 2px;\r
}\r
\r
.pricing-features .included .icon,\r
.pricing-mark.included .icon {\r
  color: var(--_success);\r
}\r
\r
.pricing-features .excluded .icon,\r
.pricing-mark.excluded .icon {\r
  color: var(--_fg-muted);\r
}\r
\r
/* ---------- Comparison ---------- */\r
\r
.pricing-compare {\r
  display: grid;\r
  gap: var(--_space-3);\r
  min-width: 0;\r
}\r
\r
.pricing-compare-title {\r
  margin: 0;\r
  color: var(--_fg);\r
  font: 600 16px / 1.3 var(--_font-ui);\r
}\r
\r
.pricing-scroll {\r
  overflow-x: auto;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
.pricing-scroll:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.pricing-scroll table {\r
  width: 100%;\r
  min-width: 480px;\r
  border-collapse: collapse;\r
  color: var(--_fg);\r
  font: 400 var(--_font-size-ui) / 1.45 var(--_font-ui);\r
}\r
\r
.pricing-scroll th,\r
.pricing-scroll td {\r
  padding: var(--_space-2) var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  text-align: center;\r
  vertical-align: top;\r
}\r
\r
.pricing-scroll tbody tr:last-child > * {\r
  border-bottom: 0;\r
}\r
\r
.pricing-scroll th:first-child {\r
  position: sticky;\r
  left: 0;\r
  z-index: 1;\r
  background: var(--_surface);\r
  font-weight: 500;\r
  text-align: left;\r
}\r
\r
.pricing-scroll thead th {\r
  font-weight: 600;\r
}\r
\r
.pricing-scroll .highlight {\r
  background: var(--_accent-soft);\r
}\r
\r
.pricing-group th,\r
.pricing-group th:first-child {\r
  background: var(--_surface-sunken);\r
  color: var(--_fg-muted);\r
  font: 600 var(--_font-size-small) / 1.3 var(--_font-ui);\r
  letter-spacing: 0.04em;\r
  text-align: left;\r
  text-transform: uppercase;\r
}\r
\r
.pricing-row-note {\r
  display: block;\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-weight: 400;\r
}\r
\r
.pricing-mark {\r
  display: inline-flex;\r
}\r
`;var m=Object.freeze({plans:12,rows:500,features:100,periods:6}),j=Object.freeze({monthly:1,month:1,quarterly:3,quarter:3,yearly:12,year:12,annual:12,annually:12}),w=/^[A-Z]{3}$/,p=a=>typeof a=="object"&&a!==null&&!Array.isArray(a);function l(a,r=500){return typeof a=="number"?String(a):typeof a=="string"?a.trim().slice(0,r):""}function I(a){let r=a.toLowerCase();return Object.hasOwn(j,r)?j[r]:0}function T(a){if(p(a)){let t=l(a.text??a.name);return t?{text:t,included:a.included!==!1}:null}let r=l(a);return r?{text:r,included:!0}:null}function q(a,r){let t=p(a.cta)?a.cta:{label:a.cta,url:a.url},e=l(t.url,2e3),i=Array.isArray(a.features)?a.features:[];return{id:l(a.id,100)||`plan-${r}`,name:l(a.name,200),description:l(a.description),badge:l(a.badge,60),highlight:a.highlight===!0,unit:l(a.unit,60),price:a.price,cta:l(t.label,100),url:e&&S(e)?e:null,features:i.slice(0,m.features).map(T).filter(o=>o!==null)}}function R(a){if(!Array.isArray(a))return[];let r=[];for(let t of a.slice(0,m.periods)){let e=p(t)?t:{id:t},i=l(e.id,60);if(!i)continue;let o=Number(e.months);r.push({id:i,label:l(e.label,60),months:Number.isFinite(o)&&o>=0?o:I(i),note:l(e.note,60)})}return r}function Y(a){let r=new Set;for(let t of a)if(p(t.price))for(let e of Object.keys(t.price))w.test(e)||r.add(e);return[...r].slice(0,m.periods).map(t=>({id:t,label:"",months:I(t),note:""})).sort((t,e)=>t.months-e.months)}function D(a,r){let t=(Array.isArray(r)?r:[r]).map(o=>l(o,10).toUpperCase()).filter(o=>w.test(o));if(t.length)return[...new Set(t)];let e=new Set,i=o=>{if(p(o))for(let[s,c]of Object.entries(o))w.test(s)?e.add(s):i(c)};for(let o of a)i(o.price);return e.size?[...e]:["USD"]}function L(a){return Array.isArray(a)?a.filter(p).slice(0,m.rows).map(r=>{let t=Object.create(null);if(p(r.values))for(let[e,i]of Object.entries(r.values))t[e]=typeof i=="boolean"?i:l(i,200);return{name:l(r.name,200),description:l(r.description),group:l(r.group,200),values:t}}).filter(r=>r.name):[]}function k(a){let r;try{r=JSON.parse(a)}catch(i){return{ok:!1,error:"json",message:i instanceof Error?i.message:""}}if(Array.isArray(r)&&(r={plans:r}),!p(r)||!Array.isArray(r.plans))return{ok:!1,error:"shape",message:""};let t=r.plans.filter(p).slice(0,m.plans).map(q),e=R(r.periods);return{ok:!0,pricing:{currencies:D(t,r.currencies??r.currency),periods:e.length?e:Y(t),plans:t,rows:L(r.compare??r.rows),note:l(r.note,1e3)}}}function h(a,r,t){let e=a.price;if(p(e)&&r!==null&&Object.hasOwn(e,r)&&(e=e[r]),p(e)&&(e=Object.hasOwn(e,t)?e[t]:null),typeof e=="number"&&Number.isFinite(e)&&e>=0)return{kind:"amount",amount:e};let i=l(e,60);return i?{kind:"text",text:i}:{kind:"none"}}function E(a,r,t,e){if(t.months<=0)return 0;let i=h(a,t.id,e);if(i.kind!=="amount"||i.amount===0)return 0;let o=r.periods.filter(u=>u.months>0&&u.months<t.months);if(!o.length)return 0;let s=o.reduce((u,f)=>f.months<u.months?f:u),c=h(a,s.id,e);if(c.kind!=="amount"||c.amount===0)return 0;let d=i.amount/t.months,g=c.amount/s.months;return Math.max(0,Math.round((1-d/g)*100))}var F=Object.freeze({pricingPeriod:"Billing period",pricingCurrency:"Currency",pricingPeriod_monthly:"Monthly",pricingPeriod_quarterly:"Quarterly",pricingPeriod_yearly:"Yearly",pricingFree:"Free",pricingPerMonth:"/ month",pricingPerYear:"/ year",pricingBilled:"{amount} billed every {months} months",pricingBilledYearly:"{amount} billed yearly",pricingSave:"Save {percent}%",pricingChoose:"Choose {name}",pricingCompare:"Compare plans",pricingFeature:"Feature",pricingIncluded:"Included",pricingExcluded:"Not included",pricingNoPrice:"Price not available",pricingEmpty:"No plans.",pricingInvalidJson:"This is not valid JSON: {message}",pricingInvalidShape:'Pricing is an object with a "plans" list.'}),M=Object.freeze({pricingPeriod:"P\xE9riode de facturation",pricingCurrency:"Devise",pricingPeriod_monthly:"Mensuel",pricingPeriod_quarterly:"Trimestriel",pricingPeriod_yearly:"Annuel",pricingFree:"Gratuit",pricingPerMonth:"/ mois",pricingPerYear:"/ an",pricingBilled:"{amount} factur\xE9s tous les {months} mois",pricingBilledYearly:"{amount} factur\xE9s par an",pricingSave:"{percent} % d\u2019\xE9conomie",pricingChoose:"Choisir {name}",pricingCompare:"Comparer les offres",pricingFeature:"Fonctionnalit\xE9",pricingIncluded:"Inclus",pricingExcluded:"Non inclus",pricingNoPrice:"Prix non disponible",pricingEmpty:"Aucune offre.",pricingInvalidJson:"Ce n'est pas du JSON valide : {message}",pricingInvalidShape:"Une grille tarifaire est un objet avec une liste \xAB plans \xBB."});A({en:F,fr:M});var U=["_self","_blank"],J=["monthly","total"],B=class extends O{static type="pricing";static componentAttributes=Object.freeze(["period","currency","display","compare","link-target"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,download:!0,fullscreen:!0}};static styles=[C,P,z];constructor(){super(),this.panelId=v("panel"),this.groupName=v("period"),this.currencyId=v("currency"),this.periodState=null,this.currencyState=null}get pricing(){let r=k(this.text??"");return r.ok?r.pricing:null}get selectedPeriod(){return this.activePeriod(this.pricing)?.id??null}set selectedPeriod(r){this.periodState=r,this.requestRender()}get selectedCurrency(){return this.activeCurrency(this.pricing)}set selectedCurrency(r){this.currencyState=r,this.requestRender()}attributeChangedCallback(r,t,e){r==="period"&&t!==e&&(this.periodState=null),r==="currency"&&t!==e&&(this.currencyState=null),super.attributeChangedCallback(r,t,e)}activePeriod(r){if(!r?.periods.length)return null;let t=this.periodState??this.getAttribute("period");return r.periods.find(e=>e.id===t)??r.periods[0]}activeCurrency(r){let t=r?.currencies??[],e=(this.currencyState??this.getAttribute("currency")??"").toUpperCase();return t.includes(e)?e:t[0]??"USD"}renderContent(r){let t=this.t,e=k(this.text??""),i=n("div",{class:"body pricing-body",part:"body"});e.ok?e.pricing.plans.length?this.renderPlans(i,e.pricing):i.append(n("p",{class:"pricing-note",text:t("pricingEmpty")})):i.append(N(e.error==="json"?t("pricingInvalidJson",{message:e.message}):t("pricingInvalidShape")));let{panel:o,history:s}=this.previewPanel(i,this.panelId);r.append(...this.chrome({badge:"JSON",actions:[...s,this.editToggleButton(),this.fullscreenButton(),this.feature("download")?this.downloadButton(()=>this.text??"",this.downloadName("pricing.json"),"application/json"):null,this.feature("copy")?this.copyButton(()=>this.text??""):null]}),o),this.editor?.align()}renderPlans(r,t){let e=this.activePeriod(t),i=this.activeCurrency(t),o=this.controls(t,e,i);o&&r.append(o),r.append(n("ul",{class:"pricing-plans",part:"plans"},...t.plans.map(s=>this.planCard(s,t,e,i)))),t.rows.length&&this.flag("compare")&&r.append(this.compareTable(t)),t.note&&r.append(n("p",{class:"pricing-note",text:t.note}))}controls(r,t,e){let i=r.periods.length>1?this.periodSwitch(r,t):null,o=r.currencies.length>1?this.currencyPicker(r,e):null;return i||o?n("div",{class:"pricing-controls",part:"controls"},i,o):null}periodSwitch(r,t){return n("fieldset",{class:"pricing-periods"},n("legend",{class:"sr-only",text:this.t("pricingPeriod")}),...r.periods.map(e=>{let i=e.id===t?.id;return n("label",{class:`pricing-period${i?" active":""}`,part:"period"},n("input",{attrs:{type:"radio",name:this.groupName,value:e.id,checked:i,"data-focus-key":`period-${e.id}`},on:{change:()=>{this.periodState=e.id,this.changed(r)}}}),n("span",{text:this.periodLabel(e)}),e.note?n("span",{class:"pricing-period-note",text:e.note}):null)}))}periodLabel(r){if(r.label)return r.label;let t={month:"monthly",monthly:"monthly",quarter:"quarterly",quarterly:"quarterly",year:"yearly",yearly:"yearly",annual:"yearly",annually:"yearly"}[r.id.toLowerCase()];return t?this.t(`pricingPeriod_${t}`):r.id.charAt(0).toUpperCase()+r.id.slice(1)}currencyPicker(r,t){return n("div",{class:"pricing-currency"},n("label",{class:"sr-only",text:this.t("pricingCurrency"),attrs:{for:this.currencyId}}),n("select",{part:"currency",attrs:{id:this.currencyId,"data-focus-key":"currency"},on:{change:e=>{this.currencyState=e.target.value,this.changed(r)}}},...r.currencies.map(e=>n("option",{text:e,attrs:{value:e,selected:e===t}}))))}changed(r){this.render();let t=this.activePeriod(r)?.id??null,e=this.activeCurrency(r);x(this,b.PRICING_CHANGE,{period:t,currency:e})}planCard(r,t,e,i){let o=this.t,s=e?E(r,t,e,i):0;return n("li",{class:`pricing-plan${r.highlight?" highlight":""}`,part:r.highlight?"plan plan-highlight":"plan"},r.badge?n("span",{class:"pricing-badge",text:r.badge}):null,n("h3",{class:"pricing-name",text:r.name}),r.description?n("p",{class:"pricing-description",text:r.description}):null,this.priceView(r,e,i),s?n("p",{class:"pricing-saving",part:"saving",text:o("pricingSave",{percent:s})}):null,this.ctaView(r,e,i),r.features.length?n("ul",{class:"pricing-features"},...r.features.map(c=>n("li",{class:c.included?"included":"excluded",part:"feature"},_(c.included?"check":"close"),n("span",{class:"sr-only",text:o(c.included?"pricingIncluded":"pricingExcluded")}),n("span",{text:c.text})))):null)}priceView(r,t,e){let i=this.t,o=h(r,t?.id??null,e),s=n("div",{class:"pricing-price",part:"price"});if(o.kind==="none")return s.append(n("span",{class:"pricing-amount small",text:i("pricingNoPrice")})),s;if(o.kind==="text")return s.append(n("span",{class:"pricing-amount small",text:o.text})),s;if(o.amount===0)return s.append(n("span",{class:"pricing-amount",text:i("pricingFree")})),s;let c=t?.months??0,d=c>0&&y(this.getAttribute("display"),J,"monthly")==="monthly",g=d?o.amount/c:o.amount;s.append(n("span",{class:"pricing-amount",text:this.money(g,e)}));let u=[d||c===1?i("pricingPerMonth"):c===12?i("pricingPerYear"):"",r.unit].filter(Boolean).join(" ");if(u&&s.append(n("span",{class:"pricing-unit",text:u})),d&&c>1){let f=this.money(o.amount,e);s.append(n("span",{class:"pricing-billed",text:c===12?i("pricingBilledYearly",{amount:f}):i("pricingBilled",{amount:f,months:c})}))}return s}ctaView(r,t,e){let i=r.cta||this.t("pricingChoose",{name:r.name}),o=`pricing-cta${r.highlight?" primary":""}`,s=d=>{let g=h(r,t?.id??null,e);x(this,b.PLAN_SELECT,{plan:r.id,name:r.name,period:t?.id??null,currency:e,amount:g.kind==="amount"?g.amount:null,url:r.url})||d.preventDefault()};if(!r.url)return n("button",{class:o,part:"cta",text:i,attrs:{type:"button","data-focus-key":`cta-${r.id}`},on:{click:s}});let c=y(this.getAttribute("link-target"),U,"_self");return n("a",{class:o,part:"cta",text:i,attrs:{href:r.url,"data-focus-key":`cta-${r.id}`,target:c==="_blank"?"_blank":null,rel:c==="_blank"?"noopener noreferrer":null},on:{click:s}})}money(r,t){let e=Math.round(r*100)/100,i=Number.isInteger(e)?0:2;try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:t,minimumFractionDigits:i,maximumFractionDigits:i}).format(e)}catch{return`${e} ${t}`}}compareTable(r){let t=this.t,{plans:e,rows:i}=r,o=[],s="";for(let c of i)c.group&&c.group!==s&&(s=c.group,o.push(n("tr",{class:"pricing-group"},n("th",{text:s,attrs:{colspan:e.length+1,scope:"colgroup"}})))),o.push(this.compareRow(c,e));return n("section",{class:"pricing-compare",attrs:{"aria-label":t("pricingCompare")}},n("h3",{class:"pricing-compare-title",text:t("pricingCompare")}),n("div",{class:"pricing-scroll",attrs:{role:"region",tabindex:"0","aria-label":t("pricingCompare")}},n("table",{part:"compare"},n("thead",{},n("tr",{},n("th",{text:t("pricingFeature"),attrs:{scope:"col"}}),...e.map(c=>n("th",{class:c.highlight?"highlight":void 0,text:c.name,attrs:{scope:"col"}})))),n("tbody",{},...o))))}compareRow(r,t){return n("tr",{},n("th",{attrs:{scope:"row"}},n("span",{text:r.name}),r.description?n("span",{class:"pricing-row-note",text:r.description}):null),...t.map(e=>n("td",{class:e.highlight?"highlight":void 0},this.compareValue(r.values[e.id]))))}compareValue(r){let t=this.t;if(r===!0||r===!1||r===void 0||r===""){let e=r===!0;return n("span",{class:`pricing-mark ${e?"included":"excluded"}`},_(e?"check":"close"),n("span",{class:"sr-only",text:t(e?"pricingIncluded":"pricingExcluded")}))}return n("span",{text:r})}};export{B as a};
