"""Esquema SQLite (SPEC seção 5). Campos *_enc guardam nonce||ciphertext||tag."""

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS vault_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    salt BLOB NOT NULL,
    kdf_params TEXT NOT NULL,
    wrapped_data_key BLOB NOT NULL,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contas (
    id TEXT PRIMARY KEY,
    rotulo TEXT NOT NULL,
    email TEXT NOT NULL,
    senha_enc BLOB,
    perfil_dir TEXT,
    status_sessao TEXT NOT NULL DEFAULT 'desconhecido',  -- desconhecido|ok|expirada|precisa_otp
    ultimo_sync TEXT
);

CREATE TABLE IF NOT EXISTS cartoes_conta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id TEXT NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    bandeira TEXT,
    final TEXT,
    apelido TEXT,
    aceita_parcelamento INTEGER,
    sincronizado_em TEXT
);

CREATE TABLE IF NOT EXISTS enderecos_conta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id TEXT NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    rotulo TEXT,
    resumo TEXT,
    padrao INTEGER NOT NULL DEFAULT 0,
    sincronizado_em TEXT
);

CREATE TABLE IF NOT EXISTS cartoes_cofre (
    id TEXT PRIMARY KEY,
    apelido TEXT,
    bandeira TEXT,
    final TEXT,
    titular_enc BLOB,
    numero_enc BLOB,
    validade_enc BLOB,
    cvv_enc BLOB,
    cvv_dinamico INTEGER NOT NULL DEFAULT 0,
    limite_informado REAL
);

CREATE TABLE IF NOT EXISTS cartao_vinculo (
    cartao_cofre_id TEXT NOT NULL REFERENCES cartoes_cofre(id) ON DELETE CASCADE,
    conta_id TEXT NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    adicionado_em TEXT,
    PRIMARY KEY (cartao_cofre_id, conta_id)
);

CREATE TABLE IF NOT EXISTS produtos (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    asin TEXT,
    titulo TEXT,
    imagem_url TEXT,
    conta_id TEXT REFERENCES contas(id),
    fonte_cartao TEXT,                 -- conta | cofre
    cartao_ref TEXT,
    parcelas INTEGER NOT NULL DEFAULT 1,
    parcelas_fallback TEXT NOT NULL DEFAULT 'pausar',   -- maior_disponivel_ate | pausar
    endereco_id INTEGER,
    quantidade INTEGER NOT NULL DEFAULT 1,
    preco_maximo REAL,
    total_maximo REAL,
    exigir_vendido_por_amazon INTEGER NOT NULL DEFAULT 1,
    aceitar_usado INTEGER NOT NULL DEFAULT 0,
    modo TEXT NOT NULL DEFAULT 'dry_run',               -- dry_run | confirmar | automatico
    intervalo_seg INTEGER NOT NULL DEFAULT 30,
    janela_inicio TEXT,
    janela_fim TEXT,
    janela_intervalo_seg INTEGER,
    status TEXT NOT NULL DEFAULT 'parado',              -- parado|monitorando|em_checkout|pausado|comprado
    ultimo_check TEXT,
    ultimo_preco REAL,
    ultima_disponibilidade TEXT
);

CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id TEXT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    ts TEXT NOT NULL,
    disponivel INTEGER,
    preco REAL,
    vendedor TEXT,
    latencia_ms INTEGER,
    erro TEXT
);
CREATE INDEX IF NOT EXISTS idx_checks_produto_ts ON checks(produto_id, ts);

CREATE TABLE IF NOT EXISTS tentativas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id TEXT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    conta_id TEXT,
    modo TEXT,
    inicio TEXT,
    fim TEXT,
    estado_final TEXT,                 -- COMPRADO | DRY_RUN_OK | PAUSADO | FALHOU | CANCELADO
    motivo TEXT,
    total REAL,
    parcelas INTEGER,
    pedido_numero TEXT,
    screenshots TEXT,
    tempos TEXT                        -- JSON com timestamps por estado (Modo Turbo, 8.8)
);

CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT
);
"""

# Campos sensíveis: (tabela, coluna). Usados pela redação e pelo teste de segredos.
ENCRYPTED_FIELDS = {
    ("contas", "senha_enc"),
    ("cartoes_cofre", "titular_enc"),
    ("cartoes_cofre", "numero_enc"),
    ("cartoes_cofre", "validade_enc"),
    ("cartoes_cofre", "cvv_enc"),
}
