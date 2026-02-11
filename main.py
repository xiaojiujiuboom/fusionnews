import os
import requests
import feedparser
import datetime
import time
import google.generativeai as genai
from bs4 import BeautifulSoup
from time import mktime

# --- 配置部分 ---
# 【关键修改】这里必须和你截图里的 Secret 名字完全一致
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 
SEARCH_API_KEY = os.environ.get("GOOGLESEARCH_API_KEY") # 改成无下划线
SEARCH_CX = os.environ.get("GOOGLESEARCH_CX")           # 改成无下划线

# 初始化 Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Gemini 配置出错: {e}")
else:
    print("警告: 未配置 GOOGLE_API_KEY")

# --- 1. 获取新闻 ---
def get_fusion_news():
    print("正在抓取新闻...")
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+when:48h&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:10]:
            published_date = "未知日期"
            if hasattr(entry, 'published_parsed'):
                dt = datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
                published_date = dt.strftime('%Y-%m-%d')
            
            news_items.append(f"- [{entry.title}]({entry.link}) (日期: {published_date})")
        return "\n".join(news_items) if news_items else "过去48小时无重大新闻。"
    except Exception as e:
        return f"新闻抓取失败: {e}"

# --- 2. 搜索实习 ---
def search_internships():
    print("正在搜索实习岗位...")
    
    # 检查 Key 是否存在
    if not SEARCH_API_KEY or not SEARCH_CX:
        return "错误：代码无法读取到 Search Key。请检查 main.py 和 yaml 文件中的变量名是否一致。"

    query = '"nuclear fusion" (internship OR thesis OR "summer student" OR "phd position") -news'
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': SEARCH_API_KEY,
        'cx': SEARCH_CX,
        'q': query,
        'dateRestrict': 'm3',
        'num': 3 
    }

    try:
        response = requests.get(url, params=params).json()
        
        if 'error' in response:
            return f"Google Search API 报错: {response['error']['message']}"

        items = response.get('items', [])
        if not items:
            return "最近3个月未发现高相关度的实习信息。"

        processed_jobs = []
        for item in items:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet')
            
            page_content = snippet
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; FusionBot/1.0)'}
                page_res = requests.get(link, headers=headers, timeout=5)
                if page_res.status_code == 200:
                    soup = BeautifulSoup(page_res.text, 'html.parser')
                    for script in soup(["script", "style"]):
                        script.extract()
                    page_content = " ".join(soup.get_text().split())[:3000]
            except:
                pass 
            
            processed_jobs.append(f"岗位: {title}\n链接: {link}\n内容: {page_content}\n---")
            
        return "\n".join(processed_jobs)
    except Exception as e:
        return f"实习搜索出错: {e}"

# --- 3. 生成日报 ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    prompt = f"""
    你是一位核聚变科研助理。请生成 {today_str} 的日报。

    ### 第一部分：聚变前沿 (News)
    {news_text}
    要求：挑选最有价值的新闻，按 Markdown 列表输出，包含[What, Significance]。

    ### 第二部分：岗位雷达 (Jobs)
    {internship_text}
    要求：针对每个岗位，提取 [机构, 职责, 要求]，保留链接。如果没有合适岗位，请明确说明。

    ### 第三部分：每日硬核科普 (Deep Dive)
    要求：讲解一个进阶的核聚变物理/工程知识点（如MHD、TBR、偏滤器等），250字左右，深度适中。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 生成报告失败: {e}"

# --- 4. 推送 ---
def send_wechat(content):
    if not SERVERCHAN_SENDKEY:
        print("未配置 Server酱 Key，跳过推送")
        return

    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    data = {"title": f"⚛️ 核聚变日报 {datetime.date.today()}", "desp": content}
    requests.post(url, data=data)

if __name__ == "__main__":
    news = get_fusion_news()
    internships = search_internships()
    report = generate_daily_report(news, internships)
    print(report)
    send_wechat(report)
