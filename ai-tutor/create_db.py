"""创建MySQL数据库（如果不存在）"""
import pymysql
from app.core.config import get_settings

settings = get_settings()

# 尝试多种连接方式
connection_methods = [
    # 方式1：无密码 + mysql_native_password认证
    {
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "auth_plugin": "mysql_native_password"
    },
    # 方式2：无密码 + caching_sha2_password认证
    {
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "auth_plugin": "caching_sha2_password"
    },
    # 方式3：尝试空密码
    {
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": ""
    }
]

connection = None
for i, method in enumerate(connection_methods, 1):
    try:
        print(f"尝试连接方式 {i}...")
        connection = pymysql.connect(**method)
        print(f"✓ 连接成功（使用方式 {i})")
        break
    except Exception as e:
        print(f"× 连接失败: {e}")

if not connection:
    print("\n❌ 所有连接方式都失败！")
    print("请检查MySQL配置或手动创建数据库：")
    print("  1. 打开MySQL Workbench或命令行")
    print("  2. 执行: CREATE DATABASE IF NOT EXISTS ai_tutor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print("  3. 或在.env文件中设置正确的MYSQL_PASSWORD")
    exit(1)

try:
    with connection.cursor() as cursor:
        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.mysql_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ 数据库 '{settings.mysql_db}' 创建成功（或已存在）")

    connection.commit()
finally:
    connection.close()
    print("✓ 数据库连接关闭")

print("\n✅ 数据库配置完成，可以启动应用了！")