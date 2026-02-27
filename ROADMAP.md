# Calibre Jr. V2.0 - Roadmap e Próximos Passos (Backlog)

Este documento detalha as sugestões de evolução e novas funcionalidades para a próxima grande fase do Calibre Jr. (V2.0), organizadas por categoria e inovação. A fase V1 de enriquecimento, temas, e suporte a séries foi concluída com sucesso.

---

## ✅ Fase 0 — Refatoração & Testes (CONCLUÍDA)

> Modularização do `main.py` monolítico em arquitetura Controller-Service-Model.

- [x] **Modularização do Backend** — `main.py` dividido em `app/core/`, `app/models/`, `app/services/`, `app/api/routes/`
- [x] **Schemas Pydantic** — Todos os modelos centralizados em `app/models/schemas.py`
- [x] **Database Layer** — `app/core/database.py` com init, migrations, WAL mode
- [x] **Services** — `book_service`, `metadata_service`, `device_service`, `watchdog_service`
- [x] **API Routes** — `books.py`, `metadata.py`, `events.py`, `misc.py`
- [x] **Testes com pytest** — `tests/conftest.py`, `tests/api/test_books_api.py`
- [x] **Comando de execução** — `uvicorn app.main:app --reload`

---

## ✅ Fase 1 — WebReader Embutido (CONCLUÍDA)

> Leitor de e-books no navegador usando `foliate-js` via CDN.

- [x] **Suporte multi-formato** — EPUB, MOBI, AZW3, PDF, FB2, CBZ via `/api/books/{id}/file`
- [x] **Página dedicada** — `templates/reader.html` com foliate-js (CDN jsDelivr)
- [x] **Temas do leitor** — Escuro (invert), Claro, Sépia via CSS `::part(filter)`
- [x] **Controle de fonte** — Aumentar/diminuir tamanho (70%–200%)
- [x] **Modos de leitura** — Paginado (com animação) e Scroll
- [x] **Sumário (TOC)** — Painel lateral slide-in com capítulos clicáveis
- [x] **Navegação** — Tap zones (esq/centro/dir), teclado (←→), slider de progresso
- [x] **Layout responsivo** — `max-column-count=2` + `max-inline-size=720` (1 coluna em retrato, 2 em paisagem)
- [x] **Progresso de leitura** — CFI (EPUB) + percentual (outros formatos), auto-save com debounce 3s
- [x] **Perfil padrão** — Vinculado ao perfil "Visitante" (id=1)
- [x] **Botão "Ler"** — Visível em todos os cards de livros compatíveis (não só EPUB)
- [x] **Botão "Fechar"** — Salva progresso e fecha a aba

---

## ✅ Fase 2 — Organização de Arquivos (CONCLUÍDA)

> Auto-renomear e scanner de duplicatas no modo de edição.

- [x] **Auto-Renamer em lote** — `POST /api/books/auto-rename` renomeia todos os arquivo para `Autor - Título.ext`
- [x] **Scanner de Duplicatas** — `GET /api/books/duplicates` busca por hash MD5 (idênticos) + título/autor normalizado (similares)
- [x] **Prioridade de formatos** — EPUB > AZW3 > MOBI > PDF (melhor formato = "Original")
- [x] **Modal de duplicatas** — Grid visual com capas, checkboxes, "Manter melhor em todos", exclusão em lote
- [x] **Barra de ferramentas Edição** — Botões "Auto-Renomear Todos" e "Buscar Duplicatas" no modo manutenção
- [x] **Banner fixo Modo Edição** — Indicador permanente no topo + fundo laranja sutil
- [x] **Fix EPub Reader** — Corrigido erro `endsWith` no foliate-js (Blob → File com filename)

---

## 📡 3. O Calibre Jr "Sem Fio" (Wireless & Nuvem)
*   **Servidor OPDS (A Mágica do KOReader):**
    *   **Funcionalidade:** Criar uma rota OPDS no backend Python.
    *   **Ação:** O KOReader nativamente consegue acessar "Catálogos de Rede OPDS" via Wi-Fi. Resultado: Você liga o Wi-Fi no Kindle, entra no KOReader e baixa o arquivo do seu PC sem plugar cabo USB.
*   **Botão "Send-to-Kindle" via E-mail:**
    *   **Funcionalidade:** Adicionar botão de "Enviar" via E-mail.
    *   **Ação:** Para quando o Kindle estiver na rua ou rodando no sistema nativo. Usando `smtplib` envia o arquivo direto para o "@kindle.com" ativando a sincronia de nuvem da Amazon.

## 📖 4. Sistema Multi-Perfis
*   **Funcionalidade:** Sessões de usuário ou abas.
*   **Ação:** "Biblioteca do Fred", "Biblioteca da Esposa", separando o progresso de leitura e favoritos de cada morador da casa.
*   **Status:** Backend preparado (tabelas `profiles`, `reading_progress` com `profile_id`). Falta criar a UI de seleção de perfil.

## 📚 5. Organização Profunda & Gamificação
*   ~~**Padronizador Automático de Arquivos (Auto-Renamer):**~~ ✅ Concluído na Fase 2
*   **Gestão de Lidos vs Não Lidos:**
    *   **Funcionalidade:** "Status de Leitura" e "Nota".
    *   **Ação:** Exibir uma barrinha de progresso no card (X%) ou um flag verde "Terminado", filtrável no Menu Lateral e com a possibilidade de você dar notas (1 a 5 Estrelas).
*   **Tags & Prateleiras Virtuais (Collections):**
    *   **Funcionalidade:** Pastas lógicas em vez de físicas.
    *   **Ação:** Criar Categorias ("Sci-Fi", "Terminar esse Mês", "Favoritos").
*   ~~**Faxina de Duplicatas:**~~ ✅ Concluído na Fase 2
*   **Upload e Watchdog Inteligente (Drag & Drop):**
    *   **Funcionalidade:** Subir novos PDFs e E-Pubs pela interface web direto pro PC Hospedeiro. Em complemento com o Watchdog da Pasta `Ebooks`.

## ⚙️ 5. Motor de Conversão Transparente
*   **Conversão 'On-the-Fly' (Na mosca):**
    *   **Funcionalidade:** Integração com bibliotecas CLI como `calibre-cli`, `kepubify` (para KOBO) ou `pandoc`.
    *   **Ação:** Se tentar enviar um arquivo formato antigo (EPUB para firmware antigo de Kindle nativo), o servidor intercepta o envio, converte silenciosamente em RAM para o formato mais amigoso para aquele USB conectado, e envia convertido.

---
*Gerado para direcionar os pranchins e ideias disruptivas da Versão 2 do sistema.*
