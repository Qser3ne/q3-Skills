---
name: pdf
description: PDF 读写与审阅。当用户需要读取、创建、编辑或检查 PDF，且版式渲染很重要时使用。输入通常包括 PDF、内容或布局要求；输出包括 PDF 产物、提取结果或版式检查结论。不用于普通文本处理。
---


# pdf

## 用途

读取、创建、编辑或审阅 PDF，并在版式渲染重要时通过页面渲染检查最终效果。

## 何时使用

- Read or review PDF content where layout and visuals matter.
- Create PDFs programmatically with reliable formatting.
- Validate final rendering before delivery.

## 输入

- 待读取或审阅的 PDF 文件。
- 要生成 PDF 的文本、图片、表格或版式要求。
- 用户对输出路径、文件名或视觉质量的要求。

## 输出

- 生成或修改后的 PDF 文件。
- PDF 文本提取、内容审阅或版式检查结论。
- 必要时输出渲染后的 PNG 检查结果。

## 执行流程

1. Prefer visual review: render PDF pages to PNGs and inspect them.
   - Use `pdftoppm` if available.
   - If unavailable, install Poppler or ask the user to review the output locally.
2. Use `reportlab` to generate PDFs when creating new documents.
3. Use `pdfplumber` (or `pypdf`) for text extraction and quick checks; do not rely on it for layout fidelity.
4. After each meaningful update, re-render pages and verify alignment, spacing, and legibility.

## 约束规则

- Use `tmp/pdfs/` for intermediate files; delete when done.
- Write final artifacts under `output/pdf/` when working in this repo.
- Keep filenames stable and descriptive.
- Maintain polished visual design: consistent typography, spacing, margins, and section hierarchy.
- Avoid rendering issues: clipped text, overlapping elements, broken tables, black squares, or unreadable glyphs.
- Charts, tables, and images must be sharp, aligned, and clearly labeled.
- Use ASCII hyphens only. Avoid U+2011 (non-breaking hyphen) and other Unicode dashes.
- Citations and references must be human-readable; never leave tool tokens or placeholder strings.

### Dependencies (install if missing)

Prefer `uv` for dependency management.

Python packages:
```
uv pip install reportlab pdfplumber pypdf
```
If `uv` is unavailable:
```
python3 -m pip install reportlab pdfplumber pypdf
```
System tools (for rendering):
```
# macOS (Homebrew)
brew install poppler

# Ubuntu/Debian
sudo apt-get install -y poppler-utils
```

If installation isn't possible in this environment, tell the user which dependency is missing and how to install it locally.

### Environment

No required environment variables.

### Rendering command

```
pdftoppm -png $INPUT_PDF $OUTPUT_PREFIX
```

## 边界情况

- If installation isn't possible in this environment, tell the user which dependency is missing and how to install it locally.
- If rendering tools are unavailable, do not claim layout has been visually verified.

## 示例

User:

```text
把这些内容生成一个排版稳定的 PDF。
```

Assistant:

```text
使用 reportlab 生成 PDF，渲染为 PNG 后检查版式，再交付最终文件。
```

## 不适用场景

- 普通文本处理或 Markdown 编辑，不涉及 PDF 版式。
- 不需要渲染或视觉检查的简单文本摘录。

## Final checks

- Do not deliver until the latest PNG inspection shows zero visual or formatting defects.
- Confirm headers/footers, page numbering, and section transitions look polished.
- Keep intermediate files organized or remove them after final approval.
