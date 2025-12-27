"""
DYNAMIC QUERY BUILDER v27.4 - 100% AGNÓSTICO
Não assume NADA sobre a molécula - tudo vem do enrichment!
"""

from typing import List, Dict, Set
import re


class DynamicQueryBuilder:
    """
    100% DINÂMICO - Funciona para QUALQUER molécula!
    
    Estratégia:
    1. Core queries (molécula + brand + dev codes) - SEMPRE funcionam
    2. Pattern-based queries (formulation, crystalline, etc) - UNIVERSAIS
    3. Enrichment-driven queries (mechanism, indication, companies) - DINÂMICOS
    4. IPC codes - DESCOBERTOS dinamicamente ou genéricos
    """
    
    def __init__(self, molecule: str, brand: str, enriched_data: Dict):
        self.molecule = molecule.lower()
        self.molecule_original = molecule
        self.brand = brand
        self.enriched = enriched_data
        
    # ============= UTILITIES =============
    
    def clean_text(self, text: str) -> str:
        """Remove caracteres problemáticos para EPO"""
        if not text:
            return ""
        # Remove parentheses, slashes, quotes
        text = re.sub(r'[()/<>"\']', '', text)
        # Remove múltiplos espaços
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def is_valid_term(self, term: str, max_length: int = 30) -> bool:
        """Valida se termo pode ser usado em query EPO"""
        if not term or len(term) > max_length:
            return False
        # Não pode ter caracteres problemáticos
        if any(c in term for c in ['(', ')', '/', '<', '>', '"', "'"]):
            return False
        # Deve ter pelo menos 3 caracteres
        if len(term) < 3:
            return False
        return True
    
    # ============= CORE QUERIES (SEMPRE FUNCIONAM) =============
    
    def get_core_queries(self) -> List[str]:
        """
        Queries CORE - funcionam para QUALQUER molécula
        """
        queries = []
        mol = self.molecule_original
        
        # Molécula em todos os campos
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
            # Padrão válido: XX-12345 ou XX12345
            if re.match(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', str(code), re.I):
                code_clean = self.clean_text(str(code))
                if self.is_valid_term(code_clean, max_length=20):
                    valid_codes.append(code_clean)
                    # Versão sem hífen
                    code_no_hyphen = code_clean.replace('-', '')
                    if code_no_hyphen != code_clean:
                        valid_codes.append(code_no_hyphen)
        
        # Top 8 dev codes
        for code in valid_codes[:8]:
            queries.append(f'txt="{code}"')
        
        # Synonyms válidos (FILTRADOS)
        synonyms = self.enriched.get('synonyms', [])
        valid_syns = []
        
        for syn in synonyms:
            syn_clean = self.clean_text(str(syn))
            if self.is_valid_term(syn_clean, max_length=25):
                # Não incluir se for igual à molécula ou brand
                if syn_clean.lower() not in [self.molecule, self.brand.lower()]:
                    valid_syns.append(syn_clean)
        
        # Top 5 synonyms
        for syn in valid_syns[:5]:
            queries.append(f'txt="{syn}"')
        
        return queries
    
    # ============= PATTERN-BASED (UNIVERSAL) =============
    
    def get_formulation_queries(self) -> List[str]:
        """
        FORMULATION - UNIVERSAL para qualquer droga
        """
        queries = []
        mol = self.molecule_original
        
        # Padrões universais de formulação
        formulation_terms = [
            'formulation',
            'pharmaceutical composition',
            'composition',
            'tablet',
            'capsule',
            'dosage form',
        ]
        
        for term in formulation_terms:
            queries.append(f'txt="{mol}" and txt="{term}"')
        
        # Propriedades farmacêuticas (universais)
        properties = [
            'bioavailability',
            'solubility',
            'dissolution',
            'stability',
        ]
        
        for prop in properties[:3]:
            queries.append(f'txt="{mol}" and txt="{prop}"')
        
        return queries
    
    def get_crystalline_queries(self) -> List[str]:
        """
        CRYSTALLINE FORMS - UNIVERSAL (qualquer small molecule pode ter)
        """
        queries = []
        mol = self.molecule_original
        
        # Termos de forma cristalina
        crystal_terms = [
            'crystalline',
            'crystal',
            'polymorph',
            'solid state',
        ]
        
        for term in crystal_terms:
            queries.append(f'txt="{mol}" and txt="{term}"')
        
        # Formas específicas (padrão universal)
        forms = ['form a', 'form b', 'form i', 'form ii']
        
        for form in forms:
            queries.append(f'txt="{mol}" and txt="{form}"')
        
        # Estados (universal)
        states = ['anhydrous', 'hydrate', 'solvate']
        
        for state in states:
            queries.append(f'txt="{mol}" and txt="{state}"')
        
        return queries
    
    def get_salt_queries(self) -> List[str]:
        """
        SALT FORMS - UNIVERSAL para small molecules
        """
        queries = []
        mol = self.molecule_original
        
        # Termos de sal
        queries.append(f'txt="{mol}" and txt="salt"')
        queries.append(f'txt="{mol}" and txt="pharmaceutically acceptable salt"')
        
        # Sais comuns
        common_salts = [
            'hydrochloride',
            'mesylate',
            'tosylate',
            'sulfate',
            'phosphate',
        ]
        
        for salt in common_salts[:4]:
            queries.append(f'txt="{mol}" and txt="{salt}"')
        
        return queries
    
    def get_process_queries(self) -> List[str]:
        """
        PROCESS/SYNTHESIS - UNIVERSAL
        """
        queries = []
        mol = self.molecule_original
        
        process_terms = [
            'synthesis',
            'preparation',
            'process',
            'manufacturing',
            'production',
        ]
        
        for term in process_terms:
            queries.append(f'txt="{mol}" and txt="{term}"')
        
        return queries
    
    def get_combination_queries(self) -> List[str]:
        """
        COMBINATION - UNIVERSAL (qualquer droga pode ter combinações)
        """
        queries = []
        mol = self.molecule_original
        
        # Termos genéricos de combinação
        queries.append(f'txt="{mol}" and txt="combination"')
        queries.append(f'txt="{mol}" and txt="combination therapy"')
        queries.append(f'txt="{mol}" and txt="co administration"')
        
        return queries
    
    # ============= ENRICHMENT-DRIVEN (DINÂMICO) =============
    
    def get_mechanism_queries(self) -> List[str]:
        """
        MECHANISM OF ACTION - DINÂMICO do enrichment
        """
        queries = []
        mol = self.molecule_original
        
        # Extrair mecanismos do enrichment
        # Pode vir de PubMed, papers, etc
        synonyms = self.enriched.get('synonyms', [])
        
        # Identificar termos de mecanismo (padrões conhecidos)
        mechanism_patterns = [
            r'inhibitor',
            r'antagonist',
            r'agonist',
            r'modulator',
            r'blocker',
            r'activator',
        ]
        
        mechanisms = []
        for syn in synonyms:
            syn_lower = str(syn).lower()
            for pattern in mechanism_patterns:
                if pattern in syn_lower:
                    # Extrair frase completa (ex: "PARP inhibitor")
                    words = syn_lower.split()
                    for i, word in enumerate(words):
                        if pattern in word and i > 0:
                            # Pegar palavra anterior + pattern
                            mech = f"{words[i-1]} {word}"
                            if self.is_valid_term(mech):
                                mechanisms.append(mech)
        
        # Usar mecanismos descobertos
        for mech in mechanisms[:5]:
            queries.append(f'txt="{mech}"')
            queries.append(f'ti="{mech}"')
        
        return queries
    
    def get_indication_queries(self) -> List[str]:
        """
        THERAPEUTIC INDICATIONS - DINÂMICO do enrichment
        """
        queries = []
        mol = self.molecule_original
        
        # Extrair indicações dos synonyms/abstracts
        synonyms = self.enriched.get('synonyms', [])
        
        # Padrões de indicação
        indication_keywords = [
            'cancer', 'carcinoma', 'tumor', 'leukemia', 'lymphoma',
            'diabetes', 'hypertension', 'infection', 'inflammation',
            'pain', 'arthritis', 'asthma', 'depression', 'anxiety'
        ]
        
        indications = []
        for syn in synonyms:
            syn_lower = str(syn).lower()
            for keyword in indication_keywords:
                if keyword in syn_lower:
                    indications.append(keyword)
        
        # Remover duplicatas
        indications = list(set(indications))
        
        # Queries com indicações
        for indication in indications[:5]:
            queries.append(f'txt="{mol}" and txt="{indication}"')
            queries.append(f'txt="{mol}" and txt="treatment" and txt="{indication}"')
        
        return queries
    
    def get_company_queries(self) -> List[str]:
        """
        COMPANY-SPECIFIC - DINÂMICO do enrichment
        """
        queries = []
        
        # Empresas do enrichment (FILTRADAS)
        companies = self.enriched.get('companies', [])
        valid_companies = []
        
        company_indicators = [
            'pharma', 'inc', 'ltd', 'corp', 'gmbh', 'sa', 'ag', 
            'ab', 'llc', 'co', 'laboratories', 'therapeutics'
        ]
        
        for company in companies:
            company_lower = str(company).lower()
            # Deve ter indicador de empresa
            if any(ind in company_lower for ind in company_indicators):
                # Limpar e validar
                company_clean = self.clean_text(str(company))
                if self.is_valid_term(company_clean, max_length=50):
                    valid_companies.append(company_clean)
        
        # Top 8 empresas
        for company in valid_companies[:8]:
            # Company queries genéricas (funcionam para qualquer molécula)
            queries.append(f'pa="{company}"')
            queries.append(f'pa="{company}" and txt="{self.molecule_original}"')
        
        return queries
    
    def get_ipc_generic_queries(self) -> List[str]:
        """
        IPC CODES - Genéricos (funcionam para qualquer tipo de droga)
        """
        queries = []
        
        # IPC codes UNIVERSAIS para pharma
        generic_ipcs = [
            'A61K',        # Medicinal preparations (TODAS as drogas!)
            'A61K9',       # Medicinal preparations (formulations)
            'A61K31',      # Organic active ingredients
            'A61P',        # Therapeutic activity (TODAS as indicações!)
            'C07',         # Organic chemistry (TODAS small molecules!)
        ]
        
        for ipc in generic_ipcs:
            queries.append(f'ic="{ipc}"')
        
        # IPC + molécula
        queries.append(f'ic="A61K" and txt="{self.molecule_original}"')
        queries.append(f'ic="A61K31" and txt="{self.molecule_original}"')
        
        return queries
    
    # ============= BUILDER PRINCIPAL =============
    
    def build_all_queries(self) -> List[str]:
        """
        Constrói TODAS as queries de forma 100% DINÂMICA
        """
        all_queries = []
        
        # 1. CORE (sempre funcionam - molécula, brand, dev codes, synonyms)
        all_queries.extend(self.get_core_queries())
        
        # 2. PATTERN-BASED (universais - funcionam para qualquer droga)
        all_queries.extend(self.get_formulation_queries())
        all_queries.extend(self.get_crystalline_queries())
        all_queries.extend(self.get_salt_queries())
        all_queries.extend(self.get_process_queries())
        all_queries.extend(self.get_combination_queries())
        
        # 3. ENRICHMENT-DRIVEN (dinâmicos - descobertos do enrichment)
        all_queries.extend(self.get_mechanism_queries())
        all_queries.extend(self.get_indication_queries())
        all_queries.extend(self.get_company_queries())
        
        # 4. IPC GENERIC (universais para pharma)
        all_queries.extend(self.get_ipc_generic_queries())
        
        # Remove duplicatas mantendo ordem
        seen = set()
        unique_queries = []
        for q in all_queries:
            q_normalized = q.lower()
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q)
        
        return unique_queries
    
    def get_query_stats(self, queries: List[str]) -> Dict:
        """Estatísticas das queries"""
        return {
            "total_queries": len(queries),
            "by_category": {
                "core": len(self.get_core_queries()),
                "formulation": len(self.get_formulation_queries()),
                "crystalline": len(self.get_crystalline_queries()),
                "salt": len(self.get_salt_queries()),
                "process": len(self.get_process_queries()),
                "combination": len(self.get_combination_queries()),
                "mechanism": len(self.get_mechanism_queries()),
                "indication": len(self.get_indication_queries()),
                "companies": len(self.get_company_queries()),
                "ipc_generic": len(self.get_ipc_generic_queries()),
            }
        }


