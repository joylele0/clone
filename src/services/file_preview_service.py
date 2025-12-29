import flet as ft
import base64
import mimetypes
import io
from googleapiclient.http import MediaIoBaseDownload
from utils.common import show_snackbar


class FilePreviewService:

    def __init__(self, page: ft.Page, drive_service=None):
        self.page = page
        self.drive_service = drive_service
        self.current_overlay = None
    
    def show_preview(self, file_id=None, file_path=None, file_name="File"):
        content_container = ft.Container(
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Loading preview...", size=14)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=700,
            height=500,
            alignment=ft.alignment.center
        )
        
        def close_preview(e):
            if self.current_overlay and self.current_overlay in self.page.overlay:
                self.page.overlay.remove(self.current_overlay)
                self.current_overlay = None
                self.page.update()
        
        self.current_overlay = ft.Container(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.VISIBILITY, size=24, color=ft.Colors.BLUE),
                        ft.Text(file_name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            on_click=close_preview,
                            tooltip="Close preview"
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=1),
                    content_container
                ], tight=True, spacing=10),
                padding=20,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                width=750,
                height=600,
                shadow=ft.BoxShadow(
                    blur_radius=20,
                    color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)
                )
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            on_click=lambda e: None 
        )
        
        self.page.overlay.append(self.current_overlay)
        self.page.update()
        
        
        if file_id and self.drive_service:
            self._load_from_drive(file_id, file_name, content_container, close_preview)
        elif file_path:
            self._load_from_path(file_path, file_name, content_container, close_preview)
        else:
            content_container.content = ft.Column([
                ft.Icon(ft.Icons.ERROR, size=48, color=ft.Colors.RED),
                ft.Text("No file to preview", color=ft.Colors.RED)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            self.page.update()
    
    def _load_from_drive(self, file_id, file_name, container, close_callback):
        
        try:
            
            file_info = self.drive_service.get_file_info(file_id)
            mime_type = file_info.get('mimeType', '')
            
            
            request = self.drive_service.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_buffer.seek(0)
            file_data = file_buffer.read()
            
            
            self._render_preview(file_data, mime_type, file_name, container, file_id, close_callback)
            
        except Exception as e:
            container.content = self._create_error_view(
                f"Error loading file: {str(e)}",
                file_id=file_id
            )
            self.page.update()
    
    def _load_from_path(self, file_path, file_name, container, close_callback):
        
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            self._render_preview(file_data, mime_type, file_name, container, None, close_callback)
            
        except Exception as e:
            container.content = self._create_error_view(f"Error loading file: {str(e)}")
            self.page.update()
    
    def _render_preview(self, file_data, mime_type, file_name, container, file_id=None, close_callback=None):
        
        preview_widget = None
        size_mb = len(file_data) / (1024 * 1024)
        
        
        if mime_type and mime_type.startswith('image/'):
            preview_widget = self._create_image_preview(file_data, size_mb)
        
        
        elif mime_type == 'application/pdf':
            preview_widget = self._create_pdf_preview(file_data, file_name, size_mb, file_id)
        
        
        elif mime_type and mime_type.startswith('text/'):
            preview_widget = self._create_text_preview(file_data, size_mb)
        
        
        elif mime_type in [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]:
            preview_widget = self._create_word_preview(file_data, file_name, size_mb, file_id)
        
        
        elif mime_type in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]:
            preview_widget = self._create_excel_preview(file_data, file_name, size_mb, file_id)
        
        elif mime_type in [
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ]:
            preview_widget = self._create_powerpoint_preview(file_data, file_name, size_mb, file_id)
        
        else:
            preview_widget = self._create_default_preview(file_data, file_name, mime_type, size_mb, file_id)
        
        container.content = ft.Column(
            [preview_widget],
            scroll="auto",
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )
        self.page.update()
    
    def _create_image_preview(self, file_data, size_mb):
        
        base64_data = base64.b64encode(file_data).decode()
        return ft.Column([
            ft.Image(
                src_base64=base64_data,
                fit=ft.ImageFit.CONTAIN,
                width=650,
                height=450,
                border_radius=8
            ),
            ft.Text(f"Size: {size_mb:.2f} MB", size=12, color=ft.Colors.GREY_600)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    def _create_pdf_preview(self, file_data, file_name, size_mb, file_id):
        return ft.Column([
            ft.Icon(ft.Icons.PICTURE_AS_PDF, size=100, color=ft.Colors.RED),
            ft.Text("PDF Document", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Size: {size_mb:.2f} MB", size=14),
            ft.Text("PDF preview is not available in-app", size=12, italic=True, color=ft.Colors.GREY_600),
            ft.Container(height=20),
            ft.Row([
                ft.ElevatedButton(
                    "Download PDF",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e: self._download_file(file_data, file_name)
                ),
                ft.ElevatedButton(
                    "Open in Browser",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda e: self._open_in_browser(file_id),
                    bgcolor=ft.Colors.BLUE
                ) if file_id else ft.Container()
            ], spacing=10)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    
    def _create_text_preview(self, file_data, size_mb):
        try:
            text_content = file_data.decode('utf-8')
            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text(text_content, selectable=True, size=13)
                    ], scroll="auto"),
                    padding=15,
                    bgcolor=ft.Colors.GREY_100,
                    border_radius=8,
                    width=650,
                    height=450,
                    border=ft.border.all(1, ft.Colors.GREY_300)
                ),
                ft.Text(f"Size: {size_mb:.2f} MB | {len(text_content)} characters", 
                       size=12, color=ft.Colors.GREY_600)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        except UnicodeDecodeError:
            return ft.Column([
                ft.Icon(ft.Icons.ERROR, size=48, color=ft.Colors.ORANGE),
                ft.Text("Cannot decode text file", color=ft.Colors.ORANGE),
                ft.Text("File may be binary or use unsupported encoding", size=12, italic=True)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    def _create_word_preview(self, file_data, file_name, size_mb, file_id):
        return ft.Column([
            ft.Icon(ft.Icons.DESCRIPTION, size=100, color=ft.Colors.BLUE),
            ft.Text("Word Document", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Size: {size_mb:.2f} MB", size=14),
            ft.Text("Word preview is not available in-app", size=12, italic=True, color=ft.Colors.GREY_600),
            ft.Text("Download to view full content", size=12, color=ft.Colors.GREY_600),
            ft.Container(height=20),
            ft.Row([
                ft.ElevatedButton(
                    "Download Document",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e: self._download_file(file_data, file_name)
                ),
                ft.ElevatedButton(
                    "Open in Browser",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda e: self._open_in_browser(file_id),
                    bgcolor=ft.Colors.BLUE
                ) if file_id else ft.Container()
            ], spacing=10)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    
    def _create_excel_preview(self, file_data, file_name, size_mb, file_id):
        return ft.Column([
            ft.Icon(ft.Icons.TABLE_CHART, size=100, color=ft.Colors.GREEN),
            ft.Text("Spreadsheet Document", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Size: {size_mb:.2f} MB", size=14),
            ft.Text("Spreadsheet preview is not available in-app", size=12, italic=True, color=ft.Colors.GREY_600),
            ft.Container(height=20),
            ft.Row([
                ft.ElevatedButton(
                    "Download Spreadsheet",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e: self._download_file(file_data, file_name)
                ),
                ft.ElevatedButton(
                    "Open in Browser",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda e: self._open_in_browser(file_id),
                    bgcolor=ft.Colors.GREEN
                ) if file_id else ft.Container()
            ], spacing=10)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    
    def _create_powerpoint_preview(self, file_data, file_name, size_mb, file_id):
        return ft.Column([
            ft.Icon(ft.Icons.SLIDESHOW, size=100, color=ft.Colors.ORANGE),
            ft.Text("Presentation Document", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Size: {size_mb:.2f} MB", size=14),
            ft.Text("Presentation preview is not available in-app", size=12, italic=True, color=ft.Colors.GREY_600),
            ft.Container(height=20),
            ft.Row([
                ft.ElevatedButton(
                    "Download Presentation",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e: self._download_file(file_data, file_name)
                ),
                ft.ElevatedButton(
                    "Open in Browser",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda e: self._open_in_browser(file_id),
                    bgcolor=ft.Colors.ORANGE
                ) if file_id else ft.Container()
            ], spacing=10)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    
    def _create_default_preview(self, file_data, file_name, mime_type, size_mb, file_id):
        ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        icon_map = {
            'zip': (ft.Icons.FOLDER_ZIP, ft.Colors.PURPLE),
            'rar': (ft.Icons.FOLDER_ZIP, ft.Colors.PURPLE),
            '7z': (ft.Icons.FOLDER_ZIP, ft.Colors.PURPLE),
            'mp4': (ft.Icons.VIDEO_FILE, ft.Colors.RED),
            'avi': (ft.Icons.VIDEO_FILE, ft.Colors.RED),
            'mov': (ft.Icons.VIDEO_FILE, ft.Colors.RED),
            'mp3': (ft.Icons.AUDIO_FILE, ft.Colors.BLUE),
            'wav': (ft.Icons.AUDIO_FILE, ft.Colors.BLUE),
            'json': (ft.Icons.DATA_OBJECT, ft.Colors.GREEN),
            'xml': (ft.Icons.CODE, ft.Colors.ORANGE),
            'sql': (ft.Icons.STORAGE, ft.Colors.BLUE),
        }
        
        icon, color = icon_map.get(ext, (ft.Icons.INSERT_DRIVE_FILE, ft.Colors.GREY))
        
        return ft.Column([
            ft.Icon(icon, size=100, color=color),
            ft.Text("File Preview Not Available", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Type: {mime_type or 'Unknown'}", size=14, color=ft.Colors.GREY_700),
            ft.Text(f"Size: {size_mb:.2f} MB", size=14, color=ft.Colors.GREY_700),
            ft.Container(height=20),
            ft.Row([
                ft.ElevatedButton(
                    "Download File",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e: self._download_file(file_data, file_name)
                ),
                ft.ElevatedButton(
                    "Open in Browser",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda e: self._open_in_browser(file_id),
                    bgcolor=ft.Colors.BLUE
                ) if file_id else ft.Container()
            ], spacing=10)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    
    def _create_error_view(self, error_message, file_id=None):
        return ft.Column([
            ft.Icon(ft.Icons.ERROR, size=48, color=ft.Colors.RED),
            ft.Text(error_message, color=ft.Colors.RED, text_align=ft.TextAlign.CENTER),
            ft.Container(height=20),
            ft.ElevatedButton(
                "Open in Browser",
                icon=ft.Icons.OPEN_IN_NEW,
                on_click=lambda e: self._open_in_browser(file_id)
            ) if file_id else ft.Container()
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    def _download_file(self, file_data, file_name):
        try:
            from pathlib import Path
            
            downloads_path = Path.home() / "Downloads" / file_name
            
            counter = 1
            original_path = downloads_path
            while downloads_path.exists():
                name, ext = original_path.stem, original_path.suffix
                downloads_path = original_path.parent / f"{name} ({counter}){ext}"
                counter += 1
            
            with open(downloads_path, 'wb') as f:
                f.write(file_data)
            
            show_snackbar(self.page, f"✓ Downloaded to: {downloads_path.name}", ft.Colors.GREEN)
        except Exception as e:
            show_snackbar(self.page, f"✗ Download failed: {str(e)}", ft.Colors.RED)
    
    def _open_in_browser(self, file_id):
        if file_id:
            import webbrowser
            webbrowser.open(f"https://drive.google.com/file/d/{file_id}/view")
    
    
    def close_preview(self):
        if self.current_overlay and self.current_overlay in self.page.overlay:
            self.page.overlay.remove(self.current_overlay)
            self.current_overlay = None
            self.page.update()