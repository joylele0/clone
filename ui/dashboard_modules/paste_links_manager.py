import flet as ft
import json
import os

SAVED_LINKS_FILE = "saved_links.json"


class PasteLinksManager:
    def __init__(self, dashboard):
        self.dash = dashboard
        
        try:
            from services.file_preview_service import FilePreviewService
            self.file_preview = FilePreviewService(dashboard.page, dashboard.drive)
        except ImportError:
            self.file_preview = None
    
    def load_saved_links(self):
        if os.path.exists(SAVED_LINKS_FILE):
            try:
                with open(SAVED_LINKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("links", [])
            except Exception as e:
                print(f"Error loading saved links: {e}")
                return []
        return []
    
    def save_saved_links(self, links):
        try:
            with open(SAVED_LINKS_FILE, "w", encoding="utf-8") as f:
                json.dump({"links": links}, f, indent=2)
        except Exception as e:
            print(f"Error saving saved links: {e}")
    
    def add_saved_link(self, file_id, info, original_url):
        links = self.load_saved_links()
        if any(l.get("id") == file_id for l in links):
            return False
        links.append({
            "id": file_id,
            "name": info.get("name", file_id),
            "mimeType": info.get("mimeType", ""),
            "url": original_url,
        })
        self.save_saved_links(links)
        return True
    
    def delete_saved_link(self, item):
        links = self.load_saved_links()
        links = [l for l in links if l.get("id") != item.get("id")]
        self.save_saved_links(links)
        
        if self.dash.current_view == "paste_links":
            self.load_paste_links_view()
    
    def open_saved_link(self, item):
        if item.get("mimeType") == "application/vnd.google-apps.folder":
            self.dash.folder_navigator.show_folder_contents(item["id"], item.get("name", item["id"]))
        else:
            if self.file_preview:
                self.file_preview.show_preview(
                    file_id=item["id"],
                    file_name=item.get("name", "File")
                )
            else:
                info = self.dash.drive.get_file_info(item["id"])
                if info:
                    self.dash.file_manager.show_file_info(info)
                else:
                    self.dash.page.snack_bar = ft.SnackBar(ft.Text("Failed to open saved link"), open=True)
                    self.dash.page.update()
    
    def load_paste_links_view(self):
        self.dash.current_view = "paste_links"
        self.dash.folder_list.controls.clear()

        header = ft.Container(
            content=ft.Text("Paste Drive Links", size=20, weight=ft.FontWeight.BOLD),
            padding=10
        )

        paste_section = ft.Container(
            content=ft.Column([
                ft.Text("Paste a Google Drive folder or file link:" , size=14),
                self.dash.paste_link_field,
                ft.ElevatedButton(
                    "Open Link",
                    on_click=self.handle_paste_link,
                    bgcolor=ft.Colors.BLUE_400,
                    color=ft.Colors.WHITE,
                    icon=ft.Icons.LINK
                ),
                ft.Text(
                    "Supported formats:\n"
                    "• https://drive.google.com/drive/folders/FOLDER_ID\n"
                    "• https://drive.google.com/file/d/FILE_ID\n"
                    "• https://drive.google.com/...?id=ID",
                    size=12,
                    color=ft.Colors.GREY_600
                )
            ], spacing=10),
            padding=20,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10
        )

        saved_links_header = ft.Container(
            content=ft.Text("Saved Links", size=16, weight=ft.FontWeight.BOLD),
            padding=ft.padding.only(top=20, bottom=10, left=10)
        )

        saved_links_list = ft.Container(
            content=self.build_saved_links_ui(),
            padding=10
        )

        self.dash.folder_list.controls.extend([
            header,
            paste_section,
            saved_links_header,
            saved_links_list
        ])

        self.dash.page.update()
    
    def handle_paste_link(self, e):
        link = self.dash.paste_link_field.value.strip()
        print(f"DEBUG: handle_paste_link called with: {link}")

        if not link:
            print("DEBUG: Empty link")
            return
        
        loading_snack = ft.SnackBar(
            content=ft.Text("Loading Drive link..."),
            open=True
        )
        self.dash.page.snack_bar = loading_snack
        self.dash.page.update()

        try:
            file_id, info = self.dash.drive.resolve_drive_link(link)

            print(f"DEBUG: file_id={file_id}, info={info}")

            if not file_id or not info:
                error_snack = ft.SnackBar(
                    content=ft.Text("Invalid or inaccessible Drive link"),
                    bgcolor=ft.Colors.RED_400,
                    open=True
                )
                self.dash.page.snack_bar = error_snack
                self.dash.page.update()
                return

            mime_type = info.get("mimeType", "")
            name = info.get("name", "Shared Item")

            print(f"DEBUG: mime_type={mime_type}, name={name}")

            try:
                saved_added = self.add_saved_link(file_id, info, link)
                if saved_added:
                    self.dash.page.snack_bar = ft.SnackBar(ft.Text("Saved link"), open=True)
                else:
                    self.dash.page.snack_bar = ft.SnackBar(ft.Text("Link already saved"), open=True)
            except Exception as ex:
                print(f"ERROR: Failed to save link: {ex}")

            if mime_type == "application/vnd.google-apps.folder":
                success_snack = ft.SnackBar(
                    content=ft.Text(f"Opening folder: {name}"),
                    bgcolor=ft.Colors.GREEN_400,
                    open=True
                )
                self.dash.page.snack_bar = success_snack
                self.dash.page.update()
                self.dash.folder_navigator.show_folder_contents(file_id, name)
            else:
                if self.file_preview:
                    info_snack = ft.SnackBar(
                        content=ft.Text(f"Opening preview: {name}"),
                        bgcolor=ft.Colors.BLUE_400,
                        open=True
                    )
                    self.dash.page.snack_bar = info_snack
                    self.dash.page.update()
                    self.file_preview.show_preview(file_id=file_id, file_name=name)
                else:
                    info_snack = ft.SnackBar(
                        content=ft.Text(f"File detected: {name}"),
                        bgcolor=ft.Colors.BLUE_400,
                        open=True
                    )
                    self.dash.page.snack_bar = info_snack
                    self.dash.page.update()
                    self.dash.file_manager.show_file_info(info)

            self.dash.paste_link_field.value = ""

        except Exception as ex:
            print(f"ERROR: Exception in handle_paste_link: {ex}")
            error_snack = ft.SnackBar(
                content=ft.Text(f"Error: {str(ex)}"),
                bgcolor=ft.Colors.RED_400,
                open=True
            )
            self.dash.page.snack_bar = error_snack

        if self.dash.current_view == "paste_links":
            self.load_paste_links_view()

        self.dash.page.update()
    
    def build_saved_links_ui(self):
        saved = self.load_saved_links()
        col = ft.Column(spacing=4)

        if not saved:
            col.controls.append(ft.Text("No saved links yet.", color=ft.Colors.GREY_600))
            return col

        for item in saved:
            is_folder = item.get("mimeType") == "application/vnd.google-apps.folder"
            icon = ft.Icons.FOLDER if is_folder else ft.Icons.DESCRIPTION

            row = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=20),
                    ft.Text(item["name"], expand=True),
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        tooltip="Preview" if not is_folder else "Open",
                        on_click=lambda e, it=item: self.open_saved_link(it)
                    ) if self.file_preview or is_folder else ft.Container(),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Delete",
                        on_click=lambda e, it=item: self.delete_saved_link(it)
                    )
                ]),
                padding=8,
                ink=True,
                on_click=lambda e, it=item: self.open_saved_link(it),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=8
            )

            col.controls.append(row)

        return col