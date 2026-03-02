const translations = {
    "en": {
        "title": "Calibre Jr. Library",
        "search_placeholder": "Search title, author...",
        "sort_by": "Sort by",
        "date_added": "Date Added",
        "author": "Author",
        "title_header": "Title",
        "tools": "Tools:",
        "auto_rename_all": "Auto-Rename All",
        "find_duplicates": "Find Duplicates",
        "maintenance": "Maintenance",
        "edit_mode_active": "EDIT MODE ACTIVE",
        "reading_list": "Reading List",
        "table_all": "All",
        "table_cover": "Cover",
        "table_title": "Title",
        "table_author": "Author",
        "table_actions": "Actions",
        "btn_read": "Read",
        "btn_details": "Details",
        "btn_download": "Download",
        "btn_send_kindle": "Send to Kindle",
        "btn_edit_metadata": "Edit Metadata",
        "btn_change_cover": "Change Cover",
        "btn_delete": "Delete",
        "modal_details_title": "Book Details",
        "modal_details_author": "Author:",
        "modal_details_language": "Language:",
        "modal_details_year": "Year:",
        "modal_details_publisher": "Publisher:",
        "modal_details_isbn": "ISBN:",
        "modal_details_tags": "Tags:",
        "modal_details_description": "Description:",
        "modal_edit_title": "Edit Metadata",
        "modal_edit_header_title": "Title",
        "modal_edit_header_author": "Author",
        "modal_edit_search_btn": "Search Online",
        "modal_edit_save_btn": "Save Changes",
        "modal_settings_title": "Directory Settings",
        "modal_settings_books": "Books Folder",
        "modal_settings_threads": "Scanner Threads",
        "modal_settings_save_btn": "Save & Re-scan",
        "reading_progress": "Reading...",
        "selected_items": "Selected",
        "action_send_kindle": "Send to Kindle",
        "action_delete": "Delete Selected",
        "folder_browser_title": "Select Folder",
        "folder_browser_select": "Select",
        "folder_browser_cancel": "Cancel",
        "status_scanning": "Scanning library...",
        "profiles_title": "Select Profile",
        "profiles_new": "New Profile",
        "profiles_create_btn": "Create Profile",
        "theme_system": "System Appearance",
        "theme_desc": "Select the interface colors.",
        "theme_dark": "Dark (Default)",
        "theme_light": "Light",
        "theme_pink": "Pink Light",
        "theme_dark_pink": "Pink Dark",
        "nav_library": "Library",
        "nav_collections": "Collections",
        "nav_activity": "Send Log"
    },
    "pt-BR": {
        "title": "Biblioteca Calibre Jr.",
        "search_placeholder": "Buscar título, autor...",
        "sort_by": "Ordenar por",
        "date_added": "Data de Adição",
        "author": "Autor",
        "title_header": "Título",
        "tools": "Ferramentas:",
        "auto_rename_all": "Auto-Renomear Todos",
        "find_duplicates": "Encontrar Duplicatas",
        "maintenance": "Manutenção",
        "edit_mode_active": "MODO DE EDIÇÃO ATIVADO",
        "reading_list": "Lista de Leitura",
        "table_all": "Todos",
        "table_cover": "Capa",
        "table_title": "Título",
        "table_author": "Autor",
        "table_actions": "Ações",
        "btn_read": "Ler",
        "btn_details": "Detalhes",
        "btn_download": "Baixar",
        "btn_send_kindle": "Enviar pro Kindle",
        "btn_edit_metadata": "Editar Metadados",
        "btn_change_cover": "Alterar Capa",
        "btn_delete": "Deletar",
        "modal_details_title": "Detalhes do Livro",
        "modal_details_author": "Autor:",
        "modal_details_language": "Idioma:",
        "modal_details_year": "Ano:",
        "modal_details_publisher": "Editora:",
        "modal_details_isbn": "ISBN:",
        "modal_details_tags": "Tags:",
        "modal_details_description": "Descrição:",
        "modal_edit_title": "Editar Metadados",
        "modal_edit_header_title": "Título",
        "modal_edit_header_author": "Autor",
        "modal_edit_search_btn": "Buscar Online",
        "modal_edit_save_btn": "Salvar Mudanças",
        "modal_settings_title": "Configurações de Diretórios",
        "modal_settings_books": "Pasta de Livros",
        "modal_settings_threads": "Threads do Scanner",
        "modal_settings_save_btn": "Salvar e Re-escanear",
        "reading_progress": "Lendo...",
        "selected_items": "Selecionados",
        "action_send_kindle": "Enviar pro Kindle",
        "action_delete": "Deletar Selecionados",
        "folder_browser_title": "Selecione a Pasta",
        "folder_browser_select": "Selecionar",
        "folder_browser_cancel": "Cancelar",
        "status_scanning": "Escaneando biblioteca...",
        "profiles_title": "Selecionar Perfil",
        "profiles_new": "Novo Perfil",
        "profiles_create_btn": "Criar Perfil",
        "theme_system": "Aparência do Sistema",
        "theme_desc": "Selecione as cores da interface.",
        "theme_dark": "Escuro (Padrão)",
        "theme_light": "Claro",
        "theme_pink": "Pink Claro",
        "theme_dark_pink": "Pink Escuro",
        "nav_library": "Biblioteca",
        "nav_collections": "Coleções",
        "nav_activity": "Atividade"
    }
};

let currentLocale = localStorage.getItem("locale") || "pt-BR";

function setLocale(locale) {
    if (translations[locale]) {
        currentLocale = locale;
        localStorage.setItem("locale", locale);
        updateInterface();
    }
}

function t(key) {
    const lang = translations[currentLocale] || translations["en"];
    return lang[key] || key;
}

function updateInterface() {
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (el.tagName === "INPUT" && el.hasAttribute("placeholder")) {
            el.setAttribute("placeholder", t(key));
        } else {
            el.textContent = t(key);
        }
    });

    // Handle initial selects
    document.querySelectorAll("[data-i18n-append]").forEach(el => {
        const key = el.getAttribute("data-i18n-append");
        // Optional implementation for append texts if needed
    });
}

// Call updateInterface on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
    updateInterface();
});
