import os
import requests
import feedparser
import datetime
import time
import random  # 新增：用于随机抽题
import google.generativeai as genai
from bs4 import BeautifulSoup
from time import mktime

# --- 配置部分 ---
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 
SEARCH_API_KEY = os.environ.get("GOOGLESEARCH_API_KEY") 
SEARCH_CX = os.environ.get("GOOGLESEARCH_CX")            

# 初始化 Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 使用 2.0-flash 以获得最佳稳定性
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Gemini 配置出错: {e}")
else:
    print("警告: 未配置 GOOGLE_API_KEY")

# --- 1. 获取新闻 ---
def get_fusion_news():
    print("正在抓取新闻...")
    # 稍微放宽一点搜索词，确保有内容
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+energy&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:8]: # 抓取前8条给AI筛选
            published_date = "未知日期"
            if hasattr(entry, 'published_parsed'):
                dt = datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
                published_date = dt.strftime('%Y-%m-%d')
            
            news_items.append(f"- [{entry.title}]({entry.link}) (日期: {published_date})")
        return "\n".join(news_items) if news_items else "暂无重大新闻。"
    except Exception as e:
        return f"新闻抓取失败: {e}"

# --- 2. 搜索实习 (优化版：移除死板的时间限制) ---
def search_internships():
    print("正在搜索实习岗位...")
    if not SEARCH_API_KEY or not SEARCH_CX:
        return "错误：代码无法读取到 Search Key。"

    # 优化关键词：增加 career, job，移除 -news 以免误伤
    query = '"nuclear fusion" (internship OR "summer student" OR "phd position" OR career)'
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': SEARCH_API_KEY,
        'cx': SEARCH_CX,
        'q': query,
        # 'dateRestrict': 'm3',  <-- 【关键修改】移除时间限制，让AI去判断页面里的内容是否过期
        'num': 3 
    }

    try:
        response = requests.get(url, params=params).json()
        
        if 'error' in response:
            return f"Google Search API 报错: {response['error']['message']}"

        items = response.get('items', [])
        if not items:
            return "Search API 返回空结果 (未找到相关页面)。"

        processed_jobs = []
        for item in items:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet')
            
            # 简单清洗
            processed_jobs.append(f"岗位标题: {title}\n链接: {link}\n摘要: {snippet}\n---")
            
        return "\n".join(processed_jobs)
    except Exception as e:
        return f"实习搜索出错: {e}"

# --- 3. 生成日报 (随机题库 + 链接优化) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # 【新增】核聚变知识随机题库 (防止每天讲一样的内容)
    fusion_topics = [
        "托卡马克(Tokamak)与仿星器(Stellarator)的区别",
        "氚增殖比 (Tritium Breeding Ratio, TBR)",
        "偏滤器 (Divertor) 的热负荷挑战",
        "第一壁材料 (First Wall Materials) 与中子辐照",
        "磁流体动力学 (MHD) 不稳定性",
        "锯齿振荡 (Sawtooth instability)",
        "边缘局域模 (ELMs)",
        "H模式 (High-confinement mode) 与 L模式",
        "劳森判据 (Lawson Criterion)",
        "Q值 (Q factor) 与点火条件",
        "ITER 项目的工程挑战",
        "惯性约束聚变 (Inertial Confinement Fusion)",
        "瑞利-泰勒不稳定性 (Rayleigh-Taylor instability)",
        "高温超导磁体 (HTS magnets) 在聚变中的应用",
        "球形托卡马克 (Spherical Tokamak)",
        "场反向配置 (Field-Reversed Configuration, FRC)",
        "Helion Energy 的脉冲磁聚变方案",
        "聚变反应堆的遥操作维护 (Remote Handling)",
        "锂铅包层 (Li-Pb Blanket)",
        "聚变能的经济性分析 (LCOE)"
    ]
    # 每天随机选一个
    today_topic = random.choice(fusion_topics)
    print(f"今日随机科普主题: {today_topic}")

    prompt = f"""
    你是一位**深耕核聚变领域的资深科研助理**，同时也是一位文笔幽默、逻辑严密的科技博主。
    请根据以下输入数据，为我生成一份 {today_str} 的《核聚变情报局·每日简报》。

    ---
    ### 输入数据区
    **1. 新闻源数据:**
    {news_text}

    **2. 实习岗位抓取数据:**
    {internship_text}
    
    **3. 今日指定科普主题:** {today_topic}

    ---
    ### 输出要求 (Markdown格式)

    # ⚛️ 聚变情报局 | {today_str}
    > "在这里，我们离人造太阳更近一步。"

    ## 📰 1. Fusion Frontiers
    *(指令：筛选 5-7 条有价值的新闻。)*
    * **[新闻标题 (中文)]**
        * 📍 **Who**: [机构/地点]
        * 💡 **Core**: [核心事件简述]
        * 🚀 **Significance**: [深度点评意义]
        * 🔗 [点击阅读原文]({'{link}'})  <-- **重要指令：不要直接显示长链接，请使用 Markdown 语法将链接隐藏在“点击阅读原文”文字中，保留原始链接地址。**

    ## 🎯 2. Career Radar
    *(指令：根据抓取到的数据分析。由于我们取消了搜索时间限制，请你根据摘要内容判断这些岗位是否看起来像近期的。如果数据里没有明显的岗位，请幽默地写一段鼓励的话，不要报错。)*
    
    * 🏢 **[机构名]** —— **[岗位名]**
        * 📝 **任务**: [干什么]
        * 🎓 **要求**: [要什么人]
        * 🔗 [点击直达官网]({'{link}'}) <-- **重要：使用短链接格式**

    ## 🧠 3. Deep Dive: {today_topic}
    *(指令：今天必须讲解这个特定主题：**{today_topic}**。)*
    
    * **今日词条：{today_topic}**
    * **🧐 硬核原理解析**：
        [专业术语描述机制，约 200 字]
    * **🍎 也就是人话版**：
        [**重点！** 使用极其通俗、生活化的比喻（如用水管、果冻、交通拥堵等比喻）。约 150 字]
    * **🤔 为什么它很重要？**：
        [一句话点评]

    ---
    *由 GitHub Actions 自动生成 · 今日随机种子: {today_topic}*
    """
    
    # 重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"尝试 {attempt+1} 失败: {e}")
            if "429" in str(e):
                time.sleep(10)
            else:
                time.sleep(5)
    return "❌ 生成失败，请检查 API 配额或网络。"

# --- 4. 推送 ---
def send_wechat(content):
    if not SERVERCHAN_SENDKEY:
        print("未配置 Server酱 Key，跳过推送")
        return

    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    data = {
        "title": f"⚛️ {datetime.date.today()} 聚变情报局", 
        "desp": content
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    news = get_fusion_news()
    internships = search_internships()
    report = generate_daily_report(news, internships)
    print(report)
    send_wechat(report)
