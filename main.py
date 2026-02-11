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
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# --- 1. 获取新闻 (带日期处理) ---
def get_fusion_news():
    print("正在抓取新闻...")
    # 关键词：Nuclear Fusion，时间：过去48小时 (when:48h)
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+when:48h&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:10]: # 限制前10条
            # 处理日期
            published_date = "未知日期"
            if hasattr(entry, 'published_parsed'):
                dt = datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
                published_date = dt.strftime('%Y-%m-%d')
            
            news_items.append(f"""
            - 标题: {entry.title}
            - 时间: {published_date}
            - 链接: {entry.link}
            - 来源: {entry.source.title if hasattr(entry, 'source') else 'Google News'}
            """)
        return "\n".join(news_items) if news_items else "过去48小时无重大新闻。"
    except Exception as e:
        return f"新闻抓取失败: {e}"

# --- 2. 广域搜索实习 ---
def search_internships():
    print("正在搜索实习岗位...")
    if not GOOGLESEARCHAPI_KEY or not GOOFLESEARCH_CX:
        return "错误：未配置 Google Search API Key 或 CX ID。"

    # 搜索关键词优化：强制包含 fusion，寻找 internship/thesis
    # 排除一些纯新闻网站，尽量找招聘页
    query = '"nuclear fusion" (internship OR thesis OR "summer student" OR "phd position") -news'
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': SEARCH_API_KEY,
        'cx': SEARCH_CX,
        'q': query,
        'dateRestrict': 'm3', # 限制最近3个月，保证新鲜度
        'num': 3 # 只取最相关的3个
    }

    try:
        response = requests.get(url, params=params).json()
        items = response.get('items', [])
        
        if not items:
            return "最近3个月未发现高相关度的实习信息。"

        processed_jobs = []
        for item in items:
            title = item.get('title')
            link = item.get('link')
            snippet = item.get('snippet')
            
            # 尝试抓取正文，增加AI分析的准确度
            page_content = snippet
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; FusionBot/1.0)'}
                # 设置短超时，防止卡住
                page_res = requests.get(link, headers=headers, timeout=5)
                if page_res.status_code == 200:
                    soup = BeautifulSoup(page_res.text, 'html.parser')
                    for script in soup(["script", "style", "nav", "footer"]):
                        script.extract()
                    # 只取前3000字符，避免Token超限
                    page_content = " ".join(soup.get_text().split())[:3000]
            except:
                pass # 抓取失败就用摘要
            
            processed_jobs.append(f"岗位标题: {title}\n链接: {link}\n网页内容: {page_content}\n----------------")
            
        return "\n".join(processed_jobs)
    except Exception as e:
        return f"实习搜索出错: {e}"

# --- 3. 生成深度日报 (Prompt 大升级) ---
def generate_daily_report(news_text, internship_text):
    print("正在生成 AI 日报...")
    
    # 获取今天的日期
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    prompt = f"""
    你是一位专业的核聚变科研助理，服务对象是物理/核工程专业的学生。请生成一份高质量的日报。
    日期：{today_str}

    ### 第一部分：聚变前沿动态 (Strict Format)
    请阅读以下新闻数据，挑选最有价值的 7-8 条。
    对于每一条，必须严格按照以下格式总结，中文格式输出（不要废话）：
    
    News Data:
    {news_text}

    **输出格式要求：**
    📅 **[日期] 新闻标题**
    * **Who/Where**: [某机构/某人/某地]
    * **What**: [核心事件简述]
    * **Significance**: [标志着什么？对行业的具体意义？]
    * 🔗 [链接]

    ---

    ### 第二部分：岗位雷达
    请阅读以下抓取到的岗位信息，提炼最核心的干货。
    
    Internship Data:
    {internship_text}

    **输出格式要求（针对每一个岗位）：**
    🏢 **[推测的机构名称] - [岗位名称]**
    * **📝 岗位描述**: [做什么研究？参与什么项目？]
    * **🛠️ 职责**: [具体Daily work是什么]
    * **🎓 要求**: [专业背景/技能栈/学位要求]
    * 🔗 [申请链接]

    ---

    ### 第三部分：每日硬核科普 (Deep Dive)
    **目标受众**：具备等离子体物理或核工程基础的本科/研究生（非普通大众）。
    **要求**：
    1.  拒绝浅显的阐述，可以深入讲解。
    2.  选取一个**具体的、进阶的**知识点。例如可以包括但不限于：磁流体动力学(MHD)不稳定性（如锯齿振荡、ELMs）、托卡马克偏滤器材料挑战、氚增殖比(TBR)的计算、仿星器的线圈优化逻辑、惯性约束的瑞利-泰勒不稳定性等，对部分抽象知识点可以辅佐现实举例解释。
    3.  字数 250-300 字，逻辑严密，可以包含必要的物理参数或工程指标。
    4.  最后附上一句简短的点评或思考。

    请直接输出 Markdown 格式。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 生成报告失败: {e}"

# --- 4. 推送 ---
def send_wechat(content):
    print("正在推送...")
    if not SERVERCHAN_SENDKEY:
        print("未配置 Server酱 Key，跳过推送")
        return

    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    data = {
        "title": f"⚛️ 核聚变科研日报 {datetime.date.today()}",
        "desp": content 
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    news = get_fusion_news()
    internships = search_internships()
    report = generate_daily_report(news, internships)
    
    print("--- DEBUG: 生成的内容预览 ---")
    print(report)
    print("--- DEBUG END ---")
    
    send_wechat(report)
