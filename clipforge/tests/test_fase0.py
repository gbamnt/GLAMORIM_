import json
import tempfile
import unittest
from pathlib import Path

from engine import config, doctor


class TestConfig(unittest.TestCase):
    def test_mescla_local_sobrescreve(self):
        with tempfile.TemporaryDirectory() as d:
            base, local = Path(d, "c.json"), Path(d, "l.json")
            base.write_text(json.dumps({"a": 1, "llm": {"modo": "heuristica", "x": 1}}), encoding="utf-8")
            local.write_text(json.dumps({"llm": {"modo": "gemini"}}), encoding="utf-8")
            cfg = config.carregar(base, local)
            self.assertEqual(cfg, {"a": 1, "llm": {"modo": "gemini", "x": 1}})

    def test_local_ausente(self):
        cfg = config.carregar(config.ARQ_PADRAO, Path("/nao/existe.json"))
        self.assertIn("presets", cfg)
        self.assertEqual(cfg["presets"]["rewards"], {"min_s": 62, "max_s": 110})

    def test_chave_gemini_nao_vaza_no_doctor(self):
        segredo = "AIza-TESTE-NAO-IMPRIMIR"
        it = doctor.checar_gemini({"llm": {"gemini": {"chave": segredo}}})
        self.assertTrue(it.ok)
        self.assertNotIn(segredo, it.detalhe + it.correcao)


class TestDoctor(unittest.TestCase):
    def test_python(self):
        self.assertTrue(doctor.checar_python().ok)

    def test_item_falho_tem_correcao(self):
        it = doctor.checar_binario("binario-que-nao-existe-xyz")
        self.assertFalse(it.ok)
        self.assertIn("winget", it.correcao)


if __name__ == "__main__":
    unittest.main()
