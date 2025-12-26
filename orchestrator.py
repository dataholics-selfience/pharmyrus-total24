"""
Pharmyrus v27 Orchestrator - Coordinates EPO + Google Patents layers.
"""
from typing import List, Dict
from layers.epo_layer import EPOLayer
from layers.google_patents_layer import GooglePatentsLayer
from utils.deduplicator import Deduplicator
from utils.merger import Merger


class PharmyrusOrchestrator:
    """Orchestrates multi-layer patent search."""
    
    def __init__(self):
        self.epo_layer = EPOLayer()
        self.google_layer = GooglePatentsLayer()
        self.deduplicator = Deduplicator()
        self.merger = Merger()
    
    async def search(
        self,
        molecule_name: str,
        brand_name: str = None,
        target_countries: List[str] = None
    ) -> Dict:
        """
        Execute full patent search pipeline.
        
        Args:
            molecule_name: Name of the molecule
            brand_name: Commercial brand name (optional)
            target_countries: List of target countries
            
        Returns:
            Complete patent search results
        """
        print("="*80)
        print(f"🚀 PHARMYRUS V27 - Patent Search")
        print(f"   Molecule: {molecule_name}")
        print(f"   Brand: {brand_name or 'N/A'}")
        print(f"   Countries: {', '.join(target_countries or ['BR'])}")
        print("="*80)
        
        # LAYER 1: EPO OPS (fast, official API)
        print("\n🔵 LAYER 1: EPO OPS")
        print("-"*80)
        
        epo_results = await self.epo_layer.search(
            molecule_name=molecule_name,
            brand_name=brand_name,
            countries=target_countries
        )
        
        epo_wos = set(epo_results.get('wo_patents', []))
        epo_brs = set()
        
        if 'BR' in (target_countries or []):
            br_patents = epo_results.get('patents_by_country', {}).get('BR', [])
            epo_brs = set([p['patent_number'] for p in br_patents])
        
        print(f"\n✅ EPO Layer complete:")
        print(f"   WOs: {len(epo_wos)}")
        print(f"   BRs: {len(epo_brs)}")
        
        # LAYER 2: Google Patents (comprehensive crawling)
        print("\n🟢 LAYER 2: GOOGLE PATENTS")
        print("-"*80)
        
        google_results = await self.google_layer.search(
            molecule_name=molecule_name,
            pubchem_data=epo_results.get('summary', {}),
            existing_wos=epo_wos,
            existing_brs=epo_brs,
            target_countries=target_countries or ['BR']
        )
        
        google_wos = set(google_results.get('additional_wos', []))
        
        print(f"\n✅ Google Layer complete:")
        print(f"   Additional WOs: {len(google_wos)}")
        
        # MERGE results
        print("\n🔀 MERGING RESULTS")
        print("-"*80)
        
        merged_results = self.merger.merge(epo_results, google_results)
        
        # DEDUPLICATE
        final_results = self.deduplicator.deduplicate(merged_results)
        
        # Final stats
        total_wos = len(final_results.get('wo_patents', []))
        total_patents = final_results.get('summary', {}).get('total_patents', 0)
        
        print(f"\n✅ FINAL RESULTS:")
        print(f"   Total WOs: {total_wos}")
        print(f"   Total Patents: {total_patents}")
        print("="*80)
        
        return final_results
