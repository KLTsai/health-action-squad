"""Test script to validate all Verified Sources URLs.

This script:
1. Extracts all URLs from planner_prompt.txt
2. Tests each URL for accessibility (HTTP status)
3. Reports any broken or inaccessible links

Run this periodically to ensure sources remain valid.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    
    # Retry strategy: 3 retries with backoff
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set user agent to avoid being blocked
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    return session


def extract_urls_from_prompt(prompt_path: Path) -> List[str]:
    """Extract all URLs from the planner prompt file.
    
    Args:
        prompt_path: Path to planner_prompt.txt
        
    Returns:
        List of extracted URLs
    """
    content = prompt_path.read_text(encoding='utf-8')
    
    # Extract URLs in backticks (format: `https://...`)
    urls = re.findall(r'`(https?://[^`]+)`', content)
    
    return urls


def test_url(session: requests.Session, url: str) -> Tuple[str, int, str]:
    """Test if a URL is accessible.
    
    Args:
        session: Requests session
        url: URL to test
        
    Returns:
        Tuple of (url, status_code, status_message)
    """
    try:
        # Use HEAD request for faster checking
        response = session.head(url, timeout=10, allow_redirects=True)
        
        if response.status_code == 405:  # Method Not Allowed, try GET
            response = session.get(url, timeout=10, allow_redirects=True)
        
        status_code = response.status_code
        
        if status_code == 200:
            status_msg = "✅ OK"
        elif 300 <= status_code < 400:
            status_msg = f"⚠️ Redirect ({status_code})"
        elif status_code == 403:
            status_msg = "❌ Forbidden (403)"
        elif status_code == 404:
            status_msg = "❌ Not Found (404)"
        else:
            status_msg = f"⚠️ Status {status_code}"
            
        return (url, status_code, status_msg)
        
    except requests.exceptions.Timeout:
        return (url, 0, "❌ Timeout")
    except requests.exceptions.ConnectionError:
        return (url, 0, "❌ Connection Error")
    except requests.exceptions.RequestException as e:
        return (url, 0, f"❌ Error: {str(e)[:50]}")


def main():
    """Main test function."""
    # Locate planner_prompt.txt
    project_root = Path(__file__).parent.parent
    prompt_path = project_root / "resources" / "prompts" / "planner_prompt.txt"
    
    if not prompt_path.exists():
        print(f"❌ Error: Could not find {prompt_path}")
        sys.exit(1)
    
    print("🔍 Extracting URLs from planner_prompt.txt...")
    urls = extract_urls_from_prompt(prompt_path)
    print(f"   Found {len(urls)} URLs to test\n")
    
    # Create session with retry logic
    session = create_session()
    
    # Test each URL
    results = []
    failed_urls = []
    
    print("🧪 Testing URLs...\n")
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Testing {url[:60]}...")
        result = test_url(session, url)
        results.append(result)
        
        url, status_code, status_msg = result
        print(f"        {status_msg}")
        
        if status_code == 0 or status_code >= 400:
            failed_urls.append(result)
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    success_count = len([r for r in results if 200 <= r[1] < 400])
    print(f"\n✅ Successful: {success_count}/{len(urls)}")
    print(f"❌ Failed: {len(failed_urls)}/{len(urls)}")
    
    if failed_urls:
        print("\n⚠️ FAILED URLs:")
        print("-" * 80)
        for url, status_code, status_msg in failed_urls:
            print(f"\n{status_msg}")
            print(f"  {url}")
        
        print("\n" + "="*80)
        print("❌ Some URLs are not accessible. Please review and update.")
        sys.exit(1)
    else:
        print("\n" + "="*80)
        print("✅ All URLs are accessible!")
        sys.exit(0)


if __name__ == "__main__":
    main()
