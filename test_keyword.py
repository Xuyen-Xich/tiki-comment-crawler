#!/usr/bin/env python
"""Quick test script to identify issues."""
import sys
import traceback

try:
    print("Testing imports...")
    from core.logger import logger
    print("✓ Logger imported")
    
    from crawlers import KeywordCrawler, CommentCrawler
    print("✓ Crawlers imported")
    
    from services import RankingService, ProductService, CommentService
    print("✓ Services imported")
    
    from config.settings import settings
    print("✓ Settings imported")
    
    print("\nTesting keyword crawler...")
    keywords = ["bách hóa online"]
    
    with KeywordCrawler(max_products=settings.KEYWORD_MAX_PRODUCTS) as k_crawler:
        products = k_crawler.search_keywords(keywords)
    
    print(f"✓ Found {len(products)} products")
    if products:
        print(f"  Sample product: {products[0].product_name}")
    
    print("\nTesting product deduplication...")
    products = ProductService.deduplicate_products(products)
    print(f"✓ After dedup: {len(products)} products")
    
    print("\nTesting ranking service...")
    ranker = RankingService()
    top_products = ranker.get_top_n(products, 50)
    print(f"✓ Top products: {len(top_products)}")
    
    print("\nTesting comment crawler...")
    if top_products:
        with CommentCrawler() as comment_crawler:
            comments = comment_crawler.crawl_products([p.dict() for p in top_products])
        print(f"✓ Crawled {len(comments)} comments")
    else:
        print("⚠ No top products to crawl comments for")
    
    print("\n✓ All tests passed!")
    
except Exception as e:
    print(f"\n✗ Error occurred:")
    print(f"  {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)
