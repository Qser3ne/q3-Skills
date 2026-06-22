---
name: assist-skillCreator
description: Codex skill 创建与更新。当用户要新建、补强或修订 skill，或提到触发方式、路径、agents 元数据时使用。输入通常包括目标 skill 信息；输出包括 `SKILL.md` 与 `agents/openai.yaml`。不用于普通代码开发。
---

# assist-skillCreator

## 用途

用于补强 `skill-creator` 在“创建 / 更新 skill”场景下的行为，减少靠猜补全配置的情况。

## 何时使用

- 用户要创建新的 Codex skill
- 用户要更新、补齐、修正已有 skill
- 用户提到 skill 的路径、触发方式、`agents/openai.yaml`、显示名或默认 prompt 等元信息
- 即使用户没有显式提到本 skill，只要任务本质上是在创建或更新 skill，也应触发

## 输入

- 目标 skill 名称、目标落盘路径和新建/更新类型。
- 触发方式：主动触发（显式）还是被动触发（隐式）。
- `agents/openai.yaml`、`display_name`、`short_description`、`default_prompt` 等 UI 元数据。
- 是否需要 `scripts/`、`references/`、`assets/`。

## 输出

- 新建或修正后的 `SKILL.md`。
- 默认生成或修正的 `agents/openai.yaml`。
- 必要时输出中文 skill 创建 / 更新计划。
- 完整改名时同步更新目录、调用名、标题和相关引用。

## 执行流程

### 1. 先确定目标 skill 的基础信息

- 目标 skill 名称
- 目标落盘路径
- 是否是新建还是更新已有 skill

如果用户没有给出路径，默认使用 `SKILL-ASSIST-SKILLCREATOR-DEFAULT-SKILLS-DIR` 环境变量指定的目录；如果用户明确说明是项目级 skill，则默认使用项目根目录。

因为变量名包含连字符，读取时使用 `printenv`，不要使用 shell 参数展开：

```bash
default_skills_dir="$(printenv 'SKILL-ASSIST-SKILLCREATOR-DEFAULT-SKILLS-DIR' || true)"
```

如果该变量未设置，先询问用户目标落盘路径或要求用户设置环境变量；不要猜测本机全局 skill 目录。

### 2. 对缺失信息执行扩展提问集

当以下信息未被用户明确提供时，必须补问，不能跳过：

- 触发方式：主动触发（显式）还是被动触发（隐式）
- 是否生成 `agents/openai.yaml`
- 目标落盘路径
- 是否需要 `scripts/`、`references/`、`assets/`
- `display_name`
- `short_description`
- `default_prompt`

处理原则：

- 如果用户已经明确给出某项值，不重复追问，直接沿用或仅做必要确认
- 如果用户只给了模糊描述，先规范化成可写入文件的值，再向用户确认
- 如果用户说明“项目级 skill”“项目内 skill”或等价语义，但未给出具体子目录，默认将项目根目录视为落盘基准路径
- 对 `agents/openai.yaml`，默认答案是“生成”

### 3. 生成或修正目标 skill 的文件结构

创建新 skill 时，至少确保：

- `SKILL.md`
- `agents/openai.yaml`

更新已有 skill 时，至少检查：

- `SKILL.md` 是否仍准确描述触发场景和用途
- `agents/openai.yaml` 是否存在
- `agents/openai.yaml` 是否与目标 skill 的触发方式和 UI 元信息一致

### 4. 约束目标 skill 的 `agents/openai.yaml`

默认只生成最小必要字段：

```yaml
interface:
  display_name: "..."
  short_description: "..."
  default_prompt: "..."

policy:
  allow_implicit_invocation: true|false
```

规则：

- `display_name` 用于 UI 展示
- `short_description` 保持简短清晰，适合列表扫描
- `default_prompt` 应是一句可直接使用的提示，并显式提到目标 skill 名称，如 `$skill-name`
- 仅当触发方式需要明确表达时写入 `policy.allow_implicit_invocation`
- 不默认添加 `icon_small`、`icon_large`、`brand_color`、`dependencies`

## 约束规则

### 默认规则

