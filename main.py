import os
import requests
import feedparser
import datetime
import time
import random
import hashlib
import re
import google.generativeai as genai
from bs4 import BeautifulSoup
from time import mktime
from urllib.parse import urljoin

# --- 配置部分 ---
SERVERCHAN_SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 

# 初始化 Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 使用 1.5-flash 保证速度和稳定性 (处理长文本能力强)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Gemini 配置出错: {e}")
else:
    print("警告: 未配置 GOOGLE_API_KEY")

# --- 辅助函数：通用网页抓取 ---
def fetch_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.text, resp.url
    except Exception:
        pass
    return None, None

# --- 1. 获取新闻 (保持不变) ---
def get_fusion_news():
    print("正在抓取新闻...")
    rss_url = "https://news.google.com/rss/search?q=Nuclear+Fusion+when:48h&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:6]: 
            published_time_str = "未知时间"
            if hasattr(entry, 'published_parsed'):
                dt = datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
                published_time_str = dt.strftime('%Y-%m-%d %H:%M')
            news_items.append(f"- {entry.title} (Time: {published_time_str}) [Link: {entry.link}]")
        return "\n".join(news_items) if news_items else "过去48小时无重大新闻。"
    except Exception as e:
        return f"新闻抓取失败: {e}"

# --- 2. 深度遍历职位 (Deep Crawler) ---
def search_jobs_deep_dive():
    print("🚀 启动二级深度爬虫 (Deep Traversal Mode)...")
    
    # 目标源：包含聚合页和具体的实验室页面
    # 策略：不仅看这个页面，还要尝试点开里面的理工科岗位
    targets = [
        {"name": "ITER Jobs", "url": "https://www.iter.org/jobs", "base": "https://www.iter.org"},
        {"name": "UKAEA (英国原子能局)", "url": "https://careers.ukaea.uk/vacancies/", "base": "https://careers.ukaea.uk"},
        {"name": "Princeton Plasma Physics Lab", "url": "https://www.pppl.gov/careers", "base": "https://www.pppl.gov"},
        {"name": "General Fusion", "url": "https://generalfusion.com/careers/", "base": "https://generalfusion.com"},
        {"name": "Tokamak Energy", "url": "https://tokamakenergy.co.uk/careers", "base": "https://tokamakenergy.co.uk"},
        {"name": "Commonwealth Fusion Systems", "url": "https://cfs.energy/careers", "base": "https://cfs.energy"},
        {"name": "US Fusion Energy", "url": "https://usfusionenergy.org/opportunities", "base": "https://usfusionenergy.org"}
    ]

    # 关键词过滤：只对包含这些词的链接感兴趣
    stem_keywords = ["physicist", "engineer", "scientist", "research", "plasma", "postdoc", "fellow", "technical", "diagnostics", "magnet", "cryogenic"]
    
    final_report_data = ""

    # 为了防止超时，我们随机选 3 个源进行深度扫描，而不是全部
    selected_targets = random.sample(targets, 3)

    for target in selected_targets:
        print(f"正在扫描: {target['name']} ...")
        html, final_url = fetch_url(target['url'])
        
        if not html:
            continue
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 提取页面上所有的链接
        links = soup.find_all('a', href=True)
        potential_jobs = []

        # 2. 筛选出可能是“具体岗位”的链接
        for link in links:
            text = link.get_text().lower()
            href = link['href']
            # 如果链接文本包含理工科关键词，且不是仅仅跳转回主页
            if any(k in text for k in stem_keywords) and len(text) > 10:
                full_link = urljoin(target.get('base', ''), href)
                potential_jobs.append({"title": link.get_text().strip(), "url": full_link})

        # 去重
        potential_jobs = [dict(t) for t in {tuple(d.items()) for d in potential_jobs}]

        # 3. 如果找到了具体岗位，随机选 1-2 个点进去看看 (二级遍历)
        if potential_jobs:
            print(f"  -> 发现 {len(potential_jobs)} 个潜在理工科岗位，正在深入分析其中 1-2 个...")
            jobs_to_visit = random.sample(potential_jobs, min(2, len(potential_jobs)))
            
            for job in jobs_to_visit:
                print(f"    -> 正在抓取详情: {job['title'][:30]}...")
                job_html, _ = fetch_url(job['url'])
                if job_html:
                    job_soup = BeautifulSoup(job_html, 'html.parser')
                    # 移除脚本，只留正文
                    for s in job_soup(["script", "style", "nav", "footer"]):
                        s.extract()
                    # 提取正文 (限制长度)
                    job_text = job_soup.get_text(separator='\n', strip=True)[:3500]
                    
                    final_report_data += f"\n=== 深度抓取: {target['name']} ===\n"
                    final_report_data += f"岗位名称: {job['title']}\n"
                    final_report_data += f"链接: {job['url']}\n"
                    final_report_data += f"详情页正文:\n{job_text}\n"
                    final_report_data += "--------------------------------\n"
                    time.sleep(1) # 礼貌延时
        else:
            # 如果没找到具体链接，就抓当前页面的大概
            print("  -> 未发现具体岗位链接，仅抓取概览。")
            text = soup.get_text(separator='\n', strip=True)[:2000]
            final_report_data += f"\n=== 概览: {target['name']} ===\n内容: {text}\n链接: {target['url']}\n----------------\n"

    if not final_report_data:
        return "本次深度扫描未获取有效数据，建议直接访问 ITER 或 FIA 官网。"
        
    return final_report_data

