import json
import datetime
import time
from pathlib import Path


try:
    from plyer import notification as os_notification
    PLYER_AVAILABLE = True
    print("✓ plyer loaded - OS notifications enabled")
except ImportError:
    PLYER_AVAILABLE = False
    print("⚠ plyer not installed - OS notifications disabled")
    print("  Install with: pip install plyer")
    print("  Note: OS notifications require desktop environment")


class NotificationService:
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("lms_data")
        self.data_dir.mkdir(exist_ok=True)
        self.notifications_file = self.data_dir / "notifications.json"
        self.notifications = self.load_notifications()
        self.os_notifications_enabled = PLYER_AVAILABLE
    
    def get_notification_status(self):
        return {
            "os_available": PLYER_AVAILABLE,
            "in_app_enabled": True,
            "total_notifications": len(self.notifications),
            "message": "OS notifications enabled" if PLYER_AVAILABLE else "OS notifications unavailable - install plyer"
        }
    
    def load_notifications(self):
        if self.notifications_file.exists():
            try:
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    notifications = data.get("notifications", [])
                    for notif in notifications:
                        if 'read' not in notif:
                            notif['read'] = False
                        if 'id' not in notif:
                            notif['id'] = str(time.time())
                    return notifications
            except Exception as e:
                print(f"Error loading notifications: {e}")
        return []
    
    def save_notifications(self):
        try:
            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                json.dump({"notifications": self.notifications}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving notifications: {e}")
    
    def send_notification(self, title: str, message: str, student_email: str = None, assignment_id: str = None, notification_type: str = "info", show_os_notification: bool = False):
        notification_record = {
            "id": str(time.time()),
            "type": notification_type,
            "title": title,
            "message": message,
            "student_email": student_email,
            "assignment_id": assignment_id,
            "created_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            "read": False
        }
        self.notifications.append(notification_record)
        self.save_notifications()
        
        if show_os_notification and PLYER_AVAILABLE:
            try:
                os_notification.notify(
                    title=title,
                    message=message,
                    app_name="LMS Assignment Manager",
                    timeout=10
                )
                return True
            except Exception as e:
                print(f"OS notification failed: {e}")
        
        return False
    
    def notify_new_assignment(self, assignment: dict, students: list):
        title = f"New Assignment: {assignment.get('title', 'Untitled')}"
        deadline = assignment.get('deadline', 'No deadline')
        if deadline and deadline != 'No deadline':
            try:
                deadline_dt = datetime.datetime.fromisoformat(deadline)
                deadline = deadline_dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                pass
        message = f"Subject: {assignment.get('subject', 'N/A')}\nDeadline: {deadline}"
        
        for i, student in enumerate(students):
            student_email = student.get('email')
            show_os = (i == 0)
            self.send_notification(
                title=title,
                message=message,
                student_email=student_email,
                assignment_id=assignment.get('id'),
                notification_type="new_assignment",
                show_os_notification=show_os
            )
        
        if PLYER_AVAILABLE and len(students) > 0:
            try:
                os_notification.notify(
                    title=title,
                    message=f"{message}\nAssigned to {len(students)} student{'s' if len(students) != 1 else ''}",
                    app_name="LMS Assignment Manager",
                    timeout=10
                )
            except Exception as e:
                print(f"OS notification failed: {e}")
    
    def notify_deadline_reminder(self, assignment: dict, student_email: str, hours_remaining: int):
        title = f"Deadline Reminder: {assignment.get('title', 'Assignment')}"
        message = f"Only {hours_remaining} hours remaining to submit!"
        
        self.send_notification(
            title=title,
            message=message,
            student_email=student_email,
            assignment_id=assignment.get('id'),
            notification_type="deadline_reminder",
            show_os_notification=True
        )
    
    def notify_submission_received(self, assignment: dict, student_name: str):
        title = f"Submission Received"
        message = f"{student_name} submitted: {assignment.get('title', 'Assignment')}"
        
        self.send_notification(
            title=title,
            message=message,
            assignment_id=assignment.get('id'),
            notification_type="submission_received",
            show_os_notification=True
        )
    
    def notify_grade_posted(self, assignment: dict, student_email: str, grade: str):
        title = f"Grade Posted: {assignment.get('title', 'Assignment')}"
        message = f"Your grade: {grade}"
        
        self.send_notification(
            title=title,
            message=message,
            student_email=student_email,
            assignment_id=assignment.get('id'),
            notification_type="grade_posted",
            show_os_notification=True
        )
    
    def get_notifications_for_student(self, student_email: str):
        if not student_email:
            return []
        return [n for n in self.notifications 
                if n.get('student_email') == student_email or n.get('student_email') is None]
    
    def get_unread_count(self, student_email: str = None):
        if student_email:
            relevant = self.get_notifications_for_student(student_email)
        else:
            relevant = self.notifications
        return sum(1 for n in relevant if not n.get('read', False))
    
    def mark_as_read(self, notification_id: str):
        if not notification_id:
            return False
        for n in self.notifications:
            if n.get('id') == notification_id:
                n['read'] = True
                self.save_notifications()
                return True
        return False
    
    def mark_all_as_read(self, student_email: str = None):
        modified = False
        for n in self.notifications:
            if student_email is None or n.get('student_email') == student_email:
                if not n.get('read', False):
                    n['read'] = True
                    modified = True
        if modified:
            self.save_notifications()
    
    def clear_old_notifications(self, days: int = 30):
        try:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            original_count = len(self.notifications)
            self.notifications = [
                n for n in self.notifications
                if datetime.datetime.strptime(n['created_at'], '%Y-%m-%d %H:%M') > cutoff
            ]
            if len(self.notifications) < original_count:
                self.save_notifications()
        except Exception as e:
            print(f"Error clearing old notifications: {e}")