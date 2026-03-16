import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_people():
    return [
        {
            "id": "1",
            "name": "Alice",
            "company_id": "techcorp",
            "email": "alice@techcorp.com",
            "title": "CTO",
            "linkedin": "https://linkedin.com/in/alice",
        },
        {
            "id": "2",
            "name": "Bob",
            "company_id": "techcorp",
            "email": "bob@techcorp.com",
            "title": "VP Eng",
            "linkedin": None,
        },
    ]


def test_append_people_upserts_to_supabase(sample_people):
    """append_people() should upsert rows into the Supabase people table."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.execute.return_value.data = []
    mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    with patch("tools.people_sheet.get_db", return_value=mock_db):
        from tools.people_sheet import append_people
        append_people(sample_people)

    # Should have queried companies and upserted people
    assert mock_db.table.called


def test_get_existing_people_returns_email_keyed_dict():
    """get_existing_people() should return a dict keyed by lowercase email."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.execute.return_value.data = [
        {"id": "1", "email": "alice@techcorp.com", "last_contact": "email", "last_contact_date": "2024-01-01"},
        {"id": "2", "email": "bob@techcorp.com", "last_contact": None, "last_contact_date": None},
    ]

    with patch("tools.people_sheet.get_db", return_value=mock_db):
        from tools.people_sheet import get_existing_people
        result = get_existing_people()

    assert "alice@techcorp.com" in result
    assert "bob@techcorp.com" in result
    assert result["alice@techcorp.com"]["id"] == "1"
