import googlemaps
import sys

city = sys.argv[-1]

gmaps = googlemaps.Client(key="___key_here___")
result = gmaps.geocode(city)[0]["geometry"]["location"]
print([result["lat"], result["lng"]])
