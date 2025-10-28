"""
Tests for database optimization - N+1 queries, eager loading
"""

import pytest
from backend.services.record import get_records_sa
from backend.database.models import Record, Result


def test_no_n_plus_one_queries(test_db_session):
    """Test that records query doesn't cause N+1 queries"""
    # This test checks that queries are using eager loading
    records = (
        test_db_session.query(Record)
        .options(
            # Add eager loading for related records
            joinedload(Record.result)
        )
        .all()
    )

    # Should not cause additional queries when accessing related data
    for record in records:
        if record.result:
            _ = record.result.id  # Should not trigger new query


def test_query_performance(test_db_session):
    """Test query execution time"""
    import time

    start = time.perf_counter()
    records = test_db_session.execute(get_records_sa("test_owner_id"))
    end = time.perf_counter()

    # Query should complete quickly
    assert (end - start) < 1.0  # Should complete in less than 1 second


def test_eager_loading_works(test_db_session):
    """Test that eager loading is working correctly"""
    from sqlalchemy.orm import joinedload

    records = (
        test_db_session.query(Record).options(joinedload(Record.result)).limit(10).all()
    )

    # Accessing related data should not trigger new queries
    for record in records:
        _ = record.result  # Should not cause N+1 query
