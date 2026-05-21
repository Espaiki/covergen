"""Cover content model. All validation lives here — no caller should re-check."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Accepted academic prefixes for teacher_name. Frozen for thread-safety and intent.
VALID_TEACHER_PREFIXES: Final[frozenset[str]] = frozenset({
    "Prof.", "Lic.", "Dr.", "Dra.", "Ing.", "Mg.", "Mgs.", "PhD.",
})

# 'YYYY-YYYY' — anchored both sides to reject leading/trailing garbage.
_SCHOOL_YEAR_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{4})-(\d{4})$")


class CoverData(BaseModel):
    """
    Strict content payload for a printable cover.

    Validation contract:
      - All strings are stripped of surrounding whitespace.
      - Empty strings are rejected at construction time.
      - teacher_name MUST start with an accepted academic prefix.
      - school_year MUST match 'YYYY-YYYY' with consecutive years.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    institution_name: str = Field(min_length=2, max_length=200)
    subject_name: str = Field(min_length=2, max_length=120)
    teacher_name: str = Field(min_length=3, max_length=120)
    student_name: str = Field(min_length=3, max_length=120)
    grade_course: str = Field(min_length=1, max_length=80)
    school_year: str = Field(min_length=9, max_length=9)

    @field_validator("teacher_name")
    @classmethod
    def _validate_teacher_prefix(cls, v: str) -> str:
        tokens = v.split()
        if len(tokens) < 2:
            raise ValueError("teacher_name must include a prefix AND a name")
        prefix = tokens[0]
        if prefix not in VALID_TEACHER_PREFIXES:
            raise ValueError(
                f"teacher_name must start with one of "
                f"{sorted(VALID_TEACHER_PREFIXES)}; got '{prefix}'"
            )
        return v

    @field_validator("school_year")
    @classmethod
    def _validate_school_year(cls, v: str) -> str:
        match = _SCHOOL_YEAR_RE.match(v)
        if not match:
            raise ValueError(
                "school_year must match 'YYYY-YYYY' (e.g. '2026-2027')"
            )
        start, end = int(match.group(1)), int(match.group(2))
        if end != start + 1:
            raise ValueError(
                f"school_year must be two consecutive years; got {start}-{end}"
            )
        current = datetime.now().year
        if not (2000 <= start <= current + 5):
            raise ValueError(
                f"school_year start ({start}) outside plausible range "
                f"[2000, {current + 5}]"
            )
        return v
