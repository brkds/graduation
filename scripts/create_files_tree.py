import os
import argparse
import sqlite3
from sqlite3 import Error

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn

def create_tables(conn):
    try:
        cursor = conn.cursor()
        # 创建目录表，支持嵌套（使用 parent_id 表示父目录）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS directories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES directories (id)
            );
        ''')
        # 创建文件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                directory_id INTEGER,
                FOREIGN KEY (directory_id) REFERENCES directories (id)
            );
        ''')
        conn.commit()
    except Error as e:
        print(e)

def insert_directory(conn, name, parent_id=None):
    sql = '''INSERT INTO directories(name, parent_id) VALUES(?,?)'''
    cursor = conn.cursor()
    cursor.execute(sql, (name, parent_id))
    conn.commit()
    return cursor.lastrowid  # 返回新插入的目录 ID

def insert_file(conn, file_name, file_path, directory_id):
    sql = '''INSERT INTO files(file_name, file_path, directory_id) VALUES(?,?,?)'''
    cursor = conn.cursor()
    cursor.execute(sql, (file_name, file_path, directory_id))
    conn.commit()

def scan_directory(conn, path, parent_id=None):
    dir_id = insert_directory(conn, os.path.basename(path), parent_id)  # 插入当前目录
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                # 递归扫描子目录
                scan_directory(conn, item_path, dir_id)
            elif item_path.endswith(('.h', '.c')):  # 只处理 .h 和 .c 文件
                insert_file(conn, item, item_path, dir_id)
    except Exception as e:
        print(f"Error scanning {path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Scan directory and update SQLite database.")
    parser.add_argument('--db', required=True, help='Path to the SQLite database file')
    parser.add_argument('--dir', required=True, help='Path to the directory to scan')
    args = parser.parse_args()

    # 解析后的参数
    db_file = args.db
    directory_to_scan = args.dir

    # 可选：转换为绝对路径（更健壮）
    db_file = os.path.abspath(db_file)
    directory_to_scan = os.path.abspath(directory_to_scan)

    conn = create_connection(db_file)
    if conn:
        create_tables(conn)  # 创建表
        scan_directory(conn, directory_to_scan)
        conn.close()

if __name__ == '__main__':
    main() 