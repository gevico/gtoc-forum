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

def count_topics_in_md(md_path: str) -> int:
    """统计 Markdown 文件中以 '-' 开头的列表项数量（议题数量）"""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        count = 0
        for line in lines:
            line_stripped = line.strip()
            # 统计以 '- ' 开头的列表项（注意有空格）
            if line_stripped.startswith('- '):
                count += 1
        
        return count
    except Exception as e:
        print(f"警告：统计 {md_path} 议题数量失败 - {str(e)}")
        return 0

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

def generate_html(year_data: Dict[str, Dict], total_topics: int = 0) -> str:
    """
    生成完整的 HTML 内容：
    year_data 结构：{
        "年份文件夹路径": {
            "tab_name": "标签页名称",
            "subfolder_order": ["子文件夹1", "子文件夹2", ...],
            "cards": [(卡片标题, 卡片内容), ...]
        }
    }
    total_topics: 所有议题的总数量
    """
    # 提取所有年份（按降序排序后的顺序）
    year_folders = sorted(year_data.keys(), reverse=True, key=lambda x: os.path.basename(x))
    if not year_folders:
        raise ValueError("未找到任何有效年份文件夹，请检查 INPUT_DIR 配置")
    
    # 计算主题领域数量（根据实际卡片数量）
    topic_areas = sum(len(year_data[yf]["cards"]) for yf in year_folders)
    
    # 优化标签页按钮设计
    tab_buttons = []
    for year_folder in year_folders:
        year_info = year_data[year_folder]
        year_name = os.path.basename(year_folder)
        active_class = "tab-active" if year_folder == year_folders[0] else ""
        year_specific_class = "year-default" if year_name == "2025" else ""
        tab_buttons.append(f'''
            <button class="tab-btn {active_class} {year_specific_class} rounded-xl text-lg md:text-xl hover:bg-blue-50" data-year="{year_name}">
                <span class="relative z-10">{year_info["tab_name"]}</span>
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
        
        # 生成卡片 HTML（按顺序排列，增强视觉效果）
        card_htmls = []
        for idx, (card_title, card_content) in enumerate(cards):
            # 为每个卡片添加不同的图标
            icon_map = {
                'QEMU': 'fa-server',
                'Kernel': 'fa-linux',
                'Compiler': 'fa-code',
            }
            icon_class = icon_map.get(card_title.split('/')[0].strip(), 'fa-file-text-o')
            anim_delay = idx * 0.1
            
            card_htmls.append(f'''
                <div class="bg-white rounded-2xl shadow-md border border-gray-100 p-8 card-hover group" style="animation-delay: {anim_delay}s;">
                    <!-- 卡片头部 -->
                    <div class="flex items-start gap-4 mb-6">
                        <div class="flex-shrink-0 w-14 h-14 bg-gradient-to-br from-secondary to-accent rounded-xl flex items-center justify-center text-white text-2xl shadow-lg group-hover:scale-110 transition-transform duration-300">
                            <i class="fa {icon_class}"></i>
                        </div>
                        <div class="flex-1">
                            <h3 class="text-2xl md:text-3xl font-bold text-primary group-hover:text-secondary transition-colors duration-300">
                                {card_title}
                            </h3>
                            <div class="mt-2 h-1 w-16 bg-gradient-to-r from-secondary to-accent rounded-full group-hover:w-24 transition-all duration-300"></div>
                        </div>
                    </div>
                    
                    <!-- 卡片内容 -->
                    <div class="card-content text-gray-700 text-base md:text-lg leading-relaxed">
                        {card_content}
                    </div>
                </div>
            ''')
        
        # 处理无卡片的情况（添加精美的空状态提示）
        if not card_htmls:
            card_htmls.append(f'''
                <div class="bg-gradient-to-br from-blue-50 to-gray-50 rounded-2xl shadow-md border-2 border-dashed border-gray-300 p-16 text-center">
                    <div class="max-w-md mx-auto">
                        <div class="w-24 h-24 bg-gradient-to-br from-secondary/20 to-accent/20 rounded-full flex items-center justify-center mx-auto mb-6">
                            <i class="fa fa-calendar-o text-5xl text-secondary"></i>
                        </div>
                        <h3 class="text-2xl font-bold text-gray-700 mb-3">{year_name}年内容暂未更新</h3>
                        <p class="text-gray-500 mb-6">敬请期待更多精彩的技术分享</p>
                        <a href="https://github.com/gevico/gtoc-forum/issues" 
                           target="_blank" 
                           rel="noopener noreferrer"
                           class="inline-flex items-center gap-2 px-6 py-3 bg-secondary text-white rounded-lg hover:bg-secondary/90 transition-all font-medium">
                            <i class="fa fa-plus"></i>
                            <span>申请议题</span>
                        </a>
                    </div>
                </div>
            ''')
        
        # 生成标签页内容容器（优化动画和布局）
        tab_contents.append(f'''
            <div class="tab-content {active_class} animate-fade-in" data-year="{year_name}">
                <div class="grid grid-cols-1 gap-8">
                    {"".join(card_htmls)}
                </div>
            </div>
        ''')
    tab_contents_html = "\n".join(tab_contents)
    
    # HTML 模板（优化版本 - 增强视觉效果和用户体验）
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="msvalidate.01" content="B936D7B6A9AB03565B05356475E91930" />
    <title>GTOC Forum - 格维开源社区技术论坛</title>
    <meta name="description" content="GTOC Forum 是格维开源社区发起的线上技术交流论坛，分享 QEMU/KVM、Linux Kernel、编译器等前沿技术。">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" rel="stylesheet">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap" rel="stylesheet">
    <!-- 配置Tailwind自定义主题 -->
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '#0f172a',
                        secondary: '#3b82f6',
                        accent: '#f59e0b',
                        dark: '#020617',
                        lightBg: '#f8fafc',
                    }},
                    fontFamily: {{
                        sans: ['Noto Sans SC', 'Inter', 'system-ui', 'sans-serif'],
                    }},
                    animation: {{
                        'fade-in': 'fadeIn 0.6s ease-in-out',
                        'slide-up': 'slideUp 0.5s ease-out',
                        'float': 'float 3s ease-in-out infinite',
                    }},
                    keyframes: {{
                        fadeIn: {{
                            '0%': {{ opacity: '0' }},
                            '100%': {{ opacity: '1' }},
                        }},
                        slideUp: {{
                            '0%': {{ transform: 'translateY(30px)', opacity: '0' }},
                            '100%': {{ transform: 'translateY(0)', opacity: '1' }},
                        }},
                        float: {{
                            '0%, 100%': {{ transform: 'translateY(0px)' }},
                            '50%': {{ transform: 'translateY(-10px)' }},
                        }},
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
                text-shadow: 0 2px 8px rgba(0,0,0,0.4);
            }}
            .text-shadow-lg {{
                text-shadow: 0 4px 12px rgba(0,0,0,0.6);
            }}
            .bg-blur {{
                backdrop-filter: blur(12px);
            }}
            .gradient-overlay {{
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.75) 100%);
            }}
            .hero-gradient {{
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
            }}
            .tab-active {{
                color: theme('colors.secondary');
                position: relative;
            }}
            .tab-active::after {{
                content: '';
                position: absolute;
                bottom: -2px;
                left: 50%;
                transform: translateX(-50%);
                width: 60%;
                height: 3px;
                background: linear-gradient(90deg, transparent, theme('colors.secondary'), transparent);
                border-radius: 2px;
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
            }}
            /* 标签页按钮样式优化 */
            .tab-btn {{
                white-space: nowrap;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                padding: 1rem 2rem;
                font-weight: 600;
                color: #64748b;
            }}
            .tab-btn:hover:not(.tab-active) {{
                color: theme('colors.secondary');
                transform: translateY(-2px);
            }}
            .tab-btn:hover:not(.tab-active)::after {{
                content: '';
                position: absolute;
                bottom: -2px;
                left: 50%;
                transform: translateX(-50%);
                width: 40%;
                height: 2px;
                background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.5), transparent);
                border-radius: 2px;
            }}
            .year-default {{
                display: inline-block;
                position: relative;
            }}
            /* 卡片悬停效果增强 */
            .card-hover {{
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                border: 1px solid #e2e8f0;
                position: relative;
                overflow: hidden;
            }}
            .card-hover::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.05), transparent);
                transition: left 0.5s ease;
            }}
            .card-hover:hover {{
                transform: translateY(-8px);
                box-shadow: 0 20px 40px -10px rgba(59, 130, 246, 0.2), 0 0 0 1px rgba(59, 130, 246, 0.1);
                border-color: rgba(59, 130, 246, 0.3);
            }}
            .card-hover:hover::before {{
                left: 100%;
            }}
            /* -------------- Markdown 样式优化 -------------- */
            .card-content ul {{
                list-style-type: none;
                margin-left: 0;
                margin-bottom: 1.25rem;
                line-height: 2;
            }}
            .card-content ul li {{
                position: relative;
                padding-left: 1.75rem;
                margin-bottom: 0.75rem;
            }}
            .card-content ul li::before {{
                content: '▸';
                position: absolute;
                left: 0;
                color: theme('colors.secondary');
                font-weight: bold;
                font-size: 1.1em;
            }}
            .card-content ul ul {{
                margin-left: 1.5rem;
                margin-top: 0.5rem;
            }}
            .card-content ul ul li::before {{
                content: '◦';
                color: theme('colors.accent');
            }}
            .card-content ol {{
                list-style-type: decimal;
                margin-left: 1.75rem;
                margin-bottom: 1.25rem;
                line-height: 2;
            }}
            .card-content li {{
                margin-bottom: 0.75rem;
                transition: all 0.2s ease;
            }}
            .card-content a {{
                color: #3b82f6;
                font-weight: 500;
                text-decoration: none;
                transition: all 0.2s ease;
                position: relative;
                padding-bottom: 2px;
            }}
            .card-content a::after {{
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                width: 0;
                height: 2px;
                background: linear-gradient(90deg, #3b82f6, #60a5fa);
                transition: width 0.3s ease;
            }}
            .card-content a:hover {{
                color: #2563eb;
            }}
            .card-content a:hover::after {{
                width: 100%;
            }}
            .card-content strong {{
                color: #0f172a;
                font-weight: 700;
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                padding: 0.1rem 0.3rem;
                border-radius: 0.25rem;
            }}
            .card-content em {{
                color: #475569;
                font-style: italic;
            }}
            .card-content pre {{
                background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
                padding: 1.25rem;
                border-radius: 0.75rem;
                margin: 1.5rem 0;
                overflow-x: auto;
                font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
                font-size: 0.95rem;
                border: 1px solid #cbd5e1;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            }}
            .card-content code {{
                background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
                padding: 0.25rem 0.5rem;
                border-radius: 0.375rem;
                font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
                font-size: 0.9rem;
                border: 1px solid #cbd5e1;
                color: #0f172a;
                font-weight: 500;
            }}
            .card-content table {{
                width: 100%;
                border-collapse: collapse;
                margin: 1.5rem 0;
                border-radius: 0.5rem;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            }}
            .card-content th, .card-content td {{
                border: 1px solid #e2e8f0;
                padding: 0.875rem 1.25rem;
                text-align: left;
            }}
            .card-content th {{
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                font-weight: 700;
                color: #0f172a;
            }}
            .card-content tr:hover {{
                background-color: #f8fafc;
                transition: background-color 0.2s ease;
            }}
            .card-content img {{
                max-width: 100%;
                height: auto;
                border-radius: 0.75rem;
                margin: 1.5rem 0;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            .card-content img:hover {{
                transform: scale(1.02);
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            }}
            .card-content blockquote {{
                border-left: 4px solid #3b82f6;
                padding: 1rem 1.5rem;
                background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                margin: 1.5rem 0;
                border-radius: 0 0.5rem 0.5rem 0;
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
                font-style: italic;
                color: #1e293b;
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
<body class="font-sans text-gray-800 antialiased">
    <!-- 全屏图片区域 - 增强视觉效果 -->
    <header class="relative h-screen w-full overflow-hidden">
        <!-- 背景图片层 -->
        <div class="absolute inset-0 z-0">
            <img src="https://github.com/gevico/gtoc-forum/blob/main/asserts/head.png?raw=true" 
                 alt="GTOC Forum 背景"
                 class="w-full h-full object-cover scale-105 animate-[zoom_20s_ease-in-out_infinite_alternate]"
                 loading="eager">
            <!-- 多层渐变叠加 -->
            <div class="absolute inset-0 gradient-overlay"></div>
            <div class="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-dark/30"></div>
        </div>
        
        <!-- 装饰性几何元素 -->
        <div class="absolute inset-0 z-0 opacity-10">
            <div class="absolute top-20 left-10 w-72 h-72 bg-secondary rounded-full mix-blend-multiply filter blur-3xl animate-float"></div>
            <div class="absolute top-40 right-10 w-72 h-72 bg-accent rounded-full mix-blend-multiply filter blur-3xl animate-float" style="animation-delay: 2s;"></div>
            <div class="absolute bottom-20 left-1/3 w-72 h-72 bg-secondary rounded-full mix-blend-multiply filter blur-3xl animate-float" style="animation-delay: 4s;"></div>
        </div>
        
        <!-- 标题区域 - 增强动画效果 -->
        <div class="absolute inset-0 flex items-center justify-center z-10 text-center px-4">
            <div class="max-w-4xl mx-auto animate-fade-in">
                <!-- 主标题 -->
                <div class="mb-8">
                    <h1 class="text-[clamp(3rem,10vw,5.5rem)] font-black text-white text-shadow-lg mb-4 leading-tight tracking-tight">
                        GTOC <span class="text-transparent bg-clip-text bg-gradient-to-r from-secondary to-accent">Forum</span>
                    </h1>
                    <div class="flex items-center justify-center gap-3 mb-4">
                        <div class="h-px w-16 bg-gradient-to-r from-transparent to-secondary"></div>
                        <span class="text-2xl md:text-3xl font-bold text-secondary">2025</span>
                        <div class="h-px w-16 bg-gradient-to-l from-transparent to-secondary"></div>
                    </div>
                </div>
                
                <!-- 副标题 -->
                <p class="text-[clamp(1.1rem,3vw,1.5rem)] text-white/90 text-shadow max-w-2xl mx-auto mb-10 leading-relaxed font-medium">
                    格维开源社区 · 线上技术交流论坛
                </p>
                
                <!-- 特色标签 -->
                <div class="flex flex-wrap justify-center gap-3 mb-8">
                    <span class="px-4 py-2 bg-white/10 backdrop-blur-md rounded-full text-white text-sm font-medium border border-white/20 hover:bg-white/20 transition-all">
                        <i class="fa-solid fa-server mr-2"></i>AI Infra
                    </span>
                    <span class="px-4 py-2 bg-white/10 backdrop-blur-md rounded-full text-white text-sm font-medium border border-white/20 hover:bg-white/20 transition-all">
                        <i class="fa fa-code mr-2"></i>QEMU/KVM
                    </span>
                    <span class="px-4 py-2 bg-white/10 backdrop-blur-md rounded-full text-white text-sm font-medium border border-white/20 hover:bg-white/20 transition-all">
                        <i class="fa fa-linux mr-2"></i>Linux Kernel
                    </span>
                    <span class="px-4 py-2 bg-white/10 backdrop-blur-md rounded-full text-white text-sm font-medium border border-white/20 hover:bg-white/20 transition-all">
                        <i class="fa fa-cogs mr-2"></i>Compiler
                    </span>
                </div>
            </div>
        </div>
        
        <!-- 向下滚动指示 - 居中布局 -->
        <div class="absolute bottom-12 left-0 right-0 z-10 flex justify-center">
            <a href="#forum-archive" 
               class="text-white text-5xl opacity-70 hover:opacity-100 transition-all animate-bounce hover:scale-110">
                <i class="fa fa-angle-double-down"></i>
            </a>
        </div>
    </header>
    <!-- 内容区域 - 优化布局和视觉效果 -->
    <section id="forum-archive" class="py-16 bg-gradient-to-b from-lightBg via-white to-lightBg">
        <div class="container mx-auto px-4">
            <!-- 区域标题 -->
            <div class="max-w-5xl mx-auto mb-12 text-center animate-slide-up">
                <h2 class="text-4xl md:text-5xl font-bold text-primary mb-4">
                    <i class="fa fa-calendar-o mr-3 text-secondary"></i>往期分享
                </h2>
                <p class="text-lg text-gray-600 max-w-2xl mx-auto">
                    探索往期技术分享，涵盖人工智能、内核、编译器、虚拟化等前沿主题
                </p>
                <div class="mt-6 flex justify-center">
                    <div class="h-1 w-24 bg-gradient-to-r from-secondary to-accent rounded-full"></div>
                </div>
            </div>
            
            <!-- 标签页导航容器 - 优化设计 -->
            <div class="max-w-5xl mx-auto mb-10">
                <div class="bg-white rounded-2xl shadow-lg border border-gray-100 p-2 animate-slide-up" style="animation-delay: 0.1s;">
                    <div class="flex flex-wrap justify-center gap-2">
                        {tab_buttons_html}
                    </div>
                </div>
            </div>

            <!-- 标签页内容 - 增强卡片效果 -->
            <div class="max-w-5xl mx-auto mb-12 animate-slide-up" style="animation-delay: 0.2s;">
                {tab_contents_html}
            </div>

            <!-- 说明文字 - 重新设计 -->
            <div class="max-w-5xl mx-auto mb-12 animate-slide-up" style="animation-delay: 0.3s;">
                <div class="relative bg-gradient-to-br from-blue-50 via-white to-amber-50 p-8 rounded-2xl border-2 border-blue-100 shadow-lg overflow-hidden">
                    <!-- 装饰性背景 -->
                    <div class="absolute top-0 right-0 w-64 h-64 bg-secondary/5 rounded-full blur-3xl -mr-32 -mt-32"></div>
                    <div class="absolute bottom-0 left-0 w-64 h-64 bg-accent/5 rounded-full blur-3xl -ml-32 -mb-32"></div>
                    
                    <div class="relative z-10">
                        <div class="flex items-start gap-4 mb-4">
                            <div class="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-secondary to-accent rounded-xl flex items-center justify-center text-white text-xl shadow-lg">
                                <i class="fa fa-info-circle"></i>
                            </div>
                            <div class="flex-1">
                                <h3 class="text-xl font-bold text-primary mb-2">关于 GTOC Forum</h3>
                                <p class="text-base text-gray-700 leading-relaxed text-justify">
                                    GTOC Forum 是由社区成员牵头发起的线上技术交流论坛，不定期开展技术分享会。社区成员如果有感兴趣或者想要申报议题，可以通过
                                    <a href="https://github.com/gevico/gtoc-forum/issues" 
                                       target="_blank" 
                                       rel="noopener noreferrer"
                                       class="inline-flex items-center gap-1 text-secondary hover:text-primary font-semibold transition-all hover:gap-2">
                                        <i class="fa fa-github"></i>
                                        <span>Github 仓库的 issues</span>
                                        <i class="fa fa-external-link text-xs"></i>
                                    </a>
                                    页面发起讨论和申请。
                                </p>
                            </div>
                        </div>
                        
                        <!-- 统计信息 -->
                        <div class="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-gray-200">
                            <div class="text-center">
                                <div class="text-2xl font-bold text-secondary mb-1">{total_topics}</div>
                                <div class="text-sm text-gray-600">技术分享</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-secondary mb-1">{topic_areas}</div>
                                <div class="text-sm text-gray-600">主题领域</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-secondary mb-1">3600+</div>
                                <div class="text-sm text-gray-600">社区成员</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
    <!-- 页脚 - 现代化设计 -->
    <footer class="hero-gradient text-white py-16 footer-force-visible relative overflow-hidden">
        <!-- 装饰性背景 -->
        <div class="absolute inset-0 opacity-5">
            <div class="absolute top-0 left-0 w-96 h-96 bg-secondary rounded-full mix-blend-multiply filter blur-3xl"></div>
            <div class="absolute bottom-0 right-0 w-96 h-96 bg-accent rounded-full mix-blend-multiply filter blur-3xl"></div>
        </div>
        
        <div class="container mx-auto px-4 relative z-10">
            <div class="max-w-5xl mx-auto">
                <!-- 社交链接 -->
                <div class="mb-10">
                    <h3 class="text-center text-lg font-semibold text-white/80 mb-6 tracking-wide">关注我们</h3>
                    <div class="flex flex-wrap justify-center gap-4">
                        <a href="https://github.com/gevico" 
                           target="_blank" 
                           rel="noopener noreferrer"
                           class="group flex items-center gap-3 px-6 py-3 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg border border-white/20">
                            <i class="fa fa-github text-2xl group-hover:scale-110 transition-transform"></i>
                            <span class="font-medium">Github</span>
                        </a>
                        <a href="https://space.bilibili.com/483048140/lists/6433029?type=season" 
                           target="_blank"
                           rel="noopener noreferrer" 
                           class="group flex items-center gap-3 px-6 py-3 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg border border-white/20">
                            <i class="fa fa-youtube-play text-2xl group-hover:scale-110 transition-transform"></i>
                            <span class="font-medium">Bilibili</span>
                        </a>
                        <a href="https://qm.qq.com/q/jIXYyZkQqQ" 
                           target="_blank" 
                           rel="noopener noreferrer"
                           class="group flex items-center gap-3 px-6 py-3 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg border border-white/20">
                            <i class="fa fa-qq text-2xl group-hover:scale-110 transition-transform"></i>
                            <span class="font-medium">QQ Group</span>
                        </a>
                        <a href="https://t.me/gevico_channel" 
                           target="_blank" 
                           rel="noopener noreferrer"
                           class="group flex items-center gap-3 px-6 py-3 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg border border-white/20">
                            <i class="fa fa-telegram text-2xl group-hover:scale-110 transition-transform"></i>
                            <span class="font-medium">Telegram</span>
                        </a>
                    </div>
                </div>
                
                <!-- 分隔线 -->
                <div class="mb-8">
                    <div class="h-px bg-gradient-to-r from-transparent via-white/30 to-transparent"></div>
                </div>
                
                <!-- 版权信息 -->
                <div class="text-center">
                    <p class="text-white/70 text-sm mb-2 flex items-center justify-center gap-2">
                        <i class="fa fa-copyright"></i>
                        <span>{os.path.basename(year_folders[0])} 格维开源社区. 保留所有权利.</span>
                    </p>
                    <p class="text-white/50 text-xs flex items-center justify-center gap-2">
                        <i class="fa fa-heart text-red-400"></i>
                        <span>用心打造开源技术社区</span>
                    </p>
                </div>
            </div>
        </div>
    </footer>
    <!-- JavaScript - 增强交互功能 -->
    <script>
        // 标签页切换功能（增强动画）
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                const targetYear = btn.getAttribute('data-year');
                
                // 切换标签激活状态
                tabBtns.forEach(b => b.classList.remove('tab-active'));
                btn.classList.add('tab-active');
                
                // 切换内容显示（添加淡入动画）
                tabContents.forEach(content => {{
                    if (content.getAttribute('data-year') === targetYear) {{
                        content.classList.remove('hidden');
                        // 重新触发动画
                        content.style.animation = 'none';
                        setTimeout(() => {{
                            content.style.animation = '';
                        }}, 10);
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
                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                if (targetElement) {{
                    targetElement.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'start'
                    }});
                }}
            }});
        }});
        
        // 滚动动画效果
        const observerOptions = {{
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px'
        }};
        
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }}
            }});
        }}, observerOptions);
        
        // 监听所有卡片元素
        document.addEventListener('DOMContentLoaded', () => {{
            const cards = document.querySelectorAll('.card-hover');
            cards.forEach(card => {{
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px)';
                card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(card);
            }});
        }});
        
        // 确保页面加载完成后页脚可见
        window.addEventListener('load', function() {{
            const footer = document.querySelector('footer');
            if (footer) {{
                footer.style.display = 'block';
                footer.style.opacity = '1';
                footer.offsetHeight;
            }}
        }});
        
        // 添加滚动进度指示器
        window.addEventListener('scroll', () => {{
            const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
            const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scrolled = (winScroll / height) * 100;
            
            // 可以在这里添加滚动进度条（如果需要）
        }});
        
        // 添加 CSS 动画类
        const style = document.createElement('style');
        style.textContent = `
            @keyframes zoom {{
                0%, 100% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
            }}
        `;
        document.head.appendChild(style);
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
    total_topics = 0  # 统计所有议题总数
    
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
                
                # 统计该文件中的议题数量
                topic_count = count_topics_in_md(index_md_path)
                total_topics += topic_count
                
                print(f"成功解析：{year_name}/{sf_name}/index.md → 卡片标题：{card_title}，议题数：{topic_count}")
            except Exception as e:
                print(f"警告：解析 {year_name}/{sf_name}/index.md 失败 - {str(e)}，跳过")
    
    # 4. 生成 HTML 并保存
    try:
        html_content = generate_html(year_data, total_topics)
        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n成功生成 HTML 文件：{os.path.abspath(OUTPUT_HTML)}")
        print(f"统计信息：共 {total_topics} 个技术议题")
    except Exception as e:
        print(f"错误：生成 HTML 失败 - {str(e)}")

if __name__ == "__main__":
    main()