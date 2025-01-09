"""Platforma sensor pentru integrarea CNAIR eRovinieta."""

import logging
from datetime import datetime
import time
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.core import callback

from .const import DOMAIN, ATTRIBUTION, DEFAULT_TRANSACTION_HISTORY_YEARS
from .coordinator import ErovinietaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Configurează entitățile senzorului pe baza unei intrări de configurare."""
    coordinator: ErovinietaCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    sensors = []
    _LOGGER.debug("Începem configurarea senzorilor pentru entry_id: %s", config_entry.entry_id)

    # Verificăm dacă datele din coordinator sunt disponibile
    if not coordinator.data:
        _LOGGER.error("Datele de la coordinator sunt indisponibile. Nu se pot crea senzori.")
        return

    try:
        # Adaugă senzor pentru utilizator
        sensors.append(DateUtilizatorSensor(coordinator, config_entry))
        _LOGGER.debug("Senzor DateUtilizatorSensor creat cu succes.")
    except Exception as e:
        _LOGGER.error("Eroare la crearea senzorului DateUtilizatorSensor: %s", e)

    # Adaugă senzori pentru vehicule
    paginated_data = coordinator.data.get("paginated_data", {}).get("view", [])
    vehicule_data = []  # Pentru stocarea vehiculelor în coordinator
    if paginated_data:
        _LOGGER.debug("Găsite %d vehicule în datele paginate.", len(paginated_data))
        for vehicul in paginated_data:
            plate_no = vehicul.get("entity", {}).get("plateNo", "Necunoscut")
            try:
                vin = vehicul.get("entity", {}).get("vin", "Necunoscut")
                certificate_series = vehicul.get("entity", {}).get("certificateSeries", "Necunoscut")

                if not vin or not plate_no or not certificate_series:
                    _LOGGER.warning(
                        "Vehicul cu date incomplete: VIN=%s, PlateNo=%s, CertificateSeries=%s",
                        vin, plate_no, certificate_series,
                    )
                    continue

                # Creează senzor pentru vehicul
                sensors.append(VehiculSensor(coordinator, config_entry, vehicul))
                _LOGGER.debug("Senzor VehiculSensor creat pentru vehiculul cu număr: %s", plate_no)

                # Creează senzor pentru plăți treceri pod, bazat pe vehicul
                sensors.append(
                    PlataTreceriPodSensor(
                        coordinator,
                        config_entry,
                        vin=vin,
                        plate_no=plate_no,
                        certificate_series=certificate_series,
                    )
                )
                _LOGGER.debug(
                    "Senzor PlataTreceriPodSensor creat pentru vehiculul cu număr: %s", plate_no
                )

                # Creează senzor pentru treceri de pod, bazat pe vehicul
                sensors.append(
                    TreceriPodSensor(
                        coordinator,
                        config_entry,
                        vin=vin,
                        plate_no=plate_no,
                        certificate_series=certificate_series,
                    )
                )
                _LOGGER.debug(
                    "Senzor TreceriPodSensor creat pentru vehiculul cu număr: %s", plate_no
                )

                # Creează senzor SoldSensor pentru fiecare vehicul
                sensors.append(SoldSensor(coordinator, config_entry, plate_no))
                _LOGGER.debug("Senzor SoldSensor creat pentru vehiculul cu număr: %s", plate_no)

                # Adaugă vehiculul în vehicule_data
                vehicule_data.append({
                    "vin": vin,
                    "plateNo": plate_no,
                    "certificateSeries": certificate_series,
                })
            except Exception as e:
                _LOGGER.error("Eroare la crearea senzorilor pentru vehiculul %s: %s", plate_no, e)

        # Adaugă vehiculele în coordinator
        coordinator.vehicule_data = vehicule_data
        _LOGGER.debug("Vehiculele au fost salvate în coordinator: %s", vehicule_data)
    else:
        _LOGGER.warning("Nu au fost găsite vehicule în datele paginate.")

    # Adaugă senzor pentru raport tranzacții
    tranzactii_data = coordinator.data.get("transactions", [])
    if tranzactii_data:
        _LOGGER.debug("Găsite %d tranzacții în datele disponibile.", len(tranzactii_data))
        try:
            sensors.append(RaportTranzactiiSensor(coordinator, config_entry))
            _LOGGER.debug("Senzor RaportTranzactiiSensor creat cu succes.")
        except Exception as e:
            _LOGGER.error("Eroare la crearea senzorului RaportTranzactiiSensor: %s", e)
    else:
        _LOGGER.warning("Nu au fost găsite tranzacții în datele furnizate.")

    # Adăugăm senzorii în Home Assistant
    if sensors:
        try:
            async_add_entities(sensors, update_before_add=True)
            _LOGGER.info("Toți senzorii au fost adăugați cu succes.")
        except Exception as e:
            _LOGGER.error("Eroare la adăugarea senzorilor: %s", e)
    else:
        _LOGGER.warning("Nu au fost creați senzori din cauza lipsei datelor relevante.")

# -------------------------------------------------------------------
#                           Baza
# -------------------------------------------------------------------

class ErovinietaBaseSensor(CoordinatorEntity, SensorEntity):
    """Clasa de bază pentru senzorii Erovinieta."""

    def __init__(self, coordinator, config_entry, name, unique_id, entity_id, icon=None):
        """Inițializează senzorul de bază."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_entity_id = entity_id
        self._attr_icon = icon

        _LOGGER.debug(
            "Inițializare ErovinietaBaseSensor: name=%s, unique_id=%s, entity_id=%s",
            self._attr_name,
            self._attr_unique_id,
            self._attr_entity_id,
        )

    @property
    def device_info(self):
        """Informații despre dispozitiv pentru integrare."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "CNAIR eRovinieta",
            "manufacturer": "Ciprian Nicolae (cnecrea)",
            "model": "CNAIR eRovinieta",
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def unique_id(self):
        """Returnează identificatorul unic al senzorului."""
        return self._attr_unique_id

    @property
    def entity_id(self):
        """Returnează identificatorul explicit al entității."""
        return self._attr_entity_id

    @entity_id.setter
    def entity_id(self, value):
        """Setează identificatorul explicit al entității."""
        self._attr_entity_id = value

    @property
    def icon(self):
        """Pictograma senzorului."""
        return self._attr_icon


# -------------------------------------------------------------------
#                     DateUtilizatorSensor
# -------------------------------------------------------------------
class DateUtilizatorSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea datelor utilizatorului."""

    def __init__(self, coordinator, config_entry):
        """Inițializează senzorul DateUtilizatorSensor."""
        user_data = coordinator.data.get("user_data", {})
        utilizator_data = user_data.get("utilizator", {})
        user_identifier = utilizator_data.get("nume", "necunoscut").replace(" ", "_").lower()
        entity_id = f"sensor.{DOMAIN}_date_utilizator_{user_identifier}"
        unique_id = f"{DOMAIN}_date_utilizator_{user_identifier}"

        # Inițializăm clasa de bază
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Date utilizator",
            unique_id=unique_id,
            entity_id=entity_id,
            icon="mdi:account-details",
        )

        _LOGGER.debug(
            "Inițializare DateUtilizatorSensor: name=%s, unique_id=%s, entity_id=%s",
            self._attr_name,
            self._attr_unique_id,
            self._attr_entity_id,
        )

    @property
    def state(self):
        """Returnează starea senzorului (atribut principal)."""
        if not self.coordinator.data or "user_data" not in self.coordinator.data:
            _LOGGER.debug("DateUtilizatorSensor - Nu există date în coordinator.")
            return "nespecificat"

        user_data = self.coordinator.data["user_data"]
        user_id = user_data.get("id")
        return user_id if user_id is not None else "nespecificat"

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare."""
        if not self.coordinator.data or "user_data" not in self.coordinator.data:
            _LOGGER.debug("DateUtilizatorSensor - Nu există date în coordinator.")
            return {}

        user_data = self.coordinator.data["user_data"]
        utilizator_data = user_data.get("utilizator", {})
        tara_data = user_data.get("tara", {})
        denumire_tara = tara_data.get("denumire", "nespecificat")

        def safe_get(data, key, default="nespecificat"):
            """Returnează valoarea pentru o cheie sau 'nespecificat' dacă e null."""
            value = data.get(key)
            return value if value is not None else default

        def capitalize_name(name):
            """Formatează corect numele cu inițiale mari."""
            return " ".join(word.capitalize() for word in name.split())

        # Determinăm valorile pentru Județ și Localitate în funcție de țară
        if denumire_tara.lower() == "romania":
            judet = safe_get(user_data.get("judet", {}), "nume")
            localitate = safe_get(user_data.get("localitate", {}), "nume")
        else:
            judet = safe_get(user_data, "judetText")
            localitate = safe_get(user_data, "localitateText")

        attributes = {
            "Numele și prenumele": safe_get(utilizator_data, "nume", "").title(),
            "CNP": safe_get(user_data, "cnpCui"),
            "Telefon de contact": safe_get(utilizator_data, "telefon"),
            "Persoană fizică": "Da" if safe_get(user_data, "pf") else "Nu",
            "Email utilizator": safe_get(utilizator_data, "email"),
            "Acceptă corespondența": "Da" if safe_get(user_data, "acceptaCorespondenta") else "Nu",
            "Adresa": safe_get(user_data, "adresa"),
            "Localitate": localitate,
            "Județ": judet,
            "Țară": capitalize_name(denumire_tara),
        }

        attributes["attribution"] = ATTRIBUTION
        return attributes

# -------------------------------------------------------------------
#                     VehiculSensor
# -------------------------------------------------------------------

class VehiculSensor(ErovinietaBaseSensor):
    """Senzor pentru un vehicul în sistemul e-Rovinietă."""

    def __init__(self, coordinator, config_entry, vehicul_data):
        """Inițializează senzorul pentru un vehicul specific."""
        plate_no = vehicul_data.get("entity", {}).get("plateNo", "Necunoscut")
        entity_id = f"sensor.{DOMAIN}_vehicul_{plate_no.replace(' ', '_').lower()}"
        unique_id = f"{DOMAIN}_vehicul_{plate_no.replace(' ', '_').lower()}"

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Vehicul",
            unique_id=unique_id,
            entity_id=entity_id,
            icon="mdi:car",
        )

        self.vehicul_data = vehicul_data

        _LOGGER.debug(
            "Inițializare VehiculSensor: name=%s, unique_id=%s, entity_id=%s",
            self._attr_name,
            self._attr_unique_id,
            self._attr_entity_id,
        )

        # Transmite datele vehiculului către coordonator pentru utilizare ulterioară
        vin = vehicul_data.get("entity", {}).get("vin", "Necunoscut")
        certificate_series = vehicul_data.get("entity", {}).get("certificateSeries", "Necunoscut")
        self.coordinator.vehicule_data.append({
            "vin": vin,
            "plateNo": plate_no,
            "certificateSeries": certificate_series,
        })
        _LOGGER.debug(
            "VehiculSensor - Date vehicul trimise către coordonator: VIN=%s, PlateNo=%s, CertificateSeries=%s",
            vin, plate_no, certificate_series
        )

    @staticmethod
    def get_country_name(country_id, countries_data):
        """Returnează denumirea țării pe baza ID-ului."""
        if not country_id or not countries_data:
            return "Necunoscut"
        for country in countries_data:
            if country.get("id") == country_id:
                country_name = country.get("denumire", "Necunoscut")
                # Capitalizăm fiecare cuvânt din denumirea țării (opțional)
                return " ".join(word.capitalize() for word in country_name.split())
        return "Necunoscut"

    @staticmethod
    def format_timestamp(timestamp_millis):
        """
        Formatează un timestamp (în milisecunde) în format:
        YYYY-MM-DD HH:MM:SS.
        Returnează șir gol dacă timestamp-ul lipsește.
        """
        if timestamp_millis:
            try:
                dt = datetime.fromtimestamp(timestamp_millis / 1000)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except (OSError, ValueError):
                return "Dată invalidă"
        return ""

    @property
    def state(self):
        """Returnează numărul de înmatriculare ca stare principală a senzorului."""
        plate_no = self.vehicul_data.get("entity", {}).get("plateNo", "Necunoscut")
        return plate_no

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare ale senzorului."""
        entity = self.vehicul_data.get("entity", {})
        vignettes_list = self.vehicul_data.get("userDetailsVignettes", [])

        # Atribute de bază, mereu prezente
        attributes = {
            "Număr de înmatriculare": entity.get("plateNo", "Necunoscut"),
            "VIN": entity.get("vin", "Necunoscut"),
            "Seria certificatului": entity.get("certificateSeries", "Necunoscut"),
            "Țara": self.get_country_name(
                entity.get("tara"),
                self.coordinator.data.get("countries_data", [])
            ),
            "attribution": ATTRIBUTION,
        }

        # Verificăm dacă există rovinietă
        if not vignettes_list:
            # Nu există rovinietă
            attributes["Rovinietă"] = "Nu există rovinietă"
        else:
            # Există cel puțin o rovinietă -> afișăm detaliile primei roviniete
            vignette = vignettes_list[0]
            start_ts = vignette.get("vignetteStartDate")
            stop_ts = vignette.get("vignetteStopDate")

            # Convertim datele
            start_date_str = self.format_timestamp(start_ts)
            stop_date_str = self.format_timestamp(stop_ts)

            # Calculăm câte zile mai sunt până la expirare
            zile_ramase = None
            if stop_ts:
                now_seconds = int(time.time())
                stop_seconds = stop_ts // 1000
                days_diff = (stop_seconds - now_seconds) // 86400
                zile_ramase = days_diff

            # Actualizăm atributele cu informații despre rovinietă
            attributes["Categorie vignietă"] = vignette.get("vignetteCategory", "Necunoscut")
            attributes["Data început vignietă"] = start_date_str
            attributes["Data sfârșit vignietă"] = stop_date_str
            attributes["Expiră peste (zile)"] = zile_ramase if zile_ramase is not None else "N/A"

        return attributes


