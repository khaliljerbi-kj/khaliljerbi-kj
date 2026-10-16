from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Role, SearchAlert, User
from ..schemas import AlertCreate, AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(body: AlertCreate, db: Session = Depends(get_db)) -> AlertOut:
    """Enregistre la requête JSON extraite par l'IA pour être notifié des nouveaux biens."""
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=body.name, role=Role.TENANT)
        db.add(user)
        db.flush()
    alert = SearchAlert(
        user_id=user.id,
        criteria=body.criteria.model_dump(mode="json"),
        query=body.query,
        min_score=get_settings().alert_min_score,
    )
    db.add(alert)
    db.commit()
    return AlertOut(id=str(alert.id), email=user.email, min_score=alert.min_score, active=alert.active)


@router.delete("/{alert_id}", status_code=204)
def disable_alert(alert_id: str, db: Session = Depends(get_db)) -> None:
    alert = db.get(SearchAlert, _uuid(alert_id))
    if alert is None:
        raise HTTPException(404, "Alerte introuvable")
    alert.active = False
    db.commit()


def _uuid(value: str):
    import uuid

    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(404, "Alerte introuvable") from exc
