import flet as ft


class FileManager:
    def __init__(self, dashboard):
        self.dash = dashboard
        
        try:
            from services.file_preview_service import FilePreviewService
            self.file_preview = FilePreviewService(dashboard.page, dashboard.drive)
        except ImportError:
            self.file_preview = None
    
    def create_folder_item(self, folder, subfolder_count, is_shared_drive=False):
        folder_name = folder.get("name", "Untitled")
        display_name = folder_name if len(folder_name) < 40 else folder_name[:37] + "..."

        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.FOLDER, size=24),
                ft.Column([
                    ft.Text(display_name, size=14),
                    ft.Text(f"{subfolder_count} folders", size=12, color=ft.Colors.GREY_600),
                ], expand=True),
                ft.IconButton(icon=ft.Icons.MORE_VERT, on_click=lambda e, f=folder: self.show_folder_menu(f, is_shared_drive)),
            ]),
            padding=10,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
            on_click=lambda e, f=folder: self.open_folder(f, is_shared_drive),
        )
    
    def create_file_item(self, file):
        is_folder = file.get("mimeType") == "application/vnd.google-apps.folder"
        icon = ft.Icons.FOLDER if is_folder else ft.Icons.INSERT_DRIVE_FILE
        size_str = "Folder" if is_folder else self.format_size(file.get("size"))

        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=24),
                ft.Column([
                    ft.Text(file.get("name", "Untitled"), size=14),
                    ft.Text(size_str, size=12, color=ft.Colors.GREY_600),
                ], expand=True),
                ft.IconButton(
                    icon=ft.Icons.VISIBILITY,
                    tooltip="Preview",
                    on_click=lambda e, f=file: self.preview_file(f)
                ) if not is_folder and self.file_preview else ft.Container(),
                ft.IconButton(icon=ft.Icons.MORE_VERT, on_click=lambda e, f=file: self.show_file_menu(f)),
            ]),
            padding=10,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
            on_click=lambda e, f=file: self.handle_file_click(f) if is_folder else self.preview_file(f),
        )
    
    def preview_file(self, file):
        if self.file_preview and file.get("mimeType") != "application/vnd.google-apps.folder":
            self.file_preview.show_preview(
                file_id=file.get("id"),
                file_name=file.get("name", "File")
            )
    
    def format_size(self, size):
        try:
            s = int(size)
            if s < 1024:
                return f"{s} B"
            if s < 1024 * 1024:
                return f"{s / 1024:.1f} KB"
            if s < 1024 * 1024 * 1024:
                return f"{s / (1024 * 1024):.1f} MB"
            return f"{s / (1024 * 1024 * 1024):.1f} GB"
        except:
            return "Unknown size"
    
    def open_folder(self, folder, is_shared_drive=False):
        self.dash.show_folder_contents(folder["id"], folder.get("name", folder["id"]), is_shared_drive)
    
    def handle_file_click(self, file):
        if file.get("mimeType") == "application/vnd.google-apps.folder":
            self.dash.show_folder_contents(file["id"], file["name"])
        else:
            self.preview_file(file)
    
    def show_folder_menu(self, folder, is_shared_drive=False):
        self.open_folder(folder, is_shared_drive)
    
    def show_file_menu(self, file):
        def on_preview(e):
            self.preview_file(file)
            popup.open = False
            self.dash.page.update()

        def on_rename(e):
            self.rename_file_dialog(file)
            popup.open = False
            self.dash.page.update()

        def on_delete(e):
            self.delete_file_dialog(file)
            popup.open = False
            self.dash.page.update()

        def on_info(e):
            self.show_file_info(file)
            popup.open = False
            self.dash.page.update()

        menu_items = [
            ft.PopupMenuItem(text="Preview", on_click=on_preview) if self.file_preview else None,
            ft.PopupMenuItem(text="Info", on_click=on_info),
            ft.PopupMenuItem(text="Rename", on_click=on_rename),
            ft.PopupMenuItem(text="Delete", on_click=on_delete),
        ]
        
        menu_items = [item for item in menu_items if item is not None]

        popup = ft.PopupMenuButton(items=menu_items)
        self.dash.page.add(popup)
        popup.open = True
        self.dash.page.update()
    
    def rename_file_dialog(self, file):
        name_field = ft.TextField(value=file["name"], autofocus=True)

        def rename(e):
            new_name = name_field.value.strip()
            if new_name and new_name != file["name"]:
                self.dash.drive.rename_file(file["id"], new_name)
                self.dash.refresh_folder_contents()
            dialog.open = False
            self.dash.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Rename"),
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.dash.close_dialog(dialog)),
                ft.ElevatedButton("Rename", on_click=rename)
            ],
        )

        self.dash.page.dialog = dialog
        dialog.open = True
        self.dash.page.update()
    
    def delete_file_dialog(self, file):
        def delete(e):
            self.dash.drive.delete_file(file["id"])
            self.dash.refresh_folder_contents()
            dialog.open = False
            self.dash.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Delete '{file.get('name', '')}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.dash.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.Colors.RED)
            ],
        )

        self.dash.page.dialog = dialog
        dialog.open = True
        self.dash.page.update()
    
    def show_file_info(self, file):
        info = self.dash.drive.get_file_info(file["id"]) if isinstance(file, dict) and "id" in file else file
        if not info:
            return
        
        size_str = self.format_size(info.get('size')) if info.get('size') else "N/A"
        
        preview_button = (
            ft.ElevatedButton(
                "Preview",
                icon=ft.Icons.VISIBILITY,
                on_click=lambda e: (self.preview_file(info), setattr(dialog, 'open', False), self.dash.page.update())
            ) if self.file_preview else ft.Container()
        )
        
        browser_button = ft.ElevatedButton(
            "Open in Browser",
            icon=ft.Icons.OPEN_IN_NEW,
            on_click=lambda e: self._open_in_browser(info.get('id'))
        )
        
        content = ft.Column([
            ft.Text(f"Name: {info.get('name', 'N/A')}"),
            ft.Text(f"Type: {info.get('mimeType', 'N/A')}"),
            ft.Text(f"Size: {size_str}"),
            ft.Text(f"Modified: {info.get('modifiedTime', 'N/A')[:10]}"),
            ft.Divider(),
            ft.Row([preview_button, browser_button], spacing=10)
        ], spacing=5)

        dialog = ft.AlertDialog(
            title=ft.Text("File Information"), 
            content=content, 
            actions=[ft.TextButton("Close", on_click=lambda e: self.dash.close_dialog(dialog))]
        )

        self.dash.page.dialog = dialog
        dialog.open = True
        self.dash.page.update()
    
    def _open_in_browser(self, file_id):
        import webbrowser
        webbrowser.open(f"https://drive.google.com/file/d/{file_id}/view")
    
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
    
    def show_new_menu(self, e):
        popup = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(text="New Folder", on_click=lambda e: self.create_new_folder_dialog()),
                ft.PopupMenuItem(text="Upload File", on_click=lambda e: self.select_file_to_upload()),
            ]
        )
        self.dash.page.add(popup)
        popup.open = True
        self.dash.page.update()