# -------------------------------------------------------------------
#                     Senzor RaportTranzactiiSensor
# -------------------------------------------------------------------

class RaportTranzactiiSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea raportului tranzacțiilor."""

    def __init__(self, coordinator, config_entry):
        """Inițializează senzorul RaportTranzactiiSensor."""
        # Accesăm datele utilizatorului din "user_data"
        user_data = coordinator.data.get("user_data", {})
        utilizator_data = user_data.get("utilizator", {})
        user_identifier = utilizator_data.get("nume", "necunoscut").replace(" ", "_").lower()
        
        # Setăm entity_id și unique_id pe baza numelui utilizatorului
        entity_id = f"sensor.{DOMAIN}_raport_tranzactii_{user_identifier}"
        unique_id = f"{DOMAIN}_raport_tranzactii_{user_identifier}"
        
        # Inițializăm clasa de bază
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Raport tranzacții",
            unique_id=unique_id,
            entity_id=entity_id,
            icon="mdi:chart-bar-stacked",
        )

        _LOGGER.debug(
            "Inițializare RaportTranzactiiSensor: name=%s, unique_id=%s, entity_id=%s",
            self._attr_name,
            self._attr_unique_id,
            self._attr_entity_id,
        )

    @property
    def state(self):
        """Returnează numărul total al tranzacțiilor realizate."""
        tranzactii_data = self.coordinator.data.get("transactions", [])
        return len(tranzactii_data)

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare simplificate."""
        tranzactii_data = self.coordinator.data.get("transactions", [])
        total_sum = sum(
            float(item.get("valoareTotalaCuTva", 0)) for item in tranzactii_data if isinstance(item, dict)
        )

        # Calculăm perioada analizată
        years_analyzed = self.coordinator.config_entry.options.get("transaction_history_years", 2)
        attributes = {
            "Perioadă analizată": f"Ultimii {years_analyzed} ani",
            "Număr facturi": len(tranzactii_data),
            "Suma totală plătită": f"{total_sum:.2f} RON",
            "attribution": ATTRIBUTION,
        }
        return attributes


