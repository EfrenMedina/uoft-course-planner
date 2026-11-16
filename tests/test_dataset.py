"""Integration tests against the bundled UofT course dataset."""
from pathlib import Path

import pytest

from course_planner.algorithms import get_next_needed_courses
from course_planner.course_graph import CourseGraph
from course_planner.json_to_graph import load_graph_from_json

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'courses.json'


@pytest.fixture(scope='module')
def graph() -> CourseGraph:
    return load_graph_from_json(str(DATA_FILE))


def test_dataset_loads(graph: CourseGraph) -> None:
    assert len(graph.vertices) > 5000
    assert all(code == vertex.code for code, vertex in graph.vertices.items())
    assert all(vertex.level() in {0, 100, 200, 300, 400} for vertex in graph.vertices.values())


def test_known_prerequisites(graph: CourseGraph) -> None:
    csc373 = graph.vertices['CSC373H1']
    assert csc373.prerequisites.get_all_courses() >= {'CSC263H1', 'CSC265H1'}
    assert graph.is_eligible('CSC373H1', {'CSC263H1'})
    assert not graph.is_eligible('CSC373H1', {'CSC236H1'})


def test_next_courses_for_csc373(graph: CourseGraph) -> None:
    done = {'CSC110Y1', 'CSC111H1', 'MAT137Y1'}
    suggestions = get_next_needed_courses(graph, 'CSC373H1', done)
    assert 'CSC236H1' in suggestions
    assert all(graph.is_eligible(code, done) for code in suggestions)


@pytest.mark.parametrize('target', ['CSC263H1', 'CSC311H1', 'CSC373H1', 'CSC413H1', 'MAT347Y1', 'STA302H1'])
def test_navigation_reaches_target(graph: CourseGraph, target: str) -> None:
    """Simulate a student who always takes one suggested course; they must reach the target."""
    completed: set[str] = set()
    for _ in range(40):
        options = get_next_needed_courses(graph, target, completed)
        assert options, f'dead end before reaching {target} with {sorted(completed)}'
        if target in options:
            return
        assert all(graph.is_eligible(code, completed) for code in options)
        completed.add(min(options))
    pytest.fail(f'did not reach {target} within 40 courses')
