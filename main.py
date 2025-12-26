"""
Pharmyrus v27.2 DYNAMIC - Patent Search System
Layer 0: Data Enrichment (PubChem, OpenFDA, PubMed)
Layer 1: EPO OPS (Complete with feedback loops)
Layer 2: Google Patents (Dynamic with enriched data)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import httpx
import base64
import asyncio
import re
import json
from datetime import datetime
import logging

# Import custom modules
from data_enrichment import data_enrichment
from google_patents_crawler import google_crawler
from search_state import SearchState

# Logging avançado
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

app = FastAPI(
    title="Pharmyrus v27.2",
    description="Dynamic Patent Search with Multi-Source Data Enrichment",
    version="27.2"
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


# ============= EPO LAYER FUNCTIONS (MANTIDAS DO v27.1) =============

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


def build_search_queries_dynamic(
    molecule: str,
    brand: str,
    enriched_data: Dict,
    found_assignees: Set[str] = None
) -> List[str]:
    """
    Constrói queries EPO DINÂMICAS usando dados enriched
    """
    queries = []
    
    # 1. Nome da molécula
    queries.append(f'txt="{molecule}"')
    queries.append(f'ti="{molecule}"')
    queries.append(f'ab="{molecule}"')
    
    # 2. Nome comercial
    if brand:
        queries.append(f'txt="{brand}"')
        queries.append(f'ti="{brand}"')
    
    # 3. SINÔNIMOS extraídos (DINÂMICO!)
    synonyms = enriched_data.get("synonyms", [])
    for syn in synonyms[:10]:  # Top 10
        if len(syn) > 4 and len(syn) < 50:
            queries.append(f'txt="{syn}"')
    
    # 4. DEV CODES extraídos (DINÂMICO!)
    dev_codes = enriched_data.get("dev_codes", [])
    for code in dev_codes[:10]:  # Top 10
        queries.append(f'txt="{code}"')
        code_no_hyphen = code.replace("-", "")
        if code_no_hyphen != code:
            queries.append(f'txt="{code_no_hyphen}"')
    
    # 5. CAS NUMBERS extraídos (DINÂMICO!)
    cas_numbers = enriched_data.get("cas_numbers", [])
    for cas in cas_numbers:
        queries.append(f'txt="{cas}"')
    
    # 6. COMPANIES extraídas (DINÂMICO!)
    companies = enriched_data.get("companies", [])
    if companies:
        keywords = ["androgen", "receptor", "crystalline", "pharmaceutical", 
                   "cancer", "inhibitor", "modulating", "antagonist"]
        
        for company in companies[:10]:  # Top 10 empresas
            for kw in keywords[:4]:  # Top 4 keywords
                queries.append(f'pa="{company}" and ti="{kw}"')
    
    # 7. ASSIGNEES ENCONTRADOS (FEEDBACK LOOP!)
    if found_assignees:
        keywords = ["androgen", "receptor", "crystalline", "pharmaceutical"]
        for assignee in list(found_assignees)[:5]:  # Top 5 assignees
            for kw in keywords[:2]:
                queries.append(f'pa="{assignee}" and ti="{kw}"')
    
    # 8. Queries terapêuticas específicas
    queries.append('txt="nonsteroidal antiandrogen"')
    queries.append('txt="androgen receptor antagonist"')
    queries.append('txt="nmCRPC"')
    queries.append('txt="non-metastatic" and txt="castration-resistant"')
    queries.append('ti="androgen receptor" and ti="inhibitor"')
    
    return queries


async def search_epo(client: httpx.AsyncClient, token: str, query: str, state: SearchState) -> List[str]:
    """Executa busca EPO e registra no state"""
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
            
            # Registrar query no state
            state.add_query_executed("epo_text", query, len(wos))
        
    except Exception as e:
        logger.debug(f"EPO search error for '{query}': {e}")
    
    return list(wos)


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


async def search_related_wos(client: httpx.AsyncClient, token: str, found_wos: List[str], state: SearchState) -> List[str]:
    """Busca WOs relacionados via prioridades"""
    additional_wos = set()
    
    logger.info(f"   🔄 EPO priority search: Checking {len(found_wos[:10])} WOs...")
    
    for wo in found_wos[:10]:
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
                    prio = m.get("priority-claim", [])
                    if not isinstance(prio, list):
                        prio = [prio] if prio else []
                    
                    for p in prio:
                        doc_id = p.get("document-id", {})
                        if isinstance(doc_id, list):
                            doc_id = doc_id[0] if doc_id else {}
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


async def get_family_patents(client: httpx.AsyncClient, token: str, wo_number: str, 
                            target_countries: List[str]) -> Dict[str, List[Dict]]:
    """Extrai patentes da família"""
    patents = {cc: [] for cc in target_countries}
    
    try:
        response = await client.get(
            f"https://ops.epo.org/3.2/rest-services/family/publication/docdb/{wo_number}/biblio",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0
        )
        
        if response.status_code == 413:
            response = await client.get(
                f"https://ops.epo.org/3.2/rest-services/family/publication/docdb/{wo_number}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=30.0
            )
        
        if response.status_code != 200:
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
                        
                        bib = member.get("exchange-document", {}).get("bibliographic-data", {}) if "exchange-document" in member else {}
                        
                        titles = bib.get("invention-title", [])
                        if isinstance(titles, dict):
                            titles = [titles]
                        title_en = None
                        title_orig = None
                        for t in titles:
                            if t.get("@lang") == "en":
                                title_en = t.get("$")
                            else:
                                title_orig = t.get("$")
                        
                        applicants = []
                        parties = bib.get("parties", {}).get("applicants", {}).get("applicant", [])
                        if isinstance(parties, dict):
                            parties = [parties]
                        for p in parties[:5]:
                            name = p.get("applicant-name", {}).get("name", {}).get("$")
                            if name:
                                applicants.append(name)
                        
                        pub_date = doc_id.get("date", {}).get("$", "")
                        
                        patent_data = {
                            "patent_number": patent_num,
                            "country": country,
                            "wo_primary": wo_number,
                            "title": title_en,
                            "title_original": title_orig,
                            "abstract": None,
                            "applicants": applicants,
                            "inventors": [],
                            "ipc_codes": [],
                            "publication_date": pub_date,
                            "filing_date": "",
                            "priority_date": None,
                            "kind": kind,
                            "link_espacenet": f"https://worldwide.espacenet.com/patent/search?q=pn%3D{patent_num}",
                            "link_national": f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={patent_num}" if country == "BR" else None,
                            "country_name": COUNTRY_CODES.get(country, country)
                        }
                        
                        patents[country].append(patent_data)
    
    except Exception as e:
        logger.debug(f"Error getting family for {wo_number}: {e}")
    
    return patents


# ============= ENDPOINTS =============

@app.get("/")
async def root():
    return {
        "message": "Pharmyrus v27.2 - Dynamic Patent Search", 
        "version": "27.2",
        "layers": [
            "Layer 0: Data Enrichment (PubChem, OpenFDA, PubMed)",
            "Layer 1: EPO OPS (Dynamic with feedback)",
            "Layer 2: Google Patents (Dynamic with enriched data)"
        ]
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "27.2"}


@app.get("/countries")
async def list_countries():
    return {"countries": COUNTRY_CODES}


@app.post("/search")
async def search_patents(request: SearchRequest):
    """
    Busca DINÂMICA em 3 camadas com feedback loops
    """
    
    start_time = datetime.now()
    
    molecule = request.nome_molecula.strip()
    brand = (request.nome_comercial or "").strip()
    target_countries = [c.upper() for c in request.paises_alvo if c.upper() in COUNTRY_CODES]
    
    if not target_countries:
        target_countries = ["BR"]
    
    logger.info(f"{'='*80}")
    logger.info(f"🚀 PHARMYRUS v27.2 DYNAMIC SEARCH STARTED")
    logger.info(f"{'='*80}")
    logger.info(f"Molecule: {molecule}")
    logger.info(f"Brand: {brand}")
    logger.info(f"Countries: {target_countries}")
    
    # Inicializar state
    state = SearchState(molecule)
    
    async with httpx.AsyncClient() as client:
        # ===== LAYER 0: DATA ENRICHMENT =====
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 LAYER 0: DATA ENRICHMENT")
        logger.info(f"{'='*80}")
        
        enriched_data = await data_enrichment.run_all_enrichment(client, molecule, brand)
        state.mark_enrichment_complete("pubchem")
        state.mark_enrichment_complete("openfda")
        state.mark_enrichment_complete("pubmed")
        
        # ===== LAYER 1: EPO OPS =====
        logger.info(f"\n{'='*80}")
        logger.info(f"🔵 LAYER 1: EPO OPS (DYNAMIC)")
        logger.info(f"{'='*80}")
        
        token = await get_epo_token(client)
        logger.info("   ✅ EPO token obtained")
        
        # Build queries dinâmicas
        queries = build_search_queries_dynamic(
            molecule,
            brand,
            enriched_data,
            state.assignees_found
        )
        
        state.epo_status["queries_total"] = len(queries)
        logger.info(f"   📊 Generated {len(queries)} dynamic EPO queries")
        
        # Text search
        epo_wos = set()
        for i, query in enumerate(queries):
            wos = await search_epo(client, token, query, state)
            epo_wos.update(wos)
            state.epo_status["queries_executed"] = i + 1
            await asyncio.sleep(0.2)
        
        state.add_wos("epo_text", epo_wos)
        state.mark_epo_phase_complete("text_search")
        logger.info(f"   ✅ EPO text search: {len(epo_wos)} WOs")
        
        # Priority search
        if epo_wos:
            related_wos = await search_related_wos(client, token, list(epo_wos), state)
            if related_wos:
                state.add_wos("epo_priority", set(related_wos))
                epo_wos.update(related_wos)
                state.mark_epo_phase_complete("priority_search")
                logger.info(f"   ✅ EPO priority search: {len(related_wos)} additional WOs")
            else:
                state.mark_epo_phase_complete("priority_search")
                logger.info(f"   ✅ EPO priority search: 0 additional WOs")
        
        # Citation search
        key_wos = list(epo_wos)[:5]
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
        
        state.mark_epo_phase_complete("citation_search")
        logger.info(f"   ✅ EPO TOTAL: {len(epo_wos)} WOs")
        
        # ===== LAYER 2: GOOGLE PATENTS =====
        logger.info(f"\n{'='*80}")
        logger.info(f"🟢 LAYER 2: GOOGLE PATENTS (DYNAMIC)")
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
        
        all_patents = []
        for country, patents in patents_by_country.items():
            all_patents.extend(patents)
        
        all_patents.sort(key=lambda x: x.get("publication_date", "") or "", reverse=True)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Final summary
        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 SEARCH COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total WOs: {len(all_wos)}")
        logger.info(f"Total Patents: {len(all_patents)}")
        logger.info(f"By country: {', '.join([f'{c}: {len(patents_by_country.get(c, []))}' for c in target_countries])}")
        logger.info(f"Elapsed: {elapsed:.2f}s")
        logger.info(f"{'='*80}\n")
        
        return {
            "metadata": {
                "molecule": molecule,
                "brand_name": brand,
                "search_date": datetime.now().isoformat(),
                "target_countries": target_countries,
                "elapsed_seconds": round(elapsed, 2),
                "version": "Pharmyrus v27.2 DYNAMIC",
                "sources": [
                    "PubChem (enrichment)",
                    "OpenFDA (enrichment)",
                    "PubMed (enrichment)",
                    "EPO OPS (full)",
                    "Google Patents (dynamic)"
                ]
            },
            "enrichment": {
                "synonyms_found": len(enriched_data.get("synonyms", [])),
                "dev_codes_found": len(enriched_data.get("dev_codes", [])),
                "cas_numbers_found": len(enriched_data.get("cas_numbers", [])),
                "companies_found": len(enriched_data.get("companies", [])),
            },
            "summary": {
                "total_wos": len(all_wos),
                "epo_wos": len(epo_wos),
                "google_wos": len(google_wos),
                "total_patents": len(all_patents),
                "by_country": {c: len(patents_by_country.get(c, [])) for c in target_countries},
                "wos_by_source": state.get_summary()["wos_by_source"],
                "assignees_discovered": state.get_summary()["assignees_found"],
            },
            "wo_patents": sorted(list(all_wos)),
            "patents_by_country": patents_by_country,
            "all_patents": all_patents,
            "search_state": state.get_summary()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
