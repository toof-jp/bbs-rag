#!/usr/bin/env python
"""
データベースのインデックスを確認するスクリプト
"""
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text

def check_indexes():
    """データベースのインデックスを確認"""
    with engine.connect() as conn:
        # resテーブルのインデックスを確認
        result = conn.execute(text("""
            SELECT 
                indexname,
                indexdef
            FROM 
                pg_indexes
            WHERE 
                tablename = 'res'
                AND schemaname = 'public'
            ORDER BY 
                indexname;
        """))
        
        print("=== Indexes on 'res' table ===")
        for row in result:
            print(f"Index: {row[0]}")
            print(f"Definition: {row[1]}")
            print()
        
        # インデックスが存在しない場合の推奨
        result_count = conn.execute(text("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = 'res' 
            AND schemaname = 'public'
            AND indexname LIKE '%no%'
        """)).scalar()
        
        if result_count == 0:
            print("\n⚠️  WARNING: No index found on 'no' column!")
            print("Recommended: CREATE INDEX idx_res_no ON public.res (no);")
            print("This will significantly improve loading performance.")

if __name__ == "__main__":
    check_indexes()