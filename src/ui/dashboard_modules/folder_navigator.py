import flet as ft


class FolderNavigator:
    def __init__(self, dashboard):
        self.dash = dashboard
    
    def load_your_folders(self):
        self.dash.current_view = "your_folders"
        self.dash.current_folder_id = "root"
        self.dash.current_folder_name = "My Drive"
        self.dash.folder_list.controls.clear()

        try:
            result = self.dash.drive.list_files("root", page_size=100)
            if result is None:
                self.dash.folder_list.controls.append(ft.Text("Failed to load folders."))
            else:
                files = result.get("files", [])
                
                if not files:
                    self.dash.folder_list.controls.append(ft.Text("No items found"))
                else:
                    
                    folders = [f for f in files if f.get("mimeType") == "application/vnd.google-apps.folder"]
                    for folder in folders:
                        sub_result = self.dash.drive.list_files(folder["id"], page_size=100)
                        sub_count = 0 if sub_result is None else len([
                            f for f in sub_result.get("files", [])
                            if f.get("mimeType") == "application/vnd.google-apps.folder"
                        ])
                        self.dash.folder_list.controls.append(self.dash.file_manager.create_folder_item(folder, sub_count))
                    
                    regular_files = [f for f in files if f.get("mimeType") != "application/vnd.google-apps.folder"]
                    for file in regular_files:
                        self.dash.folder_list.controls.append(self.dash.file_manager.create_file_item(file))
        except:
            self.dash.folder_list.controls.append(ft.Text("Error loading your folders", color=ft.Colors.RED))

        self.dash.page.update()
    
    def load_shared_drives(self):
        self.dash.current_view = "shared_drives"
        self.dash.folder_stack = []
        self.dash.folder_list.controls.clear()

        try:
            results = self.dash.drive.service.drives().list(pageSize=100, fields="drives(id, name)").execute()
            shared_drives = results.get("drives", [])
            if not shared_drives:
                self.dash.folder_list.controls.append(ft.Text("No shared drives found"))
            else:
                for d in shared_drives:
                    fake_folder = {"id": d["id"], "name": d["name"], "mimeType": "application/vnd.google-apps.folder"}
                    self.dash.folder_list.controls.append(self.dash.file_manager.create_folder_item(fake_folder, 0, is_shared_drive=True))
        except:
            self.dash.folder_list.controls.append(ft.Text("Error loading shared drives", color=ft.Colors.RED))

        self.dash.page.update()
    
    def show_folder_contents(self, folder_id, folder_name=None, is_shared_drive=False, push_to_stack=True):
        display_name = folder_name or folder_id

        if push_to_stack and self.dash.current_folder_id != folder_id:
            self.dash.folder_stack.append((self.dash.current_folder_id, self.dash.current_folder_name))

        self.dash.current_folder_id = folder_id
        self.dash.current_folder_name = display_name

        self.dash.folder_list.controls.clear()

        back_controls = []

        if self.dash.folder_stack:
            back_controls.append(
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: self.go_back())
            )

        back_btn = ft.Row(
            [
                *back_controls,
                ft.Text(display_name, size=18, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("Refresh", icon=ft.Icons.REFRESH, on_click=lambda e: self.refresh_folder_contents()),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.dash.folder_list.controls.append(back_btn)

        loading_indicator = ft.Row([
            ft.ProgressRing(width=20, height=20),
            ft.Text("Loading folder contents...", size=14)
        ])
        self.dash.folder_list.controls.append(loading_indicator)
        self.dash.page.update()

        try:
            result = self.dash.drive.list_files(folder_id, page_size=200, use_cache=False)
            self.dash.folder_list.controls.remove(loading_indicator)

            if result is None:
                self.dash.folder_list.controls.append(ft.Text("Network error", color=ft.Colors.ORANGE))
            else:
                files = result.get("files", [])
                if not files:
                    self.dash.folder_list.controls.append(ft.Text("Folder is empty"))
                else:
                    for f in files:
                        self.dash.folder_list.controls.append(self.dash.file_manager.create_file_item(f))
        except:
            self.dash.folder_list.controls.append(ft.Text("Error loading folder contents", color=ft.Colors.RED))

        self.dash.page.update()
    
    def refresh_folder_contents(self):
        self.dash.drive._invalidate_cache(self.dash.current_folder_id)
        self.show_folder_contents(self.dash.current_folder_id, self.dash.current_folder_name, push_to_stack=False)
    
    def go_back(self):
        if not self.dash.folder_stack:
            return
        fid, fname = self.dash.folder_stack.pop()
        self.dash.current_folder_id = fid
        self.dash.current_folder_name = fname

        if fid == "root":
            if self.dash.current_view == "your_folders":
                self.load_your_folders()
            elif self.dash.current_view == "paste_links":
                self.dash.paste_links_manager.load_paste_links_view()
            elif self.dash.current_view == "shared_drives":
                self.load_shared_drives()
        else:
            self.show_folder_contents(fid, fname, push_to_stack=False)
    
    def reset_to_root(self):
        self.dash.folder_stack = []
        self.dash.current_folder_id = "root"
        self.dash.current_folder_name = "My Drive"
        self.load_your_folders()
    
    def handle_search(self, e):
        query = self.dash.search_field.value.strip()
        if not query:
            self.load_your_folders()
            return
        results = self.dash.drive.search_files(query)
        self.dash.folder_list.controls.clear()
        if not results:
            self.dash.folder_list.controls.append(ft.Text("No results"))
        else:
            for r in results:
                if r.get("mimeType") == "application/vnd.google-apps.folder":
                    self.dash.folder_list.controls.append(self.dash.file_manager.create_folder_item(r, 0))
                else:
                    self.dash.folder_list.controls.append(self.dash.file_manager.create_file_item(r))
        self.dash.page.update()