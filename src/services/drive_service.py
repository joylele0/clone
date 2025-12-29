from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime, timedelta
from functools import lru_cache
import time
import io
from utils.common import extract_drive_id, format_file_size


class DriveService:
    
    def __init__(self, service, cache_ttl=300, max_retries=3):
        self.service = service
        self._cache = {}
        self._cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.retry_delay = 1
        self._setup_lru_caches()
    
    def _setup_lru_caches(self):
        @lru_cache(maxsize=128)
        def cached_get_file_info(file_id):
            return self.get_file_info(file_id, use_cache=False)
        self._cached_get_file_info = cached_get_file_info
    
    def _get_cached(self, key):
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._cache_ttl):
                return data
            del self._cache[key]
        return None
    
    def _set_cache(self, key, data):
        self._cache[key] = (data, datetime.now())
    
    def _invalidate_cache(self, folder_id=None):
        if folder_id:
            keys_to_remove = [k for k in self._cache.keys() if folder_id in k]
            for key in keys_to_remove:
                del self._cache[key]
            if hasattr(self, '_cached_get_file_info'):
                try:
                    self._cached_get_file_info.cache_clear()
                except:
                    pass
        else:
            self._cache.clear()
            if hasattr(self, '_cached_get_file_info'):
                self._cached_get_file_info.cache_clear()
    
    def _retry_request(self, request_func, operation_name="operation"):
        for attempt in range(self.max_retries):
            try:
                return request_func()
            except (TimeoutError, HttpError, Exception) as error:
                should_retry = (
                    isinstance(error, TimeoutError) or
                    (isinstance(error, HttpError) and error.resp.status in [429, 500, 503]) or
                    (not isinstance(error, HttpError) and attempt < self.max_retries - 1)
                )
                
                if should_retry and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"Error on {operation_name} (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"Final error on {operation_name}: {error}")
                    return None
        return None
    
    def _execute_file_list_query(self, query, page_size=100, page_token=None, fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, owners)", order_by="folder,name"):
        def make_request():
            return self.service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields=fields,
                orderBy=order_by
            ).execute()
        
        return self._retry_request(make_request, f"list_query({query[:50]})")
    
    def list_files(self, folder_id='root', page_size=100, page_token=None, use_cache=True):
        cache_key = f"files_{folder_id}_{page_size}_{page_token}"
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                print(f"Cache hit for {cache_key}")
                return cached
        
        query = f"'{folder_id}' in parents and trashed=false"
        result = self._execute_file_list_query(query, page_size, page_token)
        
        if result is not None:
            formatted_result = {
                'files': result.get('files', []),
                'nextPageToken': result.get('nextPageToken', None)
            }
            self._set_cache(cache_key, formatted_result)
            return formatted_result
        
        return None
    
    def search_files(self, query_text, folder_id=None, use_cache=False):
        cache_key = f"search_{query_text}_{folder_id}"
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached
        
        query = f"name contains '{query_text}' and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        result = self._execute_file_list_query(query, page_size=50, fields="files(id, name, mimeType, modifiedTime, parents)")
        files = result.get('files', []) if result else []
        
        if use_cache and files:
            self._set_cache(cache_key, files)
        
        return files
    
    def get_file_info(self, file_id, use_cache=True):
        if use_cache and hasattr(self, '_cached_get_file_info'):
            try:
                return self._cached_get_file_info(file_id)
            except:
                pass
        
        cache_key = f"fileinfo_{file_id}"
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached
        
        def make_request():
            return self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, owners, parents, webViewLink"
            ).execute()
        
        file = self._retry_request(make_request, f"get_file_info({file_id})")
        
        if file is not None:
            self._set_cache(cache_key, file)
        
        return file

    def resolve_drive_link(self, link):
        file_id = extract_drive_id(link)
        
        if not file_id:
            print(f"Could not extract file ID from link: {link}")
            return None, None
        
        info = self.get_file_info(file_id)
        
        if not info:
            print(f"Could not retrieve file info for ID: {file_id}")
            return None, None
        
        return file_id, info
    
    def _execute_file_mutation(self, operation_name, request_func, parent_id=None):
        result = self._retry_request(request_func, operation_name)
        
        if result and parent_id:
            self._invalidate_cache(parent_id)
        
        return result
    
    def create_folder(self, folder_name, parent_id='root'):
        def make_request():
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            return self.service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()
        
        return self._execute_file_mutation(f"create_folder({folder_name})", make_request, parent_id)
    
    def upload_file(self, file_path, parent_id='root', file_name=None, progress_callback=None):
        try:
            if not file_name:
                import os
                file_name = os.path.basename(file_path)
                
            file_metadata = {
                'name': file_name,
                'parents': [parent_id]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, size, webViewLink, parents'
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.resumable_progress, status.total_size)
            
            self._invalidate_cache(parent_id)
            
            return response
            
        except Exception as error:
            print(f"Error uploading file: {error}")
            return None
    
    def update_file(self, file_id, file_path, new_name=None):
        try:
            file_metadata = {}
            if new_name:
                file_metadata['name'] = new_name
            
            media = MediaFileUpload(file_path, resumable=True)
            
            updated_file = self.service.files().update(
                fileId=file_id,
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, modifiedTime'
            ).execute()
            
            self._invalidate_cache(file_id)
            return updated_file
        except Exception as error:
            print(f"Error updating file: {error}")
            return None

    def read_file_content(self, file_id):
        try:
            request = self.service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                done = downloader.next_chunk()
            
            return file.getvalue().decode('utf-8')
        except Exception as error:
            print(f"Error reading file content: {error}")
            return None

    def find_file(self, name, parent_id):
        query = f"name = '{name}' and '{parent_id}' in parents and trashed=false"
        results = self.service.files().list(
            q=query,
            pageSize=1,
            fields="files(id, name, mimeType, modifiedTime)"
        ).execute()
        files = results.get('files', [])
        return files[0] if files else None

    def move_file(self, file_id, new_parent_id):
        def make_request():
            file = self.service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            return self.service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
        
        updated_file = self._retry_request(make_request, f"move_file({file_id})")
        
        if updated_file:
            file = self.service.files().get(fileId=file_id, fields='parents').execute()
            for parent in file.get('parents', []):
                self._invalidate_cache(parent)
            self._invalidate_cache(new_parent_id)
        
        return updated_file
    
    def rename_file(self, file_id, new_name):
        def make_request():
            file_metadata = {'name': new_name}
            return self.service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id, name, parents'
            ).execute()
        
        updated_file = self._retry_request(make_request, f"rename_file({file_id})")
        
        if updated_file:
            for parent in updated_file.get('parents', []):
                self._invalidate_cache(parent)
            self._invalidate_cache(file_id)
        
        return updated_file
    
    def delete_file(self, file_id):
        file_info = self.get_file_info(file_id, use_cache=False)
        
        def make_request():
            self.service.files().delete(fileId=file_id).execute()
            return True
        
        success = self._retry_request(make_request, f"delete_file({file_id})")
        
        if success:
            if file_info and 'parents' in file_info:
                for parent in file_info['parents']:
                    self._invalidate_cache(parent)
            self._invalidate_cache(file_id)
            return True
        
        return False
    
    def get_folder_tree(self, folder_id='root', max_depth=2, current_depth=0):
        if current_depth >= max_depth:
            return None
        
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        result = self._execute_file_list_query(query, page_size=100, fields="files(id, name)", order_by="name")
        folders = result.get('files', []) if result else []
        
        for folder in folders:
            folder['children'] = self.get_folder_tree(
                folder['id'], 
                max_depth, 
                current_depth + 1
            )
        
        return folders