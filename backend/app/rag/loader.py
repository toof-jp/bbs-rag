import json
from collections.abc import Iterator

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.res import Res


class PostgresResLoader(BaseLoader):
    """PostgreSQLのresテーブルからドキュメントをロードするカスタムローダー"""

    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size

    def lazy_load(self) -> Iterator[Document]:
        """レスデータを遅延読み込みでDocumentとして返す"""
        db: Session = SessionLocal()
        try:
            last_no = 0  # 最後に処理したレス番号
            batch_count = 0
            total_processed = 0

            while True:
                # WHERE句を使用してバッチ単位でレスを取得（OFFSETを使わない）
                res_list = (
                    db.query(Res)
                    .filter(Res.no > last_no)
                    .order_by(Res.no)
                    .limit(self.batch_size)
                    .all()
                )

                if not res_list:
                    break

                batch_count += 1
                total_processed += len(res_list)

                if batch_count % 10 == 0:
                    print(f"  [PostgresResLoader] Processed {total_processed} records...")

                for res in res_list:
                    # ドキュメントのコンテンツを作成
                    content = f"No.{res.no}: {res.main_text}"

                    # メタデータを作成
                    metadata = {
                        "no": res.no,
                        "id": res.id,
                        "datetime": res.datetime.isoformat() if res.datetime else "",
                        "datetime_text": res.datetime_text,
                        "name_and_trip": res.name_and_trip,
                        "source": f"res_no_{res.no}",
                    }

                    yield Document(page_content=content, metadata=metadata)

                # 最後のレス番号を更新
                last_no = res_list[-1].no
        except Exception as e:
            print(f"Error in PostgresResLoader: {e}")
            raise
        finally:
            db.close()

    def load(self) -> list[Document]:
        """すべてのドキュメントを一度にロード"""
        return list(self.lazy_load())


class ThreadAwareLoader(BaseLoader):
    """スライディングウィンドウ方式のドキュメントローダー（親ドキュメント用）"""

    def __init__(self, window_size: int = 50, overlap: int = 20):
        """
        Args:
            window_size: 親ドキュメントに含めるレスの数
            overlap: ウィンドウ間の重複レス数
        """
        self.window_size = window_size
        self.overlap = overlap
        self.stride = window_size - overlap  # ウィンドウの移動幅
        self.base_loader = PostgresResLoader()

    def lazy_load(self) -> Iterator[Document]:
        """スライディングウィンドウ方式で親ドキュメントを生成"""
        # まず全てのドキュメントをメモリに読み込む（メモリ効率は犠牲にして実装をシンプルに）
        all_docs = list(self.base_loader.lazy_load())

        if not all_docs:
            return

        # スライディングウィンドウで処理
        position = 0
        window_count = 0

        while position < len(all_docs):
            # ウィンドウの終端を計算
            end_position = min(position + self.window_size, len(all_docs))
            window_docs = all_docs[position:end_position]

            if window_docs:
                # 親ドキュメントを作成
                parent_content = "\n\n".join([d.page_content for d in window_docs])

                # 各レスの詳細情報も保持（citation用）
                res_details = []
                for doc in window_docs:
                    res_details.append(
                        {
                            "no": doc.metadata["no"],
                            "id": doc.metadata["id"],
                            "datetime": doc.metadata["datetime"],
                            "name_and_trip": doc.metadata["name_and_trip"],
                        }
                    )

                # メタデータは最初と最後のレスから作成
                parent_metadata = {
                    "start_no": window_docs[0].metadata["no"],
                    "end_no": window_docs[-1].metadata["no"],
                    "start_datetime": window_docs[0].metadata["datetime"],
                    "end_datetime": window_docs[-1].metadata["datetime"],
                    "res_count": len(window_docs),
                    "window_number": window_count,
                    "res_details": json.dumps(res_details, ensure_ascii=False),
                    "source": (
                        f"window_{window_count}_"
                        f"no{window_docs[0].metadata['no']}-"
                        f"{window_docs[-1].metadata['no']}"
                    ),
                }

                yield Document(page_content=parent_content, metadata=parent_metadata)
                window_count += 1

            # 次のウィンドウへ移動（重複を考慮）
            position += self.stride

            # 最後のウィンドウが小さすぎる場合は、少し戻って確実にカバー
            if position < len(all_docs) and (len(all_docs) - position) < self.overlap:
                position = len(all_docs) - self.window_size
                if position < 0:
                    position = 0

    def load(self) -> list[Document]:
        """すべての親ドキュメントを一度にロード"""
        return list(self.lazy_load())
