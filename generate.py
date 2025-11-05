import os
import glob
import markdown
import re
from typing import Dict, List, Tuple, Optional

# -------------------------- 配置项 --------------------------
INPUT_DIR = "./docs"  # MD 文件根目录（年份文件夹 → index.md + 子文件夹）
OUTPUT_HTML = "./index.html"  # 生成的 HTML 输出路径
# 匹配 Markdown 列表项格式：- [显示文本](子文件夹名称)
ORDER_LIST_PATTERN = re.compile(r'^\s*-\s*\[(.*?)\]\((.*?)\)\s*$')
# -----------------------------------------------------------------------------

def get_year_folders(input_dir: str) -> List[str]:
    """获取所有年份文件夹（按年份降序排序）"""
    year_folders = []
    for name in os.listdir(input_dir):
        folder_path = os.path.join(input_dir, name)
        if os.path.isdir(folder_path) and name.isdigit():  # 仅保留数字命名的年份文件夹
            year_folders.append(folder_path)
    # 按年份降序排序（最新年份在前）
    return sorted(year_folders, reverse=True, key=lambda x: os.path.basename(x))

def parse_year_index(year_folder: str) -> Tuple[str, List[str]]:
    """
    解析年份文件夹下的 index.md：
    - 一级标题作为标签页名称
    - 列表项（- [xxx](子文件夹名)）作为卡片顺序
    返回：(标签页名称, 子文件夹顺序列表)
    """
    index_md_path = os.path.join(year_folder, "index.md")
    year_name = os.path.basename(year_folder)
    default_tab_name = year_name  
    default_order = []  # 默认顺序（空，后续按子文件夹名称排序）
    
    # 如果没有 index.md，返回默认值
    if not os.path.exists(index_md_path):
        print(f"提示：年份文件夹 {year_name} 下未找到 index.md，使用默认标签页名称（{default_tab_name}）和排序")
        return default_tab_name, default_order
    
    try:
        with open(index_md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        tab_name = default_tab_name  # 标签页名称（默认值）
        subfolder_order = []  # 子文件夹顺序
        
        # 解析一级标题（第一个 # 开头的行）
        title_found = False
        for line in lines:
            line_stripped = line.strip()
            if not title_found and line_stripped.startswith("# "):
                tab_name = line_stripped.lstrip("# ").strip()
                title_found = True
                continue  # 标题行处理完，后续找列表项
            
            # 解析列表项（- [xxx](子文件夹名)）
            match = ORDER_LIST_PATTERN.match(line_stripped)
            if match:
                subfolder_name = match.group(2).strip()  # 提取子文件夹名称（链接目标）
                if subfolder_name:
                    subfolder_order.append(subfolder_name)
        
        # 去重（保留第一次出现的顺序）
        subfolder_order = list(dict.fromkeys(subfolder_order))
        print(f"成功解析 {year_name}/index.md：标签页名称='{tab_name}'，卡片顺序={subfolder_order}")
        return tab_name, subfolder_order
    
    except Exception as e:
        print(f"警告：解析 {year_name}/index.md 失败 - {str(e)}，使用默认标签页名称（{default_tab_name}）和排序")
        return default_tab_name, default_order

def parse_md_file(md_path: str) -> Tuple[str, str]:
    """解析 MD 文件：提取一级标题和 HTML 内容（兼容所有环境）"""
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 提取一级标题（第一个 # 开头的行）
    title = "未命名卡片"
    content_lines = []
    title_found = False
    for line in lines:
        line_stripped = line.strip()
        if not title_found and line_stripped.startswith("# "):
            title = line_stripped.lstrip("# ").strip()
            title_found = True
            continue  # 跳过标题行，不加入内容
        content_lines.append(line)
    
    # 仅保留 2 个最核心的非原生扩展（兼容所有 markdown 版本）
    md_extensions = [
        "fenced_code",
        "tables"
    ]
    content_html = markdown.markdown(
        "".join(content_lines),
        extensions=md_extensions
    )
    return title, content_html

def generate_html(year_data: Dict[str, Dict]) -> str:
    """
    生成完整的 HTML 内容：
    year_data 结构：{
        "年份文件夹路径": {
            "tab_name": "标签页名称",
            "subfolder_order": ["子文件夹1", "子文件夹2", ...],
            "cards": [(卡片标题, 卡片内容), ...]
        }
    }
    """
    # 提取所有年份（按降序排序后的顺序）
    year_folders = sorted(year_data.keys(), reverse=True, key=lambda x: os.path.basename(x))
    if not year_folders:
        raise ValueError("未找到任何有效年份文件夹，请检查 INPUT_DIR 配置")
    
    # 标签页文字放大2倍（text-lg → text-2xl），保持加粗和过渡效果
    tab_buttons = []
    for year_folder in year_folders:
        year_info = year_data[year_folder]
        year_name = os.path.basename(year_folder)
        active_class = "tab-active" if year_folder == year_folders[0] else ""
        # 为2025年标签添加特殊类名
        year_specific_class = "year-default" if year_name == "2025" else ""
        tab_buttons.append(f'''
            <button class="tab-btn {active_class} {year_specific_class} py-4 px-8 text-gray-700 hover:text-primary transition-all font-bold text-2xl" data-year="{year_name}">
                {year_info["tab_name"]}
            </button>
        ''')
    tab_buttons_html = "\n".join(tab_buttons)
    
    # 生成标签页内容（按解析后的顺序排列卡片）
    tab_contents = []
    for year_folder in year_folders:
        year_info = year_data[year_folder]
        year_name = os.path.basename(year_folder)
        cards = year_info["cards"]
        active_class = "" if year_folder == year_folders[0] else "hidden"
        
        # 生成卡片 HTML（按顺序排列）
        card_htmls = []
        for card_title, card_content in cards:
            card_htmls.append(f'''
                <div class="bg-white rounded-lg shadow-sm border border-gray-100 p-6 card-hover">
                    <div class="mb-4">
                        <h3 class="text-2xl font-bold text-primary">{card_title}</h3>
                    </div>
                    <div class="card-content text-gray-700 text-lg leading-relaxed">
                        {card_content}
                    </div>
                </div>
            ''')
        
        # 处理无卡片的情况（添加默认提示）
        if not card_htmls:
            card_htmls.append(f'''
                <div class="bg-white rounded-lg shadow-sm border border-gray-100 p-8 text-center text-gray-500">
                    <i class="fa fa-calendar-o text-4xl mb-3"></i>
                    <p class="text-lg">{year_name}年 内容暂未更新</p>
                </div>
            ''')
        
        # 生成标签页内容容器
        tab_contents.append(f'''
            <div class="tab-content {active_class}" data-year="{year_name}">
                <div class="grid grid-cols-1 gap-8">
                    {"".join(card_htmls)}
                </div>
            </div>
        ''')
    tab_contents_html = "\n".join(tab_contents)
    
    # HTML 模板（同步最新样式修改）
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="msvalidate.01" content="B936D7B6A9AB03565B05356475E91930" />
    <title>GTOC Forum</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" rel="stylesheet">
    <!-- 配置Tailwind自定义主题 -->
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '#1a365d',
                        secondary: '#4299e1',
                        accent: '#ed8936',
                        dark: '#1a202c',
                    }},
                    fontFamily: {{
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                    }},
                }},
            }}
        }}
    </script>
    <style type="text/tailwindcss">
        @layer utilities {{
            .content-auto {{
                content-visibility: auto;
            }}
            .text-shadow {{
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}
            .text-shadow-lg {{
                text-shadow: 0 4px 8px rgba(0,0,0,0.5);
            }}
            .bg-blur {{
                backdrop-filter: blur(8px);
            }}
            .tab-active {{
                color: theme('colors.primary');
                /* 激活状态下划线样式 */
                text-decoration: underline;
                text-underline-offset: 6px;
                text-decoration-thickness: 3px;
                text-decoration-color: theme('colors.primary');
                font-weight: 700;
            }}
            /* 标签页按钮样式：默认无下划线，hover 显示下划线 */
            .tab-btn {{
                white-space: nowrap; /* 防止文字换行 */
                transition: all 0.3s ease;
            }}
            .tab-btn:hover:not(.tab-active) {{
                text-decoration: underline;
                text-underline-offset: 6px;
                text-decoration-thickness: 2px;
                text-decoration-color: theme('colors.primary/60');
            }}
            /* 2025年标签页特定样式，确保居中显示 */
            .year-default {{
                display: inline-block;
                position: relative;
            }}
            .card-hover {{
                transition: all 0.3s ease;
            }}
            .card-hover:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
            }}
            /* -------------- Markdown 样式优化 -------------- */
            .card-content ul {{
                list-style-type: disc;
                margin-left: 1.75rem;
                margin-bottom: 1.25rem;
                line-height: 1.9;
            }}
            .card-content ul ul {{
                list-style-type: circle;
                margin-left: 2rem;
                margin-top: 0.5rem;
            }}
            .card-content ol {{
                list-style-type: decimal;
                margin-left: 1.75rem;
                margin-bottom: 1.25rem;
                line-height: 1.9;
            }}
            .card-content li {{
                margin-bottom: 0.5rem;
            }}
            .card-content a {{
                color: #2563eb; /* 蓝色（可调整为 theme('colors.secondary')） */
                font-weight: 500;
                transition: all 0.2s ease;
            }}
            .card-content a:hover {{
                color: #1d4ed8; /* hover 加深蓝色 */
                text-decoration: underline;
            }}
            .card-content strong {{
                color: #1a365d;
                font-weight: 600;
            }}
            .card-content em {{
                color: #4b5563;
                font-style: italic;
            }}
            .card-content pre {{
                background-color: #f3f4f6;
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 1rem 0;
                overflow-x: auto;
                font-family: 'Menlo', 'Monaco', monospace;
                font-size: 0.95rem;
            }}
            .card-content code {{
                background-color: #f3f4f6;
                padding: 0.2rem 0.4rem;
                border-radius: 0.3rem;
                font-family: 'Menlo', 'Monaco', monospace;
                font-size: 0.95rem;
            }}
            .card-content table {{
                width: 100%;
                border-collapse: collapse;
                margin: 1.25rem 0;
            }}
            .card-content th, .card-content td {{
                border: 1px solid #e5e7eb;
                padding: 0.75rem 1rem;
                text-align: left;
            }}
            .card-content th {{
                background-color: #f9fafb;
                font-weight: 600;
            }}
            .card-content img {{
                max-width: 100%;
                height: auto;
                border-radius: 0.5rem;
                margin: 1.25rem 0;
            }}
            .card-content blockquote {{
                border-left: 4px solid #4299e1;
                padding: 0.75rem 1rem;
                background-color: #f0f8ff;
                margin: 1.25rem 0;
                border-radius: 0 0.3rem 0.3rem 0;
            }}
            /* 页脚强制显示样式 */
            .footer-force-visible {{
                display: block !important;
                position: relative !important;
                z-index: 999 !important;
                opacity: 1 !important;
                visibility: visible !important;
            }}
        }}
    </style>
