#!/usr/bin/env python3
"""
Update starred-lists repo: fetch all starred repos, classify, generate markdown, commit & push.
Usage: python3 update_starred.py [repo_path]
  repo_path defaults to the directory containing this script.
"""
import json, os, re, subprocess, sys
from datetime import datetime

CATEGORIES = {
    "ai-llm-agents": {
        "label": "🤖 AI / LLM / Agents",
        "topics": r"agent|gpt|chatbot|langchain|llama|rag|retrieval-augmented|llm|openai|claude|copilot|assistant|chat|conversation|prompt",
        "desc_keywords": r"agent|gpt|llm|chatbot|langchain|copilot|assistant|openai|claude|prompt engineering|conversation",
    },
    "ml-training-infra": {
        "label": "🧠 ML Training / Inference / Infra",
        "topics": r"machine-learning|deep-learning|neural|fine-tune|reinforcement|quantization|vllm|triton|tensorrt|onnx|gguf|peft|lora|dpo|rlhf|grpo|unsloth|axolotl|training|inference|distributed|model-parallel|tensor-parallel|cuda|pytorch|tensorflow|jax|transformers|huggingface|model|ml-engineering|mlops",
        "desc_keywords": r"fine-tuning|training|inference|quantization|lora|rlhf|dpo|distributed|model parallel|pytorch|tensorflow|huggingface|mlops",
    },
    "ai-multimedia": {
        "label": "🎨 AI Vision / Speech / Audio / Video",
        "topics": r"computer-vision|image-generation|text-to-image|diffusion|stable-diffusion|speech|whisper|tts|stt|voice|audio-generation|music-generation|video-generation|image-processing|ocr|object-detection|segmentation|face|vision|multimodal|clip|sam",
        "desc_keywords": r"image generation|speech|voice|music|video|vision|ocr|diffusion|stable diffusion|whisper|text-to-speech|audio|multimodal|object detection|segmentation",
    },
    "ai-skills-workflow": {
        "label": "⚡ AI Skills / Workflows / Automation",
        "topics": r"ai-skills|skill|workflow|automation|agent-workflows|book-to-skill|knowledge-distillation|skill-generator|mcp|model-context-protocol|tool-use|function-calling",
        "desc_keywords": r"skill|workflow|automation|tool use|function calling|mcp|knowledge distillation|agent workflow",
    },
    "devops-cloud": {
        "label": "☁️ DevOps / Cloud / Infrastructure",
        "topics": r"docker|kubernetes|k8s|terraform|ansible|ci-cd|devops|cloud|aws|gcp|azure|serverless|container|helm|prometheus|grafana|monitoring|logging|infrastructure|iaco",
        "desc_keywords": r"docker|kubernetes|container|orchestration|ci/cd|pipeline|terraform|infrastructure|cloud|serverless|monitoring|deploy",
    },
    "frontend-web": {
        "label": "🌐 Frontend / Web",
        "topics": r"react|vue|angular|svelte|nextjs|nuxt|tailwind|css|webpack|vite|frontend|ui-component|design-system|web|javascript|typescript|html|pwa|webapp|chrome-extension",
        "desc_keywords": r"react|vue|angular|svelte|component|ui|frontend|web|css|tailwind|javascript|typescript|next\.js|nuxt",
    },
    "backend-dev": {
        "label": "⚙️ Backend / Development Tools",
        "topics": r"api|backend|framework|grpc|graphql|rest|microservice|database|orm|server|web-framework|fastapi|django|flask|spring|express|gin|echo|gorm",
        "desc_keywords": r"api|backend|framework|server|database|orm|microservice|grpc|graphql|restful",
    },
    "cli-tools": {
        "label": "🛠️ CLI / Tools / Utilities",
        "topics": r"cli|tool|utility|command-line|terminal|productivity|automation|script|workflow|editor|vim|neovim|emacs|ide|linter|formatter|debugger",
        "desc_keywords": r"cli|command line|terminal|tool|utility|productivity|automation|workflow|editor|vim|neovim|plugin",
    },
    "data-science": {
        "label": "📊 Data Science / Analytics",
        "topics": r"data-science|data-analysis|data-visualization|pandas|numpy|jupyter|notebook|matplotlib|plotly|bi|analytics|etl|data-pipeline|spark|hadoop",
        "desc_keywords": r"data science|data analysis|visualization|pandas|jupyter|notebook|analytics|etl|big data|spark",
    },
    "mobile-dev": {
        "label": "📱 Mobile Development",
        "topics": r"android|ios|flutter|react-native|swift|kotlin|mobile|app|mobile-app|xamarin|maui",
        "desc_keywords": r"android|ios|flutter|react native|mobile|app|swift|kotlin",
    },
    "security": {
        "label": "🔒 Security",
        "topics": r"security|pentest|vulnerability|cve|exploit|cryptography|encryption|authentication|oauth|jwt|firewall|waf|red-team",
        "desc_keywords": r"security|pentest|vulnerability|exploit|cryptograph|authenticat|red team|penetration",
    },
    "education": {
        "label": "📚 Education / Learning",
        "topics": r"education|learning|tutorial|course|book|notes|knowledge|study|algorithm|coding-interview|competitive-programming|leetcode",
        "desc_keywords": r"tutorial|learn|course|book|notes|education|algorithm|coding interview|competitive",
    },
    "games-graphics": {
        "label": "🎮 Games / Graphics / Media",
        "topics": r"game|gamedev|graphics|opengl|vulkan|shader|webgl|threejs|ray-tracing|media|video|audio|ffmpeg|image-processing|animation",
        "desc_keywords": r"game|graphics|shader|render|ray|video|audio|media|ffmpeg|animation|image",
    },
    "open-source": {
        "label": "🌟 Open Source Projects",
        "topics": r"open-source|opensource|community|free|foss",
        "desc_keywords": r"open source|community-driven|free software",
    },
}

