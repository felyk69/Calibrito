# Calibre Jr. - Roadmap e Próximos Passos

Este documento detalha as sugestões de evolução e novas funcionalidades para o Calibre Jr., organizadas por categoria e prioridade.

## 1. Enriquecimento de Metadados (Scraping) 🌐
Atualmente as capas e autores vêm apenas de dentro do arquivo.
*   **Integração com API (Google Books API / OpenLibrary):**
    *   **Funcionalidade:** Adicionar um botão "Buscar Metadados na Internet" no modal de Edição.
    *   **Ação:** O sistema faria uma busca rápida pelo título ou autor e sugeriria a capa oficial em alta resolução, sinopse, publicadora e ano, salvando tudo no banco de dados local.
*   **Suporte a Séries e Coleções:**
    *   **Funcionalidade:** Adicionar os campos "Série" e "Volume" (ex: *Harry Potter - Vol 1*).
    *   **Ação:** Essencial para quem organiza bibliotecas de mangás (arquivos CBZ) e franquias de livros literários.

## 2. Automação e Importação 🤖
Melhorar a forma como novos livros entram no sistema.
*   **Pasta Monitorada (Watchdog):**
    *   **Funcionalidade:** Fazer o servidor Python observar a pasta `Ebooks` do Windows em tempo real.
    *   **Ação:** Ao baixar um novo e-book e salvar na pasta, o sistema automaticamente extrai a capa, lê os metadados e atualiza a interface Web sem a necessidade de recarregar a página (via WebSockets ou SSE).
*   **Upload via Web (Drag & Drop):**
    *   **Funcionalidade:** Adicionar uma área de "Arrastar e Soltar" na interface web.
    *   **Ação:** Permitir o envio de livros para o servidor local diretamente pelo navegador, processando a extração da capa durante o upload.

## 3. Melhorias de Leitura e Experiência (UX/UI) 📱
Aprimorar a performance e a usabilidade geral.
*   **Conversão Automática "Na Mosca":**
    *   **Funcionalidade:** Integração com bibliotecas de conversão (ex: executável do *calibre-cli* ou *kindlegen*).
    *   **Ação:** Se o usuário tentar enviar um arquivo formato antigo ou incompatível para o *Modo Kindle Nativo*, o sistema o converte silenciosamente para `.kfx` ou `.azw3` antes de colocar no USB.
*   **Paginação e Lazy Loading:**
    *   **Funcionalidade:** Carregamento sob demanda (Infinite Scroll).
    *   **Ação:** Ao invés de popular frentes de HTML com milhares de livros, carregar "blocos" de 50 livros conforme a tela desliza para baixo, blindando o navegador contra travamentos em acervos massivos.


## 4. Refinamento de Estatísticas e Gerenciamento 📊
*   **Destaque para "Lidos" e "Não Lidos":**
    *   **Funcionalidade:** Marcadores visuais simples.
    *   **Ação:** Permitir que o usuário saiba o que já leu diretamente pela Galeria.
*   **Filtros Avançados na Barra Lateral:**
    *   **Funcionalidade:** Checkboxes dinâmicos.
    *   **Ação:** Ampliar o atual filtro (Kindle vs KOReader) incluindo categorias de "Tags", "Apenas PDFs", "Mangás/HQ's", etc.

---
*Gerado para orientar as próximas fases de desenvolvimento.*
