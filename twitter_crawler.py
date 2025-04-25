import asyncio
from crawl4ai import AsyncWebCrawler
import json
from datetime import datetime
import time
import logging
from twitter_urls import TWITTER_URLS
from nitter_parser import parse_nitter_content

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitter_crawler.log'),
        logging.StreamHandler()
    ]
)

async def get_nitter_url(url):
    """Convert X URL to Nitter URL for better accessibility"""
    return url.replace('x.com', 'nitter.net')

async def crawl_profile(crawler, url):
    try:
        logging.info(f"Starting to crawl: {url}")
        nitter_url = await get_nitter_url(url)
        
        result = await crawler.arun(
            url=nitter_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
        )
        
        if not result.markdown:
            raise Exception("No content retrieved")
        
        # Parse the content immediately
        try:
            profile = parse_nitter_content(result.markdown)
            parsed_data = {
                'username': profile.username,
                'display_name': profile.display_name,
                'bio': profile.bio,
                'tweets': [
                    {
                        'text': tweet.text,
                        'time': tweet.time,
                        'likes': tweet.likes,
                        'retweets': tweet.retweets
                    }
                    for tweet in profile.tweets
                ]
            }
            logging.info(f"Successfully parsed profile for {url}: found {len(profile.tweets)} tweets")
        except Exception as e:
            logging.error(f"Error parsing content for {url}: {str(e)}")
            parsed_data = None
            
        logging.info(f"Successfully crawled: {url}")
        return {
            'url': url,
            'nitter_url': nitter_url,
            'timestamp': datetime.now().isoformat(),
            'parsed_data': parsed_data,
            'success': True
        }
    except Exception as e:
        logging.error(f"Error crawling {url}: {str(e)}")
        return {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'success': False
        }

async def main():
    results = []
    failed_urls = []
    
    async with AsyncWebCrawler() as crawler:
        for i, url in enumerate(TWITTER_URLS):
            logging.info(f"Processing {url} ({i+1}/{len(TWITTER_URLS)})")
            
            # Add delay between requests to avoid rate limiting
            if i > 0:
                await asyncio.sleep(3)  # Increased delay to 3 seconds
            
            result = await crawl_profile(crawler, url)
            results.append(result)
            
            if not result['success']:
                failed_urls.append(url)
            elif result['parsed_data']:
                # Print preview of parsed data
                profile = result['parsed_data']
                print(f"\nProcessed {url}")
                print(f"Username: {profile['username']}")
                if profile['tweets']:
                    print(f"Latest tweet: {profile['tweets'][0]['text'][:100]}...")
                print(f"Found {len(profile['tweets'])} tweets")
            
            # Save results periodically
            if (i + 1) % 5 == 0:  # Save more frequently
                timestamp = int(time.time())
                with open(f'twitter_results_{timestamp}.json', 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                logging.info(f"Saved intermediate results to twitter_results_{timestamp}.json")
    
    # Save final results
    timestamp = int(time.time())
    with open(f'twitter_results_final_{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Save failed URLs separately
    if failed_urls:
        with open(f'failed_urls_{timestamp}.txt', 'w', encoding='utf-8') as f:
            for url in failed_urls:
                f.write(f"{url}\n")
        logging.warning(f"Failed to crawl {len(failed_urls)} URLs. See failed_urls_{timestamp}.txt for details")
    
    logging.info("Crawling completed!")
    logging.info(f"Successfully crawled: {len(results) - len(failed_urls)} URLs")
    logging.info(f"Failed to crawl: {len(failed_urls)} URLs")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Crawling interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}") 