# -------------------------------------------------------------------
#             Senzor PlataTreceriPodSensor - neachitate
# -------------------------------------------------------------------

class PlataTreceriPodSensor(ErovinietaBaseSensor):
    """Senzor pentru verificarea plăților pentru treceri de pod (restanțe)."""

    def __init__(self, coordinator, config_entry, vin, plate_no, certificate_series):
        """Inițializează senzorul PlataTreceriPodSensor."""
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Restanțe treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_plata_treceri_pod_{plate_no.replace(' ', '_').lower()}",
            entity_id=f"sensor.{DOMAIN}_plata_treceri_pod_{plate_no.replace(' ', '_').lower()}",
            icon="mdi:invoice-text-remove",
        )
        self.vin = vin
        self.plate_no = plate_no
        self.certificate_series = certificate_series
        _LOGGER.debug(
            "Inițializare PlataTreceriPodSensor: name=%s, unique_id=%s, vin=%s, plate_no=%s",
            self._attr_name,
            self._attr_unique_id,
            self.vin,
            self.plate_no,
        )

    @property
    def state(self):
        """Returnează starea principală: Da sau Nu (există restanțe?)."""
        detection_list = self.coordinator.data.get("detectionList", [])
        now = int(datetime.now().timestamp() * 1000)  # Timpul actual în milisecunde
        interval_ms = 24 * 60 * 60 * 1000  # 24 ore în milisecunde

        # Filtrează trecerile neplătite din ultimele 24h
        neplatite = [
            detection for detection in detection_list
            if detection.get("paymentStatus") is None
            and now - detection.get("detectionTimestamp", 0) <= interval_ms
        ]
        return "Da" if len(neplatite) > 0 else "Nu"

    @property
    def extra_state_attributes(self):
        """Returnează detalii despre trecerile neplătite (restanțe)."""
        detection_list = self.coordinator.data.get("detectionList", [])
        now = int(datetime.now().timestamp() * 1000)
        interval_ms = 24 * 60 * 60 * 1000  # 24 ore în milisecunde

        # Filtrează trecerile neplătite
        neplatite = [
            detection for detection in detection_list
            if detection.get("paymentStatus") is None
            and now - detection.get("detectionTimestamp", 0) <= interval_ms
        ]

        attributes = {
            "Număr treceri neplătite": len(neplatite),
            "Număr de înmatriculare": self.plate_no,
            "VIN": self.vin,
            "Seria certificatului": self.certificate_series,
        }

        # Funcție pentru a gestiona valori lipsă
        def safe_get(value, default=""):
            return value if value is not None else default

        # Adăugăm fiecare trecere cu detalii
        for idx, detection in enumerate(neplatite, start=1):
            timestamp = detection.get("detectionTimestamp")
            formatted_time = (
                datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                if timestamp
                else ""
            )
            # Separator vizual minimal
            attributes[f"--- Restanțe pentru trecerea de pod #{idx}"] = "\n"
            attributes[f"Trecere {idx} - Categorie"] = safe_get(detection.get("detectionCategory"))
            attributes[f"Trecere {idx} - Timp detectare"] = formatted_time
            attributes[f"Trecere {idx} - Direcție"] = safe_get(detection.get("direction"))
            attributes[f"Trecere {idx} - Bandă"] = safe_get(detection.get("lane"))

        attributes["attribution"] = ATTRIBUTION
        return attributes


