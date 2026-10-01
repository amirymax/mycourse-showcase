# trial-access — sequential unlocking and a time-limited trial

The generic part of the platform's lesson-access logic. Payments, pricing and enrollment
creation are deliberately **not** part of this module.

## What it decides

For a learner and a lesson: *can they open it, and if not, why?*

- Lessons unlock **sequentially** (first uncompleted lesson and everything before it).
- A **trial** learner is limited to the first block, and everything locks when the trial
  window ends.
- `trial_lock_reason()` returns `"trial_expired"` / `"trial_limit"` / `None` instead of a bare
  boolean, so the frontend can show the right call-to-action (upsell vs. "finish the previous
  lesson").

## Key decisions

- **Pure functions over dataclasses.** The production version queries the ORM inside the
  rules; extracting them into `AccessState` made them trivially testable (no DB, no
  fixtures) and removed N+1 queries from the rule path.
- **Reason codes over booleans** — one source of truth for both the API response and the UI.
- **Expiry beats scope.** An expired trial locks even already-completed content; the rule
  order in `trial_lock_reason` encodes that on purpose.

## Wiring it to Django

```python
def build_state(student) -> AccessState:
    enr = Enrollment.objects.select_related("course").get(student=student)
    lessons = [LessonRef(l.id, l.course_id, l.order, l.block.order if l.block_id else None)
               for l in enr.course.lessons.select_related("block")]
    done = frozenset(LessonProgress.objects.filter(student=student, completed=True)
                     .values_list("lesson_id", flat=True))
    return AccessState(enr.course_id, lessons, done, enr.is_trial, enr.trial_expires_at,
                       first_block_order=min((l.block_order for l in lessons if l.block_order is not None), default=None))
```

## Tests

```bash
pip install -r requirements.txt && pytest
```
