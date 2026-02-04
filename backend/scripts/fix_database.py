# -*- coding: utf-8 -*-
"""
修复数据库表结构脚本
"""

import sqlite3
import os
from pathlib import Path

# 数据库路径
BASE_DIR = Path(__file__).resolve().parent.parent
db_path = BASE_DIR / "database" / "auto_geo_v3.db"

print(f"数据库路径: {db_path}")

if not db_path.exists():
    print("数据库文件不存在，退出")
    exit(1)

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查geo_articles表结构
print("\n检查geo_articles表结构...")
cursor.execute("PRAGMA table_info(geo_articles)")
columns = cursor.fetchall()
print("现有列:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# 检查是否存在publish_time列
has_publish_time = any(col[1] == 'publish_time' for col in columns)
print(f"\npublish_time列存在: {has_publish_time}")

# 如果不存在publish_time列，添加它
if not has_publish_time:
    print("添加publish_time列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN publish_time DATETIME")
        conn.commit()
        print("✓ publish_time列添加成功")
    except Exception as e:
        print(f"✗ 添加publish_time列失败: {e}")
        conn.rollback()

# 检查其他可能缺失的列
print("\n检查其他可能缺失的列...")

# 检查last_check_time列
has_last_check_time = any(col[1] == 'last_check_time' for col in columns)
print(f"last_check_time列存在: {has_last_check_time}")

if not has_last_check_time:
    print("添加last_check_time列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN last_check_time DATETIME")
        conn.commit()
        print("✓ last_check_time列添加成功")
    except Exception as e:
        print(f"✗ 添加last_check_time列失败: {e}")
        conn.rollback()

# 检查index_details列
has_index_details = any(col[1] == 'index_details' for col in columns)
print(f"index_details列存在: {has_index_details}")

if not has_index_details:
    print("添加index_details列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN index_details TEXT")
        conn.commit()
        print("✓ index_details列添加成功")
    except Exception as e:
        print(f"✗ 添加index_details列失败: {e}")
        conn.rollback()

# 检查quality_status列
has_quality_status = any(col[1] == 'quality_status' for col in columns)
print(f"quality_status列存在: {has_quality_status}")

if not has_quality_status:
    print("添加quality_status列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN quality_status TEXT DEFAULT 'pending'")
        conn.commit()
        print("✓ quality_status列添加成功")
    except Exception as e:
        print(f"✗ 添加quality_status列失败: {e}")
        conn.rollback()

# 检查quality_score列
has_quality_score = any(col[1] == 'quality_score' for col in columns)
print(f"quality_score列存在: {has_quality_score}")

if not has_quality_score:
    print("添加quality_score列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN quality_score INTEGER")
        conn.commit()
        print("✓ quality_score列添加成功")
    except Exception as e:
        print(f"✗ 添加quality_score列失败: {e}")
        conn.rollback()

# 检查ai_score列
has_ai_score = any(col[1] == 'ai_score' for col in columns)
print(f"ai_score列存在: {has_ai_score}")

if not has_ai_score:
    print("添加ai_score列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN ai_score INTEGER")
        conn.commit()
        print("✓ ai_score列添加成功")
    except Exception as e:
        print(f"✗ 添加ai_score列失败: {e}")
        conn.rollback()

# 检查readability_score列
has_readability_score = any(col[1] == 'readability_score' for col in columns)
print(f"readability_score列存在: {has_readability_score}")

if not has_readability_score:
    print("添加readability_score列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN readability_score INTEGER")
        conn.commit()
        print("✓ readability_score列添加成功")
    except Exception as e:
        print(f"✗ 添加readability_score列失败: {e}")
        conn.rollback()

# 检查retry_count列
has_retry_count = any(col[1] == 'retry_count' for col in columns)
print(f"retry_count列存在: {has_retry_count}")

if not has_retry_count:
    print("添加retry_count列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN retry_count INTEGER DEFAULT 0")
        conn.commit()
        print("✓ retry_count列添加成功")
    except Exception as e:
        print(f"✗ 添加retry_count列失败: {e}")
        conn.rollback()

# 检查error_msg列
has_error_msg = any(col[1] == 'error_msg' for col in columns)
print(f"error_msg列存在: {has_error_msg}")

if not has_error_msg:
    print("添加error_msg列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN error_msg TEXT")
        conn.commit()
        print("✓ error_msg列添加成功")
    except Exception as e:
        print(f"✗ 添加error_msg列失败: {e}")
        conn.rollback()

# 检查publish_logs列
has_publish_logs = any(col[1] == 'publish_logs' for col in columns)
print(f"publish_logs列存在: {has_publish_logs}")

if not has_publish_logs:
    print("添加publish_logs列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN publish_logs TEXT")
        conn.commit()
        print("✓ publish_logs列添加成功")
    except Exception as e:
        print(f"✗ 添加publish_logs列失败: {e}")
        conn.rollback()

# 检查platform_url列
has_platform_url = any(col[1] == 'platform_url' for col in columns)
print(f"platform_url列存在: {has_platform_url}")

if not has_platform_url:
    print("添加platform_url列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN platform_url TEXT")
        conn.commit()
        print("✓ platform_url列添加成功")
    except Exception as e:
        print(f"✗ 添加platform_url列失败: {e}")
        conn.rollback()

# 检查index_status列
has_index_status = any(col[1] == 'index_status' for col in columns)
print(f"index_status列存在: {has_index_status}")

if not has_index_status:
    print("添加index_status列...")
    try:
        cursor.execute("ALTER TABLE geo_articles ADD COLUMN index_status TEXT DEFAULT 'uncheck'")
        conn.commit()
        print("✓ index_status列添加成功")
    except Exception as e:
        print(f"✗ 添加index_status列失败: {e}")
        conn.rollback()

# 关闭连接
conn.close()
print("\n数据库表结构检查和修复完成")
