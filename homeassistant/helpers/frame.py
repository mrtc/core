"""Provide frame helper for finding the current frame context."""
import asyncio
import functools
import logging
from traceback import FrameSummary, extract_stack
from typing import Any, Callable, Tuple, TypeVar, cast

from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

CALLABLE_T = TypeVar("CALLABLE_T", bound=Callable)


def get_integration_frame() -> Tuple[FrameSummary, str, str]:
    """Return the frame, integration and integration path of the current stack frame."""
    found_frame = None

    for frame in reversed(extract_stack()):
        for path in ("custom_components/", "homeassistant/components/"):
            try:
                index = frame.filename.index(path)
                found_frame = frame
                break
            except ValueError:
                continue

        if found_frame is not None:
            break

    if found_frame is None:
        raise MissingIntegrationFrame

    start = index + len(path)
    end = found_frame.filename.index("/", start)

    integration = found_frame.filename[start:end]

    return found_frame, integration, path


class MissingIntegrationFrame(HomeAssistantError):
    """Raised when no integration is found in the frame."""


def report(what: str) -> None:
    """Report incorrect usage.

    Async friendly.
    """
    try:
        found_frame, integration, path = get_integration_frame()
    except MissingIntegrationFrame:
        # Did not source from an integration? Hard error.
        raise RuntimeError(f"Detected code that {what}. Please report this issue.")

    index = found_frame.filename.index(path)
    if path == "custom_components/":
        extra = " to the custom component author"
    else:
        extra = ""

    _LOGGER.warning(
        "Detected integration that %s. "
        "Please report issue%s for %s using this method at %s, line %s: %s",
        what,
        extra,
        integration,
        found_frame.filename[index:],
        found_frame.lineno,
        found_frame.line.strip(),
    )


def warn_use(func: CALLABLE_T, what: str) -> CALLABLE_T:
    """Mock close to avoid integrations closing our session."""
    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def report_use(*args: Any, **kwargs: Any) -> None:
            report(what)

    else:

        @functools.wraps(func)
        def report_use(*args: Any, **kwargs: Any) -> None:
            report(what)

    return cast(CALLABLE_T, report_use)
