from crawl4ai import AsyncWebCrawler
import json
from datetime import datetime
import os
import logging
import asyncio
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TechCrunchCrawler:
    def __init__(self):
        self.base_url = "https://techcrunch.com/latest/"
        
    async def crawl(self, num_pages: int = 1) -> List[Dict]:
        """只爬取TechCrunch文章链接"""
        articles = []
        
        async with AsyncWebCrawler() as crawler:
            for page in range(1, num_pages + 1):
                url = self.base_url
                try:
                    result = await crawler.arun(
                        url=url,
                        extract_text=True,
                        extract_metadata=True,
                        javascript=True
                    )
                    
                    if result and result.html:
                        soup = BeautifulSoup(result.html, 'html.parser')
                        # 查找所有文章链接
                        for link in soup.find_all('a', class_='loop-card__title-link', href=True):
                            href = link.get('href', '').strip(':')
                            if href and href.startswith('https://techcrunch.com/20'):
                                articles.append({
                                    'url': href,
                                    'title': link.get_text(strip=True),
                                    'crawl_date': datetime.now().isoformat()
                                })
                                logger.info(f"成功获取文章链接: {href}")
                    
                except Exception as e:
                    logger.error(f"爬取页面出错 {url}: {str(e)}")
                    continue
                    
        return articles

def save_articles(articles: List[Dict], filename: Optional[str] = None):
    """保存文章链接和提示词到JSON文件"""
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(results_dir, f"techcrunch_links_{timestamp}.json")
    
    # 构建输出的JSON结构
    output_data = {
        "articles": articles,
        "prompt": """请以科技主编的视角总结以下所有推文内容，可以搜索网络，适当扩展，要求：

1. 内容要求：
   - 交代清楚背景信息
   - 主语必须是人或机构组织（如果是人要带上身份/职位）
   - 使用简单易懂的中文，避免专业术语
   - 纯文本输出，不要使用markdown格式
   - 确保所有信息准确无误，如有不确定的内容请明确标注"待确认"
   - 每个重要信息点必须标注具体来源

2. 写作风格：
   - 语气专业但不失亲和力
   - 逻辑清晰，层次分明
   - 重点突出，避免冗长
   - 适当使用数据支持观点
   - 保持客观中立，避免主观臆测

3. 信息来源要求：
   - 如需补充外部信息，必须引用网络公开信息，并标注具体来源链接
   - 对于推测性内容，必须明确标注"推测"或"可能"
   - 对于有争议的内容，需要标注不同观点及其来源
   - 所有引用的外部信息必须是可公开访问的网络资料"""
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"保存了 {len(articles)} 个文章链接到 {filename}")

if __name__ == "__main__":
    crawler = TechCrunchCrawler()
    articles = asyncio.run(crawler.crawl(num_pages=1))  # 爬取前2页
    save_articles(articles)