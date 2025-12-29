import flet as ft
import traceback

from utils.common import show_snackbar


class LoginBase(ft.Column):
    def __init__(self, page, auth_service, on_success=None):
        super().__init__(
            controls=[],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=20
        )
        self.page = page
        self.auth = auth_service
        self.on_success = on_success
        self._build_ui()

    def _build_ui(self):
        platform_name = self._get_platform_name()
        
        self.controls.extend([
            ft.Container(height=50),
            ft.Icon(ft.Icons.CLOUD_CIRCLE, size=100, color=ft.Colors.BLUE_600),
            ft.Text("Learning Management System", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Text("Access your learning materials anywhere", size=16, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Text(f"Platform: {platform_name}", size=12, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
            ft.Container(height=20)
        ])
        
        self.status_text = ft.Text("Please log in to continue", color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER)
        self.controls.append(self.status_text)
        
        self.login_button = ft.ElevatedButton(
            text="Login with Google",
            icon=ft.Icons.LOGIN,
            on_click=self.handle_login,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_600,
                color=ft.Colors.WHITE,
                padding=ft.padding.symmetric(horizontal=30, vertical=15),
            ),
            height=50
        )
        
        self.controls.extend([
            ft.Container(height=10),
            self.login_button,
            ft.Container(height=20),
            ft.Text("Secure authentication via Google OAuth 2.0", size=12, color=ft.Colors.GREY_500, 
                   text_align=ft.TextAlign.CENTER, italic=True)
        ])

    def _get_platform_name(self):
        platform_map = {
            ft.PagePlatform.WINDOWS: "Windows",
            ft.PagePlatform.LINUX: "Linux",
            ft.PagePlatform.MACOS: "macOS",
            ft.PagePlatform.ANDROID: "Android",
            ft.PagePlatform.IOS: "iOS"
        }
        return platform_map.get(self.page.platform, str(self.page.platform))

    def update_status(self, message, color=ft.Colors.BLUE_600, disable_button=None):
        self.status_text.value = message
        self.status_text.color = color
        if disable_button is not None:
            self.login_button.disabled = disable_button
        self.page.update()

    def handle_success(self):
        self.update_status("Login successful!", ft.Colors.GREEN_600)
        if self.on_success:
            self.on_success()

    def handle_error(self, error, context="Login"):
        error_msg = str(error)
        self.update_status(f"{context} failed: {error_msg[:50]}...", ft.Colors.RED_600, False)
        print(f"{context} error: {error}\n{traceback.format_exc()}")

    def handle_login(self, e):
        raise NotImplementedError("Subclasses must implement handle_login")


class LoginView(LoginBase):
    def __init__(self, page, provider, auth_service, on_success=None):
        self.provider = provider
        super().__init__(page, auth_service, on_success)

    def handle_login(self, e):
        is_desktop = self.page.platform in [
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.LINUX,
            ft.PagePlatform.MACOS
        ]

        if is_desktop:
            self._handle_desktop_login()
        else:
            self._handle_mobile_login()

    def _handle_desktop_login(self):
        self.update_status("Opening browser for authentication...", disable_button=True)
        
        try:
            self.auth.login_desktop()
            
            if self.auth.is_authenticated():
                self.handle_success()
            else:
                self.update_status("Login completed but authentication failed", ft.Colors.RED_600, False)
                     
        except Exception as ex:
            self.handle_error(ex, "Desktop login")

    def _handle_mobile_login(self):
        import urllib.parse
        
        self.update_status("Opening browser...", disable_button=True)
        
        try:
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
            params = {
                'client_id': self.provider.client_id,
                'redirect_uri': self.provider.redirect_url,
                'response_type': 'code',
                'scope': ' '.join(self.provider.scopes),
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            oauth_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
            
            self.page.launch_url(oauth_url)
            
            self.update_status("Complete sign-in in browser, then return to app", ft.Colors.BLUE_600, False)

            show_snackbar(self.page, "Browser opened. Complete sign-in, then return here.", ft.Colors.BLUE_600)

        except Exception as ex:
            self.handle_error(ex, "Browser launch")