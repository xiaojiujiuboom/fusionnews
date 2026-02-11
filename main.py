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

# --- 配置部分 ---
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 

# 初始化 Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Gemini 配置出错: {e}")
else:
    print("警告: 未配置 GOOGLE_API_KEY")

# --- 辅助函数：强力网页抓取器 ---
def fetch_url_content(url, source_name):
    print(f"正在抓取 {source_name} ...")
    try:
        # 伪装成普通浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 移除脚本和样式，只留干货
            for script in soup(["script", "style", "nav", "footer", "iframe"]):
                script.extract()
            # 提取正文，限制长度防止 token 溢出
            text = soup.get_text(separator='\n', strip=True)[:4000]
            print(f"  -> 成功获取 {len(text)} 字符")
            return f"=== 来自 {source_name} 的招聘页面数据 ===\nURL: {url}\n页面内容摘要:\n{text}\n----------------\n"
        else:
            print(f"  -> 失败 (状态码 {resp.status_code})")
            return f"{source_name} 抓取失败，请手动访问: {url}\n"
    except Exception as e:
        print(f"  -> 抓取异常: {e}")
        return f"{source_name} 连接超时，请手动访问: {url}\n"

# --- 1. 获取新闻 (保持不变) ---
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

# --- 2. 职位雷达 (定向靶点抓取模式) ---
def search_internships():
    print("🚀 启动职位雷达 (Targeted Aggregator Mode)...")
    
    # 这里定义了三个含金量最高的聚变职位聚合页
    targets = [
        {
            "name": "Fusion Industry Association (FIA)",
            "url": "https://www.fusionindustryassociation.org/about/job-opportunities/"
        },
        {
            "name": "US Fusion Energy Opportunities",
            "url": "https://usfusionenergy.org/opportunities"
        },
        {
            "name": "ITER Jobs",
            "url": "https://www.iter.org/jobs"
        }
    ]
    
    all_content = ""
    for target in targets:
        content = fetch_url_content(target["url"], target["name"])
        all_content += content
        time.sleep(2) # 礼貌延时
        
    return all_content

# --- 3. 生成日报 ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    fusion_topics = [
        "劳森判据", "Q值", "MHD不稳定性", "托卡马克", "仿星器", "ICF",
        "第一壁材料", "钨", "偏滤器", "氚增殖比", "中子辐照", "H模式", 
        "ELMs", "ITER", "CFS SPARC", "Helion", "General Fusion"
    ]
    date_hash = int(hashlib.sha256(today_str.encode('utf-8')).hexdigest(), 16)
    today_topic = fusion_topics[date_hash % len(fusion_topics)]

    prompt = f"""
    你是一位**核聚变情报局特工**。请生成 {today_str} 的日报。
    
    ---
    ### 1. News Data
    {news_text}
    
    ### 2. Job Market Intel (Raw Scraped Data)
    *(这是直接从 FIA、ITER 等官网抓取的网页正文文本。)*
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
    
    ## 🎯 2. Career Radar (官网直连)
    *(指令：请分析抓取到的网页正文。告诉用户这些页面上目前主要在招哪些类型的岗位？有没有提到具体的公司名字？)*
    *(注意：如果网页正文太乱，请只提取最核心的岗位关键词，如 'Plasma Physicist', 'Intern', 'Engineer' 等。)*
    
    * 🏢 **Fusion Industry Association (FIA)**
        * 📝 **情报**: [根据抓取内容，总结FIA页面上列出的最新机会类型]
        * 🔗 [点击直达汇总页](https://www.fusionindustryassociation.org/about/job-opportunities/)
        
    * 🏢 **US Fusion Energy**
        * 📝 **情报**: [根据抓取内容，总结美国方面的机会]
        * 🔗 [点击直达汇总页](https://usfusionenergy.org/opportunities)

    * 🏢 **ITER Organization**
        * 📝 **情报**: [根据抓取内容，ITER最近在招什么人？]
        * 🔗 [点击直达官网](https://www.iter.org/jobs)
    
    ## 🧠 3. Deep Dive: {today_topic}
    * **今日词条：{today_topic}**
    * **🧐 硬核解析**：[200字]
    * **🍎 人话版**：[生活比喻，150字]
    * **🤔 为什么重要？**：[一句话]
    
    ---
    *Generated by FusionBot*
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
