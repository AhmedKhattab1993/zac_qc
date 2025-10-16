
# Using Codex CLI as a Terminal Coding Sub-Agent

Codex CLI is a local AI coding agent that runs in your terminal, capable of reading, modifying, and executing code within your project directory. Built in Rust and maintained open-source by OpenAI, it provides an interactive command-line UI for pair programming and task automation. This guide will show how to install and configure Codex CLI on macOS/Linux, use it for common coding tasks (code generation, explanation, refactoring), and integrate it into your shell scripts, git workflows, and development automation. We’ll also cover its limitations and best practices to ensure you use Codex safely and effectively.

## Installation and Setup

Codex CLI officially supports **macOS and Linux**. To get started, install the CLI and authenticate it with your OpenAI account or API key:

1. **Install Codex CLI** using one of the following methods:
   - **npm (Node.js)**:
     ```bash
     npm install -g @openai/codex
     ``` 
   - **Homebrew (macOS/Linux)**:
     ```bash
     brew install codex
     ``` 
   - **Direct Download**:
     Download a precompiled binary for your OS from the Codex GitHub releases and add it to your `$PATH`. Choose the file matching your platform, extract it, and rename the binary to `codex`.

2. **Launch Codex**:
   ```bash
   codex
   ``` 
   You’ll be prompted to authenticate using your OpenAI account or an API key.

3. **Verify Setup**:
   ```bash
   codex --version
   ```

4. *(Optional)* **Update Codex CLI**:
   ```bash
   npm install -g @openai/codex@latest
   # or
   brew update && brew upgrade codex
   ```

## Configuration

Codex CLI works out of the box, but you can customize behavior in `~/.codex/config.toml`.

- **Default Model**:
  ```toml
  model = "gpt-5-codex"
  ```

- **Approval Policy**:
  ```toml
  approval_policy = "on-request"
  ```

- **Sandbox / Filesystem Access**:
  ```toml
  sandbox_mode = "workspace-write"
  ```

- **Environment Variables**:
  ```toml
  [shell_environment_policy]
  include_only = ["PATH", "HOME"]
  ```

- **Reasoning Effort**:
  ```toml
  model_reasoning_effort = "high"
  ```

- **Profiles**:
  ```toml
  [profiles.deployment]
  approval_policy = "full"
  sandbox_mode = "none"
  ```

## Using Codex CLI Interactively

Launch with:
```bash
codex
```

You can enter natural language tasks, e.g.:
```
Fix the bug in this code
Generate a Dockerfile
Explain main.py
```

### Slash Commands

- `/model` – Switch models
- `/status` – Show usage & config
- `/approvals` – Change approval level
- `/diff` – Show changes made
- `/review` – Launch code review mode

## Non-Interactive Mode (`codex exec`)

Run one-off tasks:
```bash
codex exec "fix the CI failure"
codex exec "Explain the function calculateMetrics()"
codex exec "Update README with setup instructions"
```

Structured output with schema:
```bash
codex exec --output-schema schema.json "summarize all errors"
```

Show execution plan:
```bash
codex exec --include-plan-tool "Refactor auth module"
```

## Examples of Common Tasks

- **Generate code**:
  ```bash
  codex exec "Create backup.py that zips all .txt files"
  ```

- **Explain code**:
  ```bash
  codex exec "Explain the doTask() function in utils.py"
  ```

- **Refactor**:
  ```bash
  codex exec "Use list comprehensions in utils.py"
  ```

- **Fix tests**:
  ```bash
  codex exec "Run tests and fix failures"
  ```

- **Code review**:
  ```bash
  codex /review diff --base main --instructions "Focus on security issues"
  ```

## Workflow Integrations

- **Shell Scripts**:
  Embed commands like:
  ```bash
  codex exec "Generate Markdown summary from logs"
  ```

- **Git Hooks**:
  ```bash
  # pre-commit
  codex /review || exit 1
  ```

- **CI/CD**:
  Codex can auto-fix CI failures or post reviews as GitHub Actions using API keys.

## Limitations and Best Practices

- Always review Codex changes.
- Use version control to track edits.
- Avoid vague prompts—be specific.
- Monitor rate and resource usage.
- Run in sandbox or isolated environments for sensitive projects.
- Validate output through tests.

---

Codex CLI is a powerful tool to augment your coding process. Use it safely, review its work, and customize it to suit your workflow needs.
