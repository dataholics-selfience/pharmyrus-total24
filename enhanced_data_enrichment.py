"""
ENHANCED DATA ENRICHMENT v28.0
Integra TODAS as fontes: PubChem, OpenFDA, PubMed, ClinicalTrials.gov
Detecção CORRIGIDA de mechanism, indication, patent types
"""

import httpx
import re
import logging
from typing import Dict, List, Set

logger = logging.getLogger("pharmyrus.enrichment")


class EnhancedDataEnrichment:
    """
    Enrichment PROFISSIONAL - padrão Cortellis/PatSnap
    """
    
    def __init__(self):
        self.timeout = 30.0
        
    # ============= MECHANISM DETECTION (CORRIGIDO!) =============
    
    def detect_mechanisms(self, synonyms: List[str], abstracts: List[str] = None) -> List[str]:
        """
        Detecta mecanismos de ação - CORTELLIS STYLE (CORRIGIDO!)
        
        Patterns ROBUSTOS:
        - "nonsteroidal antiandrogen" ✅
        - "PARP inhibitor" ✅
        - "androgen receptor antagonist" ✅
        - "anti-inflammatory" ✅
        """
        mechanisms = []
        
        # Mechanism keywords (Cortellis Action field)
        # ORDEM IMPORTA: patterns mais específicos primeiro!
        mechanism_patterns = [
            # 1. Multi-word + suffix (CRITICAL!)
            r'(\w+\s+\w+\s+\w+)\s+(inhibitor|antagonist|agonist|modulator|blocker)',  # "androgen receptor antagonist"
            r'(\w+\s+\w+)\s+(inhibitor|antagonist|agonist|modulator|blocker)',  # "PARP inhibitor", "kinase inhibitor"
            
            # 2. Nonsteroidal patterns (SPECIAL CASE!)
            r'(nonsteroidal\s+\w+)',  # "nonsteroidal antiandrogen"
            r'(non-steroidal\s+\w+)',  # "non-steroidal antiandrogen"
            
            # 3. Anti- patterns (CORRECTED!)
            r'(anti-\w+)',  # "anti-inflammatory", "anti-androgen" (com hífen)
            r'(anti\s+\w+)',  # "anti inflammatory" (com espaço)
            r'(anti\w{6,})',  # "antiandrogen", "antiinflammatory" (palavra única, mínimo 10 chars total)
            
            # 4. Receptor patterns
            r'(\w+\s+receptor)\s+(inhibitor|antagonist|agonist|modulator)',  # "androgen receptor antagonist"
            
            # 5. Single word + suffix (fallback)
            r'(\w{4,})\s+(inhibitor|antagonist|agonist|modulator|blocker|activator)',  # "PARP inhibitor"
            
            # 6. Selective patterns
            r'(selective)\s+(\w+)\s+(inhibitor|antagonist)',
        ]
        
        all_text = synonyms + (abstracts or [])
        
        logger.debug(f"   🔍 Searching mechanisms in {len(all_text)} texts")
        
        for text in all_text:
            text_str = str(text)
            text_lower = text_str.lower()
            
            # Debug: log se contém palavras-chave
            if any(kw in text_lower for kw in ['inhibitor', 'antagonist', 'agonist', 'anti']):
                logger.debug(f"      Checking: {text_str[:100]}")
            
            for i, pattern in enumerate(mechanism_patterns):
                matches = re.finditer(pattern, text_lower, re.I)
                for match in matches:
                    # Extrair mecanismo completo
                    if len(match.groups()) == 2:
                        # Padrão com 2 grupos: "XXX" + "inhibitor"
                        mech = f"{match.group(1)} {match.group(2)}"
                    elif len(match.groups()) == 3:
                        # Padrão com 3 grupos: "selective" + "XXX" + "inhibitor"
                        mech = f"{match.group(1)} {match.group(2)} {match.group(3)}"
                    else:
                        # Padrão com 1 grupo: "antiandrogen"
                        mech = match.group(1) if match.groups() else match.group(0)
                    
                    # Limpar e validar
                    mech = re.sub(r'\s+', ' ', mech).strip()
                    
                    # Validações
                    if len(mech) < 5 or len(mech) > 60:
                        continue
                    
                    # Não incluir se for só a palavra "anti"
                    if mech in ['anti', 'selective']:
                        continue
                    
                    logger.debug(f"      ✓ Found with pattern {i}: '{mech}'")
                    mechanisms.append(mech)
        
        # Remove duplicatas, mantém ordem
        seen = set()
        unique_mechs = []
        for m in mechanisms:
            m_norm = m.lower()
            if m_norm not in seen:
                seen.add(m_norm)
                unique_mechs.append(m)
        
        if unique_mechs:
            logger.info(f"   🎯 Detected {len(unique_mechs)} mechanisms: {unique_mechs[:5]}")
        else:
            logger.warning(f"   ⚠️  No mechanisms detected from {len(all_text)} texts!")
            # Debug: mostrar primeiros synonyms para investigação
            logger.debug(f"      Sample synonyms: {synonyms[:5]}")
        
        return unique_mechs
    
    # ============= INDICATION DETECTION (CORRIGIDO!) =============
    
    def detect_indications(self, synonyms: List[str], abstracts: List[str] = None) -> List[str]:
        """
        Detecta indicações terapêuticas - CORTELLIS STYLE
        
        Therapy areas: oncology, neurology, cardiology, etc
        """
        indications = []
        
        # Indication keywords (Cortellis Indication field)
        # Based on A61P therapeutic activity codes
        indication_patterns = {
            # Cancer/Oncology
            'cancer': ['cancer', 'carcinoma', 'tumor', 'tumour', 'neoplasm', 'oncology', 'malignancy'],
            'leukemia': ['leukemia', 'leukaemia', 'lymphoma', 'myeloma'],
            'prostate cancer': ['prostate cancer', 'prostate carcinoma', 'castration resistant'],
            'breast cancer': ['breast cancer', 'breast carcinoma'],
            'lung cancer': ['lung cancer', 'nsclc', 'sclc'],
            
            # Cardiovascular
            'hypertension': ['hypertension', 'high blood pressure'],
            'heart failure': ['heart failure', 'cardiac failure', 'chf'],
            'arrhythmia': ['arrhythmia', 'atrial fibrillation', 'afib'],
            
            # Neurology
            'alzheimer': ['alzheimer', 'dementia', 'cognitive impairment'],
            'parkinson': ['parkinson', 'parkinsonian'],
            'epilepsy': ['epilepsy', 'seizure'],
            'pain': ['pain', 'analgesia', 'nociception'],
            
            # Metabolic
            'diabetes': ['diabetes', 'diabetic', 'hyperglycemia'],
            'obesity': ['obesity', 'weight loss', 'anti-obesity'],
            
            # Infectious
            'hiv': ['hiv', 'aids', 'antiretroviral'],
            'hepatitis': ['hepatitis', 'hcv', 'hbv'],
            'infection': ['infection', 'antibiotic', 'antimicrobial'],
            
            # Inflammatory/Immune
            'inflammation': ['inflammation', 'inflammatory'],
            'arthritis': ['arthritis', 'rheumatoid'],
            'asthma': ['asthma', 'copd'],
            
            # Psychiatric
            'depression': ['depression', 'antidepressant'],
            'anxiety': ['anxiety', 'anxiolytic'],
            'schizophrenia': ['schizophrenia', 'psychosis', 'antipsychotic'],
        }
        
        all_text = synonyms + (abstracts or [])
        
        for text in all_text:
            text_lower = str(text).lower()
            
            for indication, keywords in indication_patterns.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        indications.append(indication)
                        break  # Evita duplicatas desta indicação
        
        # Remove duplicatas
        indications = list(set(indications))
        
        logger.info(f"   🎯 Detected {len(indications)} indications: {indications[:5]}")
        return indications
    
    # ============= PATENT TYPE CLASSIFICATION =============
    
    def classify_patent_types(self, synonyms: List[str]) -> List[str]:
        """
        Classifica tipos de patente - CORTELLIS STYLE
        
        Types:
        - Product (compound)
        - Product derivative (salt, polymorph, ester, prodrug)
        - Formulation
        - New use (therapeutic use)
        - Process (synthesis)
        - Drug combination
        - Drug delivery device
        """
        types = []
        
        type_keywords = {
            'product_derivative': ['salt', 'polymorph', 'crystal', 'ester', 'prodrug', 'metabolite', 'hydrate', 'solvate'],
            'formulation': ['formulation', 'composition', 'tablet', 'capsule', 'dosage', 'pharmaceutical composition'],
            'process': ['synthesis', 'preparation', 'process', 'manufacturing', 'method of making'],
            'combination': ['combination', 'co-administration', 'fixed-dose', 'dual therapy'],
            'new_use': ['treatment', 'therapy', 'method of treating', 'for use in'],
        }
        
        text = ' '.join(str(s).lower() for s in synonyms)
        
        for ptype, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                types.append(ptype)
        
        return types
    
    # ============= THERAPEUTIC AREA =============
    
    def detect_therapeutic_area(self, indications: List[str]) -> str:
        """
        Mapeia indicações para therapy areas - CORTELLIS STYLE
        """
        area_mapping = {
            'oncology': ['cancer', 'carcinoma', 'tumor', 'leukemia', 'lymphoma', 'neoplasm'],
            'cardiology': ['hypertension', 'heart failure', 'arrhythmia', 'cardiovascular'],
            'neurology': ['alzheimer', 'parkinson', 'epilepsy', 'pain', 'neurology'],
            'metabolic': ['diabetes', 'obesity'],
            'infectious': ['hiv', 'hepatitis', 'infection'],
            'immunology': ['inflammation', 'arthritis', 'asthma', 'immunology'],
            'psychiatry': ['depression', 'anxiety', 'schizophrenia'],
        }
        
        for area, keywords in area_mapping.items():
            if any(ind in keywords for ind in indications):
                return area
        
        return 'general'
    
    # ============= PUBCHEM =============
    
    async def enrich_pubchem(self, client: httpx.AsyncClient, molecule: str) -> Dict:
        """PubChem enrichment"""
        data = {
            'synonyms': [],
            'dev_codes': [],
            'cas_numbers': [],
            'formula': None,
            'inchi': None,
            'smiles': None,
        }
        
        try:
            # Synonyms
            response = await client.get(
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/synonyms/JSON",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                synonyms = result.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
                
                # Process synonyms
                for syn in synonyms:
                    syn_str = str(syn)
                    
                    # CAS number pattern
                    if re.match(r'^\d{2,7}-\d{2}-\d$', syn_str):
                        data['cas_numbers'].append(syn_str)
                    
                    # Dev code patterns
                    elif re.match(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', syn_str, re.I):
                        data['dev_codes'].append(syn_str)
                    
                    # All synonyms
                    data['synonyms'].append(syn_str)
                
                logger.info(f"   📊 PubChem: {len(data['dev_codes'])} dev codes, {len(data['cas_numbers'])} CAS")
            
            # Chemical properties
            response = await client.get(
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/property/MolecularFormula,InChI,CanonicalSMILES/JSON",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                props = result.get('PropertyTable', {}).get('Properties', [{}])[0]
                
                data['formula'] = props.get('MolecularFormula')
                data['inchi'] = props.get('InChI')
                data['smiles'] = props.get('CanonicalSMILES')
                
                logger.info(f"   ✅ Formula: {data['formula']}")
        
        except Exception as e:
            logger.debug(f"PubChem error: {e}")
        
        return data
    
    # ============= OPENFDA =============
    
    async def enrich_openfda(self, client: httpx.AsyncClient, molecule: str, brand: str) -> Dict:
        """OpenFDA enrichment"""
        data = {
            'companies': [],
            'brand_names': [],
        }
        
        for term in [molecule, brand]:
            if not term:
                continue
            
            try:
                response = await client.get(
                    f"https://api.fda.gov/drug/drugsfda.json",
                    params={
                        'search': f'openfda.brand_name:{term}+openfda.generic_name:{term}',
                        'limit': 100
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    
                    for result in results:
                        # Companies
                        sponsor = result.get('sponsor_name')
                        if sponsor:
                            data['companies'].append(sponsor)
                        
                        # Brand names
                        products = result.get('products', [])
                        for prod in products:
                            brand = prod.get('brand_name')
                            if brand:
                                data['brand_names'].append(brand)
                    
                    if data['companies']:
                        logger.info(f"   ✅ Company: {data['companies'][0]}")
            
            except Exception as e:
                logger.debug(f"OpenFDA error for {term}: {e}")
        
        # Deduplicate
        data['companies'] = list(set(data['companies']))
        data['brand_names'] = list(set(data['brand_names']))
        
        return data
    
    # ============= PUBMED =============
    
    async def enrich_pubmed(self, client: httpx.AsyncClient, molecule: str) -> Dict:
        """PubMed enrichment - abstracts for mechanism/indication detection"""
        data = {
            'abstracts': [],
            'article_count': 0,
        }
        
        try:
            # Search
            response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={
                    'db': 'pubmed',
                    'term': f'{molecule} patent',
                    'retmax': 50,
                    'retmode': 'json'
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                id_list = result.get('esearchresult', {}).get('idlist', [])
                data['article_count'] = len(id_list)
                
                logger.info(f"   📊 PubMed: Found {data['article_count']} articles")
                
                # Fetch summaries for mechanism/indication detection
                if id_list[:10]:  # Top 10 articles
                    response = await client.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                        params={
                            'db': 'pubmed',
                            'id': ','.join(id_list[:10]),
                            'retmode': 'json'
                        },
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        summaries = response.json().get('result', {})
                        
                        for pmid, article in summaries.items():
                            if pmid == 'uids':
                                continue
                            
                            title = article.get('title', '')
                            # Abstract not in summary, but title is useful
                            if title:
                                data['abstracts'].append(title)
        
        except Exception as e:
            logger.debug(f"PubMed error: {e}")
        
        return data
    
    # ============= CLINICALTRIALS.GOV (NOVO!) =============
    
    async def enrich_clinicaltrials(self, client: httpx.AsyncClient, molecule: str) -> Dict:
        """
        ClinicalTrials.gov enrichment - NOVO!
        
        Dados críticos para R&D:
        - Trial phases (Phase 1, 2, 3, 4)
        - Indications (conditions)
        - Status (recruiting, completed, terminated)
        - Sponsors
        """
        data = {
            'trials': [],
            'phases': [],
            'conditions': [],
            'sponsors': [],
            'total_trials': 0,
        }
        
        try:
            # ClinicalTrials.gov API v2
            response = await client.get(
                "https://clinicaltrials.gov/api/v2/studies",
                params={
                    'query.term': molecule,
                    'pageSize': 50,
                    'format': 'json'
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                studies = result.get('studies', [])
                data['total_trials'] = len(studies)
                
                for study in studies:
                    protocol = study.get('protocolSection', {})
                    
                    # Identification
                    nct_id = protocol.get('identificationModule', {}).get('nctId')
                    title = protocol.get('identificationModule', {}).get('briefTitle')
                    
                    # Status
                    status_module = protocol.get('statusModule', {})
                    overall_status = status_module.get('overallStatus')
                    
                    # Phase
                    design = protocol.get('designModule', {})
                    phases = design.get('phases', [])
                    
                    # Conditions
                    conditions_module = protocol.get('conditionsModule', {})
                    conditions = conditions_module.get('conditions', [])
                    
                    # Sponsor
                    sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
                    lead_sponsor = sponsor_module.get('leadSponsor', {}).get('name')
                    
                    # Store trial
                    trial_data = {
                        'nct_id': nct_id,
                        'title': title,
                        'status': overall_status,
                        'phases': phases,
                        'conditions': conditions,
                        'sponsor': lead_sponsor,
                    }
                    
                    data['trials'].append(trial_data)
                    
                    # Aggregate data
                    if phases:
                        data['phases'].extend(phases)
                    if conditions:
                        data['conditions'].extend(conditions)
                    if lead_sponsor:
                        data['sponsors'].append(lead_sponsor)
                
                # Deduplicate aggregates
                data['phases'] = list(set(data['phases']))
                data['conditions'] = list(set(data['conditions']))
                data['sponsors'] = list(set(data['sponsors']))
                
                logger.info(f"   🧪 ClinicalTrials.gov: {data['total_trials']} trials")
                logger.info(f"      Phases: {', '.join(data['phases'])}")
                logger.info(f"      Top conditions: {', '.join(data['conditions'][:3])}")
        
        except Exception as e:
            logger.debug(f"ClinicalTrials.gov error: {e}")
        
        return data
    
    # ============= MASTER ENRICHMENT =============
    
    async def run_all_enrichment(self, client: httpx.AsyncClient, molecule: str, brand: str = None) -> Dict:
        """
        Run ALL enrichment sources
        """
        logger.info(f"🔍 ENRICHMENT: Starting comprehensive data extraction for {molecule}")
        
        enriched = {
            'synonyms': [],
            'dev_codes': [],
            'cas_numbers': [],
            'companies': [],
            'brand_names': [],
            'mechanisms': [],
            'indications': [],
            'patent_types': [],
            'therapeutic_area': None,
            'formula': None,
            'inchi': None,
            'smiles': None,
            'clinical_trials': {},
            'pubmed_articles': 0,
        }
        
        # Run all sources
        logger.info(f"📊 ENRICHMENT: PubChem for {molecule}")
        pubchem_data = await self.enrich_pubchem(client, molecule)
        
        logger.info(f"📊 ENRICHMENT: OpenFDA for {molecule}")
        openfda_data = await self.enrich_openfda(client, molecule, brand or '')
        
        logger.info(f"📊 ENRICHMENT: PubMed for {molecule}")
        pubmed_data = await self.enrich_pubmed(client, molecule)
        
        logger.info(f"📊 ENRICHMENT: ClinicalTrials.gov for {molecule}")
        clinical_data = await self.enrich_clinicaltrials(client, molecule)
        
        # Merge data
        enriched['synonyms'] = pubchem_data['synonyms'] + openfda_data['brand_names']
        enriched['dev_codes'] = pubchem_data['dev_codes']
        enriched['cas_numbers'] = pubchem_data['cas_numbers']
        enriched['companies'] = openfda_data['companies'] + clinical_data['sponsors']
        enriched['brand_names'] = openfda_data['brand_names']
        enriched['formula'] = pubchem_data['formula']
        enriched['inchi'] = pubchem_data['inchi']
        enriched['smiles'] = pubchem_data['smiles']
        enriched['clinical_trials'] = clinical_data
        enriched['pubmed_articles'] = pubmed_data['article_count']
        
        # CRITICAL: Detect mechanisms and indications
        enriched['mechanisms'] = self.detect_mechanisms(
            enriched['synonyms'],
            pubmed_data['abstracts']
        )
        
        enriched['indications'] = self.detect_indications(
            enriched['synonyms'] + clinical_data['conditions'],
            pubmed_data['abstracts']
        )
        
        enriched['patent_types'] = self.classify_patent_types(enriched['synonyms'])
        enriched['therapeutic_area'] = self.detect_therapeutic_area(enriched['indications'])
        
        # Deduplicate
        enriched['synonyms'] = list(set(enriched['synonyms']))
        enriched['companies'] = list(set(enriched['companies']))
        enriched['brand_names'] = list(set(enriched['brand_names']))
        
        logger.info(f"✅ ENRICHMENT COMPLETE:")
        logger.info(f"   - Synonyms: {len(enriched['synonyms'])}")
        logger.info(f"   - Dev codes: {len(enriched['dev_codes'])}")
        logger.info(f"   - CAS numbers: {len(enriched['cas_numbers'])}")
        logger.info(f"   - Companies: {len(enriched['companies'])}")
        logger.info(f"   - Mechanisms: {len(enriched['mechanisms'])}")
        logger.info(f"   - Indications: {len(enriched['indications'])}")
        logger.info(f"   - Clinical trials: {enriched['clinical_trials']['total_trials']}")
        logger.info(f"   - Therapeutic area: {enriched['therapeutic_area']}")
        
        return enriched
