import flet as ft
from utils.common import format_file_size, create_icon_button, show_snackbar, create_dialog, open_drive_file


class FileManager:
    def __init__(self, dashboard):
        self.dash = dashboard
        
        try:
            from services.file_preview_service import FilePreviewService
            self.file_preview = FilePreviewService(dashboard.page, dashboard.drive)
        except ImportError:
            self.file_preview = None

    def show_menu(self, item, is_folder=False, is_shared_drive=False):
        
        def on_preview(e):
            if not is_folder:
                self.preview_file(item)

        def on_rename(e):
            self._rename_file_dialog(item)

        def on_delete(e):
            self._delete_file_dialog(item)

        def on_info(e):
            self.show_file_info(item)
        
        menu_items = [
            ft.PopupMenuItem(text="Preview", icon=ft.Icons.VISIBILITY, on_click=on_preview) if self.file_preview and not is_folder else None,
            ft.PopupMenuItem(text="Info", icon=ft.Icons.INFO, on_click=on_info),
            ft.PopupMenuItem(text="Rename", icon=ft.Icons.EDIT, on_click=on_rename),
            ft.PopupMenuItem(text="Delete", icon=ft.Icons.DELETE, on_click=on_delete),
        ]

        return [item for item in menu_items if item is not None]

    def create_folder_item(self, folder, subfolder_count, is_shared_drive=False):
        folder_name = folder.get("name", "Untitled")
        display_name = folder_name if len(folder_name) < 40 else folder_name[:37] + "..."
        
        menu_items = self.show_menu(folder, is_folder=True, is_shared_drive=is_shared_drive)

        return ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.FOLDER, size=24),
                    ft.Column([
                        ft.Text(display_name, size=14),
                        ft.Text(f"{subfolder_count} folders", size=12, color=ft.Colors.GREY_600),
                    ], expand=True),
                    ft.PopupMenuButton(items=menu_items),
                ]),
                padding=8,
                ink=True,
                on_click=lambda e, f=folder: self.open_folder(f, is_shared_drive),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            )
        
    
    def create_file_item(self, file):
        is_folder = file.get("mimeType") == "application/vnd.google-apps.folder"
        icon = ft.Icons.FOLDER if is_folder else ft.Icons.INSERT_DRIVE_FILE
        size_str = "Folder" if is_folder else format_file_size(file.get("size"))

        menu_items = self.show_menu(file, is_folder=is_folder)
        action_buttons = []
        if not is_folder and self.file_preview:
            action_buttons.append(
                create_icon_button(ft.Icons.VISIBILITY, "Preview", 
                                  lambda e, f=file: self.preview_file(f))
            )
        action_buttons.append(
            ft.PopupMenuButton(items=menu_items)
        )

        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=24),
                ft.Column([
                    ft.Text(file.get("name", "Untitled"), size=14),
                    ft.Text(size_str, size=12, color=ft.Colors.GREY_600),
                ], expand=True),
                *action_buttons
            ]),
            padding=10,
            ink=True,
            on_click=lambda e, f=file: self.handle_file_click(f) if is_folder else self.preview_file(f),
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=8,
            margin=ft.margin.only(bottom=10),
        )
    
    def preview_file(self, file):
        if self.file_preview and file.get("mimeType") != "application/vnd.google-apps.folder":
            self.file_preview.show_preview(
                file_id=file.get("id"),
                file_name=file.get("name", "File")
            )
    
    def open_folder(self, folder, is_shared_drive=False):
        self.dash.show_folder_contents(folder["id"], folder.get("name", folder["id"]), is_shared_drive)
    
    def handle_file_click(self, file):
        if file.get("mimeType") == "application/vnd.google-apps.folder":
            self.dash.show_folder_contents(file["id"], file["name"])
        else:
            self.preview_file(file)
    
    def show_folder_menu(self, folder, is_shared_drive=False):
        self.open_folder(folder, is_shared_drive)
    
    def _rename_file_dialog(self, file):
        name_field = ft.TextField(value=file["name"], autofocus=True)

        def rename(e):
            new_name = name_field.value.strip()
            if new_name and new_name != file["name"]:
                self.dash.drive.rename_file(file["id"], new_name)
                self.dash.refresh_folder_contents()
            dialog_container.visible = False
            self.dash.page.update()

        def cancel(e):
            dialog_container.visible = False
            self.dash.page.update()

        dialog_container = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Rename", size=20, weight=ft.FontWeight.BOLD),
                    name_field,
                    ft.Row([
                        ft.TextButton("Cancel", on_click=cancel),
                        ft.ElevatedButton("Rename", on_click=rename)
                    ], alignment=ft.MainAxisAlignment.END),
                ], tight=True, spacing=15),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                width=400,
            ),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
        )

        self.dash.page.overlay.append(dialog_container)
        self.dash.page.update()
    
    def _delete_file_dialog(self, file):
        def delete(e):
            self.dash.drive.delete_file(file["id"])
            self.dash.refresh_folder_contents()
            dialog_container.visible = False
            self.dash.page.update()

        def cancel(e):
            dialog_container.visible = False
            self.dash.page.update()

        dialog_container = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Confirm Delete", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Delete '{file.get('name', '')}'?"),
                    ft.Row([
                        ft.TextButton("Cancel", on_click=cancel),
                        ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.Colors.RED)
                    ], alignment=ft.MainAxisAlignment.END),
                ], tight=True, spacing=15),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                width=400,
            ),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
        )

        self.dash.page.overlay.append(dialog_container)
        self.dash.page.update()


    
    def show_file_info(self, file):
        info = self.dash.drive.get_file_info(file["id"]) if isinstance(file, dict) and "id" in file else file
        if not info:
            return
        
        size_str = format_file_size(info.get('size')) if info.get('size') else "N/A"
        
        def close_dialog(e):
            dialog_container.visible = False
            self.dash.page.update()
        
        def on_preview(e):
            self.preview_file(info)
            dialog_container.visible = False
            self.dash.page.update()
        
        preview_button = (
            ft.ElevatedButton(
                "Preview",
                icon=ft.Icons.VISIBILITY,
                on_click=on_preview
            ) if self.file_preview else ft.Container()
        )
        
        browser_button = ft.ElevatedButton(
            "Open in Browser",
            icon=ft.Icons.OPEN_IN_NEW,
            on_click=lambda e: open_drive_file(info.get('id'))
        )
        
        dialog_container = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("File Information", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Name: {info.get('name', 'N/A')}"),
                    ft.Text(f"Type: {info.get('mimeType', 'N/A')}"),
                    ft.Text(f"Size: {size_str}"),
                    ft.Text(f"Modified: {info.get('modifiedTime', 'N/A')[:10]}"),
                    ft.Divider(),
                    ft.Row([preview_button, browser_button], spacing=10),
                    ft.Row([
                        ft.TextButton("Close", on_click=close_dialog)
                    ], alignment=ft.MainAxisAlignment.END),
                ], tight=True, spacing=10),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                width=400,
            ),
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
        )

        self.dash.page.overlay.append(dialog_container)
        self.dash.page.update()

    
    def create_new_folder_dialog(self):
        name_field = ft.TextField(label="Folder name", autofocus=True)
        loading_text = ft.Text("")

        def create(e):
            folder_name = name_field.value.strip()
            if not folder_name:
                return
            loading_text.value = "Creating folder..."
            self.dash.page.update()

            folder = self.dash.drive.create_folder(folder_name, parent_id=self.dash.current_folder_id)
            if folder:
                self.dash.page.overlay.pop()
                new_folder_item = self.create_folder_item({
                    'id': folder['id'],
                    'name': folder['name'],
                    'mimeType': 'application/vnd.google-apps.folder'
                }, 0)
                insert_position = 1
                if len(self.dash.folder_list.controls) > insert_position:
                    self.dash.folder_list.controls.insert(insert_position, new_folder_item)
                else:
                    self.dash.folder_list.controls.append(new_folder_item)

                self.dash.drive._invalidate_cache(self.dash.current_folder_id)
                self.dash.page.update()
            else:
                loading_text.value = "Failed to create folder."
                self.dash.page.update()

        dialog_container = ft.Container(
            content=ft.Column([
                ft.Text("Create New Folder"),
                name_field,
                loading_text,
                ft.Row([
                    ft.TextButton("Cancel", on_click=lambda e: (self.dash.page.overlay.pop(), self.dash.page.update())),
                    ft.ElevatedButton("Create", on_click=create),
                ], alignment=ft.MainAxisAlignment.END),
            ]),
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            width=350,
            height=200,
        )

        self.dash.page.overlay.append(dialog_container)
        self.dash.page.update()
    
    def select_file_to_upload(self):
        def on_result(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            for f in e.files:
                self.dash.drive.upload_file(f.path, parent_id=self.dash.current_folder_id)
            self.dash.refresh_folder_contents()

        file_picker = ft.FilePicker(on_result=on_result)
        self.dash.page.overlay.append(file_picker)
        self.dash.page.update()
        file_picker.pick_files()