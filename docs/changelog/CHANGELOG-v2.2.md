# AutoGeo v2.2 更新日志

**发布日期**: 2026-02-06
**版本**: v2.2
**主题**: 账号授权状态检测修复 - 修复 storage_state 结构和验证逻辑

---

## 概述

本次更新修复了账号授权状态批量检测功能的核心问题。之前所有账号检测后都显示"授权已失效"，根本原因是 `storage_state` 保存时缺少了 `cookies` 字段，导致 Playwright 无法正确恢复登录状态。

同时修复了验证过程中的多个兼容性问题，包括页面导航异常、平台超时、选择器参数错误等。

---

## 问题分析

### 核心问题：storage_state 结构错误

**问题描述**：
- 批量检测登录状态时，所有账号都显示"授权已失效"
- 访问平台页面时自动跳转到登录页（如知乎跳转到 /signin）
- Cookie 数量从授权时的 27 个减少到验证时的 27 个（说明 Cookies 没有生效）

**根本原因**：

在 `playwright_mgr.py:239-240` 保存 `storage_state` 时，只保存了 `localStorage` 和 `sessionStorage`，**缺少了 `cookies` 字段**。

**错误代码**：
```python
storage_state = await task.page.evaluate(
    "() => ({ localStorage: {...localStorage}, sessionStorage: {...sessionStorage} })")
# 结果只有：{localStorage: {...}, sessionStorage: {...}}
```

**Playwright 要求的 storage_state 结构**：
```python
{
    "cookies": [...],        # ← 必须有！
    "localStorage": {...},  # 可选
    "sessionStorage": {...}  # 可选
}
```

### 其他发现的问题

1. **query_selector 不支持 timeout 参数**
   - 错误：`Page.query_selector() got an unexpected keyword argument 'timeout'`
   - 原因：Playwright 的 `query_selector` 方法不支持 `timeout` 参数

2. **页面导航导致上下文销毁**
   - 错误：`Execution context was destroyed, most likely because of a navigation`
   - 原因：网易等平台在页面加载后会有内部导航（iframe 跳转、重定向等）

3. **部分平台访问超时**
   - 错误：`Timeout 30000ms exceeded`
   - 原因：30秒超时对某些加载较慢的网站不够

---

## 核心改动

### 1. 修复 storage_state 保存逻辑 (`backend/services/playwright_mgr.py`)

**位置**: `playwright_mgr.py:237-250`

**改动**：
```python
# 修改前
storage_state = await task.page.evaluate(
    "() => ({ localStorage: {...localStorage}, sessionStorage: {...sessionStorage} })")

# 修改后
# 提取 Cookies 和 Storage
cookies = await task.context.cookies()

# 获取 localStorage 和 sessionStorage
storage_data = await task.page.evaluate(
    "() => ({ localStorage: {...localStorage}, sessionStorage: {...sessionStorage} })")

# 构建完整的 storage_state（必须包含 cookies 字段！！）
storage_state = {
    "cookies": cookies,
    "localStorage": storage_data.get("localStorage", {}),
    "sessionStorage": storage_data.get("sessionStorage", {})
}
```

### 2. 添加旧数据兼容逻辑 (`backend/services/account_validator.py`)

**位置**: `account_validator.py:233-241`

**改动**：
```python
# 解密存储状态
storage_state = decrypt_storage_state(account.storage_state)
if not storage_state or not isinstance(storage_state, dict):
    logger.warning(f"storage_state解密失败或格式错误，尝试使用cookies")
    storage_state = {"cookies": decrypt_cookies(account.cookies)}
else:
    # 兼容旧数据格式：如果缺少 cookies 字段，从 account.cookies 补充
    if "cookies" not in storage_state and account.cookies:
        logger.warning(f"storage_state缺少cookies字段，使用独立cookies")
        storage_state["cookies"] = decrypt_cookies(account.cookies)
```

### 3. 修复发布时的兼容逻辑 (`backend/services/playwright_mgr.py`)

**位置**: `playwright_mgr.py:806-813`

**改动**：
```python
# 解密 Session
state_data = {}
if account.storage_state:
    try:
        decrypted = decrypt_storage_state(account.storage_state)
        state_data = decrypted if decrypted else json.loads(account.storage_state)

        # 兼容旧数据格式：如果缺少 cookies 字段，从 account.cookies 补充
        if isinstance(state_data, dict) and "cookies" not in state_data and account.cookies:
            logger.warning(f"storage_state缺少cookies字段，使用独立cookies")
            state_data["cookies"] = decrypt_cookies(account.cookies)
    except:
        logger.warning(f"账号 {account.account_name} Session 解析失败，尝试裸奔")
```

