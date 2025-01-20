"""Punctul de inițializare pentru integrarea CNAIR eRovinieta."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from datetime import timedelta
import logging
from .const import DOMAIN, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .coordinator import ErovinietaCoordinator
from .api import ErovinietaAPI

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

# Constante pentru integrare
PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setează integrarea folosind configuration.yaml (nu este utilizat pentru această integrare)."""
    _LOGGER.debug("Configurația YAML nu este suportată pentru integrarea CNAIR eRovinieta.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setează integrarea folosind ConfigFlow."""
    _LOGGER.info("Configurăm integrarea CNAIR eRovinieta pentru utilizatorul %s", entry.data["username"])

    # Creează instanța API și autentifică
    api = ErovinietaAPI(entry.data["username"], entry.data["password"])
    try:
        await hass.async_add_executor_job(api.authenticate)
    except Exception as e:
        _LOGGER.error("Eroare la autentificarea utilizatorului %s: %s", entry.data["username"], e)
        return False

    # Obține intervalul de actualizare
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    # Creează coordinatorul
    coordinator = ErovinietaCoordinator(hass, api, update_interval)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.error("Eroare la actualizarea inițială a datelor: %s", e)
        return False

    # Adaugă coordinatorul în Home Assistant
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    # Configurează platformele folosind `async_forward_entry_setups`
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as e:
        _LOGGER.error("Eroare la forward entry setups: %s", e)
        return False

    # Înregistrează ascultătorul pentru actualizări
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    return True

async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Aplică modificările aduse opțiunilor."""
    _LOGGER.info("Actualizăm opțiunile pentru integrarea Erovinieta.")

    # Obține noile opțiuni
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    # Actualizează intervalul în Coordinator
    coordinator: ErovinietaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator.update_interval = timedelta(seconds=update_interval)
    _LOGGER.info("Intervalul de actualizare a fost setat la %s secunde.", update_interval)

    # Forțează o actualizare
    await coordinator.async_request_refresh()

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Elimină integrarea."""
    _LOGGER.info("Eliminăm integrarea Erovinieta pentru utilizatorul %s", entry.data["username"])

    # Eliminăm platformele
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Eliminăm datele din Home Assistant
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
