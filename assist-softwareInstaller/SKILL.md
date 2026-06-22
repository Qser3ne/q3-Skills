---
name: assist-softwareInstaller
description: 软件安装与部署。当用户显式调用 `$assist-softwareInstaller` 安装、部署或设置工具和应用时使用。输入通常包括软件名、仓库或安装目标；输出包括可运行安装结果。不用于用法咨询或已安装应用排错。
---

# Software Installer

Install software with a fixed decision order and predictable filesystem layout.

Use this skill only when the user explicitly invokes `$assist-softwareInstaller` and the intent is to install, deploy, or set up software. Do not use it for requests that only ask for usage help, documentation summaries, feature comparisons, troubleshooting after an existing install, or general brainstorming.

## Trigger Rules

Trigger this skill only when the user explicitly invokes `$assist-softwareInstaller` for actions such as:

- install a tool or app
- set up software from GitHub
- deploy a project locally with Docker
- configure a local runnable install

Do not trigger this skill when the user only wants:

- usage examples
- README summarization
- package recommendations
- architecture discussion
- debugging of an already installed app unless the request clearly becomes a reinstall or fresh setup task

## Classification And Install Root

Normalize the software name into a filesystem-safe command name using lowercase letters, digits, hyphens, and underscores as needed.

Classify the target before installing:

- `ctf-tool`: CTF, exploit, pentest, web security, reverse, crypto, forensics, fuzzing, scanning, or offensive-security oriented tools
- `general-app`: everything else

Use these install roots when the installation produces persistent local files:

- `ctf-tool` -> `<ctf tools root>/<software-name>`, where `<ctf tools root>` is read from `SKILL-ASSIST-SOFTWAREINSTALLER-CTF-TOOLS-ROOT`
- `general-app` -> `<general apps root>/<software-name>`, where `<general apps root>` is read from `SKILL-ASSIST-SOFTWAREINSTALLER-GENERAL-APPS-ROOT`

If classification is unclear, default to `general-app`.

Because these variable names contain hyphens, read them with `printenv` rather than shell parameter expansion:

```bash
ctf_tools_root="$(printenv 'SKILL-ASSIST-SOFTWAREINSTALLER-CTF-TOOLS-ROOT' || true)"
general_apps_root="$(printenv 'SKILL-ASSIST-SOFTWAREINSTALLER-GENERAL-APPS-ROOT' || true)"
```

If the required install-root variable is unset, ask the user for the install root or require the environment variable before creating persistent files. Do not guess a user-specific home path. Before using the selected install root, ensure the root directory exists; create it only if it is missing.

## Decision Order

Always use this order. Do not skip earlier steps unless they are clearly not applicable.

1. Check whether the software is suitably available through `apt`.
2. If `apt` is not suitable and the target is a GitHub project, read the repository `README.md` and install documentation.
3. Choose exactly one install mode:
   - `apt`
   - release package download
   - Docker deployment
   - direct source checkout

## Apt-First Policy

Prefer `apt` when all of these are true:

- a relevant package exists
- the package reasonably matches the requested software
- the distro package is sufficient for the user's stated goal

Do not fall back to GitHub just because GitHub also exists.

If `apt` is chosen:

- install with `apt`
- report the package name used
- report any manual privileged command still required if automatic elevation fails

## GitHub Evaluation Policy

When `apt` is unavailable or unsuitable and the request targets a GitHub project, inspect the repo documentation before choosing a method.

Choose the install mode with these fixed rules:

- Choose release package download when the README primarily directs users to binaries, `.deb`, AppImage, tarballs, or other packaged releases.
- Choose Docker deployment when the README primarily documents Docker or Docker Compose as the intended runtime path.
- Choose direct source checkout only when source installation is the documented primary path or there is no better packaged path.

Do not choose multiple primary install modes in one pass. Pick the best documented path and execute that path cleanly.

## Direct Source Checkout Rules

For direct source installs, clone or fetch into the chosen install root and keep the project self-contained there.

If the project is Python-based, these steps are mandatory:

1. Create a Python 3 virtual environment with `python3 -m venv .venv`.
2. Install dependencies into that virtual environment only.
3. Use the project's documented dependency source, such as `requirements.txt`, `pyproject.toml`, or equivalent.
4. Do not install Python dependencies into the system interpreter.

After a direct source install, create a launcher script:

- place it inside the install directory
- name it after the software, for example `<selected install root>/<software-name>`
- make it the single entrypoint for running the installed software
- ensure the script activates or directly uses the correct runtime, such as `.venv/bin/python`

Then expose a globally usable command:

- create `~/.local/bin/<software-name>` as a symlink to the launcher script
- prefer `~/.local/bin` over `/usr/local/bin`

## Docker Deployment Rules

Choose Docker only when the project documentation clearly treats Docker or Compose as the normal deployment path.

If Docker is chosen:

- keep project files in the selected install root if local files are needed
- follow the documented Docker or Compose workflow
- report the exact container start command or compose command
- do not also create a source-install launcher unless the project explicitly requires one

## Privilege Handling

If a step requires elevated privileges:

1. Attempt the privileged step automatically when runtime context permits it.
2. If elevation is blocked or fails, stop that privileged path and return an exact manual command sequence for the user to run.

Manual fallback commands must be copy-paste ready.

### Sudo password source

When sudo is needed, read the password from the `SKILL-ASSIST-SOFTWAREINSTALLER-SUDO-PASSWORD` environment variable instead of hardcoding it in the skill.

Because this variable name contains hyphens, read it with `printenv` rather than shell parameter expansion:

```bash
sudo_password="$(printenv 'SKILL-ASSIST-SOFTWAREINSTALLER-SUDO-PASSWORD' || true)"
```

If the variable is set, use it non-interactively for the privileged command:

```bash
printf '%s\n' "$sudo_password" | sudo -S <command>
```

If the variable is unset or sudo fails, do not retry with a guessed password. Stop that privileged path and return exact manual commands for the user to run.

## Post-Install CLI Notes

After the installation completes, check whether the software can be driven from the command line.

If the software has a usable CLI entrypoint, create a concise Chinese Markdown document in `/mnt/d/知识库/工具集合`, using this filename pattern:

- `<software-name>-usage.md`

This document is not a full manual. Keep it short, readable, and focused on practical use.

The absolute priority of the document is:

- common commands
- key parameter explanations
- common output interpretation

Write the document in Chinese and keep examples minimal but useful. Prefer the globally usable command if one was created. If no global command exists, use the actual runnable command path in the examples.

Do not create this Markdown file when the installed software is not meaningfully CLI-driven.

## Output Contract

Every install run must end by clearly reporting:

- chosen install method: `apt`, `release package`, `docker`, or `source checkout`
- final install directory, if local files were created
- launcher path and `~/.local/bin` command, if created
- generated CLI usage Markdown path, if created
- whether privileged steps succeeded automatically
- any remaining manual commands required from the user

When a method is rejected during evaluation, keep the explanation short and concrete, for example:

- `apt package unavailable`
- `README recommends Docker as primary deployment path`
- `release binary available, source install not preferred`

## Guardrails

- v1 scope is limited to `apt` and GitHub-driven install flows.
- Do not invent unsupported package-manager paths unless the repository documentation makes them part of the selected install flow.
- Do not use this skill implicitly. The user must explicitly invoke `$assist-softwareInstaller`.
