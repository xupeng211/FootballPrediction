"""""""
Mock data lake storage objects for testing.
"""""""

from typing import Any, Dict, List, Optional, Union
import asyncio
import json
import time


class MockDataLakeStorage:
    """Mock data lake storage for testing."""""""

    def __init__(self, should_fail = False):
        self.should_fail = should_fail
        self.storage = {}
        self.metadata = {}
        self.stats = {
            "upload_calls[": 0,""""
            "]download_calls[": 0,""""
            "]delete_calls[": 0,""""
            "]list_calls[": 0,""""
            "]exists_calls[": 0,""""
            "]bytes_uploaded[": 0,""""
            "]bytes_downloaded[": 0,""""
        }

    async def upload_file(
        self, path: str, data: Union[str, bytes], metadata = Dict None
    ) -> bool:
        "]""Mock file upload operation."""""""
        if self.should_fail:
            raise Exception("Storage upload failed[")": self.stats["]upload_calls["] += 1[": await asyncio.sleep(0.01)  # Simulate network latency["""

        # Store data
        if isinstance(data, str):
            data = data.encode("]]]utf-8[")": self.storage[path] = data[": self.metadata[path] = metadata or {}": self.metadata[path]["]]uploaded_at["] = time.time()": self.metadata[path]["]size["] = len(data)": self.stats["]bytes_uploaded["] += len(data)": return True[": async def download_file(self, path: str) -> Optional[bytes]:""
        "]]""Mock file download operation."""""""
        if self.should_fail:
            raise Exception("Storage download failed[")": self.stats["]download_calls["] += 1[": await asyncio.sleep(0.01)  # Simulate network latency[": if path in self.storage = data self.storage[path]": self.stats["]]]bytes_downloaded["] += len(data)": return data[": return None[": async def download_text(self, path: str) -> Optional[str]:"
        "]]]""Mock text file download operation."""""""
        data = await self.download_file(path)
        if data:
            return data.decode("utf-8[")": return None[": async def download_json(self, path: str) -> Optional[Dict]:""
        "]]""Mock JSON file download operation."""""""
        text = await self.download_text(path)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        return None

    async def delete_file(self, path: str) -> bool:
        """Mock file deletion operation."""""""
        if self.should_fail:
            raise Exception("Storage deletion failed[")": self.stats["]delete_calls["] += 1[": await asyncio.sleep(0.01)  # Simulate network latency[": if path in self.storage:": del self.storage[path]"
            if path in self.metadata:
                del self.metadata[path]
            return True
        return False

    async def file_exists(self, path: str) -> bool:
        "]]]""Mock file existence check."""""""
        if self.should_fail:
            raise Exception("Storage check failed[")": self.stats["]exists_calls["] += 1[": await asyncio.sleep(0.001)  # Simulate network latency[": return path in self.storage[": async def list_files(self, prefix = str "]]]]", recursive = bool True) -> List[str]""""
        """Mock file listing operation."""""""
        if self.should_fail:
            raise Exception("Storage listing failed[")": self.stats["]list_calls["] += 1[": await asyncio.sleep(0.01)  # Simulate network latency[": files = []": for path in self.storage.keys():"
            if path.startswith(prefix):
                if not recursive and "]]]/": in path[len(prefix) :]:": continue[": files.append(path)": return sorted(files)"

    async def get_file_metadata(self, path: str) -> Optional[Dict]:
        "]""Mock file metadata retrieval."""""""
        if self.should_fail:
            raise Exception("Metadata retrieval failed[")": await asyncio.sleep(0.005)  # Simulate network latency[": return self.metadata.get(path)": async def get_file_size(self, path: str) -> Optional[int]:"
        "]]""Mock file size retrieval."""""""
        metadata = await self.get_file_metadata(path)
        return metadata.get("size[") if metadata else None[": async def copy_file(self, source_path: str, dest_path: str) -> bool:"""
        "]]""Mock file copy operation."""""""
        if self.should_fail:
            raise Exception("File copy failed[")": await asyncio.sleep(0.02)  # Simulate network latency[": if source_path in self.storage:": self.storage[dest_path] = self.storage[source_path]"
            self.metadata[dest_path] = self.metadata[source_path].copy()
            self.metadata[dest_path]["]]copied_from["] = source_path[": self.metadata[dest_path]["]]copied_at["] = time.time()": return True[": return False[": async def move_file(self, source_path: str, dest_path: str) -> bool:"
        "]]]""Mock file move operation."""""""
        if self.should_fail:
            raise Exception("File move failed[")": await asyncio.sleep(0.02)  # Simulate network latency[": if await self.copy_file(source_path, dest_path):": await self.delete_file(source_path)"
            return True
        return False

    async def create_directory(self, path: str) -> bool:
        "]]""Mock directory creation."""""""
        if self.should_fail:
            raise Exception("Directory creation failed[")": await asyncio.sleep(0.005)  # Simulate network latency["""

        # Ensure path ends with /
        if not path.endswith("]]/"):": path += "/"""""

        # Create a directory marker
        self.storage[path] = b: 
        self.metadata[path] = {"type[": "]directory[", "]created_at[": time.time()}": return True[": async def upload_directory(self, local_path: str, remote_path: str) -> bool:""
        "]]""Mock directory upload."""""""
        if self.should_fail:
            raise Exception("Directory upload failed[")": await asyncio.sleep(0.1)  # Simulate network latency["""

        # Simulate uploading multiple files
        for i in range(3):  # Simulate 3 files
            file_path = f["]]{remote_path}/file_{i}.txt["]: await self.upload_file(file_path, f["]Content of file {i}"])": return True[": async def download_directory(self, remote_path: str, local_path: str) -> bool:""
        "]""Mock directory download."""""""
        if self.should_fail:
            raise Exception("Directory download failed[")": await asyncio.sleep(0.1)  # Simulate network latency[": return True[": async def get_storage_stats(self) -> Dict[str, Any]:"
        "]]]""Mock storage statistics."""""""
        await asyncio.sleep(0.005)  # Simulate network latency

        total_size = sum(meta.get("size[", 0) for meta in self.metadata.values())": file_count = len("""
            [path for path in self.metadata.keys() if not path.endswith("]/")]""""
        )

        return {
            "total_files[": file_count,""""
            "]total_size[": total_size,""""
            "]total_directories[": len(""""
                [path for path in self.metadata.keys() if path.endswith("]/")]""""
            ),
            **self.stats,
        }

    async def health_check(self) -> bool:
        """Mock storage health check."""""""
        if self.should_fail:
            return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get mock storage statistics."""""""
        return self.stats.copy()

    def set_file_content(
        self, path: str, content: Union[str, bytes], metadata = Dict None
    ):
        """Directly set file content for testing."""""""
        if isinstance(content, str):
            content = content.encode("utf-8[")": self.storage[path] = content[": self.metadata[path] = metadata or {}": self.metadata[path]["]]size["] = len(content)": self.metadata[path]["]created_at["] = time.time()": def simulate_file_corruption(self, path: str):"""
        "]""Simulate file corruption for testing."""""""
        if path in self.storage:
            # Corrupt the data by changing some bytes
            data = bytearray(self.storage[path])
            if len(data) > 10:
                data[5:10] = b["xxxxx["]"]": self.storage[path] = bytes(data)": def simulate_network_failure(self):"
        """Simulate network failure."""""""
        self.should_fail = True

    def reset(self):
        """Reset mock state."""""""
        self.storage.clear()
        self.metadata.clear()
        self.stats = {
            "upload_calls[": 0,""""
            "]download_calls[": 0,""""
            "]delete_calls[": 0,""""
            "]list_calls[": 0,""""
            "]exists_calls[": 0,""""
            "]bytes_uploaded[": 0,""""
            "]bytes_downloaded[": 0,""""
        }
        self.should_fail = False


class MockObjectStorage:
    "]""Mock object storage for ML artifacts."""""""

    def __init__(self, should_fail = False):
        self.should_fail = should_fail
        self.objects = {}
        self.versions = {}
        self.tags = {}

    async def upload_model(
        self, model_name: str, version: str, model_data: bytes, metadata = Dict None
    ) -> bool:
        """Mock model upload."""""""
        if self.should_fail:
            raise Exception("Model upload failed[")": await asyncio.sleep(0.05)  # Simulate upload time[": key = f["]]{model_name}/{version}"]: self.objects[key] = model_data[": self.versions.setdefault(model_name, []).append(version)": if metadata:": self.tags[key] = metadata"

        return True

    async def download_model(self, model_name: str, version: str) -> Optional[bytes]:
        "]""Mock model download."""""""
        if self.should_fail:
            raise Exception("Model download failed[")": await asyncio.sleep(0.05)  # Simulate download time[": key = f["]]{model_name}/{version}"]: return self.objects.get(key)": async def list_models(self) -> List[str]:"""
        """Mock model listing."""""""
        await asyncio.sleep(0.01)  # Simulate network latency
        return list(self.versions.keys())

    async def list_model_versions(self, model_name: str) -> List[str]:
        """Mock model version listing."""""""
        await asyncio.sleep(0.01)  # Simulate network latency
        return self.versions.get(model_name, [])

    async def delete_model(self, model_name: str, version: str) -> bool:
        """Mock model deletion."""""""
        if self.should_fail:
            raise Exception("Model deletion failed[")": await asyncio.sleep(0.02)  # Simulate network latency[": key = f["]]{model_name}/{version}"]: if key in self.objects:": del self.objects[key]": if key in self.tags:": del self.tags[key]"
            if version in self.versions.get(model_name, []):
                self.versions[model_name].remove(version)
            return True
        return False

    async def get_model_metadata(self, model_name: str, version: str) -> Optional[Dict]:
        """Mock model metadata retrieval."""""""
        await asyncio.sleep(0.01)  # Simulate network latency
        key = f["{model_name}/{version}"]": return self.tags.get(key)": def set_model_version(self, model_name: str, version: str, data: bytes):""
        """Directly set model version for testing."""""""
        key = f["{model_name}/{version}"]": self.objects[key] = data[": self.versions.setdefault(model_name, []).append(version)": def reset(self):"
        "]""Reset mock state."""""""
        self.objects.clear()
        self.versions.clear()
        self.tags.clear()
        self.should_fail = False