CATEGORY_FILES = {cat: f"{cat}.md" for cat in CATEGORIES}
CATEGORY_FILES["favorite"] = "favorite.md"
CATEGORY_FILES["other"] = "other.md"

CATEGORY_LABELS = {
    "ai-llm-agents": "🤖 AI / LLM / Agents",
    "ml-training-infra": "🧠 ML Training / Inference / Infra",
    "ai-multimedia": "🎨 AI Vision / Speech / Audio / Video",
    "ai-skills-workflow": "⚡ AI Skills / Workflows / Automation",
    "devops-cloud": "☁️ DevOps / Cloud / Infrastructure",
    "frontend-web": "🌐 Frontend / Web",
    "backend-dev": "⚙️ Backend / Development Tools",
    "cli-tools": "🛠️ CLI / Tools / Utilities",
    "data-science": "📊 Data Science / Analytics",
    "mobile-dev": "📱 Mobile Development",
    "security": "🔒 Security",
    "education": "📚 Education / Learning",
    "games-graphics": "🎮 Games / Graphics / Media",
    "open-source": "🌟 Open Source Projects",
    "favorite": "⭐ Favorite",
    "other": "📦 其他",
}


def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"CMD FAILED: {cmd}\nstderr: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def fetch_starred():
    """Fetch all starred repos via gh CLI."""
    raw = run_cmd("gh api /user/starred --paginate")
    import json as _json
    data = _json.loads(raw)
    repos = []
    for item in data:
        desc = item.get("description") or "No description"
        stars = item.get("stargazers_count", 0)
        lang = item.get("language") or "N/A"
        starred_at = item.get("starred_at", "")
        if starred_at:
            try:
                dt = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
                starred_at = dt.strftime("%Y-%m-%d")
            except:
                pass
        topics = ", ".join(item.get("topics", []) or [])
        repos.append({
            "full_name": item["full_name"],
            "description": desc,
            "stars": stars,
            "language": lang,
            "starred_at": starred_at,
            "topics": topics,
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
        lines.extend([
            "> 手动添加你最珍视的星标仓库。编辑此文件后推送即可。",
            "",
            "| # | Repository | Description | Stars | Topics | Starred At |",
            "|---|-----------|-------------|-------|--------|------------|",
            "",
            "*在此手动添加你最珍视的仓库。*",
            ""
        ])
        return "\n".join(lines)
    
    if not repos:
        lines.append("*暂无仓库*")
        lines.append("")
        return "\n".join(lines)
    
    lines.append(f"共 **{len(repos)}** 个仓库，按星标时间倒序排列。")
    lines.append("")
    lines.append("| # | Repository | Description | Stars | Topics | Starred At |")
    lines.append("|---|-----------|-------------|-------|--------|------------|")
    
    for i, repo in enumerate(repos, 1):
        name = repo["full_name"]
        url = f"https://github.com/{name}"
        desc = repo["description"] if repo["description"] and repo["description"] != "No description" else "—"
        desc = desc.replace("|", "\\|")[:100]
        stars = f"★{repo['stars']:,}"
        topics = repo["topics"] if repo["topics"] else "—"
        starred_at = repo["starred_at"] or "—"
        lines.append(f"| {i} | [{name}]({url}) | {desc} | {stars} | {topics} | {starred_at} |")
    
    lines.append("")
    return "\n".join(lines)


def gen_readme(classified):
    today = datetime.now().strftime("%Y-%m-%d")
    total = sum(len(v) for v in classified.values())
    
    lines = [
        "# ⭐ My Starred Repositories",
        "",
        f"> 自动整理的 GitHub 星标仓库清单 · 共 **{total}** 个仓库 · 更新于 {today}",
        "",
        "---",
        ""
    ]
    
    lines.append("## 📂 分类索引")
    lines.append("")
    lines.append("| 分类 | 数量 | 链接 |")
    lines.append("|------|------|------|")
    
    for cat_id, filename in CATEGORY_FILES.items():
        label = CATEGORY_LABELS[cat_id]
        count = len(classified.get(cat_id, []))
        if count == 0 and cat_id not in ("favorite",):
            continue
        lines.append(f"| {label} | {count} | [{filename}]({filename}) |")
    
    lines.extend(["", "---", ""])
    
    all_repos = []
    for repos in classified.values():
        all_repos.extend(repos)
    all_repos.sort(key=lambda x: x["starred_at"] or "", reverse=True)
    
    lines.append("## 🕐 最近星标 (Top 20)")
    lines.append("")
    lines.append("| # | Repository | Description | Stars | Starred At |")
    lines.append("|---|-----------|-------------|-------|------------|")
    
    for i, repo in enumerate(all_repos[:20], 1):
        name = repo["full_name"]
        url = f"https://github.com/{name}"
        desc = repo["description"] if repo["description"] and repo["description"] != "No description" else "—"
        desc = desc.replace("|", "\\|")[:80]
        stars = f"★{repo['stars']:,}"
        starred_at = repo["starred_at"] or "—"
        lines.append(f"| {i} | [{name}]({url}) | {desc} | {stars} | {starred_at} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## 🔄 自动更新",
        "",
        "本仓库通过 cron 定时任务自动同步星标仓库。",
        "",
        "### 手动更新",
        "",
        "```bash",
        "cd /path/to/starred-lists",
        "python3 scripts/update_starred.py",
        "```",
        ""
    ])
    
    return "\n".join(lines)


def main():
    repo_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/starred-lists")
    
    print(f"Fetching starred repos...")
    repos = fetch_starred()
    print(f"Got {len(repos)} starred repos")
    
    print("Classifying...")
    classified = classify(repos)
    
    for cat_id in CATEGORIES:
        print(f"  {CATEGORY_LABELS[cat_id]}: {len(classified[cat_id])}")
    print(f"  ⭐ Favorite: {len(classified['favorite'])} (manual)")
    print(f"  📦 其他: {len(classified['other'])}")
    
    print("Generating markdown files...")
    for cat_id, filename in CATEGORY_FILES.items():
        repos = classified.get(cat_id, [])
        content = gen_category_md(cat_id, repos, is_favorite=(cat_id == "favorite"))
        filepath = os.path.join(repo_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)
    
    readme = gen_readme(classified)
    with open(os.path.join(repo_dir, "README.md"), "w") as f:
        f.write(readme)
    
    # Commit and push
    os.chdir(repo_dir)
    run_cmd("git add -A")
    
    status = run_cmd("git status --porcelain")
    if not status:
        print("No changes to commit.")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    run_cmd(f'git -c user.name="rainbowatlas" -c user.email="rainbowatlas@users.noreply.github.com" commit -m "Update starred lists ({today})"')
    run_cmd("gh auth setup-git")
    run_cmd("git push")
    print("Pushed successfully!")


if __name__ == "__main__":
    main()
