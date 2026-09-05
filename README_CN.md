# deep-pdf-reader

[English](README.md) | [简体中文](README_CN.md)

`deep-pdf-reader` 是一个小巧、可测试的工具包，用于针对单个 PDF 回答问题，同时避免把整份文档发送给视觉模型。

它遵循一条核心原则：

> Map 告诉我们去哪里找。原始页面告诉我们什么是真的。

MVP 工作流如下：

```text
PDF -> 逐页提取 -> 文档 Map -> 低成本搜索 -> 候选页面
    -> 按需渲染页面 -> 视觉证据检查 -> 带页码引用的答案
```

Document Map 包含面向导航的摘要、关键词、实体、章节路径和粗粒度版面标记。它不是权威事实数据库。答案中的金额、日期、百分比、单位、表格关系及其他重要主张，必须来自对渲染后原始页面的检查。

## 安装

使用 Python 3.11 或更高版本：

```bash
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -e ".[dev]"
# macOS/Linux: .venv/bin/python -m pip install -e ".[dev]"
```

运行时仅依赖 PyMuPDF。`pytest` 和 `reportlab` 是开发依赖，用于在本地生成 PDF 测试夹具并执行离线测试。

## 命令

```bash
python -m deep_pdf_reader build-map report.pdf
python -m deep_pdf_reader search report.pdf "为什么经营现金流下降？"
python -m deep_pdf_reader render report.pdf --pages 83,84,117
python -m deep_pdf_reader ask report.pdf "为什么经营现金流下降？"
```

默认情况下，Map 和按需渲染的页面存放在源 PDF 旁的 `.deep-pdf-reader/<document-id>/` 目录中。当路径、文件大小、修改时间和 SHA-256 指纹仍与 PDF 一致时，已有 Map 会被直接复用。可在子命令前使用 `--cache-dir`，或通过 `DEEP_PDF_READER_CACHE_DIR` 覆盖缓存位置。

`search` 会输出排序后的页面、章节路径、分数和透明的命中原因。分数与摘要只用于导航。`render` 只为指定的、从 1 开始计数的页码生成 PNG。

`ask` 会搜索 3～8 个页面，只渲染这些页面，并把页面图片交给 `PageInspector`。输出包含四个明确部分：

```text
Answer:
...

Evidence:
- Page 2: ...

Confidence:
...

Insufficient evidence:
...
```

如果没有配置视觉模型，`ask` 会使用安全的 mock inspector，并明确返回证据不足。它不会把 Map 文本升级为答案事实。

## OpenAI-compatible Provider

无需修改业务逻辑，即可配置托管的 OpenAI-compatible API，或 GLM 网关等内部端点：

```bash
set DEEP_PDF_READER_BASE_URL=https://example.internal/v1
set DEEP_PDF_READER_API_KEY=your-key
set DEEP_PDF_READER_TEXT_MODEL=your-text-model
set DEEP_PDF_READER_VISION_MODEL=your-vision-model
python -m deep_pdf_reader ask report.pdf "为什么现金流下降？"
```

在 macOS/Linux 上请使用 `export` 代替 `set`。可选配置包括：

- `DEEP_PDF_READER_CACHE_DIR`
- `DEEP_PDF_READER_CANDIDATE_PAGES`（限制在 3～8）
- `DEEP_PDF_READER_REQUEST_TIMEOUT`

文本模型只生成导航元数据。视觉模型接收渲染后的候选页面，并必须检查表头、单位、正负号、括号、脚注以及年份/期间对应列。一个端点可以只使用文本适配器、只使用视觉适配器、同时使用两者，或都不使用。

## Document Map

`map.json` 是便于阅读的 JSON，其中包含文档元数据、扁平章节范围，以及如下页面条目：

```json
{
  "page": 12,
  "section_path": ["MD&A", "Liquidity"],
  "summary": "Contains discussion of operating cash flow and comparisons.",
  "keywords": ["operating", "cash", "flow"],
  "entities": ["Operating Cash Flow"],
  "has_table": true,
  "has_chart": false,
  "has_image": false
}
```

生成摘要时会抑制数字细节。即便如此，Map 中的所有字段仍然是不受信任的导航元数据。

## 检索行为

