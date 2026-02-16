"""Panel registration for HASH dashboard."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ICON, PANEL_TITLE, PANEL_URL_PATH

_LOGGER = logging.getLogger(__name__)

PANEL_FRONTEND_URL = f"/{DOMAIN}_panel"
PANEL_JS_URL = f"{PANEL_FRONTEND_URL}/hash-panel.js"
PANEL_WWW_PATH = Path(__file__).parent / "www"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the HASH frontend panel."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_FRONTEND_URL, str(PANEL_WWW_PATH), False)]
    )

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="hash-panel",
        frontend_url_path=PANEL_URL_PATH,
        module_url=PANEL_JS_URL,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
    )
    _LOGGER.debug("HASH panel registered")


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Unregister the HASH frontend panel."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    _LOGGER.debug("HASH panel unregistered")
