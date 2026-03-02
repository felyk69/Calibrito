# 🔍 Análise Completa do Calibre Jr — Code Review

Revisão completa do codebase cobrindo: linguagens misturadas, atalhos, erros de boas práticas, segurança, arquitetura e manutenibilidade.

> [!NOTE]
> **Última atualização:** 28/02/2026 — Seções 1, 2, 3, 4, e 5 concluídas. Restam apenas: remover legados, testes, e melhorias futuras.

---

## 📊 Resumo Executivo

| Categoria | Severidade | Ocorrências |
|-----------|-----------|-------------|
| 🌐 Linguagens Misturadas (PT/EN) | ⚠️ Média | ~60+ locais |
| 🔇 Exceções Silenciosas (`except: pass`) | 🔴 Alta | ~20 locais |
| 🏗️ Arquitetura / Code Smells | ⚠️ Média | ~12 pontos |
| 🔒 Segurança | 🔴 Alta | 5 vulnerabilidades |
| 📝 Logging Inexistente | ⚠️ Média | Todo o projeto |
| 🧪 Testes Insuficientes | 🔴 Alta | Quase zero cobertura |
| 🖥️ Frontend Monolítico | ⚠️ Média | 1 arquivo, 2315 linhas |
| 📦 Arquivos Legados/Órfãos | 🟡 Baixa | 5+ arquivos |

---

## 1. 🌐 Linguagens Misturadas (PT + EN)

> [!WARNING]
> Este é o problema mais visível. Comentários, variáveis, mensagens de API e UI misturam português e inglês **sem critério algum**.

### Backend — Exemplos concretos

| Arquivo | Linha | Problema |
|---------|-------|---------|
| [config.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/config.py) | 8 | `TRASH_FOLDER` → pasta chamada `"Lixeira"` |
| [database.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/database.py) | 5 | Docstring `"""Cria a tabela no SQLite se não existir."""` |
| [database.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/database.py) | 9 | Comentário `# Habilita o modo WAL...` |
| [database.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/database.py) | 27 | `pass # A coluna já existe` |
| [database.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/database.py) | 55 | Mistura: `# Insert Default Profile if not exists` (EN) ao lado de `# Novas colunas de Metadados Avançados` (PT) |
| [book_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py) | 18 | `author = "Desconhecido"` (PT) mas todo restante é EN |
| [book_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py) | 61 | Variável `caminho_opf` (PT) ao lado de `root_xml` (EN) |
| [book_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py) | 74 | Variável `caminho_capa_temp` (PT) |
| [device_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/device_service.py) | 21 | Comentário PT: `# Aceita se for um Kindle Clássico OU...` |
| [books.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/api/routes/books.py) | 33 | Mensagem mista: `"Arquivo não encontrado"` (API response em PT) |
| [misc.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/api/routes/misc.py) | 29 | `title="Selecione a pasta de destino do KOReader"` (UI dialog em PT) |

### Frontend — Exemplos concretos

