name: git-release-master
description: "Управление ветками Git, слияния с main, пуши на GitHub, семантическое версионирование, аудит Definition of Done и отслеживание багов/PR через GitHub"
mcp_servers:
  - github
  - sequential-thinking
  - filesystem
skills:
  - git-release-flow
  - test-driven-development
  - codebase-design
tools_policy:
  scope_restrictions:
    - "Перед любым слиянием в main обязателен запуск pytest через .venv/Scripts/pytest.exe"
    - "Запрещен push с флагом --force в ветку main"
    - "Обязательна проверка changelog.md и синхронизация __version__ перед выпуском релиза"

