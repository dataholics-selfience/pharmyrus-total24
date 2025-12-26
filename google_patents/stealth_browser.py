"""
Stealth browser using Playwright with anti-detection.
"""
import asyncio
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async

from config.settings import (
    USER_AGENT,
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
    TIMEOUT
)


class StealthBrowser:
    """Browser with stealth configuration and human-like behavior."""
    
    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def setup(self):
        """Initialize Playwright browser with stealth."""
        self.playwright = await async_playwright().start()
        
        # Browser arguments for stealth
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-gpu'
        ]
        
        # Launch options
        launch_options = {
            'headless': True,
            'args': browser_args
        }
        
        # Add proxy if provided
        if self.proxy_url:
            launch_options['proxy'] = {'server': self.proxy_url}
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT},
            user_agent=USER_AGENT,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=[],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        return self.context
    
    async def new_page(self) -> Page:
        """Create new page with stealth applied."""
        if not self.context:
            await self.setup()
        
        page = await self.context.new_page()
        
        # Apply stealth
        await stealth_async(page)
        
        # Set default timeout
        page.set_default_timeout(TIMEOUT * 1000)
        
        return page
    
    async def human_delay(
        self, 
        min_sec: float = 12.0, 
        max_sec: float = 20.0
    ) -> None:
        """Wait with human-like randomization."""
        base_delay = random.uniform(min_sec, max_sec)
        jitter = random.uniform(-2.0, 3.0)
        final_delay = max(1.0, base_delay + jitter)
        
        await asyncio.sleep(final_delay)
    
    async def scroll_page(self, page: Page) -> None:
        """Simulate human scrolling behavior."""
        # Scroll down in increments
        for _ in range(random.randint(2, 4)):
            await page.evaluate("window.scrollBy(0, window.innerHeight / 2)")
            await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # Small chance to scroll back up
        if random.random() < 0.3:
            await page.evaluate("window.scrollBy(0, -window.innerHeight / 3)")
            await asyncio.sleep(random.uniform(0.2, 0.5))
    
    async def close(self):
        """Close browser and clean up."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
