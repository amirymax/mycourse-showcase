import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from access import AccessState, LessonRef, can_access_lesson, trial_lock_reason

NOW = datetime(2030, 1, 10, 12, 0)
LESSONS = [
    LessonRef(1, 1, 1, 0), LessonRef(2, 1, 2, 0),
    LessonRef(3, 1, 3, 1), LessonRef(4, 1, 4, 1),
]


def state(done=(), **kw):
    return AccessState(course_id=1, lessons=LESSONS, completed_lesson_ids=frozenset(done),
                       first_block_order=0, **kw)


def test_sequential_unlock():
    s = state(done={1})
    assert can_access_lesson(s, LESSONS[0], NOW)
    assert can_access_lesson(s, LESSONS[1], NOW)
    assert not can_access_lesson(s, LESSONS[2], NOW)


def test_completed_course_opens_everything():
    assert all(can_access_lesson(state(done={1, 2, 3, 4}), l, NOW) for l in LESSONS)


def test_other_course_denied():
    assert not can_access_lesson(state(), LessonRef(9, 2, 1, 0), NOW)


def test_trial_limited_to_first_block():
    s = state(done={1, 2}, is_trial=True, trial_expires_at=NOW + timedelta(days=1))
    assert trial_lock_reason(s, LESSONS[1], NOW) is None
    assert trial_lock_reason(s, LESSONS[2], NOW) == "trial_limit"
    assert not can_access_lesson(s, LESSONS[2], NOW)


def test_trial_expired_locks_everything():
    s = state(done={1}, is_trial=True, trial_expires_at=NOW - timedelta(seconds=1))
    assert trial_lock_reason(s, LESSONS[0], NOW) == "trial_expired"
    assert not can_access_lesson(s, LESSONS[0], NOW)
