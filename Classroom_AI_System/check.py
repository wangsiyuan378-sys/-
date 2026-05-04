import sqlite3
import pandas as pd

# 连接你的数据库文件
conn = sqlite3.connect('data/classroom.db')

try:
    # 读取最后 15 条数据
    df = pd.read_sql_query("SELECT * FROM focus_log ORDER BY id DESC LIMIT 15", conn)

    if df.empty:
        print("💡 数据库里暂时没数据，先运行 main.py 测一下人脸！")
    else:
        print("\n--- 数据库实时记录 (最近15条) ---")
        print(df.to_string(index=False))
except Exception as e:
    print(f"❌ 读取出错: {e}")
finally:
    conn.close()