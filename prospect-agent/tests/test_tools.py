import pytest
from unittest.mock import MagicMock, patch
from schemas.output import Lead, LeadsOutput
from tools.tool import write_leads_to_sheet


@pytest.fixture
def sample_leads():
    return LeadsOutput(
        leads=[
            Lead(id="1", name="Alice", company="TechCorp", email="alice@techcorp.com", title="CTO"),
            Lead(id="2", name="Bob", company="TechCorp", email="bob@techcorp.com", title="VP Eng"),
        ]
    )


def test_write_leads_to_sheet_calls_append(sample_leads):
    mock_worksheet = MagicMock()
    with patch("tools.tool._get_worksheet", return_value=mock_worksheet):
        result = write_leads_to_sheet(sample_leads)
    assert mock_worksheet.append_row.call_count == 2
    assert "2 leads" in result


def test_write_leads_to_sheet_returns_success_message(sample_leads):
    mock_worksheet = MagicMock()
    with patch("tools.tool._get_worksheet", return_value=mock_worksheet):
        result = write_leads_to_sheet(sample_leads)
    assert "success" in result.lower()
