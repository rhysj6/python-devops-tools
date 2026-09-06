import pytest
from pytest_mock import MockerFixture

from devops_tools.logparser.parser import CandidateGen, LogLine, ParseMatch, Parser
from devops_tools.logparser.rules import LineCheck, MatchRule

RULE_A = MatchRule(
    name="matching",
    solution="",
    max_lines=10,
    patterns=[
        LineCheck(contains="matching"),
        LineCheck(contains="matching again", maxlines=3),
    ],
)

RULE_B = MatchRule(
    name="not_matching",
    solution="",
    max_lines=10,
    patterns=[LineCheck(contains="not match"), LineCheck(contains="not match again")],
)

RULE_C = MatchRule(
    name="matching without per check max lines",
    solution="",
    max_lines=10,
    patterns=[
        LineCheck(contains="matching"),
        LineCheck(contains="matching again"),
    ],
)


def test_match_line_against_first_checks() -> None:
    p = Parser([RULE_A, RULE_B])

    matches = p._match_line_against_first_checks("matching")

    assert len(matches) == 1
    assert matches[0] == RULE_A


def _mock_parser_with_active_candidates() -> Parser:
    def __mock_active_candidate() -> CandidateGen:
        while True:
            line: LogLine = yield

            if line.content == "match":
                return ParseMatch(
                    rule=MatchRule(
                        name="test_rule", patterns=[LineCheck(contains="not match")]
                    ),
                    matched_lines=[line],
                )
            elif line.content == "don't match":
                return None

    gen = __mock_active_candidate()
    next(gen)
    parser = Parser([])
    parser._active_candidates.append(gen)
    return parser


def test_handle_active_candidates(subtests: pytest.Subtests) -> None:
    with subtests.test("successful_match"):
        parser = _mock_parser_with_active_candidates()
        line = LogLine("match", 1)
        parser._handle_active_candidates(line)

        assert len(parser.matches) == 1
        assert parser.matches[0].rule.name == "test_rule"
        assert len(parser._active_candidates) == 0

    with subtests.test("failed_match"):
        parser = _mock_parser_with_active_candidates()

        line = LogLine("don't match", 1)
        parser._handle_active_candidates(line)

        assert len(parser.matches) == 0
        assert len(parser._active_candidates) == 0

    with subtests.test("no_changes"):
        parser = _mock_parser_with_active_candidates()
        line = LogLine("don't match just yet", 1)
        parser._handle_active_candidates(line)

        assert len(parser.matches) == 0
        assert len(parser._active_candidates) == 1


def _mock_run_match_candidate(
    matched_rule: MatchRule, first_line: LogLine
) -> CandidateGen:
    yield


def test_instantiate_new_candidates_one_per_matched_rule(mocker: MockerFixture) -> None:
    p: Parser = Parser([])
    line: LogLine = LogLine("some line", 1)

    mock_factory = mocker.patch(
        "devops_tools.logparser.parser.Parser._run_match_candidate",
        side_effect=_mock_run_match_candidate,
    )

    p._instantiate_new_candidates(line, [RULE_A, RULE_B])

    assert len(p._active_candidates) == 2
    mock_factory.assert_has_calls(
        [
            mocker.call(line, RULE_A),
            mocker.call(line, RULE_B),
        ]
    )


def test_instantiate_new_candidates_not_touch_existing_candidates(
    mocker: MockerFixture,
) -> None:
    p = Parser([])
    existing: CandidateGen = _mock_run_match_candidate(RULE_A, LogLine("x", 1))
    next(existing)
    p._active_candidates.append(existing)

    mocker.patch(
        "devops_tools.logparser.parser.Parser._run_match_candidate",
        side_effect=_mock_run_match_candidate,
    )
    p._instantiate_new_candidates(LogLine("y", 2), [RULE_B])

    assert existing in p._active_candidates
    assert len(p._active_candidates) == 2


def test_instantiate_new_candidates_empty_rules(mocker: MockerFixture) -> None:
    p = Parser([])
    mock_factory = mocker.patch(
        "devops_tools.logparser.parser.Parser._run_match_candidate",
        side_effect=_mock_run_match_candidate,
    )
    p._instantiate_new_candidates(LogLine("z", 3), [])

    assert p._active_candidates == []
    mock_factory.assert_not_called()


def test_instantiate_new_candidates_instant_match(mocker: MockerFixture) -> None:
    p = Parser([])
    rule = MatchRule(
        name="single_check",
        solution="",
        max_lines=10,
        patterns=[LineCheck(contains="not match")],
    )
    mock_factory = mocker.patch(
        "devops_tools.logparser.parser.Parser._run_match_candidate",
        side_effect=_mock_run_match_candidate,
    )
    p._instantiate_new_candidates(LogLine("z", 3), [rule])

    assert len(p.matches) == 1
    assert p.matches[0].rule == rule
    mock_factory.assert_not_called()


