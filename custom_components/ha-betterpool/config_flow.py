"""Adds config flow for Blueprint."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_pool_schema(defaults: dict) -> vol.Schema:
    """Génère le schéma de configuration avec des valeurs par défaut dynamiques."""
    return vol.Schema(
        {
            vol.Required(
                "pool_volume", default=defaults.get("pool_volume", 30)
            ): vol.Coerce(int),
            vol.Required(
                "pool_type", default=defaults.get("pool_type", "sel")
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["sel", "chlore", "brome"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="pool_type_options",
                )
            ),
            vol.Required(
                "ph_sensor", default=defaults.get("temp_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="ph",
                )
            ),
            vol.Required(
                "temp_sensor", default=defaults.get("ph_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="temperature",
                )
            ),
            vol.Optional(
                "filtration_entity",
                default=defaults.get("filtration_entity", vol.UNDEFINED),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["switch", "binary_sensor", "input_boolean"],
                )
            ),
            vol.Optional(
                "orp_sensor", default=defaults.get("orp_sensor", vol.UNDEFINED)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(
                "tac_sensor", default=defaults.get("tac_sensor", vol.UNDEFINED)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(
                "th_sensor", default=defaults.get("th_sensor", vol.UNDEFINED)
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(
                "stabilizer_sensor",
                default=defaults.get("stabilizer_sensor", vol.UNDEFINED),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        }
    )


class BetterPoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestion du flux de configuration initial."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Première étape lors de l'ajout par l'utilisateur."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=f"Piscine Onyx ({user_input['pool_volume']}m³)", data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=get_pool_schema({}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Renvoie le gestionnaire d'options."""
        return BetterPoolOptionsFlowHandler()


class BetterPoolOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Gestion du flux de modification des paramètres (Options)."""

    async def async_step_init(self, user_input=None):
        """Gère la modification des options."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, **user_input}
            )

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="", data={})

        current_settings = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=get_pool_schema(current_settings),
        )
