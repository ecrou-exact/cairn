/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{A as Z,B as tt,c as U,e as P,g as $,h as g,j as q,k as p,l as f,o as J,p as L,q as Q,r as G,v as W,w as X,x as Y,y as K}from"./chunk-TUK22DTT.js";function Kt(e){U(new URL("languages/",e).href),$(new URL("syntax-themes/",e).href),P(new URL("vendor/",e).href)}var et=`/*\r
 * Syntax highlighting roles for highlight.js classes.\r
 * Mapping: docs/DESIGN_SYSTEM.md \xA72.3. Colors come from theme tokens.\r
 */\r
.hljs-keyword,\r
.hljs-built_in,\r
.hljs-literal,\r
.hljs-bullet,\r
.hljs-doctag {\r
  color: var(--_syntax-keyword);\r
}\r
\r
.hljs-string,\r
.hljs-regexp,\r
.hljs-symbol,\r
.hljs-char,\r
.hljs-code,\r
.hljs-link {\r
  color: var(--_syntax-string);\r
}\r
\r
.hljs-number {\r
  color: var(--_syntax-number);\r
}\r
\r
.hljs-title,\r
.hljs-title.function_,\r
.hljs-section,\r
.hljs-selector-class,\r
.hljs-selector-id {\r
  color: var(--_syntax-function);\r
}\r
\r
.hljs-type,\r
.hljs-title.class_,\r
.hljs-title.class_.inherited__ {\r
  color: var(--_syntax-type);\r
}\r
\r
.hljs-comment,\r
.hljs-quote {\r
  color: var(--_syntax-comment);\r
  font-style: italic;\r
}\r
\r
.hljs-attr,\r
.hljs-attribute,\r
.hljs-property,\r
.hljs-template-variable,\r
.hljs-variable.language_ {\r
  color: var(--_syntax-attr);\r
}\r
\r
.hljs-tag,\r
.hljs-name,\r
.hljs-selector-tag,\r
.hljs-selector-pseudo,\r
.hljs-selector-attr {\r
  color: var(--_syntax-tag);\r
}\r
\r
.hljs-meta,\r
.hljs-punctuation,\r
.hljs-operator,\r
.hljs-tag .hljs-punctuation {\r
  color: var(--_syntax-meta);\r
}\r
\r
.hljs-meta .hljs-keyword {\r
  color: var(--_syntax-keyword);\r
}\r
\r
.hljs-meta .hljs-string {\r
  color: var(--_syntax-string);\r
}\r
\r
.hljs-addition {\r
  color: var(--_success);\r
}\r
\r
.hljs-deletion {\r
  color: var(--_danger);\r
}\r
\r
.hljs-section,\r
.hljs-strong {\r
  font-weight: 600;\r
}\r
\r
.hljs-emphasis {\r
  font-style: italic;\r
}\r
\r
.hljs-link {\r
  text-decoration: underline;\r
  text-underline-offset: 3px;\r
}\r
`;function b(e){if(e===null)return null;let t=e.trim().toLowerCase();return!(t==="false"||t==="off"||t==="no"||t==="0")}function ee(e,{min:t,max:r,fallback:n}){if(e===null||e.length>32)return n;let s=e.trim();if(!/^[+-]?\d+$/.test(s))return n;let a=Number(s);return Number.isSafeInteger(a)?Math.min(r,Math.max(t,a)):n}function N(e,t,r){if(e===null)return r;let n=e.trim().toLowerCase();return t.includes(n)?n:r}function re(e,t){if(e===null||e.length>1e3)return null;let r=[];for(let n of e.split(",")){let s=n.trim().toLowerCase();t.includes(s)&&!r.includes(s)&&r.push(s)}return r.length?r:null}var Tt=500;function ne(e){if(!e||e.length>1e3*10)return[];let t=[];for(let n of e.split(",")){if(t.length>=Tt)break;let s=/^\s*(\d{1,9})\s*(?:-\s*(\d{1,9})\s*)?$/.exec(n);if(!s)continue;let a=Number(s[1]),o=s[2]===void 0?a:Number(s[2]);t.push([Math.min(a,o),Math.max(a,o)])}t.sort((n,s)=>n[0]-s[0]);let r=[];for(let n of t){let s=r[r.length-1];s&&n[0]<=s[1]+1?s[1]=Math.max(s[1],n[1]):r.push([n[0],n[1]])}return r}function se(e,t){let r=0,n=t.length-1;for(;r<=n;){let s=r+n>>1,[a,o]=t[s];if(e<a)n=s-1;else if(e>o)r=s+1;else return!0}return!1}function rt(e){if(e===null)return null;let t=e.trim().toLowerCase();return/^\d{1,6}(?:\.\d{1,4})?(?:px|em|rem|vh|svh|lvh|dvh|%|ch|lh)$/.test(t)?t:null}function nt(e,t=200){if(!e)return"";let n=e.slice(0,t*4).replace(/[\u0000-\u001f\u007f-\u009f]/g,"").replace(/\s+/g," ").trim();return n.length>t?n.slice(0,t-1)+"\u2026":n}function st(e,t){let r=(e??"").split(/[\\/]/).pop()??"",n=/[\u0000-\u001f\u007f<>:"|?*]/g;return r.replace(n,"").replace(/^[.\s]+/,"").trim().slice(0,120)||t}async function z(e,t=document){if(navigator.clipboard&&window.isSecureContext)try{return await navigator.clipboard.writeText(e),!0}catch{}return St(e,t)}function St(e,t){let r=document.createElement("textarea");r.value=e,r.setAttribute("readonly",""),r.setAttribute("aria-hidden","true"),r.style.position="fixed",r.style.opacity="0",r.style.pointerEvents="none",(t instanceof Document?t.body:t).appendChild(r);try{return r.select(),document.execCommand("copy")}catch{return!1}finally{r.remove()}}function at(e,t,r="text/plain"){let n=new Blob([e],{type:`${r};charset=utf-8`}),s=URL.createObjectURL(n),a=document.createElement("a");a.href=s,a.download=t,a.rel="noopener",a.style.display="none",document.body.appendChild(a),a.click(),a.remove(),setTimeout(()=>URL.revokeObjectURL(s),1e3)}function l(e,t={},...r){let n=document.createElement(e);if(t.class&&(n.className=t.class),t.part&&n.setAttribute("part",t.part),t.attrs)for(let[s,a]of Object.entries(t.attrs))a===!1||a===null||a===void 0||n.setAttribute(s,a===!0?"":String(a));if(t.text!==void 0&&(n.textContent=t.text),t.on)for(let[s,a]of Object.entries(t.on))n.addEventListener(s,a);return jt(n,r),n}function jt(e,t){for(let r of t)r==null||r===!1||e.append(typeof r=="string"?document.createTextNode(r):r)}var ot=0;function it(e){return ot+=1,`vt-${e}-${ot}`}function E(e){let t=e.replace(/\r\n?/g,`
`).split(`
`);for(;t.length&&t[0].trim()==="";)t.shift();for(;t.length&&t[t.length-1].trim()==="";)t.pop();let r=1/0;for(let n of t){if(n.trim()==="")continue;let s=/^[ \t]*/.exec(n);if(r=Math.min(r,s?s[0].length:0),r===0)break}return!Number.isFinite(r)||r===0?t.join(`
`):t.map(n=>n.slice(r)).join(`
`)}function lt(e,t){let r,n=(...s)=>{clearTimeout(r),r=setTimeout(()=>e(...s),t)};return n.cancel=()=>clearTimeout(r),n}var Lt=new Set(["http:","https:","mailto:","tel:"]),Nt=/^data:image\/(?:png|gif|jpe?g|webp|avif);base64,[a-z0-9+/]+=*$/i;function O(e,t={}){if(typeof e!="string")return!1;let r=0,n=e.length;for(;r<n&&e.charCodeAt(r)<=32;)r+=1;for(;n>r&&e.charCodeAt(n-1)<=32;)n-=1;let s=e.slice(r,n).replace(/[\t\n\r]/g,"");if(s===""||t.allowDataImage&&Nt.test(s))return!0;let a=/^([a-z][a-z0-9+.-]*):/i.exec(s);return a?Lt.has(a[1].toLowerCase()+":"):!0}function ct(e){try{return new URL(e,document.baseURI).origin===location.origin}catch{return!1}}function le(e){let t=e.toLowerCase().replace(/^\[|\]$/g,"").replace(/\.$/,"");if(t.includes(":")||/^\d{1,3}(?:\.\d{1,3}){3}$/.test(t))return t;let r=t.split(".").filter(Boolean),n=r.slice(-2).join(".");return r.length>2&&/^(?:co|com|net|org|gov|ac|edu|ne|or)\.[a-z]{2}$/.test(n)?r.slice(-3).join("."):n}var d=class extends Error{constructor(t,r={},n){super(t,n===void 0?void 0:{cause:n}),this.name="VitrineError",this.code=t,this.params=r}},zt=new Set(["text/plain","text/markdown","text/x-markdown","application/json","text/json","application/xml","text/xml"]);function ht(e){for(let n of Array.from(e.children)){if(n.hasAttribute("data-json"))continue;let s=Ot(n);if(s!==null)return s}let t="";for(let n of Array.from(e.childNodes))n.nodeType===Node.TEXT_NODE||n.nodeType===Node.CDATA_SECTION_NODE?t+=n.nodeValue??"":n.nodeType===Node.ELEMENT_NODE&&!n.hasAttribute("data-json")&&(t+=n.textContent??"");let r=E(t);return r===""?null:r}function Ot(e){if(e instanceof HTMLTemplateElement){let t=e.content.children.length>0;return E(t?e.innerHTML:e.content.textContent??"")}return e instanceof HTMLScriptElement&&zt.has(e.type.trim().toLowerCase())?E(e.textContent??""):null}function _(e,t){if(e.length>t)throw new d("tooLarge",{size:e.length,limit:t})}async function R(e,t){let r=Rt(e),n=ct(r.href);if(!n&&!t.allowRemote)throw new d("remoteBlocked");let s=new AbortController,a=setTimeout(()=>s.abort(new d("timeout")),t.timeout),o=()=>s.abort(t.signal?.reason);t.signal?.addEventListener("abort",o,{once:!0}),t.signal?.aborted&&o();try{let i=await fetch(r.href,{mode:n?"same-origin":"cors",credentials:"same-origin",redirect:"follow",referrerPolicy:"strict-origin-when-cross-origin",signal:s.signal});if(!i.ok)throw new d("loadFailed",{url:dt(r),reason:`HTTP ${i.status}`});let c=Number(i.headers.get("content-length"));if(Number.isFinite(c)&&c>t.maxSize*4)throw new d("tooLarge",{size:c,limit:t.maxSize});return await Ht(i,t.maxSize,s)}catch(i){throw Ft(i,s.signal,r)}finally{clearTimeout(a),t.signal?.removeEventListener("abort",o)}}function Rt(e){let t;try{t=new URL(e.trim(),document.baseURI)}catch{throw new d("unsafeUrl")}if(t.protocol!=="http:"&&t.protocol!=="https:")throw new d("unsafeUrl");return t}async function Ht(e,t,r){if(!e.body){let o=await e.text();return _(o,t),o}let n=e.body.getReader(),s=new TextDecoder,a="";for(;;){let{done:o,value:i}=await n.read();if(o)break;if(a+=s.decode(i,{stream:!0}),a.length>t)throw r.abort(),new d("tooLarge",{size:`> ${t}`,limit:t})}return a+=s.decode(),_(a,t),a}function Ft(e,t,r){if(e instanceof d)return e;if(t.aborted&&t.reason instanceof d)return t.reason;if(e instanceof DOMException&&e.name==="AbortError")return e;let n=e instanceof Error?e.message:String(e);return new d("loadFailed",{url:dt(r),reason:n},e)}function dt(e){let t=e.origin===location.origin?e.pathname+e.search:e.href;return t.length>120?t.slice(0,119)+"\u2026":t}function H(e){return e instanceof DOMException&&e.name==="AbortError"}var It=864e13,Bt=1e3,x=e=>typeof e=="object"&&e!==null&&!Array.isArray(e);function ut(e,t=4e3){return typeof e=="number"&&Number.isFinite(e)?String(e):typeof e=="string"?e.trim().slice(0,t):""}function fe(e,t,r){for(let n of t){let s=ut(e[n],r);if(s)return s}return""}function me(e){let t=ut(e,2e3);return t&&O(t)?t:null}function ge(e){if(typeof e!="string")return null;let t=e.trim().slice(0,5e6);return t&&O(t,{allowDataImage:!0})?t:null}function be(e){if(typeof e=="number"&&Number.isFinite(e)){let r=Math.abs(e)>1e11?e:e*1e3;return Math.abs(r)<=It?r:null}if(typeof e!="string")return null;let t=Date.parse(e);return Number.isNaN(t)?null:t}function xe(e){if(typeof e=="number")return Number.isFinite(e)?e:null;if(typeof e!="string"||!e.trim())return null;let t=Number(e);return Number.isFinite(t)?t:null}function ve(e,t){let r;try{r=JSON.parse(e)}catch(s){return{ok:!1,error:"json",message:s instanceof Error?s.message:""}}let n=r;return x(r)&&(n=t.map(s=>r[s]).find(Array.isArray)),Array.isArray(n)?{ok:!0,items:n.filter(x).slice(0,Bt),root:x(r)?r:{}}:{ok:!1,error:"shape",message:t.map(s=>`"${s}"`).join(", ")}}function ye(e){let t=e.split(/\s+/).filter(Boolean);return(t.length>1?[t[0],t[t.length-1]]:t).map(n=>[...n][0]??"").join("").toUpperCase()}function pt(e,t){let r=t.replace(/\[(\d+)\]/g,".$1").split(".").map(s=>s.trim()).filter(Boolean),n=e;for(let s of r.slice(0,32))if(Array.isArray(n)&&/^\d+$/.test(s)&&Number(s)<n.length)n=n[Number(s)];else if(x(n)&&Object.hasOwn(n,s))n=n[s];else return{ok:!1};return{ok:!0,value:n}}function F(e){return JSON.stringify(e===void 0?null:e,null,2)??"null"}function ke(e,{keys:t,attributes:r={},otherwise:n}){if(typeof e=="string")return{content:e};if(x(e)){let s=t.find(a=>typeof e[a]=="string");if(s!==void 0){let a={};for(let[o,i]of Object.entries(r))Object.hasOwn(e,o)&&!Object.hasOwn(a,i)&&(a[i]=e[o]);return{content:e[s],attributes:a}}}return n?n(e):{content:F(e)}}function Me(e,t){if(Array.isArray(e))return e;if(!x(e))return null;for(let r of t)if(Array.isArray(e[r]))return e[r];return null}var ft="http://www.w3.org/2000/svg";var w=["path",{d:"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"}],k=["path",{d:"M14 2v4a2 2 0 0 0 2 2h4"}],mt={copy:[["rect",{width:"14",height:"14",x:"8",y:"8",rx:"2",ry:"2"}],["path",{d:"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"}]],check:[["path",{d:"M20 6 9 17l-5-5"}]],search:[["path",{d:"m21 21-4.34-4.34"}],["circle",{cx:"11",cy:"11",r:"8"}]],"chevron-up":[["path",{d:"m18 15-6-6-6 6"}]],"chevron-down":[["path",{d:"m6 9 6 6 6-6"}]],"chevron-right":[["path",{d:"m9 18 6-6-6-6"}]],wrap:[["path",{d:"m16 16-3 3 3 3"}],["path",{d:"M3 12h14.5a1 1 0 0 1 0 7H13"}],["path",{d:"M3 19h6"}],["path",{d:"M3 5h18"}]],download:[["path",{d:"M12 15V3"}],["path",{d:"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"}],["path",{d:"m7 10 5 5 5-5"}]],"expand-all":[["path",{d:"m7 15 5 5 5-5"}],["path",{d:"m7 9 5-5 5 5"}]],"collapse-all":[["path",{d:"m7 20 5-5 5 5"}],["path",{d:"m7 4 5 5 5-5"}]],link:[["path",{d:"M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"}],["path",{d:"M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"}]],eye:[["path",{d:"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"}],["circle",{cx:"12",cy:"12",r:"3"}]],code:[["path",{d:"m16 18 6-6-6-6"}],["path",{d:"m8 6-6 6 6 6"}]],columns:[["rect",{width:"18",height:"18",x:"3",y:"3",rx:"2"}],["path",{d:"M12 3v18"}]],list:[["path",{d:"M3 5h.01"}],["path",{d:"M3 12h.01"}],["path",{d:"M3 19h.01"}],["path",{d:"M8 5h13"}],["path",{d:"M8 12h13"}],["path",{d:"M8 19h13"}]],pencil:[["path",{d:"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"}],["path",{d:"m15 5 4 4"}]],"chevron-left":[["path",{d:"m15 18-6-6 6-6"}]],"chevrons-left":[["path",{d:"m11 17-5-5 5-5"}],["path",{d:"m18 17-5-5 5-5"}]],"chevrons-right":[["path",{d:"m6 17 5-5-5-5"}],["path",{d:"m13 17 5-5-5-5"}]],sort:[["path",{d:"m21 16-4 4-4-4"}],["path",{d:"M17 20V4"}],["path",{d:"m3 8 4-4 4 4"}],["path",{d:"M7 4v16"}]],"sort-up":[["path",{d:"m5 12 7-7 7 7"}],["path",{d:"M12 19V5"}]],"sort-down":[["path",{d:"M12 5v14"}],["path",{d:"m19 12-7 7-7-7"}]],table:[["path",{d:"M12 3v18"}],["rect",{width:"18",height:"18",x:"3",y:"3",rx:"2"}],["path",{d:"M3 9h18"}],["path",{d:"M3 15h18"}]],undo:[["path",{d:"M9 14 4 9l5-5"}],["path",{d:"M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"}]],redo:[["path",{d:"m15 14 5-5-5-5"}],["path",{d:"M20 9H9.5A5.5 5.5 0 0 0 4 14.5A5.5 5.5 0 0 0 9.5 20H13"}]],maximize:[["path",{d:"M15 3h6v6"}],["path",{d:"m21 3-7 7"}],["path",{d:"m3 21 7-7"}],["path",{d:"M9 21H3v-6"}]],minimize:[["path",{d:"m14 10 7-7"}],["path",{d:"M20 10h-6V4"}],["path",{d:"m3 21 7-7"}],["path",{d:"M4 14h6v6"}]],swap:[["path",{d:"M8 3 4 7l4 4"}],["path",{d:"M4 7h16"}],["path",{d:"m16 21 4-4-4-4"}],["path",{d:"M20 17H4"}]],filter:[["path",{d:"M22 3H2l8 9.46V19l4 2v-8.54L22 3z"}]],keyboard:[["rect",{width:"20",height:"16",x:"2",y:"4",rx:"2"}],["path",{d:"M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10"}]],rows:[["rect",{width:"18",height:"18",x:"3",y:"3",rx:"2"}],["path",{d:"M3 12h18"}]],"sync-scroll":[["path",{d:"M9 17H7A5 5 0 0 1 7 7h2"}],["path",{d:"M15 7h2a5 5 0 1 1 0 10h-2"}],["line",{x1:"8",x2:"16",y1:"12",y2:"12"}]],alert:[["path",{d:"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"}],["path",{d:"M12 9v4"}],["path",{d:"M12 17h.01"}]],close:[["path",{d:"M18 6 6 18"}],["path",{d:"m6 6 12 12"}]],replay:[["path",{d:"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"}],["path",{d:"M3 3v5h5"}]],chart:[["path",{d:"M3 3v16a2 2 0 0 0 2 2h16"}],["path",{d:"m19 9-5 5-4-4-3 3"}]],follow:[["path",{d:"M12 17V3"}],["path",{d:"m6 11 6 6 6-6"}],["path",{d:"M19 21H5"}]],terminal:[["path",{d:"M12 19h8"}],["path",{d:"m4 17 6-6-6-6"}]],folder:[["path",{d:"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"}]],"folder-open":[["path",{d:"m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"}]],file:[w,k],"file-code":[w,k,["path",{d:"m10 13-2 2 2 2"}],["path",{d:"m14 17 2-2-2-2"}]],"file-text":[w,k,["path",{d:"M10 9H8"}],["path",{d:"M16 13H8"}],["path",{d:"M16 17H8"}]],"file-image":[w,k,["circle",{cx:"10",cy:"12",r:"2"}],["path",{d:"m20 17-1.296-1.296a2.41 2.41 0 0 0-3.408 0L9 22"}]],"file-data":[w,k,["path",{d:"M10 12a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1 1 1 0 0 1 1 1v1a1 1 0 0 0 1 1"}],["path",{d:"M14 18a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1"}]],lock:[["rect",{width:"18",height:"11",x:"3",y:"11",rx:"2",ry:"2"}],["path",{d:"M7 11V7a5 5 0 0 1 10 0v4"}]],"eye-off":[["path",{d:"M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"}],["path",{d:"M14.084 14.158a3 3 0 0 1-4.242-4.242"}],["path",{d:"M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"}],["path",{d:"m2 2 20 20"}]],"status-circle":[["circle",{cx:"12",cy:"12",r:"9"}]],"status-running":[["path",{d:"M21 12a9 9 0 1 1-6.22-8.56"}]],"status-skipped":[["circle",{cx:"12",cy:"12",r:"9"}],["path",{d:"m5.7 5.7 12.6 12.6"}]],"status-success":[["circle",{cx:"12",cy:"12",r:"9"}],["path",{d:"m8.5 12 2.5 2.5 4.5-5"}]],"status-failure":[["circle",{cx:"12",cy:"12",r:"9"}],["path",{d:"m15 9-6 6"}],["path",{d:"m9 9 6 6"}]],plus:[["path",{d:"M5 12h14"}],["path",{d:"M12 5v14"}]],trash:[["path",{d:"M3 6h18"}],["path",{d:"M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"}],["path",{d:"M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"}]],"dots-vertical":[["circle",{cx:"12",cy:"12",r:"1"}],["circle",{cx:"12",cy:"5",r:"1"}],["circle",{cx:"12",cy:"19",r:"1"}]],upload:[["path",{d:"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"}],["path",{d:"m17 8-5-5-5 5"}],["path",{d:"M12 3v12"}]],help:[["circle",{cx:"12",cy:"12",r:"10"}],["path",{d:"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"}],["path",{d:"M12 17h.01"}]],grip:[["circle",{cx:"9",cy:"5",r:"1"}],["circle",{cx:"9",cy:"12",r:"1"}],["circle",{cx:"9",cy:"19",r:"1"}],["circle",{cx:"15",cy:"5",r:"1"}],["circle",{cx:"15",cy:"12",r:"1"}],["circle",{cx:"15",cy:"19",r:"1"}]],calendar:[["rect",{width:"18",height:"18",x:"3",y:"4",rx:"2"}],["path",{d:"M16 2v4"}],["path",{d:"M8 2v4"}],["path",{d:"M3 10h18"}]],user:[["circle",{cx:"12",cy:"8",r:"5"}],["path",{d:"M20 21a8 8 0 0 0-16 0"}]],history:[["path",{d:"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"}],["path",{d:"M3 3v5h5"}],["path",{d:"M12 7v5l4 2"}]],"arrow-right":[["path",{d:"M5 12h14"}],["path",{d:"m12 5 7 7-7 7"}]],minus:[["path",{d:"M5 12h14"}]],refresh:[["path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"}],["path",{d:"M21 3v5h-5"}],["path",{d:"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"}],["path",{d:"M8 16H3v5"}]],key:[["path",{d:"M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z"}],["circle",{cx:"16.5",cy:"7.5",r:".5"}]],"shield-check":[["path",{d:"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"}],["path",{d:"m9 12 2 2 4-4"}]],"shield-alert":[["path",{d:"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"}],["path",{d:"M12 8v4"}],["path",{d:"M12 16h.01"}]],"arrow-up":[["path",{d:"m5 12 7-7 7 7"}],["path",{d:"M12 19V5"}]],star:[["path",{d:"M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"}]],fork:[["circle",{cx:"12",cy:"18",r:"3"}],["circle",{cx:"6",cy:"6",r:"3"}],["circle",{cx:"18",cy:"6",r:"3"}],["path",{d:"M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"}],["path",{d:"M12 12v3"}]],issue:[["circle",{cx:"12",cy:"12",r:"10"}],["circle",{cx:"12",cy:"12",r:"1"}]],tag:[["path",{d:"M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"}],["circle",{cx:"7.5",cy:"7.5",r:".5"}]],scale:[["path",{d:"m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"}],["path",{d:"m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"}],["path",{d:"M7 21h10"}],["path",{d:"M12 3v18"}],["path",{d:"M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"}]]};function Ee(e){return Object.hasOwn(mt,e)}function v(e){let t=document.createElementNS(ft,"svg");t.setAttribute("viewBox","0 0 24 24"),t.setAttribute("fill","none"),t.setAttribute("stroke","currentColor"),t.setAttribute("stroke-width","2.1"),t.setAttribute("stroke-linecap","round"),t.setAttribute("stroke-linejoin","round"),t.setAttribute("aria-hidden","true"),t.setAttribute("focusable","false"),t.setAttribute("class","icon");for(let[r,n]of mt[e]??[]){let s=document.createElementNS(ft,r);for(let[a,o]of Object.entries(n))s.setAttribute(a,o);t.append(s)}return t}var I=new WeakMap,M=null;function Dt(){return M||typeof IntersectionObserver>"u"||(M=new IntersectionObserver(e=>{for(let t of e)t.isIntersecting&&C(t.target)},{rootMargin:"600px 0px"})),M}function Te(e,t){I.set(e,t);let r=Dt();r?r.observe(e):C(e)}function C(e){let t=I.get(e);t&&(I.delete(e),M?.unobserve(e),t())}function gt(e){for(let t of Array.from(e.querySelectorAll(".chunk[data-pending]")))C(t)}function Se(e,t){for(let r of Array.from(e.querySelectorAll(".chunk[data-pending]"))){let n=Number(r.getAttribute("data-first")),s=Number(r.getAttribute("data-count"));if(t>=n&&t<n+s){C(r);break}}return e.querySelector(`.line[data-line="${t}"]`)}var Vt=5e3,T=200;function Ut(e){return e.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}function Pt(e,t,r=Vt){let n=[];if(!t)return{starts:n,capped:!1};let s=new RegExp(Ut(t),"gi"),a;for(;(a=s.exec(e))!==null;){if(n.length===r)return{starts:n,capped:!0};n.push(a.index),a[0].length===0&&(s.lastIndex+=1)}return{starts:n,capped:!1}}var bt=class{constructor(t,r={}){this.root=t,this.skip=r.skip??"",this.matches=[],this.current=-1}run(t){this.clear();let r=t.slice(0,T);if(!r)return{total:0,capped:!1};gt(this.root);let{nodes:n,starts:s,text:a}=this.collectText(),{starts:o,capped:i}=Pt(a,r),c=o.map(()=>[]);for(let h=o.length-1;h>=0;h-=1){let y=o[h],B=y+r.length,m=$t(s,B-1);for(;m>=0&&s[m]+(n[m].nodeValue??"").length>y;){let A=s[m],D=Math.max(y,A)-A,V=Math.min(B,A+(n[m].nodeValue??"").length)-A;V>D&&c[h].unshift(qt(n[m],D,V,h)),m-=1}}return this.matches=c,{total:c.length,capped:i}}collectText(){let t=this.skip,r=document.createTreeWalker(this.root,NodeFilter.SHOW_TEXT,{acceptNode(i){let c=i.parentElement;return t&&c&&c.closest(t)?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}}),n=[],s=[],a=[],o=0;for(let i=r.nextNode();i;i=r.nextNode()){let c=i.nodeValue??"";c&&(n.push(i),s.push(o),a.push(c),o+=c.length)}return{nodes:n,starts:s,text:a.join("")}}go(t){if(!this.matches.length)return null;let r=this.matches.length,n=(t%r+r)%r;for(let s of this.matches[this.current]??[])s.classList.remove("current");this.current=n;for(let s of this.matches[n])s.classList.add("current");return this.matches[n][0]??null}unsetCurrent(){for(let t of this.matches[this.current]??[])t.classList.remove("current");this.current=-1}clear(){let t=new Set;for(let r of this.matches)for(let n of r){let s=n.parentNode;s&&(n.replaceWith(...Array.from(n.childNodes)),t.add(s))}for(let r of t)r.normalize();this.matches=[],this.current=-1}};function $t(e,t){let r=0,n=e.length-1;for(;r<n;){let s=r+n+1>>1;e[s]<=t?r=s:n=s-1}return r}function qt(e,t,r,n){let s=e.splitText(t);s.splitText(r-t);let a=document.createElement("mark");return a.className="match",a.setAttribute("part","match"),a.dataset.match=String(n),s.replaceWith(a),a.appendChild(s),a}function Ne(e,t){let r=[];return{run(n){let s=!1;return r=e.map(a=>{let o=a.run(n);return s||=o.capped,o.total}),{total:r.reduce((a,o)=>a+o,0),capped:s}},go(n){let s=n;for(let a=0;a<e.length;a+=1){if(s<r[a]){for(let i of e)i!==e[a]&&i.unsetCurrent();let o=e[a].go(s);o&&t(o);return}s-=r[a]}},clear(){for(let n of e)n.clear()}}}function u(e){let t=l("button",{class:"btn",part:`button${e.part?` ${e.part}`:""}`,attrs:{type:"button","aria-label":e.label,title:e.label,"aria-pressed":e.pressed===void 0?null:String(e.pressed),"data-focus-key":e.key},on:{click:e.onClick}});return t.append(v(e.icon)),t}function vt(e,t,r){let n=e.querySelector("svg");n&&(n.replaceWith(v(r?"check":"alert")),e.classList.toggle("done",r),setTimeout(()=>{e.querySelector("svg")?.replaceWith(v(t)),e.classList.remove("done")},1500))}var S=class{constructor(t,r,n=""){this.t=t,this.handlers=r,this.total=0,this.capped=!1,this.index=-1;let s=it("search");this.input=l("input",{class:"search-input",part:"search-input",attrs:{id:s,type:"search",placeholder:t("searchPlaceholder"),"aria-label":t("search"),maxlength:T,autocomplete:"off",spellcheck:"false",enterkeyhint:"search","data-focus-key":"search-input"}}),this.input.value=n.slice(0,T),this.count=l("span",{class:"search-count",part:"search-count",attrs:{"aria-hidden":"true"}});let a=u({icon:"chevron-up",label:t("searchPrevious"),onClick:()=>this.step(-1),key:"search-prev"}),o=u({icon:"chevron-down",label:t("searchNext"),onClick:()=>this.step(1),key:"search-next"}),i=u({icon:"close",label:t("searchClose"),onClick:()=>r.onClose(),key:"search-close"});this.element=l("div",{class:"search",part:"search",attrs:{role:"search"}},this.input,this.count,a,o,i);let c=lt(()=>this.run(),150);this.input.addEventListener("input",c),this.input.addEventListener("keydown",h=>{h.key==="Enter"?(h.preventDefault(),c.cancel(),this.input.value!==this.lastQuery?this.run():this.step(h.shiftKey?-1:1)):h.key==="Escape"&&(h.preventDefault(),h.stopPropagation(),this.input.value?(this.input.value="",this.run()):r.onClose())}),this.lastQuery=void 0}run(){let t=this.input.value;this.lastQuery=t;let{total:r,capped:n}=this.handlers.run(t);this.total=r,this.capped=n,this.index=-1,r>0?this.step(1):this.updateCount(),this.handlers.onResult?.(t,r,n)}step(t){this.total&&(this.index=((this.index+t)%this.total+this.total)%this.total,this.handlers.go(this.index),this.updateCount())}updateCount(){if(!this.input.value)this.count.textContent="";else if(!this.total)this.count.textContent=this.t("searchNone");else{let t=this.capped?"searchCountCapped":"searchCount";this.count.textContent=this.t(t,{current:this.index+1,total:this.total})}}focus(){this.input.focus(),this.input.select()}};function Fe({tabs:e,selected:t,label:r,onSelect:n,panelId:s}){let a=l("div",{class:"tabs",part:"tabs",attrs:{role:"tablist","aria-label":r}}),o=e.map(i=>{let c=i.id===t;return l("button",{class:"tab",part:c?"tab tab-active":"tab",attrs:{type:"button",role:"tab","aria-selected":String(c),"aria-controls":s,tabindex:c?"0":"-1","data-tab":i.id,"data-focus-key":`tab-${i.id}`},on:{click:()=>n(i.id)}},i.icon?v(i.icon):null,i.label)});return a.append(...o),a.addEventListener("keydown",i=>{let c=o.findIndex(y=>y===i.target);if(c<0)return;let h=-1;i.key==="ArrowRight"?h=(c+1)%o.length:i.key==="ArrowLeft"?h=(c-1+o.length)%o.length:i.key==="Home"?h=0:i.key==="End"&&(h=o.length-1),!(h<0)&&(i.preventDefault(),n(e[h].id))}),a}function yt(e){return l("div",{class:"loader",part:"loading",attrs:{role:"status"}},Jt(),l("span",{class:"loader-label",text:e("loading")}))}var xt="http://www.w3.org/2000/svg";function Jt(){let e=document.createElementNS(xt,"svg");e.setAttribute("viewBox","0 0 120 120"),e.setAttribute("class","loader-mark"),e.setAttribute("aria-hidden","true"),e.setAttribute("focusable","false");let t=[["rect",{class:"loader-frame",x:"12",y:"16",width:"96",height:"88",rx:"18"}],["path",{class:"loader-frame",d:"M12 42 L108 42"}],["circle",{class:"loader-dot",cx:"29",cy:"29",r:"5"}],["path",{class:"loader-v",d:"M42 60 L60 86 L78 60",pathLength:"100"}]];for(let[r,n]of t){let s=document.createElementNS(xt,r);for(let[a,o]of Object.entries(n))s.setAttribute(a,o);e.append(s)}return e}function _t(e,t){return l("div",{class:"message",part:"error",attrs:{role:"alert"}},v("alert"),l("div",{},l("p",{class:"message-title",text:e}),t?l("p",{class:"message-detail",text:t}):null))}function Ie(e){return l("div",{class:"notice",part:"notice",attrs:{role:"note"}},v("alert"),l("span",{text:e}))}function wt(e){return l("div",{class:"empty",part:"empty",text:e("empty")})}var kt=`/*\r
 * Theme-independent tokens: typography, spacing, radius, motion.\r
 * Values: docs/DESIGN_SYSTEM.md \xA73, \xA74 and \xA77.\r
 * Each private \`--_\` variable reads the public \`--vt-\` variable first, so hosts can\r
 * override any token on the element or on an ancestor.\r
 */\r
:host {\r
  --_font-ui: var(\r
    --vt-font-ui,\r
    system-ui,\r
    -apple-system,\r
    'Segoe UI',\r
    'IBM Plex Sans',\r
    Roboto,\r
    sans-serif\r
  );\r
  --_font-mono: var(\r
    --vt-font-mono,\r
    'JetBrains Mono',\r
    ui-monospace,\r
    'Cascadia Code',\r
    'SF Mono',\r
    Menlo,\r
    Consolas,\r
    monospace\r
  );\r
  --_font-size: var(--vt-font-size, 14px);\r
  --_font-size-small: var(--vt-font-size-small, 12px);\r
  --_font-size-ui: var(--vt-font-size-ui, 13px);\r
  --_line-height: var(--vt-line-height, 1.6);\r
  --_space-1: var(--vt-space-1, 4px);\r
  --_space-2: var(--vt-space-2, 8px);\r
  --_space-3: var(--vt-space-3, 12px);\r
  --_space-4: var(--vt-space-4, 16px);\r
  --_space-5: var(--vt-space-5, 24px);\r
  --_space-6: var(--vt-space-6, 32px);\r
  --_space-7: var(--vt-space-7, 48px);\r
  --_space-8: var(--vt-space-8, 64px);\r
  --_radius-sm: var(--vt-radius-sm, 6px);\r
  --_radius: var(--vt-radius, 10px);\r
  --_radius-lg: var(--vt-radius-lg, 16px);\r
  --_radius-full: var(--vt-radius-full, 999px);\r
  --_header-height: var(--vt-header-height, 40px);\r
  --_tab-size: var(--vt-tab-size, 4);\r
  --_duration-fast: var(--vt-duration-fast, 120ms);\r
  --_duration: var(--vt-duration, 180ms);\r
  --_easing: var(--vt-easing, cubic-bezier(0.2, 0, 0, 1));\r
}\r
\r
@media (prefers-reduced-motion: reduce) {\r
  :host {\r
    --_duration-fast: 0ms;\r
    --_duration: 0ms;\r
  }\r
}\r
`;var Mt=`/*\r
 * Shared component frame: container, header, toolbar, tabs, search, states.\r
 * Anatomy: docs/DESIGN_SYSTEM.md \xA76. Colors come only from theme tokens.\r
 */\r
:host {\r
  display: block;\r
  min-width: 0;\r
  margin-block: var(--vt-margin, 0);\r
}\r
\r
:host([hidden]) {\r
  display: none;\r
}\r
\r
[hidden] {\r
  display: none !important;\r
}\r
\r
*,\r
*::before,\r
*::after {\r
  box-sizing: border-box;\r
}\r
\r
.vt {\r
  /* Code areas: interface colors by default, replaced by a syntax theme when one is set. */\r
  --_code-bg: var(--_surface-sunken);\r
  --_code-bg-solid: var(--_surface-sunken);\r
  --_code-fg: var(--_fg);\r
  --_code-gutter: color-mix(in srgb, var(--_fg-muted) 70%, transparent);\r
  display: flex;\r
  flex-direction: column;\r
  min-width: 0;\r
  overflow: hidden;\r
  color: var(--_fg);\r
  background: var(--_surface);\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-ui);\r
  line-height: 1.4;\r
  text-align: start;\r
  -webkit-text-size-adjust: 100%;\r
}\r
\r
/* Chrome always uses the UI font, even when the content inherits the page font. */\r
.header,\r
.search,\r
.notice,\r
.message,\r
.empty,\r
.more,\r
.toolbar,\r
.toc {\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-ui);\r
  line-height: 1.4;\r
}\r
\r
/* ---------- Header ---------- */\r
\r
.header {\r
  display: flex;\r
  flex-wrap: nowrap;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  min-height: var(--_header-height);\r
  padding: 0 var(--_space-2) 0 var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  background: var(--_surface);\r
}\r
\r
.dot {\r
  flex: none;\r
  width: 8px;\r
  height: 8px;\r
  border-radius: var(--_radius-full);\r
  background: var(--_accent);\r
}\r
\r
.title {\r
  flex: 1 1 auto;\r
  min-width: 0;\r
  overflow: hidden;\r
  color: var(--_fg);\r
  font-weight: 500;\r
  white-space: nowrap;\r
  text-overflow: ellipsis;\r
}\r
\r
.spacer {\r
  flex: 1 1 auto;\r
}\r
\r
.badge {\r
  flex: none;\r
  padding: 2px 6px;\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-sunken);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  font-weight: 600;\r
  line-height: 1.4;\r
  letter-spacing: 0.04em;\r
  text-transform: uppercase;\r
  white-space: nowrap;\r
}\r
\r
.vt {\r
  position: relative;\r
}\r
\r
.toolbar {\r
  display: flex;\r
  flex: none;\r
  align-items: center;\r
  gap: 2px;\r
}\r
\r
.toolbar.floating {\r
  position: absolute;\r
  top: var(--_space-2);\r
  right: var(--_space-2);\r
  z-index: 3;\r
  padding: 2px;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface);\r
  opacity: 0;\r
  transition: opacity var(--_duration-fast) var(--_easing);\r
}\r
\r
.vt:hover .toolbar.floating,\r
.toolbar.floating:focus-within {\r
  opacity: 1;\r
}\r
\r
@media (hover: none) {\r
  .toolbar.floating {\r
    opacity: 1;\r
  }\r
}\r
\r
/* ---------- Buttons ---------- */\r
\r
.btn {\r
  display: inline-grid;\r
  place-items: center;\r
  flex: none;\r
  width: 28px;\r
  height: 28px;\r
  padding: 0;\r
  border: 0;\r
  border-radius: var(--_radius-sm);\r
  background: transparent;\r
  color: var(--_fg-muted);\r
  font: inherit;\r
  cursor: pointer;\r
  transition:\r
    background-color var(--_duration-fast) var(--_easing),\r
    color var(--_duration-fast) var(--_easing);\r
}\r
\r
.btn:hover {\r
  background: var(--_accent-soft);\r
  color: var(--_fg);\r
}\r
\r
.btn[aria-pressed='true'] {\r
  background: var(--_accent-soft);\r
  color: var(--_accent-fg);\r
}\r
\r
.btn.done {\r
  color: var(--_success);\r
}\r
\r
.btn:disabled {\r
  opacity: 0.45;\r
  cursor: default;\r
  background: transparent;\r
}\r
\r
.icon {\r
  width: 16px;\r
  height: 16px;\r
  pointer-events: none;\r
}\r
\r
.text-btn {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: var(--_space-1);\r
  min-height: 28px;\r
  padding: 0 var(--_space-2);\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface);\r
  color: var(--_fg);\r
  font: inherit;\r
  font-weight: 500;\r
  cursor: pointer;\r
  transition: background-color var(--_duration-fast) var(--_easing);\r
}\r
\r
.text-btn:hover {\r
  background: var(--_accent-soft);\r
}\r
\r
.text-btn.done {\r
  border-color: var(--_success);\r
  color: var(--_success);\r
}\r
\r
.pathbar .text-btn {\r
  min-height: 24px;\r
  font-size: var(--_font-size-small);\r
}\r
\r
:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
:focus:not(:focus-visible) {\r
  outline: none;\r
}\r
\r
@media (pointer: coarse) {\r
  .btn {\r
    width: 44px;\r
    height: 44px;\r
  }\r
\r
  .text-btn,\r
  .tab {\r
    min-height: 44px;\r
  }\r
}\r
\r
/* ---------- Tabs (WAI-ARIA tabs pattern) ---------- */\r
\r
.tabs {\r
  display: flex;\r
  align-self: stretch;\r
  align-items: stretch;\r
  gap: var(--_space-1);\r
  min-width: 0;\r
  overflow-x: auto;\r
  scrollbar-width: none;\r
}\r
\r
.tab {\r
  position: relative;\r
  display: inline-flex;\r
  align-items: center;\r
  gap: 6px;\r
  padding: 0 var(--_space-2);\r
  border: 0;\r
  background: transparent;\r
  color: var(--_fg-muted);\r
  font: inherit;\r
  font-weight: 500;\r
  white-space: nowrap;\r
  cursor: pointer;\r
  transition: color var(--_duration-fast) var(--_easing);\r
}\r
\r
.tab::after {\r
  content: '';\r
  position: absolute;\r
  right: var(--_space-2);\r
  bottom: -1px;\r
  left: var(--_space-2);\r
  height: 2px;\r
  border-radius: 2px;\r
  background: transparent;\r
  transition: background-color var(--_duration) var(--_easing);\r
}\r
\r
.tab:hover {\r
  color: var(--_fg);\r
}\r
\r
.tab[aria-selected='true'] {\r
  color: var(--_fg);\r
}\r
\r
.tab[aria-selected='true']::after {\r
  background: var(--_accent);\r
}\r
\r
.tab:focus-visible {\r
  outline-offset: -2px;\r
}\r
\r
.tab .icon {\r
  width: 14px;\r
  height: 14px;\r
}\r
\r
/* ---------- Search ---------- */\r
\r
.search {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-1);\r
  padding: var(--_space-2) var(--_space-2) var(--_space-2) var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  background: var(--_surface);\r
}\r
\r
.search-input {\r
  flex: 1 1 auto;\r
  min-width: 0;\r
  height: 28px;\r
  padding: 0 var(--_space-2);\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-sunken);\r
  color: var(--_fg);\r
  font: inherit;\r
}\r
\r
.search-input::placeholder {\r
  color: var(--_fg-muted);\r
  opacity: 1;\r
}\r
\r
.search-input:focus-visible {\r
  outline-offset: 0;\r
  border-color: var(--_accent);\r
}\r
\r
.search-count {\r
  flex: none;\r
  min-width: 5ch;\r
  color: var(--_fg-muted);\r
  font-variant-numeric: tabular-nums;\r
  text-align: end;\r
  white-space: nowrap;\r
}\r
\r
mark.match {\r
  border-radius: 2px;\r
  background: var(--_highlight);\r
  color: inherit;\r
}\r
\r
mark.match.current {\r
  background: var(--_highlight-current);\r
  box-shadow: 0 0 0 1px var(--_warning);\r
}\r
\r
/* ---------- Body ---------- */\r
\r
.body {\r
  position: relative;\r
  min-width: 0;\r
  max-height: var(--_max-height, none);\r
  overflow: auto;\r
  background: var(--_code-bg);\r
  /*\r
   * Without a height limit the page must keep scrolling: a body that only scrolls\r
   * sideways (long lines) would otherwise swallow vertical wheel and touch scrolling.\r
   */\r
  overscroll-behavior: auto;\r
  scrollbar-width: thin;\r
  scrollbar-color: var(--_border-strong) transparent;\r
}\r
\r
:host([max-height]) .body,\r
.vt[data-fullscreen] .body {\r
  overscroll-behavior: contain;\r
}\r
\r
.body:focus-visible {\r
  outline-offset: -2px;\r
}\r
\r
/* ---------- States ---------- */\r
\r
.notice {\r
  display: flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  padding: var(--_space-2) var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  background: var(--_surface);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.notice .icon {\r
  flex: none;\r
  width: 14px;\r
  height: 14px;\r
  color: var(--_warning);\r
}\r
\r
.message {\r
  display: flex;\r
  align-items: flex-start;\r
  gap: var(--_space-2);\r
  padding: var(--_space-4);\r
  background: var(--_surface);\r
  overflow-wrap: anywhere;\r
}\r
\r
.message .icon {\r
  flex: none;\r
  margin-top: 1px;\r
  color: var(--_danger);\r
}\r
\r
.message-title {\r
  margin: 0;\r
  color: var(--_danger);\r
  font-weight: 600;\r
}\r
\r
.message-detail {\r
  margin: var(--_space-1) 0 0;\r
  color: var(--_fg-muted);\r
}\r
\r
.empty {\r
  padding: var(--_space-5) var(--_space-4);\r
  color: var(--_fg-muted);\r
  text-align: center;\r
}\r
\r
.loader {\r
  display: flex;\r
  flex-direction: column;\r
  align-items: center;\r
  justify-content: center;\r
  gap: var(--_space-3);\r
  min-height: 140px;\r
  padding: var(--_space-5);\r
  color: var(--_fg-muted);\r
  /* Fast loads show nothing: the loader only appears after a short delay. */\r
  opacity: 0;\r
  animation: vt-loader-in var(--_duration) var(--_easing) 300ms forwards;\r
}\r
\r
.loader-mark {\r
  width: 44px;\r
  height: 44px;\r
  overflow: visible;\r
}\r
\r
.loader-frame {\r
  fill: none;\r
  stroke: currentColor;\r
  stroke-width: 9;\r
}\r
\r
.loader-dot {\r
  fill: var(--_accent);\r
  transform-origin: 29px 29px;\r
  animation: vt-loader-dot 1.4s var(--_easing) infinite;\r
}\r
\r
.loader-v {\r
  fill: none;\r
  stroke: var(--_accent);\r
  stroke-width: 11;\r
  stroke-linecap: round;\r
  stroke-linejoin: round;\r
  stroke-dasharray: 100;\r
  animation: vt-loader-v 1.4s var(--_easing) infinite;\r
}\r
\r
.loader-label {\r
  font-size: var(--_font-size-small);\r
}\r
\r
@keyframes vt-loader-in {\r
  to {\r
    opacity: 1;\r
  }\r
}\r
\r
@keyframes vt-loader-v {\r
  0% {\r
    stroke-dashoffset: 100;\r
  }\r
  45%,\r
  70% {\r
    stroke-dashoffset: 0;\r
  }\r
  100% {\r
    stroke-dashoffset: -100;\r
  }\r
}\r
\r
@keyframes vt-loader-dot {\r
  0%,\r
  100% {\r
    opacity: 0.35;\r
    transform: scale(0.8);\r
  }\r
  50% {\r
    opacity: 1;\r
    transform: scale(1);\r
  }\r
}\r
\r
@media (prefers-reduced-motion: reduce) {\r
  .loader {\r
    animation-duration: 0ms;\r
  }\r
\r
  .loader-v,\r
  .loader-dot {\r
    animation: none;\r
    stroke-dashoffset: 0;\r
    opacity: 1;\r
  }\r
}\r
\r
.sr-only {\r
  position: absolute;\r
  width: 1px;\r
  height: 1px;\r
  margin: -1px;\r
  padding: 0;\r
  overflow: hidden;\r
  clip: rect(0 0 0 0);\r
  white-space: nowrap;\r
  border: 0;\r
}\r
\r
/* ---------- Full screen ---------- */\r
\r
:host(:fullscreen) {\r
  display: block;\r
  width: 100%;\r
  height: 100%;\r
}\r
\r
.vt[data-fullscreen] {\r
  height: 100%;\r
  border-radius: 0;\r
  border-width: 0;\r
}\r
\r
/* Window mode: used where the Fullscreen API is not available. */\r
.vt[data-fullscreen='window'] {\r
  position: fixed;\r
  inset: 0;\r
  z-index: 2147483000;\r
  height: auto;\r
}\r
\r
.vt[data-fullscreen] > .panel,\r
.vt[data-fullscreen] > .body {\r
  display: flex;\r
  flex: 1 1 auto;\r
  flex-direction: column;\r
  min-height: 0;\r
}\r
\r
.vt[data-fullscreen] .body {\r
  flex: 1 1 auto;\r
  max-height: none;\r
}\r
\r
.vt[data-fullscreen] .panel.split {\r
  display: grid;\r
  grid-template-rows: minmax(0, 1fr);\r
}\r
\r
.vt[data-fullscreen] .panel.split:is([data-preview='top'], [data-preview='bottom']) {\r
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);\r
}\r
\r
.vt[data-fullscreen] .panel.split > .body {\r
  height: auto;\r
  min-height: 0;\r
}\r
`;var At=new Map;function j(e){let t=At.get(e);return t||(t=new CSSStyleSheet,t.replaceSync(e),At.set(e,t)),t}var Wt=Object.freeze(["variant","theme","src","allow-remote","max-height","copy","search","download","header","dot","title","label","lang-ui","mode","edit-toggle","placeholder","syntax-theme","syntax-theme-dark","badge","history","fullscreen","status","json","json-src","json-path"]);function Xt(e){return e instanceof HTMLTemplateElement?e.content.textContent??"":e.textContent??""}var Et=class extends HTMLElement{static type="base";static componentAttributes=[];static presets={simple:{},full:{}};static allowEmpty=!1;static keepCarriageReturns=!1;static dataAttributes=[];static fromData(t){return typeof t=="string"?t:F(t)}static upgradeProperties=["content"];static styles=[];static get observedAttributes(){return[...Wt,...this.componentAttributes]}constructor(){super(),this.root=this.attachShadow({mode:"open"}),this.frame=l("div",{class:"vt",part:"container"}),this.syntaxTheme=null,this.updateSheets(null),this.live=l("div",{class:"sr-only",attrs:{"aria-live":"polite","aria-atomic":"true"}}),this.root.append(this.frame,this.live),this._content=void 0,this._data=void 0,this._fromJson=!1,this._dataAttributes=new Set,this.text=null,this.error=null,this.loading=!1,this.searchOpen=!1,this.searchQuery="",this.searchBar=null,this.t=L("en"),this._loadToken=0,this._abort=null,this._renderQueued=!1,this._readyPending=!1,this._cleanups=[],this._observer=null,this._connected=!1,this.modeState=null,this.editHistory=null,this._historyCleanup=null,this._escapeFullscreen=null}get content(){return this.text??""}set content(t){let r=t==null?void 0:String(t);r!==void 0&&r===this._content&&r===this.text||(this._content=r,this._fromJson=!1,this._connected&&this.reload())}get data(){return this._data}set data(t){this._fromJson=!1,this.applyData(t)}applyData(t){this._data=t;let r=this.constructor,n;try{n=r.fromData(t)}catch(o){this._content="",this.setError(new d("jsonUnusable",{},o));return}let{content:s,attributes:a={}}=typeof n=="string"?{content:n}:n;this.applyDataAttributes(a),this._content=s,this._connected&&this.setText(s)}applyDataAttributes(t){let r=this.constructor.dataAttributes,n=this._dataAttributes;this._dataAttributes=new Set;for(let[s,a]of Object.entries(t)){if(!r.includes(s)||a===null||a===void 0||this.hasAttribute(s)&&!n.has(s))continue;let o=a===!0?"":a===!1?"false":String(a).slice(0,2e3);this.getAttribute(s)!==o&&this.setAttribute(s,o),this._dataAttributes.add(s)}for(let s of n)this._dataAttributes.has(s)||this.removeAttribute(s)}loadJson(){let t=this.getAttribute("json-src")?.trim(),r=this.getAttribute("json"),n=this.querySelector(":scope > script[data-json], :scope > template[data-json]");if(!t&&r===null&&!n)return this._fromJson&&(this._fromJson=!1,this._content=void 0),!1;let s=++this._loadToken;if(this._abort?.abort(),this._abort=null,!t)return this.useJson(r??Xt(n)),!0;let a=g();this.loading=!0,this.error=null,this.requestRender();let o=new AbortController;return this._abort=o,R(t,{allowRemote:b(this.getAttribute("allow-remote"))===!0,maxSize:a.maxSize,timeout:a.fetchTimeout,signal:o.signal}).then(i=>s===this._loadToken&&this.useJson(i),i=>s===this._loadToken&&!H(i)&&this.setError(i)),!0}useJson(t){this.loading=!1;let r;try{_(t,g().maxSize),r=JSON.parse(t)}catch(s){this.setError(s instanceof d?s:new d("jsonInvalid",{message:s instanceof Error?s.message:""},s));return}let n=this.getAttribute("json-path")?.trim();if(n){let s=pt(r,n);if(!s.ok){this.setError(new d("jsonPathMissing",{path:n.slice(0,100)}));return}r=s.value}this._fromJson=!0,this.applyData(r)}upgradeProperty(t){if(Object.prototype.hasOwnProperty.call(this,t)){let r=this[t];delete this[t],this[t]=r}}connectedCallback(){for(let r of new Set([...this.constructor.upgradeProperties,"data"]))this.upgradeProperty(r);this._cleanups.push(q(r=>r.has("maxSize")?this.reload():this.requestRender()),X(()=>this.applyTheme()),J(()=>this.requestRender())),this._observer=new MutationObserver(()=>{(this._content===void 0||this._fromJson)&&!this.hasAttribute("src")&&this.reload()}),this._observer.observe(this,{childList:!0,characterData:!0,subtree:!0});let t=()=>{document.fullscreenElement===this?this.setFullscreen("native"):this.frame.dataset.fullscreen==="native"&&this.setFullscreen(null)};document.addEventListener("fullscreenchange",t),this._cleanups.push(()=>document.removeEventListener("fullscreenchange",t)),this._connected=!0,this.reload()}disconnectedCallback(){this._connected=!1;for(let t of this._cleanups.splice(0))t();this._observer?.disconnect(),this._observer=null,this._abort?.abort(),this._abort=null}attributeChangedCallback(t,r,n){r===n||!this.isConnected||(t==="mode"&&(this.modeState=null),["src","allow-remote","json","json-src","json-path"].includes(t)?this.reload():t==="theme"?this.applyTheme():this.requestRender())}reload(){if((this._content===void 0||this._fromJson)&&this.loadJson())return;let t=++this._loadToken;this._abort?.abort(),this._abort=null;let r=g(),n=this.getAttribute("src");if(this._content!==void 0)this.setText(this._content);else if(n!==null&&n.trim()!==""){this.loading=!0,this.error=null,this.requestRender();let s=new AbortController;this._abort=s,R(n,{allowRemote:b(this.getAttribute("allow-remote"))===!0,maxSize:r.maxSize,timeout:r.fetchTimeout,signal:s.signal}).then(a=>t===this._loadToken&&this.setText(a),a=>t===this._loadToken&&!H(a)&&this.setError(a))}else this.setText(this.readInline()??"")}setText(t){this.loading=!1,this.editHistory=null;try{_(t,g().maxSize)}catch(n){this.setError(n);return}let r=this.constructor;this.text=t.replace(r.keepCarriageReturns?/\r\n/g:/\r\n?/g,`
`),this.error=null,this.contentChanged(),this._readyPending=!0,this.requestRender()}setError(t){this.loading=!1,this._readyPending=!1,this.error=t,this.text=null,this.contentChanged(),this.requestRender();let{title:r,detail:n}=this.describeError(t);f(this,p.ERROR,{message:n||r,cause:t})}describeError(t){let r=this.t;if(t instanceof d){let n={...t.params};for(let s of["size","limit"])typeof n[s]=="number"&&(n[s]=Q(Number(n[s]),this.locale));return{title:r("errorTitle"),detail:r(t.code,n)}}return{title:r("errorTitle"),detail:t instanceof Error?t.message:String(t)}}get editing(){return(this.modeState??N(this.getAttribute("mode"),["view","edit"],"view"))==="edit"}edited(t){this.text=t,this._content=t,this.contentEdited(t),f(this,p.INPUT,{value:t})}contentEdited(t){}historyButtons(t){if(this.editHistory=t.history,b(this.getAttribute("history"))===!1)return[];let r=u({icon:"undo",label:this.t("undo"),key:"undo",part:"undo-button",onClick:()=>t.undo()}),n=u({icon:"redo",label:this.t("redo"),key:"redo",part:"redo-button",onClick:()=>t.redo()}),s=()=>{r.disabled=!t.history.canUndo,n.disabled=!t.history.canRedo};return s(),this._historyCleanup?.(),this._historyCleanup=t.history.subscribe(s),[r,n]}fullscreenButton(){if(!this.feature("fullscreen"))return null;let t=!!this.frame.dataset.fullscreen;return u({icon:t?"minimize":"maximize",label:this.t(t?"exitFullscreen":"fullscreen"),key:"fullscreen",part:"fullscreen-button",pressed:t,onClick:()=>this.toggleFullscreen()})}async toggleFullscreen(){let t=this.frame.dataset.fullscreen;if(t==="native"){await document.exitFullscreen?.().catch(()=>{});return}if(t==="window"){this.setFullscreen(null);return}if(document.fullscreenEnabled&&this.requestFullscreen)try{await this.requestFullscreen({navigationUI:"hide"});return}catch{}this.setFullscreen("window")}setFullscreen(t){t?this.frame.dataset.fullscreen=t:delete this.frame.dataset.fullscreen,t==="window"?(this._escapeFullscreen=r=>{r.key==="Escape"&&!r.defaultPrevented&&this.setFullscreen(null)},this.frame.addEventListener("keydown",this._escapeFullscreen)):this._escapeFullscreen&&(this.frame.removeEventListener("keydown",this._escapeFullscreen),this._escapeFullscreen=null),this.render(),this.root.querySelector('[data-focus-key="fullscreen"]')?.focus(),f(this,p.FULLSCREEN_CHANGE,{fullscreen:!!t})}editToggleButton(){return this.feature("edit-toggle")?u({icon:this.editing?"eye":"pencil",label:this.t(this.editing?"stopEditing":"edit"),key:"edit-toggle",part:"edit-button",pressed:this.editing,onClick:()=>{this.modeState=this.editing?"view":"edit",this.render(),f(this,p.MODE_CHANGE,{mode:this.modeState}),this.modeState==="edit"&&this.root.querySelector(".editor-input")?.focus()}}):null}readInline(){return ht(this)}contentChanged(){}get variant(){return N(this.getAttribute("variant"),["simple","full"],"simple")}feature(t){let r=b(this.getAttribute(t));return r!==null?r:this.constructor.presets[this.variant][t]??!1}get locale(){let t=this.getAttribute("lang-ui")?.trim();return t&&/^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/.test(t)?t:g().lang}get heading(){return nt(this.getAttribute("label")??this.getAttribute("title"))}requestRender(){this._renderQueued||(this._renderQueued=!0,queueMicrotask(()=>{this._renderQueued=!1,this.isConnected&&this.render()}))}applyTheme(){let t=Y(this.getAttribute("theme"));this.frame.dataset.theme=t,this.applySyntaxTheme(W(t)?.colorScheme==="dark")}applySyntaxTheme(t){let r=g(),n=t&&this.getAttribute("syntax-theme-dark")||this.getAttribute("syntax-theme")||t&&r.syntaxThemeDark||r.syntaxTheme,s=K(n);if(this.syntaxTheme=s,!s){this.updateSheets(null);return}let a=Z(s);if(a){this.updateSheets(a);return}tt(s).then(o=>{o&&this.syntaxTheme===s&&this.updateSheets(o)})}updateSheets(t){let n=this.constructor.styles.map(j),s=[j(kt),G,j(Mt),...n];this.frame.toggleAttribute("data-syntax-theme",!!t),this.root.adoptedStyleSheets=t?[...s.filter(a=>a!==j(et)),t]:s}render(){let t=this.activeFocusKey(),r=this.root.activeElement,n=r instanceof HTMLTextAreaElement||r instanceof HTMLInputElement?[r.selectionStart,r.selectionEnd]:null;this.t=L(this.locale),this.applyTheme();let s=rt(this.getAttribute("max-height"));if(s?this.frame.style.setProperty("--_max-height",s):this.frame.style.removeProperty("--_max-height"),this.searchBar=null,this.frame.replaceChildren(),this.loading){this.frame.append(...this.chrome(null),l("div",{class:"body",part:"body"},yt(this.t))),this.frame.setAttribute("aria-busy","true");return}if(this.frame.removeAttribute("aria-busy"),this.error){let{title:o,detail:i}=this.describeError(this.error);this.frame.append(...this.chrome(null),_t(o,i));return}if(!this.text&&!this.editing&&!this.constructor.allowEmpty)this.frame.append(...this.chrome(null),wt(this.t));else{this.renderContent(this.frame);let o=this.searchBar;this.searchOpen&&this.searchQuery&&o?.run()}this.restoreFocus(t);let a=this.root.activeElement;if(n&&(a instanceof HTMLTextAreaElement||a instanceof HTMLInputElement)&&n[0]!==null)try{a.setSelectionRange(n[0],n[1])}catch{}this._readyPending&&(this._readyPending=!1,f(this,p.READY,{type:this.constructor.type}))}renderContent(t){throw new Error("renderContent() must be implemented.")}chrome(t){let r=(t?.actions??[]).filter(o=>o!==null),n=r.length?l("div",{class:"toolbar",part:"toolbar",attrs:{role:"toolbar","aria-label":this.t("actions")}},...r):null;if(!this.feature("header"))return n?.classList.add("floating"),[n,t?.tabs??null,this.searchBar?.element??null].filter(o=>o!==null);let s=this.heading,a=l("div",{class:"header",part:"header"},this.feature("dot")?l("span",{class:"dot",part:"status-dot",attrs:{"aria-hidden":"true"}}):null,s?l("span",{class:"title",part:"title",text:s,attrs:{title:s}}):null,t?.tabs??null,s?null:l("span",{class:"spacer"}),t?.badge&&b(this.getAttribute("badge"))!==!1?l("span",{class:"badge",part:"badge",text:t.badge}):null);return n&&a.append(n),this.searchBar?[a,this.searchBar.element]:[a]}copyButton(t,r=this.t("copy"),n="copy"){let s=u({icon:"copy",label:r,key:n,part:"copy-button",onClick:async()=>{let a=t(),o=await z(a,this.root);vt(s,"copy",o),this.announce(this.t(o?"copied":"copyFailed")),o&&f(this,p.COPY,{text:a})}});return s}copyTextButton(t,r,n){let s=l("button",{class:"text-btn",part:"copy-button",text:r,attrs:{type:"button","data-focus-key":n},on:{click:async()=>{let a=t(),o=await z(a,this.root);s.textContent=this.t(o?"copied":"copyFailed"),s.classList.toggle("done",o),setTimeout(()=>{s.textContent=r,s.classList.remove("done")},1500),this.announce(this.t(o?"copied":"copyFailed")),o&&f(this,p.COPY,{text:a})}}});return s}downloadName(t){let r=this.getAttribute("download"),n=r&&b(r)!==!1&&!/^(?:true|on|yes)$/i.test(r.trim())?r:null,s=/\.[a-z0-9]{1,10}$/i.test(this.heading)?this.heading:null;return st(n??s,t)}downloadButton(t,r,n){return u({icon:"download",label:this.t("download"),key:"download",part:"download-button",onClick:()=>at(t(),r,n)})}searchButton(t){return this.feature("search")?(this.searchOpen&&(this.searchBar=new S(this.t,{run:r=>(this.searchQuery=r,t.run(r)),go:r=>t.go(r),onResult:(r,n,s)=>{r&&this.announce(n?this.t("searchResults",{total:s?`${n}+`:n}):this.t("searchNone")),f(this,p.SEARCH,{query:r,matches:n})},onClose:()=>{t.clear(),this.searchOpen=!1,this.searchQuery="",this.render(),this.root.querySelector('[data-focus-key="search"]')?.focus()}},this.searchQuery)),u({icon:"search",label:this.t("search"),key:"search",part:"search-button",pressed:this.searchOpen,onClick:()=>{this.searchOpen=!this.searchOpen,this.searchOpen||(this.searchQuery=""),this.render(),this.searchOpen&&this.searchBar?.focus()}})):null}announce(t){this.live.textContent="",setTimeout(()=>{this.live.textContent=t},50)}activeFocusKey(){let t=this.root.activeElement;return t instanceof HTMLElement?t.dataset.focusKey??null:null}restoreFocus(t){if(!t)return;let r=this.root.querySelector(`[data-focus-key="${CSS.escape(t)}"]`);r instanceof HTMLElement&&r.focus({preventScroll:!0})}};export{Kt as a,et as b,b as c,ee as d,N as e,re as f,ne as g,se as h,rt as i,nt as j,st as k,kt as l,z as m,at as n,l as o,jt as p,it as q,E as r,O as s,ct as t,le as u,d as v,Ot as w,_ as x,R as y,H as z,Bt as A,x as B,ut as C,fe as D,me as E,ge as F,be as G,xe as H,ve as I,ye as J,F as K,ke as L,Me as M,Ee as N,v as O,Te as P,C as Q,Se as R,Vt as S,T,bt as U,Ne as V,u as W,Fe as X,yt as Y,_t as Z,Ie as _,wt as $,j as aa,Et as ba};
