"""
数据库迁移脚本 - 添加新功能字段
执行方式: python migrate_add_new_features.py
"""
import sqlite3
from pathlib import Path


def get_database_path():
    """获取数据库路径"""
    # 假设数据库在项目根目录的 data 文件夹
    db_path = Path(__file__).resolve().parents[2] / "data" / "sd_sorter.db"

    # 如果不存在，尝试其他位置
    if not db_path.exists():
        db_path = Path("sd_sorter.db")

    return db_path


def migrate_database():
    """执行数据库迁移"""
    db_path = get_database_path()

    print(f"数据库路径: {db_path}")

    if not db_path.exists():
        print("⚠️  数据库文件不存在，将在首次运行时自动创建")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    migrations = [
        # 美学评分字段
        {
            "name": "aesthetic_score",
            "sql": "ALTER TABLE images ADD COLUMN aesthetic_score REAL DEFAULT NULL",
            "check": "SELECT COUNT(*) FROM pragma_table_info('images') WHERE name='aesthetic_score'"
        },
        # CLIP embedding 字段
        {
            "name": "clip_embedding",
            "sql": "ALTER TABLE images ADD COLUMN clip_embedding BLOB DEFAULT NULL",
            "check": "SELECT COUNT(*) FROM pragma_table_info('images') WHERE name='clip_embedding'"
        },
        # 画师识别字段（未来使用）
        {
            "name": "artist_name",
            "sql": "ALTER TABLE images ADD COLUMN artist_name TEXT DEFAULT NULL",
            "check": "SELECT COUNT(*) FROM pragma_table_info('images') WHERE name='artist_name'"
        },
        {
            "name": "artist_confidence",
            "sql": "ALTER TABLE images ADD COLUMN artist_confidence REAL DEFAULT NULL",
            "check": "SELECT COUNT(*) FROM pragma_table_info('images') WHERE name='artist_confidence'"
        },
        # 打码标记字段（未来使用）
        {
            "name": "is_censored",
            "sql": "ALTER TABLE images ADD COLUMN is_censored INTEGER DEFAULT 0",
            "check": "SELECT COUNT(*) FROM pragma_table_info('images') WHERE name='is_censored'"
        },
        {
            "name": "censor_regions",
            "sql": "ALTER TABLE images ADD COLUMN censor_regions TEXT DEFAULT NULL",
            "check": "SELECT COUNT(*) FROM pragma_table_info('images') WHERE name='censor_regions'"
        },
    ]

    print("\n开始数据库迁移...\n")

    for migration in migrations:
        name = migration["name"]
        sql = migration["sql"]
        check = migration["check"]

        # 检查字段是否已存在
        cursor.execute(check)
        exists = cursor.fetchone()[0] > 0

        if exists:
            print(f"✓ 字段 '{name}' 已存在，跳过")
        else:
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"✓ 成功添加字段 '{name}'")
            except sqlite3.Error as e:
                print(f"✗ 添加字段 '{name}' 失败: {e}")

    # 创建索引
    indexes = [
        {
            "name": "idx_images_aesthetic",
            "sql": "CREATE INDEX IF NOT EXISTS idx_images_aesthetic ON images(aesthetic_score)",
        },
        {
            "name": "idx_images_artist",
            "sql": "CREATE INDEX IF NOT EXISTS idx_images_artist ON images(artist_name)",
        },
    ]

    print("\n创建索引...\n")

    for index in indexes:
        name = index["name"]
        sql = index["sql"]

        try:
            cursor.execute(sql)
            conn.commit()
            print(f"✓ 成功创建索引 '{name}'")
        except sqlite3.Error as e:
            print(f"✗ 创建索引 '{name}' 失败: {e}")

    conn.close()

    print("\n✅ 数据库迁移完成！\n")


if __name__ == "__main__":
    migrate_database()
