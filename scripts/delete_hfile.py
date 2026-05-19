import sqlite3
from pathlib import Path

def merge_duplicate_functions(db_path: str) -> bool:
    """
    Merge duplicate function records in the database, keeping .c records and removing .h records.
    Updates foreign keys in related tables to reference the .c record's function_id.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION;")

        # 更新 AccessRelations 表
        update_access_relations_sql = """
        UPDATE AccessRelations
        SET function_id = (
            SELECT c.id
            FROM Functions c
            JOIN Functions h ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
            WHERE h.id = AccessRelations.function_id
        )
        WHERE function_id IN (
            SELECT h.id
            FROM Functions h
            JOIN Functions c ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
        );
        """
        cursor.execute(update_access_relations_sql)

        # 更新 CallRelations 表 (caller_function_id)
        update_call_relations_caller_sql = """
        UPDATE CallRelations
        SET caller_function_id = (
            SELECT c.id
            FROM Functions c
            JOIN Functions h ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
            WHERE h.id = CallRelations.caller_function_id
        )
        WHERE caller_function_id IN (
            SELECT h.id
            FROM Functions h
            JOIN Functions c ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
        );
        """
        cursor.execute(update_call_relations_caller_sql)

        # 更新 CallRelations 表 (callee_function_id)
        update_call_relations_callee_sql = """
        UPDATE CallRelations
        SET callee_function_id = (
            SELECT c.id
            FROM Functions c
            JOIN Functions h ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
            WHERE h.id = CallRelations.callee_function_id
        )
        WHERE callee_function_id IN (
            SELECT h.id
            FROM Functions h
            JOIN Functions c ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
        );
        """
        cursor.execute(update_call_relations_callee_sql)

        # 更新 FunctionPointers 表
        update_function_pointers_sql = """
        UPDATE FunctionPointers
        SET points_to_func_id = (
            SELECT c.id
            FROM Functions c
            JOIN Functions h ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
            WHERE h.id = FunctionPointers.points_to_func_id
        )
        WHERE points_to_func_id IN (
            SELECT h.id
            FROM Functions h
            JOIN Functions c ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
        );
        """
        cursor.execute(update_function_pointers_sql)

        # 删除 .h 文件的记录
        delete_header_functions_sql = """
        DELETE FROM Functions
        WHERE id IN (
            SELECT h.id
            FROM Functions h
            JOIN Functions c ON c.name = h.name 
                AND h.file_path LIKE '%.h'
                AND c.file_path LIKE '%.c'
                AND REPLACE(h.file_path, '.h', '') = REPLACE(c.file_path, '.c', '')
        );
        """
        cursor.execute(delete_header_functions_sql)

        conn.commit()
        print("Duplicate functions merged successfully.")
        return True

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error occurred: {e}")
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "../linux.db"
    if not Path(db_path).exists():
        print(f"Database file {db_path} does not exist.")
    else:
        success = merge_duplicate_functions(db_path)
        if success:
            print("Operation completed successfully.")
        else:
            print("Operation failed.")
