"""
WO Search Strategy: Find WO patents via Google Search.
"""
import re
import urllib.parse
from typing import List, Set
from .stealth_browser import StealthBrowser
from config.settings import (
    GOOGLE_SEARCH_DELAY_MIN,
    GOOGLE_SEARCH_DELAY_MAX,
    MAX_GOOGLE_QUERIES
)


class WOSearcher:
    """Searches for WO patents using Google Search."""
    
    def __init__(self, proxy_manager):
        self.proxy_manager = proxy_manager
    
    async def search_wos(
        self,
        molecule_name: str,
        dev_codes: List[str],
        cas_number: str = None
    ) -> Set[str]:
        """
        Search for WO patents using Google Search.
        
        Args:
            molecule_name: Name of the molecule
            dev_codes: Development codes (synonyms) from PubChem
            cas_number: CAS registry number
            
        Returns:
            Set of WO patent numbers found
        """
        found_wos = set()
        
        # Build search queries
        queries = self._build_queries(molecule_name, dev_codes, cas_number)
        
        print(f"🔍 WO Search: {len(queries[:MAX_GOOGLE_QUERIES])} queries")
        
        # Execute queries
        for idx, query in enumerate(queries[:MAX_GOOGLE_QUERIES], 1):
            try:
                print(f"   Query {idx}/{min(len(queries), MAX_GOOGLE_QUERIES)}: {query[:60]}...")
                
                # Get proxy
                proxy = self.proxy_manager.get_proxy("scrapingbee")
                
                # Create browser
                browser = StealthBrowser(proxy)
                await browser.setup()
                
                # Create page
                page = await browser.new_page()
                
                # Build search URL
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                
                # Navigate to Google
                await page.goto(search_url, wait_until='networkidle', timeout=30000)
                
                # Optional: Scroll to load more results
                await browser.scroll_page(page)
                
                # Get page content
                content = await page.content()
                
                # Extract WO numbers
                wos = self._extract_wo_numbers(content)
                
                if wos:
                    print(f"      ✅ Found {len(wos)} WOs: {', '.join(list(wos)[:3])}...")
                    found_wos.update(wos)
                else:
                    print(f"      ⚪ No WOs found")
                
                # Close browser
                await browser.close()
                
                # Human delay before next query
                if idx < min(len(queries), MAX_GOOGLE_QUERIES):
                    await browser.human_delay(
                        GOOGLE_SEARCH_DELAY_MIN,
                        GOOGLE_SEARCH_DELAY_MAX
                    )
                
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:60]}")
                continue
        
        print(f"✅ WO Search complete: {len(found_wos)} unique WOs found")
        return found_wos
    
    def _build_queries(
        self,
        molecule: str,
        dev_codes: List[str],
        cas: str
    ) -> List[str]:
        """Build Google search queries."""
        queries = []
        
        # Base query with molecule name
        queries.append(f'"{molecule}" patent WO site:patents.google.com')
        
        # Query with CAS number if available
        if cas:
            queries.append(f'"{cas}" patent WO site:patents.google.com')
        
        # Queries with development codes (top 3)
        for code in dev_codes[:3]:
            if code and len(code) >= 3:  # Avoid very short codes
                queries.append(f'"{code}" patent WO site:patents.google.com')
        
        # Targeted queries by year ranges (to catch older patents)
        year_ranges = [
            (2000, 2005),
            (2006, 2010),
            (2011, 2015),
            (2016, 2020),
            (2021, 2025)
        ]
        
        for start, end in year_ranges[:2]:  # Only first 2 ranges to limit queries
            queries.append(
                f'"{molecule}" patent WO{start}..WO{end} site:patents.google.com'
            )
        
        # Combination query with molecule OR top dev code
        if dev_codes:
            top_code = dev_codes[0]
            queries.append(
                f'"{molecule}" OR "{top_code}" patent WO site:patents.google.com'
            )
        
        return queries
    
    def _extract_wo_numbers(self, html: str) -> Set[str]:
        """
        Extract WO patent numbers from HTML content.
        
        Matches patterns like:
        - WO2011051540
        - WO2023161458
        - WO/2011/051540 (with slashes)
        """
        wo_patterns = [
            r'WO\d{4}\d{6}',  # WO2011051540
            r'WO\s*\d{4}\s*/?\s*\d{6}',  # WO 2011 051540 or WO2011/051540
            r'WO/\d{4}/\d{6}'  # WO/2011/051540
        ]
        
        found_wos = set()
        
        for pattern in wo_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            
            for match in matches:
                # Normalize to WO2011051540 format
                normalized = re.sub(r'[/\s]', '', match.upper())
                
                # Ensure it starts with WO
                if normalized.startswith('WO'):
                    found_wos.add(normalized)
        
        return found_wos
