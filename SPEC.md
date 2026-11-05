# SPEC v2 — Amazon Restock App (amazon.com.br)

> **Substitui o SPEC v1.**
> **Como usar:** abra o Claude Code numa pasta vazia, salve este arquivo como `SPEC.md` e mande:
> *"Leia o SPEC.md inteiro. Implemente seguindo a ordem da seção 16, parando ao fim de cada etapa para eu validar. Prioridade máxima: o fluxo de monitoramento + checkout precisa funcionar até amanhã de manhã, mesmo que a interface ainda esteja simples."*

---

## 0. Visão geral

Aplicativo desktop pessoal, executado só no computador do usuário, que:

1. **Cadastra contas Amazon** (e-mail + senha guardados num cofre criptografado) e faz login sozinho.
2. **Sincroniza os dados da conta**: cartões salvos (bandeira + final) e endereços. Esses dados aparecem como opções na hora de configurar uma compra.
3. **Cadastra cartões virtuais** no cofre (titular, número, validade, CVV). Pode também **adicionar esses cartões à conta Amazon** com antecedência ("Preparar conta").
4. **Monitora produtos** a partir do link colado e, quando voltam ao estoque, **compra conforme os parâmetros**: conta, cartão, parcelas, endereço, quantidade, preço máximo e modo de operação.
5. Envia **notificações e pedidos de confirmação** pelo Telegram e pela própria interface.

**Prazo:** o produto-alvo volta amanhã. A ordem de implementação (seção 16) garante que o motor funcione antes do acabamento da interface.

---

## 1. Modelo de ameaças e princípios de segurança

"Risco zero" não existe. O objetivo é que **um vazamento de arquivo, um acesso pela rede ou um log não exponham nada útil**.

| Ameaça | Mitigação |
|---|---|
| Alguém copia a pasta do app / o banco | Campos sensíveis cifrados com AES-256-GCM. A chave só existe na memória, derivada da senha mestra (Argon2id). |
| Acesso pela rede local / internet | **O app não abre nenhuma porta.** A interface conversa com o Python pela ponte JS↔Python do `pywebview` (sem servidor HTTP). |
| Vazamento por logs, screenshots ou Telegram | Filtro de redação obrigatório em todos os logs. Telegram e interface só mostram o **final do cartão**. Screenshots de telas de pagamento passam por máscara antes de salvar. |
| Malware no próprio computador | Fora do alcance de qualquer app. Mitigações: cartão virtual com **limite igual ao valor da compra**, criptografia de disco do SO (BitLocker/FileVault), antivírus em dia. |
| Dependência maliciosa (supply chain) | Versões fixadas com hash (`pip install --require-hashes`). Nada de CDN: JS/CSS empacotados localmente. |
| Comando falso pelo Telegram | O bot só aceita mensagens do `chat_id` configurado e só tem comandos de status / confirmar / cancelar. Nenhum comando revela dados. |
| Sessão do navegador roubada (cookies) | Perfis do navegador ficam na pasta de dados do app, com permissão restrita ao usuário do SO. Recomendação de criptografia de disco. |

Princípios fixos:
- **Senha mestra** pedida ao abrir o app. Sem ela, nada sensível é decifrado. Se for esquecida, os dados são irrecuperáveis (é o comportamento desejado).
- **Bloqueio automático da interface** após X min ocioso (padrão 10). O motor continua rodando com a chave em memória até o app ser fechado.
- **CAPTCHA nunca é contornado.** O bot pausa, avisa e espera você resolver no navegador.
- **Código de verificação (OTP/2FA)**: o bot pausa e pede o código pela interface ou pelo Telegram (você responde com o código). O segredo do 2FA não é armazenado.
- **Idempotência**: produto comprado vira `purchased` e nunca é recomprado sem reset manual.

---

## 2. Stack

