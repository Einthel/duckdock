name: code-review
description: "Многоосевое ревью кода и Pre-Flight Gatekeeper перед run_gui.bat/build.bat (Инварианты GEMINI.md, Безопасность, Чистота Diff) без внесения правок"
mcp_servers:
  - serena
  - sequential-thinking
  - memory-bank
  - filesystem
skills:
  - code-review
  - security-and-hardening
  - ast-grep
  - codebase-design
  - python-pro
  - sqlite-migrations
  - lan7-frontend-vanilla
  - test-driven-development
  - git-release-flow
tools_policy:
  read_only: true
  forbidden_actions:
    - write_file
    - edit_file
    - delete_file
    - execute_destructive_commands

