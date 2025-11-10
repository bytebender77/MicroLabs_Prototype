import httpx
from typing import Dict, List, Optional, Tuple
import os
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

class GeolocationService:
    """
    Smart geolocation service to find nearby healthcare providers.
    Uses Google Places API, OpenStreetMap, or other providers.
    """
    
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.geolocator = Nominatim(user_agent="healthguide")
    
    async def get_user_location_from_ip(self, ip_address: str) -> Dict:
        """
        Get approximate location from IP address (fallback).
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://ip-api.com/json/{ip_address}"
                )
                data = response.json()
                return {
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                    "city": data.get("city"),
                    "region": data.get("regionName"),
                    "country": data.get("country"),
                    "accuracy": "city_level"  # Low accuracy
                }
        except Exception as e:
            print(f"IP geolocation error: {e}")
            return None
    
    async def find_nearby_healthcare_providers(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 5,
        provider_type: str = "hospital",  # hospital, clinic, pharmacy
        limit: int = 10
    ) -> List[Dict]:
        """
        Find nearby healthcare providers using Google Places API.
        """
        if not self.google_api_key:
            return await self._find_nearby_osm(latitude, longitude, provider_type)
        
        try:
            async with httpx.AsyncClient() as client:
                # Google Places API - Nearby Search
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    "location": f"{latitude},{longitude}",
                    "radius": radius_km * 1000,  # Convert to meters
                    "type": provider_type,
                    "keyword": "fever doctor urgent care",
                    "key": self.google_api_key
                }
                
                response = await client.get(url, params=params)
                data = response.json()
                
                providers = []
                for place in data.get("results", [])[:limit]:
                    place_location = place.get("geometry", {}).get("location", {})
                    place_lat = place_location.get("lat")
                    place_lng = place_location.get("lng")
                    
                    # Calculate distance
                    distance = self._calculate_distance(
                        (latitude, longitude),
                        (place_lat, place_lng)
                    )
                    
                    # Get additional details
                    place_details = await self._get_place_details(
                        place.get("place_id")
                    )
                    
                    providers.append({
                        "name": place.get("name"),
                        "address": place.get("vicinity"),
                        "type": provider_type,
                        "distance_km": distance,
                        "rating": place.get("rating"),
                        "total_ratings": place.get("user_ratings_total"),
                        "open_now": place.get("opening_hours", {}).get("open_now"),
                        "latitude": place_lat,
                        "longitude": place_lng,
                        "phone": place_details.get("phone"),
                        "website": place_details.get("website"),
                        "google_maps_url": f"https://maps.google.com/?q={place_lat},{place_lng}",
                        "place_id": place.get("place_id")
                    })
                
                # Sort by distance
                providers.sort(key=lambda x: x["distance_km"])
                return providers
        
        except Exception as e:
            print(f"Google Places API error: {e}")
            return await self._find_nearby_osm(latitude, longitude, provider_type, limit)
    
    async def _get_place_details(self, place_id: str) -> Dict:
        """Get additional place details from Google Places API"""
        try:
            async with httpx.AsyncClient() as client:
                url = "https://maps.googleapis.com/maps/api/place/details/json"
                params = {
                    "place_id": place_id,
                    "fields": "formatted_phone_number,website,opening_hours,international_phone_number",
                    "key": self.google_api_key
                }
                response = await client.get(url, params=params)
                data = response.json()
                result = data.get("result", {})
                return {
                    "phone": result.get("formatted_phone_number") or result.get("international_phone_number"),
                    "website": result.get("website"),
                    "opening_hours": result.get("opening_hours", {})
                }
        except:
            return {}
    
    async def find_ambulance_services(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 10
    ) -> List[Dict]:
        """
        Find nearby ambulance services and emergency contacts.
        """
        try:
            # Search for ambulance services
            ambulance_providers = await self.find_nearby_healthcare_providers(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                provider_type="hospital",  # Hospitals typically have ambulance services
                limit=5
            )
            
            # Add emergency numbers based on country (you can expand this)
            emergency_numbers = {
                "India": {
                    "ambulance": "108",
                    "emergency": "112",
                    "police": "100",
                    "fire": "101"
                },
                "US": {
                    "emergency": "911"
                },
                "UK": {
                    "emergency": "999"
                }
            }
            
            # Try to determine country from location (simplified)
            country = "India"  # Default, can be enhanced with reverse geocoding
            
            return {
                "hospitals": ambulance_providers,
                "emergency_numbers": emergency_numbers.get(country, emergency_numbers["India"]),
                "ambulance_advice": "For life-threatening emergencies, call ambulance immediately."
            }
        except Exception as e:
            print(f"Error finding ambulance services: {e}")
            return {
                "hospitals": [],
                "emergency_numbers": {"ambulance": "108", "emergency": "112"},
                "ambulance_advice": "Call emergency services immediately."
            }
    
    async def _find_nearby_osm(
        self,
        latitude: float,
        longitude: float,
        provider_type: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Fallback: Use OpenStreetMap Overpass API (free, no API key needed).
        Returns mock data if OSM API fails.
        """
        try:
            # Map provider type to OSM amenity
            osm_amenity = {
                "hospital": "hospital",
                "clinic": "clinic",
                "pharmacy": "pharmacy",
                "doctor": "doctors"
            }.get(provider_type, "hospital")
            
            # Overpass API query
            radius = 5000  # 5km in meters
            query = f"""
            [out:json];
            (
              node["amenity"="{osm_amenity}"](around:{radius},{latitude},{longitude});
              way["amenity"="{osm_amenity}"](around:{radius},{latitude},{longitude});
            );
            out body;
            """
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://overpass-api.de/api/interpreter",
                    data={"data": query},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                providers = []
                for element in data.get("elements", []):
                    tags = element.get("tags", {})
                    elem_lat = element.get("lat") or (element.get("center", {}) or {}).get("lat")
                    elem_lon = element.get("lon") or (element.get("center", {}) or {}).get("lon")
                    
                    if elem_lat and elem_lon:
                        distance = self._calculate_distance(
                            (latitude, longitude),
                            (elem_lat, elem_lon)
                        )
                        
                        # Build address from available fields
                        addr_parts = [
                            tags.get("addr:housenumber"),
                            tags.get("addr:street"),
                            tags.get("addr:city"),
                            tags.get("addr:state"),
                            tags.get("addr:postcode")
                        ]
                        address = ", ".join([p for p in addr_parts if p]) or tags.get("addr:full") or "Address not available"
                        
                        providers.append({
                            "name": tags.get("name", "Unnamed Provider"),
                            "address": address,
                            "type": provider_type,
                            "distance_km": round(distance, 2),
                            "latitude": elem_lat,
                            "longitude": elem_lon,
                            "phone": tags.get("phone") or tags.get("contact:phone"),
                            "website": tags.get("website") or tags.get("contact:website"),
                            "google_maps_url": f"https://maps.google.com/?q={elem_lat},{elem_lon}",
                            "source": "OpenStreetMap"
                        })
                
                providers.sort(key=lambda x: x["distance_km"])
                return providers[:limit]
        
        except Exception as e:
            print(f"OSM API error: {e}")
            # Return mock data as fallback
            return self._get_mock_providers(latitude, longitude, provider_type, limit)
    
    def _get_mock_providers(self, latitude: float, longitude: float, provider_type: str, limit: int = 10) -> List[Dict]:
        """Return mock provider data when APIs fail"""
        # Calculate actual distances for mock providers
        base_providers = [
            {
                "name": "Community Health Clinic",
                "address": "456 Oak Avenue, City, State 12345",
                "type": "clinic",
                "latitude": latitude + 0.012,
                "longitude": longitude + 0.008,
                "phone": "(555) 234-5678",
                "website": None,
                "source": "Mock Data",
                "rating": 4.5,
                "total_ratings": 120,
                "open_now": True
            },
            {
                "name": "Downtown Pharmacy",
                "address": "789 Elm Street, City, State 12345",
                "type": "pharmacy",
                "latitude": latitude + 0.015,
                "longitude": longitude - 0.010,
                "phone": "(555) 345-6789",
                "website": None,
                "source": "Mock Data",
                "rating": 4.2,
                "total_ratings": 85,
                "open_now": True
            },
            {
                "name": "City General Hospital",
                "address": "123 Main Street, City, State 12345",
                "type": "hospital",
                "latitude": latitude - 0.018,
                "longitude": longitude + 0.012,
                "phone": "(555) 456-7890",
                "website": "https://hospital.example.com",
                "source": "Mock Data",
                "rating": 4.7,
                "total_ratings": 200,
                "open_now": True
            },
            {
                "name": "Urgent Care Center",
                "address": "321 Park Avenue, City, State 12345",
                "type": "clinic",
                "latitude": latitude - 0.010,
                "longitude": longitude - 0.015,
                "phone": "(555) 567-8901",
                "website": None,
                "source": "Mock Data",
                "rating": 4.3,
                "total_ratings": 95,
                "open_now": True
            }
        ]
        
        # Calculate distances and add google_maps_url
        for provider in base_providers:
            distance = self._calculate_distance(
                (latitude, longitude),
                (provider["latitude"], provider["longitude"])
            )
            provider["distance_km"] = distance
            provider["google_maps_url"] = f"https://maps.google.com/?q={provider['latitude']},{provider['longitude']}"
        
        # Filter by provider type if specified
        if provider_type and provider_type != "all":
            base_providers = [p for p in base_providers if p["type"] == provider_type]
        
        # Sort by distance
        base_providers.sort(key=lambda x: x["distance_km"])
        
        return base_providers[:limit]
    
    @staticmethod
    def _calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate distance in kilometers"""
        return round(geodesic(point1, point2).kilometers, 2)