| Camada | Escolha |
|---|---|
| Linguagem | Python 3.12 |
| Janela desktop | `pywebview` (usa o WebView2 no Windows / WebKit no macOS) com `js_api` (sem servidor HTTP) |
| Front-end | HTML + Alpine.js + Tailwind (build local via Tailwind CLI standalone; arquivos estáticos empacotados) |
| Automação | Playwright, Chromium, `launch_persistent_context` (um perfil por conta), modo headed |
| Criptografia | `cryptography` (AESGCM) + `argon2-cffi` (Argon2id) |
| Banco | SQLite (SQLModel ou sqlite3) |
| Notificação | Telegram Bot API via `httpx` (long polling para respostas) |
| Logs | loguru com filtro de redação |
| Empacotamento | PyInstaller (executável + atalho na área de trabalho) |
| Testes | pytest |

---

## 3. Estrutura de pastas

```
amazon-restock-app/
├── SPEC.md
├── README.md
├── requirements.in / requirements.txt   # com hashes (pip-compile --generate-hashes)
├── app.py                               # entrypoint: abre a janela pywebview
├── src/restock/
│   ├── api.py            # classe exposta ao JS (js_api); só ela fala com a UI
│   ├── security/
│   │   ├── vault.py      # derivação de chave, cifrar/decifrar campos, troca de senha mestra
│   │   ├── redact.py     # filtro de redação para logs/textos
│   │   └── session.py    # estado bloqueado/desbloqueado, auto-lock
│   ├── db/
│   │   ├── models.py
│   │   └── repo.py
│   ├── engine/
│   │   ├── browser.py    # contexts persistentes por conta
│   │   ├── selectors.py  # carrega selectors.yaml com fallbacks
│   │   ├── login.py      # login automático + pausa para OTP/CAPTCHA
│   │   ├── account_sync.py  # lê cartões salvos e endereços da conta
│   │   ├── card_setup.py    # adiciona cartão do cofre à conta Amazon
│   │   ├── product.py       # leitura da página do produto
│   │   ├── monitor.py       # loop de monitoramento (asyncio, thread própria)
│   │   ├── checkout.py      # máquina de estados da compra
│   │   ├── guards.py        # preço, vendedor, total, lock
│   │   └── interrupts.py    # CAPTCHA, login, OTP, CVV
│   ├── notify/telegram.py
│   └── events.py         # barramento de eventos motor -> UI (fila thread-safe)
├── ui/
│   ├── index.html
│   ├── app.js            # Alpine stores, chamadas window.pywebview.api.*
│   ├── styles.css        # gerado pelo Tailwind CLI
│   └── vendor/alpine.min.js
├── selectors.yaml
└── tests/
    ├── fixtures/         # HTML real salvo (em estoque, esgotado, checkout)
    ├── test_vault.py
    ├── test_redact.py
    ├── test_product_parser.py
    ├── test_guards.py
    └── test_no_secrets_in_logs.py
```

Pasta de dados (fora do projeto, permissão só do usuário):
- Windows: `%LOCALAPPDATA%\RestockApp\`
- macOS: `~/Library/Application Support/RestockApp/`

Conteúdo: `restock.db`, `profiles/<conta_id>/`, `screenshots/`, `logs/`, `selectors.override.yaml`.

---

## 4. Cofre (`security/vault.py`)

**Desenho (envelope encryption):**
1. Na primeira execução, o usuário cria a senha mestra (mínimo 12 caracteres).
2. Gera-se uma `data_key` aleatória de 32 bytes.
3. `kek = Argon2id(senha_mestra, salt, time_cost=3, memory_cost=64MB, parallelism=4)`.
4. `data_key` é cifrada com AES-GCM usando a `kek` e salva na tabela `vault_meta` junto com `salt` e parâmetros.
5. Cada campo sensível é guardado como `nonce(12B) || ciphertext || tag`, cifrado com a `data_key` e usando o **id do registro + nome do campo como AAD** (impede trocar campos de lugar).
6. Desbloqueio: deriva a `kek`, decifra a `data_key` e a mantém só em memória (`bytearray`, sobrescrita ao bloquear/fechar).
7. Trocar a senha mestra re-cifra apenas a `data_key`.

**Campos cifrados:** senha da conta Amazon, número do cartão, CVV, titular, validade, CPF (opcional).
**Campos em claro (necessários para listagem):** rótulos, bandeira, final do cartão (4 dígitos), URLs, configurações.

**Regras:**
- Decifrar só no momento de usar (preencher um campo no navegador) e descartar a referência logo depois.
- Nenhum dado decifrado volta para a UI. A UI recebe apenas `•••• 1234`. Exceção: botão "revelar" com nova digitação da senha mestra, mostrando o dado por 10 s.
- Teste obrigatório: cifrar → decifrar; AAD errado falha; senha errada falha; o banco não contém nenhum número de cartão em claro (`grep` por regex de PAN no arquivo .db).

---

## 5. Modelo de dados

```sql
vault_meta(id=1, salt BLOB, kdf_params TEXT, wrapped_data_key BLOB, criado_em TEXT)