# --- 3. 生成日报 (Prompt 针对 JD/Quals 优化) ---
def generate_daily_report(news_text, job_data):
    print("正在生成 AI 日报...")
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # 【超级硬核知识库】拒绝宽泛，直击细节
    hardcore_topics = [
        "新经典撕裂模 (Neoclassical Tearing Modes, NTM)", "电阻壁模 (Resistive Wall Modes, RWM)",
        "刮削层 (SOL) 宽度与热流密度", "ELM 缓解线圈 (RMP Coils)",
        "钨铜偏滤器单体设计 (W/Cu Monoblock)", "氚增殖包层 (Tritium Breeding Blanket) 的热工水力",
        "高温超导磁体失超保护 (Quench Protection)", "REBCO 胶带的机械剥离强度",
        "中性束注入 (NBI) 的气体中和效率", "电子回旋共振加热 (ECRH) 的截止密度",
        "激光聚变中的瑞利-泰勒不稳定性 (Rayleigh-Taylor Instability)", "直接驱动 vs 间接驱动 (Direct vs Indirect Drive)",
        "激波点火 (Shock Ignition)", "磁化线性惯性聚变 (MagLIF)",
        "仿星器的准等角对称性 (Quasi-isodynamic symmetry)", "球形托卡马克的低环径比优势",
        "液态锂第一壁 (Liquid Lithium First Wall)", "聚变堆遥操作 (Remote Handling) 的抗辐照电子学",
        "DEMO 反应堆的停堆剂量率", "聚变-裂变混合堆的次临界安全性"
    ]
    
    # 基于日期的哈希选择
    date_hash = int(hashlib.sha256(today_str.encode('utf-8')).hexdigest(), 16)
    today_topic = hardcore_topics[date_hash % len(hardcore_topics)]

    prompt = f"""
    你是一位**核聚变领域的资深猎头和技术专家**。请根据以下数据生成 {today_str} 的情报日报。
    
    ---
    ### 1. 新闻 (News)
    {news_text}
    
    ### 2. 深度职位情报 (Deep Crawled Jobs)
    *(这是爬虫进入具体岗位详情页抓取的正文，可能包含杂乱信息。)*
    {job_data}
    
    ### 3. 今日硬核课题: {today_topic}
    
    ---
    ### 输出格式要求 (Markdown)
    
    # ⚛️ 聚变情报局 | {today_str}
    
    ## 📰 1. Fusion Frontiers
    *(精选 4-5 条新闻)*
    * **[中文标题]**
        * 🕒 **Time**: [时间]
        * 🚀 **Significance**: [点评]
        * 🔗 [原文]({'{link}'})
    
    ## 🎯 2. Career Radar (理工科深度分析)
    *(指令：请基于【深度抓取】的内容，提取出具体的岗位硬核信息。)*
    *(格式要求：必须提取 Job Description 和 Qualifications。如果正文里没有，请根据上下文合理推断。)*
    
    *(针对每一个抓取到的具体岗位)*
    * 🏢 **[机构名]** —— **[岗位名称]**
        * 📄 **Job Description (要做什么)**: 
            [详细概括：比如负责COMSOL仿真、真空室设计、等离子体诊断代码编写等]
        * 🎓 **Qualifications (要求什么)**: 
            [硬性指标：比如 PhD in Physics, Python/C++, 熟悉 Ansys, 3年真空经验等]
        * 🔗 [点击直达岗位]({'{link}'})

    *(如果抓取的是概览而非具体岗位，请简要总结机构招聘动向)*
    
    ## 🧠 3. Deep Dive: {today_topic}
    *(今天必须讲这个具体的细分领域，不要讲宽泛的概念！)*
    * **今日词条：{today_topic}**
    * **🧐 硬核物理/工程解析**：
        [250字。请使用专业术语，例如磁面、通量、沉积、截面等，展示深度。]
    * **🍎 也就是人话版**：
        [150字。用极其精妙的类比（如水流、橡胶筋、高压锅等）让非专业人士理解其物理图像。]
    * **🤔 核心难点/瓶颈**：
        [一句话指出目前阻碍这个技术实现的最大工程或物理障碍是什么？]
    
    ---
    *Generated by FusionBot · Data Source: Crawler Level-2*
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
    job_data = search_jobs_deep_dive() # 使用新的二级爬虫函数
    report = generate_daily_report(news, job_data)
    print(report)
    send_wechat(report)
