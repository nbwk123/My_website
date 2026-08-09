#!/usr/bin/env python3
"""Local no-code manager for the MkDocs personal website.

Run:
    python3 website_manager.py

Then open:
    http://127.0.0.1:8123/

This tool intentionally uses only Python's standard library so it can keep
working without extra package installs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"
PORT = int(os.environ.get("WEBSITE_MANAGER_PORT", "8123"))
SSH_COMMAND = "ssh -i ~/.ssh/id_ed25519_github -p 443 -o IdentitiesOnly=yes"


SECTION_DIRS = {
    "home": "",
    "course": "course",
    "project": "project",
    "friends": "friends",
    "about": "about",
}

SECTION_LABELS = {
    "home": "主页",
    "course": "课程",
    "project": "项目",
    "friends": "友链",
    "about": "关于",
}

EN_SECTION_LABELS = {
    "home": "Home",
    "course": "Notes",
    "project": "Projects",
    "friends": "Links",
    "about": "About",
}


TEMPLATES = {
    "note": """# {title}

<div class="note-page" markdown="1">

{summary}
{{ .note-lead }}

<div class="note-meta" markdown="1">
<span>{section_label}</span>
<span>更新中</span>
</div>

<section class="note-callout" markdown="1">
**核心问题：** 在这里写下这篇内容想解决的一个具体问题。
</section>

## 核心内容

<div class="note-grid" markdown="1">

<section class="note-block" markdown="1">
### 概念
用自己的话解释这个主题的关键概念。
</section>

<section class="note-block" markdown="1">
### 方法
写下可以复用的步骤、流程或判断标准。
</section>

</div>

## 实践步骤

<div class="note-steps" markdown="1">

<section class="note-step" markdown="1">
### 第一步
写下第一步要做什么，以及为什么这样做。
</section>

<section class="note-step" markdown="1">
### 第二步
继续补充操作、观察或结果。
</section>

</div>

<section class="note-summary" markdown="1">

## 总结

用三到五句话总结这篇内容的收获、问题和下一步。

</section>

</div>
""",
    "project": """# {title}

<div class="note-page" markdown="1">

<section class="page-hero" markdown="1">

# {title}

{summary}

</section>

<section class="note-callout" markdown="1">
**项目价值：** 用一句话说明这个项目为什么值得被看见。
</section>

## 项目拆解

<div class="note-steps" markdown="1">

<section class="note-step" markdown="1">
### 背景
为什么做这个项目？它来自什么问题或机会？
</section>

<section class="note-step" markdown="1">
### 目标
它要解决什么问题？面向谁？怎样算成功？
</section>

<section class="note-step" markdown="1">
### 过程
你做了哪些关键工作？使用了什么工具？
</section>

<section class="note-step" markdown="1">
### 结果
最终产出了什么？有哪些可以继续改进？
</section>

</div>

</div>
""",
    "simple": """# {title}

<div class="note-page" markdown="1">

<section class="page-hero" markdown="1">

# {title}

{summary}

</section>

## 内容

在这里开始写正文。

