"""Healthcare provider service (Overpass + fallback to mock providers)"""
from typing import List, Optional
import json
import os
import requests
from math import radians, sin, cos, sqrt, atan2

from app.models import Provider, ProviderRequest
from app.config import settings


def load_mock_providers() -> List[Provider]:
    """Load mock healthcare providers"""
    providers_file = os.path.join(os.path.dirname(__file__), "..", "data", "mock_providers.json")

    try:
        with open(providers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [Provider(**provider) for provider in data]
    except FileNotFoundError:
        # default set (same as before)
        return [
            Provider(
                id="1",
                name="City General Hospital",
                type="hospital",
                address="123 Main Street, City, State 12345",
                phone="(555) 123-4567",
                distance=2.5,
                latitude=37.7749,
                longitude=-122.4194
            ),
            Provider(
                id="2",
                name="Community Health Clinic",
                type="clinic",
                address="456 Oak Avenue, City, State 12345",
                phone="(555) 234-5678",
                distance=3.1,
                latitude=37.7849,
                longitude=-122.4094
            ),
            Provider(
                id="3",
                name="Downtown Pharmacy",
                type="pharmacy",
                address="789 Elm Street, City, State 12345",
                phone="(555) 345-6789",
                distance=1.8,
                latitude=37.7649,
                longitude=-122.4294
            ),
            Provider(
                id="4",
                name="Urgent Care Center",
                type="clinic",
                address="321 Pine Road, City, State 12345",
                phone="(555) 456-7890",
                distance=4.2,
                latitude=37.7949,
                longitude=-122.4394
            )
        ]


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers (Haversine formula)"""
    R = 6371.0  # Earth's radius in kilometers

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def _overpass_query(lat: float, lon: float, radius_m: int = 5000, limit: int = 10) -> List[dict]:
    """
    Query Overpass API for nearby healthcare amenities.
    Returns raw JSON elements (nodes/ways/relations).
    """
    # Overpass QL: find nodes/ways/relations with amenity ~ clinic|hospital|doctors|pharmacy
    q = f"""
    [out:json][timeout:25];
    (
      node(around:{radius_m},{lat},{lon})["amenity"~"clinic|hospital|doctors|pharmacy"];
      way(around:{radius_m},{lat},{lon})["amenity"~"clinic|hospital|doctors|pharmacy"];
      relation(around:{radius_m},{lat},{lon})["amenity"~"clinic|hospital|doctors|pharmacy"];
    );
    out center {limit};
    """
    url = "https://overpass-api.de/api/interpreter"
    headers = {
        "User-Agent": "HealthGuide/1.0 (contact@example.com)"
    }
    resp = requests.post(url, data={"data": q}, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json().get("elements", [])


def _element_to_provider(elem: dict, origin_lat: float, origin_lon: float) -> Provider:
    """Convert Overpass element to Provider model and compute distance"""
    tags = elem.get("tags", {}) or {}
    name = tags.get("name") or tags.get("operator") or tags.get("healthcare") or "Unnamed Clinic"
    amenity = tags.get("amenity", "clinic")
    # address assembly (best effort)
    addr_parts = []
    for k in ("addr:street", "addr:housenumber", "addr:postcode", "addr:city"):
        if tags.get(k):
            addr_parts.append(tags.get(k))
    address = ", ".join(addr_parts) if addr_parts else (tags.get("address") or tags.get("description") or elem.get("type", ""))
    # coordinates: node has lat/lon; way/relation often have 'center'
    lat = elem.get("lat") or elem.get("center", {}).get("lat")
    lon = elem.get("lon") or elem.get("center", {}).get("lon")
    distance = None
    if lat and lon:
        try:
            distance = round(calculate_distance(origin_lat, origin_lon, float(lat), float(lon)), 2)
        except Exception:
            distance = None

    provider = Provider(
        id=str(elem.get("id")),
        name=name,
        type=amenity,
        address=address or "Address not available",
        phone=tags.get("phone", tags.get("contact:phone", "")),
        distance=distance,
        latitude=float(lat) if lat else None,
        longitude=float(lon) if lon else None
    )
    return provider


def get_providers(request: ProviderRequest) -> List[Provider]:
    """
    Get healthcare providers near the specified location.
    Uses Overpass API (OpenStreetMap) and falls back to mock data.
    """
    try:
        # convert km radius to meters for Overpass
        radius_m = int(request.radius * 1000)
        raw = _overpass_query(request.latitude, request.longitude, radius_m=radius_m, limit=25)

        providers: List[Provider] = []
        for elem in raw:
            try:
                provider = _element_to_provider(elem, request.latitude, request.longitude)
                # filter by type if requested
                if request.provider_type:
                    if provider.type and request.provider_type.lower() not in provider.type.lower():
                        continue
                providers.append(provider)
            except Exception:
                continue

        # sort by distance if available and filter by user radius
        providers = [p for p in providers if p.distance is not None and p.distance <= request.radius]
        providers.sort(key=lambda x: x.distance or float('inf'))

        # If no providers found via Overpass, fallback to mock
        if not providers:
            return _get_filtered_mock(request)

        return providers

    except requests.HTTPError as http_err:
        # Overpass can be rate-limited or down; fallback to mock
        print(f"Overpass HTTP error: {http_err}")
        return _get_filtered_mock(request)
    except Exception as e:
        print(f"Overpass query error: {e}")
        return _get_filtered_mock(request)


def _get_filtered_mock(request: ProviderRequest) -> List[Provider]:
    """Apply filtering to mock list (used when Overpass fails)"""
    providers = load_mock_providers()
    # filter by provider type if specified
    if request.provider_type:
        providers = [p for p in providers if p.type == request.provider_type]
    # compute actual distances for mock items if lat/lon present
    for p in providers:
        if p.latitude is not None and p.longitude is not None:
            p.distance = round(calculate_distance(request.latitude, request.longitude, p.latitude, p.longitude), 2)
    filtered = [p for p in providers if p.distance is not None and p.distance <= request.radius]
    filtered.sort(key=lambda x: x.distance or float('inf'))
    return filtered


def search_providers_google_maps(request: ProviderRequest) -> List[Provider]:
    """Search providers using Google Maps API (requires API key). Placeholder."""
    if not settings.maps_api_key:
        return get_providers(request)
    # TODO: Implement Google Places API integration with API key
    return get_providers(request)
