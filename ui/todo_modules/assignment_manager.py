import flet as ft
import datetime


class AssignmentManager:
    
    
    def __init__(self, todo_view):
        self.todo = todo_view
        
        try:
            from services.file_preview_service import FilePreviewService
            self.file_preview = FilePreviewService(todo_view.page, todo_view.drive_service)
        except ImportError:
            self.file_preview = None
    
    def add_assignment(self, e):
        title = self.todo.assignment_title.value.strip() if self.todo.assignment_title.value else ""
        description = self.todo.assignment_description.value.strip() if self.todo.assignment_description.value else ""
        subject = self.todo.subject_dropdown.value
        max_score = self.todo.max_score_field.value.strip() if self.todo.max_score_field.value else ""
        drive_folder_id = self.todo.selected_drive_folder_id
        target_for = self.todo.target_dropdown.value or "all"
        
        if not title:
            self.todo.show_snackbar("Please enter assignment title", ft.Colors.RED)
            return
        
        
        final_deadline = None
        if self.todo.selected_date_value and self.todo.selected_time_value:
            final_deadline = datetime.datetime.combine(
                self.todo.selected_date_value,
                self.todo.selected_time_value
            )
        elif self.todo.selected_date_value:
            final_deadline = datetime.datetime.combine(
                self.todo.selected_date_value,
                datetime.time(23, 59)
            )
        
        new_assignment = {
            'id': str(datetime.datetime.now().timestamp()),
            'title': title,
            'description': description,
            'subject': subject or 'Other',
            'deadline': final_deadline.isoformat() if final_deadline else None,
            'max_score': max_score or '100',
            'attachment': self.todo.selected_attachment["name"],
            'attachment_file_id': None,
            'attachment_file_link': None,
            'drive_folder_id': drive_folder_id,
            'target_for': target_for,
            'created': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'status': 'Active'
        }
        
        if self.todo.selected_attachment["path"] and self.todo.drive_service and self.todo.data_manager.lms_root_id:
            try:
                self.todo.show_snackbar("Uploading attachment to LMS storage...", ft.Colors.BLUE)
                self.todo.page.update()
                
                result = self.todo.drive_service.upload_file(
                    self.todo.selected_attachment["path"],
                    parent_id=self.todo.data_manager.lms_root_id,
                    file_name=f"ATTACHMENT_{self.todo.selected_attachment['name']}"
                )
                
                if result:
                    new_assignment['attachment_file_id'] = result.get('id')
                    new_assignment['attachment_file_link'] = result.get('webViewLink')
                    self.todo.show_snackbar("Attachment uploaded successfully!", ft.Colors.GREEN)
                else:
                    self.todo.show_snackbar("Warning: Attachment upload failed", ft.Colors.ORANGE)
            except Exception as ex:
                self.todo.show_snackbar(f"Attachment upload error: {str(ex)}", ft.Colors.ORANGE)
        elif self.todo.selected_attachment["path"] and not self.todo.data_manager.lms_root_id:
            self.todo.show_snackbar("Warning: No LMS storage folder configured. Attachment not uploaded.", ft.Colors.ORANGE)
        
        self.todo.assignments.append(new_assignment)
        self.todo.data_manager.save_assignments(self.todo.assignments)
        
        
        if self.todo.notification_service and self.todo.students:
            self.todo.notification_service.notify_new_assignment(new_assignment, self.todo.students)
        
        
        self._reset_form()
        
        self.todo.display_assignments()
        self.todo.show_snackbar("Assignment added! Students notified.", ft.Colors.GREEN)
    
    def _reset_form(self):
        
        self.todo.assignment_title.value = ""
        self.todo.assignment_description.value = ""
        self.todo.subject_dropdown.value = None
        self.todo.max_score_field.value = ""
        self.todo.selected_deadline_display.value = "No deadline selected"
        self.todo.selected_date_value = None
        self.todo.selected_time_value = None
        self.todo.attachment_text.value = "No file attached"
        self.todo.selected_attachment["path"] = None
        self.todo.selected_attachment["name"] = None
        self.todo.selected_drive_folder_id = None
        self.todo.drive_folder_label.value = "No folder selected"
    
    def display_teacher_view(self):
        
        filtered = self.todo.assignments
        if self.todo.filter_dropdown.value != "All":
            filtered = [a for a in self.todo.assignments 
                       if self.get_status(a.get('deadline')) == self.todo.filter_dropdown.value]
        
        if not filtered:
            self.todo.assignment_column.controls.append(
                ft.Container(
                    content=ft.Text("No assignments found", size=16, color=ft.Colors.GREY),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for assignment in filtered:
                card = self.create_teacher_assignment_card(assignment)
                self.todo.assignment_column.controls.append(card)
    
    def display_student_view(self):
        
        if self.todo.notification_service and self.todo.current_student_email:
            unread_count = self.todo.notification_service.get_unread_count(self.todo.current_student_email)
            if unread_count > 0:
                self.todo.assignment_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ft.Colors.ORANGE),
                            ft.Text(f"You have {unread_count} new notification(s)", 
                                   size=14, color=ft.Colors.ORANGE),
                            ft.TextButton("View All", 
                                         on_click=lambda e: self.show_notifications_dialog())
                        ]),
                        padding=10,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.ORANGE),
                        border_radius=8
                    )
                )
        
        if not self.todo.current_student_email:
            self.todo.assignment_column.controls.append(
                ft.Text("Please select a student from the dropdown", size=16, color=ft.Colors.RED)
            )
            return
        
        
        current_student = next((s for s in self.todo.students 
                               if s.get('email') == self.todo.current_student_email), None)
        is_bridging = current_student.get('is_bridging', False) if current_student else False
        
        
        filtered = []
        for a in self.todo.assignments:
            target = a.get('target_for', 'all')
            if target == 'all':
                filtered.append(a)
            elif target == 'bridging' and is_bridging:
                filtered.append(a)
            elif target == 'regular' and not is_bridging:
                filtered.append(a)
        
        
        if self.todo.filter_dropdown.value != "All":
            filtered = [a for a in filtered 
                       if self.get_status(a.get('deadline'), a['id']) == self.todo.filter_dropdown.value]
        
        if not filtered:
            self.todo.assignment_column.controls.append(
                ft.Container(
                    content=ft.Text("No assignments found", size=16, color=ft.Colors.GREY),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for assignment in filtered:
                card = self.create_student_assignment_card(assignment)
                self.todo.assignment_column.controls.append(card)
    
    def create_teacher_assignment_card(self, assignment):
        
        status = self.get_status(assignment.get('deadline'))
        time_remaining = self.get_time_remaining(assignment.get('deadline'))
        submission_count = self.get_submission_count(assignment['id'])
        total_students = len(self.todo.students)
        
        status_color = {
            "Active": ft.Colors.GREEN,
            "Completed": ft.Colors.BLUE,
            "Overdue": ft.Colors.RED
        }.get(status, ft.Colors.GREY)
        
        
        drive_folder_id = assignment.get('drive_folder_id')
        drive_folder_name = self.todo.get_folder_name_by_id(drive_folder_id) if drive_folder_id else None
        
        drive_row = ft.Row([
            ft.Icon(ft.Icons.FOLDER_SHARED, size=16, color=ft.Colors.BLUE),
            ft.Text(f"Drive: {drive_folder_name}", size=13, color=ft.Colors.BLUE),
            ft.IconButton(
                icon=ft.Icons.OPEN_IN_NEW,
                icon_size=16,
                tooltip="Open in Drive",
                on_click=lambda e, fid=drive_folder_id: self.open_drive_folder(fid)
            ) if self.todo.drive_service else ft.Container()
        ]) if drive_folder_name else ft.Container()
        
    
        attachment_row = ft.Container()
        if assignment.get('attachment'):
            attachment_controls = [
                ft.Icon(ft.Icons.ATTACH_FILE, size=16, color=ft.Colors.GREY_700),
                ft.Text(f"Attachment: {assignment['attachment']}", size=13, color=ft.Colors.GREY_700)
            ]
            
            
            if assignment.get('attachment_file_id') and self.file_preview:
                attachment_controls.append(
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        icon_size=16,
                        tooltip="Preview Attachment",
                        on_click=lambda e, fid=assignment['attachment_file_id'], 
                                fname=assignment['attachment']: self._preview_attachment(fid, fname)
                    )
                )
            
            
            if assignment.get('attachment_file_link'):
                attachment_controls.append(
                    ft.IconButton(
                        icon=ft.Icons.OPEN_IN_NEW,
                        icon_size=16,
                        tooltip="Open in Drive",
                        on_click=lambda e, link=assignment['attachment_file_link']: self._open_link(link)
                    )
                )
            elif assignment.get('attachment_file_id'):
                attachment_controls.append(
                    ft.IconButton(
                        icon=ft.Icons.OPEN_IN_NEW,
                        icon_size=16,
                        tooltip="Open in Drive",
                        on_click=lambda e, fid=assignment['attachment_file_id']: self._open_drive_file(fid)
                    )
                )
            
            attachment_row = ft.Row(attachment_controls)
        
        
        target_for = assignment.get('target_for', 'all')
        target_labels = {'all': 'All Students', 'bridging': 'Bridging Only', 'regular': 'Regular Only'}
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
                    ft.Text(assignment['title'], size=18, weight=ft.FontWeight.BOLD, expand=True),
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
                attachment_row,  
                ft.Row([
                    ft.Icon(ft.Icons.PEOPLE, size=16),
                    ft.Text(f"Submissions: {submission_count}/{total_students}", size=13),
                    target_badge
                ]),
                ft.Row([
                    ft.ElevatedButton(
                        "View Submissions",
                        on_click=lambda e, a=assignment: self.todo.submission_manager.view_submissions_dialog(a),
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
        submission = self.get_submission_status(assignment['id'], self.todo.current_student_email)
        
        status_color = {
            "Active": ft.Colors.GREEN,
            "Completed": ft.Colors.BLUE,
            "Overdue": ft.Colors.RED
        }.get(status, ft.Colors.GREY)
        
        drive_folder_id = assignment.get('drive_folder_id')
        drive_folder_name = self.todo.get_folder_name_by_id(drive_folder_id) if drive_folder_id else None
        
        
        attachment_row = ft.Container()
        if assignment.get('attachment'):
            attachment_controls = [
                ft.Icon(ft.Icons.ATTACH_FILE, size=16, color=ft.Colors.PURPLE),
                ft.Text(f"Attachment: {assignment['attachment']}", size=13, color=ft.Colors.PURPLE, 
                       weight=ft.FontWeight.BOLD)
            ]
            
            if assignment.get('attachment_file_id') and self.file_preview:
                attachment_controls.append(
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        icon_size=18,
                        icon_color=ft.Colors.BLUE,
                        tooltip="Preview Attachment",
                        on_click=lambda e, fid=assignment['attachment_file_id'], 
                                fname=assignment['attachment']: self._preview_attachment(fid, fname)
                    )
                )
            

            if assignment.get('attachment_file_link'):
                attachment_controls.append(
                    ft.IconButton(
                        icon=ft.Icons.DOWNLOAD,
                        icon_size=18,
                        icon_color=ft.Colors.GREEN,
                        tooltip="Download Attachment",
                        on_click=lambda e, link=assignment['attachment_file_link']: self._open_link(link)
                    )
                )
            elif assignment.get('attachment_file_id'):
                attachment_controls.append(
                    ft.IconButton(
                        icon=ft.Icons.DOWNLOAD,
                        icon_size=18,
                        icon_color=ft.Colors.GREEN,
                        tooltip="Download Attachment",
                        on_click=lambda e, fid=assignment['attachment_file_id']: self._open_drive_file(fid)
                    )
                )
            
            attachment_row = ft.Container(
                content=ft.Row(attachment_controls),
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.PURPLE),
                padding=8,
                border_radius=5
            )
        
        upload_btn = ft.Container()
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(assignment['title'], size=18, weight=ft.FontWeight.BOLD, expand=True),
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
                attachment_row,  
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
                    ft.ElevatedButton(
                        "Preview Submission",
                        icon=ft.Icons.VISIBILITY,
                        on_click=lambda e, s=submission: self._preview_submission_file(s)
                    ) if submission and submission.get('file_id') and self.file_preview else ft.Container(),
                    upload_btn,
                    ft.ElevatedButton(
                        "Submit Assignment" if not submission else "Resubmit",
                        on_click=lambda e, a=assignment: self.todo.submission_manager.submit_assignment_dialog(a),
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
    
    
    def get_time_remaining(self, deadline_str):
        
        if not deadline_str:
            return "No deadline"
        try:
            deadline = datetime.datetime.fromisoformat(deadline_str)
            now = datetime.datetime.now()
            remaining = deadline - now
            
            if remaining.total_seconds() <= 0:
                return "Overdue"
            
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
        
        if self.todo.current_mode == "student" and assignment_id and self.todo.current_student_email:
            submission = self.get_submission_status(assignment_id, self.todo.current_student_email)
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
        
        for sub in self.todo.submissions:
            if sub['assignment_id'] == assignment_id and sub['student_email'] == student_email:
                return sub
        return None
    
    def get_submission_count(self, assignment_id):
        
        return sum(1 for sub in self.todo.submissions if sub['assignment_id'] == assignment_id)
    
    def open_drive_folder(self, folder_id):
        
        if self.todo.drive_service:
            import webbrowser
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            webbrowser.open(url)
    
    def _preview_submission_file(self, submission):
        if self.file_preview and submission.get('file_id'):
            file_name = submission.get('file_name', 'Submission')
            self.file_preview.show_preview(file_id=submission['file_id'], file_name=file_name)
    
    def _preview_attachment(self, file_id, file_name):
        if self.file_preview:
            self.file_preview.show_preview(file_id=file_id, file_name=file_name)
    
    def _open_link(self, link):
        import webbrowser
        webbrowser.open(link)
    
    def _open_drive_file(self, file_id):
        import webbrowser
        webbrowser.open(f"https://drive.google.com/file/d/{file_id}/view")
    
    def edit_assignment_dialog(self, assignment):
        
        title_field = ft.TextField(value=assignment['title'], label="Title", width=320)
        desc_field = ft.TextField(
            value=assignment.get('description', ''),
            label="Description",
            multiline=True,
            min_lines=2,
            width=320
        )
        score_field = ft.TextField(value=assignment.get('max_score', '100'), label="Max Score", width=100)
        
        current_fid = [assignment.get('drive_folder_id')]
        initial_name = "None"
        if current_fid[0]:
            initial_name = self.todo.get_folder_name_by_id(current_fid[0])
        
        folder_label = ft.Text(f"Folder: {initial_name}", size=12, italic=True)
        

        current_attachment = {'path': None, 'name': assignment.get('attachment'), 
                             'file_id': assignment.get('attachment_file_id')}
        attachment_display = ft.Text(
            f"Current: {current_attachment['name']}" if current_attachment['name'] else "No attachment",
            size=12, italic=True
        )
        
        def on_file_picked(e: ft.FilePickerResultEvent):
            if e.files:
                current_attachment['path'] = e.files[0].path
                current_attachment['name'] = e.files[0].name
                attachment_display.value = f"New: {e.files[0].name}"
                self.todo.page.update()
        
        file_picker = ft.FilePicker(on_result=on_file_picked)
        self.todo.page.overlay.append(file_picker)
        self.todo.page.update()
        
        change_attachment_btn = ft.TextButton(
            "Change Attachment",
            icon=ft.Icons.ATTACH_FILE,
            on_click=lambda e: file_picker.pick_files()
        )
        
        def update_edit_folder(fid):
            current_fid[0] = fid
            name = self.todo.get_folder_name_by_id(fid)
            folder_label.value = f"Selected: {name}"
            self.todo.page.update()
        
        change_folder_btn = ft.TextButton(
            "Change Folder",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self.todo.storage_manager.create_browse_dialog(
                current_fid[0] or self.todo.data_manager.lms_root_id or 'root',
                update_edit_folder
            )
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
            
            if current_attachment['path'] and self.todo.drive_service and current_fid[0]:
                try:
                    self.todo.show_snackbar("Uploading new attachment...", ft.Colors.BLUE)
                    self.todo.page.update()
                    
                    result = self.todo.drive_service.upload_file(
                        current_attachment['path'],
                        parent_id=current_fid[0],
                        file_name=f"ATTACHMENT_{current_attachment['name']}"
                    )
                    
                    if result:
                        assignment['attachment'] = current_attachment['name']
                        assignment['attachment_file_id'] = result.get('id')
                        assignment['attachment_file_link'] = result.get('webViewLink')
                        self.todo.show_snackbar("Attachment uploaded!", ft.Colors.GREEN)
                except Exception as ex:
                    self.todo.show_snackbar(f"Attachment upload error: {str(ex)}", ft.Colors.ORANGE)
            
            self.todo.data_manager.save_assignments(self.todo.assignments)
            close_overlay(e)
            self.todo.display_assignments()
            self.todo.show_snackbar("Assignment updated", ft.Colors.BLUE)
        
        content = ft.Column([
            title_field,
            desc_field,
            ft.Row([score_field, target_dropdown], spacing=10),
            ft.Row([folder_label, change_folder_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Text("Attachment:", weight=ft.FontWeight.BOLD, size=13),
            ft.Row([attachment_display, change_attachment_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_overlay(e)),
                ft.ElevatedButton("Save", on_click=save, icon=ft.Icons.SAVE)
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=10)
        
        overlay, close_overlay = self.todo.show_overlay(content, "Edit Assignment", width=400)
    
    def delete_assignment(self, assignment):
        
        def confirm(e):
            
            self.todo.assignments = [a for a in self.todo.assignments if a['id'] != assignment['id']]
            self.todo.submissions = [s for s in self.todo.submissions 
                                     if s['assignment_id'] != assignment['id']]
            self.todo.data_manager.save_assignments(self.todo.assignments)
            self.todo.data_manager.save_submissions(self.todo.submissions)
            close_overlay(e)
            self.todo.display_assignments()
            self.todo.show_snackbar("Assignment deleted", ft.Colors.ORANGE)
        
        content = ft.Column([
            ft.Text(f"Delete '{assignment['title']}'?"),
            ft.Text("This will also delete all submissions.", size=12, color=ft.Colors.GREY_600),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_overlay(e)),
                ft.ElevatedButton("Delete", on_click=confirm, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE)
            ], alignment=ft.MainAxisAlignment.END)
        ], tight=True, spacing=10)
        
        overlay, close_overlay = self.todo.show_overlay(content, "Confirm Delete", width=350)
    
    def show_notifications_dialog(self):
        
        if not self.todo.notification_service:
            return
        
        notifications = self.todo.notification_service.get_notifications_for_student(
            self.todo.current_student_email
        )
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
                        on_click=lambda e, nid=n['id']: self.todo.notification_service.mark_as_read(nid)
                    )
                )
        
        def mark_all_read(e):
            self.todo.notification_service.mark_all_as_read(self.todo.current_student_email)
            self.todo.show_snackbar("All notifications marked as read", ft.Colors.BLUE)
            close_overlay(e)
            self.todo.display_assignments()
        
        content = ft.Column([
            ft.Container(content=notifications_list, width=400, height=300),
            ft.Row([
                ft.TextButton("Mark All Read", on_click=mark_all_read),
                ft.TextButton("Close", on_click=lambda e: close_overlay(e))
            ], alignment=ft.MainAxisAlignment.END)
        ])
        
        overlay, close_overlay = self.todo.show_overlay(content, "Notifications", width=450)