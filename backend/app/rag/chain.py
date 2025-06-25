import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, cast

from pydantic import SecretStr

from langchain.callbacks.base import AsyncCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.rag.retriever import get_parent_document_retriever


class StreamingCallbackHandler(AsyncCallbackHandler):
    """ストリーミング用のコールバックハンドラー"""

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """新しいトークンが生成されたときに呼ばれる"""
        await self.queue.put(token)

    async def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """LLMの生成が終了したときに呼ばれる"""
        await self.queue.put(None)  # 終了シグナル


def get_rag_prompt() -> ChatPromptTemplate:
    """RAG用のプロンプトテンプレートを取得"""
    template = """あなたは賢い掲示板のアシスタントです。
提供された掲示板の過去ログの文脈を元に、ユーザーの質問に日本語で回答してください。
文脈に答えがない場合は、無理に答えを生成せず「分かりません」と回答してください。

【文脈】
{context}

【質問】
{question}

【回答】
"""
    return ChatPromptTemplate.from_template(template)


def format_docs(docs: list[Any]) -> str:
    """検索結果のドキュメントをフォーマット"""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


async def extract_relevant_posts(docs: list[Any], question: str) -> list[dict[str, Any]]:
    """検索結果から質問に関連する具体的なレス番号を抽出"""
    if not docs:
        return []

    # 各チャンクから関連レスを抽出
    all_citations = []

    # Citation抽出用のLLM（コスト削減のため軽量モデルを使用）
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",  # 軽量モデルで十分
        temperature=0,  # 正確性重視
        api_key=SecretStr(settings.OPENAI_API_KEY),
    )

    citation_prompt = ChatPromptTemplate.from_template(
        """
以下の掲示板の会話から、質問「{question}」に最も関連するレス番号を最大5つ選んでください。
レス番号は「No.123」の形式で記載されています。

【掲示板の内容】
{content}

【出力形式】
関連するレス番号をカンマ区切りで出力してください。例: 123,456,789
関連するレスがない場合は「なし」と出力してください。
"""
    )

    # レス番号→詳細情報のマッピングを作成
    res_info_map = {}

    for doc in docs:
        try:
            # res_detailsを取得（JSON文字列として保存されている）
            res_details_str = doc.metadata.get("res_details", "[]")
            res_details = json.loads(res_details_str)

            # マッピングに追加
            for res in res_details:
                res_info_map[res["no"]] = res

            # LLMに関連レスの抽出を依頼
            response = await llm.ainvoke(
                citation_prompt.format(question=question, content=doc.page_content)
            )

            # レス番号を抽出
            result = response.content.strip() if isinstance(response.content, str) else ""
            if result and result != "なし":
                numbers = [int(n.strip()) for n in result.split(",") if n.strip().isdigit()]
                # マッピングに存在するレス番号のみを採用
                for num in numbers:
                    if num in res_info_map:
                        all_citations.append(
                            {
                                "no": num,
                                "id": res_info_map[num].get("id", ""),
                                "datetime": res_info_map[num].get("datetime", ""),
                                "name_and_trip": res_info_map[num].get("name_and_trip", ""),
                            }
                        )
        except Exception as e:
            print(f"Citation extraction error: {e}")
            continue

    # 重複を除去（レス番号でユニーク化）してソート
    seen = set()
    unique_citations = []
    for citation in all_citations:
        if citation["no"] not in seen:
            seen.add(citation["no"])
            unique_citations.append(citation)

    return sorted(unique_citations, key=lambda x: x["no"])


def extract_sources(docs: list[Any]) -> list[dict[str, Any]]:
    """ドキュメントからソース情報を抽出"""
    sources = []
    for doc in docs:
        metadata = doc.metadata
        source_info = {
            "start_no": metadata.get("start_no", 0),
            "end_no": metadata.get("end_no", 0),
            "start_datetime": metadata.get("start_datetime", ""),
            "end_datetime": metadata.get("end_datetime", ""),
            "res_count": metadata.get("res_count", 1),
        }
        sources.append(source_info)
    return sources


def format_source_citations(sources: list[dict[str, Any]]) -> list[dict[str, str]]:
    """ソース情報を表示用にフォーマット"""
    formatted_sources = []

    for source in sources:
        start_no = source["start_no"]
        end_no = source["end_no"]

        # 投稿番号の範囲を作成
        if start_no == end_no:
            post_range = f"No.{start_no}"
        else:
            post_range = f"No.{start_no}-{end_no}"

        # 日時をフォーマット
        start_datetime = source.get("start_datetime", "")
        if start_datetime:
            try:
                dt = datetime.fromisoformat(start_datetime)
                formatted_date = dt.strftime("%Y/%m/%d %H:%M:%S")
            except ValueError:
                formatted_date = start_datetime
        else:
            formatted_date = ""

        formatted_sources.append(
            {"range": post_range, "datetime": formatted_date, "count": source["res_count"]}
        )

    return formatted_sources


async def create_rag_chain(streaming: bool = True) -> Any:
    """RAGチェーンを作成"""
    # コンポーネントの初期化
    retriever = get_parent_document_retriever()
    prompt = get_rag_prompt()

    # LLMの設定
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=SecretStr(settings.OPENAI_API_KEY),
        streaming=streaming,
    )

    # チェーンの構築
    chain: Any = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


async def ask_with_streaming(question: str) -> AsyncIterator[str]:
    """ストリーミングで質問に回答し、最後に出典情報も送信"""
    # キューの作成
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    # コールバックハンドラーの作成
    callback = StreamingCallbackHandler(queue)

    # LLMの設定（ストリーミング有効）
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=SecretStr(settings.OPENAI_API_KEY),
        streaming=True,
        callbacks=[callback],
    )

    # コンポーネントの初期化
    retriever = get_parent_document_retriever()
    prompt = get_rag_prompt()

    # 先に検索を実行してソース情報を取得
    docs = await retriever.ainvoke(question)

    # 具体的なレス番号を抽出（LLMを使用）
    citations = await extract_relevant_posts(docs, question)

    # ドキュメントをフォーマット
    context = format_docs(docs)

    # チェーンの構築
    chain: Any = (
        {"context": lambda _: context, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 非同期でチェーンを実行
    task = asyncio.create_task(chain.ainvoke(question))

    # キューからトークンを取り出してyield
    while True:
        token = await queue.get()
        if token is None:  # 終了シグナル
            break
        yield token

    # タスクの完了を待つ
    await task

    # 最後に出典情報を送信（特別なトークンとして）
    if citations:
        citation_data = {"type": "citations", "citations": citations}
        yield f"\n\n[CITATION_START]{json.dumps(citation_data, ensure_ascii=False)}[CITATION_END]"


async def ask_question(question: str) -> str:
    """質問に対して回答を生成（非ストリーミング）"""
    chain = await create_rag_chain(streaming=False)
    response = await chain.ainvoke(question)
    return cast(str, response)
