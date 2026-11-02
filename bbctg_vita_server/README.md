# bbctg_vita_server

FastAPI 后端，入口 `server.py`。

日常请用仓库根的 `start_dev.bat` / `start_dev.sh` 启停：它们会先补依赖，Linux 上还会构建前端并探活。单独调试后端时，在本目录执行 `python server.py`；运行前需备好 `config/<env>/vita_server.env` 并初始化数据库。

测试：本目录执行 `python -m pytest -q`；代码检查：`ruff check .`（CI 同步执行）。

文档：[docs/backend-structure.md](../docs/backend-structure.md) · [docs/deploy.md](../docs/deploy.md)
