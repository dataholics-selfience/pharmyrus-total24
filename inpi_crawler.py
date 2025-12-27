"""
INPI Crawler Layer 3 - Brazilian Patent Office v28.4 DEBUG
Busca direta no INPI brasileiro para:
1. Completar abstracts faltantes (português nativo)
2. Descobrir BRs não mapeados via EPO family
3. Metadata em português (título, resumo original)
"""
import asyncio
import re
import os
import logging
from typing import List, Set, Dict, Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import httpx

logger = logging.getLogger("pharmyrus")


class INPICrawler:
    """Crawler para busca direta no INPI brasileiro"""
    
    def __init__(self):
        self.base_url = "https://busca.inpi.gov.br/pePI/jsp/patentes/PatenteSearchBasico.jsp"
        self.found_brs = set()
        
    async def translate_to_portuguese(self, molecule_name: str, groq_api_key: Optional[str] = None) -> str:
        """
        Traduz nome da molécula para português usando Grok X.AI (gratuito)
        Exemplos: Darolutamide → Darolutamida, Ixazomib → Ixazomibe
        """
        logger.info(f"🔄 Grok translation attempt: {molecule_name}")
        
        if not groq_api_key:
            groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not groq_api_key:
            logger.warning(f"⚠️  GROQ_API_KEY not found in env, using original name: {molecule_name}")
            return molecule_name
        
        try:
            logger.info(f"📡 Calling Grok API for: {molecule_name}")
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",  # ✅ CORRIGIDO: Grok X.AI
                    headers={
                        "Authorization": f"Bearer {groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-beta",  # ✅ CORRIGIDO: Grok model
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a pharmaceutical terminology expert. Translate drug molecule names from English to Brazilian Portuguese. Return ONLY the translated name, nothing else. Examples: Darolutamide→Darolutamida, Ixazomib→Ixazomibe, Olaparib→Olaparibe, Trastuzumab→Trastuzumabe"
                            },
                            {
                                "role": "user",
                                "content": f"Translate to Portuguese: {molecule_name}"
                            }
                        ],
                        "temperature": 0,
                        "stream": False  # ✅ BUG FIX: Era "false" (JS), agora é False (Python)
                    }
                )
                
                logger.info(f"📊 Grok response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    translated = data["choices"][0]["message"]["content"].strip()
                    # Limpar possíveis quotes ou markdown
                    translated = translated.replace('"', '').replace("'", "").replace('`', '').strip()
                    logger.info(f"✅ Grok translated: {molecule_name} → {translated}")
                    return translated
                else:
                    logger.error(f"❌ Grok API error {response.status_code}: {response.text[:200]}")
                    return molecule_name
        
        except Exception as e:
            logger.error(f"❌ Grok translation exception: {type(e).__name__}: {e}")
            return molecule_name
    
    async def search_inpi(
        self,
        molecule: str,
        brand: Optional[str] = None,
        dev_codes: List[str] = None,
        known_wos: List[str] = None,
        groq_api_key: Optional[str] = None
    ) -> List[Dict]:
        """
        Busca no INPI usando Playwright
        Retorna lista de BRs encontrados com metadata
        """
        logger.info(f"🇧🇷 Layer 3 INPI: Starting search for {molecule}...")
        logger.info(f"   📊 Input: brand={brand}, dev_codes={len(dev_codes or [])}, known_wos={len(known_wos or [])}")
        
        # Traduzir para português
        logger.info(f"🔄 Step 1/4: Translating molecule name to Portuguese...")
        molecule_pt = await self.translate_to_portuguese(molecule, groq_api_key)
        logger.info(f"   ✅ Translation result: {molecule} → {molecule_pt}")
        
        # Construir termos de busca COMPLETOS
        logger.info(f"🔄 Step 2/4: Building search terms...")
        search_terms = []
        
        # 1. Molécula em português (PRIORITÁRIO)
        search_terms.append(molecule_pt)
        search_terms.append(molecule)  # Fallback EN
        
        # 2. Brand name em português
        if brand:
            logger.info(f"   🔄 Translating brand: {brand}")
            brand_pt = await self.translate_to_portuguese(brand, groq_api_key)
            logger.info(f"   ✅ Brand translation: {brand} → {brand_pt}")
            search_terms.append(brand_pt)
            search_terms.append(brand)
        
        # 3. Dev codes (não precisam tradução)
        if dev_codes:
            logger.info(f"   📝 Adding {len(dev_codes[:5])} dev codes to search")
            search_terms.extend(dev_codes[:5])  # Top 5 dev codes
        
        # 4. WOs conhecidos para mapear BRs
        if known_wos:
            logger.info(f"   📝 Adding {len(known_wos[:10])} WOs for BR mapping")
            # Pegar top 20 WOs mais relevantes (aumentado de 10)
            for wo in known_wos[:20]:
                search_terms.append(wo)
        
        # 5. Variações químicas em português
        chemical_variants_pt = [
            f"{molecule_pt} sal",
            f"{molecule_pt} composto",
            f"{molecule_pt} derivado",
            f"{molecule_pt} farmaceutico",
            f"{molecule_pt} tratamento",
            f"antagonista {molecule_pt}",
            f"inibidor {molecule_pt}"
        ]
        search_terms.extend(chemical_variants_pt)
        
        # 6. Variações em inglês (fallback)
        chemical_variants_en = [
            f"{molecule} salt",
            f"{molecule} compound",
            f"{molecule} pharmaceutical"
        ]
        search_terms.extend(chemical_variants_en)
        
        logger.info(f"   ✅ Generated {len(search_terms)} search terms")
        logger.info(f"   📋 First 10 terms: {search_terms[:10]}")
        
        all_patents = []
        screenshot_taken = False
        
        try:
            logger.info(f"🔄 Step 3/4: Starting Playwright browser...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                logger.info(f"   ✅ Browser launched")
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                logger.info(f"   ✅ Context created")
                
                page = await context.new_page()
                logger.info(f"   ✅ Page created")
                
                # Buscar com os primeiros 20 termos (aumentado de 15)
                total_terms = min(20, len(search_terms))
                logger.info(f"🔄 Step 4/4: Executing {total_terms} INPI searches...")
                
                for i, term in enumerate(search_terms[:total_terms]):
                    try:
                        logger.info(f"   🔍 INPI search {i+1}/{total_terms}: '{term}'")
                        
                        # Ir para página de busca
                        logger.info(f"      → Navigating to INPI search page...")
                        await page.goto(self.base_url, wait_until='domcontentloaded', timeout=30000)
                        logger.info(f"      ✅ Page loaded")
                        
                        await asyncio.sleep(2)
                        
                        # VERIFICAR SE ESTÁ NA ÁREA PÚBLICA OU LOGADA
                        page_title = await page.title()
                        page_url = page.url
                        logger.info(f"      📄 Page title: '{page_title}'")
                        logger.info(f"      🔗 Page URL: {page_url}")
                        
                        # Verificar se há login required
                        login_check = await page.query_selector('input[type="password"], input[name="password"]')
                        if login_check:
                            logger.error(f"      ❌ LOGIN REQUIRED! Page is asking for credentials")
                            logger.error(f"      ⚠️  Cannot access INPI - authentication needed")
                            
                            # Screenshot para debug
                            if not screenshot_taken:
                                screenshot_path = "/tmp/inpi_login_required.png"
                                await page.screenshot(path=screenshot_path)
                                logger.error(f"      📸 Screenshot saved: {screenshot_path}")
                                screenshot_taken = True
                            
                            break  # Parar buscas se login necessário
                        
                        # Preencher campo de busca (ExpressaoPesquisa)
                        logger.info(f"      → Looking for search input field...")
                        search_input = await page.query_selector('input[name="ExpressaoPesquisa"]')
                        if not search_input:
                            logger.warning(f"      ⚠️  'ExpressaoPesquisa' not found, trying generic text input...")
                            search_input = await page.query_selector('input[type="text"]')
                        
                        if search_input:
                            logger.info(f"      ✅ Search input found")
                            logger.info(f"      → Filling search with: '{term}'")
                            await search_input.fill(term)
                            await asyncio.sleep(1)
                            
                            # Click buscar
                            logger.info(f"      → Looking for submit button...")
                            submit_btn = await page.query_selector('input[type="submit"]')
                            if not submit_btn:
                                logger.warning(f"      ⚠️  input[submit] not found, trying button[submit]...")
                                submit_btn = await page.query_selector('button[type="submit"]')
                            
                            if submit_btn:
                                logger.info(f"      ✅ Submit button found")
                                logger.info(f"      → Clicking submit...")
                                await submit_btn.click()
                                
                                logger.info(f"      → Waiting for results to load...")
                                await page.wait_for_load_state('networkidle', timeout=20000)
                                await asyncio.sleep(2)
                                logger.info(f"      ✅ Results page loaded")
                                
                                # Verificar se há resultados
                                page_content = await page.content()
                                if "Nenhum resultado encontrado" in page_content or "No results" in page_content:
                                    logger.info(f"      ⚠️  No results found for '{term}'")
                                else:
                                    logger.info(f"      → Extracting patents from results page...")
                                    
                                    # Extrair resultados
                                    patents = await self._extract_patents_from_page(page)
                                    if patents:
                                        all_patents.extend(patents)
                                        logger.info(f"      ✅ Found {len(patents)} patents for '{term}'")
                                        logger.info(f"      📋 Patent numbers: {[p['patent_number'] for p in patents]}")
                                    else:
                                        logger.warning(f"      ⚠️  Extraction returned 0 patents for '{term}'")
                                        
                                        # Screenshot para debug
                                        if not screenshot_taken and i < 3:  # Apenas primeiras 3 buscas
                                            screenshot_path = f"/tmp/inpi_no_results_{i+1}.png"
                                            await page.screenshot(path=screenshot_path, full_page=True)
                                            logger.info(f"      📸 Screenshot saved: {screenshot_path}")
                                            screenshot_taken = True
                            else:
                                logger.error(f"      ❌ Submit button not found!")
                        else:
                            logger.error(f"      ❌ Search input field not found!")
                        
                        logger.info(f"      → Waiting 3s before next search (rate limiting)...")
                        await asyncio.sleep(3)  # Rate limiting
                    
                    except PlaywrightTimeout as e:
                        logger.error(f"      ⏱️  TIMEOUT searching for: {term} ({e})")
                        continue
                    except Exception as e:
                        logger.error(f"      ❌ ERROR searching '{term}': {type(e).__name__}: {e}")
                        continue
                
                logger.info(f"   → Closing browser...")
                await browser.close()
                logger.info(f"   ✅ Browser closed")
        
        except Exception as e:
            logger.error(f"❌ INPI crawler critical error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
        
        # Deduplicate
        logger.info(f"🔄 Deduplicating results...")
        unique_patents = {}
        for patent in all_patents:
            br_num = patent.get('patent_number')
            if br_num and br_num not in unique_patents:
                unique_patents[br_num] = patent
        
        result = list(unique_patents.values())
        logger.info(f"🎯 Layer 3 INPI FINAL: Found {len(result)} unique BR patents")
        
        if result:
            logger.info(f"   📋 Final BR numbers: {[p['patent_number'] for p in result]}")
        else:
            logger.warning(f"   ⚠️  NO PATENTS FOUND - Check logs above for errors")
        
        return result
    
    async def _extract_patents_from_page(self, page) -> List[Dict]:
        """Extrai patentes da página de resultados INPI"""
        logger.info(f"         → Extracting patents from HTML...")
        
        try:
            patents = await page.evaluate("""
                () => {
                    const results = [];
                    const rows = document.querySelectorAll('table tr');
                    
                    console.log('[INPI Extract] Found ' + rows.length + ' table rows');
                    
                    rows.forEach((row, idx) => {
                        const cells = row.querySelectorAll('td');
                        
                        // Skip header rows
                        if (cells.length >= 3) {
                            const firstCell = cells[0].innerText.trim();
                            
                            console.log('[INPI Extract] Row ' + idx + ': firstCell=' + firstCell);
                            
                            // Skip if header
                            if (firstCell.includes('Pedido') || firstCell.includes('Número')) {
                                console.log('[INPI Extract] Row ' + idx + ': SKIPPED (header)');
                                return;
                            }
                            
                            // Extract BR number
                            const brMatch = firstCell.match(/BR[A-Z0-9]+/);
                            if (brMatch) {
                                const patent = {
                                    patent_number: brMatch[0],
                                    title: cells[1]?.innerText?.trim() || '',
                                    filing_date: cells[2]?.innerText?.trim() || '',
                                    applicants: cells[3]?.innerText?.trim() ? [cells[3].innerText.trim()] : [],
                                    source: 'INPI'
                                };
                                
                                console.log('[INPI Extract] Row ' + idx + ': FOUND BR=' + patent.patent_number);
                                results.push(patent);
                            } else {
                                console.log('[INPI Extract] Row ' + idx + ': NO BR NUMBER FOUND');
                            }
                        }
                    });
                    
                    console.log('[INPI Extract] TOTAL EXTRACTED: ' + results.length + ' patents');
                    return results;
                }
            """)
            
            logger.info(f"         ✅ Extracted {len(patents)} patents from page")
            
            if patents:
                for p in patents:
                    logger.info(f"         📄 {p['patent_number']}: {p.get('title', 'No title')[:60]}")
            else:
                logger.warning(f"         ⚠️  Extraction returned empty list")
            
            return patents
        
        except Exception as e:
            logger.error(f"         ❌ Error extracting patents from page: {type(e).__name__}: {e}")
            return []
    
    async def enrich_br_from_inpi(self, br_number: str) -> Optional[Dict]:
        """
        Enriquece um BR específico com dados do INPI
        Retorna abstract em português, título original, etc
        """
        print(f"   🔍 INPI enriching: {br_number}")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
                page = await browser.new_page()
                
                # Buscar BR específico
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                # Preencher com número BR
                search_input = await page.query_selector('input[name="ExpressaoPesquisa"]')
                if search_input:
                    await search_input.fill(br_number)
                    await asyncio.sleep(1)
                    
                    submit_btn = await page.query_selector('input[type="submit"]')
                    if submit_btn:
                        await submit_btn.click()
                        await page.wait_for_load_state('networkidle', timeout=20000)
                        await asyncio.sleep(2)
                        
                        # Click no BR para ver detalhes
                        link = await page.query_selector(f'a:has-text("{br_number}")')
                        if link:
                            await link.click()
                            await page.wait_for_load_state('networkidle', timeout=20000)
                            await asyncio.sleep(2)
                            
                            # Extrair metadata da página de detalhes
                            metadata = await page.evaluate("""
                                () => {
                                    const data = {
                                        title_pt: '',
                                        abstract_pt: '',
                                        applicants: [],
                                        inventors: [],
                                        ipc_codes: []
                                    };
                                    
                                    // Procurar título
                                    const titleElem = document.querySelector('td:has-text("Título"), th:has-text("Título")');
                                    if (titleElem && titleElem.nextElementSibling) {
                                        data.title_pt = titleElem.nextElementSibling.innerText.trim();
                                    }
                                    
                                    // Procurar resumo
                                    const abstractElem = document.querySelector('td:has-text("Resumo"), th:has-text("Resumo")');
                                    if (abstractElem && abstractElem.nextElementSibling) {
                                        data.abstract_pt = abstractElem.nextElementSibling.innerText.trim();
                                    }
                                    
                                    // Procurar depositante
                                    const applicantElem = document.querySelector('td:has-text("Depositante"), th:has-text("Depositante")');
                                    if (applicantElem && applicantElem.nextElementSibling) {
                                        const apps = applicantElem.nextElementSibling.innerText.trim();
                                        data.applicants = apps.split(';').map(a => a.trim()).filter(a => a);
                                    }
                                    
                                    return data;
                                }
                            """)
                            
                            await browser.close()
                            
                            if metadata.get('title_pt') or metadata.get('abstract_pt'):
                                print(f"   ✅ INPI enriched {br_number}")
                                return metadata
                
                await browser.close()
        
        except Exception as e:
            print(f"   ⚠️  INPI enrichment error for {br_number}: {e}")
        
        return None


# Instance singleton
inpi_crawler = INPICrawler()
