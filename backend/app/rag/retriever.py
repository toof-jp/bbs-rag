import os

from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import LocalFileStore
from langchain.storage._lc_store import create_kv_docstore
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


def get_embeddings():
    """埋め込みモデルのインスタンスを取得"""
    return OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL, openai_api_key=settings.OPENAI_API_KEY
    )


def get_vector_store():
    """Chromaのベクトルストアインスタンスを取得"""
    # Chromaの永続化ディレクトリ（絶対パスで指定）
    persist_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../chroma_db"))
    os.makedirs(persist_directory, exist_ok=True)

    return Chroma(
        collection_name=settings.COLLECTION_NAME,
        persist_directory=persist_directory,
        embedding_function=get_embeddings(),
    )


def get_simple_retriever(vector_store: Chroma | None = None):
    """シンプルなベクトル検索リトリーバーを取得（個々のレスを検索）"""
    if vector_store is None:
        vector_store = get_vector_store()

    # 通常のベクトル検索を使用（k=10で多めに取得）
    return vector_store.as_retriever(search_kwargs={"k": 10})


def get_parent_document_retriever(vector_store: Chroma | None = None):
    """ParentDocumentRetrieverのインスタンスを取得"""
    if vector_store is None:
        vector_store = get_vector_store()

    # ドキュメントストアの設定（親ドキュメントを保存、絶対パスで指定）
    docstore_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docstore"))
    os.makedirs(docstore_path, exist_ok=True)
    file_store = LocalFileStore(docstore_path)
    docstore = create_kv_docstore(file_store)

    # 子ドキュメント用のテキストスプリッター
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400, chunk_overlap=50, separators=["\n\n", "\n", "。", "、", " ", ""]
    )

    # ParentDocumentRetrieverの作成
    retriever = ParentDocumentRetriever(
        vectorstore=vector_store,
        docstore=docstore,
        child_splitter=child_splitter,
        search_kwargs={"k": 4},  # 取得する親ドキュメントの数
    )

    return retriever


def create_retriever_chain():
    """検索チェーンを作成"""
    retriever = get_parent_document_retriever()
    return retriever


async def search_similar_documents(query: str, k: int = 4) -> list[dict]:
    """類似ドキュメントを検索して返す"""
    retriever = get_parent_document_retriever()

    # 検索実行
    docs = await retriever.aget_relevant_documents(query)

    # 結果を整形して返す
    results = []
    for doc in docs:
        results.append({"content": doc.page_content, "metadata": doc.metadata})

    return results
