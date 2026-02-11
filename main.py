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
# 【新增】引入 DuckDuckGo 搜索库
from duckduckgo_search import DDGS

# --- 配置部分 ---
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 
# 注意：Google Search 的 Key 和 CX 现在已经不需要了，代码里会自动忽略它们

# 初始化 Gemini (建议使用 1.5-flash 以获得最佳稳定性)
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Gemini 配置出错: {e}")
else:
    print("警告: 未配置 GOOGLE_API_KEY")

# --- 1. 获取新闻 (保持 48h 限制) ---
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

# --- 2. 全网广域搜索实习 (DuckDuckGo 版本 - 无需配置) ---
def search_internships():
    print("正在使用 DuckDuckGo 广域搜索实习岗位...")
    
    # 搜索词：核聚变/等离子体 + 实习/工作 -新闻
    # 移除了 site 限制，让它真正跑全网
    query = '(nuclear fusion OR plasma physics) (internship OR "summer student" OR "early career" OR "thesis position") -news'
    
    try:
        # 使用 DuckDuckGo 搜索，获取前 5 条结果
        # max_results 控制返回数量
        results = DDGS().text(query, max_results=5)
        
        if not results:
            return "DuckDuckGo 暂未返回搜索结果，建议手动浏览 LinkedIn。"

        processed_jobs = []
        for item in results:
            # DuckDuckGo 返回的字段通常是 title, href, body
            title = item.get('title', 'No Title')
            link = item.get('href', '#')
            snippet = item.get('body', 'No snippet')
            
            processed_jobs.append(f"Search Result: {title}\nLink: {link}\nSummary: {snippet}\n---")
            
        print(f"成功抓取到 {len(processed_jobs)} 条搜索结果")
        return "\n".join(processed_jobs)

    except Exception as e:
        print(f"DuckDuckGo 搜索异常: {e}")
        # 如果出错，为了防止报错，返回一个提示
        return f"搜索环节暂时不可用: {e}"

# --- 3. 生成日报 (每日一题不重复 + 灵活岗位分析) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # 【解决方案】超级扩充的知识库 (50+ 词条)
    fusion_topics = [
        # 基础物理
        "劳森判据 (Lawson Criterion)", "库仑碰撞与截面", "Q值 (Energy Gain)", "三重积 (Triple Product)",
        "磁流体动力学 (MHD) 基础", "阿尔芬波 (Alfven Waves)", "朗缪尔波 (Langmuir Waves)",
        # 装置类型
        "托卡马克 (Tokamak) 原理", "仿星器 (Stellarator) 的线圈设计", "球形托卡马克 (ST)", 
        "反场箍缩 (RFP)", "磁镜 (Magnetic Mirror)", "Z-Pinch (Z箍缩)", "惯性约束聚变 (ICF)",
        # 工程挑战
        "第一壁材料 (First Wall)", "钨 (Tungsten) 的应用与挑战", "铍 (Beryllium) 的作用",
        "偏滤器 (Divertor) 热负荷管理", "氚增殖比 (Tritium Breeding Ratio)", "锂铅包层 (Li-Pb Blanket)",
        "中子辐照损伤 (DPA)", "遥操作维护 (Remote Handling)", "低温泵 (Cryopump)",
        # 加热与驱动
        "中性束注入 (NBI)", "离子回旋共振加热 (ICRH)", "电子回旋共振加热 (ECRH)", "低杂波驱动 (LHCD)",
        # 等离子体物理现象
        "H模式 (High-confinement Mode)", "边缘局域模 (ELMs)", "锯齿振荡 (Sawtooth)", 
        "新经典输运 (Neoclassical Transport)", "逃逸电子 (Runaway Electrons)", "磁岛 (Magnetic Islands)",
        "刮削层 (SOL) 物理", "等离子体破裂 (Disruption)",
        # 著名项目与公司
        "ITER 的组装进度", "CFS 与 SPARC 装置", "Helion 的脉冲磁聚变", 
        "General Fusion 的磁化靶聚变", "中国环流器三号 (HL-3)", "EAST (东方超环)",
        "NIF (国家点火装置)", "JET 的最后实验", "KSTAR (韩国人造太阳)"
    ]
    
    # 【核心逻辑】基于日期的伪随机选择
    date_hash = int(hashlib.sha256(today_str.encode('utf-8')).hexdigest(), 16)
    today_topic_index = date_hash % len(fusion_topics)
    today_topic = fusion_topics[today_topic_index]

    prompt = f"""
    你是一位**核聚变情报局特工**。请生成 {today_str} 的日报。
    
    ---
    ### 1. 新闻数据 (News)
    {news_text}
    
    ### 2. 广域搜索结果 (From DuckDuckGo)
    *(这是全网搜索 'fusion internship/job' 的结果)*
    {internship_text}
    
    ### 3. 今日锁定课题: {today_topic}
    *(根据日期锁定，不可更改)*
    
    ---
    ### 输出格式要求 (Markdown)
    
    # ⚛️ 聚变情报局 | {today_str}
    
    ## 📰 1. Fusion Frontiers (最新动态)
    *(筛选 5 条最近 48h 的新闻)*
    * **[中文标题]**
        * 🕒 **Time**: [原文时间]
        * 📍 **Who**: [机构/国家]
        * 🚀 **Significance**: [点评]
        * 🔗 [点击阅读原文]({'{link}'}) 
    
    ## 🎯 2. Career Radar (全网扫描)
    *(指令：请分析上面的搜索结果。总结出职位描述、岗位职责、岗位要求)*
    *(如果结果中有明确的岗位/实习页，请列出。如果结果看起来是招聘聚合网站（如LinkedIn, Glassdoor）或泛泛的页面，也请列出来并建议用户去看看。)*
    
    * 🔍 **[来源/标题]**
        * 📝 **情报**: [这个链接里大概有什么？是具体岗位还是招聘主页？]
        * 🔗 [点击直达]({'{link}'})
    
    ## 🧠 3. Deep Dive: {today_topic}
    *(今天必须讲这个！)*
    * **今日词条：{today_topic}**
    * **🧐 硬核解析**：
        [200字专业解释]
    * **🍎 人话版**：
        [**必须使用生活中的比喻** (如做饭、交通、气球等)。150字]
    * **🤔 为什么重要？**：
        [一句话总结]
    
    ---
    *Generated by FusionBot · Topic Index: {today_topic_index}*
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
