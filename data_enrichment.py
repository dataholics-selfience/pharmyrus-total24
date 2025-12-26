"""
Data Enrichment Layer 0 - DYNAMIC
Extrai dados de múltiplas fontes públicas para alimentar buscas
"""
import asyncio
import httpx
import re
from typing import Dict, List, Set
import logging

logger = logging.getLogger("pharmyrus.enrichment")


class DataEnrichment:
    """Extrai dados de múltiplas fontes públicas"""
    
    def __init__(self):
        self.enriched_data = {
            "synonyms": set(),
            "dev_codes": set(),
            "cas_numbers": set(),
            "companies": set(),
            "therapeutic_terms": set(),
            "chemical_formulas": set(),
            "inchi": set(),
            "smiles": set(),
        }
    
    async def enrich_from_pubchem(self, client: httpx.AsyncClient, molecule: str) -> Dict:
        """PubChem: Sinônimos, CAS, InChI, SMILES, formulas moleculares"""
        logger.info(f"📊 ENRICHMENT: PubChem for {molecule}")
        
        try:
            # Synonyms
            response = await client.get(
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/synonyms/JSON",
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                synonyms = data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
                
                for syn in synonyms[:200]:
                    syn_clean = syn.strip()
                    
                    # Dev codes
                    if re.match(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', syn_clean, re.I) and len(syn_clean) < 25:
                        self.enriched_data["dev_codes"].add(syn_clean)
                        logger.info(f"   ✅ Dev code: {syn_clean}")
                    
                    # CAS numbers
                    elif re.match(r'^\d{2,7}-\d{2}-\d$', syn_clean):
                        self.enriched_data["cas_numbers"].add(syn_clean)
                        logger.info(f"   ✅ CAS: {syn_clean}")
                    
                    # Sinônimos gerais
                    elif len(syn_clean) > 3 and len(syn_clean) < 100:
                        self.enriched_data["synonyms"].add(syn_clean)
                
                logger.info(f"   📊 PubChem: {len(self.enriched_data['dev_codes'])} dev codes, {len(self.enriched_data['cas_numbers'])} CAS")
            
            # Properties (formula, InChI, SMILES)
            await asyncio.sleep(0.5)
            response = await client.get(
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/property/MolecularFormula,InChI,CanonicalSMILES/JSON",
                timeout=30.0
            )
            
            if response.status_code == 200:
                props = response.json().get("PropertyTable", {}).get("Properties", [{}])[0]
                
                if "MolecularFormula" in props:
                    self.enriched_data["chemical_formulas"].add(props["MolecularFormula"])
                    logger.info(f"   ✅ Formula: {props['MolecularFormula']}")
                
                if "InChI" in props:
                    self.enriched_data["inchi"].add(props["InChI"])
                
                if "CanonicalSMILES" in props:
                    self.enriched_data["smiles"].add(props["CanonicalSMILES"])
        
        except Exception as e:
            logger.warning(f"   ⚠️  PubChem error: {e}")
        
        return self.enriched_data
    
    async def enrich_from_openfda(self, client: httpx.AsyncClient, molecule: str, brand: str = None) -> Dict:
        """OpenFDA: Drug applications, sponsors/applicants, approval dates"""
        logger.info(f"📊 ENRICHMENT: OpenFDA for {molecule}")
        
        try:
            search_terms = [molecule]
            if brand:
                search_terms.append(brand)
            
            for term in search_terms:
                response = await client.get(
                    f"https://api.fda.gov/drug/drugsfda.json?search=openfda.brand_name:{term}+openfda.generic_name:{term}&limit=100",
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    for result in results:
                        sponsor = result.get("sponsor_name", "")
                        if sponsor and len(sponsor) < 100:
                            self.enriched_data["companies"].add(sponsor)
                            logger.info(f"   ✅ Company: {sponsor}")
                        
                        openfda = result.get("openfda", {})
                        for brand_name in openfda.get("brand_name", []):
                            if len(brand_name) < 100:
                                self.enriched_data["synonyms"].add(brand_name)
                        
                        for generic in openfda.get("generic_name", []):
                            if len(generic) < 100:
                                self.enriched_data["synonyms"].add(generic)
                
                await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.warning(f"   ⚠️  OpenFDA error: {e}")
        
        return self.enriched_data
    
    async def enrich_from_pubmed(self, client: httpx.AsyncClient, molecule: str) -> Dict:
        """PubMed: Artigos científicos → termos relacionados, autores, instituições"""
        logger.info(f"📊 ENRICHMENT: PubMed for {molecule}")
        
        try:
            response = await client.get(
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={molecule}+patent&retmax=50&retmode=json",
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])
                
                logger.info(f"   📊 PubMed: Found {len(id_list)} articles")
                
                if id_list:
                    ids_str = ",".join(id_list[:10])
                    
                    await asyncio.sleep(0.5)
                    response = await client.get(
                        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json",
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        summaries = response.json().get("result", {})
                        
                        for pmid, article in summaries.items():
                            if pmid == "uids":
                                continue
                            
                            authors = article.get("authors", [])
                            for author in authors[:5]:
                                author_name = author.get("name", "")
                                if len(author_name) > 5 and len(author_name) < 100:
                                    if any(term in author_name.lower() for term in ["inc", "ltd", "corp", "pharma", "gmbh", "sa"]):
                                        self.enriched_data["companies"].add(author_name)
        
        except Exception as e:
            logger.warning(f"   ⚠️  PubMed error: {e}")
        
        return self.enriched_data
    
    async def enrich_from_fda_orangebook(self, client: httpx.AsyncClient, molecule: str, brand: str = None) -> Dict:
        """FDA Orange Book: Approved drugs, applicants, patents"""
        logger.info(f"📊 ENRICHMENT: FDA Orange Book for {molecule}")
        
        try:
            search_terms = [molecule]
            if brand:
                search_terms.append(brand)
            
            for term in search_terms:
                response = await client.get(
                    f"https://api.fda.gov/drug/nda.json?search=products.active_ingredients.name:{term}&limit=100",
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    for result in results:
                        sponsor = result.get("sponsor_name", "")
                        if sponsor and len(sponsor) < 100:
                            self.enriched_data["companies"].add(sponsor)
                            logger.info(f"   ✅ Orange Book Company: {sponsor}")
                        
                        products = result.get("products", [])
                        for product in products:
                            brand_name = product.get("brand_name", "")
                            if brand_name and len(brand_name) < 100:
                                self.enriched_data["synonyms"].add(brand_name)
                            
                            active_ingredients = product.get("active_ingredients", [])
                            for ingredient in active_ingredients:
                                ing_name = ingredient.get("name", "")
                                if ing_name and len(ing_name) < 100:
                                    self.enriched_data["synonyms"].add(ing_name)
                
                await asyncio.sleep(0.5)
                
                if brand:
                    response = await client.get(
                        f"https://api.fda.gov/drug/nda.json?search=products.brand_name:{brand}&limit=100",
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        
                        for result in results:
                            sponsor = result.get("sponsor_name", "")
                            if sponsor and len(sponsor) < 100:
                                self.enriched_data["companies"].add(sponsor)
                    
                    await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.warning(f"   ⚠️  FDA Orange Book error: {e}")
        
        return self.enriched_data
    
    async def run_all_enrichment(self, client: httpx.AsyncClient, molecule: str, brand: str = None) -> Dict:
        """Executa TODAS as fontes de enriquecimento em paralelo"""
        logger.info(f"🔍 ENRICHMENT: Starting comprehensive data extraction for {molecule}")
        
        await asyncio.gather(
            self.enrich_from_pubchem(client, molecule),
            self.enrich_from_openfda(client, molecule, brand),
            self.enrich_from_pubmed(client, molecule),
            self.enrich_from_fda_orangebook(client, molecule, brand),
            return_exceptions=True
        )
        
        result = {
            "synonyms": list(self.enriched_data["synonyms"])[:50],
            "dev_codes": list(self.enriched_data["dev_codes"])[:20],
            "cas_numbers": list(self.enriched_data["cas_numbers"]),
            "companies": list(self.enriched_data["companies"])[:30],
            "therapeutic_terms": list(self.enriched_data["therapeutic_terms"]),
            "chemical_formulas": list(self.enriched_data["chemical_formulas"]),
            "inchi": list(self.enriched_data["inchi"])[:5],
            "smiles": list(self.enriched_data["smiles"])[:5],
        }
        
        logger.info(f"✅ ENRICHMENT COMPLETE:")
        logger.info(f"   - Synonyms: {len(result['synonyms'])}")
        logger.info(f"   - Dev codes: {len(result['dev_codes'])}")
        logger.info(f"   - CAS numbers: {len(result['cas_numbers'])}")
        logger.info(f"   - Companies: {len(result['companies'])}")
        logger.info(f"   - Chemical data: {len(result['chemical_formulas'])} formulas, {len(result['inchi'])} InChI, {len(result['smiles'])} SMILES")
        
        return result


# Singleton
data_enrichment = DataEnrichment()
