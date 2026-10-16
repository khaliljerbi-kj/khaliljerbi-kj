from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import ChatRequest, ChatResponse
from ..services.llm import get_provider
from ..services.matching import find_matches, to_card

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Un tour de conversation : extraction des critères puis, si possible, Top 3 commenté."""
    provider = get_provider()
    extraction = provider.extract(req.messages, req.criteria)
    response = ChatResponse(
        reply=extraction.reply,
        criteria=extraction.criteria,
        ready_to_search=extraction.ready_to_search,
        llm_provider=provider.name,
    )
    if not extraction.ready_to_search:
        return response

    result = find_matches(db, extraction.criteria)
    cards = [to_card(s) for s in result.matches]
    for card, text in zip(cards, provider.pitches(req.messages, extraction.criteria, cards)):
        card.why_for_you = text
    response.matches = cards
    response.used_external_sources = result.used_external
    response.notes = result.notes
    return response
