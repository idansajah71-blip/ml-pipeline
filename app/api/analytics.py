"""
Lightweight funnel / drop-off analytics endpoint.

Events are stored in an in-memory ring-buffer (no DB required).
A read endpoint lets you inspect where users are dropping off.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict, deque

from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# ── In-memory store ──────────────────────────────────────────────────────────
MAX_EVENTS = 10_000  # ring buffer cap
_events: deque = deque(maxlen=MAX_EVENTS)


class FunnelEvent(BaseModel):
    funnel: str
    step: str
    action: str          # "enter" | "complete" | "abandon"
    duration_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class FunnelSummary(BaseModel):
    funnel: str
    step: str
    enters: int
    completes: int
    abandons: int
    completion_rate: float   # completes / enters (0-1)
    avg_duration_ms: Optional[float]


@router.post("/funnel", status_code=204)
async def record_funnel_event(
    event: FunnelEvent,
    current_user: User = Depends(get_current_active_user),
):
    """Record a single funnel step event. Fire-and-forget from the frontend."""
    _events.append({
        **event.dict(),
        "user_id": str(current_user.id),
        "ts": datetime.utcnow().isoformat(),
    })
    # 204 No Content — frontend doesn't wait for a response body


@router.get("/funnel/{funnel_name}", response_model=List[FunnelSummary])
async def get_funnel_report(
    funnel_name: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Aggregate step-level stats for a named funnel.
    Returns steps ordered by the average time they were first entered.
    """
    # Bucket events by step
    enters: Dict[str, int] = defaultdict(int)
    completes: Dict[str, int] = defaultdict(int)
    abandons: Dict[str, int] = defaultdict(int)
    durations: Dict[str, List[int]] = defaultdict(list)
    first_seen: Dict[str, str] = {}  # step -> earliest ts (for ordering)

    for ev in _events:
        if ev.get("funnel") != funnel_name:
            continue
        step = ev["step"]
        action = ev["action"]
        if action == "enter":
            enters[step] += 1
            if step not in first_seen:
                first_seen[step] = ev["ts"]
        elif action == "complete":
            completes[step] += 1
            if ev.get("duration_ms") is not None:
                durations[step].append(ev["duration_ms"])
        elif action == "abandon":
            abandons[step] += 1

    all_steps = sorted(first_seen.keys(), key=lambda s: first_seen[s])

    result = []
    for step in all_steps:
        e = enters[step]
        c = completes[step]
        a = abandons[step]
        dur_list = durations[step]
        result.append(FunnelSummary(
            funnel=funnel_name,
            step=step,
            enters=e,
            completes=c,
            abandons=a,
            completion_rate=round(c / e, 3) if e > 0 else 0.0,
            avg_duration_ms=round(sum(dur_list) / len(dur_list)) if dur_list else None,
        ))

    return result


@router.get("/funnel", response_model=List[str])
async def list_funnels(current_user: User = Depends(get_current_active_user)):
    """List all distinct funnel names that have been tracked."""
    seen = set()
    for ev in _events:
        if "funnel" in ev:
            seen.add(ev["funnel"])
    return sorted(seen)
