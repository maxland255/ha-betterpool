"""Plateforme de capteurs (Sensors) pour Onyx Pool."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass, UnitOfRatio, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import BetterPoolEntity

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    "lsi": SensorEntityDescription(
        key="lsi",
        name="Indice LSI",
        icon="mdi:scale-balance",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "filtration_time": SensorEntityDescription(
        key="filtration_time",
        name="Temps de filtration recommandé",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    "active_chlorine": SensorEntityDescription(
        key="active_chlorine",
        name="Chlore actif",
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
        icon="mdi:flask-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    "volume": SensorEntityDescription(
        key="volume",
        name="Volume",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        icon="mdi:pool",
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=0,
    ),
    "corrected_tac": SensorEntityDescription(
        key="corrected_tac",
        name="Alcalinité corrigée (TAC)",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        icon="mdi:water-sync",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    "filtration_status": SensorEntityDescription(
        key="filtration_status",
        name="Statut de la filtration",
        icon="mdi:pump",
    ),
    "filtration_today": SensorEntityDescription(
        key="filtration_today",
        name="Temps de filtration aujourd'hui",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:timer-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    "filtration_deficit": SensorEntityDescription(
        key="filtration_deficit",
        name="Filtration restante requise",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:timer",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    "ph_dosage": SensorEntityDescription(
        key="ph_dosage",
        name="Ajustement du pH requis",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        icon="mdi:chemical-weapon",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "chlorine_status": SensorEntityDescription(
        key="chlorine_status",
        name="Statut du chlore (Désinfection)",
        icon="mdi:shield-check",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration dynamique de tous nos capteurs de piscine."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        BetterPoolSensor(coordinator, description)
        for description in SENSOR_TYPES.values()
    ]

    async_add_entities(entities)


class BetterPoolSensor(BetterPoolEntity, SensorEntity):
    """Capteur virtuel Onyx Pool qui lit ses données depuis le coordinateur."""

    def __init__(self, coordinator: Any, description: SensorEntityDescription) -> None:
        """Initialise le capteur avec sa description unique."""
        super().__init__(coordinator)
        self.entity_description = description

        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> float | int | str | None:
        """Renvoie l'état du capteur en le piochant directement dans les données calculées par le coordinateur."""

        if self.entity_description.key == "volume":
            return round(self.coordinator.pool_volume, 2)

        return self.coordinator.data.get(self.entity_description.key)
