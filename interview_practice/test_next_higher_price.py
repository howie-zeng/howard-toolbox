import pytest

from interview_practice.next_higher_price import days_until_higher


@pytest.mark.parametrize(
    ("prices", "expected"),
    [
        ([73, 74, 75, 71, 69, 72, 76, 73], [1, 1, 4, 2, 1, 1, 0, 0]),
        ([5, 4, 3, 2, 1], [0, 0, 0, 0, 0]),
        ([2, 2, 3, 1, 3], [2, 1, 0, 1, 0]),
    ],
)
def test_examples(prices: list[int], expected: list[int]) -> None:
    assert days_until_higher(prices) == expected


@pytest.mark.parametrize(
    ("prices", "expected"),
    [
        ([10], [0]),
        ([4, 4, 4], [0, 0, 0]),
        ([1, 3, 2, 4], [1, 2, 1, 0]),
    ],
)
def test_edge_cases(prices: list[int], expected: list[int]) -> None:
    assert days_until_higher(prices) == expected