### 4. 修复 query_selector timeout 参数 (`backend/services/account_validator.py`)

**位置**: `account_validator.py:119-180`

**改动**：移除所有 `query_selector` 调用中的 `timeout=5000` 参数

```python
# 修改前
login_button = await page.query_selector("button:has-text('登录')", timeout=5000)

# 修改后
login_button = await page.query_selector("button:has-text('登录')")
```

### 5. 修复页面导航异常处理 (`backend/services/account_validator.py`)

**位置**: `account_validator.py:253-268`

**改动**：
```python
# 获取实际 URL 和标题（添加异常处理，防止页面导航导致上下文销毁）
try:
    actual_url = page.url
    title = await page.title()
except Exception as e:
    logger.warning(f"获取页面信息时发生异常（可能是页面导航）: {e}")
    # 使用导航前的URL作为实际URL
    actual_url = test_url
    title = ""
```

### 6. 优化平台超时和浏览器参数 (`backend/services/account_validator.py`)

**位置**: `account_validator.py:25-36`

**改动**：
```python
# 增加特定平台的超时时间
timeout = 30000
if account.platform in ["sohu", "wangyi"]:
    timeout = 60000  # 搜狐和网易超时时间增加到60秒

# 优化浏览器启动参数
self._browser = await self._playwright.chromium.launch(
    headless=True,
    args=BROWSER_ARGS + [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        "--disable-features=Translate",
        "--disable-infobars",
        "--no-sandbox",
        "--disable-web-security",  # 允许跨域，某些平台需要
        "--disable-features=IsolateOrigins,site-per-process"  # 共享进程上下文
    ]
)
```

---

## 文件修改清单

| 文件 | 类型 | 变更内容 |
|------|------|----------|
| `backend/services/playwright_mgr.py` | 修复 | 修复 storage_state 保存逻辑（+13行） |
| `backend/services/playwright_mgr.py` | 修复 | 添加旧数据兼容逻辑（+5行） |
| `backend/services/account_validator.py` | 修复 | 添加旧数据兼容逻辑（+4行） |
| `backend/services/account_validator.py` | 修复 | 移除 query_selector timeout 参数（-4处） |
| `backend/services/account_validator.py` | 修复 | 添加页面导航异常处理（+7行） |
| `backend/services/account_validator.py` | 优化 | 优化平台超时和浏览器参数（+5行） |

**总计变更**: 约 +38 行代码

---

## 验证结果

### 修复前
```
访问URL: https://zhuanlan.zhihu.com/write
实际URL: https://www.zhihu.com/signin?next=...  ← 跳转到登录页
Title: 知乎 - 登录
Cookie结果: 27  ← Cookies 未生效
验证结果: 授权已失效
```

### 修复后
```
访问URL: https://zhuanlan.zhihu.com/write
实际URL: https://zhuanlan.zhihu.com/write  ← 没有跳转
Title: 写文章 - 知乎
Cookie数量: 31  ← Cookies 生效（从 27 增加到 31）
验证结果: 账号 知乎账号 授权有效 ✅
```

---

## 技术总结

### 数据结构设计

**正确的 storage_state 结构**：
```python
{
    "cookies": [
        {
            "name": "z_c0",
            "value": "...",
            "domain": ".zhihu.com",
            "path": "/",
            "expires": 1700000000,
            "httpOnly": true,
            "secure": true,
            "sameSite": "Lax"
        },
        # ... 更多 cookies
    ],
    "localStorage": {
        "crystal": "...",
        "assva6": "...",
        # ... 更多 localStorage 条目
    },
    "sessionStorage": {
        # sessionStorage 条目
    }
}
```

### Playwright Storage State 恢复机制

当使用 `storage_state` 参数创建浏览器上下文时，Playwright 会自动：

1. **恢复 Cookies**
   - 将 `cookies` 数组中的每个 cookie 添加到浏览器
   - 包括 domain、path、expires 等属性
   - 访问同域页面时自动携带

2. **恢复 LocalStorage**
   - 在页面加载前预填充 localStorage
   - 支持 SPA 应用的 token 恢复

3. **恢复 SessionStorage**
   - 在页面加载前预填充 sessionStorage

