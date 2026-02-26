# claude-project

CLI for managing [Claude.ai](https://claude.ai) Projects from the terminal — list projects, upload knowledge files, update instructions, and chat within project scope. Built for both human use and agent/script automation.

## Install

```bash
# Clone and install
cd ~/claude-project
pipx install -e ".[browser]"

# Install browser for auto-login (one-time)
playwright install chromium
```

The `[browser]` extra includes Playwright for the browser login flow. If you only plan to authenticate with `--cookie`, you can skip it:

```bash
pipx install -e .
```

## Quick Start

```bash
# Login (opens browser, captures session automatically)
claude-project auth login

# List your projects
claude-project projects list

# Get project details
claude-project projects get <project-uuid>

# Upload a knowledge doc
claude-project docs add <project-uuid> --file ./notes.md

# Chat within a project
claude-project chat send <project-uuid> "Summarize the project knowledge"

# Interactive chat
claude-project chat send <project-uuid> -i
```

## Authentication

### Browser login (default)

```bash
claude-project auth login
```

Opens Chrome to `claude.ai/login`. If you're already logged in, the session is captured immediately. Otherwise, log in and the CLI grabs the cookie automatically.

### Manual cookie

```bash
claude-project auth login --cookie <sessionKey>
```

Copy `sessionKey` from Chrome DevTools → Application → Cookies → `claude.ai`. Useful for headless servers or CI.

### Session management

```bash
claude-project auth status   # Check if authenticated
claude-project auth logout   # Clear stored credentials
```

Credentials are stored at `~/.config/claude-project/config.json` with `0600` permissions.

## Commands

### Projects

```bash
claude-project projects list [--limit N]
claude-project projects get <uuid>
claude-project projects create --name "My Project" [--description "..."] [--private]
claude-project projects update <uuid> [--name "..."] [--description "..."] \
    [--instructions "..."] [--instructions-file ./prompt.md] [--star | --unstar]
claude-project projects delete <uuid> [--confirm]
```

### Knowledge Docs

```bash
claude-project docs list <project-uuid>
claude-project docs add <project-uuid> --file ./document.md
claude-project docs add <project-uuid> --name "notes.txt" --content "inline text"
cat file.md | claude-project docs add <project-uuid> --name "piped.md"
claude-project docs rm <project-uuid> <doc-uuid>
```

### Chat

```bash
# One-shot (creates ephemeral conversation, streams response, cleans up)
claude-project chat send <project-uuid> "Your question here"

# Pipe from stdin
echo "Summarize everything" | claude-project chat send <project-uuid>

# Interactive REPL (/exit to quit)
claude-project chat send <project-uuid> -i

# Choose model
claude-project chat send <project-uuid> "question" --model claude-sonnet-4-6
```

## JSON Mode

Every command supports `--json` / `-j` for structured output:

```bash
# Pipe project list to jq
claude-project projects list --json | jq '.[].name'

# Get a project's instructions
claude-project projects get <uuid> --json | jq -r '.prompt_template'

# Chat and capture response
claude-project chat send <uuid> "question" --json | jq -r '.response'
```

In JSON mode:
- Structured JSON goes to **stdout** (pipeable)
- Rich formatting goes to **stderr** (non-interfering)
- Errors are JSON too: `{"error": "message", "code": 5}`

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Auth error (not logged in, expired session) |
| `3` | Not found |
| `4` | Rate limited |
| `5` | API error |

## Using with Scripts and Agents

The CLI is designed to be automation-friendly:

```bash
# Check auth before proceeding
claude-project auth status --json 2>/dev/null | jq -e '.status == "authenticated"' || \
    claude-project auth login --cookie "$SESSION_KEY"

# Upload all markdown files in a directory
for f in docs/*.md; do
    claude-project docs add <project-uuid> --file "$f" --json
done

# Non-interactive delete (--confirm required when stdin is not a tty)
claude-project projects delete <uuid> --confirm --json

# Pipe content from another command
pbpaste | claude-project docs add <project-uuid> --name "clipboard.md"
```

## Requirements

- Python 3.10+
- A [Claude.ai](https://claude.ai) account (Pro or Team plan)
- Chrome browser (for `auth login` without `--cookie`)
