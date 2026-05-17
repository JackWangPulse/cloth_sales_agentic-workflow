# 介绍

导购场景 AI 后端服务，当前只保留两条核心链路：

- 个性化推荐
- 商品检索

## 文档导航

如果你是第一次看这个项目，建议按下面顺序阅读：

- 总览看这里：[README.md](./README.md)
- 本地启动看这里：[START_SERVER.md](./START_SERVER.md)
- 服务器部署看这里：[deploy.md](./deploy.md)
- 启动后联调检查看这里：[FINAL_VERIFY.md](./FINAL_VERIFY.md)
- Trace ID / 日志链路看这里：[LOGGING_TRACE_ID_README.md](./LOGGING_TRACE_ID_README.md)
- Python 依赖清单看这里：[requirements.txt](./requirements.txt)

## 项目定位

项目基于 FastAPI 构建，使用 MySQL、Redis、FAISS 和 LLM 能力，为导购提供：

- 面向单个用户和单个商品的个性化跟进建议
- 面向导购自然语言查询的商品检索

当前 README 不再保留旧的版本演进叙事，也不再把图像接口作为对外主链路。

## 当前两条链路

### 1. 个性化推荐

核心接口：

- `POST /ai/guide/assistant`
- `POST /ai/sales/graph`
- `GET /ai/sales/graph/health`

用途：

- 判断某个用户当前是否适合跟进
- 生成导购建议、发送时机和候选话术
- 输出意图等级、推荐动作和跟进建议

典型输入：

- `user_id`
- `sku`
- `guide_id`

典型输出：

- `intent_level`
- `allowed`
- `decision_reason`
- `final_message`
- `sales_suggestion`
- `rag_chunks`

### 2. 商品检索

核心接口：

- `POST /ai/guide/assistant`
- `POST /ai/vector/search`
- `GET /ai/vector/stats`

用途：

- 根据自然语言描述检索商品
- 返回相关商品片段
- 对部分结果补充商品名和话术候选

常见检索语句：

- “找一双棕色通勤风女鞋”
- “找适合夏天穿的浅色款”
- “有没有更轻便一点的鞋”

## 推荐接入方式

推荐优先接统一入口：

- `POST /ai/guide/assistant`

当前路由规则很简单：

- 如果请求更偏“要不要跟进、怎么跟进”，走个性化推荐链路
- 如果请求更偏“找什么商品”，走商品检索链路

示例请求：

```json
{
  "query": "帮我看看这个用户现在适不适合跟进",
  "user_id": "user_001",
  "sku": "8WZ01CM1",
  "guide_id": "guide_001",
  "use_custom_plan": false
}
```

## 主要接口

### 个性化推荐

- `POST /ai/guide/assistant`
  - 统一导购入口
- `POST /ai/sales/graph`
  - 销售推荐执行链路
- `GET /ai/sales/graph/health`
  - 销售推荐链路健康检查

### 商品检索

- `POST /ai/vector/search`
  - 文本商品检索
- `GET /ai/vector/stats`
  - 查看向量索引状态

### 基础接口

- `GET /`
- `GET /health`
- `GET /api/v1/ping`
- `GET /docs`

## 本地启动

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

如果你想看依赖分组说明，直接打开 [requirements.txt](./requirements.txt)。

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并至少补齐以下配置：

```env
APP_NAME=Cloth Sales Service
APP_VERSION=5.3.0
APP_ENV=prod
DEBUG=false

DATABASE_URL=mysql+pymysql://cloth_user:cloth_password@mysql:3306/cloth_sales?charset=utf8mb4
REDIS_URL=redis://redis:6379/0

LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

EMBEDDING_API_KEY=your_embedding_api_key_here
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v2
```

本地启动的更细说明见 [START_SERVER.md](./START_SERVER.md)。

### 3. 初始化数据库

```bash
mysql -u root -p < sql/schema.sql
mysql -u root -p < sql/seed_data.sql
```

### 4. 初始化向量索引

```bash
python app/db/init_vector_store.py
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload
```

或者：

```bash
python -m uvicorn app.main:app --reload
```

启动后可访问：

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Docker 启动

当前文档对应的镜像名称：

```text
jjwang0718/cloth_sales:latest
```

启动：

```bash
docker compose up -d
```

查看日志：

```bash
docker compose logs -f cloth-sales-app
```

部署与线上排查看 [deploy.md](./deploy.md)。

## 调用示例

### 统一导购入口

```bash
curl -X POST "http://127.0.0.1:8000/ai/guide/assistant" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "帮我看看这个用户现在适不适合跟进",
    "user_id": "user_001",
    "sku": "8WZ01CM1",
    "guide_id": "guide_001"
  }'
```

### 个性化推荐

```bash
curl -X POST "http://127.0.0.1:8000/ai/sales/graph" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "sku": "8WZ01CM1",
    "guide_id": "guide_001",
    "use_custom_plan": false
  }'
```

### 商品检索

```bash
curl -X POST "http://127.0.0.1:8000/ai/vector/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "找一双棕色通勤风女鞋",
    "top_k": 5
  }'
```

## 关键代码入口

- [app/main.py](./app/main.py)
- [app/api/v1/guide_assistant.py](./app/api/v1/guide_assistant.py)
- [app/api/v1/sales_graph.py](./app/api/v1/sales_graph.py)
- [app/api/v1/vector_search.py](./app/api/v1/vector_search.py)
- [app/services/guide_assistant_service.py](./app/services/guide_assistant_service.py)

后续还会继续更新，待续。
