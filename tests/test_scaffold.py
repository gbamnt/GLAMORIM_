import os
import stat

from restock import paths
from restock.db import repo


def test_data_dir_created_private(isolated_data_dir):
    d = paths.data_dir()
    assert d == isolated_data_dir
    for sub in ("profiles", "screenshots", "logs"):
        assert (d / sub).is_dir()
    if os.name == "posix":
        assert stat.S_IMODE(d.stat().st_mode) == 0o700


def test_schema_created_and_db_private():
    db = repo.init_db()
    with repo.connect() as c:
        tables = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"vault_meta", "contas", "cartoes_conta", "enderecos_conta", "cartoes_cofre",
            "cartao_vinculo", "produtos", "checks", "tentativas", "config"} <= tables
    if os.name == "posix":
        assert stat.S_IMODE(db.stat().st_mode) == 0o600


def test_config_roundtrip():
    repo.set_config("intervalo_padrao", "30")
    repo.set_config("intervalo_padrao", "20")
    assert repo.get_config("intervalo_padrao") == "20"
    assert repo.get_config("nao_existe", "x") == "x"


def test_checkout_lock_is_exclusive():
    with repo.connect() as c:
        c.execute("INSERT INTO produtos(id, url, status) VALUES('p1', 'https://x', 'monitorando')")
    assert repo.acquire_checkout_lock("p1") is True
    assert repo.acquire_checkout_lock("p1") is False


def test_api_requires_unlock():
    from restock.api import Api
    api = Api()
    assert api.app_info()["ok"] is True
    assert api.poll_events() == {"ok": False, "erro": "bloqueado"}
