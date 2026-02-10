import os
import requests
import feedparser
import datetime
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- 配置部分 ---
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 
SEARCH_API_KEY = os.environ.get("GOOGLESEARCH_API_KEY") 
SEARCH_CX = os.environ.get("GOOGLESEARCH_CX")

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# --- 1. 获取新闻 ---
def get_fusion_news():
    print("正在抓取新闻...")
    # 关键词：Nuclear Fusion，时间：过去48小时
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+when:48h&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:5]:
            news_items.append(f"- [{entry.title}]({entry.link})")
        return "\n".join(news_items) if news_items else "过去48小时无重大新闻。"
    except Exception as e:
        return f"新闻抓取失败: {e}"

# --- 2. 搜索实习 ---
def search_internships():
    print("正在搜索实习岗位...")
    if not SEARCH_API_KEY or not SEARCH_CX:
        return "错误：未配置 Google Search API Key 或 CX ID。"

    # 搜索关键词：实习、论文、学生，限制最近3个月
    query = "internship OR thesis OR student OR graduate"
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': SEARCH_API_KEY,
        'cx': SEARCH_CX,
        'q': query,
        'dateRestrict': 'm3',
        'num': 3 # 取前3个结果
    }

    try:
        response = requests.get(url, params=params).json()
        items = response.get('items', [])
        
        if not items:
            return "最近3个月未在指定网站发现新的实习/校招信息。"

        processed_jobs = []
        for item in items:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet')
            processed_jobs.append(f"岗位: {title}\n链接: {link}\n摘要: {snippet}\n---")
            
        return "\n".join(processed_jobs)
    except Exception as e:
        return f"实习搜索出错: {e}"

# --- 3. 生成日报 (AI) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    prompt = f"""
    你是一个核聚变领域的资深科技博主。请根据以下输入生成一份微信日报。

    ### 第一部分：【聚变新动态】(基于以下新闻，用中文简要概括，每条不超过50字)
    {news_text}

    ### 第二部分：【实习与搞钱】(这是重点！请仔细阅读以下抓取到的岗位信息)
    {internship_text}
    如果有岗位，请务必针对每一个岗位，按以下格式列出：
    * **🏢 机构**: [推断机构名称]
    * **👨‍🎓 需求**: [总结原文中的要求]
    * **🔗 传送门**: [保留原始链接]

    ### 第三部分：【每日一口聚变鲜】
    请给我科普一个核聚变相关的知识点（工程或理论皆可），要求：
    1. 风格轻松愉快，可以适当使用 emoji。
    2. 篇幅 100 字左右。
    3. 内容要有含金量，不要太小白。

    请直接输出 Markdown 格式。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 生成报告失败: {e}"

# --- 4. 推送 (Server酱) ---
def send_wechat(content):
    print("正在推送...")
    if not SERVERCHAN_SENDKEY:
        print("未配置 Server酱 Key，跳过推送")
        return

    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    data = {
        "title": f"⚛️ 核聚变早报 {datetime.date.today()}",
        "desp": content 
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    news = get_fusion_news()
    internships = search_internships()
    report = generate_daily_report(news, internships)
    print(report) # 在日志里也打印一份，方便调试
    send_wechat(report)
