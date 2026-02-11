import os
import requests
import feedparser
import datetime
import time
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

# --- 1. 获取新闻 ---
def get_fusion_news():
    print("正在抓取新闻...")
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+when:48h&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:8]:
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
    if not SEARCH_API_KEY or not SEARCH_CX:
        return "错误：代码无法读取到 Search Key。"

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

# --- 3. 生成日报 (Prompts 深度优化版) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # 这是一个精心设计的系统级 Prompt
    prompt = f"""
    你是一位**深耕核聚变领域的资深科研助理**，同时也是一位文笔幽默、逻辑严密的科技博主。
    你的目标受众是：物理系学生、核工专业研究生以及聚变技术发烧友。
    
    请根据以下输入数据，为我生成一份 {today_str} 的《核聚变情报局·每日简报》。
    
    ---
    
    ### 输入数据区
    **1. 新闻源数据 (News Data):**
    {news_text}
    
    **2. 实习岗位抓取数据 (Internship Data):**
    {internship_text}
    
    ---
    
    ### 输出要求 (请严格按照以下 Markdown 格式输出)
    
    # 聚变情报局 | {today_str}
    > "在这里，我们离人造太阳更近一步。"
    
    ## 📰 1. Fusion Frontiers
    *(指令：从新闻源中筛选出真正有价值的 7-8 条新闻。剔除重复或无意义的营销文。)*
    *(格式：每一条新闻请按以下结构撰写，务必用中文)*
    
    * **[新闻标题 (中文翻译)]**
        * 📍 **Who/Where**: [机构或地点，如 ITER, CFS, 麻省理工]
        * 💡 **Core**: [用一句话概括发生了什么核心事件]
        * 🚀 **Significance**: [**重点！** 深度解析这条新闻意味着什么？是工程突破？理论验证？还是资金到位？请用专业的眼光点评其对行业的价值]
        * 🔗 [原文链接]
    
    ## 🎯 2. Career Radar
    *(指令：仔细分析抓取到的岗位信息。如果没有实质性的岗位，请分析一下为什么，是没有抓取到还是没有。)*
    *(格式：如果有岗位，请按以下结构)*
    
    * 🏢 **[推测出的机构名称]** —— **[岗位名称]**
        * 📝 **任务书**: [简单概括要干什么活，比如仿真模拟、材料测试、还是洗试管？]
        * 🎓 **通缉令**: [他们想要什么背景的人？PhD? Python高手? 还是拥有极强抗压能力？]
        * 🔗 [申请传送门](链接)
    
    ## 🧠 3. Deep Dive
    *(指令：这是本文的灵魂。请利用你作为 AI 的庞大知识库，讲解一个**进阶**的核聚变知识点。)*
    *(选题建议包括但不限于：MHD不稳定性、托卡马克偏滤器热负荷、仿星器线圈优化、球形托卡马克优势、惯性约束的点火条件、氚增殖比 TBR 等。)*
    
    * **今日词条：[知识点名称]**
    * **🧐 硬核原理解析**：
        [用专业术语准确描述其物理机制，约 200 字。展示你的专业性]
    * **🍎 也就是人话版**：
        [**重点！** 使用一个极其通俗、生活化的比喻来解释上面的概念。比如把等离子体比作果冻，把磁场比作笼子等。让大一新生也能听懂。约 150 字]
    * **🤔 为什么它很重要？**：
        [一句话点出它在聚变发电道路上的地位]
    
    ---
    *保持好奇，探索未来*
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

    # 标题加上 Emoji 让通知栏更好看
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    data = {
        "title": f"⚛️ {datetime.date.today()} 聚变情报局日报", 
        "desp": content
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    news = get_fusion_news()
    internships = search_internships()
    report = generate_daily_report(news, internships)
    print(report) # 在日志里打印预览
    send_wechat(report)
