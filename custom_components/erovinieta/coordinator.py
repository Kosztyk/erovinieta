"""Coordinator pentru integrarea Erovinieta."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT
from .api_manager import ErovinietaAPI

_LOGGER = logging.getLogger(__name__)

class ErovinietaCoordinator(DataUpdateCoordinator):
    """Coordinator pentru gestionarea datelor din API-ul Erovinieta."""

    def __init__(self, hass: HomeAssistant, api: ErovinietaAPI, update_interval=DEFAULT_UPDATE_INTERVAL, istoricul_tranzactiilor=ISTORIC_TRANZACTII_DEFAULT):
        """Inițializează coordinatorul."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.data = {}  # `self.data` va fi populat de `_async_update_data()`
        self.istoricul_tranzactiilor = istoricul_tranzactiilor  # Ani specificați de utilizator

    async def _async_update_data(self) -> dict:
        """Actualizează datele periodic."""
        _LOGGER.debug("Începem actualizarea datelor în coordinator...")

        try:
            # Cereri către API pentru diferite seturi de date
            user_data = await self.hass.async_add_executor_job(self.api.get_user_data)
            paginated_data = await self.hass.async_add_executor_job(self.api.get_paginated_data)
            countries_data = await self.hass.async_add_executor_job(self.api.get_countries)

            # Calculăm intervalul de timp pentru tranzacții (în funcție de ani)
            date_from = int((datetime.now() - timedelta(days=self.istoricul_tranzactiilor * 365)).timestamp() * 1000)
            date_to = int(datetime.now().timestamp() * 1000)

            _LOGGER.debug(
                "Interval tranzacții: de la %s până la %s",
                datetime.fromtimestamp(date_from / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                datetime.fromtimestamp(date_to / 1000).strftime('%Y-%m-%d %H:%M:%S'),
            )

            # Obținem tranzacțiile
            transactions = await self.hass.async_add_executor_job(
                self.api.get_tranzactii, date_from, date_to
            )
            _LOGGER.debug("Tranzacții obținute: %d tranzacții", len(transactions.get("view", [])))

            # Consolidăm toate datele într-un singur obiect
            new_data = {
                "user": user_data.get("user", {}),
                "paginated_data": paginated_data,
                "countries_data": countries_data,
                "transactions": transactions.get("view", []),  # Doar lista tranzacțiilor
            }

            # Stocăm datele consolidate pentru utilizare ulterioară
            self.data = new_data

            #_LOGGER.debug("Date consolidate în coordinator.data: %s", {k: len(v) if isinstance(v, list) else 'N/A' for k, v in new_data.items()})
            _LOGGER.info("Datele au fost actualizate cu succes.")
            return self.data

        except Exception as e:
            _LOGGER.error("Eroare la actualizarea datelor: %s", e)
            raise UpdateFailed(f"Eroare la actualizarea datelor: {e}")
