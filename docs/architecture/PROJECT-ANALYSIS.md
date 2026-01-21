# AutoGeo 项目综合架构分析报告

> **文档说明**：本文档是项目架构的全面分析报告，包含技术栈、目录结构、核心模块、数据流、潜在问题和改进建议等内容。
>
> **更新时间**：2025-01-14
> **维护者**：开发者

---

## 一、项目概览

### 1.1 项目定位

**AutoGeo** 是一个智能多平台文章发布助手，采用 **Electron + Vue3 + FastAPI + Playwright** 技术栈构建的桌面应用。主要功能是帮助用户一键将文章发布到多个内容平台。

### 1.2 核心特性

| 特性 | 描述 |
|-----|------|
| **多平台发布** | 支持知乎、百家号、搜狐号、头条号 |
| **账号管理** | 安全的 Cookie 加密存储和授权管理 |
| **批量发布** | 支持一篇文章发布到多个平台/账号 |
| **实时进度** | WebSocket 推送发布进度 |
| **桌面应用** | Electron 跨平台客户端 |

### 1.3 技术栈总览

| 层级 | 技术选型 | 版本 |
|-----|---------|------|
| **前端框架** | Vue 3 + TypeScript | 3.4.0, 5.3.0 |
| **构建工具** | Vite | 5.0.0 |
| **状态管理** | Pinia | 2.1.7 |
| **UI组件库** | Element Plus | 2.5.0 |
| **桌面框架** | Electron | 28.0.0 |
| **后端框架** | FastAPI | 0.109.0 |
| **异步运行时** | Uvicorn | 0.27.0 |
| **数据库ORM** | SQLAlchemy | 2.0.25 |
| **数据库** | SQLite | - |
| **浏览器自动化** | Playwright | 1.40.0 |
| **加密** | cryptography | 41.0.7 |

---

## 二、项目整体结构

### 2.1 目录布局

