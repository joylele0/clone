import flet as ft
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
        
        self.data_dir = Path("lms_data")
        self.data_dir.mkdir(exist_ok=True)
        
        from ui.todo_modules.data_manager import DataManager
        from ui.todo_modules.storage_manager import StorageManager
        from ui.todo_modules.assignment_manager import AssignmentManager
        from ui.todo_modules.student_manager import StudentManager
        from ui.todo_modules.submission_manager import SubmissionManager
        
        self.data_manager = DataManager(self.data_dir, drive_service)
        self.storage_manager = StorageManager(self, drive_service)
        self.assignment_manager = AssignmentManager(self)
        self.student_manager = StudentManager(self)
        self.submission_manager = SubmissionManager(self)
        
        self.assignments = self.data_manager.load_assignments()
        self.students = self.data_manager.load_students()
        self.submissions = self.data_manager.load_submissions()
        self.saved_links = self.load_saved_links()
        
        try:
            from services.notification_service import NotificationService
            self.notification_service = NotificationService(self.data_dir)
        except ImportError:
            self.notification_service = None
        
        self.current_mode = "teacher"
        self.current_student_email = None
        
        self._init_ui_components()
        
    def _init_ui_components(self):

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
        
        
        self.selected_drive_folder_id = None
        self.drive_folder_label = ft.Text("No folder selected", size=12, italic=True)
        

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
            on_click=lambda e: self.storage_manager.show_storage_settings()
        )
        
        self.student_dropdown = ft.Dropdown(
            hint_text="Select Student",
            width=250,
            on_change=self.on_student_selected
        )
        self.student_manager.update_student_dropdown()
        
        self.student_selector_row = ft.Row([
            ft.Text("Viewing as:", size=14),
            self.student_dropdown
        ], visible=False)
        
        self.form_container = None
        self.manage_students_btn = None
    
    def load_saved_links(self):
        if os.path.exists(SAVED_LINKS_FILE):
            try:
                with open(SAVED_LINKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("links", [])
            except:
                pass
        return []
    
    def get_folder_name_by_id(self, folder_id):
        for link in self.saved_links:
            if link.get("id") == folder_id:
                return link.get("name", folder_id)
        
        if self.drive_service:
            try:
                info = self.drive_service.get_file_info(folder_id)
                if info:
                    return info.get('name', 'Linked Folder')
            except:
                pass
        
        return "Linked Folder"
    
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
    
    def display_assignments(self):
        self.assignment_column.controls.clear()
        
        if self.current_mode == "teacher":
            self.assignment_manager.display_teacher_view()
        else:
            self.assignment_manager.display_student_view()
        
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
    
    def on_student_selected(self, e):
        if self.student_dropdown.value == "__register__":
            self.student_dropdown.value = None
            self.student_manager.register_student_dialog()
            return
        self.current_student_email = self.student_dropdown.value
        self.display_assignments()
    
    
    def show_overlay(self, content, title=None, width=400, height=None):
        def close_overlay(e):
            if overlay in self.page.overlay:
                self.page.overlay.remove(overlay)
                self.page.update()
        
        header_controls = []
        if title:
            header_controls.append(
                ft.Text(
                    title, 
                    size=20, 
                    weight=ft.FontWeight.BOLD,
                    overflow=ft.TextOverflow.VISIBLE,
                    no_wrap=False,
                    expand=True
                )
            )
        
        header_controls.append(ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_overlay))
        
        if height and isinstance(content, ft.Column) and content.scroll:
            content_wrapper = ft.Container(
                content=content,
                expand=True,
                padding=10
            )
        else:
            content_wrapper = content
        
        overlay_content = ft.Column([
            ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            content_wrapper
        ], tight=True, spacing=10, expand=True if height else False)
        
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
            on_click=self.assignment_manager.add_assignment,
            icon=ft.Icons.ADD,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
        )
        
        self.form_container = ft.Container(
            content=ft.Column([
                ft.Text("Create New Assignment", size=20, weight=ft.FontWeight.BOLD),
                self.assignment_title,
                ft.Row([self.subject_dropdown, self.max_score_field, self.target_dropdown]),
                self.assignment_description,
                ft.Row([
                    ft.Text("Link to Drive:", size=14),
                    self.drive_folder_label,
                    ft.IconButton(
                        ft.Icons.FOLDER_OPEN,
                        tooltip="Select Drive Folder",
                        on_click=self.storage_manager.open_new_assignment_folder_picker
                    )
                ], spacing=10),
                ft.Row([attach_btn, self.attachment_text], spacing=10),
                ft.Row([
                    pick_deadline_btn, 
                    ft.Container(
                        content=self.selected_deadline_display,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        border_radius=5,
                    )
                ], spacing=10),
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
            on_click=self.student_manager.manage_students_dialog,
            icon=ft.Icons.PEOPLE,
            visible=self.current_mode == "teacher"
        )
        
        return ft.Column([
            ft.Container(
                content=ft.Row([
                    back_btn,
                    ft.Icon(ft.Icons.SCHOOL, size=40, color=ft.Colors.BLUE),
                    ft.Text("Learning Management System", size=28, weight=ft.FontWeight.BOLD, expand=True, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
                ], alignment=ft.MainAxisAlignment.START),
                padding=20
            ),
            
            ft.Container(
                content=ft.Row([
                    self.mode_label,
                    self.mode_switch,
                    self.settings_btn,
                    ft.Container(expand=True),
                    self.manage_students_btn,
                    
                ]),
                padding=10,
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE),
                border_radius=10,
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