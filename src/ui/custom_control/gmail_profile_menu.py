import flet as ft


class GmailProfileMenu:
    def __init__(self, page, user_info, on_logout, on_add_account=None, on_switch_account=None, saved_accounts=None):
        self.page = page
        self.user_info = user_info
        self.on_logout = on_logout
        self.on_add_account = on_add_account
        self.on_switch_account = on_switch_account
        self.saved_accounts = saved_accounts or []
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
                    account_initials = self._get_initials(account_email.split("@")[0])
                    menu_controls.append(
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=16, vertical=8),
                            content=ft.Row([
                                ft.Container(
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
                                ),
                                ft.Text(account_email, size=14, expand=True),
                            ], spacing=12),
                            on_click=lambda e, email=account_email: self.handle_switch_account(email),
                            ink=True,
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
            width=320,
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
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Add account feature coming soon!"),
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def handle_switch_account(self, email):
        self.hide_menu()
        if self.on_switch_account:
            self.on_switch_account(email)
    
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