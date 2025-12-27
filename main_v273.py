"""
Pharmyrus v27.3 HYBRID SUPREME
Base: v26 proven queries (173 WOs)
+ Dynamic queries (Cortellis-inspired)
+ Fixed priority/citation search
+ Filtered enrichment
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
from data_enrichment import data_enrichment
from google_patents_crawler import google_crawler
from search_state import SearchState
from expert_query_builder import ExpertQueryBuilder

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

app = FastAPI(
    title="Pharmyrus v27.3 HYBRID",
    description="Patent Search with Cortellis-inspired strategy",
    version="27.3"
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


# ============= ENRICHMENT FILTER =============

def filter_synonyms_for_epo(synonyms: List[str]) -> List[str]:
    """Filtra sinônimos para EPO - só os que funcionam"""
    filtered = []
    for syn in synonyms:
        # Skip se muito longo
        if len(syn) > 30:
            continue
        # Skip se tem parentheses (ex: "Darolutamide (JAN/USAN)")
        if "(" in syn or ")" in syn:
            continue
        # Skip se tem barra
        if "/" in syn:
            continue
        # OK!
        filtered.append(syn)
    return filtered[:10]  # Top 10


def filter_dev_codes_for_epo(dev_codes: List[str]) -> List[str]:
    """Filtra dev codes - só padrões válidos"""
    filtered = []
    for code in dev_codes:
        # Padrão: XX-12345 ou XX12345
        if re.match(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', code, re.I):
            filtered.append(code)
            # Adicionar versão sem hífen
            code_no_hyphen = code.replace("-", "")
            if code_no_hyphen != code:
                filtered.append(code_no_hyphen)
    return filtered[:15]  # Top 15


def filter_companies_for_epo(companies: List[str]) -> List[str]:
    """Filtra companies - só empresas reais"""
    filtered = []
    for company in companies:
        # Skip se muito longo
        if len(company) > 50:
            continue
        # Deve ter indicador de empresa
        company_lower = company.lower()
        if any(x in company_lower for x in ["pharma", "inc", "ltd", "corp", "gmbh", "sa", "ag", "ab", "llc"]):
            filtered.append(company)
    return filtered[:10]  # Top 10


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


def build_v26_core_queries(molecule: str, brand: str) -> List[str]:
    """Queries v26 COMPROVADAS (173 WOs)"""
    queries = []
    
    # Core molecule
    queries.append(f'txt="{molecule}"')
    queries.append(f'ti="{molecule}"')
    queries.append(f'ab="{molecule}"')
    
    if brand:
        queries.append(f'txt="{brand}"')
        queries.append(f'ti="{brand}"')
    
    # Therapeutic/mechanism queries (v26 proven)
    queries.append('txt="nonsteroidal antiandrogen"')
    queries.append('txt="androgen receptor antagonist"')
    queries.append('ti="androgen receptor" and ti="antagonist"')
    queries.append('ti="androgen receptor" and ti="inhibitor"')
    
    return queries


def build_cortellis_inspired_queries(molecule: str, enriched_data: Dict) -> List[str]:
    """Queries inspiradas em Cortellis"""
    queries = []
    
    # Category 1: FORMULATION (Cortellis type)
    queries.append(f'txt="{molecule}" and txt="formulation"')
    queries.append(f'txt="{molecule}" and txt="pharmaceutical composition"')
    queries.append(f'txt="{molecule}" and txt="tablet"')
    queries.append(f'txt="{molecule}" and txt="capsule"')
    
    # Category 2: CRYSTALLINE FORMS
    queries.append(f'txt="{molecule}" and txt="crystalline"')
    queries.append(f'txt="{molecule}" and txt="polymorph"')
    queries.append(f'txt="{molecule}" and txt="crystal"')
    
    # Category 3: SALT FORMS
    queries.append(f'txt="{molecule}" and txt="salt"')
    queries.append(f'txt="{molecule}" and txt="mesylate"')
    
    # Category 4: SYNTHESIS/PROCESS
    queries.append(f'txt="{molecule}" and txt="synthesis"')
    queries.append(f'txt="{molecule}" and txt="preparation"')
    queries.append(f'txt="{molecule}" and txt="process"')
    
    # Category 5: THERAPEUTIC USE
    queries.append(f'txt="{molecule}" and txt="prostate cancer"')
    queries.append(f'txt="{molecule}" and txt="castration resistant"')
    queries.append(f'txt="{molecule}" and txt="treatment"')
    
    # Category 6: DRUG COMBINATIONS
    queries.append(f'txt="{molecule}" and txt="combination"')
    
    # Category 7: IPC CODES (Cortellis usa muito!)
    queries.append('ic="A61K31/4439"')  # Darolutamide class
    queries.append('ic="A61K31/44"')    # Pyridines
    queries.append('ic="A61K9"')        # Medicinal preparations
    queries.append('ic="A61P35"')       # Antineoplastic
    
    return queries


def build_dynamic_queries(enriched_data: Dict) -> List[str]:
    """Queries dinâmicas com filtro"""
    queries = []
    
    # Dev codes FILTRADOS
    dev_codes = filter_dev_codes_for_epo(enriched_data.get("dev_codes", []))
    for code in dev_codes[:10]:
        queries.append(f'txt="{code}"')
    
    # Companies FILTRADAS
    companies = filter_companies_for_epo(enriched_data.get("companies", []))
    for company in companies[:5]:
        queries.append(f'pa="{company}" and ti="receptor"')
        queries.append(f'pa="{company}" and ic="A61K31"')
    
    return queries


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
    CORRIGIDO: Busca WOs relacionados via publication-reference (NÃO priority-claim!)
    """
    additional_wos = set()
    
    logger.info(f"   🔄 EPO priority search: Checking {len(found_wos[:15])} WOs...")
    
    for wo in found_wos[:15]:  # Aumentado de 10 para 15
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
                    # CORREÇÃO: usar publication-reference, NÃO priority-claim!
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
        "message": "Pharmyrus v27.3 HYBRID SUPREME", 
        "version": "27.3",
        "strategy": "v26 proven queries + Cortellis-inspired + Fixed priority search"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "27.3"}