```
auto_geo/
├── backend/                    # 后端服务
│   ├── api/                    # API 路由层
│   │   ├── account.py          # 账号管理 API
│   │   ├── article.py          # 文章管理 API
│   │   └── publish.py          # 发布管理 API
│   ├── database/               # 数据库层
│   │   ├── __init__.py         # 数据库初始化
│   │   ├── models.py           # ORM 模型定义
│   │   └── auto_geo_v3.db      # SQLite 数据库文件
│   ├── schemas/                # Pydantic 数据模型
│   │   └── __init__.py         # 请求/响应模型
│   ├── services/               # 业务服务层
│   │   ├── crypto.py           # 加密服务
│   │   ├── playwright_mgr.py   # Playwright 管理器（核心）
│   │   ├── publisher.py        # 发布服务（旧版）
│   │   └── playwright/         # Playwright 平台适配器
│   │       └── publishers/     # 各平台发布器
│   │           ├── base.py     # 基础发布器
│   │           ├── zhihu.py    # 知乎发布器
│   │           ├── baijiahao.py # 百家号发布器
│   │           ├── sohu.py     # 搜狐发布器
│   │           └── toutiao.py  # 头条发布器
│   ├── static/                 # 静态文件
│   │   └── auth_confirm.html   # 授权确认页面
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置文件
│   └── requirements.txt        # Python 依赖
│
├── fronted/                    # 前端应用（拼写保留）
│   ├── electron/               # Electron 主进程
│   │   ├── main/               # 主进程代码
│   │   │   ├── index.ts        # 主进程入口
│   │   │   ├── window-manager.ts    # 窗口管理
│   │   │   ├── ipc-handlers.ts      # IPC 处理器
│   │   │   ├── tray-manager.ts      # 系统托盘
│   │   │   └── backend-manager.ts   # 后端进程管理
│   │   ├── preload/            # 预加载脚本
│   │   │   └── index.ts        # 安全桥接层
│   │   └── resources/          # 资源文件
│   │       └── icons/          # 应用图标
│   │
│   ├── src/                    # Vue 渲染进程源码
│   │   ├── main.ts             # Vue 应用入口
│   │   ├── App.vue             # 根组件
│   │   ├── assets/             # 静态资源
│   │   │   ├── images/
│   │   │   │   └── platforms/  # 平台 logo
│   │   │   └── styles/         # 全局样式
│   │   ├── components/         # 组件层
│   │   │   ├── business/       # 业务组件
│   │   │   │   ├── account/    # 账号相关组件
│   │   │   │   ├── article/    # 文章相关组件
│   │   │   │   └── publish/    # 发布相关组件
│   │   │   └── common/         # 通用组件
│   │   ├── composables/        # 组合式函数
│   │   │   ├── useAccount.ts   # 账号相关 hooks
│   │   │   ├── useArticle.ts   # 文章相关 hooks
│   │   │   ├── usePublish.ts   # 发布相关 hooks
│   │   │   ├── usePlatform.ts  # 平台相关 hooks
│   │   │   ├── useRequest.ts   # 请求封装
│   │   │   └── useWebSocket.ts # WebSocket 封装
│   │   ├── core/               # 核心层
│   │   │   ├── config/         # 配置管理
│   │   │   ├── platform/       # 平台适配系统
│   │   │   ├── constants/      # 常量定义
│   │   │   ├── utils/          # 工具函数
│   │   │   └── decorators/     # 装饰器
│   │   ├── router/             # 路由配置
│   │   │   └── index.ts        # 路由定义
│   │   ├── services/           # 服务层
│   │   │   ├── api/            # HTTP API 服务
│   │   │   │   └── index.ts    # axios 封装
│   │   │   ├── websocket/      # WebSocket 服务
│   │   │   │   └── index.ts    # WS 客户端
│   │   │   ├── ipc/            # IPC 服务
│   │   │   └── storage/        # 本地存储服务
│   │   ├── stores/             # 状态管理
│   │   │   └── modules/        # Pinia Store 模块
│   │   │       ├── account.ts  # 账号状态
│   │   │       ├── article.ts  # 文章状态
│   │   │       └── platform.ts # 平台状态
│   │   ├── types/              # TypeScript 类型定义
│   │   ├── views/              # 页面视图
│   │   │   ├── layout/         # 布局组件
│   │   │   ├── account/        # 账号管理页面
│   │   │   ├── article/        # 文章管理页面
│   │   │   ├── publish/        # 发布页面
│   │   │   └── settings/       # 设置页面
│   │   └── locale/             # 国际化（预留）
│   │
│   ├── package.json            # Node 依赖配置
│   ├── vite.config.ts          # Vite 配置
│   ├── tsconfig.json           # TypeScript 配置
│   └── electron.vite.config.ts # Electron Vite 配置
│
├── docs/                       # 项目文档
│   ├── architecture/           # 架构设计文档
│   ├── features/               # 功能说明文档
│   ├── testing/                # 测试文档
│   ├── overview/               # 项目总览
│   ├── security/               # 安全文档
│   └── changelog/              # 变更日志
│
├── .cookies/                   # Cookie 存储目录
├── .env                        # 环境变量（不提交）
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略配置
└── README.md                   # 项目说明
```

### 2.2 模块划分

#### 后端模块（Python FastAPI）
1. **API 层** (`api/`): 处理 HTTP 请求，路由分发
2. **数据层** (`database/`): ORM 模型、数据库操作
3. **业务层** (`services/`): 核心业务逻辑
4. **数据模型** (`schemas/`): Pydantic 请求/响应模型

#### 前端模块（Vue + Electron）
1. **Electron 主进程** (`electron/main/`): 窗口管理、IPC 通信、后端进程管理
2. **渲染进程** (`src/`): Vue 应用
   - **视图层** (`views/`): 页面组件
   - **组件层** (`components/`): 可复用组件
   - **状态层** (`stores/`): Pinia 状态管理
   - **服务层** (`services/`): API 调用、WebSocket、IPC
   - **组合层** (`composables/`): 业务逻辑 hooks

