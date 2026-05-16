"""
Main entrypoint for Tiki crawling framework.

Provides simple CLI-like usage examples.
"""
import argparse
import asyncio
import sys
from core.logger import logger
from pipelines.full_pipeline import full_pipeline
from pipelines.keyword_pipeline import keyword_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description="Tiki Crawling Framework")
    parser.add_argument("--mode", type=str, default="full", help="Pipeline mode: full | keyword")
    parser.add_argument("--headless", action="store_true", help="Run browsers headless")
    parser.add_argument("--keywords", type=str, help="Comma-separated keywords for keyword mode")
    return parser.parse_args()


def main():
    args = parse_args()
    mode = args.mode

    try:
        if mode == "full":
            asyncio.run(full_pipeline(headless=args.headless))
        elif mode == "keyword":
            if not args.keywords:
                logger.error("Provide --keywords for keyword mode")
                sys.exit(1)
            
            keywords = [k.strip() for k in args.keywords.split(",")]
            if not keywords:
                logger.error("No valid keywords provided")
                sys.exit(1)
            
            logger.info(f"Starting keyword pipeline with keywords: {keywords}")
            keyword_pipeline(keywords)
            
        else:
            logger.error(f"Unknown mode: {mode}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