@app.get("/countries")
async def list_countries():
    return {"countries": COUNTRY_CODES}


@app.post("/search")
async def search_patents(request: SearchRequest):
    """Busca HYBRID: v26 + Cortellis + Dynamic filtered"""
    
    start_time = datetime.now()
    
    molecule = request.nome_molecula.strip()
    brand = (request.nome_comercial or "").strip()
    target_countries = [c.upper() for c in request.paises_alvo if c.upper() in COUNTRY_CODES]
    
    if not target_countries:
        target_countries = ["BR"]
    
    logger.info(f"{'='*80}")
    logger.info(f"🚀 PHARMYRUS v27.3 HYBRID SEARCH STARTED")
    logger.info(f"{'='*80}")
    logger.info(f"Molecule: {molecule}")
    logger.info(f"Brand: {brand}")
    logger.info(f"Countries: {target_countries}")
    
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
        
        # ===== LAYER 1: EPO OPS HYBRID =====
        logger.info(f"\n{'='*80}")
        logger.info(f"🔵 LAYER 1: EPO OPS (HYBRID v26 + Cortellis)")
        logger.info(f"{'='*80}")
        
        token = await get_epo_token(client)
        logger.info("   ✅ EPO token obtained")
        
        # Build queries using EXPERT QUERY BUILDER
        query_builder = ExpertQueryBuilder(molecule, brand, enriched_data)
        queries = query_builder.build_all_queries()
        query_stats = query_builder.get_query_stats(queries)
        
        state.epo_status["queries_total"] = len(queries)
        logger.info(f"   📊 Generated {len(queries)} EXPERT queries:")
        logger.info(f"      - v26 proven: {query_stats['by_category']['v26_proven']}")
        logger.info(f"      - Combination therapy: {query_stats['by_category']['combination_therapy']}")
        logger.info(f"      - Formulation: {query_stats['by_category']['formulation']}")
        logger.info(f"      - Crystalline: {query_stats['by_category']['crystalline']}")
        logger.info(f"      - IPC codes: {query_stats['by_category']['ipc_codes']}")
        logger.info(f"      - Companies: {query_stats['by_category']['companies']}")
        logger.info(f"      - Others: {len(queries) - sum([query_stats['by_category']['v26_proven'], query_stats['by_category']['combination_therapy'], query_stats['by_category']['formulation'], query_stats['by_category']['crystalline'], query_stats['by_category']['ipc_codes'], query_stats['by_category']['companies']])}")
        
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
        
        # Priority search (FIXED!)
        if epo_wos:
            related_wos = await search_related_wos_FIXED(client, token, list(epo_wos), state)
            if related_wos:
                state.add_wos("epo_priority", set(related_wos))
                epo_wos.update(related_wos)
                state.mark_epo_phase_complete("priority_search")
                logger.info(f"   ✅ EPO priority search: {len(related_wos)} additional WOs")
            else:
                state.mark_epo_phase_complete("priority_search")
                logger.info(f"   ✅ EPO priority search: 0 additional WOs")
        
        # Citation search (improved: 10 WOs)
        key_wos = list(epo_wos)[:10]  # Aumentado de 5 para 10
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
                "version": "Pharmyrus v27.3 HYBRID SUPREME",
                "strategy": "v26 proven + Cortellis-inspired + Fixed priority"
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
