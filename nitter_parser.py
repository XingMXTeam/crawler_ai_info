from dataclasses import dataclass
from typing import List, Optional
import re
from datetime import datetime, timedelta

@dataclass
class Tweet:
    text: str
    time: str
    likes: Optional[int] = None
    retweets: Optional[int] = None
    quotes: Optional[int] = None
    replies: Optional[int] = None
    
@dataclass
class Profile:
    username: str
    display_name: str
    bio: Optional[str] = None
    tweets: List[Tweet] = None

def clean_tweet_text(text: str) -> str:
    """Clean tweet text by removing profile images, links and unnecessary formatting"""
    # Remove profile image markdown
    text = re.sub(r'\[!\[\]\([^)]+\)\]\([^)]+\)', '', text)
    # Remove user profile links
    text = re.sub(r'\[[^\]]+\]\([^)]+\s+"[^"]+"\)', '', text)
    # Remove username links
    text = re.sub(r'\[@[^\]]+\]\([^)]+\s+"@[^"]+"\)', '', text)
    # Remove date links
    text = re.sub(r'\[[^\]]+\]\([^)]+#m\s+"[^"]+"\)', '', text)
    # Remove status links
    text = re.sub(r'\[\]\(https://nitter\.net/[^)]+\)', '', text)
    # Remove engagement metrics pattern (4 numbers at the end)
    text = re.sub(r'\n\d+(?:\n\d+){3}\s*$', '', text)
    # Remove any remaining single numbers at the end
    text = re.sub(r'\n\d+\s*$', '', text)
    # Remove multiple newlines
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def parse_date(date_str: str) -> datetime:
    """Convert date string to datetime object"""
    months = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    month_str, day_str = date_str.split()
    month = months[month_str]
    day = int(day_str)
    
    # Get current year
    current_date = datetime.now()
    year = current_date.year
    
    # If the month is ahead of current month, it must be from last year
    if month > current_date.month:
        year -= 1
        
    return datetime(year, month, day)

def is_within_days(date_str: str, days: int = 3) -> bool:
    """Check if the given date is within specified days from now"""
    try:
        tweet_date = parse_date(date_str)
        cutoff_date = datetime.now() - timedelta(days=days)
        return tweet_date >= cutoff_date
    except Exception:
        return False

def extract_engagement_metrics(block: str) -> tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """Extract engagement metrics from tweet block"""
    # Try to find the pattern of 4 numbers at the end
    numbers = re.findall(r'\n(\d+(?:,\d+)?)\s*$', block)
    if len(numbers) >= 4:
        # Convert the last 4 numbers, removing commas
        try:
            retweets = int(numbers[-4].replace(',', ''))
            quotes = int(numbers[-3].replace(',', ''))
            replies = int(numbers[-2].replace(',', ''))
            likes = int(numbers[-1].replace(',', ''))
            return retweets, quotes, replies, likes
        except ValueError:
            pass
    return None, None, None, None

def parse_nitter_content(content: str, max_days: int = 3) -> Profile:
    """Parse Nitter content and extract profile and tweet information"""
    # Extract profile information
    profile = {}
    
    # Find username and display name (simplified)
    profile_match = re.search(r'@(\w+)', content)
    if profile_match:
        profile['username'] = f"@{profile_match.group(1)}"
        
        # Try to find display name in the content
        display_name_match = re.search(r'\[([^\]]+)\]\([^)]+\s+"([^"]+)"\)\s+\[@\w+\]', content)
        if display_name_match:
            profile['display_name'] = display_name_match.group(1)
        else:
            profile['display_name'] = profile_match.group(1)
    
    # Find bio (if exists)
    bio_match = re.search(r'Bio:\s+([^\n]+)', content)
    if bio_match:
        profile['bio'] = bio_match.group(1).strip()
    
    # Extract tweets
    tweets = []
    # Split content into tweet blocks
    tweet_blocks = re.split(r'\n(?=\[(?:Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)\s+\d{1,2}\])', content)
    
    for block in tweet_blocks:
        # Skip non-tweet blocks or empty blocks
        if not block.strip() or not re.search(r'\[(Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)', block):
            continue
            
        # Extract tweet time
        time_match = re.search(r'\[((?:Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)\s+\d{1,2})\]', block)
        if not time_match:
            continue
        
        time = time_match.group(1)
        
        # Skip tweets older than max_days
        if not is_within_days(time, max_days):
            continue
        
        # Extract engagement metrics before cleaning the text
        retweets, quotes, replies, likes = extract_engagement_metrics(block)
        
        # Clean and extract tweet text
        text = clean_tweet_text(block)
        
        if text:  # Only add if we have actual text content
            tweets.append(Tweet(
                text=text,
                time=time,
                likes=likes,
                retweets=retweets,
                quotes=quotes,
                replies=replies
            ))
    
    return Profile(
        username=profile.get('username', ''),
        display_name=profile.get('display_name', ''),
        bio=profile.get('bio'),
        tweets=tweets
    ) 