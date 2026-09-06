import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LineCheck(BaseModel):
    """
    LineCheck is a single line condition using contains and/or regex.
    """

    contains: str | None = Field(
        None,
        description="simple substring that must be present in the line for it to match",
    )

    regex: str | None = Field(
        None,
        description="regex pattern that the line must match. Optional. If both contains and regex are provided, then both conditions must be satisfied for the line to match.",
    )
    max_lines: int | None = Field(
        None,
        alias="maxlines",
        description="maximum number of lines that can be parsed since the previous check was matched",
    )

    @model_validator(mode="after")
    def __validate(self) -> Self:
        if self.contains is None and self.regex is None:
            raise ValueError("Both contains and regex cannot be blank")
        # Normalise blank string to None for easier comparisons
        if self.contains == "":
            self.contains = None
        if self.regex == "":
            self.regex = None

        if self.regex is not None:
            # Test compile regex
            re.compile(self.regex)

        return self

    def check(self, line: str) -> bool:
        """
        Checks if the supplied line matches the rule
        """
        if self.contains is not None and self.contains not in line:
            return False
        elif self.regex is not None:
            return re.match(self.regex, line) != None
        else:
            return self.contains is not None


class MatchRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(
        description="Name of the match rule, is fed back as part of the match"
    )

    checks: list[LineCheck] = Field(
        [], description="List of patterns to sequentially match on", alias="patterns"
    )
    max_lines: int = Field(
        1,
        description="Maximum number of lines to check from the first pattern that matched",
    )
    notes: str = Field(
        "", description="Notes related to the recognised match", alias="solution"
    )

    @model_validator(mode="after")
    def __validate(self) -> Self:
        if self.max_lines < len(self.checks):
            raise ValueError(
                f"Rule {self.name}: max_lines is less than number of checks, therefore this rule will never match."
            )
        if len(self.checks) == 0:
            raise ValueError(f"Rule {self.name}: has 0 checks")
        return self
