import asyncio
from playwright.async_api import async_playwright, TimeoutError
import json
from datetime import datetime
import logging
import random
import os
from twitter_urls import TWITTER_URLS

# Transform Twitter URLs to Nitter URLs
NITTER_URLS = [url.replace('twitter.com', 'nitter.net').replace('x.com', 'nitter.net') for url in TWITTER_URLS]

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class NitterCrawler:
    def __init__(self):
        self.context = None
        self.page = None
    
    async def random_delay(self, min_seconds=1, max_seconds=3):
        """Random delay to simulate human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def wait_for_page_load(self):
        """Wait for the page to be fully loaded"""
        try:
            # First check if we're being challenged
            content = await self.page.content()
            if "challenge" in content.lower() or "cloudflare" in content.lower():
                logging.info("Detected Cloudflare challenge, waiting for it to resolve...")
                await asyncio.sleep(15)  # Wait for challenge to resolve
            
            # Wait for network to be idle
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            # Wait for DOM to be ready
            await self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            # Wait for JavaScript to be ready
            await self.page.wait_for_load_state('load', timeout=30000)
            
            # Additional wait for dynamic content
            await asyncio.sleep(5)
            
            # Check if page is actually loaded
            content = await self.page.content()
            if len(content) < 100:  # If content is too short
                logging.warning("Page content seems too short, waiting longer...")
                await asyncio.sleep(10)  # Wait longer
                
                # Try to evaluate JavaScript to check if page is loaded
                is_loaded = await self.page.evaluate('''() => {
                    return document.readyState === 'complete' && 
                           document.body && 
                           document.body.innerHTML.length > 0;
                }''')
                
                if not is_loaded:
                    # Try to reload the page
                    logging.info("Attempting to reload the page...")
                    await self.page.reload(wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(5)
                    
                    # Check again after reload
                    content = await self.page.content()
                    if len(content) < 100:
                        raise Exception("Page failed to load properly even after reload")
                
        except Exception as e:
            logging.warning(f"Page load warning: {str(e)}")
            raise  # Re-raise the exception to handle it in the calling function

    async def crawl_profile(self, url):
        """Crawl a specific profile from nitter.net"""
        max_retries = 3
        for retry in range(max_retries):
            try:
                logging.info(f"Starting to crawl: {url} (Attempt {retry + 1}/{max_retries})")
                
                # Visit the page
                try:
                    logging.info(f"Attempting to navigate to: {url}")
                    response = await self.page.goto(url, wait_until='networkidle', timeout=30000)
                    logging.info(f"Page response status: {response.status if response else 'No response'}")
                    
                    await self.random_delay(3, 5)
                    await self.wait_for_page_load()
                    
                    # Check if we're blocked or redirected
                    current_url = self.page.url
                    if 'nitter.net' not in current_url:
                        raise Exception(f"Redirected to unexpected URL: {current_url}")
                    
                except Exception as e:
                    logging.error(f"Page navigation error: {str(e)}")
                    return {
                        'url': url,
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e),
                        'success': False
                    }
                
                # Extract profile data
                try:
                    # Get username
                    username_element = await self.page.query_selector('.profile-card-username')
                    username = await username_element.inner_text() if username_element else ""
                    
                    # Get tweets
                    tweets = []
                    tweet_elements = await self.page.query_selector_all('.timeline-item')
                    
                    if not tweet_elements:
                        logging.warning("No tweets found on the page")
                    
                    for tweet in tweet_elements[:4]:  # Get first 4 tweets
                        try:
                            # Check if it's a retweet
                            retweet_header = await tweet.query_selector('.retweet-header')
                            if retweet_header:
                                logging.info("Skipping retweet")
                                continue
                            
                            # Get tweet link
                            tweet_link = await tweet.query_selector('.tweet-link')
                            tweet_url = await tweet_link.get_attribute('href') if tweet_link else ""
                            if tweet_url:
                                tweet_url = f"https://nitter.net{tweet_url}"
                            
                            # Get tweet content
                            tweet_content = await tweet.query_selector('.tweet-content')
                            text = await tweet_content.inner_text() if tweet_content else ""
                            
                            # Get tweet time
                            time_element = await tweet.query_selector('.tweet-date a')
                            timestamp = await time_element.get_attribute('title') if time_element else ""
                            
                            # Get tweet stats
                            metrics = {}
                            stats_container = await tweet.query_selector('.tweet-stats')
                            if stats_container:
                                # Get replies
                                reply_stat = await stats_container.query_selector('.tweet-stat:has(.icon-comment)')
                                if reply_stat:
                                    reply_text = await reply_stat.inner_text()
                                    metrics['reply'] = int(''.join(filter(str.isdigit, reply_text))) if reply_text else 0
                                
                                # Get retweets
                                retweet_stat = await stats_container.query_selector('.tweet-stat:has(.icon-retweet)')
                                if retweet_stat:
                                    retweet_text = await retweet_stat.inner_text()
                                    metrics['retweet'] = int(''.join(filter(str.isdigit, retweet_text))) if retweet_text else 0
                                
                                # Get likes
                                like_stat = await stats_container.query_selector('.tweet-stat:has(.icon-heart)')
                                if like_stat:
                                    like_text = await like_stat.inner_text()
                                    metrics['like'] = int(''.join(filter(str.isdigit, like_text))) if like_text else 0
                            
                            tweet_data = {
                                'text': text,
                                'timestamp': timestamp,
                                'url': tweet_url,
                                'metrics': metrics
                            }
                            
                            tweets.append(tweet_data)
                            
                        except Exception as e:
                            logging.error(f"Error extracting tweet data: {str(e)}")
                            continue
                    
                    result = {
                        'url': url,
                        'username': username,
                        'timestamp': datetime.now().isoformat(),
                        'tweets': tweets,
                        'success': True
                    }
                    
                    logging.info(f"Successfully crawled {url}: found {len(tweets)} tweets")
                    return result
                    
                except Exception as e:
                    logging.error(f"Error extracting profile data: {str(e)}")
                    return {
                        'url': url,
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e),
                        'success': False
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
    # List of URLs to crawl
    async with async_playwright() as playwright:
        # Launch headless browser
        logging.info("Launching headless browser...")
        browser = await playwright.chromium.launch(
            headless=True,  # Use headless mode
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
                '--disable-features=CrossOriginOpenerPolicy',
                '--disable-features=CrossOriginEmbedderPolicy'
            ]
        )
        
        # Create a new context with realistic browser settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
            bypass_csp=True,
            java_script_enabled=True,
            has_touch=True,
            is_mobile=False,
            color_scheme='light',
            reduced_motion='no-preference',
            forced_colors='none'
        )
        
        # Create a new page
        page = await context.new_page()
        
        # Set extra HTTP headers
        await page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'DNT': '1',
            'Referer': 'https://www.google.com/'
        })
        
        crawler = NitterCrawler()
        crawler.page = page
        
        results = []
        failed_urls = []
        
        # Create results directory if it doesn't exist
        os.makedirs('nitter_results', exist_ok=True)
        
        try:
            for i, url in enumerate(NITTER_URLS):
                logging.info(f"Processing {url} ({i+1}/{len(NITTER_URLS)})")
                
                # Add delay to avoid rate limiting
                if i > 0:
                    await asyncio.sleep(5)
                
                result = await crawler.crawl_profile(url)
                results.append(result)
                
                if not result['success']:
                    failed_urls.append(url)
                
                # Save intermediate results
                if (i + 1) % 5 == 0:
                    with open('nitter_results/nitter_results_temp.json', 'w', encoding='utf-8') as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)
                    logging.info("Saved intermediate results to nitter_results/nitter_results_temp.json")
            
            # Save final results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            final_filename = f'nitter_results/nitter_results_{timestamp}.json'
            with open(final_filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            # Save failed URLs
            if failed_urls:
                failed_filename = f'nitter_results/failed_urls_{timestamp}.txt'
                with open(failed_filename, 'w', encoding='utf-8') as f:
                    for url in failed_urls:
                        f.write(f"{url}\n")
                logging.warning(f"Failed to crawl {len(failed_urls)} URLs. See {failed_filename} for details")
            
            logging.info(f"Crawling completed! Final results saved to {final_filename}")
            logging.info(f"Successfully crawled: {len(results) - len(failed_urls)} URLs")
            logging.info(f"Failed to crawl: {len(failed_urls)} URLs")
            
        finally:
            # Clean up
            await context.close()
            await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Crawling interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}") 