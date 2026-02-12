# -*- coding: utf-8 -*-
"""
Playwright浏览器管理器 - 工业级完整版
负责：浏览器生命周期、账号授权、自动化发布、用户名提取
整合了浏览器管理和发布任务执行的基础设施
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
from sqlalchemy.orm import Session

from backend.config import (
    BROWSER_TYPE, BROWSER_ARGS, DEFAULT_USER_AGENT,
    LOGIN_CHECK_INTERVAL, LOGIN_MAX_WAIT_TIME, PLATFORMS
)
from backend.services.crypto import encrypt_cookies, encrypt_storage_state, decrypt_cookies, decrypt_storage_state
# 注意：这里我们只导入 registry，具体的发布器注册逻辑通常在应用启动时完成
from backend.services.playwright.publishers.base import registry


class AuthTask:
    """授权任务模型"""

    def __init__(
            self,
            platform: str,
            account_id: Optional[int] = None,
            account_name: Optional[str] = None
    ):
        self.task_id = str(uuid.uuid4())
        self.platform = platform
        self.account_id = account_id
        self.account_name = account_name
        self.status = "pending"  # pending, running, success, failed, timeout
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.cookies: List[Dict] = []
        self.storage_state: Dict = {}
        self.error_message: Optional[str] = None
        self.created_at = datetime.now()
        # 授权成功后的账号ID（新账号创建后）
        self.created_account_id: Optional[int] = None


class PlaywrightManager:
    """
    Playwright 管理器 (单例模式)
    管理所有浏览器实例、授权任务和上下文
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._auth_tasks: Dict[str, AuthTask] = {}
        self._contexts: Dict[str, BrowserContext] = {}
        self._is_running = False
        # 数据库会话工厂（由外部设置，通常是 SessionLocal）
        self._db_factory: Optional[Callable] = None
        # WebSocket 通知回调
        self._ws_callback: Optional[Callable] = None

    def set_db_factory(self, db_factory: Callable):
        """设置数据库会话工厂"""
        self._db_factory = db_factory

    def set_ws_callback(self, callback: Callable):
        """设置 WebSocket 通知回调"""
        self._ws_callback = callback

    def _get_db(self) -> Optional[Session]:
        """获取数据库会话"""
        if self._db_factory:
            # 如果是生成器函数，使用 next()
            # 如果是类（如 SessionLocal），直接实例化
            try:
                db_obj = self._db_factory()
                if hasattr(db_obj, '__next__'):
                    return next(db_obj)
                return db_obj
            except Exception as e:
                logger.error(f"获取数据库会话失败: {e}")
                return None
        return None

    async def start(self):
        """启动浏览器服务"""
        if self._is_running:
            return

        logger.info("🚀 正在启动 Playwright 浏览器服务...")
        self._playwright = await async_playwright().start()

        # 尝试查找本地 Chrome 路径（绕过检测，更稳定）
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        
        # Mac OS 支持
        if sys.platform == "darwin":
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            ]

        executable_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                executable_path = path
                logger.info(f"✅ 找到本地 Chrome 浏览器: {path}")
                break

        # 构建启动参数
        # 移除重复参数，保留 config 中的配置
        args = list(BROWSER_ARGS)
        
        # 添加额外的反爬和稳定性参数
        extra_args = [
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-features=Translate",
        ]
        
        # 确保不重复添加
        for arg in extra_args:
            if arg not in args:
                args.append(arg)
                
        # Mac 特殊处理
        if sys.platform == "darwin":
            # Mac 上移除可能导致崩溃的 no-sandbox
            if "--no-sandbox" in args:
                args.remove("--no-sandbox")
            # 尝试禁用 GPU 以避免崩溃
            if "--disable-gpu" not in args:
                args.append("--disable-gpu")

        launch_options = {
            "headless": False,  # 授权和发布通常需要有头模式，或者由上层控制
            "args": args
        }

        if executable_path:
            launch_options["executable_path"] = executable_path

        try:
            self._browser = await self._playwright[BROWSER_TYPE].launch(**launch_options)
            self._is_running = True
            logger.success(f"✅ Playwright 浏览器 ({BROWSER_TYPE}) 已就绪")
        except Exception as e:
            logger.error(f"❌ 浏览器启动失败: {e}")
            raise e

    async def stop(self):
        """停止浏览器服务"""
        if not self._is_running:
            return

        # 关闭所有上下文
        for context in self._contexts.values():
            await context.close()
        self._contexts.clear()

        # 关闭浏览器
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._is_running = False
        logger.info("🛑 Playwright 浏览器服务已停止")

    # ==================== 授权相关 ====================

    async def create_auth_task(
            self,
            platform: str,
            account_id: Optional[int] = None,
            account_name: Optional[str] = None
    ) -> AuthTask:
        """
        创建授权任务：启动浏览器，打开登录页，注入JS桥接
        """
        logger.info(f"[Auth] 开始创建授权任务: platform={platform}, account_id={account_id}")

        await self.start()

        if platform not in PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")

        task = AuthTask(platform, account_id, account_name)
        self._auth_tasks[task.task_id] = task

        platform_config = PLATFORMS[platform]

        # 创建浏览器上下文
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=DEFAULT_USER_AGENT
        )
        task.context = context

        # 注入 JS 桥接函数：供前端控制页调用
        async def confirm_auth_wrapper(task_id_from_browser: str) -> str:
            """浏览器调用的确认授权函数"""
            return await self._finalize_auth(task_id_from_browser)

        await context.expose_function("confirmAuth", confirm_auth_wrapper)
        logger.info(f"[Auth] confirmAuth 函数已注入")

        # Tab 1: 打开目标平台登录页
        login_page = await context.new_page()
        task.page = login_page
        await login_page.goto(platform_config["login_url"], wait_until="domcontentloaded")

        # Tab 2: 打开本地控制页
        # 假设 static 目录在 backend 下
        static_dir = Path(__file__).parent.parent / "static"
        control_page_path = static_dir / "auth_confirm.html"

        # 兼容性处理：如果找不到文件，使用内置HTML
        if not control_page_path.exists():
            logger.warning(f"控制页模板未找到: {control_page_path}")
            # 这里可以考虑写入一个临时文件或者直接用 data:text/html
            # 为了简单，我们假设文件存在。实际部署时请确保 backend/static/auth_confirm.html 存在。

        control_page_url = f"file:///{control_page_path.as_posix()}?task_id={task.task_id}&platform={platform}"
        control_page = await context.new_page()
        try:
            await control_page.goto(control_page_url)
        except Exception as e:
            logger.error(f"打开控制页失败: {e}")

        task.status = "running"
        logger.info(f"[Auth] 授权任务就绪: {task.task_id}")

        return task

    def get_auth_task(self, task_id: str) -> Optional[AuthTask]:
        """获取授权任务"""
        return self._auth_tasks.get(task_id)

    async def _finalize_auth(self, task_id: str) -> str:
        """
        核心：提取登录凭证并入库
        """
        task = self._auth_tasks.get(task_id)
        if not task:
            return json.dumps({"success": False, "message": "任务已失效"})

        logger.info(f"[Auth] 收到确认信号: {task_id}")

        try:
            # 1. 提取 Cookies 和 Storage
            cookies = await task.context.cookies()

            # 获取 localStorage 和 sessionStorage
            storage_data = await task.page.evaluate(
                "() => ({ localStorage: {...localStorage}, sessionStorage: {...sessionStorage} })") or {}

            # 构建完整的 storage_state（必须包含 cookies 字段！）
            storage_state = {
                "cookies": cookies,
                "localStorage": storage_data.get("localStorage", {}),
                "sessionStorage": storage_data.get("sessionStorage", {})
            }

            # 2. 基础验证
            # 针对不同平台的关键 Cookie 检查 (支持多个备选Cookie，用|分隔)
            platform_checks = {
                "zhihu": "z_c0|z_cari0",  # 知乎关键Cookie，增加 z_c0 作为备选
                "baijiahao": "BDUSS|STOKEN",
                "toutiao": "sessionid|sid_tt",
                "wenku": "BDUSS|STOKEN",
                "penguin": "uin|skey|p_sktkt",
                "weixin": "pt2gguin|token|app_id|app_msgid",  # 微信公众号关键Cookie
                "wangyi": "NTES_SESS|S_INFO",
                "sohu": "ppinf|pprdig",
                "zijie": "sessionid|sid_tt",
                "xiaohongshu": "xhs_web_session|webid|web_session|webId",  # 小红书关键Cookie
                "bilibili": "bili_jct|SESSDATA",
                "36kr": "uid|ticket",
                "huxiu": "huxiu_hash|huxiusessionid",
                "woshipm": "uid|token",
                # 新增平台
                "doyin": "sessionid|passport_auth_id",
                "kuaishou": "userId|token",
                "video_account": "wxuin|webwxuvid",
                "sohu_video": "ppinf|pprdig",
                "weibo": "SUB|SUBP",
                "haokan": "BAIDUID|STOKEN",
                "xigua": "sessionid|sid_tt",
                "jianshu": "_session_id",
                "iqiyi": "P00001|P00003",
                "dayu": "e_token|e_u",
                "acfun": "acFun__web__pc__session_id",
                "tencent_video": "vqq_vusession",
                "yidian": "uid|token",
                "pipixia": "token|uid",
                "meipai": "token|uid",
                "douban": "dbcl2|ll",
                "kuai_chuan": "qi_uin|qkn",
                "dafeng": "auth_cookie|ssuid",
                "xueqiu": "xq_a_token|xq_r_token",
                "yiche": "yiche_uid|yiche_sso",
                "chejia": "autohomecookie|token",
                "duoduo": "cookie2|p_token",
                "weishi": "uin|skey",
                "mango": "mgtv_complex_id",
                "ximalaya": "device_idudi|token",
                "meituan": "token|userId",
                "alipay": "euid|ALIPAY_JWT",
                "douyin_company": "sessionid|passport_auth_id",
                "douyin_company_lead": "sessionid|passport_auth_id",
            }
            key_cookie_str = platform_checks.get(task.platform)

            # 🔍 调试：输出所有 Cookie
            logger.info(f"[Auth] 平台: {task.platform}, Cookie数量: {len(cookies)}")
            if cookies:
                cookie_names = [c['name'] for c in cookies]
                logger.info(f"[Auth] Cookie列表: {cookie_names}")
            logger.info(f"[Auth] 需要的Cookie: {key_cookie_str}")

            # 验证逻辑：如果配置了检查项，则必须包含至少一个关键Cookie
            has_auth = True  # 默认为真，只对有检查要求的平台进行验证
            if key_cookie_str:
                required_keys = key_cookie_str.split("|")
                # 检查是否存在任意一个关键Cookie（不区分大小写）
                has_auth = any(c['name'].lower() in [k.lower() for k in required_keys] for c in cookies)

                # 特殊处理：企鹅号如果已经进入后台页面，视为成功
                if task.platform == "penguin":
                    current_url = task.page.url
                    # 检查是否在企鹅号域名下
                    if "om.qq.com" in current_url:
                        # 排除登录页
                        if "userAuth" not in current_url and "login" not in current_url:
                            has_auth = True
                            logger.info(f"[Auth] 企鹅号授权成功，当前页面: {current_url}")
                        else:
                            has_auth = False

                # 特殊处理：微信公众号 - 放宽验证，只要在公众号平台域名且不在登录页就
                # 跳过严格的Cookie检查，因为微信公众号的Cookie结构复杂且多变
                if task.platform == "weixin":
                    current_url = task.page.url
                    logger.info(f"[Auth] 微信公众号当前URL: {current_url}")
                    # 微信公众号登录成功后会在公众号管理平台首页
                    # 检查URL中是否包含公众号平台特征
                    if "mp.weixin.qq.com" in current_url:
                        # 如果在登录页面，则表示未登录成功
                        if any(x in current_url for x in ["/login", "/bind", "/captcha", "/oauth"]):
                            has_auth = False
                            logger.warning(f"[Auth] 微信公众号仍在登录页，需要完成登录")
                        else:
                            # 已登录到公众号平台，直接视为成功，跳过Cookie检查
                            has_auth = True
                            logger.info(f"[Auth] 微信公众号授权成功，当前页面: {current_url}")

                if not has_auth:
                    return json.dumps({"success": False, "message": f"未检测到登录凭证 (需要包含: {key_cookie_str})，请确认已登录"})

            # 3. 提取用户名
            try:
                username = await self._extract_username(task.page, task.platform)
                logger.info(f"[Auth] 提取到用户名: {username}")
            except Exception as e:
                logger.warning(f"[Auth] 提取用户名失败: {e}")
                username = None

            # 4. 数据库操作
            db = self._get_db()
            if not db:
                return json.dumps({"success": False, "message": "数据库连接失败"})

            try:
                from backend.database.models import Account

                # 加密敏感数据
                enc_cookies = encrypt_cookies(cookies)
                enc_storage = encrypt_storage_state(storage_state)

                if task.account_id:
                    # 更新
                    account = db.query(Account).filter(Account.id == task.account_id).first()
                    if account:
                        account.cookies = enc_cookies
                        account.storage_state = enc_storage
                        account.username = username or account.username
                        account.status = 1
                        account.last_auth_time = datetime.now()
                        db.commit()
                        logger.success(f"[Auth] 账号 {account.account_name} 更新成功")
                else:
                    # 新增
                    name = task.account_name or f"{PLATFORMS[task.platform]['name']}_{username or 'User'}"
                    account = Account(
                        platform=task.platform,
                        account_name=name,
                        username=username,
                        cookies=enc_cookies,
                        storage_state=enc_storage,
                        status=1,
                        last_auth_time=datetime.now()
                    )
                    db.add(account)
                    db.commit()
                    db.refresh(account)
                    task.created_account_id = account.id
                    logger.success(f"[Auth] 新账号 {name} 创建成功")

                task.status = "success"

                # WebSocket 通知
                if self._ws_callback:
                    await self._ws_callback({
                        "type": "auth_complete",
                        "task_id": task_id,
                        "success": True,
                        "platform": task.platform
                    })

                # 延时关闭
                asyncio.create_task(self._delayed_close_task(task_id))

                return json.dumps({"success": True, "message": "授权成功！账号已保存"})

            except Exception as e:
                db.rollback()
                logger.error(f"[Auth] 数据库错误: {e}")
                return json.dumps({"success": False, "message": str(e)})
            finally:
                db.close()

        except Exception as e:
            logger.error(f"[Auth] 处理异常: {e}")
            return json.dumps({"success": False, "message": str(e)})

    async def _delayed_close_task(self, task_id: str):
        """延时关闭任务，给前端反应时间"""
        await asyncio.sleep(5)
        await self.close_auth_task(task_id)

    async def close_auth_task(self, task_id: str):
        """关闭任务资源"""
        task = self._auth_tasks.get(task_id)
        if task:
            if task.context: await task.context.close()
            if task_id in self._auth_tasks: del self._auth_tasks[task_id]
            logger.info(f"[Auth] 任务资源已释放: {task_id}")

    async def _extract_username(self, page: Page, platform: str) -> Optional[str]:
        """
        从页面提取用户名 (增强版)
        """
        try:
            if platform == "zhihu":
                # 尝试多种选择器
                selectors = [".AppHeader-profileText", ".Header-userName", ".UserLink-link", ".ProfileHeader-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "toutiao":
                selectors = [".user-name", ".name", ".mp-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "wenku":
                selectors = [".user-info-name", ".user-name", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "penguin":
                selectors = [".header-user-name", ".user-info-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "weixin":
                selectors = [".weui-desktop-account__name", ".account_name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "wangyi":
                # 增加更宽泛的选择器
                selectors = [".name", ".account-name", ".user-name", ".m-name", ".header-info .name", ".media-info .name", "div[class*='name']"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text and text.strip(): return text.strip()

            elif platform == "sohu":
                selectors = [".user-name", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "zijie":
                # 字节号（与头条号相同）
                selectors = [".user-name", ".name", ".mp-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "xiaohongshu":
                # 小红书
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "bilibili":
                # B站专栏
                selectors = [".username-text", ".user-nick", ".nickname"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "36kr":
                # 36氪
                selectors = [".user-name", ".name", ".profile-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "huxiu":
                # 虎嗅
                selectors = [".user-name", ".username", ".author-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "woshipm":
                # 人人都是产品经理
                selectors = [".user-name", ".username", ".author-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            # 新增平台的用户名提取
            elif platform == "douyin":
                selectors = [".user-name", ".username", ".nickname"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "kuaishou":
                selectors = [".user-name", ".username", ".creator-name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "video_account":
                selectors = [".user-name", ".username", ".nickname"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "sohu_video":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "weibo":
                selectors = [".ScreenName", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "haokan":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "xigua":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "jianshu":
                selectors = [".user-nick", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "iqiyi":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "dayu":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "acfun":
                selectors = [".user-name", ".username", ".nickname"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "tencent_video":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "yidian":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "pipixia":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "meipai":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "douban":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "kuai_chuan":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "dafeng":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "xueqiu":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "yiche":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "chejia":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "duoduo":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "weishi":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "mango":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "ximalaya":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "meituan":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "alipay":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "douyin_company":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            elif platform == "douyin_company_company_lead":
                selectors = [".user-name", ".username", ".name"]
                for s in selectors:
                    el = await page.query_selector(s)
                    if el:
                        text = await el.text_content()
                        if text: return text.strip()

            return None
        except:
            return None

    # ==================== 发布相关 ====================

    async def execute_publish(self, article: Any, account: Any) -> Dict[str, Any]:
        """
        供 Service 调用的发布执行入口 (核心)
        """
        await self.start()

        # 动态获取发布器
        publisher = registry.get(account.platform)
        if not publisher:
            return {"success": False, "error_msg": f"未找到平台 {account.platform} 的适配器"}

        # 准备上下文
        context = None
        try:
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

            context = await self._browser.new_context(
                storage_state=state_data if state_data else None,
                viewport={"width": 1280, "height": 800}
            )

            page = await context.new_page()

            # 执行发布逻辑
            logger.info(f"🚀 [Publish] 开始执行发布: {account.platform} - {article.title}")
            result = await publisher.publish(page, article, account)

            return result

        except Exception as e:
            logger.exception(f"❌ [Publish] 执行异常: {e}")
            return {"success": False, "error_msg": str(e)}
        finally:
            if context:
                await context.close()


# 全局单例
playwright_mgr = PlaywrightManager()