---

## 三、数据模型设计

### 3.1 核心数据表

**文件位置**: `backend/database/models.py`

#### Account 表 - 账号信息

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| platform | String | 平台ID (zhihu/baijiahao/sohu/toutiao) |
| account_name | String | 账号备注名称 |
| username | String | 登录账号/用户名 |
| cookies | Text | 加密的 Cookies |
| storage_state | Text | 加密的 localStorage |
| user_agent | String | 浏览器 UA |
| status | Integer | 状态：1=正常 0=禁用 -1=过期 |
| last_auth_time | DateTime | 最后授权时间 |
| remark | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### Article 表 - 文章内容

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| title | String | 文章标题 |
| content | Text | 正文内容（Markdown/HTML） |
| tags | String | 标签，逗号分隔 |
| category | String | 文章分类 |
| cover_image | String | 封面图片URL |
| status | Integer | 状态：0=草稿 1=已发布 |
| view_count | Integer | 查看次数 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| published_at | DateTime | 首次发布时间 |

#### PublishRecord 表 - 发布记录

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| article_id | Integer | 外键 -> articles.id |
| account_id | Integer | 外键 -> accounts.id |
| publish_status | Integer | 0=待发布 1=发布中 2=成功 3=失败 |
| platform_url | String | 发布后的文章链接 |
| error_msg | Text | 错误信息 |
| retry_count | Integer | 重试次数 |
| created_at | DateTime | 创建时间 |
| published_at | DateTime | 发布时间 |

---

## 四、API 路由设计

### 4.1 账号管理 API

**文件位置**: `backend/api/account.py`

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/accounts` | 获取账号列表 |
| POST | `/api/accounts` | 创建账号 |
| GET | `/api/accounts/{id}` | 获取账号详情 |
| PUT | `/api/accounts/{id}` | 更新账号 |
| DELETE | `/api/accounts/{id}` | 删除账号 |
| POST | `/api/accounts/auth/start` | 开始授权（打开浏览器） |
| GET | `/api/accounts/auth/status/{task_id}` | 查询授权状态 |
| POST | `/api/accounts/auth/confirm/{task_id}` | 确认授权完成 |
| DELETE | `/api/accounts/auth/task/{task_id}` | 取消授权任务 |

### 4.2 文章管理 API

**文件位置**: `backend/api/article.py`

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/articles` | 获取文章列表 |
| POST | `/api/articles` | 创建文章 |
| GET | `/api/articles/{id}` | 获取文章详情 |
| PUT | `/api/articles/{id}` | 更新文章 |
| DELETE | `/api/articles/{id}` | 删除文章 |

### 4.3 发布管理 API

**文件位置**: `backend/api/publish.py`

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/publish/create` | 创建发布任务 |
| GET | `/api/publish/progress/{task_id}` | 查询发布进度 |
| GET | `/api/publish/records` | 获取发布记录 |
| POST | `/api/publish/retry/{record_id}` | 重试发布 |
| GET | `/api/publish/platforms` | 获取支持的平台列表 |

### 4.4 WebSocket

| 路径 | 说明 |
|------|------|
| `/ws` | WebSocket 连接（实时推送进度） |

---

## 五、核心服务层

### 5.1 Playwright 管理器

**文件位置**: `backend/services/playwright_mgr.py`

这是后端的核心模块，负责：

#### 浏览器管理
- 启动/停止 Chromium 浏览器
- 支持使用本地 Chrome 而非 Chromium（避免被检测）
- 创建独立的浏览器上下文

#### 授权流程
```python
async def create_auth_task(platform, account_id, account_name):
    # 1. 创建浏览器上下文
    # 2. 暴露 confirmAuth 函数到浏览器（绕过 CORS）
    # 3. 打开平台登录页
    # 4. 打开本地确认页面（auth_confirm.html）
    # 5. 用户在平台登录后，点击确认页面的按钮
    # 6. 提取 cookies 和 localStorage
    # 7. 验证关键 cookie 是否存在
    # 8. 自动创建或更新账号记录
