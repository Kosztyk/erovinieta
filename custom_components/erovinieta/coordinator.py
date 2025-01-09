# custom_components/erovinieta/coordinator.py

from datetime import datetime, timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, ISTORIC_TRANZACTII_DEFAULT
from .api import ErovinietaAPI  # Asigură-te că această linie este prezentă

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
        api: object,
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
            # 1. Date utilizator (folosind endpoint-ul corect)
            try:
                user_data = await self.hass.async_add_executor_job(self.api.get_user_data)
                _LOGGER.debug("Răspuns brut get_user_data: %s", user_data)

                # Verificare date utilizator
                nume = safe_get(user_data.get("utilizator", {}).get("nume"), "N/A")
                email = safe_get(user_data.get("utilizator", {}).get("email"), "N/A")
                _LOGGER.debug("Nume utilizator: %s, Email: %s", nume, email)
            except Exception as e:
                _LOGGER.error("Eroare la obținerea datelor utilizator: %s", e)
                user_data = {}

            # 2. Date paginate: vehicule
            try:
                paginated_data = await self.hass.async_add_executor_job(self.api.get_paginated_data)
                _LOGGER.debug("Răspuns brut get_paginated_data: %s", paginated_data)

                vehicule_data = safe_get(paginated_data.get("view"), [])
                self.vehicule_data = [safe_get(vehicul.get("entity"), {}) for vehicul in vehicule_data]
            except Exception as e:
                _LOGGER.error("Eroare la obținerea datelor vehicule: %s", e)
                paginated_data = {}

            # 3. Lista de țări
            try:
                countries_data = await self.hass.async_add_executor_job(self.api.get_countries)
                _LOGGER.debug("Răspuns brut get_countries: %s", countries_data)
            except Exception as e:
                _LOGGER.error("Eroare la obținerea listei de țări: %s", e)
                countries_data = []

            # 4. Treceri de pod
            treceri_pod_data = {"detectionList": []}
            for vehicul in self.vehicule_data:
                vin = safe_get(vehicul.get("vin"), "N/A")
                plate_no = safe_get(vehicul.get("plateNo"), "N/A")
                certificate_series = safe_get(vehicul.get("certificateSeries"), "N/A")
                if vin == "N/A" or plate_no == "N/A" or certificate_series == "N/A":
                    _LOGGER.warning("Date incomplete pentru vehicul: VIN=%s, PlateNo=%s", vin, plate_no)
                    continue

                try:
                    vehicul_treceri = await self.hass.async_add_executor_job(
                        self.api.get_treceri_pod, vin, plate_no, certificate_series
                    )
                    detection_list = safe_get(vehicul_treceri.get("detectionList"), [])
                    treceri_pod_data["detectionList"].extend(detection_list)
                except Exception as e:
                    _LOGGER.error("Eroare la obținerea trecerilor pentru %s: %s", plate_no, e)

            # 5. Tranzacții
            try:
                date_from = int((datetime.now() - timedelta(days=self.istoricul_tranzactiilor * 365)).timestamp() * 1000)
                date_to = int(datetime.now().timestamp() * 1000)
                transactions = await self.hass.async_add_executor_job(self.api.get_tranzactii, date_from, date_to)
                tranzactii_lista = safe_get(transactions.get("view"), [])
            except Exception as e:
                _LOGGER.error("Eroare la obținerea tranzacțiilor: %s", e)
                tranzactii_lista = []

            # 6. Consolidare date
            new_data = {
                "user_data": user_data,  # Salvează datele brute din get_user_data
                "paginated_data": paginated_data,
                "countries_data": countries_data,
                "transactions": tranzactii_lista,
                "detectionList": safe_get(treceri_pod_data.get("detectionList"), []),
            }

            self.data = new_data
            _LOGGER.info("Datele au fost actualizate cu succes.")
            return self.data

        except Exception as e:
            _LOGGER.error("Eroare la actualizarea datelor: %s", e)
            raise UpdateFailed(f"Eroare la actualizarea datelor: {e}")
