import flet as ft
import datetime
import json
import os
from pathlib import Path

SAVED_LINKS_FILE = "saved_links.json"
LMS_CONFIG_FILE = "lms_config.json"


class TodoView:
 
    def __init__(self, page: ft.Page, on_back=None, drive_service=None):
        self.page = page
        self.on_back = on_back
        self.drive_service = drive_service
        self.lms_config = self._load_config()
        self.lms_root_id = self.lms_config.get("lms_root_id")
        
        self.data_dir = Path("lms_data")
        self.data_dir.mkdir(exist_ok=True)
        self.assignments_file = self.data_dir / "assignments.json"
        self.students_file = self.data_dir / "students.json"
        self.submissions_file = self.data_dir / "submissions.json"
        
        
        try:
            from services.notification_service import NotificationService
            self.notification_service = NotificationService(self.data_dir)
        except ImportError:
            self.notification_service = None
        
        self.assignments = self.load_json(self.assignments_file, [])
        self.students = self.load_json(self.students_file, [])
        self.submissions = self.load_json(self.submissions_file, [])
        
        
        self.saved_links = self.load_saved_links()
        
        for assignment in self.assignments:
            if 'id' not in assignment:
                assignment['id'] = str(datetime.datetime.now().timestamp()) + str(self.assignments.index(assignment))
        if self.assignments:
            self.save_json(self.assignments_file, self.assignments)
        
        self.current_mode = "teacher"  
        self.current_student_email = None
        
        self.assignment_title = ft.TextField(hint_text="Assignment Title", expand=True)
        self.assignment_description = ft.TextField(
            hint_text="Description/Instructions",
            multiline=True,
            min_lines=3,
            max_lines=5,
            expand=True
        )
        
        self.subject_dropdown = ft.Dropdown(
            hint_text="Select Subject",
            options=[
                ft.dropdown.Option("Mathematics"),
                ft.dropdown.Option("Science"),
                ft.dropdown.Option("English"),
                ft.dropdown.Option("History"),
                ft.dropdown.Option("Computer Science"),
                ft.dropdown.Option("Arts"),
                ft.dropdown.Option("Physical Education"),
                ft.dropdown.Option("Other"),
            ],
            width=200
        )
        
        self.max_score_field = ft.TextField(
            hint_text="Max Score (e.g., 100)",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter()
        )
        
        
        self.selected_drive_folder_id = None
        self.drive_folder_label = ft.Text("No folder selected", size=12, italic=True)

        
        
        self.target_dropdown = ft.Dropdown(
            hint_text="Assign To",
            width=200,
            value="all",
            options=[
                ft.dropdown.Option("all", "All Students"),
                ft.dropdown.Option("bridging", "Bridging Only"),
                ft.dropdown.Option("regular", "Regular Only"),
            ]
        )

        self.attachment_text = ft.Text("No file attached", size=12, italic=True)
        self.selected_attachment = {"path": None, "name": None}
        
        self.selected_date_value = None
        self.selected_time_value = None
        self.selected_deadline_display = ft.Text("No deadline selected", size=12, italic=True)
        
        self.date_picker = ft.DatePicker(on_change=self.on_date_selected)
        self.time_picker = ft.TimePicker(on_change=self.on_time_selected)
        
        self.assignment_column = ft.Column(scroll="auto", expand=True, spacing=10)
        
        self.filter_dropdown = ft.Dropdown(
            hint_text="Filter",
            options=[
                ft.dropdown.Option("All"),
                ft.dropdown.Option("Active"),
                ft.dropdown.Option("Completed"),
                ft.dropdown.Option("Overdue"),
            ],
            value="All",
            width=150,
            on_change=lambda e: self.display_assignments()
        )
        
        self.mode_switch = ft.Switch(value=False, on_change=self.switch_mode)
        self.mode_label = ft.Text("👨‍🏫 Teacher View", size=16, weight=ft.FontWeight.BOLD)
        
        self.settings_btn = ft.ElevatedButton(
            "Storage",
            icon=ft.Icons.SETTINGS,
            on_click=lambda e: (print("DEBUG: Settings Clicked"), self.show_storage_settings())
        )
        
        self.student_dropdown = ft.Dropdown(
            hint_text="Select Student",
            width=250,
            on_change=self.on_student_selected
        )
        self.update_student_dropdown()
        
        self.student_selector_row = ft.Row([
            ft.Text("Viewing as:", size=14),
            self.student_dropdown
        ], visible=False)
        
        
        self.form_container = None
        self.manage_students_btn = None
        
    
    def _create_browse_dialog(self, initial_parent_id, on_select):
        
        current_folder = {'id': initial_parent_id, 'name': 'Root'}
        if initial_parent_id == 'root':
             current_folder['name'] = 'My Drive'
        elif self.drive_service:
             try:
                 info = self.drive_service.get_file_info(initial_parent_id)
                 if info: current_folder = info
             except: pass

        
        file_list = ft.Column(scroll="auto", height=300)
        current_path_text = ft.Text(f"Current: {current_folder['name']}", weight=ft.FontWeight.BOLD)
        loading_indicator = ft.ProgressBar(width=None, visible=False)
        
        dialog = None 
        
        def load_folder(folder_id, initial=False):
            loading_indicator.visible = True
            file_list.controls.clear()
            
            
            self.page.update()
            
            try:
                results = self.drive_service.list_files(folder_id=folder_id, use_cache=True)
                files = results.get('files', []) if results else []
                
                folders = [f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder']
                
                
                if (folder_id == 'root' or folder_id == initial_parent_id) and self.saved_links:
                    file_list.controls.append(ft.Container(
                        content=ft.Text("⭐ Saved Folders", weight=ft.FontWeight.BOLD),
                        padding=ft.padding.only(left=10, top=10, bottom=5)
                    ))
                    for link in self.saved_links:
                        
                        if link.get("mimeType") == "application/vnd.google-apps.folder":
                            file_list.controls.append(
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.FOLDER_SPECIAL, color=ft.Colors.AMBER),
                                    title=ft.Text(link.get("name", "Unknown")),
                                    subtitle=ft.Text("Saved Link"),
                                    on_click=lambda e, fid=link["id"], fname=link["name"]: enter_folder(fid, fname),
                                    trailing=ft.IconButton(ft.Icons.CHECK, on_click=lambda e, fid=link["id"]: confirm_selection(fid))
                                )
                            )
                    file_list.controls.append(ft.Divider())

                if folder_id != 'root' and folder_id != initial_parent_id:
                     file_list.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.ARROW_UPWARD),
                            title=ft.Text(".. (Up)"),
                            on_click=lambda e: load_parent(folder_id)
                        )
                     )
                
                for f in folders:
                     file_list.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.FOLDER),
                            title=ft.Text(f['name']),
                            subtitle=ft.Text("Click to open"),
                            on_click=lambda e, fid=f['id'], fname=f['name']: enter_folder(fid, fname),
                            trailing=ft.IconButton(ft.Icons.CHECK, on_click=lambda e, fid=f['id']: confirm_selection(fid))
                        )
                     )
                     
                if not folders:
                    file_list.controls.append(ft.Text("No subfolders found."))
                    
            except Exception as e:
                file_list.controls.append(ft.Text(f"Error: {e}", color=ft.Colors.RED))
                
            loading_indicator.visible = False
            self.page.update()

        def enter_folder(fid, fname):
            current_path_text.value = f"Current: {fname}"
            load_folder(fid)
            
        def load_parent(current_id):
            current_path_text.value = f"Current: {current_folder['name']}"
            load_folder(initial_parent_id) 

        def confirm_selection(fid):
            on_select(fid)
            close_func(None)


        
        content = ft.Column([
            current_path_text,
            loading_indicator,
            file_list
        ])
        
        
        load_folder(initial_parent_id, initial=True)
        
        overlay, close_func = self._show_overlay_dialog(content, "Select Folder", width=400, height=500)

        content.controls.append(ft.Divider())
        content.controls.append(
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_func(None)),
                ft.ElevatedButton("Select Current Folder", on_click=lambda e, fid=current_folder['id']: confirm_selection(fid))
            ], alignment=ft.MainAxisAlignment.END)
        )

    def _load_config(self):
        if os.path.exists(LMS_CONFIG_FILE):
            try:
                with open(LMS_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_config(self):
        with open(LMS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.lms_config, f, indent=2)

    def load_json(self, filepath, default=None):
        
        if self.drive_service and self.lms_root_id:
            filename = filepath.name
            try:
                file = self.drive_service.find_file(filename, self.lms_root_id)
                if file:
                    content = self.drive_service.read_file_content(file['id'])
                    if content:
                        return json.loads(content)
            except Exception as e:
                print(f"Error loading from Drive: {e}")
                pass

        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return default if default is not None else []

    def save_json(self, filepath, data):
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving local: {e}")

        
        if self.drive_service and self.lms_root_id:
            filename = filepath.name
            try:
                existing = self.drive_service.find_file(filename, self.lms_root_id)
                if existing:
                    self.drive_service.update_file(existing['id'], str(filepath))
                else:
                    self.drive_service.upload_file(str(filepath), parent_id=self.lms_root_id)
            except Exception as e:
                print(f"Error saving to Drive: {e}")
                self.show_snackbar(f"Drive Sync Error: {e}", ft.Colors.RED)

    def _show_overlay_dialog(self, content_control, title=None, width=400, height=None):
        def close_overlay(e):
            if overlay in self.page.overlay:
                self.page.overlay.remove(overlay)
                self.page.update()

        header_controls = []
        if title:
             header_controls.append(ft.Text(title, size=20, weight=ft.FontWeight.BOLD))
        
        header_controls.append(ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_overlay))
        
        overlay_content = ft.Column([
            ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            content_control
        ], tight=True, spacing=10)

        overlay = ft.Container(
            content=ft.Container(
                content=overlay_content,
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                width=width,
                height=height,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
            ),
            alignment=ft.alignment.center,
            expand=True, 
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            on_click=lambda e: None 
        )
        
        self.page.overlay.append(overlay)
        self.page.update()
        return overlay, close_overlay

    def show_storage_settings(self):
        if not self.drive_service:
            self.show_snackbar("Drive service not available", ft.Colors.RED)
            return

        current_folder_name = "Not Set (Using Local Storage)"
        if self.lms_root_id:
            try:
                info = self.drive_service.get_file_info(self.lms_root_id)
                if info:
                    current_folder_name = info.get('name', 'Unknown')
            except:
                current_folder_name = "Invalid ID"
        
        unlink_btn = ft.ElevatedButton("Unlink (Use Local)", color=ft.Colors.RED)
        select_btn = ft.ElevatedButton("Select/Change Drive Folder")
        
        content = ft.Column([
            ft.Text(f"Current LMS Data Folder: {current_folder_name}", weight=ft.FontWeight.BOLD),
            ft.Text("Select a shared folder where all students and teachers have access."),
            ft.Divider(),
            select_btn,
            unlink_btn
        ], tight=True)
        
        overlay, close_func = self._show_overlay_dialog(content, "Storage Settings")
        print("DEBUG: Storage Settings Overlay Opened")

        unlink_btn.on_click = lambda e: self.unlink_drive_folder(overlay, close_func)
        select_btn.on_click = lambda e: (close_func(None), self.select_drive_folder_dialog())
        
        unlink_btn.update()
        select_btn.update()
        self.page.update()

    def unlink_drive_folder(self, overlay, close_func):
        self.lms_config["lms_root_id"] = None
        self.lms_root_id = None
        self._save_config()
        self.show_snackbar("Unlinked Drive folder. Using local storage.", ft.Colors.ORANGE)
        if close_func: close_func(None)
        
        self._refresh_students()
        self.display_assignments()

    def select_drive_folder_dialog(self):
        
        folders = None
        try:
            folders = self.drive_service.list_files(folder_id='root', use_cache=False)
        except Exception as e:
            self.show_snackbar(f"Error listing folders: {e}", ft.Colors.RED)
            return
        
        folder_list = folders.get('files', []) if folders else []
        folder_list = [f for f in folder_list if f['mimeType'] == 'application/vnd.google-apps.folder']

        list_view = ft.ListView(expand=True, spacing=10, height=300)

        def perform_search(query):
            results = self.drive_service.search_files(query, use_cache=False)
            update_list([f for f in results if f['mimeType'] == 'application/vnd.google-apps.folder'])

        def update_list(items):
            list_view.controls.clear()
            for f in items:
                 list_view.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.FOLDER),
                        title=ft.Text(f['name']),
                        on_click=lambda e, f=f: on_select(f)
                    )
                 )
            if list_view.page:
                list_view.update()

        def on_select(folder):
            self.lms_config["lms_root_id"] = folder['id']
            self.lms_root_id = folder['id']
            self._save_config()
            self.show_snackbar(f"Linked to '{folder['name']}'", ft.Colors.GREEN)
            close_func(None)
            
            self.assignments = self.load_json(self.assignments_file, [])
            self.students = self.load_json(self.students_file, [])
            self.submissions = self.load_json(self.submissions_file, [])
            self.display_assignments()

        search_field = ft.TextField(hint_text="Search folders...", on_submit=lambda e: perform_search(e.control.value))
        
        content = ft.Column([
            search_field,
            list_view
        ], height=400)
        
        
        def process_link(e):
            link = link_field.value.strip()
            if not link:
                return
            
            
            file_id = None
            
            
            if "/folders/" in link:
                try:
                    parts = link.split("/folders/")
                    if len(parts) > 1:
                        
                        
                        file_id = parts[1].split('?')[0].split('/')[0]
                except:
                    pass
            elif "id=" in link:
                try:
                    parts = link.split("id=")
                    if len(parts) > 1:
                        file_id = parts[1].split('&')[0]
                except:
                    pass
            elif len(link) > 20 and "/" not in link: 
                file_id = link
            
            if not file_id:
                self.show_snackbar("Could not extract ID from link", ft.Colors.RED)
                return
            
            
            try:
                info = self.drive_service.get_file_info(file_id)
                if info and info.get('mimeType') == 'application/vnd.google-apps.folder':
                    on_select(info['id'])
                else:
                    self.show_snackbar("ID is not a valid folder or access denied", ft.Colors.RED)
            except Exception as ex:
                self.show_snackbar(f"Error checking Link: {ex}", ft.Colors.RED)

        link_field = ft.TextField(
            hint_text="Paste Drive Link or Folder ID", 
            expand=True,
            text_size=12,
            on_submit=process_link
        )
        link_btn = ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=process_link, tooltip="Use Link")

        content = ft.Column([
            ft.Row([link_field, link_btn]),
            ft.Text("- OR -", size=10, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            search_field,
            list_view
        ], height=450)
        
        
        update_list(folder_list)
        
        overlay, close_func = self._show_overlay_dialog(content, "Select Drive Folder", width=500)
    
    def get_folder_name_by_id(self, folder_id):
        
        for link in self.saved_links:
            if link.get("id") == folder_id:
                return link.get("name", folder_id)
        return "Linked Folder"
    
    def _get_drive_folder_options(self):
        options = [ft.dropdown.Option("none", "No Drive folder")]
        return options

    def close_dialog(self, dialog):
        if dialog:
            dialog.open = False
            self.page.update()

    def load_saved_links(self):
        if os.path.exists(SAVED_LINKS_FILE):
            try:
                with open(SAVED_LINKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("links", [])
            except:
                pass
        return []

    def _get_bridging_students(self):
        return [s for s in self.students if s.get('is_bridging', False)]

    def _get_regular_students(self):
        return [s for s in self.students if not s.get('is_bridging', False)]

    def _refresh_students(self):
        self.students = self.load_json(self.students_file, [])
        self.update_student_dropdown()

    def _validate_email(self, email):
        if not email:
            return False, "Email is required"
        
        if "@" not in email or "." not in email:
             return False, "Invalid email format"
        
        for s in self.students:
            if s['email'] == email:
                return False, "Email already registered"
        return True, ""

    def on_date_selected(self, e):
        self.selected_date_value = self.date_picker.value
        self.update_deadline_display()
        self.page.close(self.date_picker)
        self.page.open(self.time_picker)
        self.page.update()

    def on_time_selected(self, e):
        self.selected_time_value = self.time_picker.value
        self.update_deadline_display()
        self.page.close(self.time_picker)
        self.page.update()



    def update_deadline_display(self):
        if self.selected_date_value and self.selected_time_value:
            self.selected_deadline_display.value = f"Deadline: {self.selected_date_value} at {self.selected_time_value}"
        elif self.selected_date_value:
            self.selected_deadline_display.value = f"Deadline: {self.selected_date_value}"
        else:
            self.selected_deadline_display.value = "No deadline selected"

    def pick_file(self, e):
        def on_result(e: ft.FilePickerResultEvent):
            if e.files:
                self.selected_attachment["path"] = e.files[0].path
                self.selected_attachment["name"] = e.files[0].name
                self.attachment_text.value = f"📎 {e.files[0].name}"
                self.page.update()
        
        file_picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files()
        
    def get_time_remaining(self, deadline_str):
        if not deadline_str:
            return "No deadline"
        try:
            deadline = datetime.datetime.fromisoformat(deadline_str)
            now = datetime.datetime.now()
            remaining = deadline - now
            
            if remaining.total_seconds() <= 0:
                return "⚠️ Overdue"
            
            days = remaining.days
            hours = remaining.seconds // 3600
            
            if days > 0:
                return f"⏱️ {days}d {hours}h remaining"
            elif hours > 0:
                minutes = (remaining.seconds % 3600) // 60
                return f"⏱️ {hours}h {minutes}m remaining"
            else:
                minutes = remaining.seconds // 60
                return f"⏱️ {minutes}m remaining"
        except:
            return "Invalid deadline"

    def get_status(self, deadline_str, assignment_id=None):
        if self.current_mode == "student" and assignment_id and self.current_student_email:
            
            submission = self.get_submission_status(assignment_id, self.current_student_email)
            if submission:
                return "Completed"

        if not deadline_str:
            return "Active"
        try:
            deadline = datetime.datetime.fromisoformat(deadline_str)
            if datetime.datetime.now() > deadline:
                return "Overdue"
            return "Active"
        except:
            return "Active"

    def get_submission_status(self, assignment_id, student_email):
        for sub in self.submissions:
            if sub['assignment_id'] == assignment_id and sub['student_email'] == student_email:
                return sub
        return None

    def get_submission_count(self, assignment_id):
        return sum(1 for sub in self.submissions if sub['assignment_id'] == assignment_id)

    def display_assignments(self):
        self.assignment_column.controls.clear()
        
        if self.current_mode == "teacher":
            self.display_teacher_view()
        else:
            self.display_student_view()
        
        self.page.update()

    def display_teacher_view(self):
        filtered = self.assignments
        if self.filter_dropdown.value != "All":
            filtered = [a for a in self.assignments if self.get_status(a.get('deadline')) == self.filter_dropdown.value]
        
        if not filtered:
            self.assignment_column.controls.append(
                ft.Container(
                    content=ft.Text("No assignments found", size=16, color=ft.Colors.GREY),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for assignment in filtered:
                card = self.create_teacher_assignment_card(assignment)
                self.assignment_column.controls.append(card)

    def display_student_view(self):
        
        if self.notification_service and self.current_student_email:
            unread_count = self.notification_service.get_unread_count(self.current_student_email)
            if unread_count > 0:
                self.assignment_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ft.Colors.ORANGE),
                            ft.Text(f"You have {unread_count} new notification(s)", 
                                   size=14, color=ft.Colors.ORANGE),
                            ft.TextButton("View All", on_click=lambda e: self.show_notifications_dialog())
                        ]),
                        padding=10,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.ORANGE),
                        border_radius=8
                    )
                )
        
        if not self.current_student_email:
            self.assignment_column.controls.append(
                ft.Text("Please select a student from the dropdown", size=16, color=ft.Colors.RED)
            )
            return
        
        
        current_student = next((s for s in self.students if s.get('email') == self.current_student_email), None)
        is_bridging = current_student.get('is_bridging', False) if current_student else False
        
        
        filtered = []
        for a in self.assignments:
            target = a.get('target_for', 'all')
            if target == 'all':
                filtered.append(a)
            elif target == 'bridging' and is_bridging:
                filtered.append(a)
            elif target == 'regular' and not is_bridging:
                filtered.append(a)
        
        
        if self.filter_dropdown.value != "All":
            filtered = [a for a in filtered if self.get_status(a.get('deadline'), a['id']) == self.filter_dropdown.value]
        
        if not filtered:
            self.assignment_column.controls.append(
                ft.Container(
                    content=ft.Text("No assignments found", size=16, color=ft.Colors.GREY),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for assignment in filtered:
                card = self.create_student_assignment_card(assignment)
                self.assignment_column.controls.append(card)

    def create_teacher_assignment_card(self, assignment):
        status = self.get_status(assignment.get('deadline'))
        time_remaining = self.get_time_remaining(assignment.get('deadline'))
        submission_count = self.get_submission_count(assignment['id'])
        total_students = len(self.students)
        
        status_color = {
            "Active": ft.Colors.GREEN,
            "Completed": ft.Colors.BLUE,
            "Overdue": ft.Colors.RED
        }.get(status, ft.Colors.GREY)
        
        drive_folder_id = assignment.get('drive_folder_id')
        drive_folder_name = self.get_folder_name_by_id(drive_folder_id) if drive_folder_id else None
        
        drive_row = ft.Row([
            ft.Icon(ft.Icons.FOLDER_SHARED, size=16, color=ft.Colors.BLUE),
            ft.Text(f"Drive: {drive_folder_name}", size=13, color=ft.Colors.BLUE),
            ft.IconButton(
                icon=ft.Icons.OPEN_IN_NEW,
                icon_size=16,
                tooltip="Open in Drive",
                on_click=lambda e, fid=drive_folder_id: self.open_drive_folder(fid)
            ) if self.drive_service else ft.Container()
        ]) if drive_folder_name else ft.Container()
        
        
        target_for = assignment.get('target_for', 'all')
        target_labels = {'all': '👥 All Students', 'bridging': '🔄 Bridging Only', 'regular': '📚 Regular Only'}
        target_colors = {'all': ft.Colors.GREY_700, 'bridging': ft.Colors.ORANGE, 'regular': ft.Colors.BLUE}
        target_badge = ft.Container(
            content=ft.Text(target_labels.get(target_for, 'All'), size=11, color=ft.Colors.WHITE),
            bgcolor=target_colors.get(target_for, ft.Colors.GREY),
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
            border_radius=10
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(
                        assignment['title'],
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        expand=True
                    ),
                    ft.Container(
                        content=ft.Text(status, size=12, color=ft.Colors.WHITE),
                        bgcolor=status_color,
                        padding=5,
                        border_radius=5
                    ),
                ]),
                ft.Divider(height=1),
                ft.Text(f"Subject: {assignment.get('subject', 'N/A')}", size=14),
                ft.Text(assignment.get('description', 'No description'), size=14, max_lines=3),
                ft.Row([
                    ft.Icon(ft.Icons.ACCESS_TIME, size=16),
                    ft.Text(time_remaining, size=13, italic=True)
                ]),
                ft.Text(f"Max Score: {assignment.get('max_score', 'N/A')}", size=13),
                drive_row,
                ft.Row([
                    ft.Icon(ft.Icons.PEOPLE, size=16),
                    ft.Text(f"Submissions: {submission_count}/{total_students}", size=13),
                    target_badge
                ]),
                ft.Row([
                    ft.ElevatedButton(
                        "View Submissions",
                        on_click=lambda e, a=assignment: self.view_submissions_dialog(a),
                        icon=ft.Icons.ASSIGNMENT_TURNED_IN
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Edit",
                        on_click=lambda e, a=assignment: self.edit_assignment_dialog(a)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Delete",
                        icon_color=ft.Colors.RED,
                        on_click=lambda e, a=assignment: self.delete_assignment(a)
                    ),
                ], alignment=ft.MainAxisAlignment.END, spacing=0),
            ]),
            padding=10,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE),
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100)
        )

    def create_student_assignment_card(self, assignment):
        status = self.get_status(assignment.get('deadline'), assignment['id'])
        time_remaining = self.get_time_remaining(assignment.get('deadline'))
        submission = self.get_submission_status(assignment['id'], self.current_student_email)
        
        status_color = {
            "Active": ft.Colors.GREEN,
            "Completed": ft.Colors.BLUE,
            "Overdue": ft.Colors.RED
        }.get(status, ft.Colors.GREY)
        
        drive_folder_id = assignment.get('drive_folder_id')
        drive_folder_name = self.get_folder_name_by_id(drive_folder_id) if drive_folder_id else None
        
        upload_btn = ft.Container()
        
        if drive_folder_id and self.drive_service:
            upload_btn = ft.ElevatedButton(
                "📤 Upload to Drive",
                on_click=lambda e, a=assignment: self.upload_to_drive_dialog(a),
                icon=ft.Icons.CLOUD_UPLOAD,
                bgcolor=ft.Colors.GREEN
            )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(
                        assignment['title'],
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        expand=True
                    ),
                    ft.Container(
                        content=ft.Text(status, size=12, color=ft.Colors.WHITE),
                        bgcolor=status_color,
                        padding=5,
                        border_radius=5
                    ),
                ]),
                ft.Divider(height=1),
                ft.Text(f"Subject: {assignment.get('subject', 'N/A')}", size=14),
                ft.Text(assignment.get('description', 'No description'), size=14, max_lines=3),
                ft.Row([
                    ft.Icon(ft.Icons.ACCESS_TIME, size=16),
                    ft.Text(time_remaining, size=13, italic=True)
                ]),
                ft.Text(f"Max Score: {assignment.get('max_score', 'N/A')}", size=13),
                ft.Row([
                    ft.Icon(ft.Icons.FOLDER_SHARED, size=16, color=ft.Colors.BLUE),
                    ft.Text(f"Submit to: {drive_folder_name}", size=13, color=ft.Colors.BLUE),
                ]) if drive_folder_name else ft.Container(),
                ft.Row([
                    ft.Icon(ft.Icons.ASSIGNMENT, size=16),
                    ft.Text(
                        f"Status: {'Submitted ✓' if submission else 'Not Submitted'}",
                        size=13,
                        color=ft.Colors.GREEN if submission else ft.Colors.ORANGE
                    )
                ]),
                ft.Row([
                    ft.Text(
                        f"Grade: {submission.get('grade', 'Not graded')}" if submission else "",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE
                    ),
                    ft.Text(
                        f"Feedback: {submission.get('feedback', 'No feedback')}" if submission else "",
                        size=12,
                        italic=True,
                        expand=True
                    )
                ]) if submission else ft.Container(),
                ft.Row([
                    upload_btn,
                    ft.ElevatedButton(
                        "Submit Assignment" if not submission else "Resubmit",
                        on_click=lambda e, a=assignment: self.submit_assignment_dialog(a),
                        icon=ft.Icons.UPLOAD,
                        bgcolor=ft.Colors.BLUE if not submission else ft.Colors.ORANGE
                    ) if status != "Overdue" or submission else ft.Text("Deadline passed", color=ft.Colors.RED)
                ], spacing=10)
            ], spacing=5),
            padding=15,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE),
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100)
        )

    def open_drive_folder(self, folder_id):
        if self.drive_service:
            import webbrowser
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            webbrowser.open(url)

    def upload_to_drive_dialog(self, assignment):
        drive_folder_id = assignment.get('drive_folder_id')
        if not drive_folder_id or not self.drive_service:
            self.show_snackbar("No Drive folder linked", ft.Colors.RED)
            return
            
        selected_folder_id = [drive_folder_id]
        folder_display = ft.Text("Root Folder")
        
        def update_folder(fid): 
            selected_folder_id[0] = fid
            folder_display.value = "Selected Subfolder"
            self.page.update()

        folder_selector = ft.Row([
            ft.Text("Target: "), 
            folder_display,
            ft.TextButton("Change", on_click=lambda e: self._create_browse_dialog(drive_folder_id, update_folder))
        ])
        
        upload_status = ft.Text("")
        
        def on_file_picked(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            
            file_path = e.files[0].path
            file_name = e.files[0].name
            
            student_name = self.current_student_email.split('@')[0] if self.current_student_email else "unknown"
            
            upload_status.value = f"Uploading {file_name}..."
            self.page.update()
            
            
            try:
                
                new_filename = f"{student_name}_{file_name}"
                
                target_folder_id = selected_folder_id[0]
                    
                result = self.drive_service.upload_file(file_path, parent_id=target_folder_id, file_name=new_filename)
                
                if result:
                    upload_status.value = f"✅ Uploaded: {new_filename}"
                    self.show_snackbar("File uploaded to Google Drive!", ft.Colors.GREEN)
                    
                    # Create/Update submission record
                    existing = self.get_submission_status(assignment['id'], self.current_student_email)
                    if existing:
                        existing['submitted_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                        existing['file_id'] = result.get('id')
                        existing['file_name'] = new_filename
                        existing['file_link'] = result.get('webViewLink')
                    else:
                        self.submissions.append({
                            'id': str(datetime.datetime.now().timestamp()),
                            'assignment_id': assignment['id'],
                            'student_email': self.current_student_email,
                            'submission_text': "File uploaded via Drive",
                            'submitted_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'grade': None,
                            'feedback': None,
                            'file_id': result.get('id'),
                            'file_name': new_filename,
                            'file_link': result.get('webViewLink')
                        })
                    self.save_json(self.submissions_file, self.submissions)
                    self.display_assignments()
                    
                    
                    if self.notification_service:
                        self.notification_service.notify_submission_received(assignment, student_name)
                    
                    import time
                    time.sleep(1)
                    close_overlay(None)
                else:
                    upload_status.value = "❌ Upload failed"
                    self.show_snackbar("Upload failed", ft.Colors.RED)
            except Exception as ex:
                upload_status.value = f"❌ Error: {str(ex)}"
                self.show_snackbar(f"Error: {str(ex)}", ft.Colors.RED)
            
            self.page.update()
        
        file_picker = ft.FilePicker(on_result=on_file_picked)
        self.page.overlay.append(file_picker)
        self.page.update() 
        
        folder_name = self.get_folder_name_by_id(drive_folder_id)
        
        def close_overlay(e):
            if overlay in self.page.overlay:
                self.page.overlay.remove(overlay)
                self.page.update()
        
        overlay = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"Upload to: {folder_name}", size=20, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_overlay)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Text(f"Assignment: {assignment.get('title')}"),
                    folder_selector,
                    ft.Text("Select a file to upload to the Google Drive folder.", size=14),
                    ft.Text("Select a file to upload to the Google Drive folder.", size=14),
                    ft.ElevatedButton(
                        "Choose File",
                        icon=ft.Icons.FILE_UPLOAD,
                        on_click=lambda e: file_picker.pick_files()
                    ),
                    upload_status,
                    ft.Container(height=10),
                    ft.Row([
                        ft.TextButton("Close", on_click=close_overlay)
                    ], alignment=ft.MainAxisAlignment.END)
                ], spacing=10),
                padding=25,
                bgcolor=ft.Colors.WHITE,
                border_radius=12,
                width=400,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)
        )
        
        self.page.overlay.append(overlay)
        self.page.update()

    def show_notifications_dialog(self):
        if not self.notification_service:
            return
        
        notifications = self.notification_service.get_notifications_for_student(self.current_student_email)
        notifications_list = ft.Column(scroll="auto", spacing=5)
        
        if not notifications:
            notifications_list.controls.append(ft.Text("No notifications", color=ft.Colors.GREY))
        else:
            for n in reversed(notifications[-20:]):  
                is_unread = not n.get('read', False)
                notifications_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.CIRCLE, size=8, 
                                       color=ft.Colors.BLUE if is_unread else ft.Colors.GREY),
                                ft.Text(n.get('title', 'Notification'), 
                                       weight=ft.FontWeight.BOLD if is_unread else ft.FontWeight.NORMAL),
                            ]),
                            ft.Text(n.get('message', ''), size=12),
                            ft.Text(n.get('created_at', ''), size=10, color=ft.Colors.GREY),
                        ]),
                        padding=8,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE) if is_unread else None,
                        border_radius=5,
                        on_click=lambda e, nid=n['id']: self.notification_service.mark_as_read(nid)
                    )
                )
        
        def mark_all_read(e):
            self.notification_service.mark_all_as_read(self.current_student_email)
            self.show_snackbar("All notifications marked as read", ft.Colors.BLUE)
            self.close_dialog(dialog)
            self.display_assignments()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Notifications"),
            content=ft.Container(content=notifications_list, width=400, height=300),
            actions=[
                ft.TextButton("Mark All Read", on_click=mark_all_read),
                ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    
    def open_new_assignment_folder_picker(self, e):
         start_id = self.selected_drive_folder_id or self.lms_root_id or 'root'
         self._create_browse_dialog(start_id, self.update_new_assignment_folder)

    def update_new_assignment_folder(self, fid):
         self.selected_drive_folder_id = fid
         name = self.get_folder_name_by_id(fid)
         
         if name == "Linked Folder" and self.drive_service:
             try:
                 info = self.drive_service.get_file_info(fid)
                 if info: name = info.get('name', name)
             except: pass
         
         self.drive_folder_label.value = f"Selected: {name}"
         self.page.update()

    def add_assignment(self, e):
        title = self.assignment_title.value.strip()
        description = self.assignment_description.value.strip()
        subject = self.subject_dropdown.value
        max_score = self.max_score_field.value.strip()
        drive_folder_id = self.selected_drive_folder_id
        target_for = self.target_dropdown.value or "all"  
        
        if not title:
            self.show_snackbar("Please enter assignment title", ft.Colors.RED)
            return
        
        final_deadline = None
        if self.selected_date_value and self.selected_time_value:
            final_deadline = datetime.datetime.combine(self.selected_date_value, self.selected_time_value)
        elif self.selected_date_value:
            final_deadline = datetime.datetime.combine(self.selected_date_value, datetime.time(23, 59))
        
        new_assignment = {
            'id': str(datetime.datetime.now().timestamp()),
            'title': title,
            'description': description,
            'subject': subject or 'Other',
            'deadline': final_deadline.isoformat() if final_deadline else None,
            'max_score': max_score or '100',
            'attachment': self.selected_attachment["name"],
            'drive_folder_id': drive_folder_id,
            'target_for': target_for,  
            'created': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'status': 'Active'
        }
        
        self.assignments.append(new_assignment)
        self.save_json(self.assignments_file, self.assignments)
        
    
        if self.notification_service and self.students:
            self.notification_service.notify_new_assignment(new_assignment, self.students)
        

        self.assignment_title.value = ""
        self.assignment_description.value = ""
        self.subject_dropdown.value = None
        self.max_score_field.value = ""
        self.selected_deadline_display.value = "No deadline selected"
        self.selected_date_value = None
        self.selected_time_value = None
        self.attachment_text.value = "No file attached"
        self.selected_attachment["path"] = None
        self.selected_attachment["name"] = None
        self.selected_drive_folder_id = None
        self.drive_folder_label.value = "No folder selected"
        
        self.display_assignments()
        self.show_snackbar("Assignment added! Students notified.", ft.Colors.GREEN)

    def delete_assignment(self, assignment):
        
        def confirm(e):
            self.assignments.remove(assignment)
            self.submissions = [s for s in self.submissions if s['assignment_id'] != assignment['id']]
            self.save_json(self.assignments_file, self.assignments)
            self.save_json(self.submissions_file, self.submissions)
            close_overlay(e)
            self.display_assignments()
            self.show_snackbar("Assignment deleted", ft.Colors.ORANGE)
        
        def close_overlay(e):
            if overlay in self.page.overlay:
                self.page.overlay.remove(overlay)
                self.page.update()
        
        overlay = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Confirm Delete", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text(f"Delete '{assignment['title']}'?"),
                    ft.Text("This will also delete all submissions.", size=12, color=ft.Colors.GREY_600),
                    ft.Container(height=10),
                    ft.Row([
                        ft.TextButton("Cancel", on_click=close_overlay),
                        ft.ElevatedButton("Delete", on_click=confirm, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE)
                    ], alignment=ft.MainAxisAlignment.END)
                ], tight=True, spacing=10),
                padding=25,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                width=350,
                shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)
        )
        
        self.page.overlay.append(overlay)
        self.page.update()

    def edit_assignment_dialog(self, assignment):
        
        title_field = ft.TextField(value=assignment['title'], label="Title", width=320)
        desc_field = ft.TextField(value=assignment.get('description', ''), label="Description", multiline=True, min_lines=2, width=320)
        score_field = ft.TextField(value=assignment.get('max_score', '100'), label="Max Score", width=100)
        
        current_fid = [assignment.get('drive_folder_id')]
        
        
        initial_name = "None"
        if current_fid[0]:
            initial_name = self.get_folder_name_by_id(current_fid[0])
            if initial_name == "Linked Folder" and self.drive_service:
                 try:
                     info = self.drive_service.get_file_info(current_fid[0])
                     if info: initial_name = info.get('name', initial_name)
                 except: pass

        folder_label = ft.Text(f"Folder: {initial_name}", size=12, italic=True)
        
        def update_edit_folder(fid):
            current_fid[0] = fid
            name = self.get_folder_name_by_id(fid)
             
            if name == "Linked Folder" and self.drive_service:
                 try:
                     info = self.drive_service.get_file_info(fid)
                     if info: name = info.get('name', name)
                 except: pass
            folder_label.value = f"Selected: {name}"
            self.page.update()

        change_folder_btn = ft.TextButton(
            "Change Folder",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._create_browse_dialog(current_fid[0] or self.lms_root_id or 'root', update_edit_folder)
        )
        
        target_dropdown = ft.Dropdown(
            label="Assign To",
            value=assignment.get('target_for', 'all'),
            options=[
                ft.dropdown.Option("all", "All Students"),
                ft.dropdown.Option("bridging", "Bridging Only"),
                ft.dropdown.Option("regular", "Regular Only"),
            ],
            width=150
        )
        
        def save(e):
            assignment['title'] = title_field.value
            assignment['description'] = desc_field.value
            assignment['max_score'] = score_field.value
            assignment['drive_folder_id'] = current_fid[0]
            assignment['target_for'] = target_dropdown.value
            self.save_json(self.assignments_file, self.assignments)
            close_overlay(e)
            self.display_assignments()
            self.show_snackbar("Assignment updated", ft.Colors.BLUE)
        
        def close_overlay(e):
            if overlay in self.page.overlay:
                self.page.overlay.remove(overlay)
                self.page.update()
        
        overlay = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Edit Assignment", size=20, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_overlay)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    title_field,
                    desc_field,
                    ft.Row([score_field, target_dropdown], spacing=10),
                    ft.Row([folder_label, change_folder_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(height=10),
                    ft.Row([
                        ft.TextButton("Cancel", on_click=close_overlay),
                        ft.ElevatedButton("Save", on_click=save, icon=ft.Icons.SAVE)
                    ], alignment=ft.MainAxisAlignment.END)
                ], spacing=10),
                padding=25,
                bgcolor=ft.Colors.WHITE,
                border_radius=12,
                width=400,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)
        )
        
        self.page.overlay.append(overlay)
        self.page.update()

    
    def submit_assignment_dialog(self, assignment):
        submission_text = ft.TextField(
            hint_text="Submission notes/comments",
            multiline=True,
            min_lines=3,
            width=350
        )
        
        uploaded_file_info = ft.Text("No file attached", size=12, italic=True)
        self.temp_file_path = None
        self.temp_file_name = None
        
        
        
        selected_folder_id = [assignment.get('drive_folder_id')] 
        selected_folder_name = ft.Text("Uploading to: Root Folder", size=12)
        
        def on_folder_chosen(fid):
            selected_folder_id[0] = fid
            selected_folder_name.value = f"Selected Target ID: ...{str(fid)[-6:]}"
            self.page.update()

        change_folder_btn = ft.TextButton(
            "Change Folder", 
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._create_browse_dialog(assignment.get('drive_folder_id'), on_folder_chosen),
            visible=bool(assignment.get('drive_folder_id'))
        )
        
        def on_file_picked(e: ft.FilePickerResultEvent):
            if e.files:
                self.temp_file_path = e.files[0].path
                self.temp_file_name = e.files[0].name
                uploaded_file_info.value = f"📎 Attached: {self.temp_file_name}"
                self.page.update()
        
        file_picker = ft.FilePicker(on_result=on_file_picked)
        self.page.overlay.append(file_picker)
        self.page.update()

        def submit(e):
            existing = self.get_submission_status(assignment['id'], self.current_student_email)
            
            
            sub_data = {
                'submission_text': submission_text.value,
                'submitted_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
            if self.temp_file_path and self.drive_service and assignment.get('drive_folder_id'):
                 try:
                    target_folder_id = selected_folder_id[0]
                        
                    student_name = self.current_student_email.split('@')[0] if self.current_student_email else "unknown"
                    new_filename = f"{student_name}_{self.temp_file_name}"
                    result = self.drive_service.upload_file(
                        self.temp_file_path, 
                        parent_id=target_folder_id, 
                        file_name=new_filename
                    )
                    if result:
                        sub_data['file_id'] = result.get('id')
                        sub_data['file_name'] = new_filename
                        sub_data['file_link'] = result.get('webViewLink')
                        self.show_snackbar("File uploaded successfully", ft.Colors.GREEN)
                 except Exception as ex:
                     self.show_snackbar(f"File upload error: {str(ex)}", ft.Colors.RED)
            
            if existing:
                existing.update(sub_data)
            else:
                new_sub = {
                    'id': str(datetime.datetime.now().timestamp()),
                    'assignment_id': assignment['id'],
                    'student_email': self.current_student_email,
                    'grade': None,
                    'feedback': None
                }
                new_sub.update(sub_data)
                self.submissions.append(new_sub)
            
            self.save_json(self.submissions_file, self.submissions)
            
            if self.notification_service:
                student_name = self.current_student_email.split('@')[0] if self.current_student_email else "Student"
                self.notification_service.notify_submission_received(assignment, student_name)
            
            close_overlay(e)
            self.display_assignments()
            self.show_snackbar("Assignment submitted!", ft.Colors.GREEN)
        
        def close_overlay(e):
            if overlay in self.page.overlay:
                self.page.overlay.remove(overlay)
                self.page.update()
        
        overlay = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"Submit: {assignment['title']}", size=20, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_overlay)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Text("Enter your submission details below:", size=14),
                    ft.Text("Enter your submission details below:", size=14),
                    submission_text,
                    ft.Row([selected_folder_name, change_folder_btn]),
                    ft.Row([
                        ft.ElevatedButton("Attach File", icon=ft.Icons.ATTACH_FILE, on_click=lambda _: file_picker.pick_files()),
                        ft.Container(content=uploaded_file_info, padding=ft.padding.only(left=10))
                    ]),
                    ft.Container(height=10),
                    ft.Row([
                        ft.TextButton("Cancel", on_click=close_overlay),
                        ft.ElevatedButton("Submit", on_click=submit, icon=ft.Icons.SEND)
                    ], alignment=ft.MainAxisAlignment.END)
                ], spacing=10),
                padding=25,
                bgcolor=ft.Colors.WHITE,
                border_radius=12,
                width=450,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)
        )
        
        self.page.overlay.append(overlay)
        self.page.update()

    def view_submissions_dialog(self, assignment):
        print(f"DEBUG: Viewing submissions for {assignment.get('title')}")
        try:
            submissions_list = ft.Column(scroll="auto", spacing=10)
            
            target = assignment.get('target_for', 'all')
            if target == 'bridging':
                target_students = self._get_bridging_students()
            elif target == 'regular':
                target_students = self._get_regular_students()
            else:
                target_students = self.students
                
            if not target_students:
                 submissions_list.controls.append(ft.Text("No students enrolled for this assignment type", color=ft.Colors.GREY))
            
            submitted_count = 0
        
            for student in target_students:
                sub = next((s for s in self.submissions 
                           if s['assignment_id'] == assignment['id'] and s['student_email'] == student['email']), None)
                
                student_name = student['name']
                
                if sub:
                    submitted_count += 1
                    status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN)
                    status_text = f"Submitted: {sub['submitted_at']}"
                    
                    grade_field = ft.TextField(
                        value=sub.get('grade', ''),
                        label="Grade",
                        width=100
                    )
                    feedback_field = ft.TextField(
                        value=sub.get('feedback', ''),
                        label="Feedback",
                        multiline=True,
                        expand=True
                    )
                    
                    def save_grade(e, s=sub, g=grade_field, f=feedback_field):
                        s['grade'] = g.value
                        s['feedback'] = f.value
                        self.save_json(self.submissions_file, self.submissions)
                        
                        
                        if self.notification_service and g.value:
                            self.notification_service.notify_grade_posted(assignment, s['student_email'], g.value)
                        
                        self.show_snackbar("Grade saved", ft.Colors.BLUE)
                    
                    
                    file_link_btn = ft.Container()
                    if sub.get('file_link'):
                        file_link_btn = ft.TextButton(
                            "Open File", 
                            icon=ft.Icons.OPEN_IN_NEW, 
                            on_click=lambda e, link=sub['file_link']: self.open_link(link)
                        )
                    elif sub.get('file_id') and self.drive_service:
                         file_link_btn = ft.TextButton(
                            "Open File",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e, fid=sub['file_id']: self.open_drive_file(fid)
                         )

                    card_content = ft.Column([
                        ft.Row([
                            status_icon,
                            ft.Text(f"{student_name} ({student['email']})", weight=ft.FontWeight.BOLD),
                        ]),
                        ft.Text(status_text, size=12, color=ft.Colors.GREEN),
                        ft.Text(f"Notes: {sub.get('submission_text', 'No notes')}", size=12),
                        file_link_btn,
                        ft.Divider(),
                        ft.Row([grade_field, feedback_field]),
                        ft.ElevatedButton("Save Grade", on_click=save_grade, icon=ft.Icons.SAVE)
                    ])
                    card_border_color = ft.Colors.GREEN_200
                    card_bg = ft.Colors.GREEN_50
                else:
                    status_icon = ft.Icon(ft.Icons.CANCEL, color=ft.Colors.RED)
                    status_text = "Missing"
                    card_content = ft.Row([
                        status_icon,
                        ft.Text(f"{student_name} ({student['email']})", weight=ft.FontWeight.BOLD),
                        ft.Text(status_text, color=ft.Colors.RED, weight=ft.FontWeight.BOLD)
                    ])
                    card_border_color = ft.Colors.RED_200
                    card_bg = ft.Colors.RED_50

                card = ft.Container(
                    content=card_content,
                    padding=10,
                    border=ft.border.all(1, card_border_color),
                    border_radius=8,
                    bgcolor=card_bg
                )
                submissions_list.controls.append(card)
        except Exception as e:
            print(f"Error viewing submissions: {e}")
            self.show_snackbar(f"Error opening submissions: {e}", ft.Colors.RED)
            return

        self._show_overlay_dialog(submissions_list, f"Submissions: {assignment['title']}", width=600, height=500)

    def open_drive_file(self, file_id):
        import webbrowser
        webbrowser.open(f"https://drive.google.com/file/d/{file_id}/view")
        self.page.update()

    def manage_students_dialog(self, e):
        students_list = ft.Column(scroll="auto", spacing=5)
        name_field = ft.TextField(label="Student Name", width=180)
        email_field = ft.TextField(label="Student Email", width=220)
        bridging_checkbox = ft.Checkbox(label="Bridging", value=False)
        
        def refresh_list():
            students_list.controls.clear()
            for student in self.students:
                bridging_badge = "[B] " if student.get('is_bridging', False) else ""
                students_list.controls.append(
                    ft.Row([
                        ft.Text(f"{bridging_badge}{student['name']} ({student['email']})", expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                            on_click=lambda e, s=student: remove_student(s),
                            tooltip="Remove student"
                        )
                    ])
                )
            self.page.update()
        
        def add_student(e):
            if name_field.value.strip() and email_field.value.strip():
                self.students.append({
                    'name': name_field.value.strip(),
                    'email': email_field.value.strip(),
                    'is_bridging': bridging_checkbox.value
                })
                self.save_json(self.students_file, self.students)
                name_field.value = ""
                email_field.value = ""
                bridging_checkbox.value = False
                refresh_list()
                self.update_student_dropdown()
                self.show_snackbar("Student added", ft.Colors.GREEN)
        
        def remove_student(student):
            self.students.remove(student)
            self.save_json(self.students_file, self.students)
            refresh_list()
            self.update_student_dropdown()
            self.show_snackbar("Student removed", ft.Colors.ORANGE)
        
        refresh_list()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Manage Students"),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([name_field, email_field, bridging_checkbox]),
                    ft.ElevatedButton("Add Student", on_click=add_student, icon=ft.Icons.ADD),
                    ft.Divider(),
                    ft.Row([
                        ft.Text("Current Students:", weight=ft.FontWeight.BOLD),
                        ft.Text("[B] = Bridging Student", size=11, color=ft.Colors.GREY_600)
                    ]),
                    students_list
                ]),
                width=550,
                height=400
            ),
            actions=[ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def show_snackbar(self, message, color=ft.Colors.BLUE):
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def switch_mode(self, e):
        self.current_mode = "student" if self.mode_switch.value else "teacher"
        if self.current_mode == "student":
            self.mode_label.value = "👨‍🎓 Student View"
            self.student_selector_row.visible = True
            if self.form_container:
                self.form_container.visible = False
            if self.manage_students_btn:
                self.manage_students_btn.visible = False
        else:
            self.mode_label.value = "👨‍🏫 Teacher View"
            self.student_selector_row.visible = False
            if self.form_container:
                self.form_container.visible = True
            if self.manage_students_btn:
                self.manage_students_btn.visible = True
        self.display_assignments()
        self.page.update()

    def update_student_dropdown(self):
        options = []
        for s in self.students:
            if s.get('is_bridging', False):
                options.append(ft.dropdown.Option(s['email'], f"[B] {s['name']}"))
            else:
                options.append(ft.dropdown.Option(s['email'], s['name']))
        
        self.student_dropdown.options = options
        
        self.student_dropdown.options.insert(0, ft.dropdown.Option("__register__", "📝 Register New Account"))
        self.page.update()

    def register_student_dialog(self, e=None):
        
        name_field = ft.TextField(label="Your Full Name", autofocus=True, width=300)
        email_field = ft.TextField(label="Your Email (Gmail required)", width=300)
        student_id_field = ft.TextField(label="Student ID (required)", width=300)
        bridging_switch = ft.Switch(label="I am a Bridging Student", value=False)
        error_text = ft.Text("", color=ft.Colors.RED, size=12)
        
        
        overlay_container = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("📝 Student Registration", size=20, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            on_click=lambda e: self._close_registration_overlay(overlay_container)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text("Register to access assignments and submit your work.", size=14),
                    ft.Divider(),
                    name_field,
                    email_field,
                    student_id_field,
                    ft.Container(
                        content=bridging_switch,
                        padding=ft.padding.only(top=10, bottom=5)
                    ),
                    ft.Text("Bridging students are those transferring or taking additional courses.", 
                           size=11, color=ft.Colors.GREY_600, italic=True),
                    error_text,
                    ft.Row([
                        ft.TextButton("Cancel", on_click=lambda e: self._close_registration_overlay(overlay_container)),
                        ft.ElevatedButton(
                            "Register", 
                            icon=ft.Icons.PERSON_ADD,
                            on_click=lambda e: self._do_register(
                                name_field, email_field, student_id_field, 
                                bridging_switch, error_text, overlay_container
                            )
                        )
                    ], alignment=ft.MainAxisAlignment.END)
                ], spacing=10),
                padding=30,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                width=420,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)
        )
        
        self.page.overlay.append(overlay_container)
        self.page.update()
    
    def _close_registration_overlay(self, overlay):
        if overlay in self.page.overlay:
            self.page.overlay.remove(overlay)
            self.page.update()
    
    def _do_register(self, name_field, email_field, student_id_field, bridging_switch, error_text, overlay):
        name = name_field.value.strip() if name_field.value else ""
        email = email_field.value.strip() if email_field.value else ""
        student_id = student_id_field.value.strip() if student_id_field.value else ""
        is_bridging = bridging_switch.value
        
        print(f"DEBUG: Registering - Name: {name}, Email: {email}, Bridging: {is_bridging}")
        
        if not name:
            error_text.value = "Please enter your full name"
            self.page.update()
            return
        
        
        if not student_id:
            error_text.value = "Student ID is required"
            self.page.update()
            return
        
        
        is_valid, error_msg = self._validate_email(email)
        if not is_valid:
            error_text.value = error_msg
            self.page.update()
            return
        
        
        if not email.lower().endswith('@gmail.com'):
            error_text.value = "Only Gmail accounts are accepted"
            self.page.update()
            return
        
        
        if any(s.get('email') == email for s in self.students):
            error_text.value = "This email is already registered"
            self.page.update()
            return
        
        
        new_student = {
            'name': name,
            'email': email,
            'student_id': student_id if student_id else None,
            'is_bridging': is_bridging,
            'registered_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
        
        self.students.append(new_student)
        self.save_json(self.students_file, self.students)
        
        student_type = "Bridging Student" if is_bridging else "Regular Student"
        print(f"DEBUG: {student_type} saved to students.json")
        
        
        self._close_registration_overlay(overlay)
        
        
        
        self.update_student_dropdown()
        self.student_dropdown.value = email
        self.current_student_email = email
        
        self.display_assignments()
        self.show_snackbar(f"Welcome, {name}! Registered as {student_type}.", ft.Colors.GREEN)

    def on_student_selected(self, e):
        if self.student_dropdown.value == "__register__":
            self.student_dropdown.value = None
            self.register_student_dialog()
            return
        self.current_student_email = self.student_dropdown.value
        self.display_assignments()

    def get_view(self):
        
        
        self.display_assignments()
        
        attach_btn = ft.ElevatedButton(
            "📎 Attach File",
            on_click=self.pick_file,
            icon=ft.Icons.ATTACH_FILE
        )
        
        pick_deadline_btn = ft.ElevatedButton(
            "📅 Set Deadline",
            on_click=lambda e: self.page.open(self.date_picker),
            icon=ft.Icons.CALENDAR_MONTH
        )
        
        add_btn = ft.ElevatedButton(
            "➕ Add Assignment",
            on_click=self.add_assignment,
            icon=ft.Icons.ADD,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
        )
        
        self.form_container = ft.Container(
            content=ft.Column([
                ft.Text("Create New Assignment", size=20, weight=ft.FontWeight.BOLD),
                self.assignment_title,
                ft.Row([self.subject_dropdown, self.max_score_field, self.target_dropdown]),
                self.assignment_description,
                self.assignment_description,
                ft.Row([
                    ft.Text("Link to Drive:", size=14), 
                    self.drive_folder_label,
                    ft.IconButton(
                        ft.Icons.FOLDER_OPEN, 
                        tooltip="Select Drive Folder",
                        on_click=self.open_new_assignment_folder_picker
                    )
                ], spacing=10),
                ft.Row([attach_btn, self.attachment_text], spacing=10),
                ft.Row([pick_deadline_btn, self.selected_deadline_display], spacing=10),
                ft.Container(height=10),
                add_btn,
            ], spacing=10),
            padding=20,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY),
            visible=self.current_mode == "teacher"
        )
        
        back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            on_click=lambda e: self.on_back() if self.on_back else None,
            tooltip="Back to Dashboard"
        ) if self.on_back else ft.Container()
        
        self.manage_students_btn = ft.ElevatedButton(
            "👥 Manage Students",
            on_click=self.manage_students_dialog,
            icon=ft.Icons.PEOPLE,
            visible=self.current_mode == "teacher"
        )
        
        return ft.Column([
            ft.Container(
                content=ft.Row([
                    back_btn,
                    ft.Icon(ft.Icons.SCHOOL, size=40, color=ft.Colors.BLUE),
                    ft.Text("Learning Management System", size=28, weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.START),
                padding=20
            ),
            
            ft.Container(
                content=ft.Row([
                    self.mode_label,
                    self.mode_switch,
                    self.settings_btn,
                    ft.Container(expand=True),
                    self.manage_students_btn
                ]),
                padding=10,
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE),
                border_radius=10
            ),
            
            self.student_selector_row,
            
            self.form_container,
            
            ft.Divider(height=20),
            
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Assignments", size=20, weight=ft.FontWeight.BOLD, expand=True),
                        self.filter_dropdown
                    ]),
                    ft.Container(content=self.assignment_column, expand=True)
                ], spacing=10),
                expand=True
            )
        ], 
        expand=True,
        scroll="auto")
