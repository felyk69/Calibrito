# Calibre Jr. V2.0 - Roadmap e Próximos Passos (Backlog)

Este documento detalha as sugestões de evolução e novas funcionalidades para a próxima grande fase do Calibre Jr. (V2.0), organizadas por categoria e inovação. A fase V1 de enriquecimento, temas, e suporte a séries foi concluída com sucesso.

## 📡 1. O Calibre Jr "Sem Fio" (Wireless & Nuvem)
*   **Servidor OPDS (A Mágica do KOReader):**
    *   **Funcionalidade:** Criar uma rota OPDS no backend Python.
    *   **Ação:** O KOReader nativamente consegue acessar "Catálogos de Rede OPDS" via Wi-Fi. Resultado: Você liga o Wi-Fi no Kindle, entra no KOReader e baixa o arquivo do seu PC sem plugar cabo USB.
*   **Botão "Send-to-Kindle" via E-mail:**
    *   **Funcionalidade:** Adicionar botão de "Enviar" via E-mail.
    *   **Ação:** Para quando o Kindle estiver na rua ou rodando no sistema nativo. Usando `smtplib` envia o arquivo direto para o "@kindle.com" ativando a sincronia de nuvem da Amazon.

## 📖 2. Netflix de Livros (Media Server)
*   **Leitor Embutido no Web (WebReader):**
    *   **Funcionalidade:**  Usar uma biblioteca como `epub.js`.
    *   **Ação:** Você pode abrir e *ler* os livros pelo próprio navegador do PC, Tablet ou Celular conectado na rede local. O banco de dados salva a configuração e a "página/marcador".
*   **Sistema Multi-Perfis:**
    *   **Funcionalidade:** Sessões de usuário ou abas.
    *   **Ação:** "Biblioteca do Fred", "Biblioteca da Esposa", separando o progresso de leitura e favoritos de cada morador da casa.

## 📚 3. Organização Profunda, Automação & Gamificação
*   **Padronizador Automático de Arquivos (Auto-Renamer):**
    *   **Funcionalidade:** Botão ou Hook "Auto-Renomear Arquivos Físicos".
    *   **Ação:** Se o livro no disco rígido estiver com nome feio (`h4rrY_potter.epub`), o sistema pega os Metadados + Capa que limpamos via Google API e renomeia o arquivo físico para manter a pasta impecável (ex: `J.K. Rowling - Harry Potter.epub`).
*   **Gestão de Lidos vs Não Lidos:**
    *   **Funcionalidade:** "Status de Leitura" e "Nota".
    *   **Ação:** Exibir uma barrinha de progresso no card (X%) ou um flag verde "Terminado", filtrável no Menu Lateral e com a possibilidade de você dar notas (1 a 5 Estrelas).
*   **Tags & Prateleiras Virtuais (Collections):**
    *   **Funcionalidade:** Pastas lógicas em vez de físicas.
    *   **Ação:** Criar Categorias ("Sci-Fi", "Terminar esse Mês", "Favoritos").
*   **Faxina de Duplicatas:**
    *   **Funcionalidade:** Scanner inteligente anti-cópias.
    *   **Ação:** Um botão no Manage Dashboard que varre o PC atrás de Hashes ou Títulos e Autores parecidos para você checar se tem dois E-pubs do mesmo livro jogados na pasta.
*   **Upload e Watchdog Inteligente (Drag & Drop):**
    *   **Funcionalidade:** Subir novos PDFs e E-Pubs pela interface web direto pro PC Hospedeiro. Em complemento com o Watchdog da Pasta `Ebooks`.

## ⚙️ 4. Motor de Conversão Transparente
*   **Conversão 'On-the-Fly' (Na mosca):**
    *   **Funcionalidade:** Integração com bibliotecas CLI como `calibre-cli`, `kepubify` (para KOBO) ou `pandoc`.
    *   **Ação:** Se tentar enviar um arquivo formato antigo (EPUB para firmware antigo de Kindle nativo), o servidor intercepta o envio, converte silenciosamente em RAM para o formato mais amigoso para aquele USB conectado, e envia convertido.

---
*Gerado para direcionar os pranchins e ideias disruptivas da Versão 2 do sistema.*