```

#### 用户名提取
授权成功后自动提取平台用户名，支持：
- 知乎
- 百家号
- 搜狐
- 头条

### 5.2 平台发布器

**文件位置**: `backend/services/playwright/publishers/`

采用**适配器模式**，每个平台一个发布器类：

```python
class BasePublisher(ABC):
    @abstractmethod
    async def publish(page, article, account):
        """发布文章 - 子类必须实现"""
        pass

class ZhihuPublisher(BasePublisher):
    async def publish(page, article, account):
        # 知乎特定的发布逻辑

class BaijiahaoPublisher(BasePublisher):
    async def publish(page, article, account):
        # 百家号特定的发布逻辑（先进入首页，再点击图文）
```

### 5.3 加密服务

**文件位置**: `backend/services/crypto.py`

使用 AES-256 加密 Cookies 和 localStorage：
```python
def encrypt_cookies(cookies):
    # AES-256 加密
    return fernet.encrypt(json.dumps(cookies).encode())

def decrypt_cookies(encrypted):
    # AES-256 解密
    return json.loads(fernet.decrypt(encrypted))
```

### 5.4 配置文件

**文件位置**: `backend/config.py`

```python
# 服务配置
HOST = "127.0.0.1"
PORT = 8001  # 避开 8000 端口的 Windows 残留占用
RELOAD = False  # Windows 上 Playwright 需要 ProactorEventLoop，与 reload 冲突

# 数据库配置
DATABASE_URL = "sqlite:///backend/database/auto_geo_v3.db"

# 加密配置
ENCRYPTION_KEY = os.getenv("AUTO_GEO_ENCRYPTION_KEY", default_key).encode()[:32]

# 平台配置
PLATFORMS = {
    "zhihu": {
        "id": "zhihu",
        "name": "知乎",
        "login_url": "https://www.zhihu.com/signin",
        "publish_url": "https://zhuanlan.zhihu.com/write",
        "color": "#0084FF",
    },
    "baijiahao": { ... },
    "sohu": { ... },
    "toutiao": { ... },
}
```

---

## 六、前端架构详解

### 6.1 Electron 架构

#### 主进程入口

**文件位置**: `fronted/electron/main/index.ts`

```typescript
// 应用生命周期
app.whenReady().then(async () => {
    // 注册 IPC 处理器
    ipcHandlers.registerHandlers()

    // 创建主窗口
    mainWindow = windowManager.createMainWindow()

    // 创建系统托盘
    trayManager.createTray(mainWindow)
})
```

#### 窗口管理

**文件位置**: `fronted/electron/main/window-manager.ts`

```typescript
export function createMainWindow(): BrowserWindow {
    const mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: join(__dirname, '../preload/index.js'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true,
        },
    })

    // 开发环境加载 Vite 服务器，生产环境加载打包文件
    const isDev = process.env.NODE_ENV === 'development'
    const URL = isDev
        ? 'http://127.0.0.1:5173'
        : formatFileUrl('index.html')

    mainWindow.loadURL(URL)
    return mainWindow
}
```

#### 后端管理

**文件位置**: `fronted/electron/main/backend-manager.ts`

负责启动和管理 Python 后端进程：

```typescript
class BackendManager {
    async start(): Promise<boolean> {
        // 1. 检查 Python 是否可用
        // 2. 检查后端目录是否存在
        // 3. spawn('python', ['main.py'], { cwd: backendDir })
        // 4. 启动健康检查（每 10 秒）
    }