</head>
<!-- 移除body的overflow-x-hidden，避免影响垂直滚动 -->
<body class="font-sans text-gray-800">
    <!-- 全屏图片区域 -->
    <header class="relative h-screen w-full overflow-hidden">
        <div class="absolute inset-0 z-0">
            <img src="https://github.com/gevico/gtoc-forum/blob/main/asserts/head.png?raw=true" alt="背景图片"
                class="w-full h-full object-cover">
            <div class="absolute inset-0 bg-black/40"></div>
        </div>
        <!-- 标题区域 -->
        <div class="absolute inset-0 flex items-center justify-center z-10 text-center px-4">
            <div class="max-w-3xl mx-auto">
                <h1 class="text-[clamp(2.8rem,8vw,4.5rem)] font-bold text-white text-shadow-lg mb-6 leading-tight">
                    GTOC Forum 2025
                </h1>
                <p class="text-[clamp(1rem,3vw,1.25rem)] text-white text-shadow max-w-2xl mx-auto mb-8">
                    格维开源社区 - 线上技术分享会
                </p>
            </div>
        </div>
        <!-- 向下滚动指示 -->
        <div class="absolute bottom-8 left-0 right-0 z-10 animate-bounce px-4">
            <div class="max-w-4xl mx-auto">
                <a href="#forum-archive" class="text-white text-3xl opacity-80 hover:opacity-100 transition-opacity flex justify-center">
                    <i class="fa fa-chevron-down"></i>
                </a>
            </div>
        </div>
    </header>
    <!-- 缩小标签页和head的距离（py-4） -->
    <section id="forum-archive" class="py-4 bg-gray-50">
        <div class="container mx-auto px-4">
            <!-- 标签页导航容器 -->
            <div class="max-w-4xl mx-auto mb-6">
                <div class="flex flex-wrap border-b border-gray-200 justify-center">
                    {tab_buttons_html}
                </div>
            </div>

            <!-- 标签页内容 -->
            <div class="max-w-4xl mx-auto mb-8">
                {tab_contents_html}
            </div>

            <!-- 说明文字（弱化样式，移到最后） -->
            <div class="max-w-4xl mx-auto mb-12">
                <div class="bg-gray-100 p-5 rounded-lg border border-gray-200 text-justify text-gray-600 text-base leading-relaxed">
                    GTOC Forum 是由社区成员牵头发起的线上技术交流会议，不定期开展。社区成员如果有感兴趣或者想要申报议题，可以通过<a
                        href="https://github.com/gevico/gtoc-forum/issues" target="_blank" rel="noopener noreferrer"
                        class="text-gray-700 hover:text-primary hover:underline font-medium"> Github 仓库的 issues </a>页面发起讨论和申请。
                </div>
            </div>
        </div>
    </section>
    <!-- 页脚优化：字体缩小2倍，图标间距缩小 -->
    <footer class="bg-primary text-white py-12 footer-force-visible border-t-2 border-white/20">
        <div class="container mx-auto px-4">
            <div class="text-center">
                <!-- 字体缩小2倍：text-2xl → text-base -->
                <p class="mb-6 text-base font-medium text-white/90">© {os.path.basename(year_folders[0])} 格维开源社区. 保留所有权利.</p>
                <!-- 间距缩小：gap-6 md:gap-10 → gap-4 md:gap-6；字体缩小：text-2xl → text-base，图标：text-3xl → text-xl -->
                <div class="flex flex-wrap justify-center gap-4 md:gap-6">
                    <a href="https://github.com/gevico/gtoc-forum" target="_blank" rel="noopener noreferrer"
                        class="flex items-center text-white/90 hover:text-white transition-colors text-base p-1">
                        <i class="fa fa-github mr-2 text-xl"></i>
                        <span>Github</span>
                    </a>
                    <a href="https://space.bilibili.com/483048140/lists/6433029?type=season" target="_blank"
                        rel="noopener noreferrer" class="flex items-center text-white/90 hover:text-white transition-colors text-base p-1">
                        <i class="fa fa-youtube-play mr-2 text-xl"></i>
                        <span>Bilibili</span>
                    </a>
                    <a href="https://qm.qq.com/q/jIXYyZkQqQ" target="_blank" rel="noopener noreferrer"
                        class="flex items-center text-white/90 hover:text-white transition-colors text-base p-1">
                        <i class="fa fa-qq mr-2 text-xl"></i>
                        <span>QQ群</span>
                    </a>
                    <a href="https://t.me/gevico_channel" target="_blank" rel="noopener noreferrer"
                        class="flex items-center text-white/90 hover:text-white transition-colors text-base p-1">
                        <i class="fa fa-telegram mr-2 text-xl"></i>
                        <span>Telegram</span>
                    </a>
                </div>
            </div>
        </div>
    </footer>
    <!-- JavaScript -->
    <script>
        // 标签页切换功能
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        tabBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                const targetYear = btn.getAttribute('data-year');
                // 切换标签激活状态
                tabBtns.forEach(b => b.classList.remove('tab-active'));
                btn.classList.add('tab-active');
                // 切换内容显示
                tabContents.forEach(content => {{
                    if (content.getAttribute('data-year') === targetYear) {{
                        content.classList.remove('hidden');
                    }} else {{
                        content.classList.add('hidden');
                    }}
                }});
            }});
        }});
        // 平滑滚动
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                document.querySelector(this.getAttribute('href'))?.scrollIntoView({{
                    behavior: 'smooth'
                }});
            }});
        }});
        // 确保页面加载完成后页脚可见
        window.addEventListener('load', function() {{
            const footer = document.querySelector('footer');
            if (footer) {{
                footer.style.display = 'block';
                footer.style.opacity = '1';
                // 强制刷新布局
                footer.offsetHeight;
            }}
        }});
    </script>
