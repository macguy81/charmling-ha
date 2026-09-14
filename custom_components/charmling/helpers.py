"""One request to the Mac, turned into the right kind of error."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError

from .api import CharmlingAuthError, CharmlingConflictError, CharmlingError
from .const import DOMAIN
from .coordinator import CharmlingData


async def async_ask(data: CharmlingData, what: str, coro: Awaitable[object]) -> None:
    """Await a request to the Mac; a refused secret starts a re-pair, the rest become readable errors."""
    try:
        await coro
    except CharmlingAuthError as err:
        data.entry.async_start_reauth(data.hass)
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="unpaired",
            translation_placeholders={"name": data.name},
        ) from err
    except CharmlingConflictError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="refused",
            translation_placeholders={"name": data.name, "what": what},
        ) from err
    except CharmlingError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="unreachable",
            translation_placeholders={"name": data.name, "what": what, "error": str(err)},
        ) from err
