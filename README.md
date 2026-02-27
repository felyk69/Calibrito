<p align="center">
  <img src="Interface/dashboard_preview.png" alt="Calibrito Dashboard" width="100%">
</p>

<h1 align="center">📚 Calibrito</h1>

<p align="center">
  <strong>🇧🇷 Um gerenciador de biblioteca digital moderno e self-hosted para Kindle & KOReader</strong><br>
  <strong>🇺🇸 A modern, self-hosted ebook library manager for Kindle & KOReader</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.131-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLite-WAL_Mode-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Tailwind_CSS-CDN-38B2AC?logo=tailwindcss&logoColor=white" alt="TailwindCSS">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

---

> 🇧🇷 **Português** abaixo | 🇺🇸 **English** [click here](#-english)

---

# 🇧🇷 Português

## ✨ Funcionalidades

### 📖 Gerenciamento da Biblioteca
- **Suporte multi-formato** — EPUB, MOBI, AZW3, PDF, FB2, CBZ
- **Auto-scan & watchdog** — Monitora sua pasta de ebooks em tempo real
- **Enriquecimento de metadados** — Busca no Google Books & OpenLibrary por título ou ISBN
- **Extração de capas** — Capas extraídas automaticamente dos arquivos ou de fontes online
- **Scanner de duplicatas** — Detecta duplicatas por hash MD5 e metadados normalizados
- **Auto-renomeador** — Renomeia em lote para o formato `Autor - Título.ext`
- **Filtro por formato** — Pills de filtro rápido por EPUB, MOBI, AZW3
- **Grid & Lista** — Slider de zoom ajustável com múltiplos layouts

### 📱 Integração com Dispositivos
- **Detecção do Kindle** — Detecta automaticamente drives USB do Kindle
- **Suporte a KOReader** — Identifica instalações do KOReader em dispositivos conectados
- **Envio para dispositivo** — Transferência com um clique e progresso em tempo real
- **Operações em lote** — Multi-seleção para envio ou exclusão em massa

### 📕 Leitor Web Integrado
- **Powered by foliate-js** — Lê EPUB, MOBI, AZW3, PDF, FB2, CBZ direto no navegador
- **Temas de leitura** — Dark, Light, Sépia
- **Controle de fonte** — Tamanho ajustável (70%–200%)
- **Modos de leitura** — Paginado (com animação) ou scroll contínuo
- **Sumário (TOC)** — Painel lateral deslizante com capítulos clicáveis
- **Tracking de progresso** — Salva posição automaticamente por livro e perfil

### 🔍 Busca de Metadados
- **Multi-fonte** — Busca paralela no Google Books + OpenLibrary
- **Suporte a ISBN** — Detecta ISBN-10/13 e usa endpoints especializados
- **Preview de capa** — Atualização ao vivo ao selecionar resultados
- **Tags como chips** — Adicione/remova tags com interface visual

### 🎨 UI/UX
- **UI dark moderna** — Efeitos glassmorphism, animações suaves
- **Múltiplos temas** — Dark, Light, Pink, Sépia
- **Modal de edição** — Layout 2 colunas com preview de capa, busca e edição inline
- **Menu contextual** — Ações: Ler, Enviar, Editar, Baixar, Excluir
- **Design responsivo** — Funciona em desktop e tablet

---

## 🏗️ Arquitetura

```
app/
├── main.py                  # App FastAPI, startup/shutdown, rotas
├── core/
│   ├── config.py            # Caminhos, settings, constantes
│   ├── database.py          # SQLite init, migrations, WAL mode
│   └── events.py            # Broadcasting de eventos SSE
├── models/
│   └── schemas.py           # Modelos Pydantic
├── services/
│   ├── book_service.py      # Scan, extração de metadados, threading
│   ├── metadata_service.py  # Busca paralela Google Books + OpenLibrary
│   ├── device_service.py    # Detecção USB de Kindle/KOReader
│   └── watchdog_service.py  # Monitoramento do sistema de arquivos
└── api/routes/
    ├── books.py             # CRUD, envio, duplicatas, auto-rename
    ├── metadata.py          # Busca & download de capas
    ├── events.py            # Stream SSE
    └── misc.py              # Settings, perfis, progresso de leitura

templates/
├── index.html               # Dashboard SPA (TailwindCSS)
└── reader.html              # Leitor web (foliate-js)
```

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.10+
- pip

### Instalação

```bash
# Clone o repositório
git clone https://github.com/felyk69/Calibrinho.git
cd Calibrinho

# Crie o ambiente virtual
python -m venv venv

# Ative (Windows)
.\venv\Scripts\activate
# Ative (macOS/Linux)
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### Executando

```bash
uvicorn app.main:app --reload
```

Abra **http://localhost:8000** no navegador.

### Primeira Configuração

1. Clique no ícone ⚙️ **Configurações** no header
2. Defina o caminho da sua pasta de ebooks (ex: `C:/Users/voce/Ebooks`)
3. Clique **Salvar** — o scanner indexará sua biblioteca automaticamente
4. Conecte seu Kindle/KOReader via USB para habilitar o envio

---

## 📸 Screenshots

<table>
  <tr>
    <td width="50%"><img src="Interface/dashboard_preview.png" alt="Dashboard"></td>
    <td width="50%"><img src="Interface/edit_modal_preview.png" alt="Modal de Edição"></td>
  </tr>
  <tr>
    <td align="center"><em>Dashboard da Biblioteca</em></td>
    <td align="center"><em>Modal de Edição de Metadados</em></td>
  </tr>
</table>

---

## 🗺️ Roadmap

Veja [ROADMAP.md](ROADMAP.md) para o roadmap completo.

**Concluído:**
- ✅ Arquitetura modular (Controller-Service-Model)
- ✅ Leitor Web integrado (foliate-js)
- ✅ Auto-renomeador & scanner de duplicatas
- ✅ Busca de metadados multi-fonte

**Planejado:**
- 📡 Servidor OPDS para download wireless via KOReader
- 📧 Send-to-Kindle via email
- 👥 Sistema multi-perfis
- ⭐ Status de leitura, notas & coleções
- 🔄 Conversão de formatos on-the-fly

---

# 🇺🇸 English

## ✨ Features

### 📖 Library Management
- **Multi-format support** — EPUB, MOBI, AZW3, PDF, FB2, CBZ
- **Auto-scan & watchdog** — Monitors your ebook folder for new files in real-time
- **Metadata enrichment** — Search Google Books & OpenLibrary by title or ISBN
- **Cover extraction** — Automatic cover art from ebook files or online sources
- **Smart duplicate scanner** — Detects duplicates by MD5 hash and normalized metadata
- **Auto-renamer** — Batch rename files to `Author - Title.ext` format
- **Format filter pills** — Quick filter by EPUB, MOBI, AZW3
- **Grid & List views** — Adjustable zoom slider with multiple layouts

### 📱 Device Integration
- **Kindle detection** — Auto-detects Kindle USB drives
- **KOReader support** — Detects KOReader installations on connected devices
- **Send to device** — One-click file transfer with real-time progress streaming
- **Batch operations** — Multi-select books for bulk send or delete

### 📕 Built-in Web Reader
- **foliate-js powered** — Reads EPUB, MOBI, AZW3, PDF, FB2, CBZ directly in the browser
- **Reading themes** — Dark, Light, Sepia
- **Font controls** — Adjustable font size (70%–200%)
- **Reading modes** — Paginated (with animation) or continuous scroll
- **Table of Contents** — Slide-in sidebar with clickable chapters
- **Progress tracking** — Auto-saves reading position per book per profile

### 🔍 Metadata Search
- **Multi-source** — Parallel search across Google Books + OpenLibrary
- **ISBN support** — Detects ISBN-10/13 and uses specialized API endpoints
- **Cover preview** — Live preview updates when selecting search results
- **Tag chips** — Add/remove tags with visual chip interface

### 🎨 UI/UX
- **Modern dark UI** — Glassmorphism effects, smooth animations
- **Multiple themes** — Dark, Light, Pink, Sepia
- **Edit Metadata modal** — 2-column layout with cover preview, search, and inline editing
- **Contextual menus** — Right-click actions: Read, Send, Edit, Download, Delete
- **Responsive design** — Works on desktop and tablet browsers

---

## 🏗️ Architecture

```
app/
├── main.py                  # FastAPI app, startup/shutdown, routes
├── core/
│   ├── config.py            # Paths, settings, constants
│   ├── database.py          # SQLite init, migrations, WAL mode
│   └── events.py            # SSE event broadcasting
├── models/
│   └── schemas.py           # Pydantic models
├── services/
│   ├── book_service.py      # Scanning, metadata extraction, threading
│   ├── metadata_service.py  # Google Books + OpenLibrary parallel search
│   ├── device_service.py    # Kindle/KOReader USB detection
│   └── watchdog_service.py  # File system watcher
└── api/routes/
    ├── books.py             # CRUD, send, duplicates, auto-rename
    ├── metadata.py          # Search & cover download
    ├── events.py            # SSE stream
    └── misc.py              # Settings, profiles, reading progress

templates/
├── index.html               # Dashboard SPA (TailwindCSS)
└── reader.html              # Web reader (foliate-js)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/felyk69/Calibrinho.git
cd Calibrinho

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000** in your browser.

### First-time Setup

1. Click the ⚙️ **Settings** icon in the header
2. Set your ebook folder path (e.g., `C:/Users/you/Ebooks`)
3. Click **Save** — the scanner will index your library automatically
4. Plug in your Kindle/KOReader device to enable sending

---

## 📸 Screenshots

<table>
  <tr>
    <td width="50%"><img src="Interface/dashboard_preview.png" alt="Dashboard"></td>
    <td width="50%"><img src="Interface/edit_modal_preview.png" alt="Edit Modal"></td>
  </tr>
  <tr>
    <td align="center"><em>Library Dashboard</em></td>
    <td align="center"><em>Edit Metadata Modal</em></td>
  </tr>
</table>

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, FastAPI, Uvicorn |
| **Database** | SQLite (WAL mode) |
| **Frontend** | HTML, JavaScript, TailwindCSS (CDN) |
| **Templating** | Jinja2 |
| **Reader** | foliate-js (jsDelivr CDN) |
| **Metadata** | Google Books API, OpenLibrary API |
| **Ebook Parsing** | ebookmeta, PyMuPDF (fitz) |
| **File Watching** | watchdog |
| **Device Detection** | Custom USB drive scanner |

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/books` | List all books |
| `PUT` | `/api/books/{id}` | Update book metadata |
| `POST` | `/api/send` | Send book to Kindle (streamed) |
| `POST` | `/api/delete` | Delete books (trash or permanent) |
| `GET` | `/api/books/duplicates` | Find duplicate books |
| `POST` | `/api/books/auto-rename` | Batch rename all files |
| `GET` | `/api/metadata/search?q=` | Search metadata (Google + OpenLibrary) |
| `GET` | `/api/detect-device` | Detect Kindle/KOReader USB |
| `GET` | `/api/settings` | Get app settings |
| `PUT` | `/api/settings` | Update settings & rescan |
| `GET` | `/api/events` | SSE real-time events stream |
| `GET` | `/reader?id=` | Open book in web reader |

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development roadmap.

**Completed:**
- ✅ Modular architecture (Controller-Service-Model)
- ✅ Built-in Web Reader (foliate-js)
- ✅ Auto-renamer & duplicate scanner
- ✅ Multi-source metadata search

**Planned:**
- 📡 OPDS server for wireless KOReader downloading
- 📧 Send-to-Kindle via email
- 👥 Multi-profile system
- ⭐ Reading status, ratings & collections
- 🔄 On-the-fly format conversion

---

## 🤝 Contributing / Contribuindo

🇧🇷 Contribuições são bem-vindas! Sinta-se livre para abrir issues ou enviar pull requests.

🇺🇸 Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📄 License / Licença

This project is licensed under the MIT License.

---

<p align="center">
  Made with ❤️ for ebook enthusiasts who want a <strong>lightweight alternative to Calibre</strong><br>
  Feito com ❤️ para entusiastas de ebooks que querem uma <strong>alternativa leve ao Calibre</strong>
</p>