词法检索器先对章节路径排序，再对页面排序。它组合使用 BM25、精确短语、关键词、实体、查询词元以及章节/标题加权。如果页面属于连续章节，或可能存在跨页表格，检索器会扩展相邻页；但它绝不会把检索分数当作证据。如果视觉检查器明确报告证据缺失，`ask` 可以执行一次有边界的二次检索，检查页面总数始终不超过八页。

## 开发

项目面向 Python 3.11+，并采用 `src/` 包目录结构。

```bash
python -m pip install -e ".[dev]"
pytest
python -m deep_pdf_reader --help
```

测试套件会在本地创建一份四页 PDF，覆盖逐页提取、两级章节推断、表格检测、Map 序列化/复用、关键词检索、章节加权、相邻页扩展、按需 PNG 渲染、mock inspection，以及端到端 `ask` 工作流。

## 作为 Codex Skill 使用

本仓库在以下位置包含一个符合当前格式的 Codex Skill：

```text
$REPO_ROOT/.agents/skills/deep-pdf-reader/
```

Codex 会从当前工作目录开始，沿父目录扫描 `.agents/skills`，直到仓库根目录。在本仓库任意目录中启动 Codex，即可让该 Skill 可用。当前官方发现与编写规则请参阅 [OpenAI 的 Build skills 指南](https://developers.openai.com/codex/skills/)。

在 Codex CLI 或 IDE 扩展中显式调用：

```text
$deep-pdf-reader 分析这份年报并解释现金流下降的原因。
```

可以使用 `/skills` 查看可用 Skill。也支持隐式调用：对于长篇或视觉结构复杂的 PDF、财务/年度/研究报告、合同、手册、复杂表格/图表，或者要求精确页面证据的问题，Codex 可以自动选择该 Skill。对于无关的编码任务，或普通阅读即可处理的小型纯文本文档，不应触发它。

### 安装 Skill 使用的 engine

Skill 负责编排现有 CLI，不会复制 Python engine。请把仓库包安装到 Codex 运行时所在的环境：

```bash
python -m pip install -e "$REPO_ROOT"
deep-pdf-reader --help
```

如果使用虚拟环境，请在激活该环境后启动 Codex，确保 `deep-pdf-reader` 控制台命令位于 `PATH` 中。

### 在不复制文件的情况下设为个人/全局 Skill

Codex 也会扫描：

```text
$HOME/.agents/skills/deep-pdf-reader/
```

可将仓库中的 Skill 以符号链接方式放到该位置，让源码和 Skill 指令保持单一来源。在 macOS/Linux 上：

```bash
mkdir -p "$HOME/.agents/skills"
ln -s "$REPO_ROOT/.agents/skills/deep-pdf-reader" \
  "$HOME/.agents/skills/deep-pdf-reader"
```

在 Windows PowerShell 中，从仓库根目录执行：

```powershell
$RepoRoot = (Resolve-Path ".").Path
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
New-Item -ItemType SymbolicLink `
  -Path "$HOME\.agents\skills\deep-pdf-reader" `
  -Target "$RepoRoot\.agents\skills\deep-pdf-reader"
```

Codex 会跟随符号链接的 Skill 目录。如果新链接的 Skill 没有出现，请重启 Codex。

### Skill 模式与 standalone 模式

```text
Standalone 模式
用户 -> deep-pdf-reader ask -> 内部 PageInspector

Codex Skill 模式（在 Codex 中首选）
用户 -> Codex -> SKILL.md -> build-map/search/render
     -> Codex 视觉检查/推理 -> 带页码引用的答案
```

非 Codex 环境仍支持 standalone `ask`。Skill 模式使用 Codex 自身完成查询规划、迭代导航、视觉证据审阅和答案综合，从而避免不必要的嵌套 VLM 调用。

## MVP 限制

- 每条命令只处理一个本地 PDF；不支持多文档语料库或跨文档问答。
- 文本型 PDF 效果最佳。扫描件/纯图片 PDF 会有视觉标记，但 deterministic Map builder 不提供 OCR。
- 标题和表格检测采用保守启发式规则，不是完整的版面重建引擎。
- 检索为词法检索；没有 embedding 或向量数据库。
- OpenAI-compatible 适配器使用 Chat Completions 风格的 JSON 响应；端点特定的认证或 payload 扩展可能需要小型适配器。
- 不包含 Elasticsearch、ColPali/ColQwen、Web UI、多用户状态、分布式任务、知识图谱、RAGFlow，也不强制安装 MinerU。
