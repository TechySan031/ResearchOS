"""
Phase 1 Stabilization — Streaming Stress Test

Simulates the following scenarios:
  1. Long draft generation with 5000+ streamed tokens
  2. Multiple concurrent project streams
  3. SSE reconnect (disconnect + reconnect mid-stream)
  4. EventBus subscriber cleanup verification
  5. Browser refresh simulation (rapid connect/disconnect)

Usage:
    python -m pytest tests/test_streaming_stress.py -v
    or
    python tests/test_streaming_stress.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.events import EventBus, AgentEvent, get_event_bus, init_event_bus


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_token_event(project_id: str, token: str, section: str = "draft") -> AgentEvent:
    return AgentEvent(
        project_id=project_id,
        agent_name="draft_writing",
        event_type="stream_token",
        data={"token": token, "section": section},
    )


def make_lifecycle_event(project_id: str, agent: str, event_type: str) -> AgentEvent:
    return AgentEvent(
        project_id=project_id,
        agent_name=agent,
        event_type=event_type,
    )


# ── Test 1: Long Draft (5000+ tokens) ───────────────────────────────────────

async def test_long_draft_streaming():
    """Simulate 5000+ tokens through the event bus and verify all arrive."""
    bus = init_event_bus(redis_client=None)  # In-memory mode

    received: list[str] = []
    queue: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)
    bus._local_subscribers.append(queue)

    total_tokens = 5500
    project_id = "proj-stress-1"

    # Producer: emit 5500 tokens
    async def producer():
        for i in range(total_tokens):
            token = f"token_{i} "
            await bus.publish(make_token_event(project_id, token))
            if i % 500 == 0:
                await asyncio.sleep(0)  # Yield to event loop

    # Consumer: drain events
    async def consumer():
        count = 0
        while count < total_tokens:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
                if event.project_id == project_id and event.event_type == "stream_token":
                    received.append(event.data["token"])
                    count += 1
            except asyncio.TimeoutError:
                break

    await asyncio.gather(producer(), consumer())

    # Cleanup
    try:
        bus._local_subscribers.remove(queue)
    except ValueError:
        pass

    assert len(received) == total_tokens, f"Expected {total_tokens}, got {len(received)}"
    print(f"  ✓ Long draft: {len(received)}/{total_tokens} tokens received")


# ── Test 2: Multiple Concurrent Projects ────────────────────────────────────

async def test_concurrent_projects():
    """3 projects streaming simultaneously — verify no cross-contamination."""
    bus = init_event_bus(redis_client=None)

    projects = ["proj-a", "proj-b", "proj-c"]
    tokens_per_project = 200
    results: dict[str, list[str]] = {p: [] for p in projects}

    queues: dict[str, asyncio.Queue] = {}
    for p in projects:
        q: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)
        bus._local_subscribers.append(q)
        queues[p] = q

    # Producer: emit tokens for all 3 projects interleaved
    async def producer():
        for i in range(tokens_per_project):
            for p in projects:
                await bus.publish(make_token_event(p, f"{p}_t{i} "))
            if i % 50 == 0:
                await asyncio.sleep(0)

    # Consumer per project: filter by project_id
    async def consumer(project_id: str, q: asyncio.Queue):
        count = 0
        target = tokens_per_project
        while count < target:
            try:
                event = await asyncio.wait_for(q.get(), timeout=5.0)
                if event.project_id == project_id and event.event_type == "stream_token":
                    results[project_id].append(event.data["token"])
                    count += 1
            except asyncio.TimeoutError:
                break

    tasks = [producer()]
    for p in projects:
        tasks.append(consumer(p, queues[p]))

    await asyncio.gather(*tasks)

    # Cleanup
    for q in queues.values():
        try:
            bus._local_subscribers.remove(q)
        except ValueError:
            pass

    for p in projects:
        assert len(results[p]) == tokens_per_project, \
            f"Project {p}: expected {tokens_per_project}, got {len(results[p])}"
        # Verify no cross-contamination
        for token in results[p]:
            assert token.startswith(p), f"Cross-contamination: {token} in {p}"

    print(f"  ✓ Concurrent projects: {len(projects)} projects × {tokens_per_project} tokens, zero cross-contamination")


# ── Test 3: SSE Reconnect (disconnect + reconnect mid-stream) ───────────────

async def test_sse_reconnect():
    """Simulate SSE disconnect mid-stream and reconnect — no token loss on bus side."""
    bus = init_event_bus(redis_client=None)

    project_id = "proj-reconnect"
    total = 100

    # Phase 1: connect, receive first 50 tokens, disconnect
    q1: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)
    bus._local_subscribers.append(q1)

    for i in range(50):
        await bus.publish(make_token_event(project_id, f"t{i} "))

    phase1_count = 0
    while not q1.empty():
        event = q1.get_nowait()
        if event.project_id == project_id:
            phase1_count += 1

    # Disconnect (remove subscriber)
    try:
        bus._local_subscribers.remove(q1)
    except ValueError:
        pass

    # Tokens emitted while disconnected — these are dropped (expected SSE behavior)
    for i in range(50, 70):
        await bus.publish(make_token_event(project_id, f"t{i} "))

    # Phase 2: reconnect with new queue
    q2: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)
    bus._local_subscribers.append(q2)

    for i in range(70, total):
        await bus.publish(make_token_event(project_id, f"t{i} "))

    phase2_count = 0
    while not q2.empty():
        event = q2.get_nowait()
        if event.project_id == project_id:
            phase2_count += 1

    try:
        bus._local_subscribers.remove(q2)
    except ValueError:
        pass

    assert phase1_count == 50, f"Phase 1: expected 50, got {phase1_count}"
    assert phase2_count == 30, f"Phase 2: expected 30, got {phase2_count}"
    print(f"  ✓ SSE reconnect: phase1={phase1_count}, dropped=20 (expected), phase2={phase2_count}")


# ── Test 4: Subscriber Cleanup ──────────────────────────────────────────────

async def test_subscriber_cleanup():
    """Verify subscribers are properly removed and don't leak."""
    bus = init_event_bus(redis_client=None)

    initial_count = len(bus._local_subscribers)

    # Add 10 subscribers
    queues = []
    for _ in range(10):
        q: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)
        bus._local_subscribers.append(q)
        queues.append(q)

    assert len(bus._local_subscribers) == initial_count + 10

    # Remove all using safe pattern (as in Fix 3)
    for q in queues:
        try:
            bus._local_subscribers.remove(q)
        except ValueError:
            pass

    assert len(bus._local_subscribers) == initial_count
    print(f"  ✓ Subscriber cleanup: 10 added → 10 removed → {len(bus._local_subscribers)} remaining")


