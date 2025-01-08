"""Coordinator pentru integrarea CNAIR eRovinieta."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    ISTORIC_TRANZACTII_DEFAULT,
)
from .api_manager import ErovinietaAPI

_LOGGER = logging.getLogger(__name__)

def safe_get(value, default=None):
    """
    Returnează o valoare sigură, înlocuind None sau string gol cu un fallback.
    :param value: Valoarea de verificat.
    :param default: Valoarea implicită dacă 'value' este gol.
    :return: Valoarea originală sau fallback-ul.
    """
    if value is None or value == "":
        return default
    return value


class ErovinietaCoordinator(DataUpdateCoordinator):
    """Coordinator pentru gestionarea datelor din API-ul Erovinieta."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ErovinietaAPI,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        istoricul_tranzactiilor: int = ISTORIC_TRANZACTII_DEFAULT,
    ):
        """Inițializează coordinatorul Erovinieta."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.data = {}
        self.istoricul_tranzactiilor = istoricul_tranzactiilor
        self.vehicule_data: list[dict] = []

    async def _async_update_data(self) -> dict:
        """Actualizează datele periodic prin apelurile către API."""
        _LOGGER.debug("Începem actualizarea datelor în ErovinietaCoordinator...")

        try:
            # 1. Date utilizator
            try:
                user_data = await self.hass.async_add_executor_job(self.api.get_user_data)
                _LOGGER.debug("Răspuns brut get_user_data: %s", user_data)

                if not user_data or not isinstance(user_data, dict):
                    raise ValueError("Răspuns invalid sau gol pentru get_user_data")

                # Navigăm în structura răspunsului
                user_info = user_data.get("user", {})
                utilizator_info = user_info.get("utilizator", {})

                # Extragem nume și email cu fallback
                nume = safe_get(utilizator_info.get("nume"), "N/A")
                email = safe_get(utilizator_info.get("email"), "N/A")

                # Logăm valorile extrase
                _LOGGER.debug("Nume: %s, Email: %s", nume, email)
            except Exception as e:
                _LOGGER.error("Eroare la obținerea datelor utilizator: %s", e)
                raise UpdateFailed(f"Eroare get_user_data: {e}")

            # 2. Date paginate: vehicule
            try:
                paginated_data = await self.hass.async_add_executor_job(self.api.get_paginated_data)
                _LOGGER.debug("Răspuns brut get_paginated_data: %s", paginated_data)

                if not paginated_data or not isinstance(paginated_data, dict):
                    raise ValueError("Răspuns invalid sau gol pentru get_paginated_data")

                vehicule_data = paginated_data.get("view", [])
                self.vehicule_data = [safe_get(vehicul.get("entity"), {}) for vehicul in vehicule_data]
            except Exception as e:
                _LOGGER.error("Eroare la obținerea datelor vehicule: %s", e)
                raise UpdateFailed(f"Eroare get_paginated_data: {e}")

            # 3. Lista de țări
            try:
                countries_data = await self.hass.async_add_executor_job(self.api.get_countries)
                _LOGGER.debug("Răspuns brut get_countries: %s", countries_data)

                if not countries_data or not isinstance(countries_data, list):
                    raise ValueError("Răspuns invalid sau gol pentru get_countries")

                for country in countries_data:
                    code = safe_get(country.get("cod"), "N/A")
                    name = safe_get(country.get("denumire"), "N/A")
                    _LOGGER.debug("Țară: Cod=%s, Nume=%s", code, name)
            except Exception as e:
                _LOGGER.error("Eroare la obținerea listei de țări: %s", e)
                countries_data = []

            # 4. Treceri de pod
            treceri_pod_data = {"detectionList": []}
            for vehicul in self.vehicule_data:
                vin = safe_get(vehicul.get("vin"), "N/A")
                plate_no = safe_get(vehicul.get("plateNo"), "N/A")
                certificate_series = safe_get(vehicul.get("certificateSeries"), "N/A")
                _LOGGER.debug("Procesăm vehiculul: VIN=%s, PlateNo=%s", vin, plate_no)

                if vin == "N/A" or plate_no == "N/A" or certificate_series == "N/A":
                    _LOGGER.warning("Date incomplete pentru vehicul: VIN=%s, PlateNo=%s", vin, plate_no)
                    continue

                try:
                    vehicul_treceri = await self.hass.async_add_executor_job(
                        self.api.get_treceri_pod,
                        vin,
                        plate_no,
                        certificate_series,
                    )
                    _LOGGER.debug("Răspuns brut get_treceri_pod pentru %s: %s", plate_no, vehicul_treceri)

                    if isinstance(vehicul_treceri, dict) and "detectionList" in vehicul_treceri:
                        treceri_pod_data["detectionList"].extend(vehicul_treceri["detectionList"])
                    else:
                        _LOGGER.info("Nu s-au găsit restanțe pentru vehiculul %s.", plate_no)
                except Exception as e:
                    _LOGGER.error("Eroare la obținerea restanțelor trecerilor de pod pentru %s: %s", plate_no, e)

            # 5. Calcul interval pentru tranzacții
            try:
                date_from = int((datetime.now() - timedelta(days=self.istoricul_tranzactiilor * 365)).timestamp() * 1000)
                date_to = int(datetime.now().timestamp() * 1000)
                transactions = await self.hass.async_add_executor_job(self.api.get_tranzactii, date_from, date_to)
                _LOGGER.debug("Răspuns brut get_tranzactii: %s", transactions)

                if not transactions or not isinstance(transactions, dict):
                    raise ValueError("Tranzacțiile nu sunt un dicționar valid")

                tranzactii_lista = transactions.get("view", [])
            except Exception as e:
                _LOGGER.error("Eroare la obținerea tranzacțiilor: %s", e)
                tranzactii_lista = []

            # 6. Consolidare date
            new_data = {
                "user": user_data.get("user", {}),
                "paginated_data": paginated_data,
                "countries_data": countries_data,
                "transactions": tranzactii_lista,
                "detectionList": treceri_pod_data.get("detectionList", []),
            }

            self.data = new_data
            _LOGGER.info("Datele au fost actualizate cu succes.")
            return self.data

        except Exception as e:
            _LOGGER.error("Eroare la actualizarea datelor: %s", e)
            raise UpdateFailed(f"Eroare la actualizarea datelor: {e}")
