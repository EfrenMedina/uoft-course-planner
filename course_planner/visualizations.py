"""Plotly visualizations of a CourseGraph.

Courses are drawn as labelled boxes in layers: a course sits one layer below its
deepest prerequisite, and arrows point from a prerequisite to the course that needs
it. Within each layer, courses are ordered to keep arrows from crossing.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

import networkx as nx
from plotly.graph_objs import Figure, Scatter

from course_planner.boolean_list import BooleanList
from course_planner.course_graph import CourseGraph, _CourseVertex

# Box styles for each course status: (legend label, fill colour, border colour)
STATUS_STYLES = {
    'completed': ('Already completed', '#e7edf6', '#7c8ea8'),
    'path': ('Chosen path', '#d3f0da', '#2f9e44'),
    'target': ('Target', '#fff1b8', '#d39e00'),
}
EDGE_COLOUR = '#9aa5b1'
TEXT_COLOUR = '#1f2328'

X_SPACING = 1.0     # horizontal distance between neighbouring courses in a layer
BEND_WIDTH = 0.35   # horizontal room taken by an edge bend point, relative to a course
SWEEPS = 12         # down/up passes used to reduce edge crossings; the best ordering is kept


def visualize_course_graph(graph: CourseGraph, output_file: str = '',
                           path: Iterable[str] = (), target: str | None = None) -> None:
    """Display graph as an interactive Plotly figure, or save it to output_file.

    Courses in path are numbered in the order given and drawn as the chosen path,
    target is highlighted, and every other course in graph is drawn as already completed.
    output_file may end in .html (interactive page) or an image extension such as
    .png (requires the optional kaleido package).
    """
    fig = build_figure(graph, path=path, target=target)
    if output_file == '':
        fig.show()
    elif output_file.endswith('.html'):
        fig.write_html(output_file)
    else:
        fig.write_image(output_file)


def build_figure(graph: CourseGraph, path: Iterable[str] = (), target: str | None = None) -> Figure:
    """Return the Plotly figure for graph; see visualize_course_graph for the arguments."""
    path = list(path)
    step_of = {code: i + 1 for i, code in enumerate(path)}

    digraph = graph.to_networkx()
    pos, routes = layered_layout(digraph)

    def status(code: str) -> str:
        if code == target:
            return 'target'
        return 'path' if code in step_of else 'completed'

    fig = Figure()
    annotations = []

    # Edges that skip layers bend through intermediate points; draw those bends as lines
    # and finish every edge with an arrow into its course. Boxes are drawn on top.
    line_x: list[float | None] = []
    line_y: list[float | None] = []
    for route in routes.values():
        if len(route) > 2:
            line_x += [x for x, _ in route[:-1]] + [None]
            line_y += [y for _, y in route[:-1]] + [None]
        (start_x, start_y), (end_x, end_y) = route[-2], route[-1]
        annotations.append({
            'x': end_x, 'y': end_y, 'xref': 'x', 'yref': 'y',
            'ax': start_x, 'ay': start_y, 'axref': 'x', 'ayref': 'y',
            'text': '', 'showarrow': True, 'arrowhead': 2, 'arrowsize': 1.2,
            'arrowwidth': 1.4, 'arrowcolor': EDGE_COLOUR, 'standoff': 20,
            'startstandoff': 20 if len(route) == 2 else 0,
        })
    if line_x:
        fig.add_trace(Scatter(x=line_x, y=line_y, mode='lines', hoverinfo='skip', showlegend=False,
                              line={'color': EDGE_COLOUR, 'width': 1.4}))

    for code in digraph.nodes:
        _, fill, border = STATUS_STYLES[status(code)]
        label = f'<b>{code}</b>'
        if code in step_of:
            label += f'<br><span style="font-size:10px">step {step_of[code]}</span>'
        elif code == target:
            label += '<br><span style="font-size:10px">target</span>'
        annotations.append({
            'x': pos[code][0], 'y': pos[code][1], 'xref': 'x', 'yref': 'y',
            'text': label, 'showarrow': False, 'font': {'size': 13, 'color': TEXT_COLOUR},
            'bgcolor': fill, 'bordercolor': border, 'borderwidth': 1.5, 'borderpad': 6,
        })

    # Invisible markers under the boxes provide the hover text.
    codes = list(digraph.nodes)
    fig.add_trace(Scatter(
        x=[pos[c][0] for c in codes], y=[pos[c][1] for c in codes], mode='markers',
        marker={'size': 44, 'opacity': 0}, showlegend=False,
        hovertext=[f'<b>{c}</b><br>{graph.vertices[c].name}<br>{STATUS_STYLES[status(c)][0]}'
                   for c in codes],
        hoverinfo='text',
    ))

    # Legend entries for the statuses that appear in this figure.
    present = {status(c) for c in codes}
    for key, (label, fill, border) in STATUS_STYLES.items():
        if key in present:
            fig.add_trace(Scatter(
                x=[None], y=[None], mode='markers', name=label,
                marker={'symbol': 'square', 'size': 14, 'color': fill, 'line': {'color': border, 'width': 1.5}},
            ))

    layer_count = 1 + max((-y for _, y in pos.values()), default=0)
    all_points = list(pos.values()) + [point for route in routes.values() for point in route]
    widest = max((abs(x) for x, _ in all_points), default=0)
    title = f'Path to {target}' if target else 'Course prerequisites'
    fig.update_layout(
        title={'text': title, 'x': 0.5},
        template='plotly_white',
        annotations=annotations,
        width=max(720, int(220 * (2 * widest + 1.6))),
        height=max(420, int(140 * layer_count + 160)),
        margin={'l': 20, 'r': 20, 't': 70, 'b': 20},
        legend={'orientation': 'h', 'x': 0.5, 'xanchor': 'center', 'y': 1.0, 'yanchor': 'bottom'},
        hoverlabel={'bgcolor': 'white'},
    )
    fig.update_xaxes(visible=False, range=[-widest - 0.8, widest + 0.8])
    fig.update_yaxes(visible=False, range=[-(layer_count - 1) - 0.6, 0.6])
    return fig


def get_depths(digraph: nx.DiGraph) -> dict[str, int]:
    """Return a dictionary mapping each node to its depth in the digraph.

    Depth is the length of the longest chain of prerequisites leading to the node.
    Courses that require each other (a cycle in the calendar data) share a depth.

    >>> g = nx.DiGraph([('A', 'B'), ('B', 'C'), ('A', 'C')])
    >>> get_depths(g) == {'A': 0, 'B': 1, 'C': 2}
    True
    >>> get_depths(nx.DiGraph([('A', 'B'), ('B', 'A'), ('B', 'C')])) == {'A': 0, 'B': 0, 'C': 1}
    True
    """
    condensed = nx.condensation(digraph)
    component_depth: dict[int, int] = {}
    for component in nx.topological_sort(condensed):
        predecessors = list(condensed.predecessors(component))
        component_depth[component] = 1 + max((component_depth[p] for p in predecessors), default=-1)
    mapping = condensed.graph['mapping']
    return {node: component_depth[mapping[node]] for node in digraph.nodes}


Position = tuple[float, float]


def layered_layout(digraph: nx.DiGraph) -> tuple[dict[str, Position], dict[tuple[str, str], list[Position]]]:
    """Return node positions and edge routes for a layered drawing of digraph.

    Each node is placed in the layer given by get_depths, drawn at y = -depth and
    centred on x = 0. An edge that skips layers is split by a bend point in every
    layer it crosses, so it can be routed around the boxes in between. Layers are
    ordered with the barycentre heuristic: repeated passes sort each layer by the
    average position of its neighbours in the adjacent layer, which removes most
    edge crossings.

    The second value maps each edge (u, v) to the points its line passes through,
    from u's position to v's position.

    >>> pos, routes = layered_layout(nx.DiGraph([('A', 'B'), ('B', 'C'), ('A', 'C')]))
    >>> [pos[n][1] for n in 'ABC']
    [0, -1, -2]
    >>> len(routes[('A', 'B')]), len(routes[('A', 'C')])
    (2, 3)
    """
    depths = get_depths(digraph)
    expanded = nx.DiGraph()
    expanded.add_nodes_from(digraph.nodes)
    layer_of: dict[object, int] = dict(depths)
    chains: dict[tuple[str, str], list[object]] = {}

    for u, v in digraph.edges:
        chain: list[object] = [u]
        for layer in range(depths[u] + 1, depths[v]):
            bend = ('bend', u, v, layer)
            layer_of[bend] = layer
            chain.append(bend)
        chain.append(v)
        nx.add_path(expanded, chain)
        chains[(u, v)] = chain

    order: list[list[object]] = [[] for _ in range(1 + max(layer_of.values(), default=-1))]
    for node in sorted(digraph.nodes):
        order[layer_of[node]].append(node)
    for node in expanded.nodes:
        if node not in depths:
            order[layer_of[node]].append(node)

    best_order = [list(layer) for layer in order]
    best_crossings = _order_crossings(expanded, order)
    for _ in range(SWEEPS):
        for d in range(1, len(order)):
            order[d] = _reorder(order[d], order[d - 1], expanded.predecessors)
        for d in range(len(order) - 2, -1, -1):
            order[d] = _reorder(order[d], order[d + 1], expanded.successors)
        crossings = _order_crossings(expanded, order)
        if crossings < best_crossings:
            best_order, best_crossings = [list(layer) for layer in order], crossings

    pos: dict[object, Position] = {}
    for depth, layer in enumerate(best_order):
        widths = [X_SPACING if node in depths else BEND_WIDTH * X_SPACING for node in layer]
        x = -sum(widths) / 2
        for node, width in zip(layer, widths, strict=True):
            pos[node] = (x + width / 2, -depth)
            x += width

    node_pos = {node: pos[node] for node in digraph.nodes}
    routes = {edge: [pos[node] for node in chain] for edge, chain in chains.items()}
    return node_pos, routes


def _order_crossings(expanded: nx.DiGraph, order: list[list]) -> int:
    """Return the number of edge crossings between adjacent layers of order."""
    index = {node: i for layer in order for i, node in enumerate(layer)}
    total = 0
    for layer in order:
        edges = [(index[u], index[v]) for u in layer for v in expanded.successors(u)]
        total += sum(1 for i, (a, b) in enumerate(edges) for c, d in edges[i + 1:] if (a - c) * (b - d) < 0)
    return total


def _reorder(layer: list, neighbour_layer: list, neighbours_of: Callable) -> list:
    """Return layer sorted by the average relative position of each node's neighbours
    in neighbour_layer. Nodes without such neighbours keep their relative position.
    """
    index = {node: i for i, node in enumerate(neighbour_layer)}
    scale = max(len(neighbour_layer) - 1, 1)

    def key(item: tuple[int, object]) -> tuple[float, int]:
        position, node = item
        linked = [index[n] for n in neighbours_of(node) if n in index]
        if linked:
            return sum(linked) / len(linked) / scale, position
        return position / max(len(layer) - 1, 1), position

    return [node for _, node in sorted(enumerate(layer), key=key)]


def hierarchical_layout(digraph: nx.DiGraph) -> dict[str, Position]:
    """Return an (x, y) position for each node of digraph; see layered_layout.

    >>> pos = hierarchical_layout(nx.DiGraph([('A', 'C'), ('B', 'C')]))
    >>> pos['C']
    (0.0, -1)
    >>> sorted(pos[n][0] for n in 'AB')
    [-0.5, 0.5]
    """
    return layered_layout(digraph)[0]


def count_crossings(routes: dict[tuple[str, str], list[Position]]) -> int:
    """Return the number of pairs of edge segments that cross between adjacent layers.

    >>> count_crossings({('A', 'D'): [(0, 0), (1, -1)], ('B', 'C'): [(1, 0), (0, -1)]})
    1
    >>> count_crossings({('A', 'C'): [(0, 0), (0, -1)], ('B', 'D'): [(1, 0), (1, -1)]})
    0
    """
    segments = [(route[i], route[i + 1]) for route in routes.values() for i in range(len(route) - 1)]
    crossings = 0
    for i, ((x1, y1), (x2, _)) in enumerate(segments):
        for (x3, y3), (x4, _) in segments[i + 1:]:
            if y1 == y3 and (x1 - x3) * (x2 - x4) < 0:
                crossings += 1
    return crossings


if __name__ == '__main__':
    # Small demo: render a short prerequisite chain.
    demo = CourseGraph()
    demo.add_vertex(_CourseVertex('CSC110Y1', 'Foundations of Computer Science I'))
    demo.add_vertex(_CourseVertex('MAT137Y1', 'Calculus with Proofs'))
    demo.add_vertex(_CourseVertex('CSC111H1', 'Foundations of Computer Science II',
                                  BooleanList('AND', ['CSC110Y1'])))
    demo.add_vertex(_CourseVertex('STA237H1', 'Probability, Statistics and Data Analysis I',
                                  BooleanList('AND', ['MAT137Y1'])))
    demo.add_vertex(_CourseVertex('CSC207H1', 'Software Design', BooleanList('AND', ['CSC111H1'])))
    visualize_course_graph(demo, path=['CSC111H1', 'STA237H1'], target='CSC207H1')
