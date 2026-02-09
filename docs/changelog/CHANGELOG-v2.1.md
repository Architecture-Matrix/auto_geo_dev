# AutoGeo v2.1 更新日志

**发布日期**: 2026-02-05
**版本**: v2.1
**主题**: 大规模平台扩展 - 新增 25+ 平台支持

---

## 概述

本次更新是平台支持能力的重大升级，新增了25+个内容平台的完整支持，包括视频平台、社交媒体、行业垂直平台等。同时修复了部分已有平台的验证逻辑问题。

---

## 新增平台支持

### 视频平台类 (10个)
| 平台ID | 平台名称 | 功能状态 |
|--------|----------|----------|
| `douyin` | 抖音 | 新增 |
| `douyin_company` | 抖音企业号 | 新增 |
| `douyin_company_lead` | 抖音企业号（线索版） | 新增 |
| `kuaishou` | 快手 | 新增 |
| `video_account` | 视频号 | 新增 |
| `sohu_video` | 搜狐视频 | 新增 |
| `weibo` | 新浪微博 | 新增 |
| `haokan` | 好看视频 | 新增 |
| `xigua` | 西瓜视频 | 新增 |
| `tencent_video` | 腾讯视频 | 新增 |

### 内容社区类 (5个)
| 平台ID | 平台名称 | 功能状态 |
|--------|----------|----------|
| `jianshu` | 简书号 | 新增 |
| `douban` | 豆瓣 | 新增 |
| `pipixia` | 皮皮虾 | 新增 |
| `meipai` | 美拍 | 新增 |
| `weishi` | 腾讯微视 | 新增 |

### 行业垂直平台 (8个)
| 平台ID | 平台名称 | 功能状态 |
|--------|----------|----------|
| `iqiyi` | 爱奇艺 | 新增 |
| `dayu` | 大鱼号 | 新增 |
| `acfun` | AcFun | 新增 |
| `yidian` | 一点号 | 新增 |
| `dafeng` | 大风号 | 新增 |
| `xueqiu` | 雪球号 | 新增 |
| `mango` | 芒果TV | 新增 |
| `ximalaya` | 喜马拉雅 | 新增 |

### 电商/支付平台 (3个)
| 平台ID | 平台名称 | 功能状态 |
|--------|----------|----------|
| `yiche` | 易车号 | 新增 |
| `chejia` | 车家号 | 新增 |
| `meituan` | 美团 | 新增 |
| `alipay` | 支付宝 | 新增 |
| `duoduo` | 多多视频 | 新增 |

### 扩展平台
| 平台ID | 平台名称 | 功能状态 |
|--------|----------|----------|
| `custom` | 自定义 | 新增 |

---

## 已修复的平台

| 平台ID | 平台名称 | 修复内容 |
|--------|----------|----------|
| `wenku` | 百度文库 | 登录URL更新 |
| `penguin` | 企鹅号 | 验证逻辑优化（URL检测） |
| `weixin` | 微信公众号 | 正常（无改动） |
| `wangyi` | 网易号 | 正常（无改动） |

---

## 核心改动

### 1. 后端配置扩展 (`backend/config.py`)

**新增平台配置**（行数扩展：156行 → 429行）：
```python
# 示例：抖音平台配置
"douyin": {
    "id": "douyin",
    "name": "抖音",
    "code": "DY",
    "login_url": "https://www.douyin.com/",
    "publish_url": "https://creator.douyin.com/",
    "color": "#000000",
},
```

### 2. 前端配置扩展 (`fronted/src/core/config/platform.ts`)

**新增平台配置**（行数扩展：115行 → 1115行）：
- 完整的平台配置对象，包含功能开关、认证配置、发布配置、限制配置
- 统一的平台图标路径

### 3. Playwright管理器扩展 (`backend/services/playwright_mgr.py`)

#### 3.1 Cookie验证配置扩展

**位置**: `playwright_mgr.py:244-289`

新增25+平台的Cookie检查规则：
```python
platform_checks = {
    # 已有平台...
    "douyin": "sessionid|passport_auth_id",
    "kuaishou": "userId|token",
    "video_account": "wxuin|webwxuvid",
    "weibo": "SUB|SUBP",
    # ... 更多平台
}
```

#### 3.2 用户名提取逻辑扩展

**位置**: `playwright与其他.py:521-753`

为每个新平台添加用户名提取选择器：
```python
elif platform == "douyin":
    selectors = [".user-name", ".username", ".nickname"]
    for s in selectors:
        el = await page.query_selector(s)
        if el:
            text = await el.text_content()
            if text: return text.strip()
```

#### 3.3 企鹅号验证逻辑优化

**位置**: `playwright_mgr.py:299-309`

```python
# 特殊处理：企鹅号如果已经进入后台页面，视为成功
if task.platform == "penguin":
    current_url = task.page.url
    if "om.qq.com" in current_url:
        if "userAuth" not in current_url and "login" not in current_url:
            has_auth = True
            logger.info(f"[Auth] 企鹅号授权成功，当前页面: {current_url}")
```

