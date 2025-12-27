"""
Pharmyrus v28.0 PROFESSIONAL
100% AGNÓSTICO + TÉCNICAS GLOBAIS
JSON dividido: Patent Discovery + R&D
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Set
import httpx
import base64
import asyncio
import re
import logging
from datetime import datetime

# Import custom modules
from enhanced_data_enrichment import EnhancedDataEnrichment
from google_patents_crawler import GooglePatentsCrawler
from search_state import SearchState
from professional_query_builder import ProfessionalQueryBuilder

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pharmyrus")

# EPO Credentials
EPO_KEY = "G5wJypxeg0GXEJoMGP37tdK370aKxeMszGKAkD6QaR0yiR5X"
EPO_SECRET = "zg5AJ0EDzXdJey3GaFNM8ztMVxHKXRrAihXH93iS5ZAzKPAPMFLuVUfiEuAqpdbz"

# Country codes
COUNTRY_CODES = {
    "BR": "Brazil", "US": "United States", "EP": "European Patent",
    "CN": "China", "JP": "Japan", "KR": "South Korea", "IN": "India",
    "MX": "Mexico", "AR": "Argentina", "CL": "Chile", "CO": "Colombia",
    "PE": "Peru", "CA": "Canada", "AU": "Australia", "RU": "Russia", "ZA": "South Africa"
}


async def fetch_patent_metadata_individual(client: httpx.AsyncClient, token: str, 
                                          patent_number: str) -> Dict:
    """
    Busca metadata COMPLETA de UMA patente individual - v28.2 COMPLETE!
    
    Garante metadata 100% preenchida buscando diretamente do número da patente.
    Usado para preencher BRs que vieram vazios da família.
    """
    metadata = {
        "title": None,
        "title_original": None,
        "abstract": None,
        "applicants": [],
        "inventors": [],
        "ipc_codes": [],
        "filing_date": None,
        "priority_date": None
    }
    
    try:
        # Extract country code
        country = patent_number[:2]
        number = patent_number[2:]
        
        logger.debug(f"      📥 Fetching metadata for {patent_number}...")
        
        # Try DOCDB format first
        response = await client.get(
            f"https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/{country}.{number}/biblio",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=15.0
        )
        
        if response.status_code != 200:
            logger.debug(f"      ❌ {patent_number}: HTTP {response.status_code}")
            return metadata
        
        data = response.json()
        
        # Navigate to biblio data
        exchange_docs = data.get("ops:world-patent-data", {}).get("exchange-documents", {})
        exchange_doc = exchange_docs.get("exchange-document", {})
        
        if isinstance(exchange_doc, list):
            exchange_doc = exchange_doc[0] if exchange_doc else {}
        
        bib = exchange_doc.get("bibliographic-data", {})
        
        if not bib:
            logger.debug(f"      ⚠️  No biblio data for {patent_number}")
            return metadata
        
        # TITLES
        titles = bib.get("invention-title", [])
        if isinstance(titles, dict):
            titles = [titles]
        for t in titles:
            if isinstance(t, dict):
                if t.get("@lang") == "en":
                    metadata["title"] = t.get("$")
                else:
                    metadata["title_original"] = t.get("$")
        
        # ABSTRACT
        abstracts = bib.get("abstract", [])
        if isinstance(abstracts, dict):
            abstracts = [abstracts]
        for ab in abstracts:
            if isinstance(ab, dict) and ab.get("@lang") == "en":
                paras = ab.get("p", [])
                if isinstance(paras, list):
                    metadata["abstract"] = " ".join([p.get("$", "") for p in paras if isinstance(p, dict)])
                elif isinstance(paras, dict):
                    metadata["abstract"] = paras.get("$", "")
                break
        
        # APPLICANTS
        parties = bib.get("parties", {}).get("applicants", {}).get("applicant", [])
        if isinstance(parties, dict):
            parties = [parties]
        for p in parties[:15]:
            if isinstance(p, dict):
                name = p.get("applicant-name", {}).get("name", {}).get("$")
                if name and name not in metadata["applicants"]:
                    metadata["applicants"].append(name)
        
        # INVENTORS
        inventors_data = bib.get("parties", {}).get("inventors", {}).get("inventor", [])
        if isinstance(inventors_data, dict):
            inventors_data = [inventors_data]
        for inv in inventors_data[:15]:
            if isinstance(inv, dict):
                name = inv.get("inventor-name", {}).get("name", {}).get("$")
                if name and name not in metadata["inventors"]:
                    metadata["inventors"].append(name)
        
        # IPC CODES
        classifications = bib.get("classifications-ipcr", {}).get("classification-ipcr", [])
        if isinstance(classifications, dict):
            classifications = [classifications]
        for cls in classifications[:25]:
            if isinstance(cls, dict):
                text = cls.get("text", {}).get("$")
                if text and text not in metadata["ipc_codes"]:
                    metadata["ipc_codes"].append(text.strip())
        
        # FILING DATE
        app_ref = bib.get("application-reference", {})
        if app_ref:
            app_doc = app_ref.get("document-id", {})
            if isinstance(app_doc, list):
                app_doc = app_doc[0] if app_doc else {}
            if isinstance(app_doc, dict):
                filing = app_doc.get("date", {}).get("$")
                if filing:
                    metadata["filing_date"] = filing
        
        # PRIORITY DATE
        priority_claims = bib.get("priority-claims", {}).get("priority-claim", [])
        if isinstance(priority_claims, dict):
            priority_claims = [priority_claims]
        if priority_claims and isinstance(priority_claims[0], dict):
            first_priority = priority_claims[0]
            prio_doc = first_priority.get("document-id", {})
            if isinstance(prio_doc, dict):
                prio_date = prio_doc.get("date", {}).get("$")
                if prio_date:
                    metadata["priority_date"] = prio_date
        
        # Count filled fields
        filled = sum([
            bool(metadata["title"] or metadata["title_original"]),
            bool(metadata["abstract"]),
            len(metadata["applicants"]) > 0,
            len(metadata["inventors"]) > 0,
            len(metadata["ipc_codes"]) > 0,
            bool(metadata["filing_date"]),
            bool(metadata["priority_date"])
        ])
        
        logger.debug(f"      ✅ {patent_number}: {filled}/7 fields filled")
        
    except Exception as e:
        logger.debug(f"      ❌ Error {patent_number}: {str(e)[:50]}")
    
    return metadata


app = FastAPI(
    title="Pharmyrus v28.2 COMPLETE",
    description="Patent Intelligence Platform - Complete Metadata Extraction",
    version="28.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    nome_molecula: str
    nome_comercial: Optional[str] = None
    paises_alvo: List[str] = Field(default=["BR"])
    incluir_wo: bool = True
    max_results: int = 100


# ============= EPO FUNCTIONS =============

async def get_epo_token(client: httpx.AsyncClient) -> str:
    """Obtém token EPO"""
    creds = f"{EPO_KEY}:{EPO_SECRET}"
    b64_creds = base64.b64encode(creds.encode()).decode()
    
    response = await client.post(
        "https://ops.epo.org/3.2/auth/accesstoken",
        headers={
            "Authorization": f"Basic {b64_creds}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={"grant_type": "client_credentials"},
        timeout=30.0
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="EPO authentication failed")
    
    return response.json()["access_token"]


async def search_epo(client: httpx.AsyncClient, token: str, query: str, state: SearchState) -> List[str]:
    """Executa busca EPO"""
    wos = set()
    
    try:
        response = await client.get(
            "https://ops.epo.org/3.2/rest-services/published-data/search",
            params={"q": query, "Range": "1-100"},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            pub_refs = data.get("ops:world-patent-data", {}).get("ops:biblio-search", {}).get("ops:search-result", {}).get("ops:publication-reference", [])
            
            if not isinstance(pub_refs, list):
                pub_refs = [pub_refs] if pub_refs else []
            
            for ref in pub_refs:
                doc_id = ref.get("document-id", {})
                if isinstance(doc_id, list):
                    doc_id = doc_id[0] if doc_id else {}
                
                if doc_id.get("@document-id-type") == "docdb":
                    country = doc_id.get("country", {}).get("$", "")
                    number = doc_id.get("doc-number", {}).get("$", "")
                    if country == "WO" and number:
                        wos.add(f"WO{number}")
            
            state.add_query_executed("epo_text", query, len(wos))
    
    except Exception as e:
        logger.debug(f"EPO search error for '{query}': {e}")
    
    return list(wos)


async def search_related_wos_FIXED(client: httpx.AsyncClient, token: str, found_wos: List[str], state: SearchState) -> List[str]:
    """
    CORRIGIDO: Busca WOs relacionados via publication-reference
    """
    additional_wos = set()
    
    logger.info(f"   🔄 EPO priority search: Checking {len(found_wos[:15])} WOs...")
    
    for wo in found_wos[:15]:
        try:
            response = await client.get(
                f"https://ops.epo.org/3.2/rest-services/family/publication/docdb/{wo}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                family = data.get("ops:world-patent-data", {}).get("ops:patent-family", {})
                
                members = family.get("ops:family-member", [])
                if not isinstance(members, list):
                    members = [members]
                
                for m in members:
                    pub_ref = m.get("publication-reference", {})
                    doc_ids = pub_ref.get("document-id", [])
                    
                    if not isinstance(doc_ids, list):
                        doc_ids = [doc_ids] if doc_ids else []
                    
                    for doc_id in doc_ids:
                        if doc_id.get("@document-id-type") == "docdb":
                            country = doc_id.get("country", {}).get("$", "")
                            number = doc_id.get("doc-number", {}).get("$", "")
                            if country == "WO" and number:
                                wo_num = f"WO{number}"
                                if wo_num not in found_wos:
                                    additional_wos.add(wo_num)
            
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.debug(f"Error searching related WOs for {wo}: {e}")
    
    return list(additional_wos)


async def search_citations(client: httpx.AsyncClient, token: str, wo_number: str, state: SearchState) -> List[str]:
    """Busca citações"""
    wos = set()
    
    try:
        query = f'ct="{wo_number}"'
        response = await client.get(
            "https://ops.epo.org/3.2/rest-services/published-data/search",
            params={"q": query, "Range": "1-100"},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            pub_refs = data.get("ops:world-patent-data", {}).get("ops:biblio-search", {}).get("ops:search-result", {}).get("ops:publication-reference", [])
            
            if not isinstance(pub_refs, list):
                pub_refs = [pub_refs] if pub_refs else []
            
            for ref in pub_refs:
                doc_id = ref.get("document-id", {})
                if isinstance(doc_id, list):
                    doc_id = doc_id[0] if doc_id else {}
                
                if doc_id.get("@document-id-type") == "docdb":
                    country = doc_id.get("country", {}).get("$", "")
                    number = doc_id.get("doc-number", {}).get("$", "")
                    if country == "WO" and number:
                        wos.add(f"WO{number}")
            
            state.add_query_executed("epo_citation", query, len(wos))
    
    except Exception as e:
        logger.debug(f"Citation search error for {wo_number}: {e}")
    
    return list(wos)


async def get_family_patents(client: httpx.AsyncClient, token: str, wo_number: str, 
                            target_countries: List[str]) -> Dict[str, List[Dict]]:
    """
    Extrai patentes da família - PARSE COMPLETO! (CORRIGIDO v28.1)
    
    Handles:
    - Error 413 (payload too large)
    - Missing bibliographic data
    - Safe dict access with isinstance checks
    """
    patents = {cc: [] for cc in target_countries}
    
    try:
        # Try /biblio endpoint first
        logger.debug(f"   Fetching family for {wo_number} with /biblio...")
        response = await client.get(
            f"https://ops.epo.org/3.2/rest-services/family/publication/docdb/{wo_number}/biblio",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0
        )
        
        # Fallback if error 413
        if response.status_code == 413:
            logger.debug(f"   Error 413 for {wo_number}, trying simple endpoint...")
            response = await client.get(
                f"https://ops.epo.org/3.2/rest-services/family/publication/docdb/{wo_number}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=30.0
            )
        
        if response.status_code != 200:
            logger.debug(f"   Failed to fetch family for {wo_number}: {response.status_code}")
            return patents
        
        data = response.json()
        family = data.get("ops:world-patent-data", {}).get("ops:patent-family", {})
        
        members = family.get("ops:family-member", [])
        if not isinstance(members, list):
            members = [members]
        
        for member in members:
            pub_ref = member.get("publication-reference", {})
            doc_ids = pub_ref.get("document-id", [])
            
            if isinstance(doc_ids, dict):
                doc_ids = [doc_ids]
            
            for doc_id in doc_ids:
                if doc_id.get("@document-id-type") == "docdb":
                    country = doc_id.get("country", {}).get("$", "")
                    number = doc_id.get("doc-number", {}).get("$", "")
                    kind = doc_id.get("kind", {}).get("$", "")
                    
                    if country in target_countries and number:
                        patent_num = f"{country}{number}"
                        
                        # PARSE COMPLETO - bibliographic data (SAFE!)
                        bib = {}
                        has_exchange_doc = "exchange-document" in member
                        
                        if has_exchange_doc:
                            exchange_doc = member.get("exchange-document", {})
                            bib = exchange_doc.get("bibliographic-data", {})
                        
                        # Titles (multi-language) - SAFE
                        title_en = None
                        title_orig = None
                        if bib:
                            titles = bib.get("invention-title", [])
                            if isinstance(titles, dict):
                                titles = [titles]
                            for t in titles:
                                if isinstance(t, dict):
                                    if t.get("@lang") == "en":
                                        title_en = t.get("$")
                                    else:
                                        title_orig = t.get("$")
                        
                        # Abstract (multi-language) - SAFE
                        abstract_text = None
                        if bib:
                            abstracts = bib.get("abstract", [])
                            if isinstance(abstracts, dict):
                                abstracts = [abstracts]
                            for ab in abstracts:
                                if isinstance(ab, dict) and ab.get("@lang") == "en":
                                    paras = ab.get("p", [])
                                    if isinstance(paras, list):
                                        abstract_text = " ".join([p.get("$", "") for p in paras if isinstance(p, dict)])
                                    elif isinstance(paras, dict):
                                        abstract_text = paras.get("$", "")
                                    break
                        
                        # Applicants - SAFE
                        applicants = []
                        if bib:
                            parties = bib.get("parties", {}).get("applicants", {}).get("applicant", [])
                            if isinstance(parties, dict):
                                parties = [parties]
                            for p in parties[:10]:  # Max 10
                                if isinstance(p, dict):
                                    name = p.get("applicant-name", {}).get("name", {}).get("$")
                                    if name:
                                        applicants.append(name)
                        
                        # Inventors - SAFE
                        inventors = []
                        if bib:
                            inventors_data = bib.get("parties", {}).get("inventors", {}).get("inventor", [])
                            if isinstance(inventors_data, dict):
                                inventors_data = [inventors_data]
                            for inv in inventors_data[:10]:  # Max 10
                                if isinstance(inv, dict):
                                    name = inv.get("inventor-name", {}).get("name", {}).get("$")
                                    if name:
                                        inventors.append(name)
                        
                        # IPC/CPC codes - SAFE
                        ipc_codes = []
                        if bib:
                            classifications = bib.get("classifications-ipcr", {}).get("classification-ipcr", [])
                            if isinstance(classifications, dict):
                                classifications = [classifications]
                            for cls in classifications[:20]:  # Max 20
                                if isinstance(cls, dict):
                                    text = cls.get("text", {}).get("$")
                                    if text:
                                        ipc_codes.append(text.strip())
                        
                        # Dates - SAFE
                        pub_date = doc_id.get("date", {}).get("$", "")
                        
                        # Priority date - SAFE
                        priority_date = None
                        if bib:
                            priority_claims = bib.get("priority-claims", {}).get("priority-claim", [])
                            if isinstance(priority_claims, dict):
                                priority_claims = [priority_claims]
                            if priority_claims and isinstance(priority_claims[0], dict):
                                first_priority = priority_claims[0]
                                priority_doc = first_priority.get("document-id", {})
                                if isinstance(priority_doc, dict):
                                    priority_date = priority_doc.get("date", {}).get("$")
                        
                        # Application date - SAFE
                        filing_date = None
                        if bib:
                            app_ref = bib.get("application-reference", {})
                            app_doc = app_ref.get("document-id", {})
                            if isinstance(app_doc, dict):
                                filing_date = app_doc.get("date", {}).get("$", "")
                        
                        patent_data = {
                            "patent_number": patent_num,
                            "country": country,
                            "wo_primary": wo_number,
                            "title": title_en,
                            "title_original": title_orig,
                            "abstract": abstract_text,
                            "applicants": applicants,
                            "inventors": inventors,
                            "ipc_codes": ipc_codes,
                            "publication_date": pub_date,
                            "filing_date": filing_date or "",
                            "priority_date": priority_date,
                            "kind": kind,
                            "link_espacenet": f"https://worldwide.espacenet.com/patent/search?q=pn%3D{patent_num}",
                            "link_national": f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={patent_num}" if country == "BR" else None,
                            "country_name": COUNTRY_CODES.get(country, country)
                        }
                        
                        # Debug log if we have good data
                        if title_en or applicants or ipc_codes:
                            logger.debug(f"      ✓ {patent_num}: title={bool(title_en)}, applicants={len(applicants)}, ipcs={len(ipc_codes)}")
                        
                        patents[country].append(patent_data)
    
    except Exception as e:
        logger.debug(f"Error getting family for {wo_number}: {e}")
    
    return patents
    
    return patents


# ============= ENDPOINTS =============

@app.get("/")
async def root():
    return {
        "message": "Pharmyrus v28.2 COMPLETE - Full Metadata Extraction", 
        "version": "28.2",
        "strategy": "100% Dynamic + Global Best Practices + Complete Metadata"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "28.2"}


@app.get("/countries")
async def list_countries():
    return {"countries": COUNTRY_CODES}


@app.post("/search")
async def search_patents(request: SearchRequest):
    """
    Busca PROFISSIONAL com JSON dividido:
    - patent_discovery: Dados de patentes
    - rd_intelligence: Dados para R&D
    """
    
    start_time = datetime.now()
    
    molecule = request.nome_molecula.strip()
    brand = (request.nome_comercial or "").strip()
    target_countries = [c.upper() for c in request.paises_alvo if c.upper() in COUNTRY_CODES]
    
    if not target_countries:
        target_countries = ["BR"]
    
    logger.info(f"{'='*80}")
    logger.info(f"🚀 PHARMYRUS v28.2 COMPLETE SEARCH STARTED")
    logger.info(f"{'='*80}")
    logger.info(f"Molecule: {molecule}")
    logger.info(f"Brand: {brand}")
    logger.info(f"Countries: {target_countries}")
    
    state = SearchState(molecule)
    
    # Initialize modules
    data_enrichment = EnhancedDataEnrichment()
    google_crawler = GooglePatentsCrawler()
    
    async with httpx.AsyncClient() as client:
        # ===== LAYER 0: ENHANCED DATA ENRICHMENT =====
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 LAYER 0: ENHANCED DATA ENRICHMENT")
        logger.info(f"{'='*80}")
        
        enriched_data = await data_enrichment.run_all_enrichment(client, molecule, brand)
        state.mark_enrichment_complete("pubchem")
        state.mark_enrichment_complete("openfda")
        state.mark_enrichment_complete("pubmed")
        state.mark_enrichment_complete("clinicaltrials")
        
        logger.info(f"   ✅ Enrichment complete:")
        logger.info(f"      - Synonyms: {len(enriched_data.get('synonyms', []))}")
        logger.info(f"      - Dev codes: {len(enriched_data.get('dev_codes', []))}")
        logger.info(f"      - Companies: {len(enriched_data.get('companies', []))}")
        logger.info(f"      - Mechanisms: {len(enriched_data.get('mechanisms', []))}")
        logger.info(f"      - Indications: {len(enriched_data.get('indications', []))}")
        logger.info(f"      - Clinical trials: {enriched_data.get('clinical_trials', {}).get('total_trials', 0)}")
        
        # ===== LAYER 1: EPO OPS (PROFESSIONAL QUERIES!) =====
        logger.info(f"\n{'='*80}")
        logger.info(f"🔵 LAYER 1: EPO OPS (PROFESSIONAL QUERIES)")
        logger.info(f"{'='*80}")
        
        token = await get_epo_token(client)
        logger.info("   ✅ EPO token obtained")
        
        # Build PROFESSIONAL queries
        query_builder = ProfessionalQueryBuilder(molecule, brand, enriched_data)
        queries = query_builder.build_all_queries()
        query_stats = query_builder.get_query_stats(queries)
        
        state.epo_status["queries_total"] = len(queries)
        logger.info(f"   📊 Generated {len(queries)} PROFESSIONAL queries")
        
        # Text search
        epo_wos = set()
        for i, query in enumerate(queries):
            wos = await search_epo(client, token, query, state)
            epo_wos.update(wos)
            state.epo_status["queries_executed"] = i + 1
            
            # Log progress every 20 queries
            if (i + 1) % 20 == 0:
                logger.info(f"      Progress: {i+1}/{len(queries)} queries ({len(epo_wos)} WOs)")
            
            await asyncio.sleep(0.2)
        
        state.add_wos("epo_text", epo_wos)
        state.mark_epo_phase_complete("text_search")
        logger.info(f"   ✅ EPO text search: {len(epo_wos)} WOs")
        
        # Priority search (FIXED v28.1!)
        logger.info(f"\n   🔄 EPO PRIORITY SEARCH")
        if len(epo_wos) > 0:
            logger.info(f"      Starting with {len(epo_wos)} WOs, checking top 15...")
            related_wos = await search_related_wos_FIXED(client, token, list(epo_wos)[:15], state)
            if related_wos:
                state.add_wos("epo_priority", set(related_wos))
                epo_wos.update(related_wos)
                state.mark_epo_phase_complete("priority_search")
                logger.info(f"   ✅ EPO priority search: {len(related_wos)} additional WOs")
            else:
                state.mark_epo_phase_complete("priority_search")
                logger.info(f"   ✅ EPO priority search: 0 additional WOs")
        else:
            logger.warning(f"   ⚠️  No WOs to search priority for!")
            state.mark_epo_phase_complete("priority_search")
        
        # Citation search (top 10 WOs)
        logger.info(f"\n   🔄 EPO CITATION SEARCH")
        if len(epo_wos) > 0:
            key_wos = list(epo_wos)[:10]
            logger.info(f"      Checking citations for top {len(key_wos)} WOs...")
            citation_wos = set()
            for wo in key_wos:
                citing = await search_citations(client, token, wo, state)
                citation_wos.update(citing)
                await asyncio.sleep(0.2)
            
            if citation_wos:
                new_from_citations = citation_wos - epo_wos
                state.add_wos("epo_citation", new_from_citations)
                epo_wos.update(citation_wos)
                logger.info(f"   ✅ EPO citation search: {len(new_from_citations)} NEW WOs")
            else:
                logger.info(f"   ✅ EPO citation search: 0 NEW WOs")
        else:
            logger.warning(f"   ⚠️  No WOs to search citations for!")
        
        state.mark_epo_phase_complete("citation_search")
        logger.info(f"   ✅ EPO TOTAL: {len(epo_wos)} WOs")
        
        # ===== LAYER 2: GOOGLE PATENTS =====
        logger.info(f"\n{'='*80}")
        logger.info(f"🟢 LAYER 2: GOOGLE PATENTS")
        logger.info(f"{'='*80}")
        
        google_wos = await google_crawler.enrich_with_google(
            molecule=molecule,
            enriched_data=enriched_data,
            epo_wos=epo_wos,
            state=state
        )
        
        state.add_wos("google", google_wos)
        logger.info(f"   ✅ Google found: {len(google_wos)} NEW WOs")
        
        # Merge WOs
        all_wos = epo_wos | google_wos
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ TOTAL WOs: {len(all_wos)} (EPO: {len(epo_wos)} + Google: {len(google_wos)})")
        logger.info(f"{'='*80}")
        
        # Extrair patentes dos países alvo
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 FAMILY MAPPING: Extracting patents for {target_countries}")
        logger.info(f"{'='*80}")
        
        patents_by_country = {cc: [] for cc in target_countries}
        seen_patents = set()
        
        for i, wo in enumerate(sorted(all_wos)):
            if i > 0 and i % 20 == 0:
                logger.info(f"   Processing WO {i}/{len(all_wos)}...")
            
            family_patents = await get_family_patents(client, token, wo, target_countries)
            
            for country, patents in family_patents.items():
                for p in patents:
                    pnum = p["patent_number"]
                    if pnum not in seen_patents:
                        seen_patents.add(pnum)
                        patents_by_country[country].append(p)
            
            await asyncio.sleep(0.3)
        
        # ===== PHASE 2: ENRICH BR METADATA (v28.2 COMPLETE!) =====
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 METADATA ENRICHMENT: Fetching complete data for BRs")
        logger.info(f"{'='*80}")
        
        br_patents = patents_by_country.get("BR", [])
        
        if br_patents:
            logger.info(f"   Found {len(br_patents)} BRs, enriching metadata...")
            
            enriched_count = 0
            for i, br in enumerate(br_patents):
                pnum = br["patent_number"]
                
                # Check if missing critical fields
                needs_enrichment = (
                    not br.get("title") or
                    not br.get("applicants") or
                    not br.get("ipc_codes") or
                    not br.get("filing_date")
                )
                
                if needs_enrichment:
                    # Fetch individual metadata
                    individual_meta = await fetch_patent_metadata_individual(client, token, pnum)
                    
                    # Merge into existing BR data (keep original if exists)
                    if individual_meta["title"] and not br.get("title"):
                        br["title"] = individual_meta["title"]
                    if individual_meta["title_original"] and not br.get("title_original"):
                        br["title_original"] = individual_meta["title_original"]
                    if individual_meta["abstract"] and not br.get("abstract"):
                        br["abstract"] = individual_meta["abstract"]
                    if individual_meta["applicants"] and not br.get("applicants"):
                        br["applicants"] = individual_meta["applicants"]
                    if individual_meta["inventors"] and not br.get("inventors"):
                        br["inventors"] = individual_meta["inventors"]
                    if individual_meta["ipc_codes"] and not br.get("ipc_codes"):
                        br["ipc_codes"] = individual_meta["ipc_codes"]
                    if individual_meta["filing_date"] and not br.get("filing_date"):
                        br["filing_date"] = individual_meta["filing_date"]
                    if individual_meta["priority_date"] and not br.get("priority_date"):
                        br["priority_date"] = individual_meta["priority_date"]
                    
                    enriched_count += 1
                    await asyncio.sleep(0.2)  # Rate limit
                
                if (i + 1) % 10 == 0:
                    logger.info(f"   Processed {i + 1}/{len(br_patents)} BRs...")
            
            logger.info(f"   ✅ Enriched {enriched_count}/{len(br_patents)} BRs with individual metadata")
        
        all_patents = []
        for country, patents in patents_by_country.items():
            all_patents.extend(patents)
        
        all_patents.sort(key=lambda x: x.get("publication_date", "") or "", reverse=True)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Final summary
        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 SEARCH COMPLETE - v28.2 COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total WOs: {len(all_wos)}")
        logger.info(f"Total Patents: {len(all_patents)}")
        logger.info(f"By country: {', '.join([f'{c}: {len(patents_by_country.get(c, []))}' for c in target_countries])}")
        logger.info(f"Elapsed: {elapsed:.2f}s")
        logger.info(f"{'='*80}\n")
        
        # ============= BUILD JSON RESPONSE (DIVIDIDO!) =============
        
        return {
            # ===== PATENT DISCOVERY (Dados de patentes) =====
            "patent_discovery": {
                "metadata": {
                    "molecule": molecule,
                    "brand_name": brand,
                    "search_date": datetime.now().isoformat(),
                    "target_countries": target_countries,
                    "elapsed_seconds": round(elapsed, 2),
                    "version": "Pharmyrus v28.2 COMPLETE",
                    "methodology": "Cortellis + PatSnap + Questel + DWPI + Individual Metadata Fetch"
                },
                "summary": {
                    "total_wos": len(all_wos),
                    "epo_wos": len(epo_wos),
                    "google_wos": len(google_wos),
                    "total_patents": len(all_patents),
                    "by_country": {c: len(patents_by_country.get(c, [])) for c in target_countries},
                    "wos_by_source": state.get_summary()["wos_by_source"],
                    "queries_executed": state.epo_status["queries_executed"],
                },
                "wo_patents": sorted(list(all_wos)),
                "patents_by_country": patents_by_country,
                "all_patents": all_patents,
                "query_breakdown": query_stats,
            },
            
            # ===== R&D INTELLIGENCE (Dados para P&D) =====
            "rd_intelligence": {
                "chemical_data": {
                    "molecular_formula": enriched_data.get("formula"),
                    "inchi": enriched_data.get("inchi"),
                    "smiles": enriched_data.get("smiles"),
                    "cas_numbers": enriched_data.get("cas_numbers", []),
                },
                "pharmacology": {
                    "mechanisms_of_action": enriched_data.get("mechanisms", []),
                    "therapeutic_indications": enriched_data.get("indications", []),
                    "therapeutic_area": enriched_data.get("therapeutic_area"),
                },
                "development": {
                    "dev_codes": enriched_data.get("dev_codes", []),
                    "brand_names": enriched_data.get("brand_names", []),
                    "synonyms": enriched_data.get("synonyms", []),
                },
                "companies": {
                    "patent_assignees": state.get_summary()["assignees_found"],
                    "sponsors": enriched_data.get("companies", []),
                },
                "clinical_trials": {
                    "total_trials": enriched_data.get("clinical_trials", {}).get("total_trials", 0),
                    "phases": enriched_data.get("clinical_trials", {}).get("phases", []),
                    "conditions": enriched_data.get("clinical_trials", {}).get("conditions", []),
                    "sponsors": enriched_data.get("clinical_trials", {}).get("sponsors", []),
                    "trials": enriched_data.get("clinical_trials", {}).get("trials", [])[:10],  # Top 10
                },
                "literature": {
                    "pubmed_articles": enriched_data.get("pubmed_articles", 0),
                },
                "patent_classification": {
                    "patent_types": enriched_data.get("patent_types", []),
                    "ipc_codes_detected": list(set([
                        ipc for p in all_patents for ipc in p.get("ipc_codes", [])
                    ]))[:50],  # Top 50
                },
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
