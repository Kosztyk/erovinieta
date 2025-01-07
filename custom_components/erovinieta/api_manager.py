"""Manager API pentru integrarea Erovinieta."""
import requests
import logging
from datetime import datetime
from json.decoder import JSONDecodeError

from .const import (
    URL_LOGIN,
    URL_GET_USER_DATA,
    URL_GET_PAGINATED,
    URL_GET_COUNTRIES,
    URL_TRANZACTII,
    URL_DETALII_TRANZACTIE,
    URL_TRECERI_POD,
)

_LOGGER = logging.getLogger(__name__)

class ErovinietaAPI:
    def __init__(self, username, password):
        """Inițializează API-ul Erovinieta."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None  # Va fi setat după autentificare

    # -------------------------------------------------------------------------
    #                 Metodă de bază pentru cererile HTTP
    # -------------------------------------------------------------------------
    def _request(self, method, url, payload=None, headers=None, reauth=True):
        """
        Trimite o cerere HTTP și parsează răspunsul JSON.
        - method: GET/POST etc.
        - url: endpoint complet
        - payload: datele trimise (pentru POST/PUT)
        - headers: antetele cererii
        - reauth: indică dacă reautentificarea se încearcă automat (True/False)

        Logica de reautentificare:
        1) Dacă nu avem JSESSIONID (self.token), apelăm authenticate().
        2) Facem cererea.
        3) Dacă primim 401/403 și reauth=True, apelăm authenticate() și refacem cererea cu reauth=False.
        4) Dacă status==200, dar conținutul nu este JSON valid, la fel, încercăm reautentificarea o singură dată.
        5) Dacă reautentificarea eșuează din nou, ridicăm excepție.
        """
        # Dacă nu avem încă un token, încercăm autentificarea
        if not self.token:
            self.authenticate()

        # Facem cererea inițială
        resp_data, status_code, resp_text = self._do_request(method, url, payload, headers)

        # -------------- 1) Verificăm codul de răspuns  --------------
        if status_code in [401, 403] and reauth:
            _LOGGER.info(
                "Token expirat sau acces interzis (status=%s). Reîncerc autentificarea...",
                status_code
            )
            self.authenticate()
            # Refacem cererea (doar o singură dată) cu reauth=False
            resp_data, status_code, resp_text = self._do_request(method, url, payload, headers)
            if status_code in [401, 403]:
                # Dacă tot 401/403 => renunțăm
                _LOGGER.error(
                    "Re-autentificare eșuată (status=%s). Abandonăm cererea.",
                    status_code
                )
                raise Exception(f"Eroare la apelarea endpoint-ului: {status_code}")

        # -------------- 2) Verificăm parsatul JSON  --------------
        # Dacă status_code == 200, dar resp_data este None => înseamnă că parsarea a eșuat
        if status_code == 200 and resp_data is None and reauth:
            _LOGGER.error(
                "Răspunsul de la server nu este JSON valid. Se reîncearcă autentificarea..."
            )
            self.authenticate()
            # O nouă cerere, de data asta reauth=False
            resp_data, status_code, resp_text = self._do_request(method, url, payload, headers)
            if status_code == 200 and resp_data is None:
                # Tot nu e JSON valid, renunțăm
                _LOGGER.error(
                    "Re-request eșuat. Răspunsul nu este JSON valid nici după re-autentificare."
                )
                raise Exception("Răspunsul de la server nu este JSON valid.")

        # Dacă status_code nu e 200, aruncăm excepție
        if status_code != 200:
            _LOGGER.error("Eroare la apelarea endpoint-ului: [%s] %s", status_code, resp_text)
            raise Exception(f"Eroare la apelarea endpoint-ului: {status_code}")

        # În acest punct, status_code=200.
        # Dacă tot n-avem date decodate, e clar că ceva e greșit.
        if resp_data is None:
            _LOGGER.error("Răspunsul de la server nu este JSON valid (după reautentificare).")
            raise Exception("Răspunsul de la server nu este JSON valid.")

        return resp_data

    def _do_request(self, method, url, payload=None, headers=None):
        """
        Efectuează cererea HTTP cu session-ul curent.
        Returnează tuple: (json_data | None, status_code, resp_text).
        - Dacă status_code=200, încearcă parse JSON. Dacă eșuează, returnează (None, status_code, resp_text).
        - Altfel, returnează (None, status_code, resp_text) pentru orice cod !=200.
        """
        if headers is None:
            headers = {}

        # Adăugăm cookie-ul JSESSIONID, dacă există
        if self.token:
            self.session.cookies.set("JSESSIONID", self.token)

        _LOGGER.debug("Cerere HTTP [%s] către %s, payload=%s", method, url, payload)
        if method.upper() == "GET":
            response = self.session.get(url, headers=headers)
        elif method.upper() == "POST":
            response = self.session.post(url, json=payload, headers=headers)
        else:
            raise ValueError(f"Metodă HTTP neimplementată: {method}")

        status_code = response.status_code
        resp_text = response.text  # text brut, util pentru debugging

        if status_code != 200:
            # Nu încercăm parse JSON dacă nu e 200
            return None, status_code, resp_text

        # E 200 -> încercăm să parsez JSON
        try:
            data = response.json()
        except JSONDecodeError:
            data = None

        return data, status_code, resp_text

    # -------------------------------------------------------------------------
    #                 Autentificare
    # -------------------------------------------------------------------------
    def authenticate(self):
        """Autentifică utilizatorul și stochează cookie-ul JSESSIONID."""
        _LOGGER.debug("Inițiem procesul de autentificare pentru utilizatorul %s", self.username)
        payload = {
            "username": self.username,
            "password": self.password,
            "_spring_security_remember_me": "on"
        }

        response = self.session.post(URL_LOGIN, json=payload)

        if response.status_code == 200:
            _LOGGER.info("Autentificarea a reușit pentru %s", self.username)
            # Extragem JSESSIONID din cookies
            self.token = self.session.cookies.get("JSESSIONID")
            _LOGGER.debug("Token obținut (JSESSIONID): %s", self.token)
        else:
            _LOGGER.error(
                "Eroare la autentificare (status=%s). Răspuns=%s",
                response.status_code,
                response.text
            )
            self.token = None
            raise Exception("Autentificare eșuată.")

    # -------------------------------------------------------------------------
    #                 Metode Helper
    # -------------------------------------------------------------------------
    def _generate_timestamp_url(self, base_url, is_first_param=True):
        """Generează un URL cu timestamp actual (milisecunde)."""
        timestamp = int(datetime.now().timestamp() * 1000)
        separator = "?" if is_first_param else "&"
        return f"{base_url}{separator}timestamp={timestamp}"

    # -------------------------------------------------------------------------
    #                 Metode Publice (Accesate de integrare)
    # -------------------------------------------------------------------------
    def get_user_data(self):
        """Obține detalii despre utilizator."""
        url = self._generate_timestamp_url(URL_GET_USER_DATA)
        _LOGGER.debug("Cerere către URL-ul utilizator: %s", url)
        return self._request("GET", url)

    def get_paginated_data(self, limit=4, page=0):
        """Obține date paginate."""
        base_url = f"{URL_GET_PAGINATED}?limit={limit}&page={page}"
        # Notă: `is_first_param=False` doar dacă `URL_GET_PAGINATED` NU conține deja un '?'
        url = self._generate_timestamp_url(base_url, is_first_param=False)
        _LOGGER.debug("Cerere către URL-ul paginat: %s", url)
        return self._request("GET", url)

    def get_countries(self):
        """Obține lista țărilor."""
        _LOGGER.debug("Cerere către URL-ul țărilor: %s", URL_GET_COUNTRIES)
        return self._request("GET", URL_GET_COUNTRIES)

    def get_tranzactii(self, date_from, date_to):
        """Obține lista de tranzacții într-un interval [date_from, date_to]."""
        url = URL_TRANZACTII.format(dateFrom=date_from, dateTo=date_to)
        _LOGGER.debug("Cerere către URL-ul tranzacțiilor: %s", url)
        return self._request("GET", url)

    def get_detalii_tranzactie(self, series):
        """Obține detalii pentru o tranzacție specifică."""
        url = URL_DETALII_TRANZACTIE.format(series=series)
        _LOGGER.debug("Cerere către URL-ul detaliilor tranzacției: %s", url)
        return self._request("GET", url)

    def get_treceri_pod(self, vin, plate_no, certificate_series, period=4):
        """Obține istoricul trecerilor de pod."""
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
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
        }

        _LOGGER.debug("Cerere către trecerile de pod: %s cu payload: %s", url, payload)
        return self._request("POST", url, payload=payload, headers=headers)
