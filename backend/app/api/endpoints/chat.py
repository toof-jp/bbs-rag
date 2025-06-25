import json
from collections.abc import AsyncIterator
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.rag.chain import ask_question, ask_with_streaming
from app.rag.schemas import AskRequest

router = APIRouter()


async def generate_sse_events(question: str) -> AsyncIterator[str]:
    """SSE形式のイベントを生成"""
    try:
        buffer = ""
        citation_processing = False

        async for token in ask_with_streaming(question):
            buffer += token

            # [CITATION_START]の検出
            if "[CITATION_START]" in buffer and not citation_processing:
                citation_start_idx = buffer.find("[CITATION_START]")
                # [CITATION_START]より前のテキストを送信
                if citation_start_idx > 0:
                    text_before = buffer[:citation_start_idx]
                    data = json.dumps(
                        {"type": "token", "token": text_before, "done": False}, ensure_ascii=False
                    )
                    yield data
                    buffer = buffer[citation_start_idx:]
                citation_processing = True

            # 引用情報の処理中
            if citation_processing and "[CITATION_END]" in buffer:
                citation_end_idx = buffer.find("[CITATION_END]")
                citation_content = buffer[: citation_end_idx + len("[CITATION_END]")]

                # 引用情報を抽出
                citation_json = citation_content.replace("[CITATION_START]", "").replace(
                    "[CITATION_END]", ""
                )
                try:
                    citation_data = json.loads(citation_json)
                    # 出典情報イベントとして送信
                    data = json.dumps(
                        {
                            "type": "citations",
                            "citations": citation_data["citations"],
                            "done": False,
                        },
                        ensure_ascii=False,
                    )
                    yield data
                except Exception as e:
                    print(f"Citation parsing error: {e}")

                # バッファから引用情報を削除
                buffer = buffer[citation_end_idx + len("[CITATION_END]") :]
                citation_processing = False

            # 通常のトークン処理（引用情報処理中でない場合）
            if not citation_processing and buffer and "[CITATION_START]" not in buffer:
                data = json.dumps(
                    {"type": "token", "token": buffer, "done": False}, ensure_ascii=False
                )
                yield data
                buffer = ""

        # 残りのバッファを送信
        if buffer and not citation_processing:
            data = json.dumps({"type": "token", "token": buffer, "done": False}, ensure_ascii=False)
            yield data

        # 終了イベントを送信
        yield json.dumps({"type": "done", "token": "", "done": True})
    except Exception as e:
        error_data = json.dumps(
            {"type": "error", "error": str(e), "done": True}, ensure_ascii=False
        )
        yield error_data


@router.post("/ask")
async def ask_question_endpoint(request: AskRequest) -> EventSourceResponse:
    """
    掲示板の内容に関する質問を受け付け、ストリーミングで回答を返す

    - **question**: 質問文
    - **conversation_id**: 会話ID（オプション、現在は未使用）

    レスポンスはServer-Sent Events (SSE)形式でストリーミングされます。
    """
    try:
        # SSEレスポンスを返す
        return EventSourceResponse(
            generate_sse_events(request.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Nginxでのバッファリングを無効化
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ask/sync")
async def ask_question_sync(request: AskRequest) -> Dict[str, str]:
    """
    非ストリーミング版の質問応答エンドポイント（デバッグ用）
    """
    try:
        response = await ask_question(request.question)
        return {"answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "service": "chat"}
