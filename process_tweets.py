import json
import glob
import os
from datetime import datetime, timedelta
import pytz  # 需要添加这个导入

def create_prompt(texts):
    combined_text = "\n\n".join([f"推文 {i+1}:\n{text}" for i, text in enumerate(texts)])
    return f"""请以科技主编的视角总结以下所有推文内容，可以搜索网络，适当扩展，要求：

1. 内容要求：
   - 先说整体结论，再分点说明重要内容
   - 交代清楚背景信息
   - 主语必须是人或机构组织（如果是人要带上身份/职位）
   - 使用简单易懂的中文，避免专业术语
   - 纯文本输出，不要使用markdown格式
   - 注意不同推文之间的关联性

2. 写作风格：
   - 语气专业但不失亲和力
   - 逻辑清晰，层次分明
   - 重点突出，避免冗长
   - 适当使用数据支持观点

请总结以下推文：
{combined_text}"""

def is_recent_tweet(tweet, days=7):
    """检查推文是否在指定天数内"""
    try:
        # 确保tweet_time是带时区的
        tweet_time = datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00'))
        # 确保cutoff_time也是带时区的
        cutoff_time = datetime.now(pytz.UTC) - timedelta(days=days)
        print(f'Debug - Tweet time: {tweet_time} (type: {type(tweet_time)})')
        print(f'Debug - Cutoff time: {cutoff_time} (type: {type(cutoff_time)})')
        print(f'Debug - Is recent: {tweet_time >= cutoff_time}')
        return tweet_time >= cutoff_time
    except Exception as e:
        print(f'Error parsing timestamp: {e}')
        return True  # 如果无法解析时间，默认包含

def process_twitter_results():
    # 获取所有twitter_results文件
    result_files = glob.glob('twitter_results_*.json')
    
    if not result_files:
        print("未找到任何twitter_results文件")
        return
    
    # 创建输出目录
    if not os.path.exists('prompts'):
        os.makedirs('prompts')
    
    for file_path in result_files:
        try:
            print(f"\n处理文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 创建对应的输出文件
            output_file = os.path.join('prompts', f'prompts_{os.path.basename(file_path)}')
            
            # 收集所有推文
            all_tweets = []
            
            for item in data:
                if not item.get('success'):
                    print(f"跳过失败的URL: {item.get('url')}")
                    continue
                    
                if not item.get('tweets'):
                    print(f"跳过无推文的URL: {item.get('url')}")
                    continue
                
                # 处理推文
                for tweet in item['tweets']:
                    if not tweet.get('text'):
                        continue
                        
                    # 检查是否是最近3天的推文
                    if not is_recent_tweet(tweet):
                        continue
                    
                    # 添加到推文列表
                    all_tweets.append({
                        "user": item.get('username', 'Unknown'),
                        "text": tweet['text']
                    })
            
            # 准备输出的JSON数据
            output_data = {
                "instruction": "请总结以下所有推文，注意不同推文之间的关联性",
                "tweets": all_tweets,
                "prompt": create_prompt([tweet['text'] for tweet in all_tweets])
            }
            
            # 写入JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"成功处理文件: {file_path}")
            print(f"生成提示文件: {output_file}")
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {str(e)}")

if __name__ == "__main__":
    process_twitter_results() 