---
name: auto-gzctf
description: GZCTF/HackHub 平台操作。当用户要列题、查看题目、开启或关闭实例、延长靶机、提交 flag 时使用。输入通常包括站点 Cookie、比赛 ID 和题目 ID；输出包括平台动作结果。不用于漏洞分析。
---

# auto-gzctf

## 用途

用于操作 GZCTF / HackHub 类平台的题目接口，重点解决三类重复动作：

- 列出比赛题目与题目详情
- 开启、延长、销毁题目实例
- 按平台前端相同逻辑加密 flag 并提交，再轮询提交状态

## 何时使用

- 用户已经提供 `GZCTF_Token` 或同类站点 Cookie
- 需要访问 `https://.../games/<id>/challenges` 背后的 API
- 需要把“开靶机 / 交 flag”固化成可复用流程

如果当前任务主要是漏洞分析、利用和拿 flag，本 skill 只负责平台动作；题目分析仍应同时使用适合的 CTF skill。

## 输入

- `GZCTF_BASE_URL`，例如 `https://hackhub.get-shell.com`
- `GZCTF_TOKEN`，站点 Cookie 值
- `GZCTF_GAME_ID`，比赛 ID
- 题目 ID、分类、flag 或 submission ID，按具体动作需要提供
- `GZCTF_PROXY`，可选，例如 `http://127.0.0.1:7897`

## 输出

- 题目列表、题目详情、实例状态或提交状态。
- 开启、延长、销毁实例的执行结果。
- flag 加密提交后的轮询结果。
- 所有重要返回值应落为稳定 JSON，便于后续脚本或 agent 继续消费。

## 执行流程

优先使用脚本：

- `scripts/gzctf_helper.py`

脚本输出稳定 JSON，便于后续脚本或 agent 继续消费。

## 约束规则

- 优先在 WSL 中执行
- 如网络访问异常，优先使用 `http://127.0.0.1:7897`
- 不要把用户 token 硬编码进 skill；用环境变量或命令行参数传入
- 优先直接运行脚本，不要重复手搓请求
- 所有重要返回值落为 JSON 输出
- 需要提交 flag 时默认使用 `submit --wait`
- 如果站点未启用 `apiPublicKey`，脚本会自动退回明文提交

## 边界情况

- 如果当前任务主要是漏洞分析、利用和拿 flag，本 skill 只负责平台动作；题目分析仍应同时使用适合的 CTF skill。
- 如果站点未启用 `apiPublicKey`，脚本会自动退回明文提交。
- 如果网络访问异常，先考虑代理、Cookie 或实例状态问题。

## 示例

### 常用命令

先确认依赖：

```bash
python3 -m pip install requests cryptography
```

列题：

```bash
python3 scripts/gzctf_helper.py list --category Web
```

查看题目详情：

```bash
python3 scripts/gzctf_helper.py challenge --challenge-id 4
```

开启靶机：

```bash
python3 scripts/gzctf_helper.py create --challenge-id 4
```

延长靶机：

```bash
python3 scripts/gzctf_helper.py extend --challenge-id 4
```

关闭靶机：

```bash
python3 scripts/gzctf_helper.py destroy --challenge-id 4
```

提交 flag 并等待最终状态：

```bash
python3 scripts/gzctf_helper.py submit --challenge-id 4 --flag 'flag{...}' --wait
```

查询某次提交状态：

```bash
python3 scripts/gzctf_helper.py status --challenge-id 4 --submission-id 12345
```

## 已验证的平台行为

对当前站点已经确认：

- 题目列表接口：`GET /api/game/<gameId>/details`
- 题目详情接口：`GET /api/game/<gameId>/challenges/<challengeId>`
- 开启实例：`POST /api/game/<gameId>/container/<challengeId>`
- 延长实例：`POST /api/game/<gameId>/container/<challengeId>/extend`
- 销毁实例：`DELETE /api/game/<gameId>/container/<challengeId>`
- 提交 flag：`POST /api/game/<gameId>/challenges/<challengeId>`
- 轮询提交状态：`GET /api/game/<gameId>/challenges/<challengeId>/status/<submissionId>`

提交 flag 时，若 `/api/config` 返回 `apiPublicKey`，则必须先按前端逻辑加密：

- `X25519`
- `SHA-256`
- `AES-GCM`
- 最终提交值为 `base64(ephemeral_public_key || nonce || ciphertext)`

## 不适用场景

- 不用于漏洞分析、payload 构造或题目利用。
- 不用于没有站点 Cookie 或比赛上下文的泛泛 CTF 讨论。
