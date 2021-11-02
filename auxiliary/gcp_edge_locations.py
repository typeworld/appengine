import googlemaps

# Go to:
# https://cloud.google.com/vpc/docs/edge-locations?hl=en
# copy list of cities into the following string:

text = """
North America

Ashburn, VA, US (2)
Atlanta, GA, US (3)
Chicago, IL, US (2)
Denver, CO, US (2)
Dallas, TX, US (3)
Los Angeles, CA, US (3)
Miami, FL, US (2)
Montreal, Canada
New York, NY, US (3)
Palo Alto, CA, US
San Jose, CA, US
Santa Clara, CA, US
Seattle, WA, US (3)
Querétaro, Mexico (2)
Toronto, Canada (2)
South America

Bogotá, Colombia (2)
Buenos Aires, Argentina
Rio de Janeiro, Brazil
Santiago, Chile
São Paulo, Brazil (5)
Europe

Amsterdam, Netherlands (5)
Budapest, Hungary
Bucharest, Romania
Dublin, Ireland (2)
Frankfurt, Germany (2)
Hamburg, Germany (3)
Kiev, Ukraine (3)
Lisbon, Portugal
London, UK (7)
Madrid, Spain (2)
Marseille, France
Milan, Italy (2)
Munich, Germany
Moscow, Russia (3)
Paris, France (8)
Prague, Czech Republic
Rome, Italy
Saint Petersburg, Russia (2)
Sofia, Bulgaria
Stockholm, Sweden (3)
Warsaw, Poland (2)
Zagreb, Croatia
Zürich, Switzerland (4)
Middle East

Fujairah, United Arab Emirates (3)
Muscat, Oman
Asia Pacific

Chennai, India (3)
Hong Kong SAR, China (3)
Jakarta, Indonesia (4)
Kuala Lumpur, Malaysia (2)
Delhi, India (3)
Osaka, Japan (2)
Mumbai, India (2)
Seoul, South Korea (4)
Singapore (3)
Taipei, Taiwan (4)
Tokyo, Japan (7)
Oceania

Sydney, Australia (3)
Melbourne, Australia (2)
Africa

Johannesburg, South Africa
Mombasa, Kenya
Lagos, Nigeria (2)
"""

cities = []
geolocations = {}

for line in text.splitlines():
    if "," in line or "(" in line:
        city = line.split("(")[0].strip()
        cities.append(city)

gmaps = googlemaps.Client(key="___key_here___")
for city in cities:
    result = gmaps.geocode(city)[0]
    location = result["geometry"]["location"]
    geolocations[result["formatted_address"]] = [location["lat"], location["lng"]]

print(geolocations)
