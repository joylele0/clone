import os
import sys
import json
import flet as ft

SCOPES = ["https://www.googleapis.com/auth/drive"]


def setup_paths():
    app_path = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    
    for path in [cwd, app_path]:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    return app_path, cwd


def repair_filesystem(cwd):
    try:
        files = os.listdir(cwd)
        for filename in files:
            if "\\" in filename:
                new_path = filename.replace("\\", os.sep)
                dir_name = os.path.dirname(new_path)
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)
                try:
                    os.rename(filename, new_path)
                except OSError:
                    pass
    except Exception:
        pass


def load_credentials(app_path, cwd):
    filenames = ["web.json", "credentials.json"]
    possible_paths = []
    
    for filename in filenames:
        possible_paths.extend([
            os.path.join(app_path, "services", filename),
            os.path.join(cwd, "services", filename),
            os.path.join(app_path, filename),
            os.path.join(cwd, filename)
        ])
    
    for creds_path in possible_paths:
        if os.path.exists(creds_path):
            try:
                with open(creds_path, 'r') as f:
                    data = json.load(f)
                    config = data.get('web') or data.get('installed')
                    
                    if not config:
                        continue
                    
                    return {
                        'path': creds_path,
                        'client_id': config.get('client_id'),
                        'client_secret': config.get('client_secret'),
                        'redirect_uris': config.get('redirect_uris', [])
                    }
            except Exception:
                continue
    
    return None


def get_redirect_url():
    return "http://localhost:8550/oauth_callback"


def main(page: ft.Page):
    page.title = "LMS Alternative"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.WHITE
    page.padding = 0
    
    try:
        app_path, cwd = setup_paths()
        repair_filesystem(cwd)
        
        from services.auth_service import GoogleAuth
        from ui.dashboard import Dashboard
        from ui.login import LoginView
        from ui.custom_control.multi_account_manager import MultiAccountManager
        
        try:
            from ui.firebase_mobile_login import FirebaseMobileLogin
        except ImportError:
            FirebaseMobileLogin = None
        
        creds = load_credentials(app_path, cwd)
        if not creds:
            page.add(ft.Text("ERROR: web.json not found!", color=ft.Colors.RED))
            page.update()
            return

        redirect_url = get_redirect_url()
        auth_service = GoogleAuth(credentials_file=creds['path'])
        account_manager = MultiAccountManager()
        
        from flet.auth.providers import GoogleOAuthProvider
        
        provider = GoogleOAuthProvider(
            client_id=creds['client_id'],
            client_secret=creds['client_secret'],
            redirect_url=redirect_url
        )
        provider.scopes = ["openid", "email", "profile"]
        
        def save_current_account_if_logged_in():
            if auth_service.is_authenticated() and auth_service.creds:
                user_info = auth_service.get_user_info()
                if user_info:
                    email = user_info.get("emailAddress")
                    if email:
                        token_dict = {
                            'token': auth_service.creds.token,
                            'refresh_token': auth_service.creds.refresh_token,
                            'token_uri': auth_service.creds.token_uri,
                            'client_id': auth_service.creds.client_id,
                            'client_secret': auth_service.creds.client_secret,
                            'scopes': list(auth_service.creds.scopes) if auth_service.creds.scopes else SCOPES,
                        }
                        account_manager.add_account(email, user_info, token_dict, save_credentials=True)
                        print(f"✓ Account saved: {email}")
                        return email
            return None
        
        def handle_on_login(e):
            if e.error:
                show_snackbar(f"Login Error: {e.error}")
                return
            
            if not hasattr(page.auth, 'token') or not page.auth.token:
                show_snackbar("Authentication failed: No token received")
                return
            
            token_data = page.auth.token
            
            if isinstance(token_data, dict):
                token_data['client_id'] = creds['client_id']
                token_data['client_secret'] = creds['client_secret']
            
            if auth_service.login_with_token(token_data):
                save_current_account_if_logged_in()
                user_info = auth_service.get_user_info()
                if user_info:
                    email = user_info.get("emailAddress")
                    account_manager.set_current_account(email)
                show_dashboard()
            else:
                show_snackbar("Authentication failed: Could not complete login")
        
        page.on_login = handle_on_login
        
        def show_snackbar(message):
            page.snack_bar = ft.SnackBar(content=ft.Text(message), action="Dismiss")
            page.snack_bar.open = True
            page.update()
        
        def show_dashboard():
            page.controls.clear()
            dashboard = Dashboard(
                page, 
                auth_service, 
                handle_logout,
                on_add_account=handle_add_account,
                on_switch_account=handle_switch_account
            )
            page.add(dashboard.get_view() if hasattr(dashboard, 'get_view') else dashboard)
            page.update()
        
        def handle_logout():
            # Only log out, do not remove any saved accounts
            auth_service.logout()
            if hasattr(page.auth, 'logout'):
                page.auth.logout()
            show_login()
        
        def handle_add_account():
            save_current_account_if_logged_in()
            
            if hasattr(page.auth, 'logout'):
                page.auth.logout()
            
            show_login(is_adding_account=True)
        
        def handle_switch_account(email):
            save_current_account_if_logged_in()
            
            account_data = account_manager.get_account(email)
            if not account_data:
                show_snackbar(f"Account {email} not found.")
                return
            
            token_data = account_data.get("token_data")
            if token_data:
                if auth_service.login_with_token(token_data):
                    account_manager.set_current_account(email)
                    show_dashboard()
                else:
                    show_snackbar(f"Session expired for {email}. Please login again.")
                    if hasattr(page.auth, 'logout'):
                        page.auth.logout()
                    show_login(switching_to_email=email)
            else:
                if hasattr(page.auth, 'logout'):
                    page.auth.logout()
                show_login(switching_to_email=email)
        
        def show_login(is_adding_account=False, switching_to_email=None):
            page.controls.clear()
            
            is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
            
            if switching_to_email:
                info_text = ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.BLUE),
                        ft.Text(
                            f"Please login to {switching_to_email}",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "This account requires re-authentication",
                            size=14,
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                )
                page.add(info_text)
            elif is_adding_account:
                info_text = ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Icon(ft.Icons.PERSON_ADD, size=48, color=ft.Colors.GREEN),
                        ft.Text(
                            "Add Another Account",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Your current account will remain saved",
                            size=14,
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                )
                page.add(info_text)
            
            if is_mobile and FirebaseMobileLogin:
                firebase_config_path = os.path.join(app_path, "services", "firebase_config.json")
                if not os.path.exists(firebase_config_path):
                    firebase_config_path = os.path.join(cwd, "services", "firebase_config.json")
                
                firebase_config = {}
                if os.path.exists(firebase_config_path):
                    with open(firebase_config_path, 'r') as f:
                        firebase_config = json.load(f)
                
                page.add(FirebaseMobileLogin(
                    page, 
                    auth_service, 
                    firebase_config,
                    creds['client_id'],
                    on_success=show_dashboard
                ))
            else:
                login_view = LoginView(page, provider, auth_service, on_success=show_dashboard)
                page.add(login_view)
            
            page.update()
        
        if auth_service.is_authenticated():
            current_email = save_current_account_if_logged_in()
            if current_email:
                account_manager.set_current_account(current_email)
            show_dashboard()
        else:
            show_login()
            
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        page.add(ft.Text(f"CRITICAL ERROR: {e}", color=ft.Colors.RED))
        page.update()
        print(f"CRITICAL ERROR:\n{error_msg}")


if __name__ == "__main__":
    ft.app(target=main)