    stop(): void {
        // Windows: taskkill /F /T /PID {pid}
        // Linux/Mac: kill SIGTERM
    }
}
```

**注意**：当前实现中，后端不再由 Electron 自动启动，需要用户手动启动。

#### Preload 脚本

**文件位置**: `fronted/electron/preload/index.ts`

安全桥接层，使用 `contextBridge` 暴露 API 给渲染进程：

```typescript
contextBridge.exposeInMainWorld('electronAPI', {
    minimizeWindow: () => ipcRenderer.send('window:minimize'),
    maximizeWindow: () => ipcRenderer.send('window:maximize'),
    closeWindow: () => ipcRenderer.send('window:close'),
    // ... 其他 API
})
```

### 6.2 Vue 应用架构

#### 路由设计

**文件位置**: `fronted/src/router/index.ts`

```typescript
const routes = [
    {
        path: '/',
        component: () => import('@/views/layout/MainLayout.vue'),
        children: [
            { path: 'dashboard', component: DashboardPage, meta: { title: '概览' } },
            { path: 'accounts', component: AccountList, meta: { title: '账号管理' } },
            { path: 'articles', component: ArticleList, meta: { title: '文章管理' } },
            { path: 'publish', component: PublishPage, meta: { title: '批量发布' } },
            { path: 'history', component: PublishHistory, meta: { title: '发布记录' } },
            { path: 'settings', component: SettingsPage, meta: { title: '设置' } },
        ],
    },
]
```

#### 状态管理

使用 **Pinia** 进行状态管理：

**account.ts** - 账号状态
```typescript
export const useAccountStore = defineStore('account', () => {
    const accounts = ref<Account[]>([])
    const selectedAccountIds = ref<number[]>([])
    const loading = ref(false)

    async function loadAccounts(platform?: string) {
        // 从后端获取账号列表
    }

    async function startAuth(platform, accountId?, accountName?) {
        // 开始授权流程
    }

    async function checkAuthStatus(taskId) {
        // 轮询授权状态
    }

    return { accounts, loadAccounts, startAuth, ... }
})
```

#### API 服务层

**文件位置**: `fronted/src/services/api/index.ts`

```typescript
// axios 实例配置
const instance = axios.create({
    baseURL: '/api',
    timeout: 30000,
})

// 账号 API
export const accountApi = {
    getList: (params?) => get('/accounts', params),
    create: (data) => post('/accounts', data),
    startAuth: (data) => post('/accounts/auth/start', data),
    getAuthStatus: (taskId) => get(`/accounts/auth/status/${taskId}`),
    // ...
}
```

#### WebSocket 服务

**文件位置**: `fronted/src/services/websocket/index.ts`

实时接收发布进度：

```typescript
class WebSocketService {
    connect(url: string) {
        this.ws = new WebSocket(url)
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            // 分发到相应的处理器
            this.handlers[data.type]?.(data)
        }
    }

    on(type: string, handler: Function) {
        this.handlers[type] = handler
    }
}
```

---

## 七、数据流和通信设计

### 7.1 通信架构图

```
┌─────────────────────────────────────────────────────────────┐
│                       通信架构图                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Vue 渲染进程          Python 后端                           │
│  ┌──────────┐        ┌──────────┐                          │
│  │ API 服务  │───────►│ FastAPI  │                          │
│  │ (axios)  │  HTTP  │          │                          │
│  └──────────┘        └──────────┘                          │
│       ▲                    ▲                                │
│       │                    │                                │
│       │ Vite Proxy         │                                │
│       │                    │                                │
│  ┌───┴────────┐      ┌───┴──────────┐                     │
│  │ Vite Dev   │      │   Uvicorn    │                     │
│  │ Server     │      │   Server     │                     │
│  │ :5173      │      │   :8001      │                     │
│  └────────────┘      └──────────────┘                     │
│                                                              │
│  Vue 渲染进程          Python 后端                           │
│  ┌──────────┐        ┌──────────┐                          │
│  │WebSocket │◄───────►│WebSocket │                          │
│  │ Service  │   WS   │ Manager   │                          │
│  └──────────┘        └──────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 授权流程详解

