from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta
from functools import lru_cache, wraps
import os
import hashlib
import time
import re


class DriveService:
    
    def __init__(self, service, cache_ttl=300, max_retries=3):
        self.service = service
        self._cache = {}
        self._cache_ttl = cache_ttl  
        self.max_retries = max_retries
        self.retry_delay = 1  
        
        
        self._setup_lru_caches()
    
    def _setup_lru_caches(self):
        
        original_get_info = self.get_file_info
        
        @lru_cache(maxsize=128)
        def cached_get_file_info(file_id):
            return original_get_info(file_id, use_cache=False)
        
        self._cached_get_file_info = cached_get_file_info
    
    def _get_cached(self, key):
        
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._cache_ttl):
                return data
            else:
                
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
            except TimeoutError as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"Timeout on {operation_name} (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"Final timeout on {operation_name} after {self.max_retries} attempts")
                    return None
            except HttpError as error:
              
                if error.resp.status in [429, 500, 503]:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (2 ** attempt)
                        print(f"HTTP {error.resp.status} on {operation_name}, retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"Final HTTP error on {operation_name}: {error}")
                        return None
                else:
                    
                    print(f"HTTP error on {operation_name}: {error}")
                    return None
            except Exception as error:
               
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"Error on {operation_name} (attempt {attempt + 1}/{self.max_retries}): {error}, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"Final error on {operation_name}: {error}")
                    return None
        return None
    
    def list_files(self, folder_id='root', page_size=100, page_token=None, use_cache=True):
        
        cache_key = f"files_{folder_id}_{page_size}_{page_token}"
        
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                print(f"Cache hit for {cache_key}")
                return cached
        
        
        def make_request():
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
        
       
        result = self._retry_request(make_request, f"list_files({folder_id})")
        
        
        if result is not None:
            self._set_cache(cache_key, result)
        
        return result
    
    def search_files(self, query_text, folder_id=None, use_cache=False):
        
        cache_key = f"search_{query_text}_{folder_id}"
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached
        
        def make_request():
            query = f"name contains '{query_text}' and trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=50,
                fields="files(id, name, mimeType, modifiedTime, parents)"
            ).execute()
            
            return results.get('files', [])
        
        files = self._retry_request(make_request, f"search_files({query_text})")
        
        if files is None:
            files = []
        elif use_cache:
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
    
    def extract_id_from_link(self, files):
        
        patterns = [
            r"/folders/([a-zA-Z0-9_-]+)",
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"[?&]id=([a-zA-Z0-9_-]+)"  # Fixed: added [?&] for proper matching
        ]
        
        for file in files:
            print(f"DEBUG: Checking link: {file}")  # Debug
            for pattern in patterns:
                match = re.search(pattern, file)
                if match:
                    extracted_id = match.group(1)
                    print(f"DEBUG: Extracted ID: {extracted_id}")  # Debug
                    return extracted_id
        
        print("DEBUG: No ID found in link")  # Debug
        return None
        

    def resolve_drive_link(self, link):
        
        print(f"DEBUG: resolve_drive_link called with: {link}")  # Debug
        
        file_id = self.extract_id_from_link([link])
        
        if not file_id:
            print(f"Could not extract file ID from link: {link}")
            return None, None
        
        print(f"DEBUG: File ID extracted: {file_id}")  # Debug
        
        info = self.get_file_info(file_id)
        
        if not info:
            print(f"Could not retrieve file info for ID: {file_id}")
            return None, None
        
        print(f"DEBUG: File info retrieved: {info.get('name')}")  # Debug
        return file_id, info


    def batch_get_file_info(self, file_ids):
        
        results = {}
        
        def callback(request_id, response, exception):
            if exception:
                print(f"Error for {request_id}: {exception}")
            else:
                results[request_id] = response
        
        def make_request():
            batch = self.service.new_batch_http_request(callback=callback)
            
            for file_id in file_ids:
                batch.add(
                    self.service.files().get(
                        fileId=file_id,
                        fields="id, name, mimeType, size, modifiedTime"
                    ),
                    request_id=file_id
                )
            
            batch.execute()
            return results
        
        return self._retry_request(make_request, "batch_get_file_info") or {}
    
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
        
        folder = self._retry_request(make_request, f"create_folder({folder_name})")
        
        if folder:
            # Invalidate parent folder cache
            self._invalidate_cache(parent_id)
        
        return folder
    
    def upload_file(self, file_path, parent_id='root', progress_callback=None):
        
        try:
            file_name = os.path.basename(file_path)
            file_metadata = {
                'name': file_name,
                'parents': [parent_id]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, size'
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.resumable_progress, status.total_size)
            
     
            self._invalidate_cache(parent_id)
            
            return response
            
        except HttpError as error:
            print(f"Error uploading file: {error}")
            return None
        except Exception as error:
            print(f"Error uploading file: {error}")
            return None
    
    def move_file(self, file_id, new_parent_id):
        
        def make_request():
            # Get current parents
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
        
        def make_request():
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name)",
                orderBy="name"
            ).execute()
            return results.get('files', [])
        
        folders = self._retry_request(make_request, f"get_folder_tree({folder_id})") or []
        
        # Recursively get subfolders
        for folder in folders:
            folder['children'] = self.get_folder_tree(
                folder['id'], 
                max_depth, 
                current_depth + 1
            )
        
        return folders
    
    def get_cache_stats(self):
        lru_stats = {}
        if hasattr(self, '_cached_get_file_info'):
            cache_info = self._cached_get_file_info.cache_info()
            lru_stats = {
                'hits': cache_info.hits,
                'misses': cache_info.misses,
                'maxsize': cache_info.maxsize,
                'currsize': cache_info.currsize
            }
        
        return {
            'manual_cache_size': len(self._cache),
            'manual_cache_keys': list(self._cache.keys()),
            'lru_cache': lru_stats
        }
    
    @staticmethod
    @lru_cache(maxsize=256)
    def parse_mime_type(mime_type):
        
        if mime_type == 'application/vnd.google-apps.folder':
            return {'category': 'folder', 'icon': 'folder'}
        elif mime_type.startswith('image/'):
            return {'category': 'image', 'icon': 'image'}
        elif mime_type.startswith('video/'):
            return {'category': 'video', 'icon': 'video'}
        elif mime_type.startswith('audio/'):
            return {'category': 'audio', 'icon': 'audio'}
        elif 'document' in mime_type or mime_type.startswith('text/'):
            return {'category': 'document', 'icon': 'document'}
        elif 'spreadsheet' in mime_type or 'excel' in mime_type:
            return {'category': 'spreadsheet', 'icon': 'table'}
        elif 'presentation' in mime_type or 'powerpoint' in mime_type:
            return {'category': 'presentation', 'icon': 'presentation'}
        else:
            return {'category': 'file', 'icon': 'file'}
    
    @staticmethod
    @lru_cache(maxsize=512)
    def format_file_size(size_bytes):
        if size_bytes is None:
            return "Unknown size"
        
        try:
            size = int(size_bytes)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} PB"
        except (ValueError, TypeError):
            return "Unknown size"