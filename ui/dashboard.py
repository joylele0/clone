import flet as ft
from services.drive_service import DriveService
import re

class Dashboard:
    """Main dashboard view with sidebar and folder listing"""
    
    def __init__(self, page, auth_service, on_logout):
        self.page = page
        self.auth = auth_service
        self.on_logout = on_logout
        self.drive = DriveService(auth_service.get_service())
        
        self.current_folder_id = 'root'
        self.folder_stack = []
        self.selected_files = set()
        self.current_view = "your_folders"  # Track current view
        
        # Get user info
        user_info = self.auth.get_user_info()
        self.user_email = user_info.get('emailAddress', 'User') if user_info else 'User'
        
        # UI Components
        self.search_field = ft.TextField(
            hint_text="Search",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.handle_search,
            border_color=ft.Colors.GREY_400,
            filled=True,
            expand=True
        )
        
        self.folder_list = ft.Column(
            spacing=0,
            scroll=ft.ScrollMode.ALWAYS,
            expand=True,
            height=None,
            width=None
        )
        
        # Load initial folders
        self.load_your_folders()
    
    def load_your_folders(self):
        """Load user's own folders from My Drive"""
        self.current_view = "your_folders"
        self.folder_list.controls.clear()
        
        print("Loading your folders...")  # Debug
        
        try:
            # Get only folders from root
            result = self.drive.list_files('root', page_size=100)
            files = result['files']
            
            print(f"Total files in root: {len(files)}")  # Debug
            
            # Filter only folders
            folders = [f for f in files if f.get('mimeType') == 'application/vnd.google-apps.folder']
            
            print(f"Total folders found: {len(folders)}")  # Debug
            
            for folder in folders:
                # Count subfolders
                subfolder_result = self.drive.list_files(folder['id'], page_size=1000)
                subfolder_count = len([f for f in subfolder_result['files'] 
                                      if f.get('mimeType') == 'application/vnd.google-apps.folder'])
                
                print(f"Folder: {folder['name']}, Subfolders: {subfolder_count}")  # Debug
                
                folder_item = self.create_folder_item(folder, subfolder_count)
                self.folder_list.controls.append(folder_item)
            
            if len(folders) == 0:
                self.folder_list.controls.append(
                    ft.Container(
                        content=ft.Text("No folders found", color=ft.Colors.GREY_500),
                        padding=20,
                        bgcolor=ft.Colors.WHITE
                    )
                )
            
            print(f"Total controls in folder_list: {len(self.folder_list.controls)}")  # Debug
            print("Updating page...")  # Debug
            self.page.update()
            print("Page updated!")  # Debug
            
        except Exception as e:
            print(f"Error loading folders: {e}")
            import traceback
            traceback.print_exc()
    
    def load_shared_drives(self):
        """Load shared drives"""
        self.current_view = "shared_drives"
        self.folder_list.controls.clear()
        
        try:
            # Get shared drives
            results = self.drive.service.drives().list(
                pageSize=100,
                fields="drives(id, name)"
            ).execute()
            
            shared_drives = results.get('drives', [])
            
            for drive in shared_drives:
                # Count folders in shared drive
                folder_result = self.drive.list_files(drive['id'], page_size=1000)
                folder_count = len([f for f in folder_result['files'] 
                                   if f.get('mimeType') == 'application/vnd.google-apps.folder'])
                
                folder_item = self.create_folder_item(
                    {'id': drive['id'], 'name': drive['name']},
                    folder_count,
                    is_shared_drive=True
                )
                self.folder_list.controls.append(folder_item)
            
            if len(shared_drives) == 0:
                self.folder_list.controls.append(
                    ft.Container(
                        content=ft.Text("No shared drives found", color=ft.Colors.GREY_500),
                        padding=20
                    )
                )
        except Exception as e:
            print(f"Error loading shared drives: {e}")
            self.folder_list.controls.append(
                ft.Container(
                    content=ft.Text("Error loading shared drives", color=ft.Colors.RED),
                    padding=20
                )
            )
        
        self.page.update()
    
    def create_folder_item(self, folder, subfolder_count, is_shared_drive=False):
        """Create a folder list item with subfolder count"""
        folder_name = folder['name'].upper() if len(folder['name']) < 20 else folder['name']
        print(f"Creating folder item for: {folder_name}")  # Debug
        
        return ft.Container(
            content=ft.Row([
                ft.Text(
                    folder_name,
                    size=14,
                    weight=ft.FontWeight.W_500,
                    expand=True
                ),
                ft.Text(
                    f"{subfolder_count} FOLDERS",
                    size=12,
                    color=ft.Colors.GREY_600
                ),
                ft.IconButton(
                    icon=ft.Icons.MORE_VERT,
                    icon_size=20,
                    on_click=lambda e, f=folder: self.show_folder_menu(f, is_shared_drive)
                )
            ]),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
            bgcolor=ft.Colors.WHITE,
            on_click=lambda e, f=folder: self.open_folder(f, is_shared_drive)
        )
    
    def open_folder(self, folder, is_shared_drive=False):
        """Open folder to show its contents"""
        print(f"Opening folder: {folder['name']}")
        self.show_folder_contents(folder['id'], folder['name'])
    
    def show_folder_contents(self, folder_id, folder_name):
        """Show contents of a folder"""
        self.folder_list.controls.clear()
        
        # Add back button
        back_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ARROW_BACK, size=20),
                ft.Text("Back", size=14, weight=ft.FontWeight.BOLD)
            ]),
            padding=15,
            on_click=lambda e: self.go_back_to_list()
        )
        self.folder_list.controls.append(back_btn)
        
        # Add folder title
        title = ft.Container(
            content=ft.Text(
                folder_name,
                size=18,
                weight=ft.FontWeight.BOLD
            ),
            padding=ft.padding.only(left=15, right=15, bottom=10)
        )
        self.folder_list.controls.append(title)
        
        # Get folder contents
        result = self.drive.list_files(folder_id, page_size=100)
        files = result['files']
        
        for file in files:
            file_item = self.create_file_item(file)
            self.folder_list.controls.append(file_item)
        
        if len(files) == 0:
            self.folder_list.controls.append(
                ft.Container(
                    content=ft.Text("Folder is empty", color=ft.Colors.GREY_500),
                    padding=20
                )
            )
        
        self.page.update()
    
    def create_file_item(self, file):
        """Create a file/folder list item for detailed view"""
        is_folder = file.get('mimeType') == 'application/vnd.google-apps.folder'
        icon = ft.Icons.FOLDER if is_folder else ft.Icons.INSERT_DRIVE_FILE
        icon_color = ft.Colors.AMBER_700 if is_folder else ft.Colors.BLUE_GREY_400
        
        # Format size
        size_str = "Folder"
        if not is_folder and file.get('size'):
            size = int(file.get('size'))
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
        
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=icon_color, size=24),
                ft.Column([
                    ft.Text(file['name'], size=14, weight=ft.FontWeight.W_500),
                    ft.Text(size_str, size=12, color=ft.Colors.GREY_600)
                ], spacing=2, expand=True),
                ft.IconButton(
                    icon=ft.Icons.MORE_VERT,
                    icon_size=20,
                    on_click=lambda e, f=file: self.show_file_menu(f)
                )
            ]),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
            on_click=lambda e: self.handle_file_click(file) if is_folder else None
        )
    
    def handle_file_click(self, file):
        """Handle clicking on a file/folder in detailed view"""
        if file.get('mimeType') == 'application/vnd.google-apps.folder':
            self.show_folder_contents(file['id'], file['name'])
    
    def go_back_to_list(self):
        """Go back to folder list"""
        if self.current_view == "your_folders":
            self.load_your_folders()
        else:
            self.load_shared_drives()
    
    def show_folder_menu(self, folder, is_shared_drive=False):
        """Show menu for folder actions"""
        def close_menu(e):
            menu.open = False
            self.page.update()
        
        menu = ft.AlertDialog(
            title=ft.Text(folder['name']),
            content=ft.Column([
                ft.TextButton("Open", on_click=lambda e: [close_menu(e), self.open_folder(folder, is_shared_drive)]),
                ft.TextButton("Rename", on_click=lambda e: [close_menu(e), self.rename_folder_dialog(folder)]),
                ft.TextButton("Delete", on_click=lambda e: [close_menu(e), self.delete_folder_dialog(folder)]),
            ], tight=True),
            actions=[ft.TextButton("Cancel", on_click=close_menu)]
        )
        self.page.dialog = menu
        menu.open = True
        self.page.update()
    
    def show_file_menu(self, file):
        """Show menu for file actions"""
        def close_menu(e):
            menu.open = False
            self.page.update()
        
        menu = ft.AlertDialog(
            title=ft.Text(file['name']),
            content=ft.Column([
                ft.TextButton("Rename", on_click=lambda e: [close_menu(e), self.rename_file_dialog(file)]),
                ft.TextButton("Delete", on_click=lambda e: [close_menu(e), self.delete_file_dialog(file)]),
                ft.TextButton("Info", on_click=lambda e: [close_menu(e), self.show_file_info(file)]),
            ], tight=True),
            actions=[ft.TextButton("Cancel", on_click=close_menu)]
        )
        self.page.dialog = menu
        menu.open = True
        self.page.update()
    
    def show_new_menu(self, e):
        """Show menu for creating new folder or adding shared link"""
        print("+ NEW button clicked!")  # Debug
        
        def close_menu(e):
            print("Closing menu")  # Debug
            menu.open = False
            self.page.update()
        
        def create_folder_handler(e):
            print("Create New Folder selected")  # Debug
            close_menu(e)
            self.create_new_folder(e)
        
        def add_link_handler(e):
            print("Add Shared Drive Link selected")  # Debug
            close_menu(e)
            self.add_shared_link_dialog(e)
        
        menu = ft.AlertDialog(
            title=ft.Text("New"),
            content=ft.Column([
                ft.ElevatedButton(
                    "Create New Folder",
                    icon=ft.Icons.CREATE_NEW_FOLDER,
                    on_click=create_folder_handler,
                    width=250
                ),
                ft.ElevatedButton(
                    "Add Shared Drive Link",
                    icon=ft.Icons.LINK,
                    on_click=add_link_handler,
                    width=250
                ),
            ], tight=True, spacing=10),
            actions=[ft.TextButton("Cancel", on_click=close_menu)]
        )
        self.page.dialog = menu
        menu.open = True
        print("Menu dialog opened")  # Debug
        self.page.update()
    
    def create_new_folder(self, e):
        """Show create folder dialog"""
        print("Create new folder dialog opened")  # Debug
        name_field = ft.TextField(hint_text="Folder name", autofocus=True)
        status_text = ft.Text("", color=ft.Colors.RED, size=12)
        
        def create(e):
            print("Create button clicked")  # Debug
            folder_name = name_field.value.strip()
            print(f"Folder name entered: '{folder_name}'")  # Debug
            
            if folder_name:
                status_text.value = "Creating folder..."
                status_text.color = ft.Colors.BLUE
                self.page.update()
                
                try:
                    print(f"Attempting to create folder: {folder_name}")  # Debug
                    result = self.drive.create_folder(folder_name, 'root')
                    print(f"Create folder result: {result}")  # Debug
                    
                    if result:
                        status_text.value = "Folder created successfully!"
                        status_text.color = ft.Colors.GREEN
                        self.page.update()
                        
                        # Close dialog and reload
                        dialog.open = False
                        self.page.update()
                        print("Reloading folders...")  # Debug
                        self.load_your_folders()
                    else:
                        status_text.value = "Failed to create folder"
                        status_text.color = ft.Colors.RED
                        self.page.update()
                except Exception as ex:
                    print(f"Exception creating folder: {ex}")  # Debug
                    status_text.value = f"Error: {str(ex)}"
                    status_text.color = ft.Colors.RED
                    self.page.update()
            else:
                status_text.value = "Please enter a folder name"
                status_text.color = ft.Colors.RED
                self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("New Folder"),
            content=ft.Column([
                name_field,
                status_text
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Create", on_click=create)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def add_shared_link_dialog(self, e):
        """Show dialog to add shared Google Drive link"""
        link_field = ft.TextField(
            hint_text="Paste Google Drive link here",
            autofocus=True,
            multiline=False
        )
        status_text = ft.Text("", color=ft.Colors.RED, size=12)
        
        def add_link(e):
            link = link_field.value.strip()
            if link:
                # Extract folder ID from link
                folder_id = self.extract_folder_id(link)
                if folder_id:
                    status_text.value = "Accessing folder..."
                    status_text.color = ft.Colors.BLUE
                    self.page.update()
                    
                    # Try to access the folder
                    try:
                        folder_info = self.drive.get_file_info(folder_id)
                        if folder_info:
                            status_text.value = f"Success! Opening '{folder_info['name']}'"
                            status_text.color = ft.Colors.GREEN
                            self.page.update()
                            
                            # Close dialog and open the folder
                            dialog.open = False
                            self.page.update()
                            self.show_folder_contents(folder_id, folder_info['name'])
                        else:
                            status_text.value = "Could not access folder. Check permissions."
                            status_text.color = ft.Colors.RED
                            self.page.update()
                    except Exception as ex:
                        status_text.value = f"Error: {str(ex)}"
                        status_text.color = ft.Colors.RED
                        self.page.update()
                else:
                    status_text.value = "Invalid Google Drive link"
                    status_text.color = ft.Colors.RED
                    self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add Shared Drive Link"),
            content=ft.Column([
                ft.Text("Paste a Google Drive folder link that has been shared with you:", size=12),
                link_field,
                status_text
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Access Folder", on_click=add_link)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def extract_folder_id(self, link):
        """Extract folder ID from Google Drive link"""
        # Pattern 1: https://drive.google.com/drive/folders/FOLDER_ID
        pattern1 = r'drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)'
        match = re.search(pattern1, link)
        if match:
            return match.group(1)
        
        # Pattern 2: https://drive.google.com/drive/u/0/folders/FOLDER_ID
        pattern2 = r'drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)'
        match = re.search(pattern2, link)
        if match:
            return match.group(1)
        
        # Pattern 3: Direct ID (if user just pastes the ID)
        pattern3 = r'^[a-zA-Z0-9_-]+$'
        if re.match(pattern3, link) and len(link) > 20:
            return link
        
        return None
    
    def rename_folder_dialog(self, folder):
        """Show rename dialog for folder"""
        name_field = ft.TextField(value=folder['name'], autofocus=True)
        
        def rename(e):
            new_name = name_field.value.strip()
            if new_name and new_name != folder['name']:
                result = self.drive.rename_file(folder['id'], new_name)
                if result:
                    self.load_your_folders()
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Rename Folder"),
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Rename", on_click=rename)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def delete_folder_dialog(self, folder):
        """Show delete confirmation for folder"""
        def delete(e):
            success = self.drive.delete_file(folder['id'])
            if success:
                self.load_your_folders()
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{folder['name']}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.Colors.RED)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def rename_file_dialog(self, file):
        """Show rename dialog"""
        name_field = ft.TextField(value=file['name'], autofocus=True)
        
        def rename(e):
            new_name = name_field.value.strip()
            if new_name and new_name != file['name']:
                result = self.drive.rename_file(file['id'], new_name)
                if result:
                    self.go_back_to_list()
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Rename File"),
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Rename", on_click=rename)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def delete_file_dialog(self, file):
        """Show delete confirmation"""
        def delete(e):
            success = self.drive.delete_file(file['id'])
            if success:
                self.go_back_to_list()
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{file['name']}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.Colors.RED)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_file_info(self, file):
        """Show file information dialog"""
        info = self.drive.get_file_info(file['id'])
        if not info:
            return
        
        content = ft.Column([
            ft.Text(f"Name: {info.get('name', 'N/A')}"),
            ft.Text(f"Type: {info.get('mimeType', 'N/A')}"),
            ft.Text(f"Size: {info.get('size', 'N/A')} bytes"),
            ft.Text(f"Modified: {info.get('modifiedTime', 'N/A')}"),
        ])
        
        dialog = ft.AlertDialog(
            title=ft.Text("File Information"),
            content=content,
            actions=[ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_dialog(self, dialog):
        """Close a dialog"""
        dialog.open = False
        self.page.update()
    
    def handle_search(self, e):
        """Handle search query"""
        query = self.search_field.value.strip()
        if not query:
            self.load_your_folders()
            return
        
        # Implement search functionality
        print(f"Searching for: {query}")
    
    def handle_logout(self, e):
        """Handle logout"""
        self.auth.logout()
        self.on_logout()
    
    def get_view(self):
        """Return the main view with sidebar"""
        # Sidebar
        sidebar = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.TextButton(
                        "+ NEW",
                        on_click=self.show_new_menu,
                        style=ft.ButtonStyle(
                            color=ft.Colors.BLACK,
                            bgcolor=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=8),
                        )
                    ),
                    padding=10
                ),
                ft.Container(
                    content=ft.TextButton(
                        "SETTINGS",
                        on_click=lambda e: print("Settings clicked"),
                        style=ft.ButtonStyle(
                            color=ft.Colors.BLACK,
                            bgcolor=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=8),
                        )
                    ),
                    padding=10
                ),
                ft.Container(
                    content=ft.TextButton(
                        "TO-DO",
                        on_click=lambda e: print("To-Do clicked"),
                        style=ft.ButtonStyle(
                            color=ft.Colors.BLACK,
                            bgcolor=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=8),
                        )
                    ),
                    padding=10
                ),
                ft.Container(
                    content=ft.TextButton(
                        "ACCOUNT",
                        on_click=self.handle_logout,
                        style=ft.ButtonStyle(
                            color=ft.Colors.BLACK,
                            bgcolor=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=8),
                        )
                    ),
                    padding=10
                ),
            ]),
            width=200,
            bgcolor=ft.Colors.GREY_100,
            padding=20
        )
        
        # Main content area
        main_content = ft.Container(
            content=ft.Column([
                # Top bar with search and account
                ft.Container(
                    content=ft.Row([
                        self.search_field,
                        ft.IconButton(
                            icon=ft.Icons.ACCOUNT_CIRCLE,
                            icon_size=32,
                            tooltip=self.user_email
                        )
                    ]),
                    padding=20,
                    bgcolor=ft.Colors.WHITE
                ),
                # Folder section header with tabs
                ft.Container(
                    content=ft.Row([
                        ft.TextButton(
                            "YOUR FOLDERS",
                            on_click=lambda e: self.load_your_folders(),
                            style=ft.ButtonStyle(
                                color=ft.Colors.BLACK if self.current_view == "your_folders" else ft.Colors.GREY_600,
                            )
                        ),
                        ft.TextButton(
                            "SHARED DRIVES",
                            on_click=lambda e: self.load_shared_drives(),
                            style=ft.ButtonStyle(
                                color=ft.Colors.BLACK if self.current_view == "shared_drives" else ft.Colors.GREY_600,
                            )
                        ),
                    ]),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                    border=ft.border.only(bottom=ft.BorderSide(2, ft.Colors.GREY_300))
                ),
                # Folder list
                ft.Container(
                    content=self.folder_list,
                    expand=True,
                    bgcolor=ft.Colors.GREY_50,
                    padding=0
                )
            ], spacing=0, expand=True),
            expand=True,
            bgcolor=ft.Colors.WHITE
        )
        
        print(f"Building view - Folder list has {len(self.folder_list.controls)} controls")  # Debug
        
        # Main layout
        return ft.Row([
            sidebar,
            ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
            main_content
        ], expand=True, spacing=0)