def test_run_match_candidate_handles_match() -> None:
    lines: list[LogLine] = []
    for i in range(3):
        lines.append(LogLine("test", i + 1))
    lines.extend((
        LogLine("matching again", 6), 
        LogLine("matched", 7),
        LogLine("test", 8)))

    rule = MatchRule(
        name="test",
        solution="",
        max_lines=10,
        patterns=[
            LineCheck(contains="matching"), 
            LineCheck(contains="matching again"),
            LineCheck(contains="matched")],
    )

    p = Parser([])
    gen = p._run_match_candidate(LogLine("matching", 1), rule)
    next(gen)

    for line in lines:
        try:
            gen.send(line)
        except StopIteration as done:
            result: ParseMatch | None = done.value
            assert result is not None
            assert result.rule == rule
            assert len(result.matched_lines) == 6
            break


def test_run_match_candidate_handles_max_lines() -> None:
    p = Parser([])
    lines: list[LogLine] = []
    for i in range(8):
        lines.append(LogLine("test", i + 1))
    lines.append(LogLine("matching again", 10))

    gen = p._run_match_candidate(LogLine("matching", 1), RULE_A)
    next(gen)

    for line in lines:
        try:
            gen.send(line)
        except StopIteration as done:
            result: ParseMatch | None = done.value
            assert result is None
            break


def test_run_match_candidate_handles_per_check_max_lines() -> None:
    p = Parser([])
    lines: list[LogLine] = [
        LogLine("matching again", 2)
    ]
    for i in range(6):
        lines.append(LogLine("test", i + 2))
    lines.extend((
        LogLine("matched", 7),
        LogLine("test", 8)))

    rule = MatchRule(
        name="test",
        solution="",
        max_lines=10,
        patterns=[
            LineCheck(contains="matching"),
            LineCheck(contains="matching again"),
            LineCheck(contains="never gonna match", maxlines=3)],
    )

    gen = p._run_match_candidate(LogLine("matching", 1), rule)
    next(gen)

    for line in lines:
        try:
            gen.send(line)
        except StopIteration as done:
            result: ParseMatch | None = done.value
            assert result is None
            break


def test_parse_line_handles_match() -> None:
    rule = MatchRule(
        name="matching",
        solution="",
        max_lines=10,
        patterns=[
            LineCheck(contains="matching"),
            LineCheck(contains="matched"),
        ],
    )
    p = Parser([rule], 1)

    assert p._parse_line(LogLine("matching", 1)) is False

    for i in range(3):
        assert p._parse_line(LogLine("test", i + 2)) is False
    assert p._parse_line(LogLine("matched", 5)) is True

    assert len(p.matches) == 1
    match = p.matches[0]
    assert match.rule == rule
    assert len(match.matched_lines) == 5


def test_parse_line_handles_no_match() -> None:
    rule = MatchRule(
        name="matching",
        solution="",
        max_lines=10,
        patterns=[
            LineCheck(contains="matching"),
            LineCheck(contains="matched"),
        ],
    )
    p = Parser([rule], 1)

    assert p._parse_line(LogLine("matching", 1)) is False

    for i in range(3):
        assert p._parse_line(LogLine("test", i + 2)) is False
    assert p._parse_line(LogLine("matching never", 5)) is False

    assert len(p.matches) == 0


def test_parse_line_handles_max_matches() -> None:
    rule = MatchRule(
        name="matching",
        solution="",
        max_lines=10,
        patterns=[
            LineCheck(contains="matching"),
            LineCheck(contains="matched"),
        ],
    )
    p = Parser([rule], max_matches=2)

    p._parse_line(LogLine("matching", 1))
    assert p._parse_line(LogLine("matched", 2)) is False

    p._parse_line(LogLine("matching", 3))
    assert p._parse_line(LogLine("matched", 4)) is True
    assert len(p.matches) == 2


def test_parse() -> None:
    rule = MatchRule(
        name="matching",
        solution="",
        max_lines=10,
        patterns=[
            LineCheck(contains="matching"),
            LineCheck(contains="matched"),
        ],
    )
    wrong_rule = MatchRule(
        name="wrong",
        solution="",
        max_lines=10,
        patterns=[
            LineCheck(contains="nono"),
            LineCheck(contains="matched"),
        ],
    )
    p = Parser([rule, wrong_rule])
    matches = p.parse(["matching", "test", "matched"])

    assert len(matches) == 1
    assert matches[0].rule == rule

def test_parse_no_match() -> None:
    p = Parser([RULE_A, RULE_B])
    matches = p.parse(["nothing here", "still nothing"])

    assert matches == []
