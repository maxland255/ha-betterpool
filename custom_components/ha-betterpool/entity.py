"""Classe d'entité de base pour Better Pool."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BetterPoolDataUpdateCoordinator


class BetterPoolEntity(CoordinatorEntity[BetterPoolDataUpdateCoordinator]):
    """Entité générique dont hériteront tous nos capteurs et contrôleurs."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BetterPoolDataUpdateCoordinator) -> None:
        """Initialise l'entité de base liée au coordinateur unique."""
        super().__init__(coordinator)
        self.coordinator = coordinator

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="My Pool",
            manufacturer="BetterPool Systems",
            model="Intelligence V1",
            sw_version="1.0.0",
        )
