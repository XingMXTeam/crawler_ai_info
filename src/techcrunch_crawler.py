from crawl4ai import AsyncWebCrawler
import json
from datetime import datetime
import os
import logging
import asyncio
from typing import List, Dict, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TechCrunchCrawler:
    def __init__(self):
        self.base_url = "https://techcrunch.com/"
        
    async def crawl(self, num_pages: int = 1) -> List[Dict]:
        """使用 crawl4ai 爬取 TechCrunch 文章"""
        articles = []
        
        async with AsyncWebCrawler() as crawler:
            for page in range(1, num_pages + 1):
                url = self.base_url if page == 1 else f"{self.base_url}page/{page}/"
                try:
                    # 使用 crawl4ai 的智能爬取功能
                    result = await crawler.arun(
                        url=url,
                        extract_text=True,
                        extract_metadata=True,
                        filter_urls=lambda u: u.startswith("https://techcrunch.com/20")
                    )
                    
                    if result and result.markdown:
                        # 从 markdown 中提取文章链接
                        article_links = [
                            line.split("](")[1].rstrip(")")
                            for line in result.markdown.split("\n")
                            if line.startswith("[") and "techcrunch.com/20" in line
                        ]
                        
                        for link in article_links:
                            try:
                                # 爬取单篇文章
                                article_result = await crawler.arun(
                                    url=link,
                                    extract_text=True,
                                    extract_metadata=True
                                )
                                
                                if article_result and article_result.markdown:
                                    articles.append({
                                        'url': link,
                                        'title': article_result.title,
                                        'content': article_result.markdown,
                                        'metadata': article_result.metadata,
                                        'crawl_date': datetime.now().isoformat()
                                    })
                                    logger.info(f"成功爬取文章: {article_result.title}")
                            
                            except Exception as e:
                                logger.error(f"爬取文章出错 {link}: {str(e)}")
                                continue
                    
                except Exception as e:
                    logger.error(f"爬取页面出错 {url}: {str(e)}")
                    continue
                    
        return articles

def save_articles(articles: List[Dict], filename: Optional[str] = None):
    """保存爬取的文章到 results 目录"""
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(results_dir, f"techcrunch_results_{timestamp}.json")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    logger.info(f"保存了 {len(articles)} 篇文章到 {filename}")

if __name__ == "__main__":
    crawler = TechCrunchCrawler()
    articles = asyncio.run(crawler.crawl(num_pages=2))  # 爬取前2页
    save_articles(articles)