contas(
  id TEXT PK, rotulo TEXT, email TEXT,
  senha_enc BLOB,
  perfil_dir TEXT,
  status_sessao TEXT,          -- desconhecido | ok | expirada | precisa_otp
  ultimo_sync TEXT
)

cartoes_conta(                  -- espelho do que já está salvo na Amazon (via sync)
  id INTEGER PK, conta_id TEXT, bandeira TEXT, final TEXT, apelido TEXT,
  aceita_parcelamento INTEGER, sincronizado_em TEXT
)

enderecos_conta(
  id INTEGER PK, conta_id TEXT, rotulo TEXT, resumo TEXT, padrao INTEGER, sincronizado_em TEXT
)

cartoes_cofre(                  -- cartões virtuais cadastrados no app
  id TEXT PK, apelido TEXT, bandeira TEXT, final TEXT,
  titular_enc BLOB, numero_enc BLOB, validade_enc BLOB, cvv_enc BLOB,
  cvv_dinamico INTEGER,          -- 1 = não guarda CVV, pede na hora
  limite_informado REAL          -- só referência visual
)

cartao_vinculo(                 -- cartão do cofre já adicionado em qual conta
  cartao_cofre_id TEXT, conta_id TEXT, adicionado_em TEXT
)

produtos(
  id TEXT PK, url TEXT, asin TEXT, titulo TEXT, imagem_url TEXT,
  conta_id TEXT,
  fonte_cartao TEXT,             -- conta | cofre
  cartao_ref TEXT,               -- id de cartoes_conta ou de cartoes_cofre
  parcelas INTEGER, parcelas_fallback TEXT,   -- maior_disponivel_ate | pausar
  endereco_id INTEGER,
  quantidade INTEGER, preco_maximo REAL, total_maximo REAL,
  exigir_vendido_por_amazon INTEGER, aceitar_usado INTEGER,
  modo TEXT,                     -- dry_run | confirmar | automatico
  intervalo_seg INTEGER,
  janela_inicio TEXT, janela_fim TEXT, janela_intervalo_seg INTEGER,
  status TEXT,                   -- parado | monitorando | em_checkout | pausado | comprado
  ultimo_check TEXT, ultimo_preco REAL, ultima_disponibilidade TEXT
)

checks(id, produto_id, ts, disponivel, preco, vendedor, latencia_ms, erro)

tentativas(
  id, produto_id, conta_id, modo, inicio, fim,
  estado_final TEXT,             -- COMPRADO | DRY_RUN_OK | PAUSADO | FALHOU | CANCELADO
  motivo TEXT, total REAL, parcelas INTEGER, pedido_numero TEXT, screenshots TEXT
)

