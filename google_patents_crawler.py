"""
Google Patents Crawler Layer 2 - DYNAMIC
Usa dados enriched para buscas progressivas
"""
import asyncio
import re
import random
from typing import List, Set, Dict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import logging

logger = logging.getLogger("pharmyrus.google")

# Proxies premium
PROXIES = [
    "http://brd-customer-hl_8ea11d75-zone-residential_proxy1:w7qs41l7ijfc@brd.superproxy.io:33335",
    "http://brd-customer-hl_8ea11d75-zone-datacenter_proxy1:93u1xg5fef4p@brd.superproxy.io:33335",
    "http://5SHQXNTHNKDHUHFD:wifi;us;;;@proxy.scrapingbee.com:8886",
    "http:XNK2KLGACMN0FKRY:wifi;us;;;@proxy.scrapingbee.com:8886",
]


class GooglePatentsCrawler:
    """Crawler DINÂMICO usando dados enriched"""
    
    def __init__(self):
        self.found_wos = set()
        self.found_assignees = set()
        self.proxy_index = 0
    
    def _get_next_proxy(self) -> str:
        """Rotaciona proxies"""
        proxy = PROXIES[self.proxy_index % len(PROXIES)]
        self.proxy_index += 1
        return proxy
    
    def _build_dynamic_search_terms(
        self,
        molecule: str,
        enriched_data: Dict,
        found_wos: Set[str] = None,
        found_assignees: Set[str] = None
    ) -> List[str]:
        """
        Constrói buscas DINÂMICAS baseadas em dados enriched
        """
        terms = []
        
        # 1. SINÔNIMOS extraídos (PubChem, OpenFDA, PubMed)
        synonyms = enriched_data.get("synonyms", [])
        for syn in synonyms[:10]:  # Top 10 sinônimos
            terms.append(f'"{syn}" patent WO')
            terms.append(f'"{syn}" WO site:patents.google.com')
        
        # 2. DEV CODES extraídos
        dev_codes = enriched_data.get("dev_codes", [])
        for code in dev_codes[:10]:  # Top 10 dev codes
            terms.append(f'"{code}" patent WO')
            terms.append(f'"{code}" WO site:patents.google.com')
        
        # 3. CAS NUMBERS extraídos
        cas_numbers = enriched_data.get("cas_numbers", [])
        for cas in cas_numbers[:5]:
            terms.append(f'"{cas}" patent WO')
        
        # 4. COMPANIES/ASSIGNEES extraídos (OpenFDA, PubMed)
        companies = enriched_data.get("companies", [])
        for company in companies[:10]:  # Top 10 empresas
            terms.append(f'{company} "{molecule}" patent WO')
            terms.append(f'"{molecule}" {company} WO')
        
        # 5. CHEMICAL FORMULAS extraídas
        formulas = enriched_data.get("chemical_formulas", [])
        for formula in formulas:
            terms.append(f'"{formula}" patent WO')
        
        # 6. VARIAÇÕES QUÍMICAS (sais, cristais, etc)
        chemical_variants = [
            f'"{molecule}" salt WO',
            f'"{molecule}" crystalline WO',
            f'"{molecule}" polymorph WO',
            f'"{molecule}" formulation WO',
            f'"{molecule}" synthesis WO',
            f'"{molecule}" enantiomer WO',
        ]
        terms.extend(chemical_variants)
        
        # 7. USO TERAPÊUTICO (genérico)
        therapeutic_variants = [
            f'"{molecule}" cancer WO',
            f'"{molecule}" treatment WO',
            f'"{molecule}" therapy WO',
            f'"{molecule}" pharmaceutical WO',
        ]
        terms.extend(therapeutic_variants)
        
        # 8. BUSCAS COM WOs ENCONTRADOS (feedback loop!)
        if found_wos:
            for wo in list(found_wos)[:5]:  # Top 5 WOs
                terms.append(f'{wo} "{molecule}"')
                terms.append(f'{wo} family')
        
        # 9. BUSCAS COM ASSIGNEES ENCONTRADOS (feedback loop!)
        if found_assignees:
            for assignee in list(found_assignees)[:5]:  # Top 5 assignees
                terms.append(f'{assignee} "{molecule}" WO')
        
        # 10. ANO RANGES (últimos 25 anos)
        year_ranges = [f'"{molecule}" WO{year}' for year in range(2000, 2026, 5)]
        terms.extend(year_ranges)
        
        return terms
    
    async def search_google_patents(
        self,
        molecule: str,
        enriched_data: Dict,
        existing_wos: Set[str],
        state
    ) -> Set[str]:
        """
        Busca DINÂMICA no Google Patents
        """
        logger.info(f"🔍 GOOGLE LAYER: Dynamic search for {molecule}")
        
        new_wos = set()
        search_terms = self._build_dynamic_search_terms(
            molecule,
            enriched_data,
            existing_wos,
            self.found_assignees
        )
        
        logger.info(f"   📊 Generated {len(search_terms)} dynamic search terms")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                
                # Executar buscas (primeiras 40 prioritárias)
                priority_terms = search_terms[:40]
                
                for i, term in enumerate(priority_terms):
                    try:
                        # Google Search
                        url = f"https://www.google.com/search?q={term.replace(' ', '+')}"
                        await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                        
                        await asyncio.sleep(random.uniform(1, 2))
                        
                        # Extrair WOs
                        content = await page.content()
                        wos_found = re.findall(r'WO\d{4}\d{6}', content)
                        
                        for wo in wos_found:
                            if wo not in existing_wos and wo not in new_wos:
                                new_wos.add(wo)
                                logger.info(f"   ✅ New WO: {wo} (via: {term[:60]}...)")
                                
                                # Registrar no state
                                state.add_query_executed("google", term, 1)
                        
                        # Tentar extrair assignees também
                        assignees = re.findall(r'([A-Z][A-Za-z\s&]+(?:Inc|Ltd|Corp|GmbH|SA|AG|AB)\.?)', content)
                        for assignee in assignees[:5]:
                            if len(assignee) > 5 and len(assignee) < 100:
                                self.found_assignees.add(assignee.strip())
                        
                        await asyncio.sleep(random.uniform(2, 4))
                        
                        # Progress
                        if (i + 1) % 10 == 0:
                            logger.info(f"   📊 Progress: {i+1}/{len(priority_terms)} | {len(new_wos)} new WOs | {len(self.found_assignees)} assignees")
                            state.google_status["searches_executed"] = i + 1
                        
                    except PlaywrightTimeout:
                        logger.warning(f"   ⏱️  Timeout: {term[:40]}...")
                        continue
                    except Exception as e:
                        logger.warning(f"   ⚠️  Error: {term[:40]}... - {str(e)[:100]}")
                        continue
                
                # Busca direta Google Patents (complementar)
                try:
                    gp_url = f"https://patents.google.com/?q={molecule}&country=WO&num=100"
                    await page.goto(gp_url, wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(random.uniform(3, 5))
                    
                    content = await page.content()
                    wos_found = re.findall(r'WO\d{4}\d{6}', content)
                    
                    for wo in wos_found:
                        if wo not in existing_wos and wo not in new_wos:
                            new_wos.add(wo)
                            logger.info(f"   ✅ New WO (Google Patents direct): {wo}")
                
                except Exception as e:
                    logger.warning(f"   ⚠️  Google Patents direct error: {str(e)[:100]}")
                
                await browser.close()
        
        except Exception as e:
            logger.error(f"❌ Google crawler error: {str(e)[:200]}")
        
        return new_wos
    
    async def enrich_with_google(
        self,
        molecule: str,
        enriched_data: Dict,
        epo_wos: Set[str],
        state
    ) -> Set[str]:
        """
        Enriquece com Google usando dados dinâmicos
        """
        additional_wos = await self.search_google_patents(
            molecule=molecule,
            enriched_data=enriched_data,
            existing_wos=epo_wos,
            state=state
        )
        
        if additional_wos:
            logger.info(f"🎯 GOOGLE LAYER: Found {len(additional_wos)} NEW WOs!")
            logger.info(f"   📊 Assignees discovered: {len(self.found_assignees)}")
        else:
            logger.info(f"ℹ️  GOOGLE LAYER: No additional WOs found")
        
        # Retornar assignees encontrados também
        state.add_assignees(self.found_assignees)
        
        return additional_wos


# Singleton
google_crawler = GooglePatentsCrawler()
