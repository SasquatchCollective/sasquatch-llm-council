"""SSE stream buffer — converts raw backend events into structured stage results."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from .errors import classify_http_error, classify_exception


def _classify_model_error(error: Any, error_message: str | None = None) -> dict | None:
    """Convert a model error value into a structured error dict, or None if no error."""
    if not error:
        return None
    msg = error_message or (str(error) if error is not True else "Unknown provider error")
    # Try to detect HTTP status codes embedded in the message
    for code in (429, 401, 403, 404):
        if str(code) in msg:
            return classify_http_error(code, msg)
    return classify_exception(Exception(msg))


def _build_stage1_result(conversation_id: str, query: str, stage1_data: list, search: dict) -> dict:
    """Build the Stage 1 response dict from accumulated events."""
    results = []
    for item in stage1_data:
        model = item.get("model", "unknown")
        response = item.get("response")
        error = item.get("error")
        error_message = item.get("error_message")

        if error:
            error_info = _classify_model_error(error, error_message)
            results.append({"model": model, "response": None, "status": "error", "error": error_info})
        else:
            results.append({"model": model, "response": response, "status": "success"})

    succeeded = sum(1 for r in results if r["status"] == "success")
    return {
        "conversation_id": conversation_id,
        "query": query,
        "web_search": bool(search.get("search_context")),
        "search_context": search.get("search_context"),
        "results": results,
        "summary": {"total": len(results), "succeeded": succeeded, "failed": len(results) - succeeded},
    }


def _build_stage2_result(conversation_id: str, stage2_data: list, metadata: dict) -> dict:
    """Build the Stage 2 response dict from accumulated events."""
    rankings = []
    for item in stage2_data:
        model = item.get("model", "unknown")
        error = item.get("error")
        if error:
            rankings.append({
                "model": model,
                "ranking_text": None,
                "parsed_ranking": [],
                "status": "error",
                "error": _classify_model_error(error),
            })
        else:
            rankings.append({
                "model": model,
                "ranking_text": item.get("ranking"),
                "parsed_ranking": item.get("parsed_ranking", []),
                "status": "success",
            })
    return {
        "conversation_id": conversation_id,
        "label_to_model": metadata.get("label_to_model", {}),
        "rankings": rankings,
        "aggregate_rankings": metadata.get("aggregate_rankings", []),
    }


def _build_stage3_result(conversation_id: str, stage3_data: dict) -> dict:
    """Build the Stage 3 response dict."""
    error = stage3_data.get("error")
    return {
        "conversation_id": conversation_id,
        "chairman_model": stage3_data.get("model", "unknown"),
        "synthesis": stage3_data.get("response") if not error else None,
        "status": "error" if error else "success",
        "error": _classify_model_error(error, stage3_data.get("error_message")) if error else None,
    }


async def _drain_to_list(events: AsyncIterator[dict]) -> list[dict]:
    """Drain an async iterator into a plain list."""
    return [event async for event in events]


async def _events_from_list(events: list[dict]) -> AsyncIterator[dict]:
    """Wrap a list as an async generator."""
    for event in events:
        yield event


async def buffer_stage1(
    events: AsyncIterator[dict],
    conversation_id: str,
    query: str,
) -> tuple[dict, AsyncIterator[dict]]:
    """
    Consume all events from the stream, find stage1_complete, then return:
    - The structured Stage 1 result dict
    - An async iterator over the remaining events (everything after stage1_complete)

    Drains the full event list first so the iterator is not partially consumed
    when passed to buffer_stage2 or buffer_stage3.
    """
    all_events = await _drain_to_list(events)

    search_info: dict = {}
    stage1_data: list[dict] = []
    complete_index: int | None = None

    for i, event in enumerate(all_events):
        event_type = event.get("type")

        if event_type == "search_complete":
            search_info = event.get("data", {})
        elif event_type == "stage1_progress":
            # Accumulate incrementally as a fallback if stage1_complete is absent
            stage1_data.append(event.get("data", {}))
        elif event_type == "stage1_complete":
            # Authoritative full list supersedes incremental accumulation
            stage1_data = event.get("data", stage1_data)
            complete_index = i
            break
        elif event_type in ("error", "complete"):
            # Stream ended early — stop here; include this event in remaining
            complete_index = i - 1
            break

    remaining_start = (complete_index + 1) if complete_index is not None else len(all_events)
    result = _build_stage1_result(conversation_id, query, stage1_data, search_info)
    return result, _events_from_list(all_events[remaining_start:])


async def buffer_stage2(
    events: AsyncIterator[dict],
    conversation_id: str,
) -> tuple[dict, AsyncIterator[dict]]:
    """
    Consume all events from the stream, find stage2_complete, then return:
    - The structured Stage 2 result dict
    - An async iterator over the remaining events (everything after stage2_complete)
    """
    all_events = await _drain_to_list(events)

    stage2_data: list[dict] = []
    metadata: dict = {}
    complete_index: int | None = None

    for i, event in enumerate(all_events):
        event_type = event.get("type")

        if event_type == "stage2_progress":
            stage2_data.append(event.get("data", {}))
        elif event_type == "stage2_complete":
            stage2_data = event.get("data", stage2_data)
            metadata = event.get("metadata", {})
            complete_index = i
            break
        elif event_type in ("error", "complete"):
            complete_index = i - 1
            break

    remaining_start = (complete_index + 1) if complete_index is not None else len(all_events)
    result = _build_stage2_result(conversation_id, stage2_data, metadata)
    return result, _events_from_list(all_events[remaining_start:])


async def buffer_stage3(events: AsyncIterator[dict], conversation_id: str) -> dict:
    """
    Consume events until stage3_complete or error, return Stage 3 result dict.
    Does not need to return a remaining iterator — Stage 3 is the final stage.
    """
    async for event in events:
        event_type = event.get("type")
        if event_type == "stage3_complete":
            return _build_stage3_result(conversation_id, event.get("data", {}))
        elif event_type == "error":
            return {
                "conversation_id": conversation_id,
                "chairman_model": "unknown",
                "synthesis": None,
                "status": "error",
                "error": {
                    "type": "provider_error",
                    "message": event.get("message", "Unknown error"),
                    "retryable": False,
                },
            }

    # Stream ended without stage3_complete
    return {
        "conversation_id": conversation_id,
        "chairman_model": "unknown",
        "synthesis": None,
        "status": "error",
        "error": {
            "type": "provider_error",
            "message": "Stage 3 did not complete",
            "retryable": True,
        },
    }
