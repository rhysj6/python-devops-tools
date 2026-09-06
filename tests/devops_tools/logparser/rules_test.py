import re

import pytest

from devops_tools.logparser.rules import LineCheck, MatchRule


def test_linecheck_validate_handles_empty_contains() -> None:
    lc1 = LineCheck(contains="", regex="idk")
    assert lc1.contains is None

    lc2 = LineCheck(regex="idk")
    assert lc2.contains is None


def test_linecheck_validate_handles_empty_regex() -> None:
    lc1 = LineCheck(contains="idk", regex="")
    assert lc1.regex is None

    lc2 = LineCheck(contains="idk")
    assert lc2.regex is None


def test_linecheck_validate_raises_on_blank_values() -> None:
    with pytest.raises(ValueError) as error:
        LineCheck()
    assert "Both contains and regex cannot be blank" in str(error.value)


def test_linecheck_validate_raises_on_incorrect_regex() -> None:
    with pytest.raises(re.PatternError) as error:
        LineCheck(regex="[invalid(regex")
    assert "unterminated character set at position 0" in str(error.value)


@pytest.mark.parametrize(
    "lc, expected",
    [
        (LineCheck(contains="ERROR"), True),
        (LineCheck(contains="INFO"), False),
        (LineCheck(contains="ERROR", regex="ERROR:"), True),
        (LineCheck(contains="ERROR", regex="ERROR:Hi"), False),
        (LineCheck(regex="ERROR:"), True),
        (LineCheck(regex="ERROR:Hi"), False),
    ],
    ids=[
        "match_contains_only",
        "no_match_contains_only",
        "match_contains_with_regex",
        "no_match_contains_with_regex",
        "match_regex_only",
        "no_match_regex_only",
    ],
)
def test_line_check_check(lc: LineCheck, expected: bool) -> None:
    line = "ERROR: Something failed"

    result = lc.check(line)

    assert result == expected


def test_match_rule_raises_on_no_checks() -> None:
    with pytest.raises(ValueError) as error:
        MatchRule(name="failing rule", checks=[], max_lines=10)
    assert "Rule failing rule: has 0 checks" in str(error.value)


def test_match_rule_raise_on_low_max_lines() -> None:
    with pytest.raises(ValueError) as error:
        MatchRule(
            name="failing rule",
            checks=[LineCheck(contains="test"), LineCheck(contains="passing")],
            max_lines=1,
        )
    assert "Rule failing rule: max_lines is less than number of checks" in str(
        error.value
    )


def test_match_rule_validates_safely() -> None:
    MatchRule(
        name="failing rule",
        checks=[LineCheck(contains="test"), LineCheck(contains="passing")],
        max_lines=32,
    )
