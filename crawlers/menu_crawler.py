"""
Menu/Category crawler using Playwright.

Crawls Tiki category hierarchy (3 levels) with deduplication and filtering.
"""
import asyncio
import re
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urljoin
from tqdm import tqdm
from core.logger import logger
from core.browser import PlaywrightBrowser
from models import CategoryModel
from config.settings import settings
from config.constants import (
    MENU_LEVEL_1_XPATH,
    MENU_LEVEL_2_3_XPATH,
    CATEGORY_MIN_NAME_LENGTH,
    CATEGORY_MAX_NAME_LENGTH,
    CATEGORY_REQUIRED_PATH_SEGMENT,
    CATEGORY_EXCLUDE_PARAMS,
    CATEGORY_LOAD_DELAY,
    SUBCATEGORY_LOAD_DELAY,
)


class MenuCrawler:
    """Crawls Tiki category hierarchy with Playwright."""

    def __init__(self, headless: bool = settings.BROWSER_HEADLESS):
        """
        Initialize menu crawler.
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.browser: Optional[PlaywrightBrowser] = None
        self.categories: List[CategoryModel] = []
        self.global_seen: Set[Tuple[str, str, str]] = set()

    async def initialize(self) -> None:
        """Initialize browser."""
        self.browser = PlaywrightBrowser()
        await self.browser.launch(headless=self.headless)
        logger.info("Menu crawler initialized")

    async def close(self) -> None:
        """Close browser."""
        if self.browser:
            await self.browser.close()
        logger.info("Menu crawler closed")

    @staticmethod
    def _is_valid_category_name(name: str) -> bool:
        """
        Validate category name.
        
        Args:
            name: Category name
            
        Returns:
            True if valid, False otherwise
        """
        if not name:
            return False
        
        if len(name) < CATEGORY_MIN_NAME_LENGTH or len(name) > CATEGORY_MAX_NAME_LENGTH:
            return False
        
        return True

    @staticmethod
    def _is_valid_category_url(url: str) -> bool:
        """
        Validate category URL.
        
        Args:
            url: Category URL
            
        Returns:
            True if valid, False otherwise
        """
        if not url:
            return False
        
        # Must contain /c path segment
        if CATEGORY_REQUIRED_PATH_SEGMENT not in url:
            return False
        
        # Exclude tracking links
        for param in CATEGORY_EXCLUDE_PARAMS:
            if param in url:
                return False
        
        return True

    async def crawl_level_1(self) -> List[Dict[str, str]]:
        """
        Crawl level 1 categories.
        
        Returns:
            List of level 1 category data
        """
        logger.info("Starting level 1 category crawl")
        
        context = await self.browser.create_context()
        page = await self.browser.create_page(context)
        
        try:
            # Navigate to Tiki home
            await self.browser.goto_with_retry(
                page,
                settings.TIKI_MENU_URL,
                wait_until="networkidle",
            )
            
            await page.wait_for_timeout(CATEGORY_LOAD_DELAY * 1000)
            
            # Extract level 1 categories
            lv1_elements = await page.locator(MENU_LEVEL_1_XPATH).all()
            logger.info(f"Found {len(lv1_elements)} level 1 categories")
            
            level_1_data = []
            lv1_visited: Set[str] = set()
            
            for element in tqdm(lv1_elements, desc="L1 Categories"):
                try:
                    name = (await element.text_content()).strip()
                    url = await element.get_attribute("href")
                    
                    # Validation
                    if not self._is_valid_category_name(name):
                        continue
                    
                    if not self._is_valid_category_url(url):
                        continue
                    
                    if url in lv1_visited:
                        continue
                    
                    lv1_visited.add(url)
                    level_1_data.append({
                        "lv1_name": name,
                        "lv1_url": url,
                    })
                    
                    logger.debug(f"L1: {name}")
                
                except Exception as e:
                    logger.warning(f"Error extracting level 1 category: {e}")
                    continue
            
            logger.info(f"Crawled {len(level_1_data)} level 1 categories")
            return level_1_data
        
        finally:
            await page.close()
            await context.close()

    async def crawl_level_2_3(self, level_1_data: List[Dict[str, str]]) -> None:
        """
        Crawl level 2 and 3 categories.
        
        Args:
            level_1_data: Level 1 category data
        """
        logger.info(f"Starting level 2/3 crawl for {len(level_1_data)} categories")
        
        for lv1_idx, lv1_row in enumerate(tqdm(level_1_data, desc="L1 Processing")):
            context = await self.browser.create_context()
            page = await self.browser.create_page(context)
            
            try:
                lv1_name = lv1_row["lv1_name"]
                lv1_url = lv1_row["lv1_url"]
                
                # Add level 1 as standalone category
                self._add_category(
                    lv1_name, lv1_url,
                    None, None,
                    None, None,
                )
                
                # Navigate to level 1 page
                success = await self.browser.goto_with_retry(
                    page,
                    lv1_url,
                    wait_until="networkidle",
                )
                
                if not success:
                    logger.warning(f"Failed to load {lv1_url}")
                    continue
                
                await page.wait_for_timeout(SUBCATEGORY_LOAD_DELAY * 1000)
                
                # Extract level 2 categories
                lv2_elements = await page.locator(MENU_LEVEL_2_3_XPATH).all()
                logger.debug(f"L1:{lv1_name} - Found {len(lv2_elements)} raw L2 items")
                
                lv2_visited: Set[str] = set()
                
                for lv2_element in lv2_elements:
                    try:
                        lv2_name = (await lv2_element.text_content()).strip()
                        lv2_url = await lv2_element.get_attribute("href")
                        
                        # Filter level 2
                        if not self._is_valid_category_name(lv2_name):
                            continue
                        
                        if not self._is_valid_category_url(lv2_url):
                            continue
                        
                        if lv2_url == lv1_url:
                            continue
                        
                        if lv2_url in lv2_visited:
                            continue
                        
                        if lv2_name == lv1_name:
                            continue
                        
                        lv2_visited.add(lv2_url)
                        
                        # Add level 2 category
                        self._add_category(
                            lv1_name, lv1_url,
                            lv2_name, lv2_url,
                            None, None,
                        )
                        
                        # Crawl level 3
                        await self._crawl_level_3(
                            page,
                            lv1_name, lv1_url,
                            lv2_name, lv2_url,
                        )
                    
                    except Exception as e:
                        logger.warning(f"Error processing L2 category: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"Error crawling {lv1_name}: {e}")
            
            finally:
                await page.close()
                await context.close()

    async def _crawl_level_3(
        self,
        parent_page,
        lv1_name: str,
        lv1_url: str,
        lv2_name: str,
        lv2_url: str,
    ) -> None:
        """
        Crawl level 3 categories for a given level 2.
        
        Args:
            parent_page: Parent page instance
            lv1_name: Level 1 name
            lv1_url: Level 1 URL
            lv2_name: Level 2 name
            lv2_url: Level 2 URL
        """
        # Create new page for level 3
        context = await self.browser.create_context()
        page = await self.browser.create_page(context)
        
        try:
            success = await self.browser.goto_with_retry(
                page,
                lv2_url,
                wait_until="networkidle",
            )
            
            if not success:
                logger.warning(f"Failed to load {lv2_url}")
                return
            
            await page.wait_for_timeout(SUBCATEGORY_LOAD_DELAY * 1000)
            
            # Extract level 3 categories
            lv3_elements = await page.locator(MENU_LEVEL_2_3_XPATH).all()
            logger.debug(f"L2:{lv2_name} - Found {len(lv3_elements)} raw L3 items")
            
            lv3_visited: Set[str] = set()
            
            for lv3_element in lv3_elements:
                try:
                    lv3_name = (await lv3_element.text_content()).strip()
                    lv3_url = await lv3_element.get_attribute("href")
                    
                    # Filter level 3
                    if not self._is_valid_category_name(lv3_name):
                        continue
                    
                    if not self._is_valid_category_url(lv3_url):
                        continue
                    
                    if lv3_url == lv2_url or lv3_url == lv1_url:
                        continue
                    
                    if lv3_name == lv2_name or lv3_name == lv1_name:
                        continue
                    
                    if lv3_url in lv3_visited:
                        continue
                    
                    lv3_visited.add(lv3_url)
                    
                    # Add level 3 category
                    self._add_category(
                        lv1_name, lv1_url,
                        lv2_name, lv2_url,
                        lv3_name, lv3_url,
                    )
                
                except Exception as e:
                    logger.warning(f"Error processing L3 category: {e}")
                    continue
        
        finally:
            await page.close()
            await context.close()

    def _add_category(
        self,
        lv1_name: str,
        lv1_url: str,
        lv2_name: Optional[str],
        lv2_url: Optional[str],
        lv3_name: Optional[str],
        lv3_url: Optional[str],
    ) -> None:
        """Add category with deduplication."""
        key = (lv1_name, lv2_name or "", lv3_name or "")
        
        if key in self.global_seen:
            return
        
        self.global_seen.add(key)
        
        # Extract category ID from the active URL
        category_url = lv3_url or lv2_url or lv1_url
        category_id = self._extract_category_id(category_url)
        
        category = CategoryModel(
            lv1_name=lv1_name,
            lv1_url=lv1_url,
            lv2_name=lv2_name,
            lv2_url=lv2_url,
            lv3_name=lv3_name,
            lv3_url=lv3_url,
            category_id=category_id,
            category_url=category_url,
        )
        
        self.categories.append(category)

    @staticmethod
    def _extract_category_id(url: str) -> Optional[str]:
        """
        Extract category ID from URL.
        
        Args:
            url: Category URL
            
        Returns:
            Category ID or None
        """
        try:
            match = re.search(r"/c(\d+)", url)
            if match:
                return match.group(1)
        except Exception as e:
            logger.warning(f"Error extracting category ID from {url}: {e}")
        
        return None

    async def crawl(self) -> List[CategoryModel]:
        """
        Execute full menu crawl.
        
        Returns:
            List of crawled categories
        """
        try:
            await self.initialize()
            
            # Level 1
            level_1_data = await self.crawl_level_1()
            
            # Level 2 + 3
            await self.crawl_level_2_3(level_1_data)
            
            logger.info(f"Menu crawl completed. Total categories: {len(self.categories)}")
            return self.categories
        
        finally:
            await self.close()


async def run_menu_crawler(headless: bool = settings.BROWSER_HEADLESS) -> List[CategoryModel]:
    """
    Convenience function to run menu crawler.
    
    Args:
        headless: Run in headless mode
        
    Returns:
        List of categories
    """
    crawler = MenuCrawler(headless=headless)
    return await crawler.crawl()


# Example usage
if __name__ == "__main__":
    categories = asyncio.run(run_menu_crawler(headless=False))
    logger.info(f"Total categories crawled: {len(categories)}")
    for cat in categories[:5]:
        logger.info(cat.dict())