</body>
</html>'''
    return html_template

def main():
    # 1. 检查输入目录是否存在
    if not os.path.exists(INPUT_DIR):
        print(f"错误：输入目录 {INPUT_DIR} 不存在，请创建后重试")
        return
    
    # 2. 获取所有年份文件夹（完整路径）
    year_folders = get_year_folders(INPUT_DIR)
    if not year_folders:
        print(f"警告：输入目录 {INPUT_DIR} 下未找到任何数字命名的年份文件夹（如 2025）")
        return
    
    # 3. 解析每个年份的 index.md 和子文件夹
    year_data = {}  # 存储每个年份的所有信息
    for year_folder in year_folders:
        year_name = os.path.basename(year_folder)
        year_data[year_folder] = {
            "tab_name": "",       # 标签页名称
            "subfolder_order": [],# 子文件夹顺序
            "cards": []           # 卡片数据 [(标题, 内容), ...]
        }
        
        # 3.1 解析年份文件夹下的 index.md（获取标签页名称和子文件夹顺序）
        tab_name, subfolder_order = parse_year_index(year_folder)
        year_data[year_folder]["tab_name"] = tab_name
        year_data[year_folder]["subfolder_order"] = subfolder_order
        
        # 3.2 获取年份文件夹下的所有有效子文件夹（非隐藏）
        all_subfolders = []
        for item in os.scandir(year_folder):
            if item.is_dir() and not item.name.startswith('.'):
                all_subfolders.append(item.name)  # 存储子文件夹名称
        
        # 3.3 按解析的顺序排列子文件夹（不存在的子文件夹跳过，剩余的按原顺序补充）
        ordered_subfolders = []
        # 先添加 index.md 中指定的子文件夹（存在的才添加）
        for sf in subfolder_order:
            if sf in all_subfolders:
                ordered_subfolders.append(sf)
                all_subfolders.remove(sf)  # 避免重复
            else:
                print(f"警告：年份 {year_name} 的 index.md 中指定的子文件夹 '{sf}' 不存在，跳过")
        # 剩余的子文件夹按名称排序补充到后面
        ordered_subfolders += sorted(all_subfolders)
        
        # 3.4 解析每个有序子文件夹下的 index.md
        for sf_name in ordered_subfolders:
            sf_path = os.path.join(year_folder, sf_name)
            index_md_path = os.path.join(sf_path, "index.md")
            
            # 检查子文件夹下是否有 index.md
            if not os.path.exists(index_md_path):
                print(f"警告：子文件夹 {year_name}/{sf_name} 下未找到 index.md，跳过")
                continue
            
            # 解析子文件夹的 index.md
            try:
                card_title, card_content = parse_md_file(index_md_path)
                year_data[year_folder]["cards"].append((card_title, card_content))
                print(f"成功解析：{year_name}/{sf_name}/index.md → 卡片标题：{card_title}")
            except Exception as e:
                print(f"警告：解析 {year_name}/{sf_name}/index.md 失败 - {str(e)}，跳过")
    
    # 4. 生成 HTML 并保存
    try:
        html_content = generate_html(year_data)
        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n成功生成 HTML 文件：{os.path.abspath(OUTPUT_HTML)}")
    except Exception as e:
        print(f"错误：生成 HTML 失败 - {str(e)}")

if __name__ == "__main__":
    main()