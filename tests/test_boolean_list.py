"""Tests for BooleanList and CreditCondition."""
import pytest

from course_planner.boolean_list import BooleanList, CreditCondition


def test_empty_tree_is_always_satisfied() -> None:
    assert BooleanList().is_satisfied(set())
    assert BooleanList('AND', []).is_satisfied(set())


def test_nested_and_or() -> None:
    # (CSC148 OR CSC111) AND (CSC165 OR CSC240)
    tree = BooleanList('AND', [
        BooleanList('OR', ['CSC148H1', 'CSC111H1']),
        BooleanList('OR', ['CSC165H1', 'CSC240H1']),
    ])
    assert tree.is_satisfied({'CSC111H1', 'CSC240H1'})
    assert not tree.is_satisfied({'CSC111H1', 'CSC148H1'})


def test_credit_condition_inside_tree() -> None:
    # CSC207 AND 1.0 MAT credit
    tree = BooleanList('AND', ['CSC207H1', CreditCondition(1.0, 'MAT')])
    assert not tree.is_satisfied({'CSC207H1', 'MAT223H1'})
    assert tree.is_satisfied({'CSC207H1', 'MAT137Y1'})
    assert tree.is_satisfied({'CSC207H1', 'MAT223H1', 'MAT224H1'})


@pytest.mark.parametrize(('amount', 'department', 'completed', 'expected'), [
    (None, None, set(), True),
    (0.0, 'CSC', set(), True),
    (1.5, None, {'CSC110Y1', 'MAT223H1'}, True),
    (1.5, None, {'CSC110Y1'}, False),
    (1.0, 'STA', {'STA237H1', 'CSC110Y1'}, False),
])
def test_credit_condition(amount: float | None, department: str | None,
                          completed: set[str], expected: bool) -> None:
    assert CreditCondition(amount, department).credits_satisfied(completed) is expected


def test_get_all_courses_ignores_credit_conditions() -> None:
    tree = BooleanList('OR', ['CSC263H1', BooleanList('AND', ['CSC236H1', CreditCondition(4.0, None)])])
    assert tree.get_all_courses() == {'CSC263H1', 'CSC236H1'}


def test_equality_is_structural_and_ordered() -> None:
    assert BooleanList('OR', ['A', BooleanList('AND', ['B'])]) == BooleanList('OR', ['A', BooleanList('AND', ['B'])])
    assert BooleanList('OR', ['A', 'B']) != BooleanList('OR', ['B', 'A'])
    assert BooleanList('OR', ['A']) != 'not a BooleanList'


def test_unknown_item_type_raises() -> None:
    with pytest.raises(ValueError, match='Unknown item type'):
        BooleanList('AND', [42]).is_satisfied(set())