config(chave TEXT PK, valor TEXT)   -- telegram, intervalos, auto-lock etc. (token do Telegram cifrado)
```

Lock de checkout: `UPDATE produtos SET status='em_checkout' WHERE id=? AND status='monitorando'` e só segue se `rowcount == 1`.

---

## 6. Interface (telas)

Layout: barra lateral com **Painel · Produtos · Contas · Cartões · Histórico · Configurações** e um cadeado no topo para bloquear manualmente.

### 6.1 Desbloqueio
- Primeira vez: criar senha mestra (com confirmação, medidor de força e aviso de que não há recuperação).
- Depois: campo de senha mestra. 5 erros seguidos → espera de 60 s.

### 6.2 Painel
- Cards por produto: imagem, título, status (cor), último preço, "checado há X s", próxima checagem.
- Botões globais: **Iniciar tudo · Parar tudo · Parada de emergência** (fecha os navegadores e cancela checkouts em andamento antes de finalizar).
- Feed de eventos ao vivo (vindo de `events.py`).
- Quando houver pausa: banner vermelho com o motivo e ação ("Digitar código", "Resolver CAPTCHA no navegador", "Informar CVV").
- Modo `confirmar`: modal "Comprar agora? R$ X em 10x no cartão •••• 1234" com contagem regressiva.

### 6.3 Produtos → Novo/Editar
1. Colar link → o app normaliza a URL, extrai o ASIN e faz uma leitura de pré-visualização (título, imagem, preço, disponibilidade).
2. Campos:
   - Conta (dropdown)
   - Cartão: abas **"Da conta Amazon"** (lista sincronizada: bandeira + final) e **"Cartão virtual do app"** (lista do cofre). Se escolher do cofre e ele ainda não estiver vinculado à conta, aparece o aviso **"Preparar agora"** (recomendado fazer antes da reposição).
   - Parcelas (1–24) e o que fazer se não estiver disponível
   - Endereço (lista sincronizada)
   - Quantidade, preço unitário máximo, total máximo com frete
   - Só vendido e entregue pela Amazon (on/off), aceitar usado (off)
   - Modo: Teste (dry run) · Confirmar pelo celular · Automático
   - Intervalo e janela intensiva (data/hora início-fim + intervalo)
3. Botão **"Simular compra"**: roda o checkout em dry run (válido se o produto estiver em estoque) e mostra o screenshot da revisão.

### 6.4 Contas
- Lista com status de sessão.
- Nova conta: rótulo, e-mail, senha (cifrada).
- Ações: **Conectar** (login automático; se pedir OTP/CAPTCHA, abre o banner de pausa) · **Sincronizar dados** (lê cartões salvos e endereços) · **Abrir navegador desta conta** (para ajustes manuais) · Excluir (apaga também o perfil do navegador).

### 6.5 Cartões (cofre)
- Novo cartão virtual: apelido, titular, número (validação de Luhn + bandeira automática), validade, CVV ou "CVV dinâmico (pedir na hora)".
- Listagem mostra só bandeira + final + em quais contas está vinculado.
- Ação **"Adicionar à conta…"** → roda `card_setup.py` na conta escolhida.
- Excluir faz sobrescrita dos campos cifrados antes de apagar a linha.

### 6.6 Histórico
- Tabela de tentativas com estado final, total, parcelas, número do pedido e galeria de screenshots.

### 6.7 Configurações
- Telegram: token (cifrado), chat_id, botão "Enviar teste".
- Intervalo padrão, intervalo mínimo (piso de 10 s), jitter.
- Tempo de auto-lock e timeout de confirmação.
- Trocar senha mestra.
- **Backup**: exportar arquivo `.restockbak` cifrado (mesma criptografia com senha própria) e importar.
- Botão "Verificar seletores" (seção 9).

---

## 7. Ponte UI ↔ motor (`api.py`, `events.py`)

- O motor roda num **loop asyncio em thread própria**. A UI nunca bloqueia.
- `api.py` expõe métodos tipados para o JS: `unlock(pw)`, `lock()`, `list_products()`, `save_product(dto)`, `start(id)`, `stop(id)`, `panic_stop()`, `preview_url(url)`, `simulate(id)`, `accounts_*`, `cards_*`, `submit_otp(conta_id, code)`, `submit_cvv(tentativa_id, cvv)`, `confirm_purchase(tentativa_id, bool)`, `settings_*`.
- **Todo método (exceto `unlock`) verifica se o cofre está desbloqueado.**
- Eventos do motor vão para uma fila; a UI faz `poll_events()` a cada 1 s (ou o Python usa `window.evaluate_js` para empurrar). Os eventos nunca contêm dados sensíveis.
- DTOs validados com Pydantic na entrada de cada método.

---

## 8. Motor

### 8.1 Login (`login.py`)
1. Abre o perfil da conta e vai para a página "Sua conta".
2. Se já estiver logado → `ok`.
3. Se não: preenche e-mail → continuar → senha (decifrada na hora) → entrar.
4. OTP: status `precisa_otp`, evento + Telegram "Código de verificação da conta X?"; aguarda `submit_otp` (UI ou resposta no Telegram) por até 5 min e preenche.
5. CAPTCHA: pausa e pede para resolver no navegador aberto.
6. A sessão fica salva no perfil persistente; o login automático só é usado quando a sessão expira (inclusive no meio de um checkout: login → volta ao produto → continua).

### 8.2 Sincronização da conta (`account_sync.py`)
- Página de formas de pagamento → extrai bandeira, final e apelido de cada cartão salvo.
- Página de endereços → extrai nome/resumo e qual é o padrão.
- Atualiza `cartoes_conta` e `enderecos_conta`. Nunca lê nem guarda número completo (a Amazon nem exibe).

### 8.3 Preparar cartão (`card_setup.py`)
- Na conta: Formas de pagamento → adicionar cartão de crédito → preencher titular, número e validade (o formulário de cartão da Amazon costuma ficar **dentro de um iframe**; usar `frame_locator`).
- Confirmar e ressincronizar. Registrar em `cartao_vinculo`.
- Também pode rodar dentro do checkout como fallback ("adicionar cartão" na tela de pagamento), mas o recomendado é fazer antes.

### 8.4 Leitura do produto (`product.py`)
Retorna `ProductStatus(asin, titulo, disponivel, preco, vendedor_amazon, tem_comprar_agora, raw_disponibilidade, ts)`.
Disponível = botão Comprar agora/Adicionar ao carrinho visível e habilitado + texto de disponibilidade sem "indisponível/esgotado/não disponível" + (se exigido) vendedor contém "Amazon". Preço BRL `"R$ 1.299,90"` → `1299.90`.

### 8.5 Monitoramento (`monitor.py`)
- Uma task por produto, uma aba por produto dentro do contexto da conta.
- Recarrega a página (`domcontentloaded`) no intervalo com jitter; usa o intervalo da janela intensiva quando estiver dentro dela.
- Backoff em erro (2→4→8→…→60 s). 5 erros seguidos → aviso.
- Heartbeat no Telegram a cada 60 min.
- Disponível e preço ok → evento + Telegram "VOLTOU" → adquire lock → checkout.

### 8.6 Checkout (`checkout.py`) — máquina de estados
```
VALIDAR_PRODUTO   preço ≤ máximo, vendedor ok, novo
→ QUANTIDADE
→ COMPRAR_AGORA
→ CHECKOUT_CARREGADO          (espera marcador, máx 20 s)
→ GARANTIR_ENDERECO           (seleciona o endereço configurado)
→ GARANTIR_PAGAMENTO          (conta: escolhe pelo final; cofre: escolhe pelo final ou adiciona o cartão)
→ GARANTIR_PARCELAS           (seleciona N; senão aplica o fallback)
→ CVV_SE_PEDIDO               (cofre com CVV salvo: preenche; CVV dinâmico ou cartão da conta: pausa e pede CVV na UI/Telegram)
→ REVISAO                     (lê total ≤ total_maximo; screenshot mascarado)
→ DECISAO                     dry_run → DRY_RUN_OK | confirmar → modal + Telegram | automatico → segue
→ FINALIZAR                   (um único clique; nunca repetir)
→ CONFIRMACAO                 (texto de confirmação + número do pedido)
→ COMPRADO
```
- `interrupts.detect()` antes de cada estado.
- Timeout ou algo inesperado → `PAUSADO` com o navegador aberto naquela tela.
- Clicou em finalizar e a confirmação não veio → **não reclicar**; pausar e avisar para conferir "Meus pedidos".
- Meta: menos de 15 s do "voltou" até a revisão, com endereço e cartão já padrão na conta.

### 8.7 Interrupções
| Situação | Ação |
|---|---|
| CAPTCHA | pausa, screenshot, aviso "resolva no navegador"; retoma sozinho ao detectar que foi resolvido |
| Sessão expirada | login automático (8.1) |
| OTP | pede o código na UI/Telegram |
| CVV | preenche do cofre ou pede na hora |
| Preço acima do teto | não compra, avisa o preço encontrado |

### 8.8 Modo Turbo (latência mínima) — PRIORIDADE

**Meta:** do momento em que o bot *detecta* o estoque até o clique em "Finalizar pedido" em **≤ 2 s** (objetivo: ~1 s). O tempo total desde a reposição real = atraso de detecção (até 1 intervalo) + checkout.

**Detecção leve (substitui o reload da página no modo Turbo):**
- Usar `context.request.get(url_produto)` do Playwright: compartilha os cookies da sessão logada, mas não renderiza a página (~150–400 ms contra 1,5–3 s de um reload).
- Parse com `selectolax` (muito mais rápido que BeautifulSoup) olhando só: preço da buybox, presença do formulário/botão de Comprar agora, texto de disponibilidade e vendedor.
- Opcional, a investigar com o DevTools: endpoint de ofertas mais leve que a página inteira (ex.: o painel AJAX de "todas as ofertas"). Usar só se for estável em teste.
- Intervalo da janela intensiva: **piso de 3 s com jitter**. Abaixo disso a Amazon tende a responder com 503/CAPTCHA, e um CAPTCHA no meio custa muito mais que os segundos ganhos. Ao receber 503 ou CAPTCHA: backoff automático e aviso.

**Checkout pré-aquecido:**
- A aba do produto fica **sempre aberta e carregada** no contexto da conta; ao detectar, faz-se um reload só dessa aba e o clique imediato em Comprar agora.
- Caminho rápido opcional (investigar e validar em dry run): extrair do HTML já baixado na detecção os campos ocultos do formulário de Comprar agora e submetê-lo direto, pulando o reload.
- `page.route` bloqueando imagens, fontes, mídia e domínios de anúncios/telemetria em todas as abas do bot.
- Nada de `sleep` fixo nem `networkidle`: cada passo espera só o seletor que precisa, com timeout curto (3–5 s), e já parte para o próximo.
- Endereço e cartão **padrão na conta** → o fluxo vira Comprar agora → (parcelas) → Finalizar. Só abrir "alterar" se o que está na tela não bate com a configuração.
- Parcelas: ler o valor selecionado; só mexer se for diferente do configurado.
- CVV e dados do cartão decifrados e mantidos em memória **apenas durante a janela intensiva**, para não gastar tempo no momento crítico (descartar ao fim da janela).
- Sessão verificada a cada 15 min durante a janela (keepalive), para que nunca seja preciso fazer login no momento da compra.

**Modo de operação:** para essa latência, o produto precisa estar em **Automático**. O modo Confirmar acrescenta o tempo de reação humana (segundos). A trava de segurança passa a ser: preço/total máximo + **limite do cartão virtual igual ao valor da compra**.

**Medição obrigatória:**
- Timestamp (`time.perf_counter`) em cada estado da máquina; gravar em `tentativas` e mostrar no Painel: `detecção→comprar agora`, `→checkout`, `→finalizar`, total.
- Comando/tela "Benchmark": roda 5 simulações em dry run num produto em estoque e mostra média e pior caso de cada etapa. Otimizar até o total ficar ≤ 2 s.

**Ambiente:** internet por cabo, sem VPN, computador na tomada, só o necessário aberto.

---

## 9. Seletores (`selectors.yaml`)

Tudo que localiza elementos vem deste arquivo, com fallbacks testados em ordem, priorizando papel/texto em pt-BR. Um `selectors.override.yaml` na pasta de dados permite corrigir sem recompilar.

```yaml
produto:
  titulo: ["#productTitle"]
  preco: ["#corePrice_feature_div .a-price .a-offscreen", "#apex_desktop .a-price .a-offscreen", ".a-price .a-offscreen"]
  disponibilidade: ["#availability", "#outOfStock"]
  comprar_agora: ["#buy-now-button", "role=button[name=/comprar agora/i]"]
  carrinho: ["#add-to-cart-button"]
  vendedor: ["#merchantInfoFeature_feature_div", "#sellerProfileTriggerId", "#tabular-buybox"]
  quantidade: ["#quantity"]
