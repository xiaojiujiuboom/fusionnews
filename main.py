import os
import requests
import feedparser
import datetime
import time
import random
import hashlib
import google.generativeai as genai
from bs4 import BeautifulSoup
from time import mktime
from duckduckgo_search import DDGS

# --- 配置部分 ---
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 

# 初始化 Gemini (使用 1.5-flash)
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Gemini 配置出错: {e}")
else:
    print("警告: 未配置 GOOGLE_API_KEY")

# --- 辅助函数：网页内容提取器 (借鉴 WorkAggregation 思路) ---
def fetch_webpage_content(url):
    """
    模拟浏览器访问 URL，提取网页正文文本
    """
    try:
        # 伪装成浏览器，防止被简单的反爬虫拦截
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        # 设置 10秒 超时，防止卡死
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # 检查 404/500 错误
        
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除 script, style 等无用标签
        for script in soup(["script", "style", "nav", "footer", "header", "iframe"]):
            script.extract()
            
        # 获取纯文本
        text = soup.get_text(separator=' ', strip=True)
        
        # 截取前 2500 个字符 (防止 Token 爆炸，通常 JD 都在前面)
        return text[:2500]
        
    except Exception as e:
        print(f"  - 访问链接失败 {url}: {e}")
        return None # 抓取失败返回空

# --- 1. 获取新闻 ---
def get_fusion_news():
    print("正在抓取新闻...")
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+when:48h&hl=en-US&gl=US&ceid=US:en"
    
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:8]: 
            published_time_str = "未知时间"
            if hasattr(entry, 'published_parsed'):
                dt = datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
                published_time_str = dt.strftime('%Y-%m-%d %H:%M')
            
            news_items.append(f"- {entry.title} (Time: {published_time_str}) [Link: {entry.link}]")
            
        return "\n".join(news_items) if news_items else "过去48小时无重大新闻。"
    except Exception as e:
        return f"新闻抓取失败: {e}"

# --- 2. 深度职位挖掘 (Search + Visit) ---
def search_internships():
    print("正在启动深度职位挖掘机...")
    
    # 策略组合：混合搜索，试图找到具体的招聘页面
    search_strategies = [
        'site:iter.org "job" OR "internship" -filetype:pdf',
        'site:cfs.energy "careers" OR "jobs"',
        'site:helionenergy.com "openings"',
        'site:pppl.gov "jobs"',
        '"nuclear fusion" "we are hiring" -news',
        '"plasma physics" internship 2025'
    ]
    
    query = random.choice(search_strategies)
    print(f"本次雷达锁定: {query}")

    try:
        # 1. 先搜链接
        # 减少数量到 4 个，因为后面要一个个访问，太慢了会超时
        results = DDGS().text(query, max_results=4)
        
        if not results:
            return "DuckDuckGo 未发现雷达信号，建议手动检查。"

        processed_jobs = []
        for item in results:
            title = item.get('title', 'No Title')
            link = item.get('href', '#')
            snippet = item.get('body', '')
            
            print(f"发现线索: {title}，正在派遣爬虫深入侦察...")
            
            # 2. 【核心升级】点进去看！
            # 调用上面的 fetch 函数去抓网页正文
            full_content = fetch_webpage_content(link)
            
            if full_content:
                # 如果抓到了正文，就喂给 AI 正文
                content_to_use = f"【网页正文抓取】: {full_content}"
            else:
                # 如果抓取失败（比如被反爬），回退到使用摘要
                content_to_use = f"【仅摘要】: {snippet}"
            
            processed_jobs.append(f"SOURCE_URL: {link}\nTITLE: {title}\nCONTENT: {content_to_use}\n---")
            
            # 礼貌性延时，防止请求太快被封
            time.sleep(2)
            
        return "\n".join(processed_jobs)

    except Exception as e:
        print(f"挖掘机故障: {e}")
        return f"职位扫描模块暂时休眠: {e}"

# --- 3. 生成日报 (Prompt 适配长文本) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    fusion_topics = [
        "劳森判据", "库仑碰撞", "Q值", "三重积", "MHD不稳定性", "阿尔芬波", 
        "托卡马克", "仿星器", "球形托卡马克", "反场箍缩", "Z-Pinch", "ICF",
        "第一壁材料", "钨", "铍", "偏滤器", "氚增殖比", "锂铅包层", "中子辐照", 
        "NBI加热", "ICRH", "ECRH", "H模式", "ELMs", "锯齿振荡", 
        "ITER", "CFS SPARC", "Helion", "General Fusion", "HL-3", "NIF"
    ]
    
    date_hash = int(hashlib.sha256(today_str.encode('utf-8')).hexdigest(), 16)
    today_topic = fusion_topics[date_hash % len(fusion_topics)]

    prompt = f"""
    你是一位**核聚变情报局特工**。请生成 {today_str} 的日报。
    
    ---
    ### 1. News Data
    {news_text}
    
    ### 2. Job Intel (深度抓取数据)
    *(以下数据包含了爬虫直接从网页抓取的正文。请忽略网页导航栏等杂讯，重点提取职位描述、要求。)*
    {internship_text}
    
    ### 3. Topic: {today_topic}
    
    ---
    ### 输出要求 (Markdown)
    
    # ⚛️ 聚变情报局 | {today_str}
    
    ## 📰 1. Fusion Frontiers
    *(筛选 4-5 条新闻)*
    * **[中文标题]**
        * 🕒 **Time**: [时间]
        * 🚀 **Significance**: [点评]
        * 🔗 [点击阅读原文]({'{link}'}) 
    
    ## 🎯 2. Career Radar (深度侦察)
    *(指令：我已通过爬虫抓取了网页正文。请根据【网页正文抓取】的内容，像猎头一样详细分析。)*
    *(如果抓取内容包含 "Apply"、"Requirements"、"Responsibilities" 等干货，请重点列出。)*
    *(如果抓取内容看起来是很多职位的列表页，请总结“该机构正在招聘哪些方向的人才”。)*
    
    * 🏢 **[机构/职位名称]**
        * 📝 **深度情报**: [从正文中提取：具体在做什么项目？涉及什么物理/工程难题？]
        * 🛠️ **通缉令**: [从正文中提取：硬性要求是什么？PhD？Python？C++？]
        * 🔗 [点击直达官网]({'{link}'})
    
    ## 🧠 3. Deep Dive: {today_topic}
    * **今日词条：{today_topic}**
    * **🧐 硬核解析**：[200字]
    * **🍎 人话版**：[生活比喻，150字]
    * **🤔 为什么重要？**：[一句话]
    
    ---
    *Generated by FusionBot · Topic: {today_topic}*
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"尝试 {attempt+1} 失败: {e}")
            time.sleep(5)
            
    return "⚠️ 生成失败，请检查 API 配额。"

# --- 4. 推送 ---
def send_wechat(content):
    if not SERVERCHAN_SENDKEY:
        return
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    data = {"title": f"⚛️ {datetime.date.today()} 聚变情报局", "desp": content}
    requests.post(url, data=data)

if __name__ == "__main__":
    news = get_fusion_news()
    internships = search_internships()
    report = generate_daily_report(news, internships)
    print(report)
    send_wechat(report)
