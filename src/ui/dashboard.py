import flet as ft
from services.drive_service import DriveService
from ui.custom_control.custom_controls import ButtonWithMenu
from ui.custom_control.gmail_profile_menu import GmailProfileMenu
from ui.custom_control.multi_account_manager import MultiAccountManager
from ui.todo_view import TodoView
from ui.dashboard_modules.file_manager import FileManager
from ui.dashboard_modules.folder_navigator import FolderNavigator
from ui.dashboard_modules.paste_links_manager import PasteLinksManager


class Dashboard:
    def __init__(self, page, auth_service, on_logout, on_add_account=None, on_switch_account=None):
        self.page = page
        self.auth = auth_service
        self.on_logout = on_logout
        self.on_add_account_callback = on_add_account
        self.on_switch_account_callback = on_switch_account
        self.drive = DriveService(auth_service.get_service())

        self.current_folder_id = "root"
        self.current_folder_name = "My Drive"
        self.folder_stack = []
        self.current_view = "your_folders"

        self.account_manager = MultiAccountManager()

        user_info = self.auth.get_user_info()
        self.user_email = user_info.get("emailAddress", "User") if user_info else "User"
        
        if user_info and not user_info.get("name") and not user_info.get("displayName"):
            user_info["name"] = self.user_email.split("@")[0]
        
        self.user_info = user_info if user_info else {
            "name": "User",
            "emailAddress": self.user_email,
            "photoLink": None
        }

        self.file_manager = FileManager(self)
        self.folder_navigator = FolderNavigator(self)
        self.paste_links_manager = PasteLinksManager(self)

        self.search_field = ft.TextField(
            hint_text="Search",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.folder_navigator.handle_search,
            border_color=ft.Colors.GREY_400,
            filled=True,
            expand=True,
        )

        self.menu_open = False

        self.paste_link_field = ft.TextField(
            hint_text="Paste Google Drive folder or file link and press Enter",
            on_submit=self.paste_links_manager.handle_paste_link,
            expand=True,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700,
        )

        self.folder_list = ft.Column(spacing=0, scroll=ft.ScrollMode.ALWAYS, expand=True)

        self.page.on_resize = self.on_resize

        self.page.title = "Drive Manager"
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

        self.folder_navigator.load_your_folders()

    def toggle_menu(self, e):
        self.menu_open = not self.menu_open
        self.sidebar_container.visible = self.menu_open or self.page.width > 700
        self.page.update()

    def on_resize(self, e):
        if self.page.width >= 900:
            self.sidebar_container.visible = True
            self.menu_open = False
        else:
            self.sidebar_container.visible = self.menu_open
        self.page.update()

    def show_folder_contents(self, folder_id, folder_name=None, is_shared_drive=False, push_to_stack=True):
        self.folder_navigator.show_folder_contents(folder_id, folder_name, is_shared_drive, push_to_stack)

    def refresh_folder_contents(self):
        self.folder_navigator.refresh_folder_contents()

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def show_todo_view(self, e):
        self.current_view = "todo"
        self.folder_list.controls.clear()
        todo_view = TodoView(self.page, on_back=self.folder_navigator.load_your_folders, drive_service=self.drive)
        self.folder_list.controls.append(todo_view.get_view())
        self.page.update()

    def handle_logout(self, e):
        self.auth.logout()
        self.on_logout()

    def handle_add_account(self, e):
        if self.on_add_account_callback:
            self.on_add_account_callback()
        else:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Redirecting to add another account..."),
            )
            self.page.snack_bar.open = True
            self.page.update()

    def handle_switch_account(self, email):
        if self.on_switch_account_callback:
            self.on_switch_account_callback(email)
        else:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Switching to {email}..."),
            )
            self.page.snack_bar.open = True
            self.page.update()

    def handle_action(self, selected_item):
        if selected_item == "Create Folder":
            self.file_manager.create_new_folder_dialog()
        elif selected_item == "Upload File":
            self.file_manager.select_file_to_upload()
        self.page.update()

    def get_view(self):
        self.sidebar_container = ft.Container(
            width=170,
            bgcolor=ft.Colors.GREY_100,
            padding=20,
            visible=(self.page.width >= 900) or self.menu_open,
            content=ft.Column([
                ButtonWithMenu(
                    text="+ NEW",
                    menu_items=["Create Folder", "Upload File"],
                    on_menu_select=self.handle_action,
                    page=self.page
                ),
                ft.ElevatedButton("TO-DO", on_click=self.show_todo_view),
            ], spacing=15)
        )

        saved_accounts = self.account_manager.get_all_accounts()
        
        profile_menu_instance = GmailProfileMenu(
            page=self.page,
            user_info=self.user_info,
            on_logout=self.handle_logout,
            on_add_account=self.handle_add_account,
            on_switch_account=self.handle_switch_account,
            saved_accounts=saved_accounts,
            account_manager=self.account_manager
        )
        profile_menu = profile_menu_instance.build()

        top_bar = ft.Container(
            padding=20,
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.MENU,
                    on_click=self.toggle_menu,
                    visible=True
                ),
                self.search_field,
                profile_menu,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        tabs = ft.Container(
            padding=10,
            content=ft.Row([
                ft.ElevatedButton(
                    "YOUR FOLDERS",
                    on_click=lambda e: (self.folder_navigator.reset_to_root()),
                ),
                ft.ElevatedButton(
                    "PASTE LINKS",
                    on_click=lambda e: (self.paste_links_manager.load_paste_links_view()),
                ),
                ft.ElevatedButton(
                    "SHARED DRIVES",
                    on_click=lambda e: (self.folder_navigator.load_shared_drives()),
                ),
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        )

        main_content = ft.Column([
            top_bar,
            tabs,
            ft.Container(expand=True, content=self.folder_list),
        ], expand=True)

        return ft.Row([
            self.sidebar_container,
            ft.VerticalDivider(width=1),
            main_content,
        ], expand=True)