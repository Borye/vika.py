import io
import json
import mimetypes
from typing import List
from urllib.parse import urljoin

import requests

from .const import API_GET_DATASHEET_QS_SET, DEFAULT_PAGE_SIZE
from .exceptions import ErrorSortParams
from .field_manager import FieldManager
from .record import Record
from .record_manager import RecordManager
from .types.response import (
    GETMetaFieldResponse,
    PatchRecordResponse,
    PostRecordResponse,
    DeleteRecordResponse,
    UploadFileResponse,
    RawRecord,
    GETMetaViewResponse, GETRecordResponse,
)
from .utils import FieldKeyMap, handle_response
from .view_manager import ViewManager


class Datasheet:
    def __init__(self, vika: 'Vika', dst_id: str, **kwargs):
        self.vika = vika
        self.id = dst_id
        field_key = kwargs.get("field_key", "name")
        if field_key not in ["name", "id"]:
            raise Exception("Error field_key, plz use「name」 or 「id」")
        self.field_key = field_key
        field_key_map = kwargs.get("field_key_map", None)
        self.field_key_map: FieldKeyMap = field_key_map

    def refresh(self):
        """
        TODO refetch datasheet
        """
        pass

    @property
    def _record_api_endpoint(self):
        return urljoin(self.vika.api_base, f"/fusion/v1/datasheets/{self.id}/records")

    @property
    def fields(self):
        return FieldManager(self)

    @property
    def primary_field(self):
        return self.fields.all()[0]

    @property
    def views(self):
        return ViewManager(self)

    @property
    def records(self):
        return RecordManager(self)

    def trans_key(self, key):
        """
        存在字段映射时，将映射的 key 转为实际的 key
        """
        field_key_map = self.field_key_map
        if key in ["_id", "recordId"]:
            return key
        if field_key_map:
            _key = field_key_map.get(key, key)
            return _key
        return key

    def trans_data(self, data):
        field_key_map = self.field_key_map
        if field_key_map:
            _data = {}
            for k, v in data.items():
                _k = field_key_map.get(k, k)
                _data[_k] = v
            return _data
        return data

    # 下面是数表管理的请求
    # 字段相关
    def get_fields(self):
        """
        获取 field meta
        """
        api_endpoint = urljoin(
            self.vika.api_base, f"/fusion/v1/datasheets/{self.id}/fields"
        )
        r = self.vika.request.get(api_endpoint).json()
        return handle_response(r, GETMetaFieldResponse)

    def get_views(self):
        """
        获取 view meta
        """
        api_endpoint = urljoin(
            self.vika.api_base, f"/fusion/v1/datasheets/{self.id}/views"
        )
        r = self.vika.request.get(api_endpoint).json()
        r = GETMetaViewResponse(**r)
        if r.success:
            return r.data.views
        raise Exception(r.message)

    def get_records(self, **kwargs):
        """
        分页获取数表数据
        """
        params = {}
        for key in kwargs:
            if key in API_GET_DATASHEET_QS_SET:
                params_value = kwargs.get(key)
                if key == 'sort':
                    if self.check_sort_params(params_value):
                        params_value = [json.dumps(i) for i in params_value]
                    else:
                        raise ErrorSortParams('sort 参数格式有误')
                params.update({key: params_value})
        resp = self.vika.request.get(self._record_api_endpoint, params=params).json()
        resp = handle_response(resp, GETRecordResponse)
        return resp

    def get_records_all(self, **kwargs) -> List[RawRecord]:
        """
        不主动传入 pageSize 和 pageNum 时候，主动加载全部记录。
        """
        page_size = kwargs.get("pageSize", DEFAULT_PAGE_SIZE)
        page_num = kwargs.get("pageNum", 1)
        page_params = {"pageSize": page_size, "pageNum": page_num}
        kwargs.update(page_params)
        records = []
        resp = self.get_records(**kwargs)
        if resp.success:
            records += resp.data.records
            current_total = page_size * page_num
            if current_total < resp.data.total:
                kwargs.update({"pageNum": page_num + 1})
                records += self.get_records_all(**kwargs)
        else:
            print(f"[{self.id}] get page:{page_num} fail\n {resp.message}")
        return records

    def create_records(self, data) -> PostRecordResponse:
        """
        添加记录
        """
        if type(data) is list:
            data = {
                "records": [{"fields": self.trans_data(item)} for item in data],
                "fieldKey": self.field_key,
            }
        else:
            data = {
                "records": [{"fields": self.trans_data(data)}],
                "fieldKey": self.field_key,
            }
        r = self.vika.request.post(self._record_api_endpoint, json=data).json()
        return handle_response(r, PostRecordResponse)

    def delete_records(self, rec_list) -> bool:
        """
        删除记录
        """
        api_endpoint = self._record_api_endpoint
        if type(rec_list) is list:
            ids = [rec._id if type(rec) is Record else rec for rec in rec_list]
        else:
            rec = rec_list
            ids = rec._id if type(rec) is Record else rec
        r = self.vika.request.delete(api_endpoint, params={"recordIds": ids}).json()
        r = handle_response(r, DeleteRecordResponse)
        return r.success

    def update_records(self, data) -> List[RawRecord]:
        """
        更新记录
        """
        if type(data) is list:
            data = {"records": data, "fieldKey": self.field_key}
        else:
            data = {"records": [data], "fieldKey": self.field_key}
        r = self.vika.request.patch(self._record_api_endpoint, json=data).json()
        if r["success"]:
            r = PatchRecordResponse(**r)
            return r.data.records
        else:
            raise Exception(r["message"])

    def upload_attachment(self, file_url):
        return self.upload_file(file_url)

    # 废弃
    def upload_file(self, file_url):
        """
        上传附件，支持本地或者网络文件路经。
        dst.upload_file("/path/to/your/file")
        """
        api_endpoint = urljoin(
            self.vika.api_base, f"/fusion/v1/datasheets/{self.id}/attachments"
        )
        is_web_file = type(file_url) is str and file_url.startswith("http")

        if is_web_file:
            r = requests.get(file_url)
            file_mimetype = r.headers["content-type"]
            with io.BytesIO() as buf:
                buf.write(r.content)
                buf.seek(0)
                _file = ("image", io.BufferedReader(buf), file_mimetype)
                r = self.vika.request.post(
                    api_endpoint,
                    files={"files": _file},
                    stream=False,
                ).json()
                print(r)
                r = UploadFileResponse(**r)
                if r.success:
                    return r.data
        else:
            with open(file_url, "rb") as upload_file:
                r = self.vika.request.post(
                    api_endpoint,
                    files={
                        "files": (
                            file_url,
                            upload_file,
                            mimetypes.guess_type(file_url)[0],
                        )
                    },
                ).json()
                r = UploadFileResponse(**r)
                if r.success:
                    return r.data
