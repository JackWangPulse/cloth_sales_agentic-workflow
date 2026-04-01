from __future__ import annotations

import contextvars
import functools
import inspect
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Iterator

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from langsmith.run_trees import RunTree
except ImportError:  # pragma: no cover
    RunTree = None  # type: ignore[assignment]


_current_run_var: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "langsmith_current_run",
    default=None,
)


@dataclass
class TraceHandle:
    run: Any | None = None
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def set_outputs(self, outputs: dict[str, Any] | None) -> None:
        if outputs:
            self.outputs.update(outputs)

    def add_metadata(self, metadata: dict[str, Any] | None) -> None:
        if metadata:
            self.metadata.update(metadata)


def langsmith_enabled() -> bool:
    settings = get_settings()
    return bool(
        RunTree is not None
        and settings.langsmith_tracing
        and settings.langsmith_api_key
        and settings.langsmith_project
    )


def _build_extra(
    metadata: dict[str, Any] | None,
    tags: list[str] | None,
) -> dict[str, Any] | None:
    extra: dict[str, Any] = {}
    if metadata:
        extra["metadata"] = metadata
    if tags:
        extra["tags"] = tags
    return extra or None


def _create_run(
    *,
    name: str,
    run_type: str,
    inputs: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    tags: list[str] | None,
) -> Any | None:
    if not langsmith_enabled():
        return None

    settings = get_settings()
    parent_run = _current_run_var.get()
    safe_inputs = inputs or {}
    extra = _build_extra(metadata, tags)

    try:
        if parent_run is not None:
            run = parent_run.create_child(
                name=name,
                run_type=run_type,
                inputs=safe_inputs,
                extra=extra,
            )
        else:
            run = RunTree(
                name=name,
                run_type=run_type,
                inputs=safe_inputs,
                project_name=settings.langsmith_project,
                extra=extra,
            )
        run.post()
        return run
    except Exception as exc:  # pragma: no cover
        logger.warning("[LANGSMITH] Failed to create run '%s': %s", name, exc)
        return None


def _finalize_run(handle: TraceHandle) -> None:
    run = handle.run
    if run is None:
        return

    try:
        if handle.metadata:
            existing_extra = getattr(run, "extra", {}) or {}
            existing_metadata = existing_extra.get("metadata", {}) or {}
            existing_metadata.update(handle.metadata)
            existing_extra["metadata"] = existing_metadata
            run.extra = existing_extra
    except Exception:
        pass

    try:
        if handle.error:
            setattr(run, "error", handle.error)
        run.end(outputs=handle.outputs or None)
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "[LANGSMITH] Failed to end run '%s': %s",
            getattr(run, "name", "?"),
            exc,
        )
    finally:
        try:
            run.patch()
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "[LANGSMITH] Failed to patch run '%s': %s",
                getattr(run, "name", "?"),
                exc,
            )


@contextmanager
def trace_span(
    name: str,
    *,
    run_type: str = "chain",
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[TraceHandle]:
    run = _create_run(
        name=name,
        run_type=run_type,
        inputs=inputs,
        metadata=metadata,
        tags=tags,
    )
    handle = TraceHandle(run=run)
    token = _current_run_var.set(run) if run is not None else None
    try:
        yield handle
    except Exception as exc:
        handle.error = str(exc)
        handle.set_outputs({"error": str(exc), "error_type": type(exc).__name__})
        raise
    finally:
        if token is not None:
            _current_run_var.reset(token)
        _finalize_run(handle)


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in list(value.items())[:20]}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(v) for v in list(value)[:20]]
    for attr in ("sku", "user_id", "guide_id", "name", "intent_level"):
        if hasattr(value, attr):
            return {
                "type": type(value).__name__,
                attr: getattr(value, attr, None),
            }
    return {"type": type(value).__name__, "repr": repr(value)[:200]}


def _build_inputs(
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    try:
        bound = inspect.signature(fn).bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return {
            key: _serialize_value(value)
            for key, value in bound.arguments.items()
            if key not in {"self", "cls"}
        }
    except Exception:
        return {"args": _serialize_value(args), "kwargs": _serialize_value(kwargs)}


def traceable_async(
    name: str,
    *,
    run_type: str = "chain",
    tags: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_span(
                name,
                run_type=run_type,
                inputs=_build_inputs(fn, args, kwargs),
                tags=tags,
            ) as trace:
                result = await fn(*args, **kwargs)
                trace.set_outputs({"result_type": type(result).__name__})
                return result

        return wrapper

    return decorator


def traceable_sync(
    name: str,
    *,
    run_type: str = "chain",
    tags: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_span(
                name,
                run_type=run_type,
                inputs=_build_inputs(fn, args, kwargs),
                tags=tags,
            ) as trace:
                result = fn(*args, **kwargs)
                trace.set_outputs({"result_type": type(result).__name__})
                return result

        return wrapper

    return decorator


def traceable_async_generator(
    name: str,
    *,
    run_type: str = "chain",
    tags: list[str] | None = None,
) -> Callable[[Callable[..., AsyncGenerator[Any, None]]], Callable[..., AsyncGenerator[Any, None]]]:
    def decorator(
        fn: Callable[..., AsyncGenerator[Any, None]]
    ) -> Callable[..., AsyncGenerator[Any, None]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
            with trace_span(
                name,
                run_type=run_type,
                inputs=_build_inputs(fn, args, kwargs),
                tags=tags,
            ) as trace:
                item_count = 0
                async for item in fn(*args, **kwargs):
                    item_count += 1
                    yield item
                trace.set_outputs({"item_count": item_count})

        return wrapper

    return decorator