# -------------------------------------------------------------------
#                Senzor TreceriPodSensor - istoric
# -------------------------------------------------------------------

class TreceriPodSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea istoriei trecerilor de pod."""

    def __init__(self, coordinator, config_entry, vin, plate_no, certificate_series):
        """Inițializează senzorul TreceriPodSensor."""
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_treceri_pod_{plate_no.replace(' ', '_').lower()}_{config_entry.entry_id}",
            entity_id=f"sensor.{DOMAIN}_treceri_pod_{plate_no.replace(' ', '_').lower()}",
            icon="mdi:bridge",
        )
        self.vin = vin
        self.plate_no = plate_no
        self.certificate_series = certificate_series
        _LOGGER.debug(
            "Inițializare TreceriPodSensor: name=%s, unique_id=%s, vin=%s, plate_no=%s, certificate_series=%s",
            self._attr_name,
            self._attr_unique_id,
            self.vin,
            self.plate_no,
            self.certificate_series,
        )

    @property
    def state(self):
        """Returnează numărul total al trecerilor pentru vehicul."""
        detection_list = [
            detection
            for detection in self.coordinator.data.get("detectionList", [])
            if detection.get("vin") == self.vin and detection.get("plateNo") == self.plate_no
        ]
        total_treceri = len(detection_list)
        return total_treceri

    @property
    def extra_state_attributes(self):
        """Returnează detalii suplimentare despre treceri."""
        detection_list = [
            detection
            for detection in self.coordinator.data.get("detectionList", [])
            if detection.get("vin") == self.vin and detection.get("plateNo") == self.plate_no
        ]

        attributes = {
            "Număr total treceri": len(detection_list),
            "Număr de înmatriculare": self.plate_no,
            "VIN": self.vin,
            "Seria certificatului": self.certificate_series,
        }

        for idx, detection in enumerate(detection_list, start=1):
            timestamp = detection.get("detectionTimestamp")
            formatted_time = (
                datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                if timestamp
                else ""
            )
            # Separator vizual minimal
            attributes[f"--- Detalii privind trecerea de pod #{idx}"] = "\n"
            attributes[f"Trecere {idx} - Categorie"] = detection.get("detectionCategory") or ""
            attributes[f"Trecere {idx} - Timp detectare"] = formatted_time
            attributes[f"Trecere {idx} - Direcție"] = detection.get("direction") or ""
            attributes[f"Trecere {idx} - Bandă"] = detection.get("lane") or ""
            attributes[f"Trecere {idx} - Valoare (RON)"] = detection.get("value") or ""
            attributes[f"Trecere {idx} - Partener"] = detection.get("partner") or ""
            attributes[f"Trecere {idx} - Metodă plată"] = detection.get("paymentMethod") or ""
            attributes[f"Trecere {idx} - Vehicul"] = detection.get("paymentPlateNo") or ""
            attributes[f"Trecere {idx} - Treceri achiziționate"] = detection.get("taxName") or ""
            valid_until_timestamp = detection.get("validUntilTimestamp")
            formatted_valid_until = (
                datetime.fromtimestamp(valid_until_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                if valid_until_timestamp
                else ""
            )
            attributes[f"Trecere {idx} - Valabilitate până la"] = formatted_valid_until

        attributes["attribution"] = ATTRIBUTION
        return attributes

    async def async_update(self):
        """Actualizează manual datele pentru senzor (opțional, când se cheamă explicit)."""
        _LOGGER.debug(
            "Actualizăm manual datele pentru TreceriPodSensor: vin=%s, plate_no=%s, certificate_series=%s",
            self.vin,
            self.plate_no,
            self.certificate_series,
        )
        try:
            treceri_pod_data = await self.coordinator.hass.async_add_executor_job(
                self.coordinator.api.get_treceri_pod,
                self.vin,
                self.plate_no,
                self.certificate_series,
            )
            # Actualizăm datele în coordinator
            self.coordinator.data["detectionList"] = treceri_pod_data.get("detectionList", [])
            _LOGGER.info(
                "Datele pentru TreceriPodSensor au fost actualizate cu succes pentru vehiculul %s.",
                self.plate_no,
            )
        except Exception as e:
            _LOGGER.error(
                "Eroare la actualizarea datelor pentru TreceriPodSensor: vin=%s, plate_no=%s, error=%s",
                self.vin,
                self.plate_no,
                e,
            )


# -------------------------------------------------------------------
#                Senzor SoldSensor
# -------------------------------------------------------------------

class SoldSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea soldului 'soldPeajeNeexpirate'."""

    def __init__(self, coordinator, config_entry, plate_no):
        """Inițializează senzorul SoldSensor."""
        sanitized_plate_no = plate_no.replace(' ', '_').lower()  # Normalizează numărul de înmatriculare

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Sold peaje neexpirate ({plate_no})",
            unique_id=f"{DOMAIN}_sold_peaje_neexpirate_{sanitized_plate_no}_{config_entry.entry_id}",
            entity_id=f"sensor.{DOMAIN}_sold_peaje_neexpirate_{sanitized_plate_no}",
            icon="mdi:boom-gate",
        )
        self.plate_no = plate_no
        _LOGGER.debug(
            "Inițializare SoldSensor: name=%s, unique_id=%s, plate_no=%s",
            self._attr_name,
            self._attr_unique_id,
            self.plate_no,
        )

    @property
    def state(self):
        """Returnează valoarea principală: soldPeajeNeexpirate."""
        paginated_data = self.coordinator.data.get("paginated_data", {}).get("view", [])
        if not paginated_data:
            _LOGGER.warning("Nu există date paginate pentru sold.")
            return 0

        try:
            for item in paginated_data:
                entity = item.get("entity", {})
                if entity and entity.get("plateNo") == self.plate_no:
                    detection_payment_sum = item.get("detectionPaymentSum", {})
                    if detection_payment_sum:
                        return detection_payment_sum.get("soldPeajeNeexpirate", 0)
            _LOGGER.info("Nu s-a găsit sold pentru numărul de înmatriculare: %s", self.plate_no)
            return 0
        except Exception as e:
            _LOGGER.error("Eroare la obținerea soldului pentru %s: %s", self.plate_no, e)
            return 0

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare ale senzorului."""
        paginated_data = self.coordinator.data.get("paginated_data", {}).get("view", [])
        attributes = {"attribution": ATTRIBUTION}

        if not paginated_data:
            _LOGGER.info("Nu există date paginate pentru configurarea atributelor.")
            attributes.update({
                "Sold Peaje Neexpirate": 0,
            })
            return attributes

        try:
            for item in paginated_data:
                entity = item.get("entity", {})
                if entity and entity.get("plateNo") == self.plate_no:
                    detection_payment_sum = item.get("detectionPaymentSum", {})
                    if detection_payment_sum:
                        attributes.update({
                            "Sold peaje neexpirate": detection_payment_sum.get("soldPeajeNeexpirate", 0),
                        })
                        return attributes

            _LOGGER.info("Nu s-au găsit atribute pentru numărul de înmatriculare: %s", self.plate_no)
        except Exception as e:
            _LOGGER.error("Eroare la configurarea atributelor suplimentare pentru %s: %s", self.plate_no, e)

        # Atribute implicite dacă nu există date relevante
        attributes.update({
            "Sold peaje neexpirate": 0,
        })
        return attributes
