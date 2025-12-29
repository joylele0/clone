import flet as ft
from utils.common import show_snackbar


class GmailProfileMenu:
    def __init__(self, page, user_info, on_logout, on_add_account=None, on_switch_account=None, saved_accounts=None, account_manager=None):
        self.page = page
        self.user_info = user_info
        self.on_logout = on_logout
        self.on_add_account = on_add_account
        self.on_switch_account = on_switch_account
        self.saved_accounts = saved_accounts or []
        self.account_manager = account_manager
        self.menu_open = False
        
        self.user_name = (
            user_info.get("displayName") or 
            user_info.get("name") or 
            user_info.get("emailAddress", "user@example.com").split("@")[0]
        )
        self.user_email = user_info.get("emailAddress", "user@example.com")
        self.profile_pic_url = user_info.get("photoLink", None) or user_info.get("picture", None)
        
        self.initials = self._get_initials(self.user_name)
    
    def _get_initials(self, name):
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        elif len(parts) == 1:
            return parts[0][0].upper()
        return "U"
    
    def toggle_menu(self, e):
        self.menu_open = not self.menu_open
        if self.menu_open:
            self.show_menu()
        else:
            self.hide_menu()
    
    def hide_menu(self):
        self.menu_open = False
        if hasattr(self, 'overlay_container'):
            self.page.overlay.remove(self.overlay_container)
            self.page.update()
    
    def show_menu(self):
        menu_controls = [
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(
                        content=self._create_profile_avatar(size=80),
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        f"Hello, {self.user_name}",
                        size=16,
                        weight=ft.FontWeight.W_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        self.user_email,
                        size=14,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            ),
            
            ft.Divider(height=1, color=ft.Colors.GREY_300),
            
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                content=ft.Row([
                    self._create_profile_avatar(size=32),
                    ft.Column(
                        [
                            ft.Text(self.user_name, size=14, weight=ft.FontWeight.W_500),
                            ft.Text(self.user_email, size=12, color=ft.Colors.GREY_700),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.BLUE, size=20),
                ], spacing=12),
                bgcolor=ft.Colors.BLUE_50,
            ),
        ]
        
        if self.saved_accounts:
            for account_email in self.saved_accounts:
                if account_email != self.user_email:
                    account_data = self.account_manager.get_account(account_email) if self.account_manager else None
                    account_user_info = account_data.get("user_info") if account_data else {}
                    has_saved_creds = self.account_manager.has_saved_credentials(account_email) if self.account_manager else False
                    
                    account_name = (
                        account_user_info.get("displayName") or 
                        account_user_info.get("name") or 
                        account_email.split("@")[0]
                    )
                    account_pic_url = account_user_info.get("photoLink") or account_user_info.get("picture")
                    account_initials = self._get_initials(account_name)
                    
                    if account_pic_url:
                        avatar = ft.Container(
                            width=32,
                            height=32,
                            border_radius=16,
                            content=ft.Image(
                                src=account_pic_url,
                                width=32,
                                height=32,
                                fit=ft.ImageFit.COVER,
                                border_radius=16,
                            ),
                        )
                    else:
                        avatar = ft.Container(
                            width=32,
                            height=32,
                            border_radius=16,
                            bgcolor=ft.Colors.GREY_400,
                            content=ft.Text(
                                account_initials,
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                            alignment=ft.alignment.center,
                        )
                    
                    status_badge = ft.Icon(
                        ft.Icons.CHECK_CIRCLE if has_saved_creds else ft.Icons.LOGIN,
                        size=16,
                        color=ft.Colors.GREEN if has_saved_creds else ft.Colors.ORANGE,
                        tooltip="Saved credentials" if has_saved_creds else "Re-login required"
                    )
                    
                    account_row = ft.Row([
                        ft.Container(
                            content=ft.Row([
                                avatar,
                                ft.Column([
                                    ft.Text(account_name, size=14, weight=ft.FontWeight.W_500),
                                    ft.Text(account_email, size=12, color=ft.Colors.GREY_700),
                                ], spacing=0),
                                status_badge,
                            ], spacing=12),
                            expand=True,
                            on_click=lambda e, email=account_email: self.handle_switch_account(email),
                            ink=True,
                        ),
                        ft.Container(
                            content=ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_size=16,
                                tooltip="Remove account",
                                on_click=lambda e, email=account_email: self.show_remove_confirmation(email),
                            ),
                            width=40,
                        ),
                    ], spacing=0)
                    
                    menu_controls.append(
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=16, vertical=8),
                            content=account_row,
                        )
                    )
        
        menu_controls.extend([
            ft.Divider(height=1, color=ft.Colors.GREY_300),
            
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON_ADD, size=20),
                    ft.Text("Add another account", size=14),
                ], spacing=12),
                on_click=self.handle_add_account,
                ink=True,
            ),
            
            ft.Divider(height=1, color=ft.Colors.GREY_300),
            
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                content=ft.Row([
                    ft.Icon(ft.Icons.LOGOUT, size=20),
                    ft.Text("Log out", size=14),
                ], spacing=12),
                on_click=self.handle_logout,
                ink=True,
            ),
        ])
        
        menu_content = ft.Container(
            width=350,
            bgcolor=ft.Colors.WHITE,
            border_radius=16,
            padding=0,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.Colors.BLACK26,
            ),
            content=ft.Column(
                controls=menu_controls,
                spacing=0,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        
        self.overlay_container = ft.Stack(
            controls=[
                ft.Container(
                    expand=True,
                    on_click=lambda e: self.hide_menu(),
                ),
                ft.Container(
                    right=20,
                    top=70,
                    content=menu_content,
                ),
            ],
        )
        
        self.page.overlay.append(self.overlay_container)
        self.page.update()
    
    def handle_logout(self, e):
        self.hide_menu()
        if self.on_logout:
            self.on_logout(e)
    
    def handle_add_account(self, e):
        self.hide_menu()
        if self.on_add_account:
            self.on_add_account(e)
            
        else:
            show_snackbar(self.page, "Add account feature coming soon!", ft.Colors.BLUE)

    
    def handle_switch_account(self, email):
        self.hide_menu()
        if self.on_switch_account:
            self.on_switch_account(email)
    
    def show_remove_confirmation(self, email):
        def confirm_remove(e):
            try:
                if self.account_manager:
                    self.account_manager.remove_account(email)
                    try:
                        self.saved_accounts = self.account_manager.get_all_accounts()
                    except Exception:
                        self.saved_accounts = [a for a in self.saved_accounts if a != email]
            except Exception as ex:
                print(f"[ERROR] Failed to remove account {email}: {ex}")
            close_confirmation()
            self.hide_menu()
            self.show_menu()

        def cancel_remove(e):
            close_confirmation()

        def close_confirmation():
            if hasattr(self, 'confirmation_overlay'):
                self.page.overlay.remove(self.confirmation_overlay)
                self.page.update()

        # Create confirmation dialog
        confirmation_dialog = ft.Container(
            width=400,
            bgcolor=ft.Colors.WHITE,
            border_radius=16,
            padding=24,
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=15,
                color=ft.Colors.BLACK38,
            ),
            content=ft.Column([
                ft.Text(
                    "Remove Account",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(height=16),
                ft.Text(
                    f"Are you sure you want to remove {email}?",
                    size=14,
                    color=ft.Colors.GREY_800,
                ),
                ft.Container(height=24),
                ft.Row([
                    ft.TextButton(
                        "Cancel",
                        on_click=cancel_remove,
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "Remove",
                        on_click=confirm_remove,
                        bgcolor=ft.Colors.RED_400,
                        color=ft.Colors.WHITE,
                    ),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=0, tight=True),
        )

        self.confirmation_overlay = ft.Stack(
            controls=[
                ft.Container(
                    expand=True,
                    bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                    on_click=lambda e: close_confirmation(),
                ),
                ft.Container(
                    content=confirmation_dialog,
                    alignment=ft.alignment.center,
                ),
            ],
        )

        self.page.overlay.append(self.confirmation_overlay)
        self.page.update()
            
    def _create_profile_avatar(self, size=36):
        if self.profile_pic_url:
            return ft.Container(
                width=size,
                height=size,
                border_radius=size // 2,
                content=ft.Image(
                    src=self.profile_pic_url,
                    width=size,
                    height=size,
                    fit=ft.ImageFit.COVER,
                    border_radius=size // 2,
                ),
            )
        else:
            return ft.Container(
                width=size,
                height=size,
                border_radius=size // 2,
                bgcolor=ft.Colors.BLUE_400,
                content=ft.Text(
                    self.initials,
                    size=size // 2.5,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                alignment=ft.alignment.center,
            )
    
    def build(self):
        profile_button = ft.IconButton(
            content=self._create_profile_avatar(size=36),
            on_click=self.toggle_menu,
            tooltip=f"{self.user_name}\n{self.user_email}",
        )
        
        return profile_button