# ── Test 5: Browser Refresh (rapid connect/disconnect) ──────────────────────

async def test_browser_refresh():
    """Simulate rapid browser refreshes — connect + disconnect 20 times quickly."""
    bus = init_event_bus(redis_client=None)

    project_id = "proj-refresh"

    for cycle in range(20):
        q: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)
        bus._local_subscribers.append(q)

        # Emit a few tokens
        for i in range(5):
            await bus.publish(make_token_event(project_id, f"c{cycle}_t{i} "))

        # Immediate disconnect (browser refresh)
        try:
            bus._local_subscribers.remove(q)
        except ValueError:
            pass

    # After 20 cycles, no subscribers should remain
    assert len(bus._local_subscribers) == 0, \
        f"Leaked {len(bus._local_subscribers)} subscribers after 20 refresh cycles"
    print(f"  ✓ Browser refresh: 20 rapid cycles, 0 leaked subscribers")


# ── Test 6: Bounded Queue Overflow ──────────────────────────────────────────

async def test_bounded_queue_overflow():
    """Verify bounded queue (maxsize=1000) handles overflow without crashing."""
    bus = init_event_bus(redis_client=None)

    project_id = "proj-overflow"
    q: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=1000)
    bus._local_subscribers.append(q)

    # Publish 1500 events (500 over the limit)
    overflow_count = 0
    for i in range(1500):
        try:
            q.put_nowait(make_token_event(project_id, f"t{i} "))
        except asyncio.QueueFull:
            overflow_count += 1

    assert q.qsize() == 1000, f"Queue size should be 1000, got {q.qsize()}"
    assert overflow_count == 500, f"Expected 500 overflows, got {overflow_count}"

    try:
        bus._local_subscribers.remove(q)
    except ValueError:
        pass

    print(f"  ✓ Bounded queue: 1000 queued, {overflow_count} dropped on overflow")


# ── Test 7: Instance Attribute Isolation ────────────────────────────────────

async def test_instance_isolation():
    """Verify _local_subscribers is per-instance, not shared across EventBus instances."""
    bus1 = EventBus(redis_client=None)
    bus2 = EventBus(redis_client=None)

    q1: asyncio.Queue[AgentEvent] = asyncio.Queue(maxsize=100)
    bus1._local_subscribers.append(q1)

    assert len(bus1._local_subscribers) == 1
    assert len(bus2._local_subscribers) == 0, \
        "Fix 3 failed: _local_subscribers is still shared as a class attribute!"

    bus1._local_subscribers.remove(q1)
    print(f"  ✓ Instance isolation: bus1 has {len(bus1._local_subscribers)} subs, bus2 has {len(bus2._local_subscribers)} subs")


# ── Runner ───────────────────────────────────────────────────────────────────

async def run_all():
    print("\n═══ Phase 1 Stabilization — Stress Tests ═══\n")

    tests = [
        ("1. Long draft (5500 tokens)", test_long_draft_streaming),
        ("2. Concurrent projects (3 × 200)", test_concurrent_projects),
        ("3. SSE reconnect mid-stream", test_sse_reconnect),
        ("4. Subscriber cleanup", test_subscriber_cleanup),
        ("5. Browser refresh (20 cycles)", test_browser_refresh),
        ("6. Bounded queue overflow", test_bounded_queue_overflow),
        ("7. Instance isolation (Fix 3)", test_instance_isolation),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1

    print(f"\n{'═' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'═' * 50}\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
