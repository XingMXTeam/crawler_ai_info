import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime, timedelta
import time
import logging
import random
from twitter_urls import TWITTER_URLS
from datetime import timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class TwitterCrawler:
    def __init__(self):
        self.context = None
        self.page = None
    
    async def random_delay(self, min_seconds=1, max_seconds=3):
        """随机延迟，模拟人类行为"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def crawl_profile(self, url):
        """爬取指定用户的推文"""
        try:
            logging.info(f"Starting to crawl: {url}")
            
            # 访问用户主页
            try:
                await self.page.goto(url)
                # 增加等待时间到5-8秒
                await self.random_delay(5, 8)
                
                # 等待页面加载完成
                try:
                    # 等待主要推文区域加载
                    await self.page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                    logging.info("Tweet area loaded successfully")
                except Exception as e:
                    logging.warning(f"Timeout waiting for tweet area: {str(e)}")
                    # 继续执行，因为页面可能已经部分加载
                
            except Exception as e:
                logging.warning(f"Page navigation warning: {str(e)}")
                # 继续执行，因为页面可能已经加载
            
            # 获取用户信息
            try:
                profile_name = await self.page.query_selector('div[data-testid="primaryColumn"] span:has-text("@")')
                username = await profile_name.inner_text() if profile_name else ""
            except Exception as e:
                logging.warning(f"Failed to get username: {str(e)}")
                username = ""
            
            # 获取推文
            tweets = await self.get_tweets(self.page)
            
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
            logging.error(f"Error crawling {url}: {str(e)}")
            return {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'success': False
            }

    async def get_tweets(self, page, max_tweets=3):
        """获取跳过置顶后的前三条推文"""
        tweets = []
        
        # 获取所有推文元素
        tweet_elements = await page.query_selector_all('article[data-testid="tweet"]')
        logging.info(f"Found {len(tweet_elements)} tweets on the page")
        
        # 跳过置顶推文，获取接下来的三条
        for tweet in tweet_elements[0:4]:  # 跳过第一个（置顶），取接下来的三个
            try:
                # 获取时间戳
                time_element = await tweet.query_selector('time')
                if not time_element:
                    continue
                    
                timestamp_str = await time_element.get_attribute('datetime')
                if not timestamp_str:
                    continue
                
                # 获取推文文本
                text_element = await tweet.query_selector('div[data-testid="tweetText"]')
                text = await text_element.inner_text() if text_element else ""
                
                if not text:
                    continue
                
                # 获取互动数据
                metrics = {}
                for metric in ['retweet', 'reply', 'like']:
                    metric_element = await tweet.query_selector(f'div[data-testid="{metric}"]')
                    if metric_element:
                        count_text = await metric_element.inner_text()
                        metrics[metric] = int(count_text) if count_text.isdigit() else 0
                
                tweet_data = {
                    'text': text,
                    'timestamp': timestamp_str,
                    'metrics': metrics
                }
                
                tweets.append(tweet_data)
                    
            except Exception as e:
                logging.error(f"Error extracting tweet data: {str(e)}")
                continue
        
        logging.info(f"Successfully collected {len(tweets)} tweets")
        return tweets

async def main():
    async with async_playwright() as playwright:
        # 尝试不同的端口连接到已存在的Chrome实例
        ports = [9222, 9223, 9224, 9225, 9226]
        browser = None
        
        for port in ports:
            try:
                logging.info(f"Trying to connect to Chrome on port {port}...")
                browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{port}")
                logging.info(f"Successfully connected to Chrome on port {port}")
                break
            except Exception as e:
                logging.warning(f"Failed to connect to port {port}: {str(e)}")
                continue
        
        if not browser:
            raise Exception("Could not connect to any Chrome instance. Please make sure Chrome is running with remote debugging enabled.")
        
        context = browser.contexts[0]  # 使用第一个上下文
        page = context.pages[0]  # 使用第一个页面
        
        crawler = TwitterCrawler()
        crawler.page = page
        
        results = []
        failed_urls = []
        
        for i, url in enumerate(TWITTER_URLS):
            logging.info(f"Processing {url} ({i+1}/{len(TWITTER_URLS)})")
            
            # 添加延迟避免频率限制
            if i > 0:
                await asyncio.sleep(5)
            
            result = await crawler.crawl_profile(url)
            results.append(result)
            
            if not result['success']:
                failed_urls.append(url)
            
            # 定期保存结果
            if (i + 1) % 5 == 0:
                with open('twitter_results_temp.json', 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                logging.info("Saved intermediate results to twitter_results_temp.json")
        
        # 保存最终结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_filename = f'twitter_results_{timestamp}.json'
        with open(final_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 保存失败的URL
        if failed_urls:
            failed_filename = f'failed_urls_{timestamp}.txt'
            with open(failed_filename, 'w', encoding='utf-8') as f:
                for url in failed_urls:
                    f.write(f"{url}\n")
            logging.warning(f"Failed to crawl {len(failed_urls)} URLs. See {failed_filename} for details")
        
        await browser.close()
        
        logging.info(f"Crawling completed! Final results saved to {final_filename}")
        logging.info(f"Successfully crawled: {len(results) - len(failed_urls)} URLs")
        logging.info(f"Failed to crawl: {len(failed_urls)} URLs")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Crawling interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}") 