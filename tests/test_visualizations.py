"""Tests for the layered path-graph layout and figure."""
import networkx as nx

from course_planner.boolean_list import BooleanList
from course_planner.course_graph import CourseGraph, _CourseVertex
from course_planner.visualizations import STATUS_STYLES, build_figure, count_crossings, get_depths, layered_layout


def path_graph() -> CourseGraph:
    """The CSC311 example: two completed courses, four chosen courses and the target."""
    graph = CourseGraph()
    for code, prereqs in [
        ('CSC110Y1', None), ('MAT137Y1', None), ('MAT223H1', None),
        ('CSC111H1', BooleanList('AND', ['CSC110Y1'])),
        ('STA237H1', BooleanList('AND', ['MAT137Y1'])),
        ('CSC207H1', BooleanList('AND', ['CSC111H1'])),
        ('CSC311H1', BooleanList('AND', ['CSC207H1', 'MAT137Y1', 'MAT223H1', 'STA237H1'])),
    ]:
        graph.add_vertex(_CourseVertex(code, f'{code} name', prereqs))
    return graph


def test_layers_follow_longest_prerequisite_chain() -> None:
    depths = get_depths(path_graph().to_networkx())
    assert depths['CSC110Y1'] == 0
    assert depths['CSC207H1'] == 2
    assert depths['CSC311H1'] == 3


def test_layout_has_no_crossings_and_routes_long_edges() -> None:
    digraph = path_graph().to_networkx()
    pos, routes = layered_layout(digraph)
    assert count_crossings(routes) == 0
    for (u, v), route in routes.items():
        assert route[0] == pos[u] and route[-1] == pos[v]
        # One point per layer: no segment skips a layer, so none can pass behind a box.
        assert [y for _, y in route] == list(range(int(pos[u][1]), int(pos[v][1]) - 1, -1))
    # Bend points never land on a course box.
    bends = {point for route in routes.values() for point in route[1:-1]}
    assert not bends & set(pos.values())


def test_cycles_do_not_break_layout() -> None:
    pos, routes = layered_layout(nx.DiGraph([('A', 'B'), ('B', 'A'), ('B', 'C')]))
    assert pos['A'][1] == pos['B'][1] == 0
    assert pos['C'][1] == -1
    assert len(routes) == 3


def test_figure_marks_status_and_steps() -> None:
    fig = build_figure(path_graph(), path=['CSC111H1', 'CSC207H1'], target='CSC311H1')
    boxes = {a.text: a for a in fig.layout.annotations if a.text}
    assert boxes['<b>CSC111H1</b><br><span style="font-size:10px">step 1</span>'].bgcolor == STATUS_STYLES['path'][1]
    assert boxes['<b>CSC311H1</b><br><span style="font-size:10px">target</span>'].bgcolor == STATUS_STYLES['target'][1]
    assert boxes['<b>CSC110Y1</b>'].bgcolor == STATUS_STYLES['completed'][1]
    arrows = [a for a in fig.layout.annotations if a.showarrow]
    assert len(arrows) == path_graph().to_networkx().number_of_edges()
    assert fig.layout.title.text == 'Path to CSC311H1'