```
┌──────────────────────────────────────────────────────────────┐
│                      授权流程                                 │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. 用户点击"开始授权"按钮                                     │
│     │                                                          │
│     ▼                                                          │
│  2. Vue 调用 POST /api/accounts/auth/start                   │
│     { platform: 'zhihu', account_name: '测试账号' }           │
│     │                                                          │
│     ▼                                                          │
│  3. Python 后端创建 AuthTask                                  │
│     - 启动 Playwright 浏览器                                  │
│     - 创建浏览器上下文                                        │
│     - 暴露 confirmAuth 函数到浏览器                            │
│     - 打开两个标签页：                                        │
│       • 知乎登录页                                            │
│       • 本地确认页 (auth_confirm.html)                        │
│     │                                                          │
│     ▼                                                          │
│  4. 用户在知乎登录页完成扫码/密码登录                          │
│     │                                                          │
│     ▼                                                          │
│  5. 用户点击本地确认页的"授权完成"按钮                         │
│     │                                                          │
│     ▼                                                          │
│  6. confirmAuth 函数被调用                                    │
│     - 提取 cookies 和 localStorage                            │
│     - 验证关键 cookie (z_c0) 是否存在                         │
│     - 自动创建或更新 Account 记录                              │
│     - 通过 WebSocket 通知前端                                 │
│     │                                                          │
│     ▼                                                          │
│  7. Vue 收到 WebSocket 消息                                   │
│     - 刷新账号列表                                            │
│     - 显示授权成功提示                                        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 发布流程详解

```
┌──────────────────────────────────────────────────────────────┐
│                      发布流程                                 │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. 用户选择文章和账号，点击"开始发布"                         │
│     │                                                          │
│     ▼                                                          │
│  2. Vue 调用 POST /api/publish/create                         │
│     { article_ids: [1], account_ids: [1, 2] }                │
│     │                                                          │
│     ▼                                                          │
│  3. Python 后端创建发布任务                                   │
│     - 生成任务 ID (UUID)                                      │
│     - 创建 PublishRecord 记录（状态=待发布）                   │
│     - 后台异步执行发布任务                                     │
│     - 返回 task_id 给前端                                     │
│     │                                                          │
│     ▼                                                          │
│  4. Vue 建立 WebSocket 连接，监听进度                         │
│     │                                                          │
│     ▼                                                          │
│  5. Python 执行发布任务                                       │
│     for each (article, account) 组合:                         │
│       - 加载账号的 cookies 和 storage                         │
│       - 创建浏览器上下文                                      │
│       - 导航到平台发布页                                      │
│       - 填充标题和正文                                        │
│       - 点击发布按钮                                          │
│       - 等待发布结果                                          │
│       - 更新 PublishRecord 状态                               │
│       - 通过 WebSocket 推送进度                               │
│     │                                                          │
│     ▼                                                          │
│  6. Vue 实时更新 UI                                           │
│     - 显示发布进度条                                          │
│     - 显示成功/失败状态                                       │
│     - 显示发布后的文章链接                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 7.4 WebSocket 消息格式

```json
// 发布进度消息
{
    "type": "publish_progress",
    "task_id": "uuid",
    "data": {
        "article_id": 1,
        "article_title": "文章标题",
        "account_id": 1,
        "account_name": "测试账号",
        "platform": "zhihu",
        "platform_name": "知乎",
        "status": 2,  // 0=待发布 1=发布中 2=成功 3=失败
        "platform_url": "https://zhuanlan.zhihu.com/p/xxx",
        "error_msg": null
    }
}

// 授权完成消息
{
    "type": "auth_complete",
    "task_id": "uuid",
    "platform": "zhihu",
    "account_id": 1,
    "success": true
}
```

---

## 八、配置和环境设置

### 8.1 环境变量

**文件位置**: `.env.example`

```bash
# AES-256 加密密钥（32字节）
AUTO_GEO_ENCRYPTION_KEY=your-32-byte-encryption-key-change-this

# 可选配置
HOST=127.0.0.1
PORT=8001
DEBUG=false
DATABASE_URL=sqlite:///backend/database/auto_geo_v3.db
```

### 8.2 Vite 配置

