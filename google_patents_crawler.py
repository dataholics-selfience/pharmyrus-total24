"""
Google Patents Crawler Layer 2
Descobre WOs adicionais que o EPO pode ter perdido
Usa Playwright + stealth + proxies premium
"""
import asyncio
import re
import random
from typing import List, Set, Dict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


# Proxies premium (das chaves fornecidas)
PROXIES = [
    "http://brd-customer-hl_8ea11d75-zone-residential_proxy1:w7qs41l7ijfc@brd.superproxy.io:33335",
    "http://brd-customer-hl_8ea11d75-zone-datacenter_proxy1:93u1xg5fef4p@brd.superproxy.io:33335",
    "http://5SHQXNTHNKDHUHFD:wifi;us;;;@proxy.scraping bee.com:8886",
    "http://XNK2KLGACMN0FKRY:wifi;us;;;@proxy.scrapingbee.com:8886",
]


class GooglePatentsCrawler:
    """Crawler Layer 2 para descobrir WOs via Google Patents"""
    
    def __init__(self):
        self.found_wos = set()
        self.proxy_index = 0
    
    def _get_next_proxy(self) -> str:
        """Rotaciona proxies"""
        proxy = PROXIES[self.proxy_index % len(PROXIES)]
        self.proxy_index += 1
        return proxy
    
    async def search_google_patents(
        self,
        molecule: str,
        dev_codes: List[str],
        existing_wos: Set[str]
    ) -> Set[str]:
        """
        Busca WOs no Google Patents que não foram encontrados pelo EPO
        
        Estratégias:
        1. Busca Google Search por WO patents
        2. Busca direta no Google Patents
        3. Busca por dev codes + patent
        """
        print(f"🔍 Layer 2: Buscando WOs no Google Patents para {molecule}...")
        
        new_wos = set()
        
        try:
            async with async_playwright() as p:
                # Launch browser com stealth
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
                
                # Estratégia 1: Google Search para patents
                search_terms = [
                    f'"{molecule}" patent WO site:patents.google.com',
                    f'"{molecule}" WO20',
                ]
                
                # Adicionar dev codes
                for code in dev_codes[:3]:
                    search_terms.append(f'"{code}" patent WO site:patents.google.com')
                
                for term in search_terms:
                    try:
                        url = f"https://www.google.com/search?q={term.replace(' ', '+')}"
                        await page.goto(url, wait_until='networkidle', timeout=30000)
                        
                        # Esperar um pouco
                        await asyncio.sleep(random.uniform(2, 4))
                        
                        # Extrair WOs da página
                        content = await page.content()
                        wos_found = re.findall(r'WO\d{4}\d{6}', content)
                        
                        for wo in wos_found:
                            if wo not in existing_wos:
                                new_wos.add(wo)
                                print(f"   ✅ Novo WO encontrado: {wo}")
                        
                        # Delay entre buscas
                        await asyncio.sleep(random.uniform(3, 6))
                        
                    except PlaywrightTimeout:
                        print(f"   ⏱️  Timeout na busca: {term}")
                        continue
                    except Exception as e:
                        print(f"   ⚠️  Erro na busca '{term}': {e}")
                        continue
                
                # Estratégia 2: Busca direta Google Patents
                try:
                    gp_url = f"https://patents.google.com/?q={molecule}&country=WO"
                    await page.goto(gp_url, wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(random.uniform(3, 5))
                    
                    content = await page.content()
                    wos_found = re.findall(r'WO\d{4}\d{6}', content)
                    
                    for wo in wos_found:
                        if wo not in existing_wos:
                            new_wos.add(wo)
                            print(f"   ✅ Novo WO (Google Patents): {wo}")
                
                except Exception as e:
                    print(f"   ⚠️  Erro Google Patents direct: {e}")
                
                await browser.close()
        
        except Exception as e:
            print(f"❌ Erro no crawler Google Patents: {e}")
        
        return new_wos
    
    async def enrich_with_google(
        self,
        molecule: str,
        dev_codes: List[str],
        epo_wos: Set[str]
    ) -> Set[str]:
        """
        Enriquece WOs do EPO com buscas no Google Patents
        
        Args:
            molecule: Nome da molécula
            dev_codes: Development codes do PubChem
            epo_wos: WOs já encontrados pelo EPO
        
        Returns:
            Set de WOs adicionais encontrados no Google
        """
        additional_wos = await self.search_google_patents(
            molecule=molecule,
            dev_codes=dev_codes,
            existing_wos=epo_wos
        )
        
        if additional_wos:
            print(f"🎯 Layer 2: Encontrou {len(additional_wos)} WOs NOVOS no Google Patents!")
        else:
            print(f"ℹ️  Layer 2: Nenhum WO adicional encontrado no Google Patents")
        
        return additional_wos


# Instance singleton
google_crawler = GooglePatentsCrawler()