| Local | Problema |
|-------|---------|
| Linha 242 | `MODO DE EDIÇÃO ATIVADO` (PT) |
| Linha 278 | `placeholder="Search title, author..."` (EN) |
| Linha 357 | `Sort by` (EN) |
| Linha 434 | `Ferramentas:` (PT) |
| Linha 441 | `Auto-Renomear Todos` (PT) |
| Linha 474-480 | Headers de tabela mistos: `Todos`, `Capa`, `Título` (PT) + [All](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/static/js/app.js#1132-1158), `Title` (EN) |
| Linha 530 | `Selecionados` (PT) |
| Linha 547 | `Enviar para Kindle` (PT) |
| Linha 598 | `Edit Metadata` (EN) |
| Linha 634 | `Change Cover` (EN) |
| Linha 749 | `Save Changes` (EN) |
| Linha 773 | `Configurações` (PT) |
| Linha 828 | `Salvar e Re-escanear` (PT) |
| Linha 918 | `Lendo...` (PT) |

**Recomendação:** Padronizar TODO o código-fonte em **inglês** (variáveis, comentários, docstrings). Optionalmente, manter a UI em PT-BR via sistema de i18n (vide skill `i18n-localization`).

---

## 2. 🔇 Exceções Silenciosas (`except: pass`)

> [!CAUTION]
> Este é o problema mais perigoso. Erros são engolidos silenciosamente em ~20 locais, tornando debugging impossível.

### Ocorrências por arquivo

| Arquivo | Linhas | Contexto |
|---------|--------|----------|
| [config.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/config.py) | 19, 30 | `except Exception: pass` ao ler settings |
| [book_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py) | 52, 70, 83, 98, 111 | **5 bare excepts** em [process_book](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py#18-110) — erros de extração de metadados e capa simplesmente desaparecem |
| [watchdog_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/watchdog_service.py) | 55, 80, 90 | 3 bare excepts no watchdog |
| [books.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/api/routes/books.py) | 155, 200 | Falha silenciosa ao renomear e ao deletar arquivos |
| [misc.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/api/routes/misc.py) | 54 | **Bare `except:` sem `Exception`** — captura até `KeyboardInterrupt` e `SystemExit` |
| [metadata_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/metadata_service.py) | 80, 115, 179, 205 | API externa falha → retorna `[]` sem log |

**Recomendação:** Trocar todo `except: pass` por tratamento específico com logging:
```python
except (FileNotFoundError, PermissionError) as e:
    logger.warning("Erro ao renomear %s: %s", file_path, e)
```

---

## 3. 📝 Logging Inexistente

> [!IMPORTANT]
> O projeto inteiro usa `print()` com `flush=True` em vez do módulo [logging](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/logger.py#6-13) padrão do Python.

**Consequências:**
- Sem níveis de log (DEBUG, INFO, WARNING, ERROR)
- Sem rotação de arquivo de log
- Sem timestamps automáticos
- Impossível filtrar saída em produção

**Ocorrências:** [main.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/main.py) L34-36-44, [book_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py) L55-152-164, [watchdog_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/watchdog_service.py) L58-63-72

**Recomendação:** Criar [app/core/logger.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/logger.py) com `logging.getLogger()` configurado uma vez e importar em todos os módulos.

---

## 4. 🔒 Segurança

### 4.1 ~~Hardcoded Path~~ ✅ CORRIGIDO
- `KINDLE_DOCUMENTS_FOLDER` substituído por [get_kindle_folder()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/config.py#43-54) que lê de [settings.json](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/settings.json). Frontend também atualizado.

### 4.2 ~~MD5 para Hashing~~ ✅ CORRIGIDO
- Todas as 5 ocorrências de `hashlib.md5()` substituídas por `hashlib.sha256()`.

### 4.3 ~~SSRF na API de Download de Capas~~ ✅ CORRIGIDO
- Adicionada função [_is_safe_url()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/metadata_service.py#21-34) em [metadata_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/metadata_service.py) que bloqueia IPs privados e valida esquema HTTP/HTTPS.

### 4.4 Tkinter no Servidor Web ⚠️ DOCUMENTADO
- Problema conhecido: `tkinter` bloqueia event loop em headless/Docker. Mantido por ora (UX depende dele para folder picker).

### 4.5 ~~f-string em SQL~~ ✅ CORRIGIDO
- Substituído por whitelist estática com validação de tipo em [database.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/database.py).

---

## 5. 🏗️ Arquitetura e Code Smells

### 5.1 ~~Deprecated FastAPI `on_event`~~ ✅ CORRIGIDO
- Migrado para [lifespan](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/main.py#20-39) async context manager em [main.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/main.py).

### 5.2 Frontend Monolítico (2315 linhas)
- [index.html](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/templates/index.html): **130KB** de HTML + CSS + JavaScript inline. Isso inclui:
  - ~220 linhas de CSS customizado
  - ~740 linhas de HTML/templates
  - ~1350 linhas de JavaScript puro
  - Zero separação de responsabilidades

### 5.3 Conexões SQLite por Request ⏳ PENDENTE
- Toda query abre/fecha uma conexão `sqlite3.connect(DB_FILE)`. Sem connection pooling ou abstração de repositório.
- Refactor grande — fora de escopo desta iteração.

### 5.4 ~~Código Duplicado — `valid_extensions`~~ ✅ CORRIGIDO
- Extraído para `VALID_EXTENSIONS` em [config.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/config.py). Importado em [book_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py) e [watchdog_service.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/watchdog_service.py).

### 5.5 ~~Rename Automático de Arquivos no Scan~~ ✅ CORRIGIDO
- Removido de [process_book()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/book_service.py#18-110). O endpoint dedicado `/api/books/auto-rename` continua disponível.

### 5.6 ~~Global Mutable State~~ ✅ CORRIGIDO
- [events.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/events.py) agora usa `threading.Lock()` para acesso thread-safe. Funções [add_client()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/events.py#18-21)/[remove_client()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/events.py#23-26) encapsulam o acesso.

---

## 6. 🧪 Testes

> [!CAUTION]
> O projeto tem **cobertura de testes próxima de zero**.

| Arquivo | Status |
|---------|--------|
| [test_meta.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/test_meta.py) | Script manual (não é pytest), com paths hardcoded |
| `tests/` | Apenas [conftest.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/tests/conftest.py) (fixtures), sem nenhum test case real |
| [test_scroll.js](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/test_scroll.js) | Script JS solto sem framework |

**Zero testes para:** rotas de API, lógica de scan, detecção de device, metadata search, watchdog, etc.

---

## 7. 📦 Arquivos Legados e Órfãos

| Arquivo | Problema |
|---------|---------|
| [legacy_main.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/legacy_main.py) | **1002 linhas** — cópia antiga de todo o app monolítico. Deve ser removido. |
| [__index.html](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/templates/__index.html) | Backup antigo do frontend (73KB). Deve ser removido. |
| [settings](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/settings) | Arquivo de 86 bytes sem extensão, ao lado de [settings.json](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/settings.json). Duplicação. |
| [tree.txt](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/tree.txt) | **250KB** — dump de diretório. Não deveria estar no repositório. |
| [test_scroll.js](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/test_scroll.js), [test_meta.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/test_meta.py) | Na raiz em vez de `tests/`. |
| [package.json](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/package.json)/`node_modules` | Apenas para Tailwind CDN? Verificar necessidade. |

---

## 8. 🔧 Outras Boas Práticas Ausentes

| Prática | Status |
|---------|--------|
| **Type Hints completos** | ❌ Muitas funções sem return type |
| **Docstrings em inglês** | ❌ Mistura PT/EN sem padrão |
| **Versioning de API** | ❌ `/api/books` sem `/v1/` |
| **CORS configurado** | ❌ Não encontrado |
| **Rate limiting** | ❌ APIs externas sem throttle |
| **Variáveis de ambiente** | ❌ Tudo hardcoded em [config.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/config.py) |
| **`.env` / `pydantic-settings`** | ❌ Ausente |
| **Migrations de DB** | ❌ `ALTER TABLE` no [init_db()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/legacy_main.py#205-267) — abordagem "boa sorte" |
| **CI/CD** | ❌ Nenhum pipeline configurado |
| **Linting (ruff/flake8)** | ❌ Nenhum configurado |
| **Formatação (black/ruff)** | ❌ Estilo inconsistente |

---

## 9. 📋 Prioridades de Correção

### 🔴 Alta Prioridade (Corrigir Imediatamente)
1. ~~Substituir todos `except: pass` por tratamento com logging~~ ✅ **FEITO** — ~20 bare excepts corrigidos com exceções específicas + logging
2. Remover [legacy_main.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/legacy_main.py), [__index.html](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/templates/__index.html), [tree.txt](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/tree.txt)
3. ~~Implementar módulo [logging](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/logger.py#6-13) no lugar de `print()`~~ ✅ **FEITO** — Criado [app/core/logger.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/logger.py), ~8 print() substituídos
4. ~~Validar URL no endpoint de download de capa (SSRF)~~ ✅ **FEITO** — [_is_safe_url()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/services/metadata_service.py#21-34) bloqueia IPs privados
5. ~~Mover `KINDLE_DOCUMENTS_FOLDER` para settings ou env var~~ ✅ **FEITO** — [get_kindle_folder()](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/config.py#43-54) lê de settings.json

### ⚠️ Média Prioridade (Sprint seguinte)
6. ~~Padronizar linguagem do código para inglês~~ ✅ **FEITO** — ~55 strings traduzidas (backend + frontend)
7. ~~Migrar `@app.on_event` para [lifespan](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/main.py#20-39)~~ ✅ **FEITO**
8. ~~Extrair `valid_extensions` para constante única em [config.py](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/app/core/config.py)~~ ✅ **FEITO**

### 🟡 Baixa Prioridade (Melhorias Futuras)
11. ~~Separar o [index.html](file:///c:/Users/frede/OneDrive/Documentos/Devs/Calibre%20Jr/templates/index.html) em componentes~~ ✅ **FEITO** — CSS e JS extraídos para `static/css` e `static/js`
12. Implementar i18n para UI PT-BR
13. ~~Adicionar connection pool / repositório para SQLite~~ ✅ **FEITO** — Dependência `get_db` adicionada via contextmanager
14. Configurar linter (ruff) e formatter
15. Implementar DB migrations com Alembic
