"""Coordinateur de mise à jour des données pour Better Pool."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import homeassistant.util.dt as dt_util
from homeassistant.components.recorder import history
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .data import (
    calculate_active_chlorine_percentage,
    calculate_chlorine_status,
    calculate_corrected_tac,
    calculate_filtration_time,
    calculate_lsi,
    calculate_ph_dosage,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class BetterPoolDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Classe pour centraliser la récupération et le calcul des données de la piscine."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise le coordinateur."""
        self.entry = entry

        # Récupération de la configuration initiale
        self.pool_volume = entry.data.get("pool_volume", 30)
        self.pool_type = entry.data.get("pool_type", "chlore")
        self.ph_sensor = entry.data.get("ph_sensor")
        self.temp_sensor = entry.data.get("temp_sensor")
        self.orp_sensor = entry.data.get("orp_sensor")
        self.filtration_entity = entry.data.get("filtration_entity")

        # Capteurs physiques optionnels s'ils existent
        self.tac_sensor = entry.data.get("tac_sensor")
        self.th_sensor = entry.data.get("th_sensor")
        self.stabilizer_sensor = entry.data.get("stabilizer_sensor")

        # C'EST ICI QUE ÇA CHANGE :
        # On va garder une référence directe vers nos objets de curseurs virtuels s'ils sont créés
        self.virtual_numbers: dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )

        self.data = {
            "lsi": None,
            "filtration_time": None,
            "active_chlorine": None,
            "corrected_tac": None,
            "orp": None,
            "ph": None,
            "temperature": None,
            "tac": None,
            "th": None,
            "stabilizer": None,
            "filtration_status": "unknown",
            "filtration_today": 0.0,
            "filtration_deficit": 0.0,
            "ph_dosage": 0.0,
            "chlorine_status": "unknown",
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Méthode requise par le framework (non utilisée car on pousse les données via les événements)."""
        return self.data

    def start_listening(self) -> None:
        """S'abonne aux changements d'états des vrais capteurs uniquement."""
        entities_to_track = [self.ph_sensor, self.temp_sensor]
        if self.orp_sensor:
            entities_to_track.append(self.orp_sensor)
        if self.tac_sensor:
            entities_to_track.append(self.tac_sensor)
        if self.th_sensor:
            entities_to_track.append(self.th_sensor)
        if self.stabilizer_sensor:
            entities_to_track.append(self.stabilizer_sensor)
        if self.filtration_entity:
            entities_to_track.append(self.filtration_entity)

        @callback
        def _async_handle_state_change(event: Event) -> None:
            self.recalculate_pool_metrics()

        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [e for e in entities_to_track if e is not None],
                _async_handle_state_change,
            )
        )

        self.recalculate_pool_metrics()

    def _get_state_value(self, entity_id: str | None) -> float | None:
        """Récupère et convertit la valeur numérique d'une entité dans HA."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return float(state.state)
            except ValueError:
                _LOGGER.warning(
                    "Impossible de convertir l'état de %s (%s) en float",
                    entity_id,
                    state.state,
                )
        return None

    async def _async_get_filtration_duration_today(self) -> float:
        """Calcule le temps cumulé de filtration aujourd'hui depuis minuit (en heures)."""
        if not self.filtration_entity:
            return 0.0

        now = dt_util.now()
        start_time = dt_util.start_of_local_day(now)

        state_changes = await self.hass.async_add_executor_job(
            history.get_significant_states,
            self.hass,
            start_time,
            now,
            [self.filtration_entity],
        )

        entity_states = state_changes.get(self.filtration_entity, [])
        if not entity_states:
            current_state = self.hass.states.get(self.filtration_entity)
            if current_state and current_state.state in ("on", "active"):
                return round((now - start_time).total_seconds() / 3600.0, 1)
            return 0.0

        total_seconds = 0.0
        last_state = None
        last_changed = start_time

        first_state = entity_states[0]
        last_state = "on" if first_state.state not in ("on", "active") else "off"

        for state in entity_states:
            current_state_val = "on" if state.state in ("on", "active") else "off"
            state_time = state.last_changed

            if last_state == "on":
                total_seconds += (state_time - last_changed).total_seconds()

            last_state = current_state_val
            last_changed = state_time

        if last_state == "on":
            total_seconds += (now - last_changed).total_seconds()

        return round(total_seconds / 3600.0, 1)

    def recalculate_pool_metrics(self) -> None:
        """Récupère l'ensemble des valeurs en temps réel et exécute notre labo de calculs."""

        ph = self._get_state_value(self.ph_sensor)
        temp = self._get_state_value(self.temp_sensor)
        orp = self._get_state_value(self.orp_sensor) if self.orp_sensor else None

        if self.tac_sensor:
            tac = self._get_state_value(self.tac_sensor)
        else:
            virtual_tac = self.virtual_numbers.get("tac")
            tac = virtual_tac.native_value if virtual_tac else None

        if self.th_sensor:
            th = self._get_state_value(self.th_sensor)
        else:
            virtual_th = self.virtual_numbers.get("th")
            th = virtual_th.native_value if virtual_th else None

        if self.stabilizer_sensor:
            stabilizer = self._get_state_value(self.stabilizer_sensor)
        else:
            virtual_stab = self.virtual_numbers.get("stabilizer")
            stabilizer = virtual_stab.native_value if virtual_stab else None

        if tac is not None:
            self.data["corrected_tac"] = calculate_corrected_tac(tac, stabilizer)
        else:
            self.data["corrected_tac"] = None

        self.data["ph"] = ph
        self.data["temperature"] = temp
        self.data["tac"] = tac
        self.data["th"] = th
        self.data["stabilizer"] = stabilizer
        self.data["orp"] = orp

        if ph is not None and temp is not None:
            self.data["active_chlorine"] = calculate_active_chlorine_percentage(
                ph, temp
            )
            self.data["filtration_time"] = calculate_filtration_time(temp)

            if tac is not None and th is not None:
                self.data["lsi"] = calculate_lsi(
                    ph, temp, th, tac, self.pool_type, stabilizer
                )
            else:
                self.data["lsi"] = None
        else:
            self.data["active_chlorine"] = None
            self.data["filtration_time"] = None
            self.data["lsi"] = None

        filtration_status = "unknown"
        if self.filtration_entity:
            state = self.hass.states.get(self.filtration_entity)
            if state:
                if state.state in ("on", "active"):
                    filtration_status = "En cours"
                else:
                    filtration_status = "Arrêtée"

        self.data["filtration_status"] = filtration_status

        if ph is not None:
            self.data["ph_dosage"] = calculate_ph_dosage(
                ph, self.pool_volume, self.pool_type
            )
        else:
            self.data["ph_dosage"] = 0.0

        self.data["chlorine_status"] = calculate_chlorine_status(orp)

        _LOGGER.debug("Nouvelles données calculées : %s", self.data)

        async def _async_load_history() -> None:
            try:
                self.data[
                    "filtration_today"
                ] = await self._async_get_filtration_duration_today()
            except Exception as err:
                _LOGGER.error(
                    "Erreur lors de la récupération de l'historique : %s", err
                )
                self.data["filtration_today"] = 0.0

            rec_time = self.data["filtration_time"]
            today_time = self.data["filtration_today"]
            if rec_time is not None:
                self.data["filtration_deficit"] = max(
                    0.0, round(rec_time - today_time, 1)
                )
            else:
                self.data["filtration_deficit"] = 0.0

            self.async_set_updated_data(self.data)

        self.hass.async_create_task(_async_load_history())