**文件位置**: `fronted/vite.config.ts`

```typescript
export default defineConfig({
    plugins: [
        vue(),
        AutoImport({
            imports: ['vue', 'vue-router', 'pinia'],
            dts: 'src/types/auto-imports.d.ts',
        }),
        Components({
            resolvers: [ElementPlusResolver()],
            dts: 'src/types/components.d.ts',
        }),
    ],
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
        },
    },
    server: {
        host: '127.0.0.1',     // 强制 IPv4，Electron 才能连上
        port: 5173,
        strictPort: true,      // 端口被占用时报错
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
            '/ws': {
                target: 'ws://127.0.0.1:8001',
                ws: true,
            },
        },
    },
    build: {
        outDir: 'out/renderer',
        emptyOutDir: true,
    },
})
```

### 8.3 关键端口一览

| 服务 | 地址 | 说明 |
|-----|------|------|
| **Vite Dev Server** | http://127.0.0.1:5173 | 前端开发服务器（仅开发环境） |
| **Python FastAPI** | http://127.0.0.1:8001 | 后端 API 服务 |
| **WebSocket** | ws://127.0.0.1:8001/ws | 实时通信（开发时通过 Vite 代理） |

---

## 九、潜在问题和改进建议

### 9.1 架构设计问题

| 问题 | 严重程度 | 说明 | 建议 |
|-----|---------|------|------|
| 后端需手动启动 | 🔴 高 | Electron不再自动启动Python后端，用户体验差 | 添加后端状态检查UI，或提供"一键启动"按钮 |
| Windows平台判断多 | 🟡 中 | 代码中有大量 `if sys.platform == "win32"` 判断 | 抽象平台差异到独立模块 |
| Playwright事件循环冲突 | 🟡 中 | Windows上Playwright需要ProactorEventLoop，与Uvicorn的reload冲突 | 考虑使用独立进程运行Playwright |

### 9.2 代码质量问题

| 问题 | 严重程度 | 说明 | 建议 |
|-----|---------|------|------|
| 注释风格不统一 | 🟡 中 | 混用中英文注释，含有非正式用语 | 统一使用英文或中文注释 |
| 错误处理不够细致 | 🟡 中 | 部分异常捕获后只记录日志，没有向用户反馈 | 区分可恢复和不可恢复错误，给用户明确提示 |
| 类型定义不完整 | 🟡 中 | 前端TypeScript类型定义较少，大量使用`any` | 完善接口类型定义 |

### 9.3 安全问题

| 问题 | 严重程度 | 说明 | 建议 |
|-----|---------|------|------|
| 默认加密密钥 | 🔴 高 | 使用硬编码的加密密钥 | 强制用户在生产环境设置自己的密钥 |
| IPC安全 | ✅ 已处理 | 已使用`contextBridge`和白名单机制 | 添加消息来源验证 |
| SQL注入 | ✅ 已处理 | 使用SQLAlchemy ORM，已避免SQL注入 | - |

### 9.4 性能问题

| 问题 | 严重程度 | 说明 | 建议 |
|-----|---------|------|------|
| 发布任务并发控制 | 🟡 中 | 最多3个并发发布任务，不可配置 | 可配置并发数，考虑使用任务队列 |
| WebSocket无心跳 | 🟡 中 | 无法检测断连 | 添加定时心跳，实现自动重连 |
| 数据库查询优化 | 🟢 低 | 发布记录查询没有使用索引 | 为常用查询字段添加索引 |

### 9.5 可扩展性问题

| 问题 | 严重程度 | 说明 | 建议 |
|-----|---------|------|------|
| 新增平台步骤较多 | 🟡 中 | 需要修改多个文件 | 实现平台自动发现机制 |
| 前端硬编码平台信息 | 🟡 中 | 平台logo、颜色等硬编码在前端 | 从后端API获取平台配置 |

### 9.6 测试问题

