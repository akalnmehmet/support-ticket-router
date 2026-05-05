import os
import json
import tempfile
import pytest

from main import main

@pytest.fixture
def temp_env():
    """Create a temporary directory for input and output files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "test_input.json")
        output_path = os.path.join(temp_dir, "test_output.json")
        db_path = os.path.join(temp_dir, "test_rules.db")
        yield input_path, output_path, db_path

def test_full_pipeline(temp_env, capsys, caplog):
    import logging
    caplog.set_level(logging.INFO)
    input_path, output_path, db_path = temp_env
    
    from unittest.mock import patch
    
    # 1. Prepare Mock Input Data
    mock_input = [
        {
            "id": 101,
            "subject": "System crash",
            "message": "The whole thing is broken.",
            "customerType": "standard",
            "createdAt": "2026-05-01T10:00:00Z"
        },
        {
            "id": 102,
            "subject": "Invoice request",
            "message": "Send me the invoice asap.",
            "customerType": "premium",
            "createdAt": "2026-05-01T10:05:00Z"
        }
    ]
    
    with open(input_path, 'w') as f:
        json.dump(mock_input, f)
        
    # 2. Run the pipeline with patched DB_PATH
    with patch('database.db.DB_PATH', db_path):
        main(input_file_path=input_path, output_file_path=output_path)
    
    # 3. Assertions on Output File
    assert os.path.exists(output_path), "Output file was not created"
    
    with open(output_path, 'r') as f:
        output_data = json.load(f)
        
    assert len(output_data) == 2, "Expected 2 processed tickets"
    
    # Verify the first ticket (Technical, Medium, Standard)
    t1 = output_data[0]
    assert t1["id"] == 101
    assert t1["category"] == "technical"
    assert t1["priority"] == "medium"
    assert t1["assignedTeam"] == "technical-support"
    
    # Verify the second ticket (Billing, High, Premium)
    t2 = output_data[1]
    assert t2["id"] == 102
    assert t2["category"] == "billing"
    assert t2["priority"] == "high"
    assert t2["assignedTeam"] == "payments-team"
    
    # 4. Assertions on Console/Log Output
    assert "Loaded 2 tickets" in caplog.text
    assert "Successfully saved processed tickets" in caplog.text
