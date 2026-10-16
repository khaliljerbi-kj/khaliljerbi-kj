"""Alertes temps réel : détecte les nouveaux biens à > 90 % de match et prévient le locataire."""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..config import get_settings
from ..models import Property, PropertyStatus, SearchAlert, _now
from ..schemas import SearchCriteria
from .matching import Candidate, Scored, rank

log = logging.getLogger(__name__)


@dataclass
class Notification:
    alert_id: str
    email: str
    matches: list[Scored]


def check_alerts(db: Session) -> list[Notification]:
    """Passe sur toutes les alertes actives. Idempotent : chaque bien n'est évalué qu'une fois par alerte."""
    run_started = _now()
    alerts = db.scalars(
        select(SearchAlert).where(SearchAlert.active.is_(True)).options(joinedload(SearchAlert.user))
    ).all()
    if not alerts:
        return []

    oldest = min(a.last_checked_at for a in alerts)
    new_props = db.scalars(
        select(Property).where(
            Property.status == PropertyStatus.ACTIVE,
            Property.created_at > oldest,
            Property.created_at <= run_started,
        )
    ).all()

    sent: list[Notification] = []
    for alert in alerts:
        fresh = [Candidate.from_property(p) for p in new_props if p.created_at > alert.last_checked_at]
        if fresh:
            try:
                criteria = SearchCriteria.model_validate(alert.criteria)
            except ValueError:
                log.exception("Critères invalides pour l'alerte %s, désactivée", alert.id)
                alert.active = False
                continue
            hits = [s for s in rank(fresh, criteria) if s.score > alert.min_score]
            if hits:
                notification = Notification(str(alert.id), alert.user.email, hits)
                send_alert_email(notification, alert.query)
                alert.last_notified_at = run_started
                sent.append(notification)
        alert.last_checked_at = run_started
    db.commit()
    return sent


def _render(notification: Notification, query: str) -> EmailMessage:
    settings = get_settings()
    best = notification.matches[0]
    msg = EmailMessage()
    msg["Subject"] = f"Nouveau bien à {best.score} % de match : {best.candidate.title}"
    msg["From"] = settings.smtp_from
    msg["To"] = notification.email
    lines = [
        "Bonjour,",
        "",
        f"De nouveaux biens correspondent à votre recherche : « {query} »",
        "",
    ]
    for s in notification.matches[:3]:
        c = s.candidate
        commute = f" · {s.commute.minutes} min de {s.commute.destination}" if s.commute else ""
        lines += [
            f"• {c.title} — {c.rent_cc} € CC, {c.surface:g} m², DPE {c.dpe}{commute}",
            f"  Match {s.score} % · {c.address}",
        ]
    lines += [
        "",
        f"Voir la recherche : {settings.frontend_url}/search",
        f"Se désabonner : {settings.frontend_url}/alertes/{notification.alert_id}/desactiver",
    ]
    msg.set_content("\n".join(lines))
    return msg


def send_alert_email(notification: Notification, query: str) -> None:
    settings = get_settings()
    msg = _render(notification, query)
    if not settings.smtp_host:
        log.info(
            "[alerte] SMTP non configuré, email simulé\nÀ : %s\nObjet : %s\n\n%s", msg["To"], msg["Subject"], msg.get_content()
        )
        return
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password or "")
        smtp.send_message(msg)
