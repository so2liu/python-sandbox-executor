# Python Code Runner

简单的 Python 代码执行服务器，接收代码和文件，在独立进程中执行，返回结果。

## 技术栈

- Python 3.12 + uv (包管理)
- FastAPI + Uvicorn

## 命令

```bash
# 开发
uv sync               # 安装依赖
uv run main.py        # 启动服务器 (端口 8765)

# 测试
uv run pytest         # 运行测试

# 检查
uv run ruff check .   # 代码检查

# Docker
docker build -t python-code-runner .
docker run -p 8765:8765 python-code-runner
```

## 环境变量

- `PORT` - 服务端口 (默认: `8765`)
- `JOB_DATA_DIR` - 作业数据目录 (默认: `data/jobs`)

## 项目结构

```
job_runner/
  api.py          # FastAPI 端点
  runner.py       # 代码执行器 (subprocess)
  models.py       # 数据模型 (JobSpec, JobPaths, JobResult)
  config.py       # 配置
  settings.py     # 环境变量
static/
  index.html      # 测试页面
```

## API 端点

- `GET /` - 测试页面
- `GET /health` - 健康检查
- `POST /run` - 执行代码 (同步，返回结果)
- `GET /jobs/{id}/artifacts/{filename}` - 下载产物
