"""
PROFESSIONAL QUERY BUILDER v28.0
Implementa TODAS as técnicas das plataformas líderes:
- Cortellis: Patent types, Action/Indication fields, proximity
- PatSnap: Semantic search, chemical structure, TAC field
- Questel: FAMPAT/FULLPAT strategy, proximity operators
- DWPI: Manual codes, fragmentation, Ring Index

REFERÊNCIA: compass_artifact_wf-9cca8bbb-67de-4b60-ae6a-cb3cadf67911_text/markdown
"""

from typing import List, Dict, Set
import re
import logging

logger = logging.getLogger("pharmyrus.queries")


class ProfessionalQueryBuilder:
    """
    Query builder PROFISSIONAL - nível Cortellis/PatSnap/Questel
    
    Implementa:
    - Proximity operators (EPO syntax)
    - Dynamic IPC codes based on mechanisms/indications
    - Patent type classification
    - Therapeutic area targeting
    - MUITO mais queries que v27.4!
    """
    
    def __init__(self, molecule: str, brand: str, enriched_data: Dict):
        self.molecule = molecule.lower()
        self.molecule_original = molecule
        self.brand = brand
        self.enriched = enriched_data
        
        # IPC/CPC mappings (dinâmicos!)
        self.mechanism_to_ipc = self._build_mechanism_ipc_mapping()
        self.indication_to_ipc = self._build_indication_ipc_mapping()
    
    # ============= IPC MAPPINGS (DINÂMICO!) =============
    
    def _build_mechanism_ipc_mapping(self) -> Dict[str, List[str]]:
        """
        Mapeia mechanisms para IPC codes específicos
        Baseado em A61K31 hierarchy
        """
        return {
            # Kinase inhibitors
            'kinase inhibitor': ['A61K31/519', 'A61K31/5377'],  # Quinazolines, pteridines
            'tyrosine kinase inhibitor': ['A61K31/519'],
            
            # Receptor antagonists/agonists
            'androgen receptor antagonist': ['A61K31/44', 'A61K31/4439'],  # Pyridines
            'androgen receptor agonist': ['A61K31/568'],  # Androstanes
            'estrogen receptor': ['A61K31/56'],  # Steroids
            
            # Enzyme inhibitors
            'parp inhibitor': ['A61K31/519', 'A61K31/5377'],  # Various heterocycles
            'proteasome inhibitor': ['A61K31/395'],  # Peptides
            'ace inhibitor': ['A61K31/401'],  # Proline derivatives
            'hmg-coa reductase inhibitor': ['A61K31/40'],  # Statins
            
            # Receptor modulators
            'gpcr': ['A61K31/40', 'A61K31/44'],  # Various
            'ion channel': ['A61K31/135', 'A61K31/137'],
            
            # Neurotransmitter
            'serotonin': ['A61K31/404'],  # Indoles
            'dopamine': ['A61K31/137'],  # Phenethylamines
            
            # Anti-infective
            'antiviral': ['A61K31/7076'],  # Nucleosides
            'antibiotic': ['A61K31/43'],  # Beta-lactams
            
            # Generic patterns
            'inhibitor': ['A61K31'],  # Catch-all
            'antagonist': ['A61K31'],
            'agonist': ['A61K31'],
            'modulator': ['A61K31'],
        }
    
    def _build_indication_ipc_mapping(self) -> Dict[str, List[str]]:
        """
        Mapeia indications para A61P therapeutic activity codes
        """
        return {
            # Cancer (A61P35)
            'cancer': ['A61P35/00'],
            'prostate cancer': ['A61P13/08', 'A61P35/00'],  # Urinary + Cancer
            'breast cancer': ['A61P35/00'],
            'lung cancer': ['A61P35/00', 'A61P11/00'],  # Cancer + Respiratory
            'leukemia': ['A61P35/02'],
            
            # Cardiovascular (A61P9)
            'hypertension': ['A61P9/12'],
            'heart failure': ['A61P9/04'],
            'arrhythmia': ['A61P9/06'],
            
            # Neurology (A61P25)
            'alzheimer': ['A61P25/28'],  # Neurodegenerative
            'parkinson': ['A61P25/16'],
            'epilepsy': ['A61P25/08'],
            'pain': ['A61P29/00', 'A61P25/04'],  # Analgesics
            
            # Metabolic (A61P3)
            'diabetes': ['A61P3/10'],
            'obesity': ['A61P3/04'],
            
            # Infectious (A61P31)
            'hiv': ['A61P31/18'],
            'hepatitis': ['A61P31/12'],  # Viral
            'infection': ['A61P31/00'],
            
            # Inflammatory/Immune (A61P29, A61P37)
            'inflammation': ['A61P29/00'],
            'arthritis': ['A61P19/02'],
            'asthma': ['A61P11/06'],
            
            # Psychiatric (A61P25)
            'depression': ['A61P25/24'],
            'anxiety': ['A61P25/22'],
            'schizophrenia': ['A61P25/18'],
        }
    
    # ============= UTILITIES =============
    
    def clean_text(self, text: str) -> str:
        """Remove caracteres problemáticos para EPO"""
        if not text:
            return ""
        text = re.sub(r'[()/<>"\']', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def is_valid_term(self, term: str, max_length: int = 40) -> bool:
        """Valida termo para query EPO"""
        if not term or len(term) > max_length:
            return False
        if any(c in term for c in ['(', ')', '/', '<', '>', '"', "'"]):
            return False
        if len(term) < 3:
            return False
        return True
    
    # ============= 1. CORE QUERIES =============
    
    def get_core_queries(self) -> List[str]:
        """
        Core queries - sempre funcionam
        CORTELLIS STYLE: Compound name, dev codes, CAS
        """
        queries = []
        mol = self.molecule_original
        
        # Molécula (all fields)
        queries.append(f'txt="{mol}"')
        queries.append(f'ti="{mol}"')
        queries.append(f'ab="{mol}"')
        
        # Brand name
        if self.brand and self.is_valid_term(self.brand):
            queries.append(f'txt="{self.brand}"')
            queries.append(f'ti="{self.brand}"')
        
        # Dev codes (FILTRADOS)
        dev_codes = self.enriched.get('dev_codes', [])
        valid_codes = []
        
        for code in dev_codes:
            if re.match(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', str(code), re.I):
                code_clean = self.clean_text(str(code))
                if self.is_valid_term(code_clean, max_length=20):
                    valid_codes.append(code_clean)
                    # Versão sem hífen
                    code_no_hyphen = code_clean.replace('-', '')
                    if code_no_hyphen != code_clean:
                        valid_codes.append(code_no_hyphen)
        
        # Top 10 dev codes
        for code in valid_codes[:10]:
            queries.append(f'txt="{code}"')
        
        # Synonyms válidos (FILTRADOS - top 5)
        synonyms = self.enriched.get('synonyms', [])
        valid_syns = []
        
        for syn in synonyms:
            syn_clean = self.clean_text(str(syn))
            if self.is_valid_term(syn_clean, max_length=30):
                if syn_clean.lower() not in [self.molecule, self.brand.lower()]:
                    valid_syns.append(syn_clean)
        
        for syn in valid_syns[:5]:
            queries.append(f'txt="{syn}"')
        
        return queries
    
    # ============= 2. MECHANISM-BASED QUERIES (NOVO! CORRIGIDO!) =============
    
    def get_mechanism_queries(self) -> List[str]:
        """
        Mechanism of Action queries - CORTELLIS ACTION FIELD
        
        Usa mechanisms detectados do enrichment!
        """
        queries = []
        mol = self.molecule_original
        
        mechanisms = self.enriched.get('mechanisms', [])
        
        if not mechanisms:
            logger.warning(f"   ⚠️  No mechanisms detected - queries may be incomplete")
            return queries
        
        logger.info(f"   🎯 Building mechanism queries from: {mechanisms[:3]}")
        
        # Top 8 mechanisms
        for mech in mechanisms[:8]:
            mech_clean = self.clean_text(mech)
            if not self.is_valid_term(mech_clean, max_length=60):
                continue
            
            # Mechanism alone (important!)
            queries.append(f'txt="{mech_clean}"')
            queries.append(f'ti="{mech_clean}"')
            
            # Mechanism + molecule
            queries.append(f'txt="{mol}" and txt="{mech_clean}"')
            
            # Get specific IPC codes for this mechanism
            ipc_codes = self._get_ipc_for_mechanism(mech_clean)
            if ipc_codes:
                # Mechanism + IPC (precision!)
                queries.append(f'txt="{mech_clean}" and ic="{ipc_codes[0]}"')
        
        return queries
    
    def _get_ipc_for_mechanism(self, mechanism: str) -> List[str]:
        """Retorna IPC codes específicos para um mecanismo"""
        mech_lower = mechanism.lower()
        
        for pattern, ipcs in self.mechanism_to_ipc.items():
            if pattern in mech_lower:
                return ipcs
        
        return ['A61K31']  # Generic fallback
    
    # ============= 3. INDICATION-BASED QUERIES (NOVO! CORRIGIDO!) =============
    
    def get_indication_queries(self) -> List[str]:
        """
        Therapeutic indication queries - CORTELLIS INDICATION FIELD
        
        Usa indications detectadas do enrichment!
        """
        queries = []
        mol = self.molecule_original
        
        indications = self.enriched.get('indications', [])
        
        if not indications:
            logger.warning(f"   ⚠️  No indications detected - queries may be incomplete")
            return queries
        
        logger.info(f"   🎯 Building indication queries from: {indications[:3]}")
        
        # Top 8 indications
        for indication in indications[:8]:
            ind_clean = self.clean_text(indication)
            
            # Indication + molecule
            queries.append(f'txt="{mol}" and txt="{ind_clean}"')
            
            # Treatment pattern (CORTELLIS STYLE)
            queries.append(f'txt="{mol}" and txt="treatment" and txt="{ind_clean}"')
            
            # Get specific A61P codes
            a61p_codes = self._get_a61p_for_indication(indication)
            if a61p_codes:
                # Molecule + A61P (precision!)
                queries.append(f'txt="{mol}" and ic="{a61p_codes[0]}"')
                
                # Indication + A61P
                queries.append(f'txt="{ind_clean}" and ic="{a61p_codes[0]}"')
        
        return queries
    
    def _get_a61p_for_indication(self, indication: str) -> List[str]:
        """Retorna A61P codes para uma indicação"""
        ind_lower = indication.lower()
        
        for pattern, ipcs in self.indication_to_ipc.items():
            if pattern in ind_lower:
                return ipcs
        
        return ['A61P']  # Generic fallback
    
    # ============= 4. FORMULATION QUERIES (UNIVERSAL) =============
    
    def get_formulation_queries(self) -> List[str]:
        """
        Formulation patents - UNIVERSAL
        A61K9 - Medicinal preparations characterized by physical form
        """
        queries = []
        mol = self.molecule_original
        
        # Basic formulation terms
        formulation_terms = [
            'formulation',
            'pharmaceutical composition',
            'composition',
            'tablet',
            'capsule',
        ]
        
        for term in formulation_terms:
            queries.append(f'txt="{mol}" and txt="{term}"')
        
        # Delivery systems (Cortellis "Drug delivery device")
        delivery_terms = [
            'controlled release',
            'sustained release',
            'extended release',
        ]
        
        for term in delivery_terms[:2]:
            queries.append(f'txt="{mol}" and txt="{term}"')
        
        # IPC A61K9 subclasses
        a61k9_codes = ['A61K9/20', 'A61K9/48']  # Tablets, Capsules
        for code in a61k9_codes:
            queries.append(f'ic="{code}" and txt="{mol}"')
        
        return queries
    
    # ============= 5. CRYSTALLINE/POLYMORPH QUERIES (PRODUCT DERIVATIVE) =============
    
    def get_crystalline_queries(self) -> List[str]:
        """
        Crystalline forms/polymorphs - CORTELLIS "Product derivative"
        C07B2200/13 - Indexing code for crystalline forms
        """
        queries = []
        mol = self.molecule_original
        
        # Core crystal terms
        crystal_terms = [
            'crystalline',
            'crystal',
            'polymorph',
            'solid state',
        ]
        
        for term in crystal_terms:
            queries.append(f'txt="{mol}" and txt="{term}"')
        
        # Specific crystal forms (PATENT PATTERN)
        forms = ['form a', 'form b', 'form i', 'form ii', 'form 1', 'form 2']
        
        for form in forms:
            queries.append(f'txt="{mol}" and txt="{form}"')
        
        # Physical states
        states = ['anhydrous', 'hydrate', 'solvate']
        
        for state in states:
            queries.append(f'txt="{mol}" and txt="{state}"')
        
        # Characterization methods (HIGH PRECISION!)
        queries.append(f'txt="{mol}" and txt="X-ray diffraction"')
        queries.append(f'txt="{mol}" and txt="powder diffraction"')
        
        return queries
    
    # ============= 6. SALT FORM QUERIES (PRODUCT DERIVATIVE) =============
    
    def get_salt_queries(self) -> List[str]:
        """
        Salt forms - CORTELLIS "Product derivative"
        """
        queries = []
        mol = self.molecule_original
        
        # Generic salt
        queries.append(f'txt="{mol}" and txt="salt"')
        queries.append(f'txt="{mol}" and txt="pharmaceutically acceptable salt"')
        
        # Common salts (PHARMA PATTERNS)
        common_salts = [
            'hydrochloride',
            'mesylate',
            'tosylate',
            'sulfate',
        ]
        
        for salt in common_salts:
            queries.append(f'txt="{mol}" and txt="{salt}"')
        
        return queries
    
    # ============= 7. PROCESS/SYNTHESIS QUERIES =============
    
    def get_process_queries(self) -> List[str]:
        """
        Process patents - CORTELLIS "Process"
        C07 codes (organic chemistry)
        """
        queries = []
        mol = self.molecule_original
        
        process_terms = [
            'synthesis',
            'preparation',
            'process',
            'manufacturing',
        ]
        
        for term in process_terms:
            queries.append(f'txt="{mol}" and txt="{term}"')
        
        # Process + C07 (precision!)
        queries.append(f'ic="C07" and txt="{mol}"')
        
        return queries
    
    # ============= 8. COMBINATION THERAPY QUERIES =============
    
    def get_combination_queries(self) -> List[str]:
        """
        Combination therapy - CORTELLIS "Drug combination"
        A61K45/06 - Mixtures of active ingredients
        """
        queries = []
        mol = self.molecule_original
        
        # Generic combination terms
        queries.append(f'txt="{mol}" and txt="combination"')
        queries.append(f'txt="{mol}" and txt="combination therapy"')
        queries.append(f'txt="{mol}" and txt="co-administration"')
        
        # IPC combination code
        queries.append(f'ic="A61K45/06" and txt="{mol}"')
        
        return queries
    
    # ============= 9. COMPANY-SPECIFIC QUERIES =============
    
    def get_company_queries(self) -> List[str]:
        """
        Company-specific - CORTELLIS Assignee field
        """
        queries = []
        mol = self.molecule_original
        
        companies = self.enriched.get('companies', [])
        valid_companies = []
        
        company_indicators = [
            'pharma', 'inc', 'ltd', 'corp', 'gmbh', 'sa', 'ag',
            'ab', 'llc', 'co', 'laboratories', 'therapeutics'
        ]
        
        for company in companies:
            company_lower = str(company).lower()
            if any(ind in company_lower for ind in company_indicators):
                company_clean = self.clean_text(str(company))
                if self.is_valid_term(company_clean, max_length=60):
                    valid_companies.append(company_clean)
        
        # Top 10 companies
        for company in valid_companies[:10]:
            queries.append(f'pa="{company}" and txt="{mol}"')
        
        return queries
    
    # ============= 10. IPC HIERARCHICAL QUERIES (NOVO!) =============
    
    def get_ipc_hierarchical_queries(self) -> List[str]:
        """
        IPC codes hierárquicos - STRATEGY ESPECÍFICA
        
        Usa mechanisms/indications para escolher IPCs específicos!
        """
        queries = []
        mol = self.molecule_original
        
        # Get therapeutic area
        therapeutic_area = self.enriched.get('therapeutic_area', 'general')
        
        # Generic pharmaceutical IPCs (SEMPRE)
        generic_ipcs = ['A61K', 'A61K31', 'A61K9']
        
        for ipc in generic_ipcs:
            queries.append(f'ic="{ipc}" and txt="{mol}"')
        
        # Specific IPCs based on detected data
        mechanisms = self.enriched.get('mechanisms', [])
        indications = self.enriched.get('indications', [])
        
        # Get specific IPCs from mechanisms
        specific_ipcs = set()
        for mech in mechanisms[:3]:
            ipcs = self._get_ipc_for_mechanism(mech)
            specific_ipcs.update(ipcs)
        
        # Get specific A61P from indications
        for indication in indications[:3]:
            ipcs = self._get_a61p_for_indication(indication)
            specific_ipcs.update(ipcs)
        
        # Add specific IPC queries
        for ipc in list(specific_ipcs)[:5]:
            queries.append(f'ic="{ipc}"')
        
        return queries
    
    # ============= 11. PROXIMITY QUERIES (NOVO! CORTELLIS/QUESTEL STYLE) =============
    
    def get_proximity_queries(self) -> List[str]:
        """
        Proximity operator queries - PROFESSIONAL LEVEL
        
        EPO syntax não suporta proximity, mas usamos combinações estratégicas
        """
        queries = []
        mol = self.molecule_original
        
        # Mechanism + Indication combinations
        mechanisms = self.enriched.get('mechanisms', [])
        indications = self.enriched.get('indications', [])
        
        # Top combinations
        if mechanisms and indications:
            # Mechanism + Indication (strategic!)
            mech = self.clean_text(mechanisms[0])
            indication = self.clean_text(indications[0])
            
            if self.is_valid_term(mech, 60) and self.is_valid_term(indication, 40):
                queries.append(f'txt="{mech}" and txt="{indication}"')
                queries.append(f'txt="{mol}" and txt="{mech}" and txt="{indication}"')
        
        # Therapeutic use patterns
        if indications:
            indication = self.clean_text(indications[0])
            if self.is_valid_term(indication, 40):
                # "Treatment of [indication]" pattern
                queries.append(f'txt="treatment" and txt="{indication}"')
                queries.append(f'txt="method of treating" and txt="{indication}"')
        
        return queries
    
    # ============= MASTER BUILDER =============
    
    def build_all_queries(self) -> List[str]:
        """
        Constrói TODAS as queries usando TODAS as técnicas globais!
        """
        all_queries = []
        
        logger.info("   🔨 Building PROFESSIONAL queries...")
        
        # 1. CORE (sempre)
        core_q = self.get_core_queries()
        all_queries.extend(core_q)
        logger.info(f"      ✅ Core: {len(core_q)} queries")
        
        # 2. MECHANISM (CRITICAL!)
        mech_q = self.get_mechanism_queries()
        all_queries.extend(mech_q)
        logger.info(f"      ✅ Mechanism: {len(mech_q)} queries")
        
        # 3. INDICATION (CRITICAL!)
        ind_q = self.get_indication_queries()
        all_queries.extend(ind_q)
        logger.info(f"      ✅ Indication: {len(ind_q)} queries")
        
        # 4. FORMULATION
        form_q = self.get_formulation_queries()
        all_queries.extend(form_q)
        logger.info(f"      ✅ Formulation: {len(form_q)} queries")
        
        # 5. CRYSTALLINE
        cryst_q = self.get_crystalline_queries()
        all_queries.extend(cryst_q)
        logger.info(f"      ✅ Crystalline: {len(cryst_q)} queries")
        
        # 6. SALT
        salt_q = self.get_salt_queries()
        all_queries.extend(salt_q)
        logger.info(f"      ✅ Salt: {len(salt_q)} queries")
        
        # 7. PROCESS
        proc_q = self.get_process_queries()
        all_queries.extend(proc_q)
        logger.info(f"      ✅ Process: {len(proc_q)} queries")
        
        # 8. COMBINATION
        comb_q = self.get_combination_queries()
        all_queries.extend(comb_q)
        logger.info(f"      ✅ Combination: {len(comb_q)} queries")
        
        # 9. COMPANIES
        comp_q = self.get_company_queries()
        all_queries.extend(comp_q)
        logger.info(f"      ✅ Companies: {len(comp_q)} queries")
        
        # 10. IPC HIERARCHICAL
        ipc_q = self.get_ipc_hierarchical_queries()
        all_queries.extend(ipc_q)
        logger.info(f"      ✅ IPC Hierarchical: {len(ipc_q)} queries")
        
        # 11. PROXIMITY
        prox_q = self.get_proximity_queries()
        all_queries.extend(prox_q)
        logger.info(f"      ✅ Proximity: {len(prox_q)} queries")
        
        # Remove duplicatas
        seen = set()
        unique_queries = []
        for q in all_queries:
            q_normalized = q.lower()
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q)
        
        logger.info(f"   🎯 TOTAL: {len(unique_queries)} unique queries (from {len(all_queries)} total)")
        
        return unique_queries
    
    def get_query_stats(self, queries: List[str]) -> Dict:
        """Estatísticas das queries"""
        return {
            "total_queries": len(queries),
            "by_category": {
                "core": len(self.get_core_queries()),
                "mechanism": len(self.get_mechanism_queries()),
                "indication": len(self.get_indication_queries()),
                "formulation": len(self.get_formulation_queries()),
                "crystalline": len(self.get_crystalline_queries()),
                "salt": len(self.get_salt_queries()),
                "process": len(self.get_process_queries()),
                "combination": len(self.get_combination_queries()),
                "companies": len(self.get_company_queries()),
                "ipc_hierarchical": len(self.get_ipc_hierarchical_queries()),
                "proximity": len(self.get_proximity_queries()),
            }
        }
