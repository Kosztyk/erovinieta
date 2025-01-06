"""Coordinator pentru integrarea Erovinieta."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, CONF_ISTORIC_TRANZACTII, ISTORIC_TRANZACTII_DEFAULT, URL_TRECERI_POD
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
        self.vehicule_data = []  # Inițializăm vehiculele ca listă goală

    async def _async_update_data(self) -> dict:
        """Actualizează datele periodic."""
        _LOGGER.debug("Începem actualizarea datelor în coordinator...")

        try:
            # Cereri către API pentru diferite seturi de date
            user_data = await self.hass.async_add_executor_job(self.api.get_user_data)
            paginated_data = await self.hass.async_add_executor_job(self.api.get_paginated_data)
            countries_data = await self.hass.async_add_executor_job(self.api.get_countries)

            # Adăugăm vehiculele din datele paginate
            self.vehicule_data = [vehicul.get("entity", {}) for vehicul in paginated_data.get("view", [])]
            treceri_pod_data = {"detectionList": []}  # Setăm o valoare implicită goală

            # Iterăm prin vehicule pentru a prelua trecerile de pod
            for vehicul in self.vehicule_data:
                vin = vehicul.get("vin", "Necunoscut")
                plate_no = vehicul.get("plateNo", "Necunoscut")
                certificate_series = vehicul.get("certificateSeries", "Necunoscut")

                if not vin or not plate_no or not certificate_series:
                    _LOGGER.warning(
                        "Date incomplete pentru restanțele trecerilor de pod: VIN=%s, PlateNo=%s, CertificateSeries=%s",
                        vin, plate_no, certificate_series
                    )
                    continue  # Sarim acest vehicul

                try:
                    # Cerere pentru treceri de pod pentru acest vehicul
                    vehicul_treceri = await self.hass.async_add_executor_job(
                        self.api.get_treceri_pod,
                        vin,
                        plate_no,
                        certificate_series,
                    )
                    # Verificăm dacă există date valide înainte de a extinde lista
                    if "detectionList" in vehicul_treceri:
                        treceri_pod_data["detectionList"].extend(vehicul_treceri.get("detectionList", []))
                        _LOGGER.debug(
                            "Restanțe treceri pod pentru vehicul %s obținute cu succes.", plate_no
                        )
                    else:
                        _LOGGER.info(
                            "Nu s-au găsit restanțe pentru trecerile de pod pentru vehiculul %s.", plate_no
                        )
                except Exception as e:
                    _LOGGER.error(
                        "Eroare la obținerea restanțelor trecerilor de pod pentru vehiculul %s: %s",
                        plate_no, e
                    )

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
                "detectionList": treceri_pod_data.get("detectionList", []),  # Lista trecerilor de pod
            }

            # Stocăm datele consolidate pentru utilizare ulterioară
            self.data = new_data

            _LOGGER.info("Datele au fost actualizate cu succes.")
            return self.data

        except Exception as e:
            _LOGGER.error("Eroare la actualizarea datelor: %s", e)
            raise UpdateFailed(f"Eroare la actualizarea datelor: {e}")
