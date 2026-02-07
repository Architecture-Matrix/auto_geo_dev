# -*- coding: utf-8 -*-
"""
AutoGeo 数据库迁移脚本 v5.0 Final
功能：补齐 scheduled_tasks 和 geo_articles 表的所有缺失字段
使用方法：python backend/database/migrate_v5_final.py
"""

import sqlite3
import os
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / "auto_geo_v3.db"

# 需要添加的字段定义
SCHEDULED_TASKS_COLUMNS = [
    ("is_quarantined", "BOOLEAN DEFAULT 0"),
    ("quarantine_reason", "TEXT"),
    ("quarantine_at", "DATETIME"),
    ("consecutive_failures", "INTEGER DEFAULT 0"),
]

GEO_ARTICLES_COLUMNS = [
    ("next_retry_at", "DATETIME"),
]

# 默认任务配置
DEFAULT_TASKS = [
    {
        "name": "文章自动发布引擎",
        "task_key": "publish_task",
        "cron_expression": "*/1 * * * *",
        "description": "扫描待发布文章并触发浏览器自动化脚本",
        "is_active": 1
    },
    {
        "name": "全网收录实时监测",
        "task_key": "monitor_task",
        "cron_expression": "*/5 * * * *",
        "description": "通过AI搜索引擎检查已发布文章的收录状态",
        "is_active": 1
    }
]


def get_existing_columns(conn, table_name: str) -> set:
    """获取表中已存在的列名"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}
    return columns


def add_column_if_not_exists(conn, table_name: str, column_name: str, column_def: str) -> bool:
    """如果列不存在则添加"""
    existing_columns = get_existing_columns(conn, table_name)

    if column_name in existing_columns:
        print(f"  [跳过] {table_name}.{column_name} 已存在")
        return False

    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        conn.commit()
        print(f"  [成功] {table_name}.{column_name} 已添加")
        return True
    except sqlite3.OperationalError as e:
        print(f"  [失败] {table_name}.{column_name} 添加失败: {e}")
        return False


def migrate_scheduled_tasks(conn):
    """迁移 scheduled_tasks 表"""
    print("\n=== 迁移 scheduled_tasks 表 ===")
    for col_name, col_def in SCHEDULED_TASKS_COLUMNS:
        add_column_if_not_exists(conn, "scheduled_tasks", col_name, col_def)


def migrate_geo_articles(conn):
    """迁移 geo_articles 表"""
    print("\n=== 迁移 geo_articles 表 ===")
    for col_name, col_def in GEO_ARTICLES_COLUMNS:
        add_column_if_not_exists(conn, "geo_articles", col_name, col_def)


def warmup_default_tasks(conn):
    """预热默认任务数据"""
    print("\n=== 预热默认任务 ===")
    cursor = conn.cursor()

    for task in DEFAULT_TASKS:
        task_key = task["task_key"]

        # 检查任务是否存在
        cursor.execute(
            "SELECT id FROM scheduled_tasks WHERE task_key = ?",
            (task_key,)
        )
        existing = cursor.fetchone()

        if existing:
            # 更新现有任务
            cursor.execute("""
                UPDATE scheduled_tasks
                SET is_active = ?, cron_expression = ?
                WHERE task_key = ?
            """, (task["is_active"], task["cron_expression"], task_key))
            print(f"  [更新] {task['name']} (task_key={task_key})")
        else:
            # 插入新任务
            cursor.execute("""
                INSERT INTO scheduled_tasks
                (name, task_key, cron_expression, is_active, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task["name"],
                task["task_key"],
                task["cron_expression"],
                task["is_active"],
                task["description"]
            ))
            print(f"  [创建] {task['name']} (task_key={task_key})")

    conn.commit()
    print("\n  [完成] 默认任务数据已就绪")


