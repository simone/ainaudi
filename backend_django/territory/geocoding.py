"""
Geocoding helpers for electoral sections and RDL addresses.

Uses Google Geocoding API to convert addresses to lat/lon coordinates.
Shared by geocode_sezioni and geocode_rdl management commands.

API Key resolution (in order):
1. GOOGLE_MAPS_API_KEY env var / Django setting
2. Secret Manager: secret "google-maps-api-key" (fetched via ADC)

Setup:
    # Create API key and store in Secret Manager
    gcloud services enable geocoding-backend.googleapis.com
    gcloud services enable secretmanager.googleapis.com
    KEY=$(gcloud alpha services api-keys create --display-name="Geocoding" \
          --api-target=service=geocoding-backend.googleapis.com --format="value(keyString)")
    echo -n "$KEY" | gcloud secrets create google-maps-api-key --data-file=-
"""
import logging
import math
import time

import requests

logger = logging.getLogger(__name__)

# Transient HTTP status codes that warrant a retry
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}

# Module-level cache for the API key (fetched once per process)
_cached_api_key = None


def _get_maps_api_key(api_key=None):
    """
    Resolve the Google Maps API key.

    Order:
    1. Explicit api_key parameter
    2. GOOGLE_MAPS_API_KEY from Django settings / env
    3. Secret Manager secret "google-maps-api-key"

    Returns:
        API key string, or None if unavailable.
    """
    global _cached_api_key

    if api_key:
        return api_key

    if _cached_api_key:
        return _cached_api_key

    # Try Django settings / env var
    try:
        from django.conf import settings
        key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        if key:
            _cached_api_key = key
            return key
    except Exception:
        pass

    # Try Secret Manager via ADC
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()

        # Resolve project ID from env or settings
        import os
        project = os.environ.get('GOOGLE_CLOUD_PROJECT', '')
        if not project:
            try:
                from django.conf import settings as s
                project = getattr(s, 'VERTEX_AI_PROJECT', '') or getattr(s, 'GCS_PROJECT_ID', '')
            except Exception:
                pass

        if project:
            secret_name = (
                f"projects/{project}/secrets/google-maps-api-key/versions/latest"
            )
            response = client.access_secret_version(
                request={"name": secret_name}
            )
            key = response.payload.data.decode("UTF-8").strip()
            if key:
                _cached_api_key = key
                logger.info("API key loaded from Secret Manager")
                return key
    except ImportError:
        logger.debug("google-cloud-secret-manager not installed, skipping")
    except Exception as e:
        logger.debug("Secret Manager lookup failed: %s", e)

    return None


def geocode_address(address, api_key=None, max_retries=3, base_delay=1.0):
    """
    Geocode an address via Google Geocoding API.

    Args:
        address: Full address string (e.g. "Via Roma 1, Roma, RM, Italia")
        api_key: Google Maps API key (optional, resolved automatically)
        max_retries: Max retry attempts on transient errors
        base_delay: Base delay in seconds for exponential backoff

    Returns:
        Tuple (lat, lon, place_id, location_type) on success, None on failure.
        location_type is one of: ROOFTOP, RANGE_INTERPOLATED,
        GEOMETRIC_CENTER, APPROXIMATE.
    """
    resolved_key = _get_maps_api_key(api_key)
    if not resolved_key:
        logger.error(
            "Google Maps API key not found. Set GOOGLE_MAPS_API_KEY env var "
            "or store in Secret Manager as 'google-maps-api-key'."
        )
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": resolved_key,
        "region": "it",
    }

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
        except requests.RequestException as e:
            logger.warning("Geocode request error (attempt %d): %s", attempt + 1, e)
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
                continue
            return None

        if resp.status_code in _TRANSIENT_STATUS_CODES:
            logger.warning(
                "Geocode HTTP %d (attempt %d)", resp.status_code, attempt + 1
            )
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
                continue
            return None

        if resp.status_code != 200:
            logger.error("Geocode HTTP %d for '%s'", resp.status_code, address)
            return None

        data = resp.json()
        status = data.get("status")

        if status == "OVER_QUERY_LIMIT":
            logger.warning("OVER_QUERY_LIMIT (attempt %d)", attempt + 1)
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
                continue
            return None

        if status != "OK" or not data.get("results"):
            logger.debug("Geocode status=%s for '%s'", status, address)
            return None

        result = data["results"][0]
        location = result["geometry"]["location"]
        location_type = result["geometry"].get("location_type", "APPROXIMATE")
        place_id = result.get("place_id", "")

        return (
            round(location["lat"], 6),
            round(location["lng"], 6),
            place_id,
            location_type,
        )

    return None


def build_section_address(sezione):
    """
    Build a geocodable address string for an electoral section.

    Handles cases where indirizzo already contains comune/provincia
    (e.g. "Via Roma 1, Affile, RM") to avoid duplication.

    Args:
        sezione: SezioneElettorale instance (with comune relation loaded)

    Returns:
        Address string, e.g. "VIA VALLOMBROSA 31, Roma, RM, Italia"
    """
    indirizzo = (sezione.indirizzo or "").strip()
    comune = sezione.comune.nome
    sigla = sezione.comune.provincia.sigla
    indirizzo_upper = indirizzo.upper()

    # Check if indirizzo already ends with "Comune, XX" or "Comune"
    already_has_comune = (
        comune.upper() in indirizzo_upper
    )

    parts = [indirizzo] if indirizzo else []
    if not already_has_comune:
        parts.append(comune)
        parts.append(sigla)
    parts.append("Italia")
    return ", ".join(parts)


def build_rdl_address(rdl):
    """
    Build a geocodable address string for an RDL registration.

    Uses domicilio address if fuorisede, otherwise residenza.

    Args:
        rdl: RdlRegistration instance

    Returns:
        Address string, e.g. "Via Cassia 472, Roma, RM, Italia"
    """
    if rdl.fuorisede and rdl.indirizzo_domicilio and rdl.comune_domicilio:
        indirizzo = rdl.indirizzo_domicilio.strip()
        comune = rdl.comune_domicilio.strip()
    else:
        indirizzo = rdl.indirizzo_residenza.strip()
        comune = rdl.comune_residenza.strip()

    return f"{indirizzo}, {comune}, Italia"


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points (in km).

    Args:
        lat1, lon1: Coordinates of point 1 (decimal degrees)
        lat2, lon2: Coordinates of point 2 (decimal degrees)

    Returns:
        Distance in kilometers.
    """
    R = 6371.0  # Earth radius in km

    lat1_r = math.radians(float(lat1))
    lat2_r = math.radians(float(lat2))
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
