import flet as ft
from flet import Icon, Icons, Text, FontWeight, TextAlign, Container, ElevatedButton, Colors
from services.auth_service import GoogleAuth


class LoginView(ft.Column):
    def __init__(self, page, auth_service: GoogleAuth, on_success):
        super().__init__(
            controls=[
                Container(height=50),
                Icon(Icons.CLOUD_CIRCLE, size=100, color=Colors.BLUE),
                Container(height=20),
                Text(
                    "Google Drive Folder Manager",
                    size=32,
                    weight=FontWeight.BOLD,
                    text_align=TextAlign.CENTER
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True
        )

        self.page = page
        self.auth = auth_service
        self.on_success = on_success

        self.status_text = Text("", color=Colors.RED)
        self.controls.append(self.status_text)

        self.login_button = ElevatedButton(
            text="Login with Google",
            icon=Icons.LOGIN,
            on_click=self.handle_login,
            style=ft.ButtonStyle(
                bgcolor=Colors.BLUE,
                color=Colors.WHITE,
                padding=ft.Padding(10, 5, 10, 5),
            )
        )
        self.controls.append(self.login_button)

    def handle_login(self, e):
        self.status_text.value = "Opening browser for Google login..."
        self.status_text.color = Colors.BLACK
        self.page.update()

        try:
            
            self.auth.login()

            if self.auth.is_authenticated():
                self.status_text.value = "Login successful!"
                self.status_text.color = Colors.GREEN
                self.page.update()
                self.on_success()
            else:
                self.status_text.value = "Login was not completed."
                self.status_text.color = Colors.RED
                self.page.update()

        except FileNotFoundError:
            self.status_text.value = f"Error: credentials.json not found at {self.auth.credentials_file}"
            self.status_text.color = Colors.RED
            self.page.update()

        except Exception as ex:
            self.status_text.value = f"Login failed: {ex}"
            self.status_text.color = Colors.RED
            self.page.update()
