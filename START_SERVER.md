# 本地启动说明

这份文档只负责本地启动说明。

## 启动前准备

### 1. Python 环境

需要 Python 3.10+。

创建虚拟环境：

```bash
python -m venv .venv
```

激活环境：

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

### 2. 环境变量

复制配置：

```bash
copy .env.example .env
```

Linux / macOS:

```bash
cp .env.example .env
```

至少保证这些配置正确：

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/cloth_sales?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
APP_NAME=Cloth Sales Service
APP_VERSION=5.3.0
DEBUG=false
```

如果你本地会调用大模型和向量检索，也要补齐对应的 LLM 与 Embedding 配置。

### 3. 初始化数据库

```bash
mysql -u root -p < sql/schema.sql
mysql -u root -p < sql/seed_data.sql
```

### 4. 初始化向量索引

商品检索链路依赖向量索引，首次启动前建议执行：

```bash
python app/db/init_vector_store.py
```

## 启动服务

### 方式 1：uvicorn

```bash
uvicorn app.main:app --reload
```

### 方式 2：python -m uvicorn

```bash
python -m uvicorn app.main:app --reload
```

## 启动后检查

启动成功后默认访问：

- 根路径：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/health`
- API Ping：`http://127.0.0.1:8000/api/v1/ping`
- Swagger：`http://127.0.0.1:8000/docs`

快速验证：

```bash
curl http://127.0.0.1:8000/health
```

PowerShell:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

更完整的联调检查见 [FINAL_VERIFY.md](./FINAL_VERIFY.md)。

## 常用接口

### 个性化推荐

```bash
curl -X POST "http://127.0.0.1:8000/ai/sales/graph" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "sku": "8WZ01CM1",
    "guide_id": "guide_001"
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

## 排查顺序

如果本地起不来，建议按这个顺序排查：

1. 看 [requirements.txt](./requirements.txt) 依赖是否装齐
2. 看 `.env` 是否正确
3. 看 MySQL / Redis 是否可连
4. 看向量索引是否已初始化
5. 看 [LOGGING_TRACE_ID_README.md](./LOGGING_TRACE_ID_README.md) 里的日志说明
