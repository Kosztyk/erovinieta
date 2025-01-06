"""Platforma sensor pentru integrarea Erovinieta."""

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
    # Preluăm coordinatorul din hass.data
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

    # Adaugă senzori pentru vehicule (din paginated_data)
    paginated_data = coordinator.data.get("paginated_data", {}).get("view", [])
    if paginated_data:
        _LOGGER.debug("Găsite %d vehicule în datele paginate.", len(paginated_data))
        for vehicul in paginated_data:
            try:
                plate_no = vehicul.get("entity", {}).get("plateNo", "Necunoscut")
                sensors.append(VehiculSensor(coordinator, config_entry, vehicul))
                _LOGGER.debug("Senzor VehiculSensor creat pentru vehiculul cu număr: %s", plate_no)
            except Exception as e:
                _LOGGER.error("Eroare la crearea senzorului VehiculSensor pentru %s: %s", plate_no, e)
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
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Date utilizator",
            unique_id=f"{DOMAIN}_date_utilizator_{config_entry.entry_id}",
            entity_id=f"sensor.{DOMAIN}_date_utilizator",
            icon="mdi:account-details",
        )

        _LOGGER.debug(
            "Inițializare DateUtilizatorSensor: name=%s, unique_id=%s",
            self._attr_name,
            self._attr_unique_id,
        )

    @property
    def state(self):
        """Returnează starea senzorului (atribut principal)."""
        if not self.coordinator.data or "user" not in self.coordinator.data:
            _LOGGER.debug("DateUtilizatorSensor - Nu există date['user'] în coordinator.")
            return None

        user_data = self.coordinator.data["user"]
        user_id = user_data.get("id")
        _LOGGER.debug("Senzor DateUtilizatorSensor - user_id: %s", user_id)
        return user_id or "Necunoscut"

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare (în stil 'DateContractSensor')."""
        if not self.coordinator.data or "user" not in self.coordinator.data:
            _LOGGER.debug("DateUtilizatorSensor - Nu există date['user'] în coordinator.")
            return {}

        user_data = self.coordinator.data["user"]
        utilizator_data = user_data.get("utilizator", {})
        tara_data = user_data.get("tara", {})

        attributes = {
            "Numele și prenumele": utilizator_data.get("nume", "").title(),
            "CNP": user_data.get("cnpCui"),
            "Telefon de contact": utilizator_data.get("telefon"),
            "Persoană fizică": "Da" if user_data.get("pf") else "Nu",
            "Email utilizator": utilizator_data.get("email"),
            "Acceptă corespondența": "Da" if user_data.get("acceptaCorespondenta") else "Nu",
            "Adresa": user_data.get("adresa"),
            "Localitate": user_data.get("localitateText"),
            "Județ": user_data.get("judetText"),
            "Țară": tara_data.get("denumire"),
        }
        #_LOGGER.debug("Senzor DateUtilizatorSensor - Atribute: %s", attributes)

        attributes["attribution"] = ATTRIBUTION
        return attributes


# -------------------------------------------------------------------
#                     VehiculSensor
# -------------------------------------------------------------------

class VehiculSensor(ErovinietaBaseSensor):
    """Senzor pentru vehicul."""

    def __init__(self, coordinator, config_entry, vehicul_data):
        """Inițializează senzorul pentru un vehicul specific."""
        plate_no = vehicul_data.get("entity", {}).get("plateNo", "Necunoscut")
        entity_id = f"sensor.{DOMAIN}_vehicul_{plate_no.replace(' ', '_').lower()}"
        unique_id = f"{DOMAIN}_vehicul_{plate_no.replace(' ', '_').lower()}"

        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Vehicul",
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

    @staticmethod
    def get_country_name(country_id, countries_data):
        """Returnează denumirea țării pe baza ID-ului."""
        for country in countries_data:
            if country.get("id") == country_id:
                return country.get("denumire", "Necunoscut")
        return "Necunoscut"

    @staticmethod
    def get_country_name(country_id, countries_data):
        """Returnează denumirea țării cu formatare corectă, pe baza ID-ului."""
        for country in countries_data:
            if country.get("id") == country_id:
                country_name = country.get("denumire", "Necunoscut")
                return " ".join(word.capitalize() for word in country_name.split())
        return "Necunoscut"

    @staticmethod
    def get_month_name(month):
        """Returnează numele lunii în limba română."""
        months = [
            "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
            "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"
        ]
        return months[month - 1] if 1 <= month <= 12 else "Necunoscut"

    @staticmethod
    def format_timestamp(timestamp):
        """Formatează timestamp-ul într-un mod prietenos."""
        dt = datetime.fromtimestamp(timestamp / 1000)  # Conversie din milisecunde
        ora = dt.hour
        minut = dt.minute

        # Gestionare singular/plural pentru minute și includerea cuvântului "de"
        if minut == 0:
            minute_text = "minute"  # Exemplu: 0 minute
        elif minut == 1:
            minute_text = "1 minut"  # Exemplu: 1 minut
        else:
            minute_text = f"{minut} de minute"  # Exemplu: 30 de minute

        # Obține numele lunii folosind funcția get_month_name
        luna = VehiculSensor.get_month_name(dt.month)

        # Returnare text formatat
        return f"{dt.day} {luna} {dt.year}, la ora {ora} și {minute_text}"

    @staticmethod
    def get_month_name(month):
        """Returnează numele lunii în limba română."""
        months = [
            "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
            "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"
        ]
        return months[month - 1] if 1 <= month <= 12 else "Necunoscut"

    @property
    def state(self):
        """Returnează starea senzorului."""
        plate_no = self.vehicul_data.get("entity", {}).get("plateNo", "Necunoscut")
        return plate_no

    @property
    def extra_state_attributes(self):
        """Returnează atributele suplimentare ale senzorului."""
        entity = self.vehicul_data.get("entity", {})
        vignettes = self.vehicul_data.get("userDetailsVignettes", [{}])[0]  # Prima vignetă, dacă există

        # Calculează zilele rămase
        # (asigură-te că vignettes.get("vignetteStopDate") nu este None sau 0)
        stop_date_ms = vignettes.get("vignetteStopDate")
        if stop_date_ms:
            zile_ramase = (stop_date_ms // 1000 - time.time()) / 86400
            zile_ramase = int(zile_ramase)
        else:
            zile_ramase = None

        # Definim dicționarul de atribute
        attributes = {
            "Număr de înmatriculare": entity.get("plateNo"),
            "VIN": entity.get("vin"),
            "Seria certificatului": entity.get("certificateSeries"),
            "Țara": self.get_country_name(entity.get("tara"), self.coordinator.data.get("countries_data", [])),
            "Categorie vignietă": vignettes.get("vignetteCategory"),
            "Data început vignietă": self.format_timestamp(vignettes.get("vignetteStartDate")),
            "Data sfârșit vignietă": self.format_timestamp(stop_date_ms),
            "Data început vignietă": self.format_timestamp(vignettes.get("vignetteStartDate")),
            "Data sfârșit vignietă": self.format_timestamp(vignettes.get("vignetteStopDate")),
            "Expiră peste (zile)": zile_ramase,  
        }

        #_LOGGER.debug("Atribute pentru VehiculSensor (%s): %s", self._attr_unique_id, attributes)
        attributes["attribution"] = ATTRIBUTION
        return attributes

# -------------------------------------------------------------------
#                     Senzor TranzactiiRealizate
# -------------------------------------------------------------------


class RaportTranzactiiSensor(ErovinietaBaseSensor):
    """Senzor pentru afișarea raportului tranzacțiilor."""

    def __init__(self, coordinator, config_entry):
        """Inițializează senzorul RaportTranzactiiSensor."""
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Raport tranzacții",
            unique_id=f"{DOMAIN}_raport_tranzactii_{config_entry.entry_id}",
            entity_id=f"sensor.{DOMAIN}_raport_tranzactii",
            icon="mdi:receipt-text-edit",
        )
        _LOGGER.debug(
            "Inițializare RaportTranzactiiSensor: name=%s, unique_id=%s",
            self._attr_name,
            self._attr_unique_id,
        )

    @property
    def state(self):
        """Returnează numărul total al tranzacțiilor realizate."""
        tranzactii_data = self.coordinator.data.get("transactions", [])
        #_LOGGER.debug("RaportTranzactiiSensor - tranzactii_data: %s", tranzactii_data)
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
            "attribution": ATTRIBUTION,  # Adăugăm sursa datelor
        }

        #_LOGGER.debug("RaportTranzactiiSensor - Atribute simplificate: %s", attributes)
        return attributes
