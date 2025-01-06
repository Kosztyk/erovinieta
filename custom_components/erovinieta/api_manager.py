"""Manager API pentru integrarea Erovinieta."""

import requests
import logging
from datetime import datetime
from .const import (
    URL_LOGIN,
    URL_GET_USER_DATA,
    URL_GET_PAGINATED,
    URL_GET_COUNTRIES,
    URL_TRANZACTII,
    URL_DETALII_TRANZACTIE,
    URL_TRECERI_POD,  # URL pentru trecerile de pod
    ATTRIBUTION,
)

_LOGGER = logging.getLogger(__name__)

class ErovinietaAPI:
    def __init__(self, username, password):
        """Inițializează API-ul Erovinieta."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None

    def authenticate(self):
        """Autentifică utilizatorul și stochează tokenul."""
        _LOGGER.debug("Inițiem procesul de autentificare pentru utilizatorul %s", self.username)
        payload = {
            "username": self.username,
            "password": self.password,
            "_spring_security_remember_me": "on"
        }
        response = self.session.post(URL_LOGIN, json=payload)
        if response.status_code == 200:
            _LOGGER.info("Autentificarea a fost realizată cu succes pentru utilizatorul %s", self.username)
            self.token = self.session.cookies.get("JSESSIONID")
            _LOGGER.debug("Token obținut: %s", self.token)
        else:
            _LOGGER.error("Eroare la autentificare: %s", response.text)
            raise Exception("Autentificare eșuată.")

    def _generate_timestamp_url(self, base_url, is_first_param=True):
        """Generează un URL cu timestamp actual."""
        timestamp = int(datetime.now().timestamp() * 1000)  # Convertim în milisecunde
        separator = "?" if is_first_param else "&"  # Folosim `?` doar pentru primul parametru
        return f"{base_url}{separator}timestamp={timestamp}"

    def get_user_data(self):
        """Obține detalii despre utilizator."""
        # 1) Verificăm dacă avem token; dacă nu, ne autentificăm
        if not self.token:
            self.authenticate()

        url = self._generate_timestamp_url(URL_GET_USER_DATA)
        _LOGGER.debug("Cerere către URL-ul utilizator: %s", url)
        response = self.session.get(url)

        # 2) Dacă primim 401 sau 403, înseamnă că a expirat tokenul: reautentificăm și refacem cererea
        if response.status_code in [401, 403]:
            _LOGGER.info("Token expirat. Reîncerc autentificarea.")
            self.authenticate()
            response = self.session.get(url)

        if response.status_code == 200:
            _LOGGER.info("Detalii utilizator obținute cu succes.")
            try:
                user_data = response.json()
                return user_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea datelor utilizator: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea datelor utilizator: %s", response.text)
            raise Exception("Eroare la obținerea datelor utilizator.")

    def get_paginated_data(self, limit=4, page=0):
        """Obține date paginate."""
        # Verificăm și reautentificăm dacă e cazul
        if not self.token:
            self.authenticate()

        base_url = f"{URL_GET_PAGINATED}?limit={limit}&page={page}"
        url = self._generate_timestamp_url(base_url, is_first_param=False)
        _LOGGER.debug("Cerere către URL-ul paginat: %s", url)
        response = self.session.get(url)

        # Dacă primim 401/403, reautentificăm
        if response.status_code in [401, 403]:
            _LOGGER.info("Token expirat. Reîncerc autentificarea.")
            self.authenticate()
            response = self.session.get(url)

        if response.status_code == 200:
            _LOGGER.info("Date paginate obținute cu succes.")
            try:
                paginated_data = response.json()
                return paginated_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea datelor paginate: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea datelor paginate: %s", response.text)
            raise Exception("Eroare la obținerea datelor paginate.")

    def get_countries(self):
        """Obține lista țărilor."""
        # Verificăm și reautentificăm dacă e cazul
        if not self.token:
            self.authenticate()

        _LOGGER.debug("Cerere către URL-ul țărilor: %s", URL_GET_COUNTRIES)
        response = self.session.get(URL_GET_COUNTRIES)

        # Dacă primim 401/403, reautentificăm
        if response.status_code in [401, 403]:
            _LOGGER.info("Token expirat. Reîncerc autentificarea.")
            self.authenticate()
            response = self.session.get(URL_GET_COUNTRIES)

        if response.status_code == 200:
            _LOGGER.info("Lista țărilor obținută cu succes.")
            try:
                countries_data = response.json()
                return countries_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea listei țărilor: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea listei țărilor: %s", response.text)
            raise Exception("Eroare la obținerea listei țărilor.")

    def get_tranzactii(self, date_from, date_to):
        """Obține lista de tranzacții între două date."""
        # Verificăm și reautentificăm dacă e cazul
        if not self.token:
            self.authenticate()

        url = URL_TRANZACTII.format(dateFrom=date_from, dateTo=date_to)
        _LOGGER.debug("Cerere către URL-ul tranzacțiilor: %s", url)
        response = self.session.get(url)

        # Dacă primim 401/403, reautentificăm
        if response.status_code in [401, 403]:
            _LOGGER.info("Token expirat. Reîncerc autentificarea.")
            self.authenticate()
            response = self.session.get(url)

        if response.status_code == 200:
            _LOGGER.info("Tranzacțiile au fost obținute cu succes.")
            try:
                tranzactii_data = response.json()
                return tranzactii_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea tranzacțiilor: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea tranzacțiilor: %s", response.text)
            raise Exception("Eroare la obținerea tranzacțiilor.")

    def get_detalii_tranzactie(self, series):
        """Obține detalii pentru o tranzacție specifică."""
        # Verificăm și reautentificăm dacă e cazul
        if not self.token:
            self.authenticate()

        url = URL_DETALII_TRANZACTIE.format(series=series)
        _LOGGER.debug("Cerere către URL-ul detaliilor tranzacției: %s", url)
        response = self.session.get(url)

        # Dacă primim 401/403, reautentificăm
        if response.status_code in [401, 403]:
            _LOGGER.info("Token expirat. Reîncerc autentificarea.")
            self.authenticate()
            response = self.session.get(url)

        if response.status_code == 200:
            _LOGGER.info("Detalii tranzacție obținute cu succes.")
            try:
                detalii_data = response.json()
                return detalii_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea detaliilor tranzacției: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea detaliilor tranzacției: %s", response.text)
            raise Exception("Eroare la obținerea detaliilor tranzacției.")

    def get_treceri_pod(self, vin, plate_no, certificate_series, period=4):
        """Obține istoricul trecerilor de pod."""
        # Verificăm și reautentificăm dacă e cazul
        if not self.token:
            self.authenticate()

        url = URL_TRECERI_POD
        payload = {
            "vin": vin,
            "plateNo": plate_no,
            "certificateSeries": certificate_series,
            "vehicleFleetEntity": {
                "certificateSeries": certificate_series,
                "plateNo": plate_no,
                "username": self.username,
                "vin": vin,
            },
            "period": period,
            "vehicle": {
                "certificateSeries": certificate_series,
                "vin": vin,
                "plateNo": plate_no,
            },
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "Referer": "https://www.erovinieta.ro/vignettes-portal-web/index.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

        _LOGGER.debug("Cerere către URL-ul trecerilor de pod: %s cu payload: %s", url, payload)
        response = self.session.post(url, json=payload, headers=headers)

        # Dacă primim 401/403, reautentificăm
        if response.status_code in [401, 403]:
            _LOGGER.info("Token expirat. Reîncerc autentificarea.")
            self.authenticate()
            response = self.session.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            _LOGGER.info("Istoricul trecerilor de pod obținut cu succes.")
            try:
                treceri_pod_data = response.json()
                return treceri_pod_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea istoricului trecerilor de pod: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea istoricului trecerilor de pod: %s", response.text)
            raise Exception("Eroare la obținerea istoricului trecerilor de pod.")
