import { N as E, S as F, E as _, T as k, f as R, C as X, c as U, a as v } from "./index.js";
const A = 1e4, I = 2e4, x = 0.15 * I;
self.onmessage = (a) => {
  if (a.data.source === X) {
    const { graph: n, resolutions: i } = a.data;
    postMessage({ type: "done", levels: U(n, i) });
    return;
  }
  a.data.source === "simulation-worker-wrapper" && z(a.data);
};
function z(a) {
  var h, t, c;
  const { nodes: n, edges: i, options: o, canvasBCR: g, groups: f = [] } = a, m = n.map((e) => {
    const u = new E(e.id, e.data, e.style);
    return u.setCircleRadius(e._circleRadius ?? 10), u.setLayoutSize(e._layoutSize), typeof e.x == "number" && (u.x = e.x), typeof e.y == "number" && (u.y = e.y), typeof e.fx == "number" && (u.fx = e.fx), typeof e.fy == "number" && (u.fy = e.fy), u;
  }), r = new Map(m.map((e) => [e.id, e])), { simulation: s, simulationForces: T } = F.initSimulationForces(o, g), p = [];
  for (const e of i) {
    const u = r.get(e.from.id), b = r.get(e.to.id);
    if (u && b) {
      const L = e.style ?? {};
      p.push(new _(e.id, u, b, e.data, L, e.directed));
    }
  }
  s.nodes(m);
  const D = s.force("link");
  D && D.id((e) => e.id).links(p), O(s, f, r), ((h = o.layout) == null ? void 0 : h.type) === "tree" ? k.registerForcesOnSimulation(m, p, s, T, o.layout, g, k) : ((t = o.layout) == null ? void 0 : t.type) === "egoTree" && k.registerForcesOnSimulation(m, p, s, T, o.layout, g, v);
  const { warmupTicks: S, reheatTicks: y } = N(o);
  let d = 0.3;
  s.alphaTarget(d);
  const l = (/* @__PURE__ */ new Date()).getTime();
  let w;
  for (let e = 0; e < S && !((/* @__PURE__ */ new Date()).getTime() - l > A || (/* @__PURE__ */ new Date()).getTime() - l > o.cooldownTime || M(o, s, d) && (/* @__PURE__ */ new Date()).getTime() - l > o.cooldownTime * 0.15); ++e)
    e % 5 === 0 && (w = C(e, (/* @__PURE__ */ new Date()).getTime() - l, o), postMessage({ type: "tick", progress: w, elapsedTime: (/* @__PURE__ */ new Date()).getTime() - l })), s.tick();
  d = 0, s.alphaTarget(d), s.alpha(1);
  for (let e = 0; e < y && !(M(o, s, d) && (/* @__PURE__ */ new Date()).getTime() - l > o.cooldownTime * 0.15); ++e)
    s.tick(), e % 5 === 0 && (w = C(S + e, (/* @__PURE__ */ new Date()).getTime() - l, o), postMessage({ type: "tick", progress: w, elapsedTime: (/* @__PURE__ */ new Date()).getTime() - l }));
  postMessage({ type: "tick", progress: 1, elapsedTime: (/* @__PURE__ */ new Date()).getTime() - l }), ((c = o.layout) == null ? void 0 : c.type) === "tree" && k.simulationDone(m, p, s, o.layout), postMessage({ type: "done", nodes: m.map((e) => e.toDict()), edges: p.map((e) => e.toDict()) });
}
function K(a, n, i, o, g = []) {
  var l, w, h;
  const f = a.map((t) => {
    const c = new E(t.id, t.getData(), t.getStyle());
    return c.weight = t.weight || 1, c.setCircleRadius(t.getCircleRadius()), typeof t.x == "number" && (c.x = t.x), typeof t.y == "number" && (c.y = t.y), typeof t.fx == "number" && (c.fx = t.fx), typeof t.fy == "number" && (c.fy = t.fy), c;
  }), m = new Map(f.map((t) => [t.id, t])), { simulation: r, simulationForces: s } = F.initSimulationForces(i, o), T = [];
  for (const t of n) {
    const c = m.get(t.from.id), e = m.get(t.to.id);
    if (c && e) {
      const u = t.getStyle() ?? {};
      T.push(new _(t.id, c, e, t.getData(), u, t.directed));
    }
  }
  r.nodes(f);
  const p = r.force("link");
  p && p.id((t) => t.id).links(T), O(r, g, m), (((l = i.layout) == null ? void 0 : l.type) === "tree" || ((w = i.layout) == null ? void 0 : w.type) === "egoTree") && k.registerForcesOnSimulation(f, T, r, s, i.layout, o, k);
  const { warmupTicks: D, reheatTicks: S } = N(i);
  let y = 0.3;
  r.alphaTarget(y);
  const d = (/* @__PURE__ */ new Date()).getTime();
  for (let t = 0; t < D && !((/* @__PURE__ */ new Date()).getTime() - d > A || (/* @__PURE__ */ new Date()).getTime() - d > i.cooldownTime || M(i, r, y) && (/* @__PURE__ */ new Date()).getTime() - d > i.cooldownTime * 0.15); ++t)
    r.tick();
  y = 0, r.alphaTarget(y), r.alpha(1);
  for (let t = 0; t < S && !(M(i, r, y) && (/* @__PURE__ */ new Date()).getTime() - d > i.cooldownTime * 0.15); ++t)
    r.tick();
  return ((h = i.layout) == null ? void 0 : h.type) === "tree" && k.simulationDone(f, T, r, i.layout), { nodes: f, edges: T };
}
function O(a, n, i) {
  const o = n.map((g) => ({ parts: g.map((f) => i.get(f)).filter((f) => f !== void 0) })).filter((g) => g.parts.length > 1);
  o.length && a.force("groupCohesion", R(() => o));
}
function N(a) {
  const n = a.warmupTicks === "auto" || a.warmupTicks == null ? I : a.warmupTicks;
  return n <= 0 ? { warmupTicks: 0, reheatTicks: 0 } : { warmupTicks: n - x, reheatTicks: x };
}
function C(a, n, i) {
  return n / i.cooldownTime;
}
function M(a, n, i) {
  return a.d3AlphaMin > 0 && n.alpha() - i < a.d3AlphaMin;
}
export {
  K as runSimulation
};
