/**
 * What every graph stage shares (D-035): DOM helpers, framing from the cards' pinned places,
 * changes applied without rebuilding the graph.
 */

import { Node } from '../../vendor/pivotick/pivotick.es.js';

export const CARD_W = 224; // a card's size in graph units (graph_core.CARD_W / CARD_H)
export const CARD_H = 96;

/** A design token's resolved colour, so the canvas follows the theme. */
export function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888';
}

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

export function icon(classes) {
  const i = el('i', classes);
  i.setAttribute('aria-hidden', 'true');
  return i;
}

export function chip(className, iconClass, text) {
  const span = el('span', className);
  if (iconClass) span.append(icon(iconClass), document.createTextNode(' '));
  span.append(document.createTextNode(text));
  return span;
}

export function fact(label, value) {
  const row = el('div');
  row.append(el('dt', '', label), el('dd', '', value));
  return row;
}

export function placePeek(stage, peek, event) {
  if (peek.hidden || !event) return;
  const box = stage.getBoundingClientRect();
  const x = Math.min(event.clientX - box.left + 18, box.width - peek.offsetWidth - 12);
  const y = Math.min(event.clientY - box.top + 18, box.height - peek.offsetHeight - 12);
  peek.style.transform = `translate(${Math.max(12, x)}px, ${Math.max(12, y)}px)`;
}

export function viewAt(graph, scale, x, y, smooth = true) {
  const renderer = graph.renderer;
  renderer.cancelDeferredFit?.(); // Pivotick's own late fit would undo this view
  const canvasSel = renderer.getCanvasSelection();
  const svg = canvasSel.node();
  const Transform = renderer.getZoomTransform().constructor;
  const target = new Transform(scale, svg.clientWidth / 2 - scale * x, svg.clientHeight / 2 - scale * y);
  (smooth ? canvasSel.transition().duration(350) : canvasSel).call(renderer.getZoomBehavior().transform, target);
}

/** Every card in view, from the cards' own (pinned) places: Pivotick's own fit measures the
 *  SVG, which does not see the size of HTML cards and can leave the view untouched. */
export function fitCards(graph, nodes, smooth = true) {
  if (!nodes.length) return;
  const svg = graph.renderer.getCanvasSelection().node();
  if (!svg.clientWidth || !svg.clientHeight) return;
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const left = Math.min(...xs) - CARD_W / 2 - 48; // a card's x, y is its centre
  const top = Math.min(...ys) - CARD_H / 2 - 48;
  const width = Math.max(...xs) + CARD_W / 2 + 48 - left;
  const height = Math.max(...ys) + CARD_H / 2 + 48 - top;
  const scale = Math.min(svg.clientWidth / width, svg.clientHeight / height, 1);
  viewAt(graph, scale, left + width / 2, top + height / 2, smooth);
}

/** Apply what changed between two answers of the server without rebuilding the graph. */
export function applyChanges(graph, current, next) {
  const before = new Map(current.nodes.map((n) => [n.id, JSON.stringify([n.data, n.x, n.y])]));
  const after = new Set(next.nodes.map((n) => n.id));
  const edgesAfter = new Set(next.edges.map((e) => e.id));
  const edgesBefore = new Set(current.edges.map((e) => e.id));
  for (const edge of current.edges) if (!edgesAfter.has(edge.id)) graph.removeEdge(edge.id);
  for (const node of current.nodes) if (!after.has(node.id)) graph.removeNode(node.id);
  for (const node of next.nodes) {
    if (!before.has(node.id)) graph.addNode(node);
    else if (before.get(node.id) !== JSON.stringify([node.data, node.x, node.y])) {
      const fresh = new Node(node.id, node.data);
      Object.assign(fresh, { x: node.x, y: node.y, fx: node.fx, fy: node.fy });
      graph.updateData([fresh]);
    }
  }
  for (const edge of next.edges) if (!edgesBefore.has(edge.id)) graph.addEdge(edge);
}
