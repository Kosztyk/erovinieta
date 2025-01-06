"""Constante pentru integrarea Erovinieta."""

DOMAIN = "erovinieta"
NAME = "CNAIR eRovinieta"
VERSION = "1.0.0"
ATTRIBUTION = "Date furnizate de www.erovinieta.ro"

# URL-urile API-ului
BASE_URL = "https://www.erovinieta.ro/vignettes-portal-web"
URL_LOGIN = f"{BASE_URL}/login"
URL_GET_USER_DATA = f"{BASE_URL}/rest/anonymous/getUserData"
URL_GET_PAGINATED = f"{BASE_URL}/rest/desktop/home/getDataPaginated"
URL_GET_COUNTRIES = f"{BASE_URL}/rest/anonymous/getCountries"

# URL pentru obținerea listei de tranzacții
URL_TRANZACTII = (
    "https://www.erovinieta.ro/vignettes-portal-web/rest/transaction/getTransaction?"
    "dateFrom={dateFrom}&dateTo={dateTo}&paymentType=2&transactionType=3"
)

CONF_ISTORIC_TRANZACTII = "istoric_tranzactii"  # Cheie pentru istoricul tranzacțiilor
ISTORIC_TRANZACTII_DEFAULT = 2  # Valoare implicită în ani

# URL pentru obținerea detaliilor unei tranzacții
URL_DETALII_TRANZACTIE = (
    "https://www.erovinieta.ro/vignettes-portal-web/rest/transaction/getTransactionDetails?"
    "series={series}&transactionType=3"
)

# Configurația cheilor pentru ConfigFlow
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

# Valori implicite
DEFAULT_UPDATE_INTERVAL = 3600  # 1 oră (în secunde)
MIN_UPDATE_INTERVAL = 300       # Minim 5 minute (în secunde)
MAX_UPDATE_INTERVAL = 86400     # Maxim 1 zi (în secunde)
DEFAULT_TRANSACTION_HISTORY_YEARS = 2
