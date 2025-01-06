"""Manager API pentru integrarea Erovinieta."""

import requests
import logging
from datetime import datetime
from .const import URL_LOGIN, URL_GET_USER_DATA, URL_GET_PAGINATED, URL_GET_COUNTRIES, URL_TRANZACTII, URL_DETALII_TRANZACTIE, ATTRIBUTION

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
        _LOGGER.debug("Încep autentificarea pentru utilizatorul %s", self.username)
        payload = {
            "username": self.username,
            "password": self.password,
            "_spring_security_remember_me": "on"
        }
        response = self.session.post(URL_LOGIN, json=payload)
        if response.status_code == 200:
            _LOGGER.info("Autentificare reușită pentru utilizatorul %s", self.username)
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
        url = self._generate_timestamp_url(URL_GET_USER_DATA)
        _LOGGER.debug("Cerere către URL-ul utilizator: %s", url)
        response = self.session.get(url)
        if response.status_code == 200:
            _LOGGER.info("Detalii utilizator obținute cu succes.")
            try:
                user_data = response.json()
                #_LOGGER.debug("Date utilizator: %s", user_data)
                return user_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea datelor utilizator: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea datelor utilizator: %s", response.text)
            raise Exception("Eroare la obținerea datelor utilizator.")

    def get_paginated_data(self, limit=4, page=0):
        """Obține date paginate."""
        base_url = f"{URL_GET_PAGINATED}?limit={limit}&page={page}"  # Folosim separatorul `?` pentru primul parametru
        url = self._generate_timestamp_url(base_url, is_first_param=False)
        _LOGGER.debug("Cerere către URL-ul paginat: %s", url)
        response = self.session.get(url)
        if response.status_code == 200:
            _LOGGER.info("Date paginate obținute cu succes.")
            try:
                paginated_data = response.json()
                #_LOGGER.debug("Date paginate: %s", paginated_data)
                return paginated_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea datelor paginate: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea datelor paginate: %s", response.text)
            raise Exception("Eroare la obținerea datelor paginate.")

    def get_countries(self):
        """Obține lista țărilor."""
        _LOGGER.debug("Cerere către URL-ul țărilor: %s", URL_GET_COUNTRIES)
        response = self.session.get(URL_GET_COUNTRIES)
        if response.status_code == 200:
            _LOGGER.info("Lista țărilor obținută cu succes.")
            try:
                countries_data = response.json()
                #_LOGGER.debug("Lista țărilor: %s", countries_data)
                return countries_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea listei țărilor: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea listei țărilor: %s", response.text)
            raise Exception("Eroare la obținerea listei țărilor.")

    def get_tranzactii(self, date_from, date_to):
        """Obține lista de tranzacții între două date."""
        url = URL_TRANZACTII.format(dateFrom=date_from, dateTo=date_to)
        _LOGGER.debug("Cerere către URL-ul tranzacțiilor: %s", url)
        response = self.session.get(url)
        if response.status_code == 200:
            _LOGGER.info("Tranzacțiile au fost obținute cu succes.")
            try:
                tranzactii_data = response.json()
                _LOGGER.debug("Date tranzacții: OK (am mascat JSON pentru că este prea lung)")
                return tranzactii_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea tranzacțiilor: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea tranzacțiilor: %s", response.text)
            raise Exception("Eroare la obținerea tranzacțiilor.")

    def get_detalii_tranzactie(self, series):
        """Obține detalii pentru o tranzacție specifică."""
        url = URL_DETALII_TRANZACTIE.format(series=series)
        _LOGGER.debug("Cerere către URL-ul detaliilor tranzacției: %s", url)
        response = self.session.get(url)
        if response.status_code == 200:
            _LOGGER.info("Detalii tranzacție obținute cu succes.")
            try:
                detalii_data = response.json()
                _LOGGER.debug("Detalii tranzacție: %s", detalii_data)
                return detalii_data
            except Exception as e:
                _LOGGER.error("Eroare la parsarea detaliilor tranzacției: %s", e)
                raise
        else:
            _LOGGER.error("Eroare la obținerea detaliilor tranzacției: %s", response.text)
            raise Exception("Eroare la obținerea detaliilor tranzacției.")
