"""
EPO OPS Layer - Fast patent search using official API.
Based on Pharmyrus v26 implementation.
"""
import time
import pubchempy as pcp
from typing import List, Dict, Set
from datetime import datetime
from epo_ops import Client
from config.settings import EPO_CONSUMER_KEY, EPO_CONSUMER_SECRET


class EPOLayer:
    """Layer 1: EPO OPS API search."""
    
    def __init__(self):
        self.client = Client(
            key=EPO_CONSUMER_KEY,
            secret=EPO_CONSUMER_SECRET
        )
    
    async def search(
        self,
        molecule_name: str,
        brand_name: str = None,
        countries: List[str] = None
    ) -> Dict:
        """
        Search patents using EPO OPS API.
        
        Args:
            molecule_name: Name of the molecule
            brand_name: Commercial brand name
            countries: List of target countries (e.g., ['BR', 'US'])
            
        Returns:
            Dictionary with WO patents and country-specific patents
        """
        start_time = time.time()
        
        print(f"🔵 EPO Layer: Searching for {molecule_name}...")
        
        # Get PubChem data
        pubchem_data = self._get_pubchem_data(molecule_name)
        
        # Extract dev codes and CAS
        dev_codes = pubchem_data.get('dev_codes', [])
        cas_number = pubchem_data.get('cas', None)
        
        print(f"   ℹ️  PubChem: {len(dev_codes)} dev codes, CAS: {cas_number}")
        
        # Search WO patents
        wo_patents = self._search_wo_patents(molecule_name, dev_codes, cas_number)
        
        print(f"   ✅ Found {len(wo_patents)} WO patents")
        
        # Map WOs to target countries
        patents_by_country = {}
        
        if countries:
            for country in countries:
                country_patents = self._map_wo_to_country(wo_patents, country)
                if country_patents:
                    patents_by_country[country] = country_patents
                    print(f"   ✅ {country}: {len(country_patents)} patents")
        
        elapsed = time.time() - start_time
        
        # Build result
        result = {
            'metadata': {
                'molecule': molecule_name,
                'brand_name': brand_name,
                'search_date': datetime.now().isoformat(),
                'target_countries': countries or [],
                'elapsed_seconds': round(elapsed, 2),
                'version': 'Pharmyrus v27 (EPO Layer)'
            },
            'summary': {
                'total_wos': len(wo_patents),
                'total_patents': sum(len(p) for p in patents_by_country.values()),
                'by_country': {k: len(v) for k, v in patents_by_country.items()},
                'pubchem_dev_codes': dev_codes,
                'pubchem_cas': cas_number
            },
            'wo_patents': sorted(list(wo_patents)),
            'patents_by_country': patents_by_country
        }
        
        return result
    
    def _get_pubchem_data(self, molecule_name: str) -> Dict:
        """Get PubChem data for molecule."""
        try:
            compounds = pcp.get_compounds(molecule_name, 'name')
            
            if not compounds:
                return {'dev_codes': [], 'cas': None}
            
            compound = compounds[0]
            
            # Get synonyms (dev codes)
            synonyms = compound.synonyms or []
            
            # Filter for dev codes (usually uppercase, contain numbers/hyphens)
            dev_codes = [
                s for s in synonyms[:50]  # Top 50 synonyms
                if any(c.isdigit() for c in s) and len(s) < 30
            ]
            
            return {
                'dev_codes': dev_codes[:20],  # Top 20
                'cas': getattr(compound, 'cas', None)
            }
            
        except Exception as e:
            print(f"   ⚠️  PubChem error: {e}")
            return {'dev_codes': [], 'cas': None}
    
    def _search_wo_patents(
        self,
        molecule_name: str,
        dev_codes: List[str],
        cas_number: str
    ) -> Set[str]:
        """Search for WO patents using EPO OPS."""
        found_wos = set()
        
        # Build search terms
        search_terms = [molecule_name]
        if cas_number:
            search_terms.append(cas_number)
        search_terms.extend(dev_codes[:5])  # Top 5 dev codes
        
        for term in search_terms:
            try:
                # EPO OPS query
                response = self.client.published_data_search(
                    cql=f'ti,ab="{term}" AND pn=WO*',
                    range_begin=1,
                    range_end=100
                )
                
                # Parse WO numbers from response
                # (Simplified - real implementation would parse XML)
                # For now, we'll return empty set as placeholder
                # This would need actual XML parsing implementation
                
            except Exception as e:
                print(f"   ⚠️  EPO search error for '{term}': {e}")
                continue
        
        # NOTE: This is a placeholder. Real implementation would:
        # 1. Parse EPO OPS XML responses
        # 2. Extract publication numbers
        # 3. Filter for WO patents
        # 4. Return set of WO numbers
        
        return found_wos
    
    def _map_wo_to_country(self, wo_patents: Set[str], country: str) -> List[Dict]:
        """Map WO patents to country-specific patents using family data."""
        country_patents = []
        
        for wo in list(wo_patents)[:20]:  # Limit to avoid rate limits
            try:
                # EPO OPS family query
                # (Simplified - real implementation would query family)
                # response = self.client.family(wo)
                
                # Parse family members
                # Extract country-specific patent numbers
                # Build patent dictionaries
                
                pass
                
            except Exception as e:
                continue
        
        # NOTE: This is a placeholder. Real implementation would:
        # 1. Query EPO OPS for patent family
        # 2. Filter family members by country code
        # 3. Extract patent metadata
        # 4. Return list of patent dictionaries
        
        return country_patents
