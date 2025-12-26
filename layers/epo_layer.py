"""
EPO OPS Layer - Real implementation based on v26.
Complete patent search using EPO OPS API.
"""
import time
import requests
import pubchempy as pcp
from typing import List, Dict, Set, Tuple
from datetime import datetime
from config.settings import EPO_CONSUMER_KEY, EPO_CONSUMER_SECRET


class EPOLayer:
    """Layer 1: EPO OPS API search - Real implementation."""
    
    def __init__(self):
        self.consumer_key = EPO_CONSUMER_KEY
        self.consumer_secret = EPO_CONSUMER_SECRET
        self.access_token = None
        self.token_expiry = 0
    
    def _get_token(self) -> str:
        """Get or refresh EPO OPS access token."""
        current_time = time.time()
        
        # Reuse token if still valid (expires in 20 minutes)
        if self.access_token and current_time < self.token_expiry:
            return self.access_token
        
        # Request new token
        try:
            response = requests.post(
                'https://ops.epo.org/3.2/auth/accesstoken',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={'grant_type': 'client_credentials'},
                auth=(self.consumer_key, self.consumer_secret),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access_token']
                # Token expires in 20 minutes, refresh after 18
                self.token_expiry = current_time + (18 * 60)
                return self.access_token
            else:
                print(f"⚠️  EPO token error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ EPO token failed: {e}")
            return None
    
    async def search(
        self,
        molecule_name: str,
        brand_name: str = None,
        countries: List[str] = None
    ) -> Dict:
        """
        Search patents using EPO OPS API.
        
        Discovers WOs and country patents from molecule name alone.
        No hardcoded patents - completely generic discovery.
        """
        start_time = time.time()
        
        print(f"🔵 EPO Layer: Searching for {molecule_name}...")
        
        # Get access token
        token = self._get_token()
        if not token:
            print("❌ Failed to get EPO token")
            return self._empty_result(molecule_name, brand_name, countries)
        
        # Get PubChem data (dev codes, CAS)
        pubchem_data = self._get_pubchem_data(molecule_name)
        dev_codes = pubchem_data.get('dev_codes', [])
        cas_number = pubchem_data.get('cas')
        
        print(f"   ℹ️  PubChem: {len(dev_codes)} dev codes, CAS: {cas_number or 'None'}")
        
        # Build search terms (generic discovery)
        search_terms = self._build_search_terms(molecule_name, dev_codes, cas_number, brand_name)
        
        # Search for WO patents
        wo_patents = self._search_wo_patents(search_terms, token)
        
        print(f"   ✅ Found {len(wo_patents)} WO patents via EPO")
        
        # Map WOs to target countries via family data
        patents_by_country = {}
        
        if countries:
            for country in countries:
                country_patents = self._map_wo_to_country(wo_patents, country, token)
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
                'version': 'Pharmyrus v27 (EPO Layer)',
                'source': 'EPO OPS API'
            },
            'summary': {
                'total_wos': len(wo_patents),
                'total_patents': sum(len(p) for p in patents_by_country.values()),
                'by_country': {k: len(v) for k, v in patents_by_country.items()},
                'pubchem_dev_codes': dev_codes,
                'pubchem_cas': cas_number
            },
            'wo_patents': sorted(list(wo_patents)),
            'patents_by_country': patents_by_country,
            'all_patents': self._flatten_patents(patents_by_country)
        }
        
        return result
    
    def _get_pubchem_data(self, molecule_name: str) -> Dict:
        """Get PubChem synonyms and CAS number."""
        try:
            compounds = pcp.get_compounds(molecule_name, 'name')
            
            if not compounds:
                print(f"   ⚠️  PubChem: No compounds found for '{molecule_name}'")
                return {'dev_codes': [], 'cas': None}
            
            compound = compounds[0]
            synonyms = compound.synonyms or []
            
            # Filter for development codes (pattern: XX-123456, ABC123, etc.)
            dev_codes = []
            cas = None
            
            for syn in synonyms[:100]:  # Check first 100 synonyms
                # Dev code pattern: 2-5 letters, optionally hyphen, 3+ digits
                if len(syn) < 20 and any(c.isdigit() for c in syn):
                    # Exclude CID references
                    if not syn.startswith('CID'):
                        dev_codes.append(syn)
                
                # CAS number pattern: XXXXX-XX-X
                if not cas and '-' in syn:
                    parts = syn.split('-')
                    if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                        cas = syn
                
                if len(dev_codes) >= 15:  # Limit to top 15
                    break
            
            return {
                'dev_codes': dev_codes[:15],
                'cas': cas
            }
            
        except Exception as e:
            print(f"   ⚠️  PubChem error: {e}")
            return {'dev_codes': [], 'cas': None}
    
    def _build_search_terms(
        self,
        molecule: str,
        dev_codes: List[str],
        cas: str,
        brand: str
    ) -> List[str]:
        """Build comprehensive search terms for generic discovery."""
        terms = []
        
        # Primary: molecule name
        terms.append(molecule)
        
        # CAS number
        if cas:
            terms.append(cas)
        
        # Brand name
        if brand:
            terms.append(brand)
        
        # Top development codes
        terms.extend(dev_codes[:10])
        
        return terms
    
    def _search_wo_patents(self, search_terms: List[str], token: str) -> Set[str]:
        """Search for WO patents using multiple terms."""
        found_wos = set()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        for term in search_terms[:15]:  # Limit to avoid rate limits
            try:
                # Search query: term AND publication number starts with WO
                query = f'ti,ab="{term}" AND pn=WO*'
                url = f'https://ops.epo.org/3.2/rest-services/published-data/search?q={query}'
                
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract WO numbers from response
                    wos = self._extract_wo_from_epo_response(data)
                    
                    if wos:
                        found_wos.update(wos)
                        print(f"      ✅ '{term}': {len(wos)} WOs")
                    
                # Small delay to avoid rate limits
                time.sleep(0.5)
                
            except Exception as e:
                print(f"      ⚠️  Search error for '{term}': {e}")
                continue
        
        return found_wos
    
    def _extract_wo_from_epo_response(self, data: Dict) -> Set[str]:
        """Extract WO patent numbers from EPO JSON response."""
        wos = set()
        
        try:
            # Navigate EPO response structure
            search_result = data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get('ops:search-result', {})
            
            refs = search_result.get('ops:publication-reference', [])
            
            # Ensure refs is a list
            if not isinstance(refs, list):
                refs = [refs] if refs else []
            
            for ref in refs:
                doc_id = ref.get('document-id', {})
                
                # EPO returns multiple document-id elements, get the one with WO
                if isinstance(doc_id, list):
                    doc_id = next((d for d in doc_id if d.get('country', {}).get('$') == 'WO'), doc_id[0] if doc_id else {})
                
                country = doc_id.get('country', {}).get('$', '')
                number = doc_id.get('doc-number', {}).get('$', '')
                
                if country == 'WO' and number:
                    # Format: WO2011051540
                    wo_num = f"WO{number}"
                    wos.add(wo_num)
            
        except Exception as e:
            print(f"      ⚠️  Parse error: {e}")
        
        return wos
    
    def _map_wo_to_country(
        self,
        wo_patents: Set[str],
        country: str,
        token: str
    ) -> List[Dict]:
        """Map WO patents to country-specific patents via family data."""
        country_patents = []
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        # Limit to avoid rate limits
        for wo in list(wo_patents)[:50]:
            try:
                # Clean WO number (remove 'WO' prefix for API)
                wo_clean = wo.replace('WO', '')
                
                # Family query
                url = f'https://ops.epo.org/3.2/rest-services/family/publication/docdb/WO.{wo_clean}.A/biblio'
                
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract family members for target country
                    members = self._extract_family_members(data, country, wo)
                    country_patents.extend(members)
                
                # Small delay
                time.sleep(0.3)
                
            except Exception as e:
                continue
        
        return country_patents
    
    def _extract_family_members(self, data: Dict, country: str, wo_primary: str) -> List[Dict]:
        """Extract family members for specific country from EPO family response."""
        members = []
        
        try:
            family_data = data.get('ops:world-patent-data', {}).get('ops:patent-family', {})
            family_members = family_data.get('ops:family-member', [])
            
            if not isinstance(family_members, list):
                family_members = [family_members] if family_members else []
            
            for member in family_members:
                pub_ref = member.get('publication-reference', {})
                doc_id = pub_ref.get('document-id', {})
                
                # Get country-specific document
                if isinstance(doc_id, list):
                    doc_id = next((d for d in doc_id if d.get('country', {}).get('$') == country), None)
                    if not doc_id:
                        continue
                
                member_country = doc_id.get('country', {}).get('$', '')
                member_number = doc_id.get('doc-number', {}).get('$', '')
                member_kind = doc_id.get('kind', {}).get('$', '')
                
                if member_country == country and member_number:
                    patent = {
                        'patent_number': f"{country}{member_number}",
                        'country': country,
                        'wo_primary': wo_primary,
                        'kind': member_kind,
                        'link_espacenet': f"https://worldwide.espacenet.com/patent/search?q=pn%3D{country}{member_number}",
                        'country_name': self._get_country_name(country)
                    }
                    members.append(patent)
            
        except Exception as e:
            pass
        
        return members
    
    def _get_country_name(self, code: str) -> str:
        """Get country name from code."""
        countries = {
            'BR': 'Brazil',
            'US': 'United States',
            'EP': 'European Patent',
            'JP': 'Japan',
            'CN': 'China',
            'KR': 'South Korea'
        }
        return countries.get(code, code)
    
    def _flatten_patents(self, patents_by_country: Dict) -> List[Dict]:
        """Flatten all patents into single list."""
        all_patents = []
        for country, patents in patents_by_country.items():
            all_patents.extend(patents)
        return all_patents
    
    def _empty_result(self, molecule: str, brand: str, countries: List[str]) -> Dict:
        """Return empty result structure."""
        return {
            'metadata': {
                'molecule': molecule,
                'brand_name': brand,
                'search_date': datetime.now().isoformat(),
                'target_countries': countries or [],
                'elapsed_seconds': 0,
                'version': 'Pharmyrus v27 (EPO Layer)',
                'source': 'EPO OPS API',
                'error': 'Failed to authenticate'
            },
            'summary': {
                'total_wos': 0,
                'total_patents': 0,
                'by_country': {},
                'pubchem_dev_codes': [],
                'pubchem_cas': None
            },
            'wo_patents': [],
            'patents_by_country': {},
            'all_patents': []
        }
