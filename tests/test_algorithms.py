"""Tests for the prerequisite-path algorithms on small hand-built graphs."""
import pytest

from course_planner.algorithms import (
    eligible_relevant_courses,
    get_next_needed_courses,
    get_relevant_courses,
    search_courses,
)
from course_planner.boolean_list import BooleanList
from course_planner.course_graph import CourseGraph, _CourseVertex


def make_graph(prereqs: dict[str, BooleanList | None]) -> CourseGraph:
    """Return a CourseGraph with one vertex per entry of prereqs."""
    graph = CourseGraph()
    for code, tree in prereqs.items():
        graph.add_vertex(_CourseVertex(code, f'{code} name', tree))
    return graph


@pytest.fixture
def graph() -> CourseGraph:
    """A small slice of the CS/math prerequisite structure.

    CSC263 needs CSC236 AND (STA237 OR STA247).
    CSC236 needs CSC148 AND CSC165.  CSC148 needs CSC108.
    STA247 needs (MAT135 AND MAT136) OR MAT137.
    """
    return make_graph({
        'CSC108H1': None,
        'CSC148H1': BooleanList('AND', ['CSC108H1']),
        'CSC165H1': None,
        'CSC236H1': BooleanList('AND', ['CSC148H1', 'CSC165H1']),
        'MAT135H1': None,
        'MAT136H1': BooleanList('AND', ['MAT135H1']),
        'MAT137Y1': None,
        'STA237H1': BooleanList('AND', ['MAT137Y1']),
        'STA247H1': BooleanList('OR', [BooleanList('AND', ['MAT135H1', 'MAT136H1']), 'MAT137Y1']),
        'CSC263H1': BooleanList('AND', ['CSC236H1', BooleanList('OR', ['STA237H1', 'STA247H1'])]),
    })


def test_and_collects_from_every_unsatisfied_branch(graph: CourseGraph) -> None:
    # From scratch, every AND branch needs work, so starting points of both are suggested.
    assert get_next_needed_courses(graph, 'CSC263H1', set()) >= {'CSC108H1', 'CSC165H1'}


def test_target_returned_once_eligible(graph: CourseGraph) -> None:
    done = {'CSC108H1', 'CSC148H1', 'CSC165H1', 'CSC236H1', 'MAT137Y1', 'STA237H1'}
    assert get_next_needed_courses(graph, 'CSC263H1', done) == {'CSC263H1'}


def test_completed_target_needs_nothing(graph: CourseGraph) -> None:
    assert get_next_needed_courses(graph, 'CSC108H1', {'CSC108H1'}) == set()


def test_or_prefers_branch_already_started(graph: CourseGraph) -> None:
    # MAT135 is done, so the planner keeps going down the (MAT135 AND MAT136) branch
    # rather than also suggesting MAT137.
    assert get_next_needed_courses(graph, 'STA247H1', {'MAT135H1'}) == {'MAT136H1'}


def test_or_prefers_immediately_eligible_options(graph: CourseGraph) -> None:
    # Nothing started: MAT137 can be taken now, and MAT135 starts the other branch.
    assert get_next_needed_courses(graph, 'STA247H1', set()) == {'MAT135H1', 'MAT137Y1'}


def test_prerequisite_cycle_terminates() -> None:
    cyclic = make_graph({
        'AAA100H1': BooleanList('AND', ['BBB100H1']),
        'BBB100H1': BooleanList('AND', ['AAA100H1']),
        'CCC300H1': BooleanList('AND', ['AAA100H1']),
    })
    assert get_next_needed_courses(cyclic, 'CCC300H1', set()) == set()


def test_relevant_courses_stop_at_completed(graph: CourseGraph) -> None:
    relevant = get_relevant_courses(graph, 'CSC236H1', {'CSC148H1'})
    assert relevant == {'CSC236H1', 'CSC148H1', 'CSC165H1'}


def test_eligible_relevant_excludes_unrelated(graph: CourseGraph) -> None:
    assert eligible_relevant_courses(graph, set(), 'CSC236H1') == {'CSC108H1', 'CSC165H1'}


def test_search_ranks_code_prefix_first() -> None:
    g = make_graph({'MAT137Y1': None, 'CSC110Y1': None})
    g.vertices['MAT137Y1'].name = 'Calculus for CSC students'
    assert search_courses(g, 'csc') == ['CSC110Y1', 'MAT137Y1']
