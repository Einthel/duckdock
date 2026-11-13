name: deep-researcher
description: "Глубокий архитектурный анализ кодовой базы, поиск связей и аудит без внесения правок"
mcp_servers:
  - serena
  - memory-bank
  - sequential-thinking
  - filesystem
  - context7
skills:
  - codebase-design
  - improve-codebase-architecture
tools_policy:
  read_only: true
  forbidden_actions:
    - write_file
    - edit_file
    - delete_file
    - execute_destructive_commands