def create_scheduler_execution_logs_table(conn):
    """创建 scheduler_execution_logs 表（如果不存在）"""
    print("\n=== 检查 scheduler_execution_logs 表 ===")
    existing_tables = get_existing_tables(conn)

    if "scheduler_execution_logs" in existing_tables:
        print("  [跳过] scheduler_execution_logs 表已存在")
        return

    try:
        conn.execute("""
            CREATE TABLE scheduler_execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_key VARCHAR(50) NOT NULL,
                article_id INTEGER,
                started_at DATETIME NOT NULL,
                finished_at DATETIME,
                duration_ms INTEGER,
                status VARCHAR(20) NOT NULL,
                result_summary TEXT,
                error_type VARCHAR(100),
                error_msg TEXT,
                error_stack_trace TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES geo_articles (id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        print("  [成功] scheduler_execution_logs 表已创建")

        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_execution_logs_task_key ON scheduler_execution_logs(task_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_execution_logs_article_id ON scheduler_execution_logs(article_id)")
        conn.commit()
        print("  [成功] 索引已创建")
    except sqlite3.OperationalError as e:
        print(f"  [失败] 创建表失败: {e}")


def get_existing_tables(conn) -> set:
    """获取所有已存在的表名"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def print_summary(conn):
    """打印迁移摘要"""
    print("\n" + "=" * 60)
    print("迁移摘要")
    print("=" * 60)

    # 检查 scheduled_tasks 表
    scheduled_cols = get_existing_columns(conn, "scheduled_tasks")
    print(f"\nscheduled_tasks 表列数: {len(scheduled_cols)}")
    for col in sorted(scheduled_cols):
        if col in [c[0] for c in SCHEDULED_TASKS_COLUMNS]:
            print(f"  [v5.0] {col}")

    # 检查 geo_articles 表
    geo_cols = get_existing_columns(conn, "geo_articles")
    print(f"\ngeo_articles 表列数: {len(geo_cols)}")
    for col in sorted(geo_cols):
        if col in [c[0] for c in GEO_ARTICLES_COLUMNS]:
            print(f"  [v5.0] {col}")

    # 检查任务数据
    cursor = conn.cursor()
    cursor.execute("SELECT name, task_key, is_active FROM scheduled_tasks")
    tasks = cursor.fetchall()
    print(f"\nscheduled_tasks 记录数: {len(tasks)}")
    for name, task_key, is_active in tasks:
        status = "启用" if is_active else "停用"
        print(f"  - {name} ({task_key}): {status}")

    print("\n" + "=" * 60)


def main():
    """主执行函数"""
    print("=" * 60)
    print("AutoGeo 数据库迁移脚本 v5.0 Final")
    print("=" * 60)
    print(f"数据库路径: {DB_PATH.absolute()}")

    if not DB_PATH.exists():
        print(f"\n[错误] 数据库文件不存在: {DB_PATH}")
        return

    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    try:
        # 开始事务
        conn.execute("BEGIN")

        # 执行迁移
        migrate_scheduled_tasks(conn)
        migrate_geo_articles(conn)
        create_scheduler_execution_logs_table(conn)
        warmup_default_tasks(conn)

        # 打印摘要
        print_summary(conn)

        print("\n[成功] 数据库迁移完成！")

    except Exception as e:
        print(f"\n[错误] 迁移过程中发生异常: {e}")
        conn.rollback()
        print("[回滚] 已回滚所有修改")
    finally:
        conn.close()


def check_clean_rebuild_option():
    """检查是否可以清理重建"""
    print("\n" + "=" * 60)
    print("清理重建建议")
    print("=" * 60)

    if not DB_PATH.exists():
        print("[提示] 数据库文件不存在，系统启动时会自动创建")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        # 检查数据量
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM geo_articles")
        article_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM accounts")
        account_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM keywords")
        keyword_count = cursor.fetchone()[0]

        total = article_count + account_count + keyword_count
        print(f"\n当前数据库数据量:")
        print(f"  - geo_articles: {article_count}")
        print(f"  - accounts: {account_count}")
        print(f"  - keywords: {keyword_count}")
        print(f"  - 总计: {total} 条记录")

        if total == 0:
            print("\n[建议] 数据库为空，可以直接删除 .db 文件重建:")
            print(f"  删除命令: del \"{DB_PATH}\"")
            print("  删除后系统启动时会自动创建完整的新数据库")
        else:
            print("\n[提示] 数据库中存在数据，建议使用迁移脚本")

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_clean_rebuild_option()
    else:
        main()
