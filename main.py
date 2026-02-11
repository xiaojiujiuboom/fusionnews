import os
import requests
import feedparser
import datetime
import time
import random
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
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Gemini 配置出错: {e}")
else:
    print("警告: 未配置 GOOGLE_API_KEY")

# --- 1. 获取新闻 (严格限制 48h) ---
def get_fusion_news():
    print("正在抓取新闻...")
    # 【关键修改】添加 when:48h 参数，强制 Google 只返回最近两天的新闻
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+when:48h&hl=en-US&gl=US&ceid=US:en"
    
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        
        # 获取当前时间用于对比（可选，主要是为了打日志）
        now = datetime.datetime.now()

        for entry in feed.entries[:10]: 
            published_time_str = "未知时间"
            
            # 解析时间戳
            if hasattr(entry, 'published_parsed'):
                # published_parsed 是 UTC 时间结构体
                dt = datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
                # 格式化为：2026-02-11 14:30
                published_time_str = dt.strftime('%Y-%m-%d %H:%M')
            
            # 组合数据喂给 AI
            # 格式：- 标题 (时间) [链接]
            news_items.append(f"- {entry.title} (Time: {published_time_str}) [Link: {entry.link}]")
            
        print(f"抓取到 {len(news_items)} 条新闻")
        return "\n".join(news_items) if news_items else "过去48小时无重大新闻 (Google RSS返回为空)。"
    except Exception as e:
        return f"新闻抓取失败: {e}"

# --- 2. 搜索实习 (保底模式 + 随机 User-Agent) ---
def search_internships():
    print("正在搜索实习岗位...")
    
    # 备用方案：硬编码的顶级机构招聘页 (防止 API 挂掉时开天窗)
    fallback_jobs = """
    【API 暂无实时数据，以下是长期有效的名企招聘入口】
    1. **ITER (国际热核聚变实验堆)**: https://www.iter.org/jobs
    2. **Commonwealth Fusion Systems (CFS)**: https://cfs.energy/careers
    3. **Helion Energy**: https://www.helionenergy.com/careers
    4. **Tokamak Energy**: https://www.tokamakenergy.co.uk/careers
    5. **General Fusion**: https://generalfusion.com/careers
    6. **Princeton Plasma Physics Lab (PPPL)**: https://www.pppl.gov/careers
    """

    if not SEARCH_API_KEY or not SEARCH_CX:
        return fallback_jobs

    # 稍微放宽一点，增加 "hiring"
    query = 'nuclear fusion (jobs OR internship OR "summer student" OR hiring)'
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': SEARCH_API_KEY,
        'cx': SEARCH_CX,
        'q': query,
        'num': 3 
    }

    try:
        print(f"请求 Google Search API...")
        response = requests.get(url, params=params).json()
        
        if 'error' in response:
            print(f"API Error: {response['error']}")
            return fallback_jobs

        items = response.get('items', [])
        if not items:
            return fallback_jobs

        processed_jobs = []
        for item in items:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet')
            processed_jobs.append(f"岗位: {title}\n链接: {link}\n摘要: {snippet}\n---")
            
        return "\n".join(processed_jobs)

    except Exception as e:
        print(f"搜索异常: {e}")
        return fallback_jobs

# --- 3. 生成日报 (日期标注 + 随机科普 + 短链接) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # 知识库 (扩充版)
    fusion_topics = [
        "托卡马克 (Tokamak) vs 仿星器", "惯性约束聚变 (ICF) 点火原理", 
        "氚增殖比 (TBR) 与燃料循环", "偏滤器 (Divertor) 的钨材料难题", 
        "第一壁 (First Wall) 的中子损伤", "H模式 (High-confinement Mode) 的发现", 
        "边缘局域模 (ELMs) 的抑制", "劳森判据 (Lawson Criterion) 详解", 
        "聚变Q值 (Q>1, Q>5, Q>10 的区别)", "高温超导 (REBCO)磁体技术", 
        "球形托卡马克 (ST) 的紧凑优势", "磁流体动力学 (MHD) 不稳定性", 
        "锯齿振荡 (Sawtooth Instability)", "中性束注入 (NBI) 加热原理", 
        "电子回旋共振加热 (ECRH)", "Helion 的脉冲磁聚变方案", 
        "Z-Pinch (Z箍缩) 技术复兴", "ITER 项目的最新进度",
        "聚变-裂变混合堆 (Fusion-Fission Hybrid)", "恒星核聚变 vs 人造太阳"
    ]
    today_topic = random.choice(fusion_topics)

    prompt = f"""
    你是一位**核聚变情报局的特工**。请生成 {today_str} 的日报。
    
    ---
    ### 1. 新闻数据 (News) - 必须关注时间
    {news_text}
    
    ### 2. 招聘数据 (Jobs)
    {internship_text}
    
    ### 3. 今日随机课题: {today_topic}
    
    ---
    ### 输出格式要求 (Markdown)
    
    # ⚛️ 聚变情报局 | {today_str}
    
    ## 📰 1. Fusion Frontiers (最新动态)
    *(指令：从新闻源中筛选 5 条最近 48 小时内的新闻。如果没有足够的新闻，就列出最近的一条并说明“今日暂无更多”。)*
    
    * **[新闻标题中文译名]**
        * 🕒 **Time**: [保留原文中的时间，如 2026-02-11 14:00]
        * 📍 **Who**: [机构/国家]
        * 🚀 **Significance**: [一句话点评行业意义]
        * 🔗 [点击阅读原文]({'{link}'}) <-- (保持格式：[点击阅读原文](URL))
    
    ## 🎯 2. Career Radar (招聘雷达)
    *(指令：如果是具体岗位，分析之。如果是 fallback 列表，直接列出并推荐访问。)*
    
    * 🏢 **[机构/公司名]**
        * 📝 **情报**: [岗位描述或公司简介]
        * 🔗 [点击直达官网]({'{link}'})
    
    ## 🧠 3. Deep Dive: {today_topic}
    
    * **今日词条：{today_topic}**
    * **🧐 硬核解析**：
        [200字专业解释]
    * **🍎 人话版**：
        [**必须使用生活中的比喻** (如做饭、交通、气球等)。150字]
    * **🤔 为什么重要？**：
        [一句话总结]
    
    ---
    *Generated by FusionBot · {today_topic}*
    """
    
    # 简单的重试逻辑
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
