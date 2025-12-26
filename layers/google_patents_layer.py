"""
Google Patents Layer - Comprehensive web crawling.
"""
from typing import Dict, List, Set
from google_patents.wo_searcher import WOSearcher
from config.proxies import ProxyManager


class GooglePatentsLayer:
    """Layer 2: Google Patents crawling."""
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.wo_searcher = WOSearcher(self.proxy_manager)
    
    async def search(
        self,
        molecule_name: str,
        pubchem_data: Dict,
        existing_wos: Set[str],
        existing_brs: Set[str],
        target_countries: List[str]
    ) -> Dict:
        """
        Search patents using Google Patents crawling.
        
        Args:
            molecule_name: Name of the molecule
            pubchem_data: PubChem data (dev codes, CAS)
            existing_wos: WOs already found by EPO
            existing_brs: BRs already found by EPO
            target_countries: List of target countries
            
        Returns:
            Dictionary with additional WOs and country patents
        """
        print(f"🟢 Google Patents Layer: Complementing EPO results...")
        
        # Extract PubChem info
        dev_codes = pubchem_data.get('pubchem_dev_codes', [])
        cas_number = pubchem_data.get('pubchem_cas')
        
        # STRATEGY 1: WO Search via Google Search
        print(f"   📍 Strategy 1: WO Search...")
        google_wos = await self.wo_searcher.search_wos(
            molecule_name=molecule_name,
            dev_codes=dev_codes,
            cas_number=cas_number
        )
        
        # Find additional WOs (not in EPO results)
        additional_wos = google_wos - existing_wos
        
        print(f"   ✅ Found {len(additional_wos)} additional WOs")
        
        # STRATEGY 2: BR Family Extraction
        # TODO: Implement in next phase
        additional_brs = {}
        
        # STRATEGY 3: BR Direct Search
        # TODO: Implement in next phase
        
        result = {
            'additional_wos': list(additional_wos),
            'additional_brs': additional_brs
        }
        
        return result
