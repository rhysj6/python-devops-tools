from collections.abc import Generator, Iterable
from dataclasses import dataclass

from .rules import MatchRule


@dataclass
class LogLine:
    content: str
    line_number: int


@dataclass
class ParseMatch:
    rule: MatchRule
    matched_lines: list[LogLine]


CandidateGen = Generator[None, LogLine, ParseMatch | None]


class Parser:
    _rules: list[MatchRule]
    _active_candidates: list[CandidateGen]
    matches: list[ParseMatch]
    _max_matches: int

    def __init__(self, rules: list[MatchRule], max_matches: int = 1) -> None:
        self._rules = rules
        self._max_matches = max_matches
        self._active_candidates = []
        self.matches = []

    def parse(self, lines: Iterable[str]) -> list[ParseMatch]:
        for line_number, content in enumerate(lines, start=1):
            log_line = LogLine(content, line_number)
            if self._parse_line(log_line):
                break
        return self.matches

    def _parse_line(self, line: LogLine) -> bool:
        """
        Takes in the next line in a log and parses it.
        Returns if the max matches has been reached.
        """

        first_check_matches = self._match_line_against_first_checks(line.content)
        self._handle_active_candidates(line)
        self._instantiate_new_candidates(line, first_check_matches)

        return len(self.matches) >= self._max_matches

    def _match_line_against_first_checks(self, line_string: str) -> list[MatchRule]:
        """
        Checks the line contents against the first check in each individual rule
        """

        matched_rules: list[MatchRule] = []

        for rule in self._rules:
            if rule.checks[0].check(line_string):
                matched_rules.append(rule)

        return matched_rules

    def _handle_active_candidates(self, line: LogLine) -> None:
        """
        Sends the next line to all active candidates and if any are inactive,
        removes them from the list, if they have a match, then add that to the matches
        """
        still_active: list[CandidateGen] = []

        for gen in self._active_candidates:
            try:
                gen.send(line)
                still_active.append(gen)
            except StopIteration as done:
                result: ParseMatch | None = done.value
                if result is not None:
                    self.matches.append(result)
        self._active_candidates = still_active

    def _instantiate_new_candidates(
        self, line: LogLine, matched_rules: list[MatchRule]
    ) -> None:
        """
        Takes the list of rules that matched the log line and instantiates the generators to recieve future lines
        """
        for rule in matched_rules:
            if len(rule.checks) == 1:
                self.matches.append(ParseMatch(rule, [line]))
            else:
                gen = self._run_match_candidate(line, rule)
                next(gen)
                self._active_candidates.append(gen)

    def _run_match_candidate(
        self, first_line: LogLine, rule: MatchRule
    ) -> CandidateGen:
        """
        Creates a generator that receives each log line, runs it against a match rule
        if there's a complete match it will return a parse match, otherwise none
        """
        rule_max_line_number: int = first_line.line_number + rule.max_lines
        check_index: int = 1
        matched_lines: list[LogLine] = [first_line]

        check_max_line_number: int = rule_max_line_number
        check_max_lines = rule.checks[check_index].max_lines
        if check_max_lines is not None:
            check_max_line_number = first_line.line_number + check_max_lines

        while True:
            line = yield
            matched_lines.append(line)

            if rule.checks[check_index].check(line.content):
                check_index += 1
                if check_index == len(rule.checks):
                    return ParseMatch(rule, matched_lines)
                check_max_lines = rule.checks[check_index].max_lines
                if check_max_lines is not None:
                    check_max_line_number = line.line_number + check_max_lines
                else:
                    check_max_line_number = rule_max_line_number
            elif line.line_number >= check_max_line_number:
                return
