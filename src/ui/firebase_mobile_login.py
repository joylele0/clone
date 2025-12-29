import flet as ft
import urllib.parse
import urllib.request
import urllib.error
import json
import secrets
import threading


class FirebaseMobileLogin(ft.Column):
    def __init__(self, page, auth_service, firebase_config, oauth_client_id, on_success=None):
        super().__init__(
            controls=[],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=20
        )
        self.page = page
        self.auth = auth_service
        self.firebase_config = firebase_config
        self.oauth_client_id = oauth_client_id
        self.on_success = on_success
        self.session_id = None
        self.polling = False
        
        self.status_text = None
        self.login_button = None
        self.progress = None
        
        self._build_ui()
        
    def _build_ui(self):
        platform_name = self._get_platform_name()
        
        self.controls.extend([
            ft.Container(height=50),
            ft.Icon(ft.Icons.CLOUD_CIRCLE, size=100, color=ft.Colors.BLUE_600),
            ft.Text("Learning Management System", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Text("Mobile Login", size=16, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Text(f"Platform: {platform_name}", size=12, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
            ft.Container(height=20)
        ])
        
        self.status_text = ft.Text("Sign in with your Google account", color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER)
        self.controls.append(self.status_text)
        
        self.login_button = ft.ElevatedButton(
            text="Sign in with Google",
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
            self.login_button
        ])
        
        self.progress = ft.ProgressRing(visible=False)
        self.controls.append(self.progress)

    def _get_platform_name(self):
        platform_map = {
            ft.PagePlatform.WINDOWS: "Windows",
            ft.PagePlatform.LINUX: "Linux",
            ft.PagePlatform.MACOS: "macOS",
            ft.PagePlatform.ANDROID: "Android",
            ft.PagePlatform.IOS: "iOS"
        }
        return platform_map.get(self.page.platform, str(self.page.platform))

    def update_status(self, message, color=ft.Colors.BLUE_600):
        self.status_text.value = message
        self.status_text.color = color
        self.page.update()

    def handle_login(self, e):
        self.session_id = secrets.token_urlsafe(16)
        
        self.update_status("Opening browser...", ft.Colors.ORANGE)
        self.login_button.disabled = True
        self.progress.visible = True
        self.page.update()
        
        try:
            oauth_url = self._build_oauth_url()
            
            self.page.launch_url(oauth_url)
            
            self.update_status("Waiting for sign-in...", ft.Colors.BLUE_600)
            self.page.update()
            
            self._start_polling()
            
        except Exception as ex:
            import traceback
            self.update_status(f"Error: {str(ex)[:50]}...", ft.Colors.RED_600)
            self.login_button.disabled = False
            self.progress.visible = False
            print(f"Mobile login error: {ex}\n{traceback.format_exc()}")
    
    def _build_oauth_url(self):
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            'client_id': self.oauth_client_id,
            'redirect_uri': 'https://lms-callback-git-main-astrallibertads-projects.vercel.app/callback.html',
            'response_type': 'token',
            'scope': 'openid email profile https://www.googleapis.com/auth/drive',
            'state': self.session_id
        }
        return f"{auth_url}?{urllib.parse.urlencode(params)}"
    
    def _start_polling(self):
        self.polling = True
        
        def poll():
            max_attempts = 60
            attempt = 0
            
            while self.polling and attempt < max_attempts:
                self.page.run_task(self._update_waiting_status, attempt)
                
                try:
                    check_url = f"https://lms-callback.vercel.app/api/token/{self.session_id}"
                    
                    req = urllib.request.Request(check_url)
                    req.add_header('Accept', 'application/json')
                    
                    try:
                        with urllib.request.urlopen(req, timeout=10) as response:
                            response_text = response.read().decode('utf-8')
                            data = json.loads(response_text)
                            
                            if data.get('success') and data.get('token'):
                                token_info = data['token']
                                if token_info.get('access_token'):
                                    self.page.run_task(self._handle_tokens, token_info)
                                    return
                            
                    except urllib.error.HTTPError:
                        pass
                    except Exception:
                        pass
                    
                    import time
                    time.sleep(5)
                    attempt += 1
                    
                except Exception:
                    import time
                    time.sleep(5)
                    attempt += 1
            
            if attempt >= max_attempts:
                self.page.run_task(self._handle_timeout)
        
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
    
    async def _update_waiting_status(self, attempt):
        dots = "." * ((attempt % 3) + 1)
        self.status_text.value = f"Waiting for sign-in{dots}"
        self.page.update()
    
    async def _handle_tokens(self, tokens):
        self.polling = False
        
        self.update_status("Authenticating...", ft.Colors.GREEN_600)
        self.page.update()
        
        token_data = {
            'access_token': tokens.get('access_token'),
            'token_type': tokens.get('token_type', 'Bearer'),
            'expires_in': tokens.get('expires_in'),
            'scope': tokens.get('scope'),
            'client_id': self.oauth_client_id,
            'client_secret': self.auth.client_secret
        }
        
        auth_result = self.auth.login_with_token(token_data)
        
        if auth_result:
            self.update_status("Authentication complete!", ft.Colors.GREEN_600)
            self.progress.visible = False
            self.page.update()
            
            if self.on_success:
                self.on_success()
        else:
            self.update_status("Authentication failed", ft.Colors.RED_600)
            self.login_button.disabled = False
            self.progress.visible = False
            self.page.update()
    
    async def _handle_timeout(self):
        self.polling = False
        self.update_status("Timeout - Sign-in took too long", ft.Colors.ORANGE)
        self.login_button.disabled = False
        self.progress.visible = False
        self.page.update()