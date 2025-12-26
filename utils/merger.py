"""
Merges results from EPO OPS and Google Patents layers.
"""
from typing import Dict, List


class Merger:
    """Merges patent results from multiple sources."""
    
    def merge(self, epo_results: Dict, google_results: Dict) -> Dict:
        """
        Merge EPO and Google Patents results.
        
        Args:
            epo_results: Results from EPO OPS layer
            google_results: Results from Google Patents layer
            
        Returns:
            Merged results dictionary
        """
        # Start with EPO results as base
        merged = epo_results.copy()
        
        # Add Google WOs to wo_patents list
        if 'additional_wos' in google_results:
            epo_wos = set(merged.get('wo_patents', []))
            google_wos = set(google_results['additional_wos'])
            
            # Combine and sort
            all_wos = list(epo_wos | google_wos)
            all_wos.sort()
            merged['wo_patents'] = all_wos
        
        # Merge country patents
        if 'additional_brs' in google_results:
            for country, google_patents in google_results['additional_brs'].items():
                if country not in merged.get('patents_by_country', {}):
                    merged.setdefault('patents_by_country', {})[country] = []
                
                # Extend with Google patents
                merged['patents_by_country'][country].extend(google_patents)
        
        # Update metadata to reflect v27
        if 'metadata' in merged:
            merged['metadata']['version'] = 'Pharmyrus v27'
            merged['metadata']['sources'] = ['EPO OPS', 'Google Patents']
        
        return merged
