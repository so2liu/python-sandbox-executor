# Python Code Runner

简单的 Python 代码执行服务器。接收 Python 代码和文件，在独立进程中执行，返回结果和产物。

## 快速开始

```bash
uv sync               # 安装依赖
uv run main.py        # 启动服务器 (默认端口 8765)
```

打开浏览器访问 http://localhost:8765 即可使用测试页面。

## 环境变量

- `PORT` - 服务端口 (默认: `8765`)
- `JOB_DATA_DIR` - 作业数据目录 (默认: `data/jobs`)

## API

### `GET /health`
健康检查。

```bash
curl http://localhost:8765/health
# {"status":"ok"}
```

### `POST /run`
执行 Python 代码（同步，等待完成返回结果）。

**参数** (multipart/form-data):
- `spec` - JSON 格式的作业配置
- `code_files` - 代码文件（至少包含入口文件）
- `input_files` - 输入文件（可选）

**JobSpec JSON**:
```json
{
  "entry": "main.py",
  "args": [],
  "timeout_sec": 60,
  "env": {}
}
```

**示例**:
```bash
curl -X POST http://localhost:8765/run \
  -F 'spec={"entry":"main.py","timeout_sec":30}' \
  -F 'code_files=@main.py'
```

**响应**:
```json
{
  "job_id": "abc123...",
  "status": "succeeded",
  "exit_code": 0,
  "error": null,
  "logs": "[runner] starting job...\nHello World\n[runner] finished with code 0\n",
  "artifacts": ["result.xlsx"]
}
```

### `GET /jobs/{job_id}/artifacts/{filename}`
下载作业产物文件。

```bash
curl -O http://localhost:8765/jobs/abc123/artifacts/result.xlsx
```

## 项目结构

```
job_runner/
├── api.py          # FastAPI 端点
├── runner.py       # 代码执行器
├── models.py       # 数据模型 (JobSpec, JobPaths, JobResult)
├── config.py       # 配置
├── settings.py     # 环境变量
└── static_utils.py # 静态文件工具
static/
└── index.html      # 测试页面
```

## Docker

```bash
docker build -t python-code-runner .
docker run -p 8765:8765 python-code-runner
```

## 测试

```bash
uv run pytest
```

## 内置库

服务器环境包含以下常用库：

**数据处理**
- numpy, pandas, openpyxl, xlsxwriter

**可视化** (支持中文)
- matplotlib, seaborn, plotly

**地理/GIS**
- geopandas, shapely, pyproj, geopy

**科学计算**
- scipy, scikit-learn

**其他**
- requests, httpx, pillow, pyyaml, python-dateutil