- 新建 skill 在未指定路径时默认放到 `SKILL-ASSIST-SKILLCREATOR-DEFAULT-SKILLS-DIR` 环境变量指定的目录；WSL 环境建议值为 `/home/qser3ne/PrjMD/q3-Skills`
- 如果用户明确说明是项目级 skill，则默认放到对应项目根目录，而不是全局 skill 目录
- 目标 skill 目录名默认规范化为小写连字符格式，除非用户明确要求其他命名
- 在当前环境中，创建 skill 时默认应生成 `agents/openai.yaml`
- `agents/openai.yaml` 采用最小配置，除非用户明确要求更复杂字段
- 如果当前输出的是 skill 创建 / 更新计划，而不是直接动手改文件，计划默认使用中文完整叙述

### 触发方式语义

创建或更新目标 skill 时，使用下面这组固定映射，不要自行改写语义：

- 主动触发 = 显式触发 = 仅用户明确调用该 skill
- 被动触发 = 隐式触发 = 系统可根据任务自动注入该 skill

映射到 `agents/openai.yaml` 时：

- 主动触发 / 显式触发 => `policy.allow_implicit_invocation: false`
- 被动触发 / 隐式触发 => `policy.allow_implicit_invocation: true`

如果用户没有明确选择，默认回退到“主动触发（显式）”。

### 计划输出语言规则

当任务处于“先给方案 / 计划，再实施”的阶段时，使用以下固定规则：

- 只要讨论的是 skill 的创建方案、修改方案、补强方案、元信息设计、触发策略或目录结构，计划默认用中文撰写
- skill 名、路径名、YAML 字段名和 `$skill-name` 之类的标识可以保留英文
- 计划正文、步骤、说明、假设、测试场景应以中文为主，不能写成英文或中英混写为主
- 仅当用户明确要求英文时，才切换为英文计划
- 这条规则同时适用于新建 skill 和更新已有 skill

### Skill 改名或标题变更规则

当用户要求更改 skill 的标题、名称、目录名或 `$skill-name` 调用名时，先判断这是完整改名还是仅修改 UI 展示名：

- 如果用户更改的是 canonical skill 名称或调用名，必须按完整改名处理。
- 如果用户只想修改 UI 展示标题且不改变 `$skill-name` 调用名，应先明确区分“展示名修改”和“完整改名”，不要自动改目录名或调用名。

完整改名时，至少同步更新：

- 目标 skill 目录名
- `SKILL.md` frontmatter 中的 `name`
- `SKILL.md` frontmatter `description` 中的旧 `$skill-name`
- `SKILL.md` 的 Markdown 主标题
- `agents/openai.yaml` 中的 `interface.display_name`
- `agents/openai.yaml` 中的 `interface.default_prompt`

完整改名后还必须搜索旧名称、旧调用名和旧标题，避免残留旧引用。如果 `short_description`、示例、README、脚本、`references/`、`assets/` 或其他 `agents` 配置中出现旧名称，也要同步更新。

### 交付要求

在完成 skill 创建或更新时，确保：

- 路径符合默认约定、项目级约定或用户显式指定
- 触发方式语义没有混淆
- `SKILL.md` 与 `agents/openai.yaml` 相互一致
- 没有省略用户未提供但又必需的元信息
- 如果执行 skill 完整改名，确认旧目录不存在、新目录存在、旧 `$skill-name` 不再残留
- 如果只修改 UI 展示名，确认未误改目录名、`SKILL.md` 的 `name` 或 `$skill-name` 调用名
- 如果交付物中包含 skill 创建计划，该计划默认使用中文叙述，除非用户明确要求英文

## 边界情况

- 如果环境变量 `SKILL-ASSIST-SKILLCREATOR-DEFAULT-SKILLS-DIR` 未设置，先询问目标落盘路径或要求用户设置环境变量。
- 如果用户没有明确选择触发方式，默认回退到主动触发（显式）。
- 如果用户要求更改 skill 标题、名称、目录名或 `$skill-name` 调用名，先判断是完整改名还是仅修改 UI 展示名。

## 示例

User:

```text
创建一个用于处理内部 API 的新 skill。
```

Assistant:

```text
先确认目标 skill 名称、路径、触发方式和 agents 元数据，再生成 SKILL.md 与最小 agents/openai.yaml。
```

## 不适用场景

- 创建插件时不要使用本 skill。
- 修改普通项目代码时不要使用本 skill。
- 处理与 skill 无关的内容时不要使用本 skill。
