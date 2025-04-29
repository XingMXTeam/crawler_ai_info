import json
import glob
import os
from datetime import datetime, timedelta

def create_prompt(text):
    return f"""请以科技主编的视角总结以下内容，要求：

1. 内容要求：
   - 先说结论，再说细节
   - 交代清楚背景信息
   - 主语必须是人或机构组织（如果是人要带上身份/职位）
   - 使用简单易懂的中文，避免专业术语
   - 纯文本输出，不要使用markdown格式

2. 写作风格：
   - 语气专业但不失亲和力
   - 逻辑清晰，层次分明
   - 重点突出，避免冗长
   - 适当使用数据支持观点

3. 参考示例：
   这几天连续在吃中日友好医院的瓜，前几天主线剧情一直是某副主任医师出轨多名同事，导致同事流产、怀孕，这些我觉得没必要在夜报里写，因为我不会当着几十万读者的面审判他人私德，多管闲事。但随着这个瓜的剧情发酵，舆情开始关注起了那位被医生搞大肚子的董医生，她的经历有些特殊。父亲是某央企的总经理\党委副书记（副厅级），母亲是北京211高校的副院长（副处级），女儿高中就去美国读书，之后在哥伦比亚大学读了一个经济学本科。......, 今天泡泡玛特炸裂上涨13%，市值飙到了2600亿。他们公司前几天 LABUBU第三代搪胶毛绒产品“前方高能”系列全球发售，国内国外都被热抢。国内二手市场溢价超过100%，国外芝加哥、洛杉矶也都排长队抢购，堪比当年iphone上市。

原文内容：
{text}

请总结："""

def is_recent_tweet(tweet, days=3):
    """检查推文是否在指定天数内"""
    try:
        tweet_time = datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00'))
        cutoff_time = datetime.now() - timedelta(days=days)
        return tweet_time >= cutoff_time
    except Exception:
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
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in data:
                    if not item.get('success'):
                        print(f"跳过失败的URL: {item.get('url')}")
                        continue
                        
                    if not item.get('tweets'):
                        print(f"跳过无推文的URL: {item.get('url')}")
                        continue
                    
                    # 写入用户信息
                    f.write(f"\n用户: {item.get('username', 'Unknown')}\n")
                    f.write("-" * 50 + "\n")
                    
                    # 处理推文
                    tweet_count = 0
                    for tweet in item['tweets']:
                        if not tweet.get('text'):
                            continue
                            
                        # 检查是否是最近3天的推文
                        if not is_recent_tweet(tweet):
                            continue
                            
                        # 写入原始推文
                        f.write(f"\n原始推文: {tweet['text']}\n")
                        # 写入提示
                        f.write(f"\n提示:\n{create_prompt(tweet['text'])}\n")
                        f.write("-" * 50 + "\n")
                        tweet_count += 1
                    
                    if tweet_count == 0:
                        print(f"URL {item.get('url')} 没有最近3天的推文")
            
            print(f"成功处理文件: {file_path}")
            print(f"生成提示文件: {output_file}")
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {str(e)}")

if __name__ == "__main__":
    process_twitter_results() 