</div>
""",
}


def now_ms() -> int:
    return int(time.time() * 1000)


def clean_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-_]", "", value)
    return value or f"page-{now_ms()}"


def safe_rel_path(value: str) -> Path:
    raw = value.strip().replace("\\", "/")
    if raw.startswith("/") or ".." in Path(raw).parts:
        raise ValueError("Invalid path")
    path = DOCS / raw
    if path.suffix != ".md":
        raise ValueError("Only Markdown files can be edited")
    resolved = path.resolve()
    if DOCS.resolve() not in resolved.parents and resolved != DOCS.resolve():
        raise ValueError("Path outside docs")
    return resolved


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def title_from_markdown(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def excerpt_from_markdown(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"^#+\s+.*$", " ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\{[^}]+\}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:110]


def section_from_path(rel: str) -> str:
    parts = Path(rel).parts
    if parts and parts[0] == "en":
        parts = parts[1:]
    if not parts or parts[0] == "index.md":
        return "home"
    return parts[0]


def lang_from_path(rel: str) -> str:
    return "en" if Path(rel).parts and Path(rel).parts[0] == "en" else "zh"


def list_pages() -> list[dict[str, Any]]:
    pages = []
    for path in sorted(DOCS.rglob("*.md")):
        rel = path.relative_to(DOCS).as_posix()
        text = read_text(path)
        pages.append(
            {
                "path": rel,
                "title": title_from_markdown(text, Path(rel).stem),
                "section": section_from_path(rel),
                "sectionLabel": section_label(section_from_path(rel), lang_from_path(rel)),
                "lang": lang_from_path(rel),
                "excerpt": excerpt_from_markdown(text),
                "mtime": path.stat().st_mtime,
            }
        )
    return pages


def section_label(section: str, lang: str) -> str:
    if lang == "en":
        return EN_SECTION_LABELS.get(section, section.title())
    return SECTION_LABELS.get(section, section)


def page_url(rel: str) -> str:
    path = Path(rel)
    if path.name == "index.md":
        base = path.parent.as_posix()
    else:
        base = path.with_suffix("").as_posix()
    return base + "/"


def link_target(source: str, href: str) -> str | None:
    if href.startswith(("http://", "https://", "#", "mailto:")):
        return None
    if href.endswith("/"):
        href = href + "index.md"
    if not href.endswith(".md"):
        href = href + ".md"
    target = (DOCS / source).parent / href
    try:
        resolved = target.resolve()
        if DOCS.resolve() not in resolved.parents:
            return None
        return resolved.relative_to(DOCS).as_posix()
    except ValueError:
        return None


def graph_data() -> dict[str, Any]:
    pages = list_pages()
    page_paths = {page["path"] for page in pages}
    edges = []
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    html_href_pattern = re.compile(r"href=[\"']([^\"']+)[\"']")
    for page in pages:
        text = read_text(DOCS / page["path"])
        links = [m.group(1) for m in link_pattern.finditer(text)]
        links.extend(m.group(1) for m in html_href_pattern.finditer(text))
        for href in links:
            target = link_target(page["path"], href)
            if target in page_paths:
                edges.append({"source": page["path"], "target": target})
    return {"nodes": pages, "edges": edges}


def page_path_for_new(section: str, lang: str, slug: str) -> str:
    clean = clean_slug(slug)
    prefix = "en/" if lang == "en" else ""
    if section == "home":
        return f"{prefix}{clean}.md"
    section_dir = SECTION_DIRS.get(section, section)
    return f"{prefix}{section_dir}/{clean}.md"


def update_nav_for_new_page(rel: str, title: str, section: str, lang: str) -> bool:
    """Best-effort nav insertion for course-like sections.

    This avoids adding project/friends/about detail pages to the top nav by
    default, but makes new notes discoverable.
    """
    if section != "course":
        return False
    text = read_text(MKDOCS)
    label = title.replace(":", "：")
    nav_path = rel
    marker = "      - Sample Note: en/course/example.md" if lang == "en" else "      - 示例课程文档: course/example.md"
    new_line = f"      - {label}: {nav_path}"
    if new_line in text:
        return False
    if marker in text:
        text = text.replace(marker, marker + "\n" + new_line)
        write_text(MKDOCS, text)
        return True
    return False


def create_page(payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title", "").strip()
    if not title:
        raise ValueError("Title is required")
    section = payload.get("section", "course")
    lang = payload.get("lang", "zh")
    slug = payload.get("slug") or title
    template_key = payload.get("template", "note")
    summary = payload.get("summary", "在这里写下这篇页面的摘要。").strip() or "在这里写下这篇页面的摘要。"
    rel = page_path_for_new(section, lang, slug)
    path = safe_rel_path(rel)
    if path.exists():
        raise ValueError(f"Page already exists: {rel}")
    template = TEMPLATES.get(template_key, TEMPLATES["note"])
    content = template.format(title=title, summary=summary, section_label=section_label(section, lang))
    write_text(path, content)
    nav_updated = update_nav_for_new_page(rel, title, section, lang)
    return {"path": rel, "navUpdated": nav_updated}


def run_command(args: list[str], env_extra: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    started = time.time()
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
        timeout=180,
    )
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "seconds": round(time.time() - started, 2),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def git_status() -> dict[str, Any]:
    return run_command(["git", "status", "-sb"])


def git_commit_push(message: str) -> dict[str, Any]:
    message = message.strip() or "Update website content"
    steps = []
    steps.append({"name": "status", **run_command(["git", "status", "-sb"])})
    steps.append({"name": "add", **run_command(["git", "add", "README.md", "mkdocs.yml", "docs", "overrides", "website_manager.py"])})
    diff_check = run_command(["git", "diff", "--cached", "--quiet"])
    if diff_check["code"] == 0:
        return {"ok": True, "steps": steps, "message": "没有需要提交的改动。"}
    steps.append({"name": "commit", **run_command(["git", "commit", "-m", message])})
    if not steps[-1]["ok"]:
        return {"ok": False, "steps": steps}
    steps.append({"name": "push main", **run_command(["git", "push", "origin", "main"], {"GIT_SSH_COMMAND": SSH_COMMAND})})
    return {"ok": steps[-1]["ok"], "steps": steps}


def deploy_pages() -> dict[str, Any]:
    return run_command([".venv/bin/mkdocs", "gh-deploy", "--force"], {"GIT_SSH_COMMAND": SSH_COMMAND})


def build_site() -> dict[str, Any]:
    return run_command([".venv/bin/mkdocs", "build"])


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kai Wang 网站管理器</title>
  <style>
    :root {
      --ink: #111;
      --muted: #6e6e73;
      --line: #e8e8ed;
      --soft: #f6f6f4;
      --purple: #7c3aed;
      --green: #0f8f55;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Noto Sans SC", "Segoe UI", sans-serif;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 3;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      min-height: 4.4rem;
      padding: 0 1.4rem;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,.9);
      backdrop-filter: blur(18px);
    }
    h1 { margin: 0; font-size: 1.45rem; }
    button, select, input, textarea {
      font: inherit;
    }
    button {
      min-height: 2.35rem;
      padding: 0 .9rem;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
      font-weight: 750;
    }
    button.primary { background: #111; border-color: #111; color: #fff; }
    button.purple { background: var(--purple); border-color: var(--purple); color: #fff; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    main {
      display: grid;
      grid-template-columns: minmax(17rem, .45fr) minmax(0, 1fr) minmax(17rem, .52fr);
      gap: 1rem;
      padding: 1rem;
      min-height: calc(100vh - 4.4rem);
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .75rem;
      padding: .95rem;
      border-bottom: 1px solid var(--line);
      background: var(--soft);
    }
    .panel-head h2 { margin: 0; font-size: .9rem; }
    .tools {
      display: flex;
      gap: .5rem;
      flex-wrap: wrap;
    }
    .filters {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: .5rem;
      padding: .75rem;
      border-bottom: 1px solid var(--line);
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      outline: none;
    }
    input, select { height: 2.25rem; padding: 0 .7rem; }
    textarea {
      min-height: calc(100vh - 17rem);
      padding: 1rem;
      border: 0;
      border-radius: 0;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: .78rem;
      line-height: 1.7;
      resize: vertical;
    }
    textarea.hidden { display: none; }
    .mode-switch {
      display: inline-flex;
      padding: .16rem;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f6f6f4;
    }
    .mode-switch button {
      min-height: 1.95rem;
      padding: 0 .75rem;
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: var(--muted);
      font-size: .72rem;
    }
    .mode-switch button.active {
      background: #111;
      color: #fff;
    }
    .visual-editor {
      display: grid;
      gap: .75rem;
      max-height: calc(100vh - 17rem);
      overflow: auto;
      padding: .9rem;
      background: #fbfbfa;
    }
    .visual-editor.hidden { display: none; }
    .content-block {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }
    .content-block__bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .6rem;
      padding: .55rem;
      border-bottom: 1px solid var(--line);
      background: #f7f7f5;
    }
    .content-block__bar select {
      width: 10rem;
      height: 2rem;
      font-size: .7rem;
      font-weight: 750;
    }
    .content-block__tools {
      display: flex;
      gap: .35rem;
    }
    .content-block__tools button {
      min-height: 1.9rem;
      padding: 0 .55rem;
      font-size: .68rem;
    }
    .content-block textarea {
      min-height: 5rem;
      border: 0;
      font-family: inherit;
      font-size: .82rem;
      line-height: 1.75;
      background: #fff;
    }
    .content-block[data-type="heading1"] textarea,
    .content-block[data-type="heading2"] textarea,
    .content-block[data-type="heading3"] textarea {
      min-height: 3.4rem;
      font-size: 1.05rem;
      font-weight: 850;
    }
    .content-block[data-type="callout"] {
      border-left: 4px solid var(--purple);
    }
    .content-block[data-type="dark"] {
      background: #151a17;
    }
    .content-block[data-type="dark"] .content-block__bar {
      border-color: rgba(255,255,255,.12);
      background: #111411;
    }
    .content-block[data-type="dark"] textarea {
      background: #151a17;
      color: rgba(255,255,255,.78);
    }
    .content-block[data-type="raw"] textarea {
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: .72rem;
    }
    .page-list {
      max-height: calc(100vh - 12rem);
      overflow: auto;
    }
    .page-item {
      display: block;
      width: 100%;
      padding: .85rem .95rem;
      border: 0;
      border-bottom: 1px solid var(--line);
      border-radius: 0;
      text-align: left;
      background: #fff;
    }
    .page-item.active { background: #f3efff; }
    .page-title { display: block; font-weight: 850; }
    .page-path { display: block; margin-top: .22rem; color: var(--muted); font-size: .66rem; }
    .editor-meta {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: .6rem;
      padding: .75rem;
      border-bottom: 1px solid var(--line);
    }
    .hint { color: var(--muted); font-size: .72rem; line-height: 1.6; }
    .status {
      white-space: pre-wrap;
      max-height: 18rem;
      overflow: auto;
      padding: .9rem;
      border-top: 1px solid var(--line);
      background: #111;
      color: #d8ffd8;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: .7rem;
      line-height: 1.55;
    }
    .create-form {
      display: grid;
      gap: .6rem;
      padding: .95rem;
      border-bottom: 1px solid var(--line);
    }
    .graph {
      position: relative;
      height: 18rem;
      border-bottom: 1px solid var(--line);
      background:
        radial-gradient(circle at 20% 20%, rgba(124,58,237,.12), transparent 11rem),
        #fbfbfa;
      overflow: hidden;
    }
    .node {
      position: absolute;
      max-width: 8rem;
      padding: .42rem .56rem;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,.92);
      font-size: .62rem;
      font-weight: 800;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      cursor: pointer;
    }
    .edge {
      position: absolute;
      height: 1px;
      transform-origin: 0 0;
      background: rgba(124,58,237,.28);
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: .6rem;
      padding: .95rem;
    }
    .metric {
      padding: .75rem;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .metric strong { display: block; font-size: 1.25rem; }
    .metric span { color: var(--muted); font-size: .66rem; }
    @media (max-width: 1000px) {
      main { grid-template-columns: 1fr; }
      textarea { min-height: 28rem; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Kai Wang 网站管理器</h1>
    <div class="tools">
      <button onclick="openSite()">打开网站</button>
      <button onclick="runAction('build')">构建</button>
      <button class="primary" onclick="commitPush()">提交并推送 main</button>
      <button class="purple" onclick="runAction('deploy')">部署网页</button>
    </div>
  </header>
  <main>
    <section class="panel">
      <div class="panel-head">
        <h2>页面</h2>
        <button onclick="refresh()">刷新</button>
      </div>
      <div class="filters">
        <select id="filter-section" onchange="renderPages()">
          <option value="">全部板块</option>
          <option value="home">主页</option>
          <option value="course">课程</option>
          <option value="project">项目</option>
          <option value="friends">友链</option>
          <option value="about">关于</option>
        </select>
        <select id="filter-lang" onchange="renderPages()">
          <option value="">全部语言</option>
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
      </div>
      <div class="create-form">
        <strong>新建页面</strong>
        <input id="new-title" placeholder="标题，例如：交互设计案例分析">
        <input id="new-slug" placeholder="英文路径，例如：interaction-case">
        <select id="new-section">
          <option value="course">课程</option>
          <option value="project">项目</option>
          <option value="friends">友链</option>
          <option value="about">关于</option>
        </select>
        <select id="new-template">
          <option value="note">课程/笔记模板</option>
          <option value="project">项目模板</option>
          <option value="simple">简单页面模板</option>
        </select>
        <select id="new-lang">
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
        <input id="new-summary" placeholder="一句话摘要">
        <button class="primary" onclick="createPage()">创建</button>
        <p class="hint">课程页面会自动加入 MkDocs 导航；项目、友链、关于的详情页默认不加入顶部导航，避免导航变得太拥挤。</p>
      </div>
      <div id="page-list" class="page-list"></div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>编辑</h2>
        <div class="tools">
          <div class="mode-switch">
            <button id="visual-mode" class="active" onclick="setEditorMode('visual')">可视化</button>
            <button id="source-mode" onclick="setEditorMode('source')">源码</button>
          </div>
          <button onclick="insertBlock('paragraph')">段落</button>
          <button onclick="insertBlock('callout')">摘要块</button>
          <button onclick="insertBlock('dark')">深色卡片</button>
          <button onclick="insertBlock('steps')">步骤模块</button>
          <button class="primary" onclick="savePage()">保存</button>
        </div>
      </div>
      <div class="editor-meta">
        <input id="current-path" readonly placeholder="选择左侧页面开始编辑">
        <button onclick="previewPage()">预览此页</button>
      </div>
      <div id="visual-editor" class="visual-editor"></div>
      <textarea id="editor" class="hidden" spellcheck="false" placeholder="选择一个页面，或新建页面。"></textarea>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>图谱与发布</h2>
        <button onclick="loadGraph()">更新图谱</button>
      </div>
      <div id="graph" class="graph"></div>
      <div class="summary-grid">
        <div class="metric"><strong id="page-count">0</strong><span>页面</span></div>
        <div class="metric"><strong id="edge-count">0</strong><span>内部链接</span></div>
      </div>
      <div class="create-form">
        <strong>发布说明</strong>
        <input id="commit-message" value="Update website content">
        <p class="hint">推荐流程：先保存页面，再点“构建”；确认本地网站没问题后，点“提交并推送 main”，最后点“部署网页”。</p>
      </div>
      <pre id="status" class="status">准备就绪。</pre>
    </section>
  </main>
  <script>
    let pages = [];
    let currentPath = "";
    let editorMode = "visual";
    let visualBlocks = [];

    const $ = (id) => document.getElementById(id);

    async function api(path, options = {}) {
      const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        throw new Error(data.error || data.message || "操作失败");
      }
      return data;
    }

    function setStatus(value) {
      $("status").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    }

    async function refresh() {
      const data = await api("/api/pages");
      pages = data.pages;
      renderPages();
      await loadGraph();
    }

    function renderPages() {
      const section = $("filter-section").value;
      const lang = $("filter-lang").value;
      const list = $("page-list");
      list.innerHTML = "";
      pages
        .filter(page => !section || page.section === section)
        .filter(page => !lang || page.lang === lang)
        .sort((a, b) => b.mtime - a.mtime)
        .forEach(page => {
          const btn = document.createElement("button");
          btn.className = "page-item" + (page.path === currentPath ? " active" : "");
          btn.innerHTML = `<span class="page-title">${escapeHtml(page.title)}</span><span class="page-path">${page.lang.toUpperCase()} · ${escapeHtml(page.sectionLabel)} · ${escapeHtml(page.path)}</span>`;
          btn.onclick = () => loadPage(page.path);
          list.appendChild(btn);
        });
    }

    async function loadPage(path) {
      const data = await api("/api/page?path=" + encodeURIComponent(path));
      currentPath = data.path;
      $("current-path").value = data.path;
      $("editor").value = data.content;
      visualBlocks = markdownToBlocks(data.content);
      renderVisualEditor();
      renderPages();
    }

    async function savePage() {
      if (!currentPath) return setStatus("请先选择页面。");
      syncVisualToSource();
      const data = await api("/api/page", {
        method: "POST",
        body: JSON.stringify({ path: currentPath, content: $("editor").value })
      });
      setStatus(`已保存：${data.path}`);
      await refresh();
    }

    async function createPage() {
      const payload = {
        title: $("new-title").value,
        slug: $("new-slug").value,
        section: $("new-section").value,
        template: $("new-template").value,
        lang: $("new-lang").value,
        summary: $("new-summary").value
      };
      const data = await api("/api/create", { method: "POST", body: JSON.stringify(payload) });
      setStatus(`已创建：${data.path}${data.navUpdated ? "\n已自动加入导航。" : ""}`);
      await refresh();
      await loadPage(data.path);
    }

    function setEditorMode(mode) {
      if (mode === editorMode) return;
      if (mode === "source") {
        syncVisualToSource();
        $("visual-editor").classList.add("hidden");
        $("editor").classList.remove("hidden");
      } else {
        syncSourceToVisual();
        $("editor").classList.add("hidden");
        $("visual-editor").classList.remove("hidden");
      }
      editorMode = mode;
      $("visual-mode").classList.toggle("active", mode === "visual");
      $("source-mode").classList.toggle("active", mode === "source");
    }

    function syncVisualToSource() {
      if (editorMode !== "visual") return;
      collectVisualBlocks();
      $("editor").value = blocksToMarkdown(visualBlocks);
    }

    function syncSourceToVisual() {
      visualBlocks = markdownToBlocks($("editor").value);
      renderVisualEditor();
    }

    function collectVisualBlocks() {
      visualBlocks = [...document.querySelectorAll(".content-block")].map(block => ({
        type: block.dataset.type || "paragraph",
        text: block.querySelector("textarea").value
      })).filter(block => block.text.trim());
    }

    function markdownToBlocks(markdown) {
      const lines = markdown.replace(/\r\n/g, "\n").split("\n");
      const blocks = [];
      let buffer = [];

      const flush = () => {
        const text = buffer.join("\n").trim();
        buffer = [];
        if (!text) return;
        blocks.push(chunkToBlock(text));
      };

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        if (trimmed.startsWith("<section") || trimmed.startsWith("<div")) {
          flush();
          const closeTag = trimmed.startsWith("<section") ? "</section>" : "</div>";
          const html = [line];
          while (i + 1 < lines.length && !lines[i].trim().startsWith(closeTag)) {
            i += 1;
            html.push(lines[i]);
          }
          blocks.push(chunkToBlock(html.join("\n").trim()));
        } else if (!trimmed) {
          flush();
        } else {
          buffer.push(line);
        }
      }
      flush();
      return blocks.length ? blocks : [{ type: "paragraph", text: "" }];
    }

    function chunkToBlock(text) {
      if (text.startsWith("# ")) return { type: "heading1", text: text.replace(/^#\s+/, "") };
      if (text.startsWith("## ")) return { type: "heading2", text: text.replace(/^##\s+/, "") };
      if (text.startsWith("### ")) return { type: "heading3", text: text.replace(/^###\s+/, "") };
      if (/^-\s+/m.test(text) && text.split("\n").every(line => !line.trim() || line.trim().startsWith("- "))) {
        return { type: "list", text: text.replace(/^- /gm, "") };
      }
      if (text.includes('class="note-callout"')) {
        return { type: "callout", text: stripWrapper(text, "section") };
      }
      if (text.includes('class="note-dark-panel"')) {
        return { type: "dark", text: stripWrapper(text, "section") };
      }
      if (text.includes('class="note-steps"')) {
        return { type: "steps", text };
      }
      if (text.startsWith("<")) return { type: "raw", text };
      return { type: "paragraph", text };
    }

    function stripWrapper(text, tag) {
      return text
        .replace(new RegExp(`^<${tag}[^>]*>\\n?`), "")
        .replace(new RegExp(`\\n?</${tag}>$`), "")
        .trim();
    }

    function blocksToMarkdown(blocks) {
      return blocks.map(block => {
        const text = block.text.trim();
        if (!text) return "";
        if (block.type === "heading1") return "# " + text;
        if (block.type === "heading2") return "## " + text;
        if (block.type === "heading3") return "### " + text;
        if (block.type === "list") return text.split("\n").filter(Boolean).map(line => "- " + line.replace(/^-\s*/, "")).join("\n");
        if (block.type === "callout") return `<section class="note-callout" markdown="1">\n${text}\n</section>`;
        if (block.type === "dark") return `<section class="note-dark-panel" markdown="1">\n\n${text}\n\n</section>`;
        if (block.type === "steps" || block.type === "raw") return text;
        return text;
      }).filter(Boolean).join("\n\n") + "\n";
    }

    function renderVisualEditor() {
      const root = $("visual-editor");
      root.innerHTML = "";
      visualBlocks.forEach((block, index) => root.appendChild(renderBlock(block, index)));
    }

    function renderBlock(block, index) {
      const wrap = document.createElement("div");
      wrap.className = "content-block";
      wrap.dataset.type = block.type || "paragraph";
      wrap.innerHTML = `
        <div class="content-block__bar">
          <select onchange="changeBlockType(${index}, this.value)">
            <option value="heading1">大标题</option>
            <option value="heading2">二级标题</option>
            <option value="heading3">三级标题</option>
            <option value="paragraph">段落</option>
            <option value="list">列表</option>
            <option value="callout">摘要块</option>
            <option value="dark">深色卡片</option>
            <option value="steps">步骤模块</option>
            <option value="raw">保留模块</option>
          </select>
          <div class="content-block__tools">
            <button onclick="moveBlock(${index}, -1)">上移</button>
            <button onclick="moveBlock(${index}, 1)">下移</button>
            <button onclick="deleteBlock(${index})">删除</button>
          </div>
        </div>
        <textarea oninput="updateBlock(${index}, this.value)" placeholder="输入内容"></textarea>
      `;
      wrap.querySelector("select").value = block.type || "paragraph";
      wrap.querySelector("textarea").value = block.text || "";
      return wrap;
    }

    function updateBlock(index, value) {
      visualBlocks[index].text = value;
    }

    function changeBlockType(index, type) {
      visualBlocks[index].type = type;
      renderVisualEditor();
    }

    function moveBlock(index, direction) {
      const target = index + direction;
      if (target < 0 || target >= visualBlocks.length) return;
      const [block] = visualBlocks.splice(index, 1);
      visualBlocks.splice(target, 0, block);
      renderVisualEditor();
    }

    function deleteBlock(index) {
      visualBlocks.splice(index, 1);
      renderVisualEditor();
    }

    function insertBlock(type) {
      const blocks = {
        paragraph: `\n新段落内容。\n`,
        callout: `\n<section class="note-callout" markdown="1">\n**核心观点：** 在这里写一句需要突出的结论。\n</section>\n`,
        dark: `\n<section class="note-dark-panel" markdown="1">\n\n## 重点模块\n\n这里适合放核心模型、项目结论或一组重要链接。\n\n</section>\n`,
        steps: `\n<div class="note-steps" markdown="1">\n\n<section class="note-step" markdown="1">\n### 第一步\n写下步骤说明。\n</section>\n\n<section class="note-step" markdown="1">\n### 第二步\n继续补充。\n</section>\n\n</div>\n`
      };
      if (editorMode === "visual") {
        const visualDefaults = {
          paragraph: { type: "paragraph", text: "新段落内容。" },
          callout: { type: "callout", text: "**核心观点：** 在这里写一句需要突出的结论。" },
          dark: { type: "dark", text: "## 重点模块\n\n这里适合放核心模型、项目结论或一组重要链接。" },
          steps: { type: "steps", text: blocks.steps.trim() }
        };
        visualBlocks.push(visualDefaults[type] || visualDefaults.paragraph);
        renderVisualEditor();
        return;
      }
      const editor = $("editor");
      const insert = blocks[type] || "";
      const start = editor.selectionStart;
      const end = editor.selectionEnd;
      editor.value = editor.value.slice(0, start) + insert + editor.value.slice(end);
      editor.focus();
      editor.selectionStart = editor.selectionEnd = start + insert.length;
    }

    async function loadGraph() {
      const data = await api("/api/graph");
      $("page-count").textContent = data.nodes.length;
      $("edge-count").textContent = data.edges.length;
      renderGraph(data);
    }

    function renderGraph(data) {
      const graph = $("graph");
      graph.innerHTML = "";
      const w = graph.clientWidth || 320;
      const h = graph.clientHeight || 260;
      const nodes = data.nodes.slice(0, 42);
      const coords = new Map();
      nodes.forEach((node, i) => {
        const angle = (Math.PI * 2 * i) / Math.max(nodes.length, 1);
        const rx = Math.max(80, w / 2 - 90);
        const ry = Math.max(60, h / 2 - 55);
        const x = w / 2 + Math.cos(angle) * rx;
        const y = h / 2 + Math.sin(angle) * ry;
        coords.set(node.path, { x, y });
      });
      data.edges.forEach(edge => {
        const a = coords.get(edge.source);
        const b = coords.get(edge.target);
        if (!a || !b) return;
        const line = document.createElement("div");
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        line.className = "edge";
        line.style.left = `${a.x}px`;
        line.style.top = `${a.y}px`;
        line.style.width = `${Math.sqrt(dx * dx + dy * dy)}px`;
        line.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
        graph.appendChild(line);
      });
      nodes.forEach(node => {
        const c = coords.get(node.path);
        const div = document.createElement("div");
        div.className = "node";
        div.style.left = `${c.x - 35}px`;
        div.style.top = `${c.y - 14}px`;
        div.textContent = node.title;
        div.title = node.path;
        div.onclick = () => loadPage(node.path);
        graph.appendChild(div);
      });
    }

    async function runAction(name) {
      setStatus("正在执行 " + name + " ...");
      try {
        const data = await api("/api/" + name, { method: "POST", body: "{}" });
        setStatus(formatCommandResult(data));
      } catch (err) {
        setStatus(err.message);
      }
    }

    async function commitPush() {
      setStatus("正在提交并推送 main ...");
      const message = $("commit-message").value || "Update website content";
      try {
        const data = await api("/api/push", {
          method: "POST",
          body: JSON.stringify({ message })
        });
        setStatus(formatCommandResult(data));
      } catch (err) {
        setStatus(err.message);
      }
    }

    function formatCommandResult(data) {
      if (data.steps) {
        return data.steps.map(step => `# ${step.name} (${step.ok ? "OK" : "FAIL"})\n${step.stdout || ""}${step.stderr || ""}`).join("\n\n") + (data.message ? "\n\n" + data.message : "");
      }
      return `${data.ok ? "OK" : "FAIL"} (${data.seconds || 0}s)\n${data.stdout || ""}${data.stderr || ""}`;
    }

    function previewPage() {
      if (!currentPath) return;
      const page = pages.find(page => page.path === currentPath);
      if (!page) return;
      window.open("/site/" + page.url, "_blank");
    }

    function openSite() {
      window.open("/site/", "_blank");
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    refresh().catch(err => setStatus(err.message));
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "WebsiteManager/1.0"

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._send_html(HTML)
            elif parsed.path == "/api/pages":
                pages = list_pages()
                for page in pages:
                    page["url"] = page_url(page["path"])
                self._send_json({"ok": True, "pages": pages})
            elif parsed.path == "/api/page":
                query = parse_qs(parsed.query)
                rel = query.get("path", [""])[0]
                path = safe_rel_path(rel)
                self._send_json({"ok": True, "path": rel, "content": read_text(path)})
            elif parsed.path == "/api/graph":
                data = graph_data()
                for node in data["nodes"]:
                    node["url"] = page_url(node["path"])
                self._send_json({"ok": True, **data})
            elif parsed.path.startswith("/site/"):
                self._serve_site_file(parsed.path.removeprefix("/site/"))
            else:
                self.send_error(404)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, 400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/page":
                rel = payload.get("path", "")
                content = payload.get("content", "")
                path = safe_rel_path(rel)
                write_text(path, content)
                self._send_json({"ok": True, "path": rel})
            elif parsed.path == "/api/create":
                self._send_json({"ok": True, **create_page(payload)})
            elif parsed.path == "/api/build":
                self._send_json(build_site())
            elif parsed.path == "/api/status":
                self._send_json(git_status())
            elif parsed.path == "/api/push":
                self._send_json(git_commit_push(payload.get("message", "")))
            elif parsed.path == "/api/deploy":
                self._send_json(deploy_pages())
            else:
                self.send_error(404)
        except subprocess.TimeoutExpired:
            self._send_json({"ok": False, "error": "命令超时。"}, 500)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, 400)

    def _serve_site_file(self, rel: str) -> None:
        rel = rel or "index.html"
        if rel.endswith("/"):
            rel += "index.html"
        target = (ROOT / "site" / rel).resolve()
        if (ROOT / "site").resolve() not in target.parents:
            self.send_error(403)
            return
        if not target.exists():
            self.send_error(404)
            return
        suffix = target.suffix.lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".json": "application/json; charset=utf-8",
        }.get(suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    os.chdir(ROOT)
    address = ("127.0.0.1", PORT)
    server = ThreadingHTTPServer(address, Handler)
    url = f"http://{address[0]}:{address[1]}/"
    print(f"Website manager running at {url}")
    if os.environ.get("WEBSITE_MANAGER_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping website manager.")


if __name__ == "__main__":
    main()
