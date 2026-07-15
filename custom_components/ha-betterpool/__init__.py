"""Initialisation de l'intégration Onyx Pool."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import DOMAIN
from .coordinator import BetterPoolDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration d'Onyx Pool à partir d'une entrée de configuration."""
    _LOGGER.info("Initialisation de l'instance de piscine : %s", entry.title)

    coordinator = BetterPoolDataUpdateCoordinator(hass, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    coordinator.start_listening()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Appelé lorsque l'utilisateur supprime l'intégration."""
    _LOGGER.info("Déchargement de l'instance Onyx Pool : %s", entry.title)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
