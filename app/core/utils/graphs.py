"""Small graph helpers shared by the planning cores (task dependencies, project links)."""

from __future__ import annotations

from collections import deque
from collections.abc import Hashable, Iterable, Mapping


def path_between[N: Hashable](edges: Mapping[N, Iterable[N]], start: N, goal: N) -> list[N] | None:
    """A shortest path from `start` to `goal` along `edges` (node → successors), or None.
    Used to refuse a link that would close a loop, and to name that loop."""
    previous: dict[N, N | None] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == goal:
            path = [node]
            while previous[path[-1]] is not None:
                path.append(previous[path[-1]])  # type: ignore[arg-type]
            return path[::-1]
        for nxt in edges.get(node, ()):
            if nxt not in previous:
                previous[nxt] = node
                queue.append(nxt)
    return None
