"""Punctul de inițializare pentru integrarea Erovinieta."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import logging
from .const import DOMAIN
from .coordinator import ErovinietaCoordinator
from .api_manager import ErovinietaAPI

_LOGGER = logging.getLogger(__name__)

# Constante pentru integrare
PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setează integrarea folosind configuration.yaml (nu este utilizat pentru această integrare)."""
    _LOGGER.debug("Configurația YAML nu este suportată pentru integrarea Erovinieta.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setează integrarea folosind ConfigFlow."""
    _LOGGER.info("Setăm integrarea Erovinieta pentru utilizatorul %s", entry.data["username"])

    # Creează instanța API și autentifică
    api = ErovinietaAPI(entry.data["username"], entry.data["password"])
    try:
        await hass.async_add_executor_job(api.authenticate)
    except Exception as e:
        _LOGGER.error("Eroare la autentificarea utilizatorului %s: %s", entry.data["username"], e)
        return False

    # Validează intervalul de actualizare
    update_interval = entry.data.get("update_interval", 3600)
    if not isinstance(update_interval, int) or update_interval <= 0:
        _LOGGER.warning(
            "Interval de actualizare invalid (%s). Se utilizează valoarea implicită (3600).",
            update_interval,
        )
        update_interval = 3600

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

    # Configurează platformele
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

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
