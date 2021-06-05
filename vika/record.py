from .exceptions import RecordWasDeleted, ErrorFieldKey
from .types import RawRecord


class Record:
    def __init__(self, datasheet: 'Datasheet', record: RawRecord):
        self._datasheet = datasheet
        self._id = record.id
        self._is_del = False

    def _get_field(self, field_key: str):
        if self._datasheet.field_key == "id":
            return self._datasheet.fields.get(id=field_key)
        return self._datasheet.fields.get(name=field_key)

    @property
    def _record(self):
        return self._datasheet.get_record_by_id(self._id)

    def _check_record_status(self):
        if self._is_del:
            raise RecordWasDeleted()
        return None

    def __str__(self):
        return f"(Record: {self._id})"

    __repr__ = __str__

    def __getattr__(self, key):
        trans_key = self._datasheet.trans_key(key)
        if not trans_key:
            raise Exception(f"record has no field:[{trans_key}]")
        # 数据里面能拿到，表示返回了
        if trans_key in self._record.data:
            return self._record.data.get(trans_key)
        # 数据里面拿不到，但存在这个字段。表示字段值为空
        if trans_key in self._datasheet.meta_field_id_map or trans_key in self._datasheet.meta_field_name_map:
            return None
        # 错误的字段
        raise ErrorFieldKey(f"'{key}' does not exist")

    def delete(self) -> bool:
        """
        删除此记录
        """
        self._check_record_status()
        is_del_success = self._datasheet.delete_records([self._id])
        if is_del_success:
            self._datasheet.client_remove_records([self._record])
            self._is_del = True
        return is_del_success

    def __setattr__(self, _key, value):
        if _key.startswith("_"):
            super().__setattr__(_key, value)
        else:
            key = self._datasheet.trans_key(_key)
            field = self._get_field(key)
            # 针对不同的字段做处理，校验。
            # 1. 附件字段的自动处理，上传流程
            if field and field.type == "Attachment":
                if isinstance(value, list):
                    value = [self._datasheet.upload_file(url) for url in value]
                if not value:
                    value = None
            data = {"recordId": self._id, "fields": {key: value}}
            update_success_count = self._datasheet.update_records(data)
            if update_success_count == 1:
                self._record.data[key] = value

    def json(self):
        self._check_record_status()
        # FIXME: 补全空值字段, 使用原始数据，还是使用映射的字段名做 key
        record_data = dict(self._record.data)
        return record_data

    def _make_update_body(self, data):
        _data = self._datasheet.trans_data(data)
        data = {"recordId": self._id, "fields": _data}
        return data

    def update(self, data):
        """
        更新多个字段
        """
        self._check_record_status()
        # 更新单个记录的多个字段，只返回一条记录
        data = self._make_update_body(data)
        return self._datasheet.update_records(data)
