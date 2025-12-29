import flet as ft
import json
from pathlib import Path
from typing import Dict, Any

def load_json_file(filepath: str | Path, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if isinstance(filepath, str):
        filepath = Path(filepath)

    if filepath.exists():
        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    return default if default is not None else {}



def save_json_file(filepath, data):
    if isinstance(filepath, str):
        filepath = Path(filepath)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving: {e}")
        return False


def format_file_size(size_bytes):
    if size_bytes is None:
        return "Unknown size"
    try:
        size = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except (ValueError, TypeError):
        return "Unknown size"


def extract_drive_id(url):
    import re
    patterns = [
        r"/folders/([a-zA-Z0-9_-]+)",
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    if len(url) > 20 and "/" not in url:
        return url
    
    return None


def open_url(url):
    import webbrowser
    webbrowser.open(url)


def open_drive_file(file_id):
    open_url(f"https://drive.google.com/file/d/{file_id}/view")


def open_drive_folder(folder_id):
    open_url(f"https://drive.google.com/drive/folders/{folder_id}")



def create_icon_button(icon, tooltip, on_click, color=None):
    return ft.IconButton(
        icon=icon,
        tooltip=tooltip,
        on_click=on_click,
        icon_color=color
    )


def show_snackbar(page, message, color=ft.Colors.BLUE, duration=3):
    import threading
    
    toast = ft.Container(
        content=ft.Text(message, color=ft.Colors.WHITE),
        bgcolor=color,
        padding=10,
        border_radius=5,
        bottom=20,
        right=20,
        opacity=0.9
    )
    
    page.overlay.append(toast)
    page.update()
    
    def remove_toast():
        import time
        time.sleep(duration)
        if toast in page.overlay:
            page.overlay.remove(toast)
            page.update()
    
    threading.Thread(target=remove_toast, daemon=True).start()