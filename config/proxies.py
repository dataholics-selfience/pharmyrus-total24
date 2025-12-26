"""
Proxy configuration for Google Patents crawling.
Hardcoded from API-keys_proxies.txt for immediate Railway deployment.
"""

SCRAPINGBEE_KEYS = [
    "7VS5IQND98IMXEO5DLQ1TWD2R325XN8QVYEU5FO",
    "JH93P8ZDZODXOXEUE88TDXLET2VZGC5C541XVKU6Y3NTHLG945MXXRF66L89V8SGD1S8FTJY834977ZK",
    "UNR05KRW150G1KB5N5IKYE5RF03ALDKJL7QWLDN525VWVY7UGUWFKDCVVEZVG5EWR4LJES3NSLZ5TP7J",
    "IEJSDS78L9GXVDBXB3ZVX2GDZIC7436ZE21GLVP5IN17CYFUGPK5QLXKMAGCYN4FEDS4UOHNRL8JW6IW",
    "DVLM6WH9FWFXKYXRUSRQ5WRM9ZJP1TVRPEVZ7RBDT41QLSKRZJ0LRFFT5JFU5P50SYTWAOM53AW0ZEER",
    "M8CRUG9L0D1EH8QKUTR64LUNPW8T3U9GPMX7X65ZNRJIOWVFH1JOXFTUXYRZEGMAUPQUM719YBC4XLLE"
]

WEBSHARE_KEYS = [
    "usj7vxj7iwvcr9yij6tsv1vaboczrocajjw3uuih",
    "64vy07th7nqa4i3zgdb934aw9ipdxgsiyhrmm0m7",
    "8rnj7xfm6rwc85opcrsvl3a53omb6qd6ctw0budc",
    "yabhnbwhzhlqpmqetth4s4fu2z5aw6tdumwf3eto",
    "x09f9lthxs63ghkjs7a05xfjyqg8jgtngd1dblr5"
]

PROXYSCRAPE_KEYS = [
    "ldisb6dpcstrdd63k4un",
    "kq5akm7j452b0z75mmic",
    "1jtnj99nsronw28oj7uf"
]

class ProxyManager:
    """Manages proxy rotation across multiple providers."""
    
    def __init__(self):
        self.scrapingbee_idx = 0
        self.webshare_idx = 0
        self.proxyscrape_idx = 0
    
    def get_scrapingbee_proxy(self) -> str:
        """Get next ScrapingBee proxy (best for Google)."""
        key = SCRAPINGBEE_KEYS[self.scrapingbee_idx]
        self.scrapingbee_idx = (self.scrapingbee_idx + 1) % len(SCRAPINGBEE_KEYS)
        return f"http://{key}:@proxy.scrapingbee.com:8886"
    
    def get_webshare_proxy(self) -> str:
        """Get next Webshare residential proxy."""
        key = WEBSHARE_KEYS[self.webshare_idx]
        self.webshare_idx = (self.webshare_idx + 1) % len(WEBSHARE_KEYS)
        return f"http://{key}:@proxy.webshare.io:80"
    
    def get_proxyscrape_proxy(self) -> str:
        """Get next ProxyScrape proxy."""
        key = PROXYSCRAPE_KEYS[self.proxyscrape_idx]
        self.proxyscrape_idx = (self.proxyscrape_idx + 1) % len(PROXYSCRAPE_KEYS)
        return f"http://{key}:@proxy.proxyscrape.com:1000"
    
    def get_proxy(self, priority: str = "scrapingbee") -> str:
        """Get proxy with priority (scrapingbee > webshare > proxyscrape)."""
        if priority == "scrapingbee":
            return self.get_scrapingbee_proxy()
        elif priority == "webshare":
            return self.get_webshare_proxy()
        else:
            return self.get_proxyscrape_proxy()
    
    def get_total_proxies(self) -> int:
        """Get total number of available proxies."""
        return len(SCRAPINGBEE_KEYS) + len(WEBSHARE_KEYS) + len(PROXYSCRAPE_KEYS)
