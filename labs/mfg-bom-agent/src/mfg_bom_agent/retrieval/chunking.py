"""정비 · 조립 문서와 이슈를 검색 단위(청크)로 자른다 (Part 2 Ch5-1 정비 문서 인덱스 연결).

검색 결과를 답변 근거로 쓰려면 "어느 문서의 어느 절, 몇 번째 줄"인지가 남아야 한다.
그래서 Markdown 은 제목(#) 단위로 자르고, 각 청크에 경로 · 절 제목 · 시작 행 번호를 붙인다.
이미지 태그 · HTML 은 검색에 도움이 안 되므로 지우되, 행 번호는 원문 기준으로 유지한다.
"""

from __future__ import annotations

import re

MAX_CHARS = 1500  # 청크 하나의 최대 길이. 길면 문단 경계에서 나눈다.

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_IMG_OR_HTML = re.compile(r"!\[[^\]]*\]\([^)]*\)|<[^>]+>")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def clean_markdown(text: str) -> str:
    """이미지 · HTML 태그를 지우고, 링크는 보이는 글자만 남긴다."""
    text = _IMG_OR_HTML.sub(" ", text)
    text = _LINK.sub(r"\1", text)
    return re.sub(r"[ \t]+", " ", text).strip()


# ─── [Hands-on P2-Ch5-1 정비 문서 인덱스 연결] 시작 ───
def chunk_markdown(path: str, text: str) -> list[dict]:
    """Markdown 문서를 제목 단위 청크 목록으로 바꾼다.

    청크 필드: doc_id(경로#순번), path, title(절 제목), line(원문 시작 행, 1부터), text
    """
    chunks: list[dict] = []
    title, start_line, buf = path, 1, []

    def flush() -> None:
        body = clean_markdown("\n".join(buf))
        if len(body) < 40:  # 제목만 있고 내용이 거의 없는 절은 검색에 쓸모가 없다
            return
        for part_no, piece in enumerate(_split_long(body)):
            chunks.append(
                {
                    "doc_id": f"{path}#{len(chunks) + 1}",
                    "source": "readme",
                    "path": path,
                    "title": title if part_no == 0 else f"{title} ({part_no + 1})",
                    "line": start_line,
                    "text": piece,
                }
            )

    for no, line in enumerate(text.splitlines(), start=1):
        match = _HEADING.match(line)
        if match:
            flush()
            title, start_line, buf = match.group(2).strip(), no, []
        else:
            buf.append(line)
    flush()
    return chunks


# ─── [Hands-on P2-Ch5-1] 끝 ───


def chunk_issue(issue: dict) -> dict:
    """GitHub 이슈 하나를 청크 하나로 만든다. 본문이 길면 앞부분만 쓴다(증상은 대개 앞에 있다)."""
    body = clean_markdown(issue.get("body") or "")[:MAX_CHARS]
    return {
        "doc_id": f"issue#{issue['number']}",
        "source": "issue",
        "path": issue["url"],
        "title": issue["title"],
        "line": 1,
        "text": f"{issue['title']}\n{body}".strip(),
        "created_at": issue["created_at"][:10],
        "state": issue["state"],
    }


def _split_long(body: str) -> list[str]:
    """MAX_CHARS 보다 긴 본문을 문단 경계에서 나눈다."""
    if len(body) <= MAX_CHARS:
        return [body]
    pieces, current = [], ""
    for para in re.split(r"\n\s*\n", body):
        if current and len(current) + len(para) > MAX_CHARS:
            pieces.append(current.strip())
            current = ""
        current += para + "\n\n"
    if current.strip():
        pieces.append(current.strip()[: MAX_CHARS * 2])
    return pieces