login:
  email: ["#ap_email"]
  continuar: ["#continue"]
  senha: ["#ap_password"]
  entrar: ["#signInSubmit"]
  otp: ["#auth-mfa-otpcode", "input[name='otpCode']"]
conta:
  pagamentos_url: "https://www.amazon.com.br/cpe/yourpayments/wallet"
  enderecos_url: "https://www.amazon.com.br/a/addresses"
checkout:
  marcador: ["#checkout-main", "text=/finalizar pedido|revise seu pedido/i"]
  alterar_endereco: ["text=/alterar/i >> nth=0"]
  alterar_pagamento: ["text=/alterar/i >> nth=1"]
  cartao_por_final: "text=/terminado em {final}|final {final}/i"
  adicionar_cartao: ["text=/adicionar (um )?cartão/i"]
  iframe_cartao: ["iframe[name*='ApxSecureIframe']", "iframe[src*='apx-security']"]
  parcelas: ["select[name*='installment']", "role=combobox[name=/parcela/i]"]
  cvv: ["input[name*='addCreditCardVerificationNumber']", "input[name*='cvv']"]
  usar_pagamento: ["role=button[name=/usar esta forma de pagamento|continuar/i]"]
  total: ["#subtotals-marketplace-table .grand-total-price"]
  finalizar: ["#submitOrderButtonId input", "role=button[name=/finalizar pedido|fazer pedido/i]"]
  confirmacao: ["text=/pedido (feito|realizado)|obrigado/i"]
  numero_pedido: ["text=/\\d{3}-\\d{7}-\\d{7}/"]
