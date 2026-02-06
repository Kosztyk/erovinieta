"""Punctul de inițializare pentru integrarea CNAIR eRovinieta.

IMPORTANT:
Home Assistant importă pachetul integrării în event loop. Pentru a evita avertismentele
de tip "Detected blocking call to import_module", păstrăm importurile la nivel de modul
foarte ușoare (fără importuri grele/IO), iar modulele interne (api/coordinator) sunt
importate "lazy" în funcțiile async.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

# Constante pentru integrare
PLATFORMS: list[str] = ["sensor"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setează integrarea folosind configuration.yaml (nu este utilizat pentru această integrare)."""
    _LOGGER.debug("Configurația YAML nu este suportată pentru integrarea CNAIR eRovinieta.")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setează integrarea folosind ConfigFlow."""
    _LOGGER.info(
        "Configurăm integrarea CNAIR eRovinieta pentru utilizatorul %s", entry.data.get("username")
    )

    # Lazy imports to keep package import fast/non-blocking.
    from .api import ErovinietaAPI
    from .coordinator import ErovinietaCoordinator

    api = ErovinietaAPI(entry.data["username"], entry.data["password"])

    try:
        await hass.async_add_executor_job(api.authenticate)
    except Exception as e:
        _LOGGER.error("Eroare la autentificarea utilizatorului %s: %s", entry.data["username"], e)
        return False

    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = ErovinietaCoordinator(hass, api, update_interval)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.error("Eroare la actualizarea inițială a datelor: %s", e)
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as e:
        _LOGGER.error("Eroare la forward entry setups: %s", e)
        return False

    entry.async_on_unload(entry.add_update_listener(async_update_entry))
    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Aplică modificările aduse opțiunilor."""
    _LOGGER.info("Actualizăm opțiunile pentru integrarea Erovinieta.")

    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator.update_interval = timedelta(seconds=update_interval)
    _LOGGER.info("Intervalul de actualizare a fost setat la %s secunde.", update_interval)

    await coordinator.async_request_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Elimină integrarea."""
    _LOGGER.info("Eliminăm integrarea Erovinieta pentru utilizatorul %s", entry.data.get("username"))

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
