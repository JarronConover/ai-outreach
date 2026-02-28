import pytest
from unittest.mock import MagicMock, patch
from tools.people_sheet import append_people


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


def test_append_people_calls_append_row(sample_people):
    mock_worksheet = MagicMock()
    with patch("tools.people_sheet._get_people_worksheet", return_value=mock_worksheet):
        result = append_people(sample_people)
    assert mock_worksheet.append_row.call_count == 2
    assert "2 people" in result


def test_append_people_returns_success_message(sample_people):
    mock_worksheet = MagicMock()
    with patch("tools.people_sheet._get_people_worksheet", return_value=mock_worksheet):
        result = append_people(sample_people)
    assert "success" in result.lower()
