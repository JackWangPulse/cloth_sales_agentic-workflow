# 部署说明

这份文档只负责服务器部署与线上排查。

## 部署前检查

### 1. Docker 环境

```bash
docker --version
docker compose version
```

### 2. 端口

默认对外端口是 `18000`。

检查占用：

```bash
netstat -tuln | grep 18000
```

### 3. Docker 网络

```bash
docker network ls | grep cloth_sales_net
```

## 获取代码

### 方式 1：git clone

```bash
cd /opt
git clone <your-repo-url> cloth-sales-service
cd cloth-sales-service
```

### 方式 2：打包上传

本地打包：

```bash
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='logs' \
    --exclude='vector_store' \
    -czf cloth-sales-service.tar.gz .
```

上传并解压：

```bash
scp cloth-sales-service.tar.gz user@server:/opt/
ssh user@server
cd /opt
mkdir -p cloth-sales-service
tar -xzf cloth-sales-service.tar.gz -C cloth-sales-service
cd cloth-sales-service
```

## 环境变量

先复制：

```bash
cp .env.example .env
```

重点配置：

- `DATABASE_URL`
- `REDIS_URL`
- `APP_PORT`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`

### 外部 MySQL

```env
DATABASE_URL=mysql+pymysql://username:password@192.168.1.100:3306/cloth_sales?charset=utf8mb4
```

### Docker MySQL

```env
DATABASE_URL=mysql+pymysql://cloth_user:cloth_password@mysql:3306/cloth_sales?charset=utf8mb4
```

## 启动服务

### 构建并启动

```bash
docker compose build
docker compose up -d
```

### 查看日志

```bash
docker compose logs -f cloth-sales-app
```

### 查看状态

```bash
docker compose ps
```

## 常用维护命令

### 重启

```bash
docker compose restart cloth-sales-app
```

### 更新后重建

```bash
git pull
docker compose build --no-cache
docker compose up -d --force-recreate cloth-sales-app
```

### 进入容器

```bash
docker compose exec cloth-sales-app /bin/bash
```

## 部署后访问地址

- 根路径：`http://<server-ip>:18000/`
- 健康检查：`http://<server-ip>:18000/health`
- Swagger：`http://<server-ip>:18000/docs`

验证：

```bash
curl http://<server-ip>:18000/health
```

如果想看更完整的部署后检查项，直接看 [FINAL_VERIFY.md](./FINAL_VERIFY.md)。

## 常见排查

### 1. 服务没起来

```bash
docker compose ps
docker compose logs cloth-sales-app
docker compose exec cloth-sales-app /bin/bash
```

### 2. 数据库连不上

```bash
docker compose exec cloth-sales-app env | grep DATABASE_URL
docker compose exec cloth-sales-app python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
print('Database connection OK')
"
```

### 3. `/docs` 打不开

```bash
docker compose ps
docker compose port cloth-sales-app 8000
sudo ufw status
```

### 4. 要看日志和 trace_id

直接看：

- [LOGGING_TRACE_ID_README.md](./LOGGING_TRACE_ID_README.md)

## 部署建议

1. 用 HTTPS 和反向代理暴露服务
2. 给 `logs/` 做持久化
3. 数据库和 Redis 做独立监控
4. 部署完成后跑一遍 [FINAL_VERIFY.md](./FINAL_VERIFY.md)
