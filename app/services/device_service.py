import os
import re

from app.core.logger import get_logger

logger = get_logger("device")


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

            # Accept classic Kindle OR KOReader-only devices (USB drives, Kobo)
            is_kindle = os.path.exists(docs_path) and os.path.exists(system_path)

            if is_kindle or koreader_root:
                device_info = {
                    "connected": True,
                    "drive": drive.replace("\\", "/"),
                    "kindle_path": docs_path.replace("\\", "/")
                    if os.path.exists(docs_path)
                    else drive.replace("\\", "/"),
                    "has_koreader": bool(koreader_root),
                    "koreader_path": "",
                }

                if device_info["has_koreader"]:
                    # Try to read settings.reader.lua to find the exact library path
                    settings_file = os.path.join(koreader_root, "settings.reader.lua")
                    found_path = None
                    if os.path.exists(settings_file):
                        try:
                            with open(settings_file, encoding="utf-8") as f:
                                content = f.read()
                                match = re.search(r'\["home_dir"\]\s*=\s*"([^"]+)"', content)
                                if match:
                                    linux_path = match.group(1)
                                    if linux_path.startswith("/mnt/us/"):
                                        relative_path = linux_path[8:]
                                    elif linux_path.startswith("/mnt/ext1/"):  # PocketBook
                                        relative_path = linux_path[10:]
                                    else:
                                        relative_path = linux_path.lstrip("/")

                                    relative_path = relative_path.replace("/", "\\")
                                    found_path = os.path.join(drive, relative_path)
                                    if os.path.exists(found_path):
                                        device_info["koreader_path"] = found_path.replace("\\", "/")
                        except (OSError, UnicodeDecodeError) as e:
                            logger.warning("Failed to read KOReader settings: %s", e)

                    if not device_info["koreader_path"]:
                        common_libs = [
                            "library",
                            "books",
                            "livros",
                            "downloads",
                            "koreader/library",
                        ]  # 'livros' intentional (PT folder name)
                        for cl in common_libs:
                            full_cl = os.path.join(drive, cl)
                            if os.path.exists(full_cl):
                                device_info["koreader_path"] = full_cl.replace("\\", "/")
                                break

                    if not device_info["koreader_path"]:
                        device_info["koreader_path"] = drive.replace("\\", "/")

                return device_info

    return {"connected": False}
