"""
General settings for Pharmyrus v27.
"""

# Version
VERSION = "Pharmyrus v27"

# Supported countries
SUPPORTED_COUNTRIES = {
    "BR": "Brazil",
    "US": "United States",
    "EP": "European Patent",
    "CN": "China",
    "JP": "Japan",
    "KR": "South Korea",
    "IN": "India",
    "MX": "Mexico",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colombia",
    "PE": "Peru",
    "CA": "Canada",
    "AU": "Australia",
    "RU": "Russia",
    "ZA": "South Africa"
}

# Google Patents settings
GOOGLE_SEARCH_DELAY_MIN = 15  # seconds
GOOGLE_SEARCH_DELAY_MAX = 22  # seconds
GOOGLE_PATENTS_DELAY_MIN = 10  # seconds
GOOGLE_PATENTS_DELAY_MAX = 18  # seconds
MAX_GOOGLE_QUERIES = 10  # max queries per molecule

# EPO OPS settings
EPO_CONSUMER_KEY = "DQOWzcWqkrW75AKZUFrS6SL8qGJoCLAD"
EPO_CONSUMER_SECRET = "gkMAjPy2DHFBp6CA"

# Crawler settings
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Performance settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
TIMEOUT = 30  # seconds

# Logging
LOG_LEVEL = "INFO"
