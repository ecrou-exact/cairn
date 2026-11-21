/*! Vitrine v0.14.0 | MIT License | https://github.com/ecrou-exact/vitrine
 * Includes: highlight.js 11.12.0 (BSD-3-Clause), marked 18.1.3 (MIT), DOMPurify 3.4.17 (Apache-2.0 OR MPL-2.0), Lucide 1.52.0 (ISC; icons derived from Feather: MIT).
 * Full license texts: THIRD_PARTY_NOTICES.md */
import{q as I}from"./chunk-JRUMHT4D.js";import{r as $}from"./chunk-DUXCLZ3D.js";import{O as T,_ as E,ba as F,c as k,o as a,q as P}from"./chunk-7PAHM2BV.js";import{h as C,k as N,l as R,m as M}from"./chunk-TUK22DTT.js";var O=`/*\r
 * DNS records: the dig header, findings, type filters and the records table with the\r
 * explanation of policy records under their data.\r
 */\r
.dns-body {\r
  display: grid;\r
  gap: var(--_space-4);\r
  padding: var(--_space-4);\r
  background: var(--_surface);\r
  font-family: var(--_font-ui);\r
  font-size: var(--_font-size-ui);\r
}\r
\r
.dns-query {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-1) var(--_space-5);\r
  margin: 0;\r
}\r
\r
.dns-query div {\r
  display: flex;\r
  gap: var(--_space-2);\r
}\r
\r
.dns-query dt {\r
  color: var(--_fg-muted);\r
}\r
\r
.dns-query dd {\r
  margin: 0;\r
}\r
\r
.dns-query code,\r
.dns-table code {\r
  font-family: var(--_font-mono);\r
}\r
\r
.dns-query .dns-bad dd {\r
  color: var(--_danger);\r
  font-weight: 600;\r
}\r
\r
.dns-findings {\r
  display: grid;\r
  margin: 0;\r
  padding: 0;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
  list-style: none;\r
}\r
\r
.dns-finding {\r
  display: grid;\r
  grid-template-columns: minmax(8.5rem, auto) 1fr;\r
  gap: var(--_space-3);\r
  padding: var(--_space-2) var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
.dns-finding:last-child {\r
  border-bottom: 0;\r
}\r
\r
.dns-level {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: var(--_space-1);\r
  font-weight: 600;\r
}\r
\r
.dns-level svg {\r
  flex: none;\r
  width: 16px;\r
  height: 16px;\r
}\r
\r
.dns-finding.bad .dns-level {\r
  color: var(--_danger);\r
}\r
\r
.dns-finding.warn .dns-level {\r
  color: var(--_warning);\r
}\r
\r
.dns-finding.info .dns-level {\r
  color: var(--_fg-muted);\r
}\r
\r
.dns-message {\r
  display: grid;\r
  gap: 2px;\r
  min-width: 0;\r
}\r
\r
.dns-message code {\r
  color: var(--_fg-muted);\r
  font-family: var(--_font-mono);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.dns-filters {\r
  display: flex;\r
  flex-wrap: wrap;\r
  gap: var(--_space-2);\r
}\r
\r
.dns-filter {\r
  display: inline-flex;\r
  align-items: center;\r
  gap: var(--_space-2);\r
  min-height: 32px;\r
  padding: 4px var(--_space-3);\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-full);\r
  background: var(--_surface);\r
  color: var(--_fg);\r
  font: inherit;\r
  cursor: pointer;\r
}\r
\r
.dns-filter[aria-pressed='true'] {\r
  border-color: var(--_accent);\r
  background: var(--_accent-soft);\r
  color: var(--_accent-fg);\r
  font-weight: 600;\r
}\r
\r
.dns-filter:focus-visible {\r
  outline: 2px solid var(--_accent);\r
  outline-offset: 2px;\r
}\r
\r
.dns-count {\r
  min-width: 2ch;\r
  padding: 0 6px;\r
  border-radius: var(--_radius-full);\r
  background: var(--_surface-sunken);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  text-align: center;\r
}\r
\r
.dns-scroll {\r
  overflow-x: auto;\r
  border: 1px solid var(--_border);\r
  border-radius: var(--_radius-sm);\r
}\r
\r
.dns-table {\r
  width: 100%;\r
  border-collapse: collapse;\r
}\r
\r
.dns-table th,\r
.dns-table td {\r
  padding: 6px var(--_space-3);\r
  border-bottom: 1px solid var(--_border);\r
  text-align: start;\r
  vertical-align: top;\r
}\r
\r
.dns-table tbody tr:last-child > * {\r
  border-bottom: 0;\r
}\r
\r
.dns-table thead th {\r
  background: var(--_surface-sunken);\r
  font-weight: 600;\r
}\r
\r
.dns-table tbody th {\r
  font-weight: 500;\r
  overflow-wrap: anywhere;\r
}\r
\r
.dns-ttl {\r
  color: var(--_fg-muted);\r
  white-space: nowrap;\r
}\r
\r
.dns-type {\r
  display: inline-block;\r
  min-width: 4ch;\r
  color: var(--_syntax-keyword);\r
  font-family: var(--_font-mono);\r
  font-weight: 600;\r
}\r
\r
.dns-tag {\r
  display: inline-block;\r
  margin-inline-start: var(--_space-1);\r
  padding: 0 6px;\r
  border: 1px solid var(--_border-strong);\r
  border-radius: var(--_radius-full);\r
  color: var(--_fg-muted);\r
  font-size: var(--_font-size-small);\r
  white-space: nowrap;\r
}\r
\r
.dns-data {\r
  min-width: 16rem;\r
}\r
\r
.dns-value {\r
  color: var(--_syntax-string);\r
  overflow-wrap: anywhere;\r
  word-break: break-word;\r
}\r
\r
.dns-explain {\r
  display: grid;\r
  gap: 2px;\r
  margin: var(--_space-2) 0 0;\r
  padding-inline-start: var(--_space-3);\r
  border-inline-start: 2px solid var(--_border);\r
  font-size: var(--_font-size-small);\r
}\r
\r
.dns-explain div {\r
  display: grid;\r
  grid-template-columns: minmax(6rem, max-content) 1fr;\r
  gap: var(--_space-2);\r
}\r
\r
.dns-explain dt code {\r
  color: var(--_syntax-function);\r
  overflow-wrap: anywhere;\r
}\r
\r
.dns-explain dd {\r
  margin: 0;\r
  color: var(--_fg-muted);\r
}\r
\r
.dns-part-value {\r
  margin-inline-end: var(--_space-2);\r
  color: var(--_fg);\r
}\r
\r
.dns-edit > .editor-body {\r
  max-height: min(35vh, 280px);\r
  border-bottom: 1px solid var(--_border);\r
}\r
\r
@media (max-width: 560px) {\r
  .dns-finding,\r
  .dns-explain div {\r
    grid-template-columns: 1fr;\r
    gap: 0;\r
  }\r
}\r
`;var q=Object.freeze({dnsRecords:"{count} records",dnsNone:"No DNS record found. Paste `dig` output or a zone file.",dnsAll:"All",dnsFilter:"Record types",dnsName:"Name",dnsTtl:"TTL",dnsType:"Type",dnsData:"Data",dnsQuestion:"Question",dnsStatus:"Status",dnsServer:"Server",dnsTime:"Query time",dnsFlags:"Flags",dnsFindings:"Findings",dnsCopyZone:"Copy records",dnsSection_authority:"Authority",dnsSection_additional:"Additional",dnsKind_spf:"SPF",dnsKind_dmarc:"DMARC",dnsKind_dkim:"DKIM",dnsKind_verification:"Verification",dnsLevel_bad:"Problem",dnsLevel_warn:"Warning",dnsLevel_info:"Note",dnsSpf_all:"{result} for every other sender.",dnsSpf_include:"{result} if {value} allows the sender.",dnsSpf_a:"{result} for the addresses of the domain (A / AAAA).",dnsSpf_mx:"{result} for the mail servers of the domain (MX).",dnsSpf_ip4:"{result} for {value}.",dnsSpf_ip6:"{result} for {value}.",dnsSpf_exists:"{result} if {value} resolves.",dnsSpf_ptr:"{result} by reverse DNS (deprecated).",dnsSpf_redirect:"Use the SPF record of {value}.",dnsSpf_exp:"Explanation for rejected mail at {value}.",dnsSpfUnknown:"Unknown term.",dnsDmarc_p:"Policy for the domain: none (report only), quarantine or reject.",dnsDmarc_sp:"Policy for subdomains.",dnsDmarc_np:"Policy for subdomains that do not exist.",dnsDmarc_pct:"Share of failing mail the policy applies to.",dnsDmarc_rua:"Where aggregate reports are sent.",dnsDmarc_ruf:"Where failure reports are sent.",dnsDmarc_adkim:"DKIM alignment: r (relaxed) or s (strict).",dnsDmarc_aspf:"SPF alignment: r (relaxed) or s (strict).",dnsDmarc_fo:"When failure reports are made.",dnsDmarc_ri:"Seconds between aggregate reports.",dnsDmarc_rf:"Format of failure reports.",dnsDmarc_t:"Testing mode.",dnsDmarc_psd:"Public suffix domain.",dnsDkim_k:"Key type.",dnsDkim_p:"Public key (empty: revoked).",dnsDkim_h:"Hash algorithms allowed.",dnsDkim_t:"Flags: y (testing), s (no subdomains).",dnsDkim_s:"Service type.",dnsDkim_n:"Notes.",dnsTagOther:"Other tag.",dnsMxPreference:"Preference: lower is tried first.",dnsMxExchange:"Mail server.",dnsMxNull:"Null MX: the domain accepts no mail.",dnsSoaMname:"Primary name server.",dnsSoaRname:"Contact of the zone.",dnsSoaSerial:"Version of the zone.",dnsSoaRefresh:"How often secondaries check for changes.",dnsSoaRetry:"Wait before retrying a failed check.",dnsSoaExpire:"When secondaries stop answering without the primary.",dnsSoaMinimum:"How long a missing name is cached.",dnsSrvPriority:"Priority: lower is tried first.",dnsSrvWeight:"Weight between targets of the same priority.",dnsSrvPort:"Port.",dnsSrvTarget:"Host.",dnsCaaIssue:"Only {ca} may issue certificates for this name.",dnsCaaIssueWild:"Only {ca} may issue wildcard certificates.",dnsCaaIodef:"Where certificate authorities report refused requests: {value}.",dnsCaaOther:"Other property.",dnsCaaCritical:"Critical: authorities that do not know the property must refuse.",dnsResult_pass:"Pass",dnsResult_fail:"Fail",dnsResult_softfail:"Soft fail",dnsResult_neutral:"Neutral",dns_spfPassAll:"SPF ends with +all: any server may send mail for the domain.",dns_spfNeutralAll:"SPF ends with ?all: other senders are neither allowed nor refused.",dns_spfNoAll:"SPF has no all and no redirect: other senders are neutral.",dns_spfPtr:"SPF uses ptr, which is slow and deprecated.",dns_spfLookups:"SPF needs {count} DNS lookups: more than 10 makes it fail.",dns_spfMultiple:"{count} SPF records: receivers treat this as an error.",dns_dmarcNoPolicy:"DMARC has no p= policy.",dns_dmarcNone:"DMARC p=none only reports: spoofed mail is still delivered.",dns_dmarcPct:"DMARC applies to {pct}% of failing mail.",dns_dmarcNoRua:"DMARC sends no aggregate reports (no rua).",dns_dkimRevoked:"DKIM key revoked (empty p=).",dns_dkimShortKey:"DKIM RSA key looks shorter than 2048 bits."}),L={dnsRecords:"{count} enregistrements",dnsNone:"Aucun enregistrement DNS trouv\xE9. Collez la sortie de `dig` ou un fichier de zone.",dnsAll:"Tous",dnsFilter:"Types d\u2019enregistrements",dnsName:"Nom",dnsData:"Donn\xE9es",dnsStatus:"Statut",dnsServer:"Serveur",dnsTime:"Dur\xE9e de la requ\xEAte",dnsFlags:"Drapeaux",dnsFindings:"R\xE9sultats",dnsCopyZone:"Copier les enregistrements",dnsSection_authority:"Autorit\xE9",dnsSection_additional:"Additionnel",dnsLevel_bad:"Probl\xE8me",dnsLevel_warn:"Avertissement",dnsLevel_info:"Remarque",dnsSpf_all:"{result} pour tout autre exp\xE9diteur.",dnsSpf_include:"{result} si {value} autorise l\u2019exp\xE9diteur.",dnsSpf_a:"{result} pour les adresses du domaine (A / AAAA).",dnsSpf_mx:"{result} pour les serveurs de messagerie du domaine (MX).",dnsSpf_ip4:"{result} pour {value}.",dnsSpf_ip6:"{result} pour {value}.",dnsSpf_exists:"{result} si {value} existe.",dnsSpf_ptr:"{result} par DNS inverse (obsol\xE8te).",dnsSpf_redirect:"Utilise l\u2019enregistrement SPF de {value}.",dnsSpf_exp:"Explication des refus en {value}.",dnsSpfUnknown:"Terme inconnu.",dnsDmarc_p:"Politique du domaine : none (rapport seulement), quarantine ou reject.",dnsDmarc_sp:"Politique des sous-domaines.",dnsDmarc_np:"Politique des sous-domaines inexistants.",dnsDmarc_pct:"Part des messages en \xE9chec concern\xE9e.",dnsDmarc_rua:"Destination des rapports agr\xE9g\xE9s.",dnsDmarc_ruf:"Destination des rapports d\u2019\xE9chec.",dnsDmarc_adkim:"Alignement DKIM : r (souple) ou s (strict).",dnsDmarc_aspf:"Alignement SPF : r (souple) ou s (strict).",dnsDmarc_fo:"Quand les rapports d\u2019\xE9chec sont produits.",dnsDmarc_ri:"Secondes entre deux rapports agr\xE9g\xE9s.",dnsDmarc_rf:"Format des rapports d\u2019\xE9chec.",dnsDmarc_t:"Mode test.",dnsDmarc_psd:"Domaine de suffixe public.",dnsDkim_k:"Type de cl\xE9.",dnsDkim_p:"Cl\xE9 publique (vide : r\xE9voqu\xE9e).",dnsDkim_h:"Algorithmes de hachage permis.",dnsDkim_t:"Drapeaux : y (test), s (pas de sous-domaines).",dnsDkim_s:"Type de service.",dnsDkim_n:"Notes.",dnsTagOther:"Autre \xE9tiquette.",dnsMxPreference:"Pr\xE9f\xE9rence : la plus basse est essay\xE9e d\u2019abord.",dnsMxExchange:"Serveur de messagerie.",dnsMxNull:"MX nul : le domaine ne re\xE7oit aucun message.",dnsSoaMname:"Serveur de noms principal.",dnsSoaRname:"Contact de la zone.",dnsSoaSerial:"Version de la zone.",dnsSoaRefresh:"Fr\xE9quence de v\xE9rification des secondaires.",dnsSoaRetry:"Attente avant de r\xE9essayer une v\xE9rification.",dnsSoaExpire:"D\xE9lai apr\xE8s lequel les secondaires cessent de r\xE9pondre sans le principal.",dnsSoaMinimum:"Dur\xE9e de cache d\u2019un nom inexistant.",dnsSrvPriority:"Priorit\xE9 : la plus basse est essay\xE9e d\u2019abord.",dnsSrvWeight:"Poids entre cibles de m\xEAme priorit\xE9.",dnsSrvPort:"Port.",dnsSrvTarget:"H\xF4te.",dnsCaaIssue:"Seule {ca} peut \xE9mettre des certificats pour ce nom.",dnsCaaIssueWild:"Seule {ca} peut \xE9mettre des certificats g\xE9n\xE9riques.",dnsCaaIodef:"O\xF9 les autorit\xE9s signalent les demandes refus\xE9es : {value}.",dnsCaaOther:"Autre propri\xE9t\xE9.",dnsCaaCritical:"Critique : une autorit\xE9 qui ne conna\xEEt pas la propri\xE9t\xE9 doit refuser.",dnsResult_pass:"Accept\xE9",dnsResult_fail:"Refus\xE9",dnsResult_softfail:"Refus souple",dnsResult_neutral:"Neutre",dns_spfPassAll:"SPF finit par +all : n\u2019importe quel serveur peut envoyer pour le domaine.",dns_spfNeutralAll:"SPF finit par ?all : les autres exp\xE9diteurs ne sont ni accept\xE9s ni refus\xE9s.",dns_spfNoAll:"SPF n\u2019a ni all ni redirect : les autres exp\xE9diteurs sont neutres.",dns_spfPtr:"SPF utilise ptr, lent et obsol\xE8te.",dns_spfLookups:"SPF demande {count} requ\xEAtes DNS : au-del\xE0 de 10, il \xE9choue.",dns_spfMultiple:"{count} enregistrements SPF : les destinataires le traitent comme une erreur.",dns_dmarcNoPolicy:"DMARC n\u2019a pas de politique p=.",dns_dmarcNone:"DMARC p=none ne fait que signaler : les messages usurp\xE9s sont distribu\xE9s.",dns_dmarcPct:"DMARC s\u2019applique \xE0 {pct} % des messages en \xE9chec.",dns_dmarcNoRua:"DMARC n\u2019envoie pas de rapports agr\xE9g\xE9s (pas de rua).",dns_dkimRevoked:"Cl\xE9 DKIM r\xE9voqu\xE9e (p= vide).",dns_dkimShortKey:"La cl\xE9 RSA DKIM semble plus courte que 2048 bits."};var W=Object.freeze(["A","AAAA","CAA","CNAME","DNAME","DNSKEY","DS","HINFO","HTTPS","LOC","MX","NAPTR","NS","NSEC","NSEC3","NSEC3PARAM","OPT","PTR","RP","RRSIG","SMIMEA","SOA","SPF","SRV","SSHFP","SVCB","TLSA","TXT","URI","ZONEMD","CDS","CDNSKEY","CERT","KEY","SIG","ANY"]),re=Object.freeze({1:"A",2:"NS",5:"CNAME",6:"SOA",12:"PTR",13:"HINFO",15:"MX",16:"TXT",17:"RP",28:"AAAA",29:"LOC",33:"SRV",35:"NAPTR",39:"DNAME",43:"DS",44:"SSHFP",46:"RRSIG",47:"NSEC",48:"DNSKEY",50:"NSEC3",51:"NSEC3PARAM",52:"TLSA",53:"SMIMEA",59:"CDS",60:"CDNSKEY",64:"SVCB",65:"HTTPS",99:"SPF",256:"URI",257:"CAA"}),X=new Set(["IN","CH","HS","CS"]);function S(o){if(/^\d{1,10}$/.test(o))return Number(o);let s={s:1,m:60,h:3600,d:86400,w:604800};if(!/^(?:\d{1,7}[smhdw]){1,5}$/i.test(o))return null;let e=0;for(let t of o.toLowerCase().matchAll(/(\d+)([smhdw])/g))e+=Number(t[1])*s[t[2]];return e}function w(o){let s=[["w",604800],["d",86400],["h",3600],["min",60],["s",1]],e=[],t=o;for(let[i,n]of s)if((t>=n||!e.length&&n===1)&&(e.push(`${Math.floor(t/n)} ${i}`),t%=n),e.length===2)break;return e.join(" ")}function z(o){let s=!1;for(let e=0;e<o.length;e++){let t=o[e];if(t==="\\")e++;else if(t==='"')s=!s;else if(t===";"&&!s)return o.slice(0,e)}return o}function j(o){return o.match(/"(?:[^"\\]|\\.)*"|\S+/g)??[]}function _(o){let s=o.match(/"((?:[^"\\]|\\.)*)"/g);return s?s.map(e=>e.slice(1,-1).replace(/\\(.)/g,"$1")).join(""):o.trim()}function K(o){let s=[],e=null,t="answer",i="",n=null,d="",l=String(o??"").split(/\r\n|\r|\n/);for(let c=0;c<l.length&&s.length<1e4;c++){let r=l[c],p=c+1,u;if(u=/^;; ->>HEADER<<- opcode: \w+, status: (\w+)/.exec(r)){e??={status:"",flags:"",server:"",time:"",question:""},e.status=u[1];continue}if(u=/^;; flags: ([\w ]+);/.exec(r)){e&&(e.flags=u[1].trim());continue}if(u=/^;; (QUESTION|ANSWER|AUTHORITY|ADDITIONAL) SECTION:/.exec(r)){e??={status:"",flags:"",server:"",time:"",question:""},t=u[1].toLowerCase();continue}if(u=/^;; Query time: (.+)$/.exec(r)){e&&(e.time=u[1].trim());continue}if(u=/^;; SERVER: ([^#(\s]+)/.exec(r)){e&&(e.server=u[1]);continue}if(t==="question"&&(u=/^;(\S+)\s+(?:\w+\s+)?(\w+)\s*$/.exec(r))){e&&(e.question=`${u[1]} ${u[2]}`);continue}if(r=z(r),!r.trim())continue;if(r.includes("(")&&!r.includes(")")){let m=r.replace("("," ");for(;++c<l.length;){let h=z(l[c]);if(h.includes(")")){m+=` ${h.replace(")"," ")}`;break}m+=` ${h}`}r=m}else r=r.replace(/[()]/g," ");if(u=/^\$ORIGIN\s+(\S+)/i.exec(r)){i=u[1].replace(/\.$/,"");continue}if(u=/^\$TTL\s+(\S+)/i.exec(r)){n=S(u[1]);continue}if(/^\$/.test(r))continue;let f=j(r),g;/^\s/.test(r)?g=d:g=f.shift();let x=null,b="";for(let m=0;m<2&&f.length;m++){let h=f[0].toUpperCase();X.has(h)&&!b?b=f.shift().toUpperCase():x===null&&S(f[0])!==null&&(x=S(f.shift()))}let v=(f.shift()??"").toUpperCase();!W.includes(v)&&!/^TYPE\d{1,5}$/.test(v)||v!=="OPT"&&(d=g,s.push({name:B(g,i),ttl:x??n,class:b||"IN",type:v,data:f.join(" "),section:t,line:p}))}return{records:s,dig:e}}function B(o,s){return o==="@"?s?`${s}.`:"@":o.endsWith(".")||!s?o:`${o}.${s}.`}var Y=new Set(["include","a","mx","ptr","exists","redirect"]),Q={"+":"pass","-":"fail","~":"softfail","?":"neutral"};function G(o){return o.split(/\s+/).slice(1).filter(Boolean).map(s=>{let e=/^([+\-~?]?)([a-z0-9]+)([:=/]?)(.*)$/i.exec(s);if(!e)return{label:s,value:"",key:"dnsSpfUnknown"};let t=Q[e[1]||"+"],i=e[2].toLowerCase(),n=["all","include","a","mx","ip4","ip6","exists","ptr","redirect","exp"];return{label:s,value:e[4],key:n.includes(i)?`dnsSpf_${i}`:"dnsSpfUnknown",params:{result:t,value:e[4]||""}}})}function y(o){let s=new Map;for(let e of o.split(";")){let t=e.indexOf("=");t>0&&s.set(e.slice(0,t).trim().toLowerCase(),e.slice(t+1).trim())}return s}function V(o){let s=o.data.split(/\s+/);switch(o.type){case"MX":return s[1]==="."?[{label:"MX",value:"",key:"dnsMxNull"}]:[{label:"preference",value:s[0],key:"dnsMxPreference"},{label:"exchange",value:s[1]??"",key:"dnsMxExchange"}];case"SOA":return[["mname","dnsSoaMname"],["rname","dnsSoaRname"],["serial","dnsSoaSerial"],["refresh","dnsSoaRefresh"],["retry","dnsSoaRetry"],["expire","dnsSoaExpire"],["minimum","dnsSoaMinimum"]].map(([e,t],i)=>{let n=s[i]??"",d=i>=3?S(n):null,l=e==="rname"?ee(n):d!==null?`${n} (${w(d)})`:n;return{label:e,value:l,key:t}});case"SRV":return[{label:"priority",value:s[0],key:"dnsSrvPriority"},{label:"weight",value:s[1]??"",key:"dnsSrvWeight"},{label:"port",value:s[2]??"",key:"dnsSrvPort"},{label:"target",value:s[3]??"",key:"dnsSrvTarget"}];case"CAA":{let e=/^(\d+)\s+([a-z0-9]+)\s+(.*)$/i.exec(o.data);if(!e)return null;let t=e[2].toLowerCase(),i=_(e[3]),n=t==="issue"?"dnsCaaIssue":t==="issuewild"?"dnsCaaIssueWild":t==="iodef"?"dnsCaaIodef":"dnsCaaOther",d=i.split(";")[0].trim();return[{label:t,value:i,key:n,params:{ca:d||";",value:i}}].concat(e[1]!=="0"?[{label:"flags",value:e[1],key:"dnsCaaCritical",params:{ca:"",value:""}}]:[])}case"TXT":case"SPF":{let e=_(o.data);return/^v=spf1(?:\s|$)/i.test(e)?G(e):/^v=DMARC1/i.test(e)?[...y(e)].filter(([t])=>t!=="v").map(([t,i])=>({label:t,value:i,key:Z.has(t)?`dnsDmarc_${t}`:"dnsTagOther"})):/^v=DKIM1/i.test(e)||/\._domainkey\./i.test(o.name)?[...y(e)].filter(([t])=>t!=="v").map(([t,i])=>({label:t,value:t==="p"&&i.length>40?`${i.slice(0,24)}\u2026${i.slice(-8)}`:i,key:J.has(t)?`dnsDkim_${t}`:"dnsTagOther"})):null}default:return null}}var Z=new Set(["p","sp","pct","rua","ruf","adkim","aspf","fo","ri","rf","np","t","psd"]),J=new Set(["k","p","h","t","s","n"]);function ee(o){let s=o.replace(/\.$/,""),e=s.search(/(?<!\\)\./);return e<0?s:`${s.slice(0,e).replace(/\\\./g,".")}@${s.slice(e+1)}`}function D(o){if(o.type!=="TXT"&&o.type!=="SPF")return null;let s=_(o.data);return/^v=spf1(?:\s|$)/i.test(s)?"spf":/^v=DMARC1/i.test(s)?"dmarc":/^v=DKIM1/i.test(s)||/\._domainkey\./i.test(o.name)?"dkim":/^[\w.-]+-(?:site-)?verification[=:]/i.test(s)||/^MS=ms\d+/.test(s)?"verification":null}function A(o){let s=[],e=new Map;for(let i of o){if(i.section!=="answer")continue;let n=D(i),d=_(i.data),l=i.name;if(n==="spf"){e.set(l,(e.get(l)??0)+1);let c=d.split(/\s+/).slice(1).filter(Boolean),r=c.find(u=>/^[+\-~?]?all$/i.test(u));r&&/^\+?all$/i.test(r)?s.push({id:"spfPassAll",level:"bad",name:l}):r&&/^\?all$/i.test(r)?s.push({id:"spfNeutralAll",level:"warn",name:l}):!r&&!c.some(u=>/^redirect=/i.test(u))&&s.push({id:"spfNoAll",level:"warn",name:l}),c.some(u=>/^[+\-~?]?ptr(?::|$)/i.test(u))&&s.push({id:"spfPtr",level:"warn",name:l});let p=c.filter(u=>Y.has((/^[+\-~?]?([a-z]+)/i.exec(u)?.[1]??"").toLowerCase())).length;p>10&&s.push({id:"spfLookups",level:"bad",name:l,params:{count:p}})}else if(n==="dmarc"){let c=y(d),r=(c.get("p")??"").toLowerCase();r?r==="none"&&s.push({id:"dmarcNone",level:"warn",name:l}):s.push({id:"dmarcNoPolicy",level:"bad",name:l});let p=Number(c.get("pct")??"100");p<100&&s.push({id:"dmarcPct",level:"info",name:l,params:{pct:p}}),c.has("rua")||s.push({id:"dmarcNoRua",level:"info",name:l})}else if(n==="dkim"){let c=y(d),r=(c.get("p")??"").replace(/\s+/g,"");r?(c.get("k")??"rsa").toLowerCase()==="rsa"&&r.length*3/4<200&&s.push({id:"dkimShortKey",level:"warn",name:l}):s.push({id:"dkimRevoked",level:"info",name:l})}}for(let[i,n]of e)n>1&&s.push({id:"spfMultiple",level:"bad",name:i,params:{count:n}});let t={bad:0,warn:1,info:2};return s.sort((i,n)=>t[i.level]-t[n.level])}M({en:q,fr:L});var se={bad:"shield-alert",warn:"alert",info:"status-circle"},H=class extends F{static type="dns";static fromData=I;static componentAttributes=Object.freeze(["explain","checks","filters"]);static presets={simple:{},full:{header:!0,dot:!0,copy:!0,fullscreen:!0}};static styles=[O];static upgradeProperties=["content"];constructor(){super(),this.panelId=P("panel"),this.only=null,this.editor=null,this.previewTimer=void 0}zone(){return K(this.text??"")}get records(){return this.zone().records}get findings(){return A(this.records)}flag(s){return k(this.getAttribute(s))!==!1}renderContent(s){let e=this.t,{records:t,dig:i}=this.zone();this.only&&!t.some(r=>r.type===this.only)&&(this.only=null);let n=a("div",{class:"body dns-body",part:"body"});if(i&&n.append(this.digView(i)),!t.length)n.append(E(e("dnsNone")));else{let r=this.flag("checks")?A(t):[];r.length&&n.append(this.findingsView(r)),this.flag("filters")&&n.append(this.filtersView(t)),n.append(this.tableView(this.only?t.filter(p=>p.type===this.only):t))}let d=a("div",{class:"panel",attrs:{id:this.panelId}}),l=[];if(this.editing){let r=this.createEditor();d.classList.add("dns-edit"),d.append(a("div",{class:"body editor-body",part:"body source"},r.element),n),l=this.historyButtons(r)}else d.append(n);let c=[...l,this.editToggleButton(),this.fullscreenButton(),this.feature("copy")&&t.length?this.copyButton(()=>t.map(r=>[r.name,r.ttl??"",r.class,r.type,r.data].join("	")).join(`
`),e("dnsCopyZone")):null];s.append(...this.chrome({badge:e("dnsRecords",{count:t.length}),actions:c}),d),this.editor?.align()}digView(s){let e=this.t,t=[["dnsQuestion",s.question],["dnsStatus",s.status],["dnsServer",s.server],["dnsTime",s.time],["dnsFlags",s.flags]];return a("dl",{class:"dns-query",part:"query"},...t.filter(([,i])=>i).map(([i,n])=>a("div",{class:i==="dnsStatus"&&n!=="NOERROR"?"dns-bad":""},a("dt",{text:e(i)}),a("dd",{},a("code",{text:n})))))}findingsView(s){let e=this.t;return a("ul",{class:"dns-findings",part:"findings",attrs:{"aria-label":e("dnsFindings")}},...s.map(t=>a("li",{class:`dns-finding ${t.level}`},a("span",{class:"dns-level"},T(se[t.level]),a("span",{text:e(`dnsLevel_${t.level}`)})),a("span",{class:"dns-message"},a("code",{text:t.name}),a("span",{text:e(`dns_${t.id}`,t.params)})))))}filtersView(s){let e=this.t,t=new Map;for(let n of s)t.set(n.type,(t.get(n.type)??0)+1);let i=(n,d,l)=>a("button",{class:"dns-filter",attrs:{type:"button","aria-pressed":String(this.only===n),"data-focus-key":`filter-${n??"all"}`},on:{click:()=>{this.only=n;let c=this.activeFocusKey();this.render(),c&&this.restoreFocus(c)}}},a("span",{text:d}),a("span",{class:"dns-count",text:String(l)}));return a("div",{class:"dns-filters",part:"filters",attrs:{role:"group","aria-label":e("dnsFilter")}},i(null,e("dnsAll"),s.length),...[...t].sort(([n],[d])=>n.localeCompare(d)).map(([n,d])=>i(n,n,d)))}tableView(s){let e=this.t,t=this.flag("explain"),i=s.map(n=>{let d=D(n),l=t?V(n):null,c=a("td",{class:"dns-data"},a("code",{class:"dns-value",text:n.data}),l?this.partsView(l):null);return a("tr",{},a("th",{attrs:{scope:"row"}},a("code",{text:n.name}),n.section==="authority"||n.section==="additional"?a("span",{class:"dns-tag",text:e(`dnsSection_${n.section}`)}):null),a("td",{class:"dns-ttl",text:n.ttl===null?"":w(n.ttl),attrs:n.ttl===null?{}:{title:`${n.ttl} s`}}),a("td",{},a("span",{class:`dns-type t-${n.type.toLowerCase()}`,part:"type",text:n.type}),d?a("span",{class:"dns-tag",text:e(`dnsKind_${d}`)}):null),c)});return a("div",{class:"dns-scroll"},a("table",{class:"dns-table",part:"records"},a("thead",{},a("tr",{},a("th",{attrs:{scope:"col"},text:e("dnsName")}),a("th",{attrs:{scope:"col"},text:e("dnsTtl")}),a("th",{attrs:{scope:"col"},text:e("dnsType")}),a("th",{attrs:{scope:"col"},text:e("dnsData")}))),a("tbody",{},...i)))}partsView(s){let e=this.t;return a("dl",{class:"dns-explain",part:"explanation"},...s.map(t=>{let i=t.params?{...t.params,result:t.params.result?e(`dnsResult_${t.params.result}`):""}:void 0,n=t.key?e(t.key,i):"",d=t.value&&!t.label.endsWith(t.value)?t.value:"";return a("div",{},a("dt",{},a("code",{text:t.label})),a("dd",{},d?a("code",{class:"dns-part-value",text:d}):null,a("span",{text:n})))}))}createEditor(){return this.editor?.destroy(),this.editor=new $({text:this.text??"",language:"plaintext",lineNumbers:!0,wrap:!1,highlightLimit:C().highlightLimit,label:this.heading||this.t("editor"),placeholder:this.getAttribute("placeholder")??void 0,onInput:s=>this.edited(s),onChange:s=>R(this,N.CHANGE,{value:s}),history:this.editHistory??void 0}),this.editor}contentEdited(){clearTimeout(this.previewTimer),this.previewTimer=setTimeout(()=>this.render(),250)}};export{H as a};
