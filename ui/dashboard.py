import flet as ft
from services.drive_service import DriveService
import re
import json
import os
from ui.custom_control.custom_controls import ButtonWithMenu

FAVORITES_FILE = "favorites.json"
SAVED_LINKS_FILE = "saved_links.json"


class Dashboard:
    def __init__(self, page, auth_service, on_logout):
        self.page = page
        self.auth = auth_service
        self.on_logout = on_logout
        self.drive = DriveService(auth_service.get_service())

        self.current_folder_id = "root"
        self.current_folder_name = "My Drive"
        self.folder_stack = []
        self.selected_files = set()
        self.current_view = "your_folders"

        user_info = self.auth.get_user_info()
        self.user_email = user_info.get("emailAddress", "User") if user_info else "User"

        self.search_field = ft.TextField(
            hint_text="Search",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.handle_search,
            border_color=ft.Colors.GREY_400,
            filled=True,
            expand=True,
        )

        self.paste_link_field = ft.TextField(
            hint_text="Paste Google Drive folder or file link and press Enter",
            on_submit=self.handle_paste_link,  
            expand=True,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700,
        )

        print("DEBUG: Dashboard initialized")  

        self.favorites = self.load_favorites()
        self.folder_list = ft.Column(spacing=0, scroll=ft.ScrollMode.ALWAYS, expand=True)
        self.main_view_container = None

        self.page.title = "Drive Manager"
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

        self.load_your_folders()

    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_favorites(self):
        try:
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.favorites, f, indent=2)
        except:
            pass

    def add_favorite(self, subject, folder_id, folder_name):
        self.favorites.setdefault(subject, [])
        if any(f["id"] == folder_id for f in self.favorites[subject]):
            return False
        self.favorites[subject].append({"id": folder_id, "name": folder_name})
        self.save_favorites()
        return True

    def remove_favorite(self, subject, folder_id):
        if subject not in self.favorites:
            return False
        self.favorites[subject] = [f for f in self.favorites[subject] if f["id"] != folder_id]
        if not self.favorites[subject]:
            del self.favorites[subject]
        self.save_favorites()
        return True

    
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
       
        if self.current_view == "paste_links":
            self.load_paste_links_view()

    def open_saved_link(self, item):
        if item.get("mimeType") == "application/vnd.google-apps.folder":
            self.show_folder_contents(item["id"], item.get("name", item["id"]))
        else:
            info = self.drive.get_file_info(item["id"])
            if info:
                self.show_file_info(info)
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Failed to open saved link"), open=True)
                self.page.update()

   

    def load_your_folders(self):
        self.current_view = "your_folders"
        self.current_folder_id = "root"
        self.current_folder_name = "My Drive"
        self.folder_list.controls.clear()

        try:
            result = self.drive.list_files("root", page_size=100)
            if result is None:
                self.folder_list.controls.append(ft.Text("Failed to load folders."))
            else:
                files = result.get("files", [])
                folders = [f for f in files if f.get("mimeType") == "application/vnd.google-apps.folder"]
                if not folders:
                    self.folder_list.controls.append(ft.Text("No folders found"))
                else:
                    for folder in folders:
                        sub_result = self.drive.list_files(folder["id"], page_size=100)
                        sub_count = 0 if sub_result is None else len([
                            f for f in sub_result.get("files", [])
                            if f.get("mimeType") == "application/vnd.google-apps.folder"
                        ])
                        self.folder_list.controls.append(self.create_folder_item(folder, sub_count))
        except:
            self.folder_list.controls.append(ft.Text("Error loading your folders", color=ft.Colors.RED))

        self.page.update()

    def load_shared_drives(self):
        self.current_view = "shared_drives"
        self.folder_stack = []
        self.folder_list.controls.clear()

        try:
            results = self.drive.service.drives().list(pageSize=100, fields="drives(id, name)").execute()
            shared_drives = results.get("drives", [])
            if not shared_drives:
                self.folder_list.controls.append(ft.Text("No shared drives found"))
            else:
                for d in shared_drives:
                    fake_folder = {"id": d["id"], "name": d["name"], "mimeType": "application/vnd.google-apps.folder"}
                    self.folder_list.controls.append(self.create_folder_item(fake_folder, 0, is_shared_drive=True))
        except:
            self.folder_list.controls.append(ft.Text("Error loading shared drives", color=ft.Colors.RED))

        self.page.update()

    def show_folder_contents(self, folder_id, folder_name=None, is_shared_drive=False, push_to_stack=True):
        self.current_view = "folder_detail"
        display_name = folder_name or folder_id

        if push_to_stack:
            self.folder_stack.append((self.current_folder_id, self.current_folder_name))

        self.current_folder_id = folder_id
        self.current_folder_name = display_name

        self.folder_list.controls.clear()
        back_controls = []

        if self.folder_stack or folder_id != "root":
            back_controls.append(ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: self.go_back()))

        back_btn = ft.Row(
            [
                *back_controls,
                ft.Text(display_name, size=18, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton("Save to favorites", on_click=lambda e: self.open_save_favorite_dialog()),
                    ft.ElevatedButton("Refresh", icon=ft.Icons.REFRESH, on_click=lambda e: self.refresh_folder_contents()),
                ]),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.folder_list.controls.append(back_btn)

        loading_indicator = ft.Row([
            ft.ProgressRing(width=20, height=20),
            ft.Text("Loading folder contents...", size=14)
        ])

        self.folder_list.controls.append(loading_indicator)
        self.page.update()

        try:
            result = self.drive.list_files(folder_id, page_size=200, use_cache=False)
            self.folder_list.controls.remove(loading_indicator)
            if result is None:
                self.folder_list.controls.append(ft.Text("Network error", color=ft.Colors.ORANGE))
            else:
                files = result.get("files", [])
                if not files:
                    self.folder_list.controls.append(ft.Text("Folder is empty"))
                else:
                    for f in files:
                        self.folder_list.controls.append(self.create_file_item(f))
        except:
            self.folder_list.controls.append(ft.Text("Error loading folder contents", color=ft.Colors.RED))

        self.page.update()

    def refresh_folder_contents(self):
        self.drive._invalidate_cache(self.current_folder_id)
        self.show_folder_contents(self.current_folder_id, self.current_folder_name, push_to_stack=False)

    def go_back(self):
        if not self.folder_stack:
            return
        fid, fname = self.folder_stack.pop()
        self.current_folder_id = fid
        self.current_folder_name = fname

        if fid == "root":
            self.load_your_folders()
        else:
            self.show_folder_contents(fid, fname, push_to_stack=False)

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
                ft.IconButton(icon=ft.Icons.MORE_VERT, on_click=lambda e, f=file: self.show_file_menu(f)),
            ]),
            padding=10,
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
            on_click=lambda e, f=file: self.handle_file_click(f) if is_folder else None,
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

    def reset_to_root(self):
        self.folder_stack = []
        self.current_folder_id = "root"
        self.current_folder_name = "My Drive"
        self.load_your_folders()

    def open_folder(self, folder, is_shared_drive=False):
        self.show_folder_contents(folder["id"], folder.get("name", folder["id"]), is_shared_drive)

    def handle_file_click(self, file):
        if file.get("mimeType") == "application/vnd.google-apps.folder":
            self.show_folder_contents(file["id"], file["name"])
        else:
            self.show_file_info(file)

    def show_folder_menu(self, folder, is_shared_drive=False):
        self.open_folder(folder, is_shared_drive)

    def show_file_menu(self, file):
        def on_rename(e):
            self.rename_file_dialog(file)
            popup.open = False
            self.page.update()

        def on_delete(e):
            self.delete_file_dialog(file)
            popup.open = False
            self.page.update()

        def on_info(e):
            self.show_file_info(file)
            popup.open = False
            self.page.update()

        popup = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(text="Info", on_click=on_info),
                ft.PopupMenuItem(text="Rename", on_click=on_rename),
                ft.PopupMenuItem(text="Delete", on_click=on_delete),
            ]
        )
        self.page.add(popup)
        popup.open = True
        self.page.update()

    def show_new_menu(self, e):
        popup = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(text="New Folder", on_click=lambda e: self.create_new_folder_dialog()),
                ft.PopupMenuItem(text="Upload File", on_click=lambda e: self.select_file_to_upload()),
            ]
        )
        self.page.add(popup)
        popup.open = True
        self.page.update()

    def create_new_folder_dialog(self):
        name_field = ft.TextField(label="Folder name", autofocus=True)
        loading_text = ft.Text("")

        def create(e):
            folder_name = name_field.value.strip()
            if not folder_name:
                return
            loading_text.value = "Creating folder..."
            self.page.update()

            folder = self.drive.create_folder(folder_name, parent_id=self.current_folder_id)
            if folder:
                self.page.overlay.pop()
                new_folder_item = self.create_folder_item({
                    'id': folder['id'],
                    'name': folder['name'],
                    'mimeType': 'application/vnd.google-apps.folder'
                }, 0)
                insert_position = 1
                if len(self.folder_list.controls) > insert_position:
                    self.folder_list.controls.insert(insert_position, new_folder_item)
                else:
                    self.folder_list.controls.append(new_folder_item)

                self.drive._invalidate_cache(self.current_folder_id)
                self.page.update()
            else:
                loading_text.value = "Failed to create folder."
                self.page.update()

        dialog_container = ft.Container(
            content=ft.Column([
                ft.Text("Create New Folder"),
                name_field,
                loading_text,
                ft.Row([
                    ft.TextButton("Cancel", on_click=lambda e: (self.page.overlay.pop(), self.page.update())),
                    ft.ElevatedButton("Create", on_click=create),
                ], alignment=ft.MainAxisAlignment.END),
            ]),
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            width=350,
            height=200,
        )

        self.page.overlay.append(dialog_container)
        self.page.update()

    def select_file_to_upload(self):
        def on_result(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            for f in e.files:
                self.drive.upload_file(f.path, parent_id=self.current_folder_id)
            self.refresh_folder_contents()

        file_picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files()

    def rename_file_dialog(self, file):
        name_field = ft.TextField(value=file["name"], autofocus=True)

        def rename(e):
            new_name = name_field.value.strip()
            if new_name and new_name != file["name"]:
                self.drive.rename_file(file["id"], new_name)
                self.refresh_folder_contents()
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Rename"),
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Rename", on_click=rename)
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def delete_file_dialog(self, file):
        def delete(e):
            self.drive.delete_file(file["id"])
            self.refresh_folder_contents()
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Delete '{file.get('name', '')}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.Colors.RED)
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def show_file_info(self, file):
        info = self.drive.get_file_info(file["id"]) if isinstance(file, dict) and "id" in file else file
        if not info:
            return
        content = ft.Column([
            ft.Text(f"Name: {info.get('name', 'N/A')}")], spacing=5)

        dialog = ft.AlertDialog(title=ft.Text("File Information"), content=content, actions=[ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))])

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def load_paste_links_view(self):
       
        self.current_view = "paste_links"
        self.folder_list.controls.clear()

  
        header = ft.Container(
            content=ft.Text("Paste Drive Links", size=20, weight=ft.FontWeight.BOLD),
            padding=10
        )

        paste_section = ft.Container(
            content=ft.Column([
                ft.Text("Paste a Google Drive folder or file link:" , size=14),
                self.paste_link_field,
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

        self.folder_list.controls.extend([
            header,
            paste_section,
            saved_links_header,
            saved_links_list
        ])

        self.page.update()

    def handle_search(self, e):
        query = self.search_field.value.strip()
        if not query:
            self.load_your_folders()
            return
        results = self.drive.search_files(query)
        self.folder_list.controls.clear()
        if not results:
            self.folder_list.controls.append(ft.Text("No results"))
        else:
            for r in results:
                if r.get("mimeType") == "application/vnd.google-apps.folder":
                    self.folder_list.controls.append(self.create_folder_item(r, 0))
                else:
                    self.folder_list.controls.append(self.create_file_item(r))
        self.page.update()

    def paste_link_dialog(self, e):
        link_field = ft.TextField(hint_text="Paste Google Drive folder link", autofocus=True)

        def open_folder(e):
            link = link_field.value.strip()

            folder_id, info = self.drive.resolve_drive_link(link)

            if folder_id:
                folder_name = info.get("name", "Shared Folder") if info else "Shared Folder"
                self.show_folder_contents(folder_id, folder_name)
                dialog.open = False
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Invalid or inaccessible Drive link"))
                self.page.snack_bar.open = True

            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Open Shared Folder"),
            content=link_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Open", on_click=open_folder)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def handle_paste_link(self, e):
        link = e.control.value.strip()
        print(f"DEBUG: handle_paste_link called with: {link}")  # Debug

        if not link:
            print("DEBUG: Empty link")
            return
        
        loading_snack = ft.SnackBar(
            content=ft.Text("🔄 Loading Drive link..."),
            open=True
        )
        self.page.snack_bar = loading_snack
        self.page.update()

        try:
            file_id, info = self.drive.resolve_drive_link(link)

            print(f"DEBUG: file_id={file_id}, info={info}") 

            if not file_id or not info:
                error_snack = ft.SnackBar(
                    content=ft.Text("Invalid or inaccessible Drive link"),
                    bgcolor=ft.Colors.RED_400,
                    open=True
                )
                self.page.snack_bar = error_snack
                self.page.update()
                return

            mime_type = info.get("mimeType", "")
            name = info.get("name", "Shared Item")

            print(f"DEBUG: mime_type={mime_type}, name={name}")  


            try:
                saved_added = self.add_saved_link(file_id, info, link)
                if saved_added:
                    self.page.snack_bar = ft.SnackBar(ft.Text("Saved link"), open=True)
                else:
                    self.page.snack_bar = ft.SnackBar(ft.Text("Link already saved"), open=True)
            except Exception as ex:
                print(f"ERROR: Failed to save link: {ex}")

            if mime_type == "application/vnd.google-apps.folder":
                
                success_snack = ft.SnackBar(
                    content=ft.Text(f"✅ Opening folder: {name}"),
                    bgcolor=ft.Colors.GREEN_400,
                    open=True
                )
                self.page.snack_bar = success_snack
                self.page.update()
                self.show_folder_contents(file_id, name)
            else:

                info_snack = ft.SnackBar(
                    content=ft.Text(f"📄 File detected: {name}"),
                    bgcolor=ft.Colors.BLUE_400,
                    open=True
                )
                self.page.snack_bar = info_snack
                self.page.update()
                self.show_file_info(info)

            self.paste_link_field.value = ""

        except Exception as ex:
            print(f"ERROR: Exception in handle_paste_link: {ex}")
            error_snack = ft.SnackBar(
                content=ft.Text(f"❌ Error: {str(ex)}"),
                bgcolor=ft.Colors.RED_400,
                open=True
            )
            self.page.snack_bar = error_snack

        if self.current_view == "paste_links":
            self.load_paste_links_view()

        self.page.update()

    def quick_paste_dialog(self):
        print("DEBUG: quick_paste_dialog called")  

        link_field = ft.TextField(
            hint_text="Paste your Google Drive link here...",
            autofocus=True,
            multiline=False,
            width=500
        )

        status_text = ft.Text("", size=12)

        dialog = None

        def open_link(e):
            print(f"DEBUG: open_link called")  
            link = link_field.value.strip()
            print(f"DEBUG: Link value: {link}")  

            if not link:
                status_text.value = "Please paste a link"
                status_text.color = ft.Colors.ORANGE
                self.page.update()
                return

            status_text.value = "Loading..."
            status_text.color = ft.Colors.BLUE
            self.page.update()

            try:
                file_id, info = self.drive.resolve_drive_link(link)
                print(f"DEBUG: Got file_id={file_id}, info={info}")  

                if file_id and info:
                    mime_type = info.get("mimeType", "")
                    name = info.get("name", "Shared Item")

                    print(f"DEBUG: Opening {mime_type}: {name}")  


                    try:
                        self.add_saved_link(file_id, info, link)
                    except Exception as ex:
                        print(f"ERROR: Failed to save link from quick dialog: {ex}")

                    if dialog:
                        dialog.open = False
                        self.page.update()

                    if mime_type == "application/vnd.google-apps.folder":
                        self.show_folder_contents(file_id, name)
                    else:
                        self.show_file_info(info)
                else:
                    status_text.value = "Invalid or inaccessible link. Check permissions!"
                    status_text.color = ft.Colors.RED
                    self.page.update()
            except Exception as ex:
                print(f"ERROR: Exception in open_link: {ex}")  
                status_text.value = f"Error: {str(ex)}"
                status_text.color = ft.Colors.RED
                self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Paste Google Drive Link"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Paste any Google Drive folder or file link:"),
                    link_field,
                    status_text,
                    ft.Container(height=10),
                    ft.Text(
                        "Examples:\n"
                        "• https://drive.google.com/drive/folders/1ABC...\n"
                        "• https://drive.google.com/file/d/1XYZ.../view",
                        size=11,
                        color=ft.Colors.GREY_600
                    )
                ], spacing=10, tight=True),
                width=500
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton(
                    "Open Link",
                    on_click=open_link,
                    bgcolor=ft.Colors.BLUE_400,
                    color=ft.Colors.WHITE
                )
            ]
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        print("DEBUG: Quick paste dialog opened and displayed")  


    def open_save_favorite_dialog(self):
        subject_field = ft.TextField(label="Subject / Category", autofocus=True)

        def save(e):
            subject = subject_field.value.strip()
            if not subject:
                return
            added = self.add_favorite(subject, self.current_folder_id, self.current_folder_name)
            self.page.snack_bar = ft.SnackBar(ft.Text("Saved to favorites" if added else "Already in favorites"))
            self.page.snack_bar.open = True
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(title=ft.Text("Save folder to favorites"), content=subject_field, actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Save", on_click=save)])

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def build_favorites_ui(self):
        col = ft.Column(spacing=6)
        if not self.favorites:
            col.controls.append(ft.Text("No saved links", color=ft.Colors.GREY_600))
            return col
        for subject, folders in self.favorites.items():
            subject_row = ft.Row([
                ft.Text(subject),
                ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, s=subject: self.remove_subject_confirm(s)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            col.controls.append(subject_row)
            for f in folders:
                folder_row = ft.Row([
                    ft.Text(f.get("name", f.get("id")), expand=True),
                    ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, on_click=lambda e, fid=f["id"], nm=f.get("name", ""): self.show_folder_contents(fid, nm)),
                    ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, s=subject, fid=f["id"]: self.confirm_remove_favorite(s, fid)),
                ])
                col.controls.append(folder_row)
        return col

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
                ]),
                padding=8,
                ink=True,
                on_click=lambda e, it=item: self.open_saved_link(it),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=8
            )

            col.controls.append(row)

        return col

        for item in saved:
            row = ft.Row([
                ft.Text(item.get("name", item.get("id")), expand=True),

                ft.IconButton(
                    icon=ft.Icons.OPEN_IN_NEW,
                    tooltip="Open",
                    on_click=lambda e, it=item: self.open_saved_link(it)
                ),

                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    tooltip="Delete",
                    on_click=lambda e, it=item: self.delete_saved_link(it)
                )
            ])
            col.controls.append(row)

        return col

    def remove_subject_confirm(self, subject):
        def remove(e):
            if subject in self.favorites:
                del self.favorites[subject]
                self.save_favorites()
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(title=ft.Text("Remove subject"), content=ft.Text(f"Remove all favorites under '{subject}'?"), actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Remove", on_click=remove, bgcolor=ft.Colors.RED)])

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def confirm_remove_favorite(self, subject, folder_id):
        def remove(e):
            self.remove_favorite(subject, folder_id)
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(title=ft.Text("Remove favorite"), content=ft.Text("Remove this saved folder?"), actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Remove", on_click=remove, bgcolor=ft.Colors.RED)])

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def handle_logout(self, e):
        self.auth.logout()
        self.on_logout()

    def handle_action(self, selected_item):
        if selected_item == "Create Folder":
            self.create_new_folder_dialog()
        elif selected_item == "Upload File":
            self.select_file_to_upload()
        self.page.update()

    def get_view(self):
        sidebar = ft.Container(
            width=260,
            bgcolor=ft.Colors.GREY_100,
            padding=20,
            content=ft.Column([
                ButtonWithMenu(
                    text="+ NEW",
                    menu_items=["Create Folder", "Upload File"],
                    on_menu_select=self.handle_action,
                    page=self.page
                ),
                ft.Container(height=20),
                
                ft.ElevatedButton(
                    "📋 PASTE LINK",
                    icon=ft.Icons.CONTENT_PASTE,
                    on_click=lambda e: (print("DEBUG: Paste button clicked"), self.quick_paste_dialog()),
                    bgcolor=ft.Colors.BLUE_400,
                    color=ft.Colors.WHITE
                ),
                ft.ElevatedButton("SETTINGS", on_click=lambda e: None),
                ft.ElevatedButton("TO-DO", on_click=lambda e: DriveService.open_shared_link(self)),
                ft.ElevatedButton("ACCOUNT", on_click=self.handle_logout),
            ], spacing=15)
        )

        top_bar = ft.Container(
            padding=20,
            content=ft.Row([
                self.search_field,
                ft.IconButton(
                    icon=ft.Icons.ACCOUNT_CIRCLE,
                    icon_size=36,
                    tooltip=self.user_email
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        tabs = ft.Container(
            padding=10,
            content=ft.Row([
                ft.ElevatedButton(
                    "YOUR FOLDERS",
                    on_click=lambda e: (print("DEBUG: YOUR FOLDERS clicked"), self.reset_to_root()),
                ),
                ft.ElevatedButton(
                    "PASTE LINKS",
                    on_click=lambda e: (print("DEBUG: PASTE LINKS tab clicked"), self.load_paste_links_view()),
                ),
                ft.ElevatedButton(
                    "SHARED DRIVES",
                    on_click=lambda e: (print("DEBUG: SHARED DRIVES clicked"), self.load_shared_drives()),
                ),
            ], spacing=10)
        )

        main_content = ft.Column([
            top_bar,
            tabs,
            ft.Container(expand=True, content=self.folder_list),
        ], expand=True)

        return ft.Row([
            sidebar,
            ft.VerticalDivider(width=1),
            main_content,
        ], expand=True)
