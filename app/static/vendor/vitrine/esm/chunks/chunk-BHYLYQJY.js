/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{a as N}from"./chunk-INCBER5S.js";import{a as S}from"./chunk-NPDHR5SA.js";import{a as x}from"./chunk-BNQD3D4I.js";import{B as E,C,D as O,E as A,F as v,I,W as d,b,d as k,e as f,o as s,q as _,t as y}from"./chunk-7PAHM2BV.js";import{k as u,l as m,m as L}from"./chunk-TUK22DTT.js";var z=`/*\r
 * Gallery: a grid of thumbnails and a viewer. The viewer is a modal dialog, so the browser keeps\r
 * the focus inside it and Escape closes it.\r
 */\r
.gallery-grid {\r
  display: grid;\r
  grid-template-columns: repeat(var(--_columns, auto-fill), minmax(min(100%, 160px), 1fr));\r
  gap: var(--_space-3);\r
  margin: 0;\r
  padding: 0;\r
  list-style: none;\r
}\r
\r
.gallery-item {\r
  display: grid;\r
  gap: var(--_space-1);\r
  align-content: start;\r
  min-width: 0;\r
}\r
\r
.gallery-open {\r
  display: block;\r
  width: 100%;\r
  padding: 0;\r
  overflow: hidden;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  background: var(--_surface-sunken);\r
  cursor: zoom-in;\r
}\r
\r
.gallery-open.static {\r
  cursor: default;\r
}\r
\r
.gallery-open:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.gallery-open img {\r
  display: block;\r
  width: 100%;\r
  height: auto;\r
  object-fit: cover;\r
}\r
\r
.aspect-square img {\r
  aspect-ratio: 1;\r
}\r
\r
.aspect-photo img {\r
  aspect-ratio: 4 / 3;\r
}\r
\r
.aspect-wide img {\r
  aspect-ratio: 16 / 9;\r
}\r
\r
.gallery-open img.failed {\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.4 var(--_font-ui);\r
}\r
\r
.gallery-caption {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-small) / 1.45 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
/* ---------- Viewer ---------- */\r
\r
.gallery-viewer {\r
  width: min(96vw, 1200px);\r
  max-width: none;\r
  height: min(94vh, 900px);\r
  max-height: none;\r
  padding: 0;\r
  overflow: hidden;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius);\r
  background: var(--_surface);\r
  color: var(--_fg);\r
}\r
\r
.gallery-viewer[open] {\r
  display: flex;\r
  flex-direction: column;\r
}\r
\r
.gallery-viewer::backdrop {\r
  background: rgb(0 0 0 / 70%);\r
}\r
\r
.gallery-stage {\r
  display: grid;\r
  flex: 1;\r
  place-items: center;\r
  min-height: 0;\r
  padding: var(--_space-2);\r
  background: var(--_surface-sunken);\r
}\r
\r
.gallery-stage img {\r
  width: 100%;\r
  height: 100%;\r
  object-fit: contain;\r
}\r
\r
.gallery-stage img.failed {\r
  color: var(--_fg-muted);\r
  font: 400 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
}\r
\r
.gallery-bar {\r
  display: flex;\r
  flex: none;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  padding: var(--_space-2) var(--_space-3);\r
  border-top: 1px solid var(--_border);\r
}\r
\r
.gallery-position {\r
  flex: none;\r
  color: var(--_fg-muted);\r
  font: 500 var(--_font-size-small) / 1.3 var(--_font-ui);\r
}\r
\r
.gallery-text {\r
  flex: 1;\r
  min-width: 0;\r
  font: 400 var(--_font-size-ui) / 1.4 var(--_font-ui);\r
  overflow-wrap: anywhere;\r
}\r
\r
.gallery-text p {\r
  margin: 0;\r
}\r
\r
.gallery-text a {\r
  color: var(--_accent-fg);\r
}\r
`;var P=Object.freeze({galleryOpen:"Open image {n} of {total}: {name}",galleryImage:"Image {n}",galleryViewer:"Image viewer",galleryPrevious:"Previous image",galleryNext:"Next image",galleryClose:"Close",galleryPosition:"{n} of {total}",galleryEmpty:"No images to show.",galleryFailed:"This image could not be loaded.",galleryLink:"More about this image"}),V=Object.freeze({galleryOpen:"Ouvrir l'image {n} sur {total} : {name}",galleryImage:"Image {n}",galleryViewer:"Visionneuse d'images",galleryPrevious:"Image pr\xE9c\xE9dente",galleryNext:"Image suivante",galleryClose:"Fermer",galleryPosition:"{n} sur {total}",galleryEmpty:"Aucune image \xE0 afficher.",galleryFailed:"Cette image n'a pas pu \xEAtre charg\xE9e.",galleryLink:"En savoir plus sur cette image"});L({en:P,fr:V});var G=["square","wide","photo","natural"],q=["allow","same-origin"];function T(h,t="allow"){let r=h;try{let e=JSON.parse(h),l=Array.isArray(e)?e:E(e)?e.images??e.items:null;Array.isArray(l)&&(r=JSON.stringify(l.map(o=>typeof o=="string"?{src:o}:o)))}catch{}let a=I(r,["images","items","photos"]);if(!a.ok)return a;let i=[];for(let e of a.items){let l=v(e.src??e.url??e.image);if(!l||t==="same-origin"&&!y(l))continue;let o=v(e.thumb??e.thumbnail),n=Number(e.width),c=Number(e.height);i.push({src:l,thumb:o&&(t!=="same-origin"||y(o))?o:l,alt:O(e,["alt","title"],500),caption:C(e.caption??e.description,1e3),href:A(e.href??e.link),width:n>0&&n<1e5?n:null,height:c>0&&c<1e5?c:null})}return{ok:!0,images:i}}var j=class extends S{static type="gallery";static componentAttributes=Object.freeze(["columns","aspect","viewer","captions","images"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,download:!0,fullscreen:!0}};static styles=[b,x,N,z];constructor(){super(),this.panelId=_("panel"),this.viewer=null,this.current=null}get policy(){return f(this.getAttribute("images"),q,"allow")}get images(){let t=T(this.text??"",this.policy);return t.ok?t.images:[]}contentChanged(){this.current=null}renderContent(t){let r=T(this.text??"",this.policy),a=s("div",{class:"body data-body gallery-body",part:"body"});r.ok?r.images.length?a.append(this.grid(r.images)):a.append(s("p",{class:"data-none",text:this.t("galleryEmpty")})):a.append(this.dataNotice(r)),this.frameWith(t,a,this.panelId,{file:"gallery.json"}),r.ok&&this.current!==null&&this.current<r.images.length&&this.openViewer(t,r.images)}grid(t){let r=k(this.getAttribute("columns"),{min:1,max:12,fallback:0}),a=f(this.getAttribute("aspect"),G,"photo"),i=s("ul",{class:`gallery-grid aspect-${a}`,part:"grid"},...t.map((e,l)=>this.item(e,l,t.length)));return r&&i.style.setProperty("--_columns",String(r)),i}item(t,r,a){let i=this.t,e=this.picture(t.thumb,t,"thumbnail"),l=t.alt||t.caption||i("galleryImage",{n:r+1}),o=this.flag("viewer")?s("button",{class:"gallery-open",attrs:{type:"button","aria-label":i("galleryOpen",{n:r+1,total:a,name:l}),"data-focus-key":`image-${r}`},on:{click:()=>this.show(r)}},e):s("div",{class:"gallery-open static"},e);return s("li",{class:"gallery-item",part:"item"},o,t.caption&&this.flag("captions")?s("p",{class:"gallery-caption",part:"caption",text:t.caption}):null)}picture(t,r,a){let i=s("img",{part:a,attrs:{src:t,alt:r.alt,loading:"lazy",decoding:"async",referrerpolicy:"no-referrer",width:r.width,height:r.height},on:{error:()=>{i.classList.add("failed"),i.setAttribute("alt",this.t("galleryFailed"))}}});return i}show(t){let r=this.images;if(!r[t])return;let a=this.current!==null;this.current=t,this.render();let i=r[t];m(this,u.SELECT,{index:t,src:i.src,alt:i.alt}),a||m(this,u.TOGGLE,{expanded:!0})}openViewer(t,r){let a=this.t,i=this.current,e=r[i],l=r.length,o=g=>this.show((i+g+l)%l),n=s("dialog",{class:"gallery-viewer",part:"viewer",attrs:{"aria-label":a("galleryViewer")},on:{keydown:g=>{let{key:p}=g;p==="ArrowLeft"?o(-1):p==="ArrowRight"?o(1):p==="Home"?this.show(0):p==="End"&&this.show(l-1)},click:g=>{g.target===n&&n.close()},close:()=>n===this.viewer&&this.closeViewer(i)}},s("div",{class:"gallery-stage"},this.picture(e.src,{...e,width:null,height:null},"image")),s("div",{class:"gallery-bar"},s("span",{class:"gallery-position",text:a("galleryPosition",{n:i+1,total:l}),attrs:{"aria-live":"polite"}}),s("div",{class:"gallery-text"},e.caption||e.alt?s("p",{text:e.caption||e.alt}):null,e.href?s("a",{text:a("galleryLink"),attrs:{href:e.href,rel:"noopener noreferrer"}}):null),l>1?d({icon:"chevron-left",label:a("galleryPrevious"),key:"viewer-previous",onClick:()=>o(-1)}):null,l>1?d({icon:"chevron-right",label:a("galleryNext"),key:"viewer-next",onClick:()=>o(1)}):null,d({icon:"close",label:a("galleryClose"),key:"viewer-close",onClick:()=>n.close()})));this.viewer=n,t.append(n);let c=this.root.activeElement;typeof n.showModal=="function"?n.showModal():n.setAttribute("open","");let w=c instanceof HTMLElement?c.dataset.focusKey:null;w?.startsWith("viewer-")&&n.querySelector(`[data-focus-key="${w}"]`)?.focus()}closeViewer(t){this.current!==null&&(this.current=null,this.viewer=null,this.render(),this.root.querySelector(`[data-focus-key="image-${t}"]`)?.focus(),m(this,u.TOGGLE,{expanded:!1}))}};export{j as a};
