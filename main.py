import os
import requests
import feedparser
import datetime
import time
import random
import hashlib
import google.generativeai as genai
from time import mktime
# 【核心库】引入 DuckDuckGo，无需 API Key 即可全网搜索
from duckduckgo_search import DDGS

# --- 配置部分 ---
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 

# 初始化 Gemini
# 使用 1.5-flash 以保证最大稳定性（2.0 预览版目前容易限流）
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
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

# --- 2. 智能全网职位挖掘 (融合了 Smart Search + DuckDuckGo) ---
def search_internships():
    print("正在智能挖掘职位信息...")
    
    # 【策略升级】定义一组“猎头级”搜索指令
    # 每次运行脚本时，随机从这里面选一个去搜，这样能保证每天看到的岗位来源不同
    # 既包含通用搜索，也包含针对特定大厂或特定语气的搜索
    search_strategies = [
        # 策略A: 寻找带有“正在招聘”字眼的页面 (最精准)
        '(nuclear fusion OR plasma physics) "we are hiring" -news',
        # 策略B: 寻找具体的职位空缺公告
        '(nuclear fusion OR plasma physics) "job opening" -linkedin -indeed',
        # 策略C: 针对实习和早期职业
        '"fusion energy" ("internship" OR "summer student" OR "thesis") 2025 2026',
        # 策略D: 定点爆破 ITER 和 CFS (两个最大的坑)
        'ITER Organization "jobs" OR "vacancies"',
        'Commonwealth Fusion Systems "careers"',
        # 策略E: 宽泛的职位搜索
        'nuclear fusion engineer jobs remote or onsite'
    ]
    
    # 随机选择一个策略
    query = random.choice(search_strategies)
    print(f"本次雷达扫描指令: {query}")

    try:
        # 使用 DuckDuckGo 搜索，获取前 8 条结果 (给 AI 足够的素材)
        results = DDGS().text(query, max_results=8)
        
        if not results:
            return f"DuckDuckGo 本次扫描 ({query}) 未返回结果，建议手动访问 LinkedIn。"

        processed_jobs = []
        for item in results:
            title = item.get('title', 'No Title')
            link = item.get('href', '#')
            snippet = item.get('body', 'No snippet')
            
            # 简单的关键词过滤，去掉显而易见的广告
            if "top 10" in title.lower() or "best colleges" in title.lower():
                continue
                
            processed_jobs.append(f"Source: {title}\nLink: {link}\nSnippet: {snippet}\n---")
            
        print(f"成功抓取到 {len(processed_jobs)} 条潜在岗位线索")
        return "\n".join(processed_jobs)

    except Exception as e:
        print(f"搜索异常: {e}")
        return f"职位扫描模块暂时休眠: {e}"

# --- 3. 生成日报 (详细 Prompt + 每日一题) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # 【超级扩充知识库】确保每天不重样 (50+ 词条)
    fusion_topics = [
        "劳森判据 (Lawson Criterion)", "库仑碰撞与截面", "Q值 (Energy Gain)", "三重积",
        "磁流体动力学 (MHD)", "阿尔芬波", "朗缪尔波",
        "托卡马克原理", "仿星器线圈设计", "球形托卡马克 (ST)", 
        "反场箍缩 (RFP)", "磁镜", "Z-Pinch", "惯性约束聚变 (ICF) 点火",
        "第一壁材料", "钨 (Tungsten) 的应用", "铍 (Beryllium)",
        "偏滤器 (Divertor) 热负荷", "氚增殖比 (TBR)", "锂铅包层",
        "中子辐照损伤 (DPA)", "遥操作维护 (Remote Handling)", "低温泵技术",
        "中性束注入 (NBI)", "离子回旋共振加热 (ICRH)", "电子回旋加热 (ECRH)", "低杂波驱动",
        "H模式 (High-confinement Mode)", "边缘局域模 (ELMs)", "锯齿振荡", 
        "新经典输运", "逃逸电子", "磁岛效应", "等离子体破裂 (Disruption)",
        "ITER 组装进度", "CFS SPARC", "Helion 脉冲磁聚变", 
        "General Fusion", "中国环流器三号 (HL-3)", "EAST", "NIF 激光聚变"
    ]
    
    # 基于日期的哈希选择，保证全天一致，隔天变样
    date_hash = int(hashlib.sha256(today_str.encode('utf-8')).hexdigest(), 16)
    today_topic_index = date_hash % len(fusion_topics)
    today_topic = fusion_topics[today_topic_index]

    prompt = f"""
    你是一位**核聚变情报局的特工**。请生成 {today_str} 的日报。
    
    ---
    ### 1. 新闻数据 (News)
    {news_text}
    
    ### 2. 招聘线索 (Raw Job Search Data)
    *(这是通过全网搜索关键词抓取到的结果，包含标题和摘要)*
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
    
    ## 🎯 2. Career Radar (智能猎头分析)
    *(指令：请扮演一位专业的猎头，仔细分析上面的“招聘线索”。)*
    *(不要只复制粘贴！请阅读搜索结果的Snippet(摘要)，尝试推断出：这是哪个机构？他们在找什么样的人？)*
    *(如果搜索结果显示的是“We are hiring”的公告页，请重点推荐。)*
    
    * 🔍 **[职位名称/机构名称]**
        * 📝 **岗位情报**: [根据摘要推断：这是全职/实习？涉及物理/工程/仿真？]
        * 🛠️ **关键要求**: [如果摘要里提到了Python, PhD, CAD等关键词，请列出；如果没有，写“建议点击详情查看”]
        * 🔗 [点击直达]({'{link}'})
    
    ## 🧠 3. Deep Dive: {today_topic}
    *(今天必须讲这个！)*
    * **今日词条：{today_topic}**
    * **🧐 硬核解析**：
        [200字专业解释，可以使用物理术语]
    * **🍎 人话版**：
        [**必须使用生活中的比喻** (如做饭、交通、气球等) 来解释上面的概念，让小白也能懂。150字]
    * **🤔 为什么重要？**：
        [一句话总结它在聚变发电中的地位]
    
    ---
    *Generated by FusionBot · Topic Index: {today_topic_index}*
    """
    
    # 重试机制
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
