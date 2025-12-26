"""
Search State Management - Persistência e Tracking
Garante que todas as buscas foram executadas
"""
import logging
from typing import Dict, List, Set
from datetime import datetime

logger = logging.getLogger("pharmyrus.state")


class SearchState:
    """Gerencia estado de todas as buscas executadas"""
    
    def __init__(self, molecule: str):
        self.molecule = molecule
        self.start_time = datetime.now()
        
        # Estados de execução
        self.enrichment_status = {
            "pubchem": False,
            "openfda": False,
            "pubmed": False,
            "drugbank": False,
        }
        
        self.epo_status = {
            "text_search": False,
            "priority_search": False,
            "citation_search": False,
            "queries_executed": 0,
            "queries_total": 0,
        }
        
        self.google_status = {
            "searches_executed": 0,
            "searches_total": 0,
        }
        
        # Dados coletados
        self.wos_by_source = {
            "epo_text": set(),
            "epo_priority": set(),
            "epo_citation": set(),
            "google": set(),
        }
        
        self.assignees_found = set()
        self.queries_executed = []
        
    def mark_enrichment_complete(self, source: str):
        """Marca fonte de enrichment como completa"""
        if source in self.enrichment_status:
            self.enrichment_status[source] = True
            logger.info(f"   ✓ Enrichment {source} complete")
    
    def mark_epo_phase_complete(self, phase: str):
        """Marca fase EPO como completa"""
        if phase in self.epo_status:
            self.epo_status[phase] = True
            logger.info(f"   ✓ EPO {phase} complete")
    
    def add_query_executed(self, source: str, query: str, results_count: int):
        """Registra query executada"""
        self.queries_executed.append({
            "source": source,
            "query": query,
            "results": results_count,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_wos(self, source: str, wos: Set[str]):
        """Adiciona WOs encontrados por fonte"""
        if source in self.wos_by_source:
            before = len(self.wos_by_source[source])
            self.wos_by_source[source].update(wos)
            after = len(self.wos_by_source[source])
            
            if after > before:
                logger.info(f"   ✅ {source}: +{after - before} WOs (total: {after})")
    
    def add_assignees(self, assignees: Set[str]):
        """Adiciona assignees encontrados"""
        before = len(self.assignees_found)
        self.assignees_found.update(assignees)
        after = len(self.assignees_found)
        
        if after > before:
            logger.info(f"   ✅ Assignees: +{after - before} (total: {after})")
    
    def get_all_wos(self) -> Set[str]:
        """Retorna todos os WOs encontrados"""
        all_wos = set()
        for wos in self.wos_by_source.values():
            all_wos.update(wos)
        return all_wos
    
    def is_enrichment_complete(self) -> bool:
        """Verifica se enrichment foi completo"""
        return all(self.enrichment_status.values())
    
    def is_epo_complete(self) -> bool:
        """Verifica se EPO foi completo"""
        return self.epo_status["text_search"] and \
               self.epo_status["priority_search"] and \
               self.epo_status["citation_search"]
    
    def get_summary(self) -> Dict:
        """Retorna sumário do estado"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "molecule": self.molecule,
            "elapsed_seconds": round(elapsed, 2),
            "enrichment": self.enrichment_status,
            "epo_phases": {
                "text_search": self.epo_status["text_search"],
                "priority_search": self.epo_status["priority_search"],
                "citation_search": self.epo_status["citation_search"],
                "queries_executed": self.epo_status["queries_executed"],
            },
            "google_searches": self.google_status["searches_executed"],
            "wos_by_source": {k: len(v) for k, v in self.wos_by_source.items()},
            "total_wos": len(self.get_all_wos()),
            "assignees_found": len(self.assignees_found),
            "queries_total": len(self.queries_executed),
        }
    
    def get_detailed_log(self) -> List[Dict]:
        """Retorna log detalhado de todas as queries"""
        return self.queries_executed
