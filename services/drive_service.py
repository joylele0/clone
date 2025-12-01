from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from datetime import datetime
import os

class DriveService:
    """Handles all Google Drive file and folder operations"""
    
    def __init__(self, service):
        self.service = service
    
    def list_files(self, folder_id='root', page_size=100, page_token=None):
        """
        List files in a folder
        Args:
            folder_id: The folder ID (default: 'root')
            page_size: Number of files to return (max 1000)
            page_token: Token for pagination
        Returns:
            dict with 'files' and 'nextPageToken'
        """
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, owners)",
                orderBy="folder,name"
            ).execute()
            
            return {
                'files': results.get('files', []),
                'nextPageToken': results.get('nextPageToken', None)
            }
        except HttpError as error:
            print(f"An error occurred: {error}")
            return {'files': [], 'nextPageToken': None}
    
    def search_files(self, query_text, folder_id=None):
        """
        Search for files by name
        Args:
            query_text: Text to search for
            folder_id: Optional folder to limit search
        Returns:
            list of files
        """
        try:
            query = f"name contains '{query_text}' and trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=50,
                fields="files(id, name, mimeType, modifiedTime, parents)"
            ).execute()
            
            return results.get('files', [])
        except HttpError as error:
            print(f"Search error: {error}")
            return []
    
    def get_file_info(self, file_id):
        """Get detailed information about a file"""
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, owners, parents, webViewLink"
            ).execute()
            return file
        except HttpError as error:
            print(f"Error getting file info: {error}")
            return None
    
    def create_folder(self, folder_name, parent_id='root'):
        """
        Create a new folder
        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID
        Returns:
            Created folder metadata or None
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()
            return folder
        except HttpError as error:
            print(f"Error creating folder: {error}")
            return None
    
    def upload_file(self, file_path, parent_id='root'):
        """
        Upload a file to Google Drive
        Args:
            file_path: Path to the file to upload
            parent_id: Parent folder ID (default: 'root')
        Returns:
            Uploaded file metadata or None
        """
        try:
            file_name = os.path.basename(file_path)
            file_metadata = {
                'name': file_name,
                'parents': [parent_id]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, size'
            ).execute()
            
            return file
        except HttpError as error:
            print(f"Error uploading file: {error}")
            return None
        except Exception as error:
            print(f"Error uploading file: {error}")
            return None
    
    def move_file(self, file_id, new_parent_id):
        """
        Move a file to a different folder
        Args:
            file_id: ID of the file to move
            new_parent_id: ID of the destination folder
        Returns:
            Updated file metadata or None
        """
        try:
            # Get current parents
            file = self.service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move the file
            updated_file = self.service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            return updated_file
        except HttpError as error:
            print(f"Error moving file: {error}")
            return None
    
    def rename_file(self, file_id, new_name):
        """
        Rename a file
        Args:
            file_id: ID of the file
            new_name: New name for the file
        Returns:
            Updated file metadata or None
        """
        try:
            file_metadata = {'name': new_name}
            updated_file = self.service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id, name'
            ).execute()
            return updated_file
        except HttpError as error:
            print(f"Error renaming file: {error}")
            return None
    
    def delete_file(self, file_id):
        """
        Delete a file (move to trash)
        Args:
            file_id: ID of the file to delete
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except HttpError as error:
            print(f"Error deleting file: {error}")
            return False
    
    def get_folder_tree(self, folder_id='root', max_depth=2, current_depth=0):
        """
        Get folder structure as a tree
        Args:
            folder_id: Starting folder ID
            max_depth: Maximum depth to traverse
            current_depth: Current depth (for recursion)
        Returns:
            Folder tree structure
        """
        if current_depth >= max_depth:
            return None
        
        try:
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name)",
                orderBy="name"
            ).execute()
            
            folders = results.get('files', [])
            
            # Recursively get subfolders
            for folder in folders:
                folder['children'] = self.get_folder_tree(
                    folder['id'], 
                    max_depth, 
                    current_depth + 1
                )
            
            return folders
        except HttpError as error:
            print(f"Error getting folder tree: {error}")
            return []