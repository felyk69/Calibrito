import os
import re

def detect_device():
    import string
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            docs_path = os.path.join(drive, "documents")
            system_path = os.path.join(drive, "system")
            
            # Check for KOReader installation
            koreader_dirs = ["koreader", "extensions/koreader", ".adds/koreader"]
            koreader_root = None
            for kd in koreader_dirs:
                full_kd = os.path.join(drive, kd)
                if os.path.exists(full_kd):
                    koreader_root = full_kd
                    break

            # Aceita se for um Kindle Clássico OU se apenas tiver a pasta KOReader (útil pra Pendrives simulados ou Kobo)
            is_kindle = os.path.exists(docs_path) and os.path.exists(system_path)
            
            if is_kindle or koreader_root:
                device_info = {
                    "connected": True,
                    "drive": drive.replace('\\', '/'),
                    "kindle_path": docs_path.replace('\\', '/') if os.path.exists(docs_path) else drive.replace('\\', '/'),
                    "has_koreader": bool(koreader_root),
                    "koreader_path": ""
                }
                
                if device_info["has_koreader"]:
                    # 1. Tentar ler o settings.reader.lua para descobrir a pasta exata!
                    settings_file = os.path.join(koreader_root, "settings.reader.lua")
                    found_path = None
                    if os.path.exists(settings_file):
                        try:
                            with open(settings_file, "r", encoding="utf-8") as f:
                                content = f.read()
                                match = re.search(r'\["home_dir"\]\s*=\s*"([^"]+)"', content)
                                if match:
                                    linux_path = match.group(1)
                                    if linux_path.startswith("/mnt/us/"):
                                        relative_path = linux_path[8:]
                                    elif linux_path.startswith("/mnt/ext1/"): # PocketBook
                                        relative_path = linux_path[10:]
                                    else:
                                        relative_path = linux_path.lstrip('/')
                                        
                                    relative_path = relative_path.replace('/', '\\')
                                    found_path = os.path.join(drive, relative_path)
                                    if os.path.exists(found_path):
                                        device_info["koreader_path"] = found_path.replace('\\', '/')
                        except Exception:
                            pass
                    
                    if not device_info["koreader_path"]:
                        common_libs = ["library", "books", "livros", "downloads", "koreader/library"]
                        for cl in common_libs:
                            full_cl = os.path.join(drive, cl)
                            if os.path.exists(full_cl):
                                device_info["koreader_path"] = full_cl.replace('\\', '/')
                                break
                    
                    if not device_info["koreader_path"]:
                        device_info["koreader_path"] = drive.replace('\\', '/')
                        
                return device_info
    
    return {"connected": False}
