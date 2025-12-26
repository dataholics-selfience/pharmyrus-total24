"""
Deduplicates patent results from multiple sources.
"""
from typing import Dict, List, Set


class Deduplicator:
    """Removes duplicate patents and WOs from results."""
    
    def deduplicate(self, results: Dict) -> Dict:
        """
        Deduplicate WO patents and country patents.
        
        Args:
            results: Dictionary with wo_patents and patents_by_country
            
        Returns:
            Deduplicated results dictionary
        """
        # Deduplicate WO patents
        if 'wo_patents' in results:
            results['wo_patents'] = list(set(results['wo_patents']))
            results['wo_patents'].sort()
        
        # Deduplicate country patents
        if 'patents_by_country' in results:
            for country, patents in results['patents_by_country'].items():
                # Use patent_number as unique key
                seen = set()
                unique_patents = []
                
                for patent in patents:
                    patent_num = patent.get('patent_number')
                    if patent_num and patent_num not in seen:
                        seen.add(patent_num)
                        unique_patents.append(patent)
                
                results['patents_by_country'][country] = unique_patents
        
        # Update summary counts
        if 'summary' in results:
            results['summary']['total_wos'] = len(results.get('wo_patents', []))
            
            total_patents = 0
            by_country = {}
            
            for country, patents in results.get('patents_by_country', {}).items():
                count = len(patents)
                total_patents += count
                by_country[country] = count
            
            results['summary']['total_patents'] = total_patents
            results['summary']['by_country'] = by_country
        
        return results