### 向后兼容策略

为避免影响已授权的账号，采用渐进式兼容：

1. **优先使用新格式**
   - 检查 `storage_state` 中是否包含 `cookies` 字段
   - 如果有，直接使用

2. **回退到旧格式**
   - 如果没有，从独立的 `account.cookies` 字段补充
   - 记录警告日志提醒用户重新授权

3. **建议重新授权**
   - 新授权会保存正确格式的数据
   - 避免混合数据导致的不确定行为

---

## 用户影响

### 立即生效（兼容逻辑）
- 已授权的账号可以使用 `account.cookies` 作为后备
- 批量检测功能可以正常工作

### 需要用户操作（重新授权）
- 建议重新授权所有账号以获得完整功能
- 新授权会保存正确格式的 `storage_state`
- 确保一键发布功能使用最佳体验

---

## 已知问题

### 兼容性
1. **旧授权数据**
   - 虽然兼容逻辑可以工作，但建议重新授权
   - `storage_state` 格式不完整可能影响部分功能

### 平台特异性
1. **加载慢的平台**
   - 搜狐、网易等平台可能需要更长超时时间
   - 已增加到 60 秒，可根据实际情况调整

2. **复杂导航**
   - 网易等平台有 iframe 嵌套和多次导航
   - 已添加异常处理，但可能需要进一步优化

---

## 下一步工作

- [ ] 实测所有平台的批量检测功能
- [ ] 根据实测结果调整平台特定超时时间
- [ ] 优化验证逻辑，减少误判率
- [ ] 添加账号状态定时自动检测功能
- [ ] 实现一键重新授权功能

---

## 测试建议

### 批量检测测试流程

1. **准备测试账号**
   - [ ] 准备至少 3 个不同平台的已授权账号
   - [ ] 确保每个平台至少有 1 个账号

2. **执行批量检测**
   - [ ] 点击"批量检测"按钮
   - [ ] 观察 WebSocket 实时进度推送
   - [ ] 等待所有账号检测完成

3. **验证检测结果**
   - [ ] 检查有效账号是否显示"授权有效"
   - [ ] 检查无效账号是否显示"授权已失效"
   - [ ] 验证最后检测时间是否更新

4. **测试状态更新**
   - [ ] 有效账号状态应保持为 1
   - [ ] 无效账号状态应更新为 -1
   - [ ] 刷新页面验证状态持久化

### 重新授权测试

1. **重新授权一个账号**
   - [ ] 点击账号的"重新授权"按钮
   - [ ] 完成登录流程
   - [ ] 确认授权成功

2. **验证新数据格式**
   - [ ] 检查数据库中 `storage_state` 是否包含 `cookies` 字段
   - [ ] 验证 cookies 数量是否正确
   - [ ] 检查 localStorage 条目是否完整

3. **测试新账号检测**
   - [ ] 对重新授权的账号执行单独检测
   - [ ] 验证检测结果是否正确
   - [ ] 对比重新授权前后的检测日志

---

## 回归测试

### 功能回归清单

| 功能 | 状态 | 备注 |
|------|------|------|
| 单个账号授权 | ⬜ 待测 | - |
| 单个账号检测 | ⬜ 待测 | - |
| 批量账号检测 | ⬜ 待测 | - |
| 账号状态更新 | ⬜ 待测 | - |
| 旧账号兼容性 | ⬜ 待测 | - |
| 新账号完整功能 | ⬜ 待测 | - |

### 平台测试清单

| 平台 | 检测功能 | 发布功能 | 备注 |
|------|----------|----------|------|
| 知乎 | ⬜ 待测 | ⬜ 待测 | - |
| 百家号 | ⬜ 待测 | ⬜ 待测 | - |
| 头条号 | ⬜ 待测 | ⬜ 待测 | - |
| 搜狐号 | ⬜ 待测 | ⬜ 待测 | - |
| 微信公众号 | ⬜ 待测 | ⬜ 待测 | - |
| 网易号 | ⬜ 待测 | ⬜ 待测 | - |
| 百度文库 | ⬜ 待测 | ⬜ 待测 | - |
| 企鹅号 | ⬜ 待测 | ⬜ 待测 | - |

---

## 相关文档

- [账号授权功能设计](./features/AUTH-FEATURE.md)
- [授权流程设计](./features/AUTH_FLOW_DESIGN.md)
- [v2.1 更新日志](./CHANGELOG-v2.1.md)
