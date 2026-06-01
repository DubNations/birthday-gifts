# Birthday Gift System

生日礼物抽奖系统 -- 输入预算，智能分配抽奖方案，用扭蛋般的体验送出心意礼物。

## 功能特性

### 用户端
- 输入预算，系统自动生成两种抽奖方案：
  - **高级优先**：优先分配高等级礼物，追求质量（均价估算）
  - **均衡多样**：最大化抽奖次数，雨露均沾（最低价估算）
- 点击抽奖券随机抽取礼物，支持**权重控制**（同等级内不同稀有度）
- 抽完后可**确认领取**或使用有限的**反悔机会**释放重抽
- 通过浏览器指纹识别用户身份，无需注册

### 管理端
- 密码登录，Token 会话持久化到数据库
- 礼物 CRUD 管理（名称、价格、链接、等级、权重）
- 统计面板：总数、可抽取、锁定中、已领取
- 导出已领取礼物 CSV 清单
- 一键重置所有礼物状态

## 技术栈

| 层 | 技术 |
|---|------|
| 前端框架 | React 18 + Vite |
| UI | Tailwind CSS + Framer Motion |
| 状态管理 | React Context |
| 后端框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | SQLite |
| 用户识别 | FingerprintJS |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 20001 --reload
```

后端默认运行在 `http://localhost:20001`，数据存储在 `gift.db`。

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:20000`，通过 Vite 代理转发 `/api` 请求到后端。

### 访问

打开浏览器访问 `http://localhost:20000`

管理后台默认密码：`admin123`（可通过环境变量修改）

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite:///./gift.db` | 数据库连接字符串 |
| `ADMIN_PASSWORD` | `admin123` | 管理员密码 |
| `ADMIN_SESSION_HOURS` | `2` | 管理员会话有效期（小时） |
| `CORS_ORIGINS` | `http://localhost:20000,http://localhost:5173` | 允许的前端域名，逗号分隔 |

## 项目结构

```
birthday-gift/
  backend/
    app/
      main.py              # FastAPI 应用入口
      config.py            # 配置项
      database.py          # 数据库初始化
      models/              # SQLAlchemy 数据模型
        gift.py            # 礼物模型（含权重字段）
        user_action.py     # 用户操作日志
        draw_session.py    # 抽奖会话
        admin_session.py   # 管理员会话（数据库持久化）
      schemas/             # Pydantic 请求/响应模型
      routers/
        admin.py           # 管理端 API
        draw.py            # 抽奖 API
      services/
        budget_allocator.py # 预算分配算法
        gift_state.py      # 礼物状态管理（锁定/领取/释放）
        identity.py        # 用户身份验证
      utils/
        helpers.py         # 工具函数
    requirements.txt
  frontend/
    src/
      api/index.js         # Axios API 封装
      store/drawStore.js   # React Context 全局状态
      hooks/               # 自定义 Hook
      pages/               # 页面组件
      components/          # UI 组件
    vite.config.js         # Vite 配置（含 API 代理）
```

## 核心机制

- **礼物锁定**：抽中后临时锁定 15 分钟，超时自动释放
- **反悔机制**：每个用户最多 1 次反悔机会（可配置）
- **权重抽奖**：同等级内按 weight 字段加权随机，weight 越大越容易抽到
- **预算控制**：只抽取价格不超过剩余预算的礼物
