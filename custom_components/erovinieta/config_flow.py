"""ConfigFlow și OptionsFlow pentru integrarea Erovinieta."""

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    CONF_ISTORIC_TRANZACTII,
    ISTORIC_TRANZACTII_DEFAULT, 
)
from .api_manager import ErovinietaAPI


class ErovinietaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow pentru configurarea integrării Erovinieta."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Prima etapă: introducerea datelor utilizatorului."""
        errors = {}

        if user_input is not None:
            # Testăm autentificarea
            try:
                api = ErovinietaAPI(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                await self.hass.async_add_executor_job(api.authenticate)
                return self.async_create_entry(title=f"CNAIR eRovinieta ({user_input.get(CONF_USERNAME, 'Utilizator nespecificat')})", data=user_input)
            except Exception:
                errors["base"] = "authentication_failed"

        schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
            ),
            vol.Optional(CONF_ISTORIC_TRANZACTII, default=ISTORIC_TRANZACTII_DEFAULT): vol.In([1,2,3,4,5,6,7,8,9,10]),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Returnează OptionsFlow pentru integrare."""
        return ErovinietaOptionsFlow(config_entry)


class ErovinietaOptionsFlow(config_entries.OptionsFlow):
    """OptionsFlow pentru gestionarea opțiunilor integrării Erovinieta."""

    def __init__(self, config_entry):
        """Inițializează OptionsFlow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Prima etapă: configurarea opțiunilor."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(CONF_UPDATE_INTERVAL, default=self.config_entry.options.get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            )): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
            ),
            vol.Optional(CONF_ISTORIC_TRANZACTII, default=self.config_entry.options.get(
                CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT
            )): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=10)  # Interval între 1 și 10 ani
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
