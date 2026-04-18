#!/usr/bin/env python3
"""Complete update: fetch -> translate with Google -> classify -> generate Chinese markdown -> push"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse
from datetime import datetime

CATEGORIES = {
    "ai-llm-agents": {"label": "🤖 AI / LLM / 智能体", "topics": r"agent|gpt|chatbot|langchain|llama|rag|retrieval-augmented|llm|openai|claude|copilot|assistant|chat|conversation|prompt", "desc_keywords": r"agent|gpt|llm|chatbot|langchain|copilot|assistant|openai|claude|prompt engineering|conversation"},
    "ml-training-infra": {"label": "🧠 ML 训练 / 推理 / 基础设施", "topics": r"machine-learning|deep-learning|neural|fine-tune|reinforcement|quantization|vllm|triton|tensorrt|onnx|gguf|peft|lora|dpo|rlhf|grpo|unsloth|axolotl|training|inference|distributed|model-parallel|tensor-parallel|cuda|pytorch|tensorflow|jax|transformers|huggingface|model|ml-engineering|mlops", "desc_keywords": r"fine-tuning|training|inference|quantization|lora|rlhf|dpo|distributed|model parallel|pytorch|tensorflow|huggingface|mlops"},
    "ai-multimedia": {"label": "🎨 AI 视觉 / 语音 / 音频 / 视频", "topics": r"computer-vision|image-generation|text-to-image|diffusion|stable-diffusion|speech|whisper|tts|stt|voice|audio-generation|music-generation|video-generation|image-processing|ocr|object-detection|segmentation|face|vision|multimodal|clip|sam", "desc_keywords": r"image generation|speech|voice|music|video|vision|ocr|diffusion|stable diffusion|whisper|text-to-speech|audio|multimodal|object detection|segmentation"},
    "ai-skills-workflow": {"label": "⚡ AI 技能 / 工作流 / 自动化", "topics": r"ai-skills|skill|workflow|automation|agent-workflows|book-to-skill|knowledge-distillation|skill-generator|mcp|model-context-protocol|tool-use|function-calling", "desc_keywords": r"skill|workflow|automation|tool use|function calling|mcp|knowledge distillation|agent workflow"},
    "devops-cloud": {"label": "☁️ DevOps / 云 / 基础设施", "topics": r"docker|kubernetes|k8s|terraform|ansible|ci-cd|devops|cloud|aws|gcp|azure|serverless|container|helm|prometheus|grafana|monitoring|logging|infrastructure|iaco", "desc_keywords": r"docker|kubernetes|container|orchestration|ci/cd|pipeline|terraform|infrastructure|cloud|serverless|monitoring|deploy"},
    "frontend-web": {"label": "🌐 前端 / Web 开发", "topics": r"react|vue|angular|svelte|nextjs|nuxt|tailwind|css|webpack|vite|frontend|ui-component|design-system|web|javascript|typescript|html|pwa|webapp|chrome-extension", "desc_keywords": r"react|vue|angular|svelte|component|ui|frontend|web|css|tailwind|javascript|typescript|next\.js|nuxt"},
    "backend-dev": {"label": "⚙️ 后端 / 开发工具", "topics": r"api|backend|framework|grpc|graphql|rest|microservice|database|orm|server|web-framework|fastapi|django|flask|spring|express|gin|echo|gorm", "desc_keywords": r"api|backend|framework|server|database|orm|microservice|grpc|graphql|restful"},
    "cli-tools": {"label": "🛠️ 命令行工具 / 实用工具", "topics": r"cli|tool|utility|command-line|terminal|productivity|automation|script|workflow|editor|vim|neovim|emacs|ide|linter|formatter|debugger", "desc_keywords": r"cli|command line|terminal|tool|utility|productivity|automation|workflow|editor|vim|neovim|plugin"},
    "data-science": {"label": "📊 数据科学 / 分析", "topics": r"data-science|data-analysis|data-visualization|pandas|numpy|jupyter|notebook|matplotlib|plotly|bi|analytics|etl|data-pipeline|spark|hadoop", "desc_keywords": r"data science|data analysis|visualization|pandas|jupyter|notebook|analytics|etl|big data|spark"},
    "mobile-dev": {"label": "📱 移动开发", "topics": r"android|ios|flutter|react-native|swift|kotlin|mobile|app|mobile-app|xamarin|maui", "desc_keywords": r"android|ios|flutter|react native|mobile|app|swift|kotlin"},
    "security": {"label": "🔒 安全", "topics": r"security|pentest|vulnerability|cve|exploit|cryptography|encryption|authentication|oauth|jwt|firewall|waf|red-team", "desc_keywords": r"security|pentest|vulnerability|exploit|cryptograph|authenticat|red team|penetration"},
    "education": {"label": "📚 教育 / 学习", "topics": r"education|learning|tutorial|course|book|notes|knowledge|study|algorithm|coding-interview|competitive-programming|leetcode", "desc_keywords": r"tutorial|learn|course|book|notes|education|algorithm|coding interview|competitive"},
    "games-graphics": {"label": "🎮 游戏 / 图形 / 多媒体", "topics": r"game|gamedev|graphics|opengl|vulkan|shader|webgl|threejs|ray-tracing|media|video|audio|ffmpeg|image-processing|animation", "desc_keywords": r"game|graphics|shader|render|ray|video|audio|media|ffmpeg|animation|image"},
    "open-source": {"label": "🌟 开源项目", "topics": r"open-source|opensource|community|free|foss", "desc_keywords": r"open source|community-driven|free software"},
}

CATEGORY_FILES = {cat: f"{cat}.md" for cat in CATEGORIES}
CATEGORY_FILES["favorite"] = "favorite.md"
CATEGORY_FILES["other"] = "other.md"

CATEGORY_LABELS = {
    "ai-llm-agents": "🤖 AI / LLM / 智能体",
    "ml-training-infra": "🧠 ML 训练 / 推理 / 基础设施",
    "ai-multimedia": "🎨 AI 视觉 / 语音 / 音频 / 视频",
    "ai-skills-workflow": "⚡ AI 技能 / 工作流 / 自动化",
    "devops-cloud": "☁️ DevOps / 云 / 基础设施",
    "frontend-web": "🌐 前端 / Web 开发",
    "backend-dev": "⚙️ 后端 / 开发工具",
    "cli-tools": "🛠️ 命令行工具 / 实用工具",
    "data-science": "📊 数据科学 / 分析",
    "mobile-dev": "📱 移动开发",
    "security": "🔒 安全",
    "education": "📚 教育 / 学习",
    "games-graphics": "🎮 游戏 / 图形 / 多媒体",
    "open-source": "🌟 开源项目",
    "favorite": "⭐ 收藏夹",
    "other": "📦 其他",
}

_translate_cache = {}

def google_translate(text):
    """Translate using Google Translate unofficial API."""
    if not text:
        return "暂无描述"
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return text
    if text in _translate_cache:
        return _translate_cache[text]
    try:
        url = f'https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={urllib.parse.quote(text)}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            result = ''.join([s[0] for s in data[0] if s[0]])
            _translate_cache[text] = result
            return result
    except Exception as e:
        print(f"  翻译出错: {e}")
        return text

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"命令失败: {cmd}\n错误: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def fetch_starred():
    raw = run_cmd("gh api /user/starred --paginate")
    data = json.loads(raw)
    repos = []
    for item in data:
        starred_at = item.get("starred_at", "")
        if starred_at:
            try:
                dt = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
                starred_at = dt.strftime("%Y-%m-%d")
            except:
                pass
        repos.append({
            "full_name": item["full_name"],
            "description": item.get("description") or "",
            "stars": item.get("stargazers_count", 0),
            "language": item.get("language") or "无",
            "starred_at": starred_at,
            "topics": ", ".join(item.get("topics", []) or []),
        })
    return repos

def classify_repo(repo):
    topics = repo["topics"].lower() if repo["topics"] else ""
    desc = repo["description"].lower() if repo["description"] else ""
    for cat_id, rules in CATEGORIES.items():
        if re.search(rules["topics"], topics) or re.search(rules["desc_keywords"], desc):
            return cat_id
    lang_map = {
        "ai-llm-agents": ["Python"],
        "ml-training-infra": ["Python", "C++"],
        "ai-multimedia": ["Python"],
        "frontend-web": ["JavaScript", "TypeScript", "HTML", "CSS"],
        "mobile-dev": ["Kotlin", "Swift", "Dart"],
        "cli-tools": ["Go", "Rust", "Shell"],
    }
    for cat_id, langs in lang_map.items():
        if repo["language"] in langs:
            return cat_id
    return "other"

def classify(repos):
    classified = {cat: [] for cat in CATEGORIES}
    classified["favorite"] = []
    classified["other"] = []
    for repo in repos:
        cat = classify_repo(repo)
        classified[cat].append(repo)
    for cat in classified:
        classified[cat].sort(key=lambda x: x["starred_at"] or "", reverse=True)
    return classified

def gen_category_md(cat_id, repos, is_favorite=False):
    label = CATEGORY_LABELS[cat_id]
    lines = [f"# {label}", ""]
    if is_favorite:
        lines.extend(["> 手动添加你最珍视的星标仓库。编辑此文件后推送即可。", "", "| 序号 | 仓库 | 描述 | 星标 | 主要话题 | 星标时间 |", "|------|------|------|------|----------|----------|", "", "*在此手动添加你最珍视的仓库。*", ""])
        return "\n".join(lines)
    if not repos:
        lines.append("*暂无仓库*")
        lines.append("")
        return "\n".join(lines)
    lines.append(f"共 **{len(repos)}** 个仓库，按星标时间倒序排列。")
    lines.append("")
    lines.append("| 序号 | 仓库 | 描述 | 星标 | 主要话题 | 星标时间 |")
    lines.append("|------|------|------|------|----------|----------|")
    for i, repo in enumerate(repos, 1):
        name = repo["full_name"]
        url = f"https://github.com/{name}"
        desc = repo["description"] if repo["description"] else "暂无描述"
        desc = desc.replace("|", "\\|")[:100]
        stars = f"★{repo['stars']:,}"
        topics = repo["topics"] if repo["topics"] else "—"
        starred_at = repo["starred_at"][:10] if repo["starred_at"] else "—"
        lines.append(f"| {i} | [{name}]({url}) | {desc} | {stars} | {topics} | {starred_at} |")
    lines.append("")
    return "\n".join(lines)

def gen_readme(classified):
    today = datetime.now().strftime("%Y-%m-%d")
    total = sum(len(v) for v in classified.values())
    lines = [
        "# ⭐ 我的星标仓库清单",
        "",
        f"> 自动整理的 GitHub 星标仓库 · 共 **{total}** 个仓库 · 更新于 {today}",
        "", "---", ""
    ]
    lines.append("## 📂 分类索引")
    lines.append("")
    lines.append("| 分类 | 数量 | 链接 |")
    lines.append("|------|------|------|")
    for cat_id, filename in CATEGORY_FILES.items():
        label = CATEGORY_LABELS[cat_id]
        count = len(classified.get(cat_id, []))
        if count == 0 and cat_id != "favorite":
            continue
        lines.append(f"| {label} | {count} | [{filename}]({filename}) |")
    lines.extend(["", "---", ""])
    all_repos = []
    for repos in classified.values():
        all_repos.extend(repos)
    all_repos.sort(key=lambda x: x["starred_at"] or "", reverse=True)
    lines.append("## 🕐 最近星标 (前 20)")
    lines.append("")
    lines.append("| 序号 | 仓库 | 描述 | 星标 | 星标时间 |")
    lines.append("|------|------|------|------|----------|")
    for i, repo in enumerate(all_repos[:20], 1):
        name = repo["full_name"]
        url = f"https://github.com/{name}"
        desc = repo["description"] if repo["description"] else "暂无描述"
        desc = desc.replace("|", "\\|")[:80]
        stars = f"★{repo['stars']:,}"
        starred_at = repo["starred_at"][:10] if repo["starred_at"] else "—"
        lines.append(f"| {i} | [{name}]({url}) | {desc} | {stars} | {starred_at} |")
    lines.extend(["", "---", "", "## 🔄 自动更新", "", "本仓库通过定时任务自动同步星标仓库。", "", "### 手动更新", "", "```bash", "cd ~/starred-lists && python3 scripts/update_starred.py", "```", ""])
    return "\n".join(lines)

def main():
    repo_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/starred-lists")
    
    print("📥 获取星标仓库...")
    repos = fetch_starred()
    print(f"✅ 获取 {len(repos)} 个星标仓库")
    
    # Translate descriptions
    print("🔄 翻译英文描述为中文...")
    en_count = 0
    for repo in repos:
        d = repo.get("description", "")
        if d and not any('\u4e00' <= c <= '\u9fff' for c in d):
            repo["description"] = google_translate(d)
            en_count += 1
            if en_count % 10 == 0:
                print(f"   已翻译 {en_count} 条...")
        elif not d:
            repo["description"] = "暂无描述"
    print(f"✅ 翻译完成，共处理 {en_count} 条")
    
    # Classify
    print("📊 分类中...")
    classified = classify(repos)
    for cat_id in CATEGORIES:
        print(f"   {CATEGORY_LABELS[cat_id]}: {len(classified[cat_id])}")
    print(f"   ⭐ 收藏夹: {len(classified['favorite'])}（手动添加）")
    print(f"   📦 其他: {len(classified['other'])}")
    
    # Check remaining English
    en_remaining = 0
    for cat, repos in classified.items():
        for r in repos:
            if r["description"] and r["description"] != "暂无描述" and not any('\u4e00' <= c <= '\u9fff' for c in r["description"]):
                en_remaining += 1
    if en_remaining > 0:
        print(f"⚠️  仍有 {en_remaining} 条英文描述未翻译")
    
    # Generate files
    print("📝 生成 Markdown 文件...")
    for cat_id, filename in CATEGORY_FILES.items():
        repos_list = classified.get(cat_id, [])
        content = gen_category_md(cat_id, repos_list, is_favorite=(cat_id == "favorite"))
        with open(os.path.join(repo_dir, filename), "w") as f:
            f.write(content)
    
    readme = gen_readme(classified)
    with open(os.path.join(repo_dir, "README.md"), "w") as f:
        f.write(readme)
    
    # Commit and push
    os.chdir(repo_dir)
    run_cmd("git add -A")
    status = run_cmd("git status --porcelain")
    if not status:
        print("✅ 无变更，跳过提交")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    run_cmd(f'git -c user.name="rainbowatlas" -c user.email="rainbowatlas@users.noreply.github.com" commit -m "更新星标清单 ({today})"')
    run_cmd("gh auth setup-git")
    run_cmd("git push")
    print("✅ 推送成功！")

if __name__ == "__main__":
    main()
