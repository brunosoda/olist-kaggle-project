# src/test_ors.py
import os
from pathlib import Path

# -------------------------------------------------
# Load environment variables from .env
# -------------------------------------------------
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

ORS_API_KEY = os.getenv("ORS_API_KEY")
if not ORS_API_KEY:
    raise RuntimeError("ORS_API_KEY not found in .env")

# -------------------------------------------------
# Call OpenRouteService for a simple example route
# -------------------------------------------------
import openrouteservice

client = openrouteservice.Client(key=ORS_API_KEY)

# Example coordinates: São Paulo (lat/lng) → Rio de Janeiro (lat/lng)
coords = [(-46.633308, -23.550520), (-43.2075, -22.90278)]

route = client.directions(
    coordinates=coords,
    profile="driving-car",
    format="json",
    units="km",          # distance returned in kilometers
    geometry=False,
    instructions=False,
)

summary = route["routes"][0]["summary"]
distance_km = summary["distance"]          # km
duration_min = summary["duration"] / 60.0   # minutes

print(f"Distance: {distance_km:.2f} km")
print(f"Estimated duration: {duration_min:.1f} min")
