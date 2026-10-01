"""Lesson access policy: sequential unlocking + a time- and scope-limited trial.

Pure functions over plain dataclasses (no ORM), so the rules are unit-testable
and easy to reason about. A thin adapter loads the data from the database and
builds an ``AccessState`` (see README).

Rules
-----
1. A learner may only open lessons of the course they are enrolled in.
2. Lessons unlock sequentially: everything up to and including the first
   uncompleted lesson is open. Once the course is complete, everything is open.
3. A trial learner is additionally restricted:
   * after the trial window ends -> everything is locked ("trial_expired");
   * before it ends -> only the first block is open ("trial_limit").
   The lock *reason* is returned (not just a bool) so the UI can show the right
   upsell instead of a generic "finish the previous lesson" message.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class LessonRef:
    id: int
    course_id: int
    order: int
    block_order: Optional[int]


@dataclass(frozen=True)
class AccessState:
    course_id: int
    lessons: Sequence[LessonRef]          # all lessons of the learner's course
    completed_lesson_ids: frozenset[int]
    is_trial: bool = False
    trial_expires_at: Optional[datetime] = None
    first_block_order: Optional[int] = None


def trial_lock_reason(state: AccessState, lesson: LessonRef, now: datetime) -> Optional[str]:
    if not state.is_trial:
        return None
    if state.trial_expires_at and now > state.trial_expires_at:
        return "trial_expired"
    if lesson.course_id != state.course_id or lesson.block_order is None:
        return None
    if state.first_block_order is None:
        return None
    return "trial_limit" if lesson.block_order > state.first_block_order else None


def next_available_lesson(state: AccessState) -> Optional[LessonRef]:
    for lesson in sorted(state.lessons, key=lambda l: l.order):
        if lesson.id not in state.completed_lesson_ids:
            return lesson
    return None  # course finished


def can_access_lesson(state: AccessState, lesson: LessonRef, now: datetime) -> bool:
    if lesson.course_id != state.course_id:
        return False
    if trial_lock_reason(state, lesson, now) is not None:
        return False
    current = next_available_lesson(state)
    if current is None:
        return True
    return lesson.order <= current.order
