#!/usr/bin/env python3
"""
AI News Aggregator - Health Check Script
Checks the health of all scrapers and reports their status

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --json  # JSON output
"""

import argparse
import asyncio
import sys
from typing import Dict, List

from src.scrapers import ScraperRegistry


async def check_scraper(name: str) -> Dict:
    """Check a single scraper"""
    scraper = ScraperRegistry.get_scraper(name)
    if not scraper:
        return {
            "name": name,
            "status": "ERROR",
            "message": "No scraper found",
            "articles": 0
        }
    
    try:
        result = await scraper.scrape()
        
        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for a in result.articles:
            if a.url and a.url not in seen_urls:
                seen_urls.add(a.url)
                unique_articles.append(a)
        
        if result.success and len(unique_articles) > 0:
            return {
                "name": name,
                "status": "OK",
                "message": None,
                "articles": len(unique_articles),
                "total_fetched": len(result.articles),
                "error": result.error
            }
        else:
            return {
                "name": name,
                "status": "FAIL",
                "message": result.error or "No articles found",
                "articles": 0,
                "total_fetched": len(result.articles),
                "error": result.error
            }
    except Exception as e:
        return {
            "name": name,
            "status": "ERROR",
            "message": str(e),
            "articles": 0
        }


async def check_all_scrapers() -> List[Dict]:
    """Check all registered scrapers"""
    scrapers = ScraperRegistry.list_scrapers()
    results = []
    
    for name in scrapers:
        result = await check_scraper(name)
        results.append(result)
        # Small delay between checks
        await asyncio.sleep(0.5)
    
    return results


def print_table(results: List[Dict]):
    """Print results as ASCII table"""
    print("\n" + "=" * 70)
    print("  AI News Aggregator - Scraper Health Check")
    print("=" * 70 + "\n")
    
    print(f"{'Source':<20} {'Status':<10} {'Articles':<15} {'Issue':<25}")
    print("-" * 70)
    
    ok_count = 0
    fail_count = 0
    
    for r in sorted(results, key=lambda x: (x["status"] != "OK", x["name"])):
        status = r["status"]
        articles = r.get("articles", 0)
        message = r.get("message", "") or ""
        
        if status == "OK":
            status_display = "✅ OK"
            ok_count += 1
            issue = ""
        elif status == "FAIL":
            status_display = "❌ FAIL"
            fail_count += 1
            issue = message[:23] if message else "No articles"
        else:
            status_display = "⚠️ ERROR"
            fail_count += 1
            issue = message[:23] if message else "Unknown"
        
        articles_display = str(articles) if status == "OK" else "-"
        
        print(f"{r['name']:<20} {status_display:<10} {articles_display:<15} {issue:<25}")
    
    print("-" * 70)
    print(f"Summary: {ok_count} OK, {fail_count} FAILED out of {len(results)} scrapers")
    print("=" * 70 + "\n")


def print_json(results: List[Dict]):
    """Print results as JSON"""
    import json
    
    output = {
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r["status"] == "OK"),
            "failed": sum(1 for r in results if r["status"] != "OK")
        },
        "scrapers": results
    }
    
    print(json.dumps(output, indent=2))


async def main():
    parser = argparse.ArgumentParser(description="Health check for AI News scrapers")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    results = await check_all_scrapers()
    
    if args.json:
        print_json(results)
    else:
        print_table(results)
    
    # Return exit code based on results
    failed = sum(1 for r in results if r["status"] != "OK")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())