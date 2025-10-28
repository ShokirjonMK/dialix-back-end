"""
Pytest configuration and fixtures
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.server import application
from backend.database.session_manager import sessionmanager
from backend.database.models import Base


# Test database URL (in-memory or test database)
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/dialix_test"


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session"""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_client(test_db_session):
    """Create test client"""

    # Override database session
    def override_get_db():
        try:
            yield test_db_session
        finally:
            test_db_session.close()

    application.dependency_overrides[get_db] = override_get_db

    yield TestClient(application)

    # Clean up
    application.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "role": "user",
        "company_name": "Test Company",
    }


@pytest.fixture
def sample_record_data():
    """Sample record data for testing"""
    return {
        "title": "Test Record",
        "duration": 120000,
        "operator_code": "001",
        "operator_name": "Test Operator",
        "call_type": "inbound",
        "source": "PBX",
        "status": "processed",
        "client_phone_number": "+998901234567",
    }
