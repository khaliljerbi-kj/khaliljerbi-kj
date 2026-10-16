import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LLM_PROVIDER"] = "heuristic"
os.environ["GOOGLE_MAPS_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db as db_module
from app.db import Base, get_db
from app.main import app
from app.models import DPE, Property, Role, User


@pytest.fixture
def session_factory(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(db_module, "SessionLocal", factory)
    return factory


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def client(session_factory):
    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def landlord(db):
    user = User(email="proprio@example.com", name="Mme Proprio", role=Role.LANDLORD)
    db.add(user)
    db.commit()
    return user


def make_property(db, owner, **overrides) -> Property:
    values = dict(
        owner_id=owner.id,
        title="2 pièces sur cour",
        description="Lumineux, calme, refait à neuf.",
        address="12 rue de la Butte-aux-Cailles, 75013 Paris",
        quartier="butte-aux-cailles",
        arrondissement=13,
        latitude=48.8275,
        longitude=2.3505,
        rent_hc=1150,
        charges=80,
        surface=38,
        rooms=2,
        floor=3,
        has_elevator=True,
        furnished=True,
        dpe=DPE.C,
        has_fiber=True,
        faces_courtyard=True,
    )
    values.update(overrides)
    prop = Property(**values)
    db.add(prop)
    db.commit()
    return prop
