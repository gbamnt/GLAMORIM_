import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Cada teste usa uma pasta de dados própria — nunca a real."""
    monkeypatch.setenv("RESTOCK_DATA_DIR", str(tmp_path / "RestockApp"))
    return tmp_path / "RestockApp"
