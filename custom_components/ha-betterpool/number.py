""""""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import UnitOfRatio

from .const import DOMAIN
from .entity import BetterPoolEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BetterPoolDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

NUMBER_DESCRIPTIONS: dict[str, NumberEntityDescription] = {
    "tac": NumberEntityDescription(
        key="tac",
        name="Alcalinité (TAC)",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        native_min_value=0.0,
        native_max_value=300.0,
        native_step=10.0,
        mode=NumberMode.SLIDER,
        icon="mdi:water-percent",
    ),
    "th": NumberEntityDescription(
        key="th",
        name="Dureté (TH)",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        native_min_value=0.0,
        native_max_value=500.0,
        native_step=10.0,
        mode=NumberMode.SLIDER,
        icon="mdi:water-opacity",
    ),
    "stabilizer": NumberEntityDescription(
        key="stabilizer",
        name="Stabilisant",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        native_min_value=0.0,
        native_max_value=150.0,
        native_step=5.0,
        mode=NumberMode.SLIDER,
        icon="mdi:shield-half-full",
    ),
}

DEFAULT_VALUES = {
    "tac": 100.0,
    "th": 150.0,
    "stabilizer": 30.0,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration des curseurs Onyx Pool."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities_to_add = []

    if not coordinator.data.get("tac_sensor"):
        entities_to_add.append(
            BetterPoolVirtualNumber(coordinator, NUMBER_DESCRIPTIONS["tac"])
        )

    if not coordinator.data.get("th_sensor"):
        entities_to_add.append(
            BetterPoolVirtualNumber(coordinator, NUMBER_DESCRIPTIONS["th"])
        )

    if not coordinator.data.get("stabilizer_sensor"):
        entities_to_add.append(
            BetterPoolVirtualNumber(coordinator, NUMBER_DESCRIPTIONS["stabilizer"])
        )

    if entities_to_add:
        async_add_entities(entities_to_add)


class BetterPoolVirtualNumber(RestoreNumber, BetterPoolEntity, NumberEntity):
    """Curseur virtuel lié à notre entité de base commune."""

    def __init__(
        self,
        coordinator: BetterPoolDataUpdateCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialise le contrôleur."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}_control"
        self._current_value: float | None = None

        # SÉCURITÉ : On donne notre propre instance au coordinateur
        coordinator.virtual_numbers[description.key] = self

    async def async_added_to_hass(self) -> None:
        """Restaure l'ancienne valeur au boot."""
        await super().async_added_to_hass()

        last_number_data = await self.async_get_last_number_data()

        if last_number_data and last_number_data.native_value is not None:
            self._current_value = float(last_number_data.native_value)
        else:
            self._current_value = DEFAULT_VALUES.get(self.entity_description.key, 0.0)

        # On force un premier calcul une fois la valeur restaurée en mémoire
        self.coordinator.recalculate_pool_metrics()

    @property
    def native_value(self) -> float | None:
        """Renvoie la position actuelle du curseur."""
        return self._current_value

    async def async_set_native_value(self, value: float) -> None:
        """Appelé lorsque l'utilisateur bouge le curseur."""
        self._current_value = value
        self.async_write_ha_state()

        # On dit au coordinateur de recalculer
        self.coordinator.recalculate_pool_metrics()