| 问题 | 严重程度 | 说明 | 建议 |
|-----|---------|------|------|
| 缺少单元测试 | 🔴 高 | 代码中没有发现单元测试文件 | 为核心业务逻辑添加单元测试 |
| 缺少E2E测试 | 🟡 中 | 没有端到端测试 | 使用Playwright编写E2E测试 |

---

## 十、核心文件清单

### 10.1 后端核心文件

| 文件路径 | 职责 |
|---------|------|
| `backend/main.py` | FastAPI 应用入口，WebSocket 管理 |
| `backend/config.py` | 配置文件（平台、数据库、加密等） |
| `backend/database/models.py` | ORM 模型定义 |
| `backend/schemas/__init__.py` | Pydantic 请求/响应模型 |
| `backend/api/account.py` | 账号管理 API |
| `backend/api/publish.py` | 发布管理 API |
| `backend/services/playwright_mgr.py` | Playwright 管理器（核心） |
| `backend/services/crypto.py` | 加密服务 |
| `backend/services/playwright/publishers/base.py` | 基础发布器 |
| `backend/services/playwright/publishers/zhihu.py` | 知乎发布器 |
| `backend/services/playwright/publishers/baijiahao.py` | 百家号发布器 |
| `backend/static/auth_confirm.html` | 授权确认页面 |

### 10.2 前端核心文件

| 文件路径 | 职责 |
|---------|------|
| `fronted/electron/main/index.ts` | Electron 主进程入口 |
| `fronted/electron/main/backend-manager.ts` | 后端进程管理 |
| `fronted/electron/main/window-manager.ts` | 窗口管理 |
| `fronted/electron/preload/index.ts` | Preload 安全桥接 |
| `fronted/src/main.ts` | Vue 应用入口 |
| `fronted/src/router/index.ts` | 路由配置 |
| `fronted/src/stores/modules/account.ts` | 账号状态管理 |
| `fronted/src/services/api/index.ts` | API 服务封装 |
| `fronted/src/services/websocket/index.ts` | WebSocket 服务 |
| `fronted/src/composables/useAccount.ts` | 账号相关 hooks |
| `fronted/src/composables/usePublish.ts` | 发布相关 hooks |
| `fronted/src/views/account/AccountList.vue` | 账号列表页 |
| `fronted/src/views/publish/PublishPage.vue` | 发布页面 |
| `fronted/vite.config.ts` | Vite 配置 |

### 10.3 配置文件

| 文件路径 | 职责 |
|---------|------|
| `.env` | 环境变量（不提交） |
| `.env.example` | 环境变量模板 |
| `backend/requirements.txt` | Python 依赖 |
| `fronted/package.json` | Node 依赖 |
| `fronted/vite.config.ts` | Vite 构建配置 |
| `fronted/tsconfig.json` | TypeScript 配置 |

---

## 十一、总结

### 11.1 架构优点

1. **清晰的分层架构** — 前后端分离，职责明确
2. **适配器模式** — 新增平台只需添加发布器，符合开闭原则
3. **安全设计** — Cookie加密存储、IPC白名单、contextBridge隔离
4. **实时通信** — WebSocket推送发布进度，用户体验好
5. **类型安全** — 前端TypeScript，后端Pydantic

### 11.2 需要改进的地方

1. **后端自动启动** — 目前需要手动启动，用户体验待优化
2. **测试覆盖** — 缺少单元测试和E2E测试
3. **错误处理** — 部分异常处理不够细致
4. **代码风格** — 注释风格不统一，含有非正式用语
5. **平台扩展** — 新增平台步骤较多，可以更自动化

### 11.3 技术亮点

1. **Playwright 授权创新** — 使用 `expose_function` 绕过 CORS，用户体验流畅
2. **本地 Chrome 支持** — 避免被平台检测为自动化工具
3. **多选择器备选** — 百家号发布器使用多个选择器，提高鲁棒性
4. **用户名自动提取** — 授权成功后自动提取平台用户名

---

**文档版本**：v1.0
**分析时间**：2025-01-14
**维护者**：开发者