interrupcoes:
  captcha: ["form[action*='validateCaptcha']", "text=/digite os caracteres/i"]
```

> **Obrigatório:** validar todos com `playwright codegen` numa sessão logada (produto em estoque, esgotado, checkout, página de pagamentos, formulário de cartão) e implementar "Verificar seletores" na UI, mostrando ✓/✗ por seletor.

---

## 10. Redação de dados sensíveis (`security/redact.py`)

- Filtro aplicado no loguru, nos eventos e no Telegram:
  - sequências de 13–19 dígitos (com ou sem espaço/hífen) → `[CARTAO]`
  - campos chamados `senha`, `password`, `cvv`, `numero`, `token` → `[REDACTED]`
  - CPF → `***.***.***-**`
- Screenshots: antes de salvar, preencher com retângulo preto as caixas dos seletores de número, CVV, senha e iframe de cartão.
- Playwright: **desligar trace e HAR** (gravariam o que é digitado).
- Teste `test_no_secrets_in_logs.py`: roda um fluxo simulado com um cartão de teste e verifica que o número e o CVV não aparecem em nenhum arquivo de `logs/`, `screenshots/` ou no banco em claro.

---

## 11. Telegram

- Só responde ao `chat_id` configurado; ignora o resto.
- Mensagens: iniciado, VOLTOU, dry run ok (com screenshot mascarado), pedido de confirmação com botões [Comprar] [Cancelar], pedido de OTP/CVV, COMPRADO + nº do pedido, PAUSADO + motivo, heartbeat.
- Respostas aceitas: botões de confirmação, `/status`, `/parar`, e mensagem com o código quando há OTP/CVV pendente (apagar a mensagem com o código no chat via `deleteMessage` logo após ler).
- Falha no Telegram nunca trava a compra.

---

## 12. Empacotamento e execução

- `pyinstaller` gerando um executável com `ui/` embutida e ícone; Playwright instala o Chromium na pasta de dados no primeiro uso.
- Atalho na área de trabalho "Restock".
- Fechar a janela pergunta: "Há N produtos monitorando. Fechar e parar tudo?"
- Enquanto houver monitoramento, o app pede ao SO para **não suspender** (Windows: `SetThreadExecutionState`; macOS: `caffeinate`).

---

## 13. Recomendações para os cartões virtuais

- Um cartão virtual por compra/produto, com **limite igual ao total esperado** (o próprio limite vira trava de segurança).
- Se o banco gerar **CVV dinâmico**, marcar "CVV dinâmico" no cadastro: o app pede na hora pelo celular.
- Se o cartão virtual for **temporário** (expira em horas), criar perto da reposição e rodar "Preparar conta" logo depois.
- Usar o mesmo endereço que já foi usado com aquele cartão reduz pedidos extras de verificação.

---

## 14. Riscos conhecidos

- **Termos de uso da Amazon** restringem automação; existe risco de bloqueio de compra ou restrição da conta. Manter poucos produtos e intervalos ≥ 10 s.
- **Seletores quebram** quando o layout muda → "Verificar seletores" antes de usos importantes.
- **Estoque disputado:** nenhum bot garante a compra; o ganho é reagir em segundos.
- **CAPTCHA/OTP** exigem você perto do celular.
- **Parcelamento** varia por valor, produto e cartão; conferir no "Simular compra".

---

## 15. Definition of Done

- Desbloqueio com senha mestra, auto-lock e cofre testados (`test_vault.py`).
- Contas: cadastrar, conectar (com OTP pela UI), sincronizar cartões e endereços.
- Cartões: cadastrar no cofre, adicionar à conta Amazon.
- Produtos: colar link com pré-visualização, todos os parâmetros, simular compra.
- Monitoramento e checkout nos três modos; parada de emergência funcionando.
- Telegram com confirmação por botão e envio de código.
- Nenhum dado sensível em logs, screenshots, eventos ou banco em claro (`test_no_secrets_in_logs.py` verde).
- App não abre nenhuma porta de rede (verificar com `netstat` durante a execução).
- Executável + atalho funcionando; README com passo a passo.

---

## 16. Ordem de implementação (hoje → amanhã)

**Bloco A — essencial para amanhã (fazer primeiro):**

| # | Etapa | Pronto quando |
|---|---|---|
| A1 | Scaffold, dependências com hash, pasta de dados, SQLite | app abre uma janela vazia |
| A2 | Cofre + tela de desbloqueio | criar senha, bloquear, desbloquear; testes verdes |
| A3 | Redação de logs + teste de segredos | teste verde |
| A4 | Contas: cadastro + login automático + OTP pela UI | sessão persiste ao reabrir o app |
| A5 | Telegram (envio + confirmação + código) | mensagens chegam e botões respondem |
| A6 | Seletores validados com codegen + "Verificar seletores" | todos ✓ nas páginas reais |
| A7 | Leitura de produto + tela de Produtos (colar link, parâmetros) | pré-visualização correta em produto em estoque e esgotado |
| A8 | Monitor + Painel com status ao vivo + parada de emergência | 10 min rodando sem erro |
| A9 | Checkout com cartão **da conta** em dry run | "Simular compra" chega à revisão com parcelas e cartão certos |
| A10 | Modo Turbo (8.8) + Benchmark | média detecção→finalizar ≤ 2 s em 5 simulações |

**Bloco B — completa a visão (se der tempo hoje, senão logo depois):**

| # | Etapa |
|---|---|
| B1 | Sincronização de cartões e endereços da conta |
| B2 | Cartões virtuais no cofre + "Adicionar à conta" |
| B3 | Checkout usando cartão do cofre + CVV (salvo ou na hora) |
| B4 | Histórico, backup cifrado, configurações completas |
| B5 | Empacotamento PyInstaller + atalho + bloqueio de suspensão |

**Ensaio de hoje à noite:** cadastrar o cartão virtual na conta (pela Amazon ou pelo B2, se já estiver pronto), deixá-lo como padrão e rodar "Simular compra" num produto **em estoque** de valor parecido com o alvo, vendido pela Amazon. Nada é comprado em dry run.

**Amanhã:** produto-alvo em modo **Automático** (Turbo), com preço/total máximo preenchidos e cartão virtual com limite igual ao valor da compra; janela intensiva no horário provável de reposição; computador na tomada e internet por cabo.