# ============= TESTE =============

if __name__ == "__main__":
    print("="*80)
    print("TESTE 1: DAROLUTAMIDE (antiandrogênio)")
    print("="*80)
    
    test_daro = {
        "synonyms": ["Darolutamide", "Nubeqa", "androgen receptor antagonist", "nonsteroidal antiandrogen"],
        "dev_codes": ["ODM-201", "BAY-1841788"],
        "companies": ["Bayer Pharma AG", "Orion Corporation"],
        "cas_numbers": ["1297538-32-9"]
    }
    
    builder1 = DynamicQueryBuilder("darolutamide", "Nubeqa", test_daro)
    queries1 = builder1.build_all_queries()
    stats1 = builder1.get_query_stats(queries1)
    
    print(f"\nTotal Queries: {stats1['total_queries']}")
    print("\nBy Category:")
    for cat, count in stats1['by_category'].items():
        print(f"  {cat}: {count}")
    
    print(f"\nSample Queries (first 15):")
    for i, q in enumerate(queries1[:15], 1):
        print(f"  {i}. {q}")
    
    print("\n" + "="*80)
    print("TESTE 2: PARACETAMOL (analgésico)")
    print("="*80)
    
    test_para = {
        "synonyms": ["Paracetamol", "Acetaminophen", "Tylenol", "analgesic", "antipyretic"],
        "dev_codes": ["APAP"],
        "companies": ["Johnson & Johnson", "GSK Pharma"],
        "cas_numbers": ["103-90-2"]
    }
    
    builder2 = DynamicQueryBuilder("paracetamol", "Tylenol", test_para)
    queries2 = builder2.build_all_queries()
    stats2 = builder2.get_query_stats(queries2)
    
    print(f"\nTotal Queries: {stats2['total_queries']}")
    print("\nBy Category:")
    for cat, count in stats2['by_category'].items():
        print(f"  {cat}: {count}")
    
    print(f"\nSample Queries (first 15):")
    for i, q in enumerate(queries2[:15], 1):
        print(f"  {i}. {q}")
    
    print("\n" + "="*80)
    print("TESTE 3: NIRAPARIB (inibidor PARP)")
    print("="*80)
    
    test_nira = {
        "synonyms": ["Niraparib", "Zejula", "PARP inhibitor", "poly ADP ribose polymerase inhibitor"],
        "dev_codes": ["MK-4827"],
        "companies": ["Merck & Co", "Tesaro Inc"],
        "cas_numbers": ["1038915-60-4"]
    }
    
    builder3 = DynamicQueryBuilder("niraparib", "Zejula", test_nira)
    queries3 = builder3.build_all_queries()
    stats3 = builder3.get_query_stats(queries3)
    
    print(f"\nTotal Queries: {stats3['total_queries']}")
    print("\nBy Category:")
    for cat, count in stats3['by_category'].items():
        print(f"  {cat}: {count}")
    
    print(f"\nSample Queries (first 15):")
    for i, q in enumerate(queries3[:15], 1):
        print(f"  {i}. {q}")
    
    print("\n" + "="*80)
    print("✅ TESTE COMPLETO - 100% DINÂMICO PARA QUALQUER MOLÉCULA!")
    print("="*80)