### 4. Schema验证扩展 (`backend/schemas/__init__.py`)

**位置**: `schemas/__init__.py:59`

更新平台验证正则表达式：
```python
platform" = Field(..., description="平台ID", pattern="^(zhihu|baijiahao|sohu|toutiao|wenku|penguin|weixin|wangyi|zijie|xiaohongshu|bilibili|36kr|huxiu|woshipm|douyin|kuaishou|video_account|sohu_video|weibo|haokan|xigua|jianshu|iqiyi|dayu|acfun|tencent_video|yidian|pipixia|meipai|douban|kuai_chuan|dafeng|xueqiu|yiche|chejia|duoduo|weishi|mango|ximalaya|meituan|alipay|douyin_company|douyin_company_lead|custom)$")
```

### 5. 前端类型定义扩展 (`fronted/src/types/index.ts`)

**位置**: `types/index.ts:8-52`

新增所有平台的PlatformId类型定义：
```typescript
export type PlatformId =
  | 'zhihu'
  | 'baijiahao'
  // ... 已有平台
  | 'douyin'
  | 'kuaishou'
  | 'video_account'
  // ... 所有新平台
  | 'custom'
```

### 6. 授权确认页面更新 (`backend/static/auth_confirm.html`)

**位置**: `auth_confirm.html:242-287`

更新平台名称映射表，支持所有新平台：
```javascript
const PLATFORM_NAMES = {
    'zhihu': '知乎',
    'douyin': '抖音',
    // ... 所有平台映射
};
```

---

## 文件修改清单

| 文件 | 类型 | 变更内容 |
|------|------|----------|
| `backend/config.py` | 扩展 | 新增25+平台配置（+291行） |
| `backend/services/playwright_mgr.py` | 扩展 | 新增Cookie检查和用户名提取逻辑（+351行） |
| `backend/schemas/__init__.py` | 修改 | 更新平台验证正则（+2行） |
| `backend/static/auth_confirm.html` | 修改 | 更新平台名称映射（+41行） |
| `fronted/src/core/config/platform.ts` | 扩展 | 新增25+平台配置（+866行） |
| `fronted/src/types/index.ts` | 扩展 | 新增平台类型定义（+46行） |

**总计新增代码**: 约 1582 行

---

## 技术总结

### 设计原则

1. **一致性**
   - 所有平台配置遵循统一的结构
   - 前后端配置完全同步

2. **可扩展性**
   - 使用枚举和配置字典，便于后续新增平台
   - Cookie检查支持多个备选键（用`|`分隔）

3. **容错性**
   - 用户名提取支持多个选择器尝试
   - 企鹅号特殊处理URL验证逻辑

### 平台支持统计

| 类别 | 数量 | 平台 |
|------|------|------|
| 原有平台 | 13 | 知乎、百家号、搜狐号、头条号、百度文库、企鹅号、微信公众号、网易号、字节号、小红书、B站专栏、36氪、虎嗅、人人都是产品经理 |
| 新增视频平台 | 10 | 抖音、抖音企业号、抖音企业号（线索版）、快手、视频号、搜狐视频、新浪微博、好看视频、西瓜视频、腾讯视频 |
| 新增内容社区 | 5 | 简书号、豆瓣、皮皮虾、美拍、腾讯微视 |
| 新增垂直平台 | 8 | 爱奇艺、大鱼号、AcFun、一点号、大风号、雪球号、芒果TV、喜马拉雅 |
| 新增电商支付 | 4 | 易车号、车家号、美团、支付宝、多多视频 |
| 自定义 | 1 | 自定义 |
| **总计** | **41** | - |

### 下一步工作

- [ ] 实测新增平台的登录流程
- [ ] 实测新增平台的发布流程
- [ ] 根据实测结果调整选择器
- [ ] 为部分平台实现发布器（目前仅支持配置和登录）
- [ ] 补充平台图标资源

---

## 测试建议

### 授权测试流程

1. **视频平台测试**
   - [ ] 抖音账号授权
   - [ ] 快手账号授权
   - [ ] 视频号授权

2. **内容社区测试**
   - [ ] 简书号授权
   - [ ] 新浪微博授权

3. **验证要点**
   - 登录URL正确
   - Cookie提取有效
   - 用户名提取成功
   - 授权状态保存正确

### 平台选择器验证

各平台选择器需要实测验证，如失效需调整：
- 用户名提取选择器（`.user-name`, `.username`等）
- 发布相关选择器（标题、内容、提交按钮）

---

## 已知问题

1. **企鹅号Cookie验证**
   - 某些情况下Cookie可能不存在
   - 通过URL检测作为备选方案

2. **部分平台选择器未验证**
   - 新增平台的用户名提取选择器为通用配置
   - 需要实测后调整

3. **发布器未实现**
   - 新增平台仅有配置和登录支持
   - 发布功能需要后续实现各平台的发布器
