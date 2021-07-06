from .const import MAX_WRITE_RECORDS_PRE_REQ, MAX_GET_RECORDS_PRE_REQ
from .exceptions import RecordDoesNotExist
from .query_set import QuerySet
from .record import Record
from .types import GETRecordResponse
from .utils import query_parse


class RecordManager:
    def __init__(self, dst: 'Datasheet'):
        self._dst = dst
        self._fetched_with = None
        self._fetched_by = None

    def bulk_create(self, data):
        """
        批量创建记录，每个请求只能创建 10 条记录
        dst.records.create({"标题": "hello vika"})
        """
        if len(data) > MAX_WRITE_RECORDS_PRE_REQ:
            raise Exception(f'单个请求创建记录数量不得大于 {MAX_WRITE_RECORDS_PRE_REQ} 条')
        resp = self._dst.create_records(data)
        return [Record(self._dst, record) for record in resp.data.records]

    def create(self, data):
        """
        创建一条记录
        dst.records.create({"标题": "hello vika"})
        """
        resp = self._dst.create_records(data)
        if resp.success:
            records = resp.data.records
            return Record(self._dst, records[0])
        raise Exception(resp.message)

    def all(self, **kwargs):
        """
        链式调用中，只有第一个 all 方法可以定制返回数据。
        * 视图ID。默认为维格表中第一个视图。请求会返回视图中经过视图中筛选/排序后的结果，可以搭配使用fields参数过滤不需要的字段数据
        viewId: 'viewId1',
        * 对指定维格表的记录进行排序。由多个“排序对象”组成的数组。支持顺序：'asc' 和 逆序：'desc'。注：此参数指定的排序条件将会覆盖视图里的排序条件。
        sort: [{ '列名称或者 ID': 'asc' }],
        * recordIds 数组。如果附带此参数，则返回参数中指定的records数组。 返回值按照传入数组的顺序排序。此时无视筛选、排序。无分页，每次最多查询 1000 条
        recordIds: ['recordId1', 'recordId2'],
        * 指定要返回的字段（默认为字段名, 也可以通过 fieldKey 指定为字段 Id）。如果附带此参数，则返回的记录合集将会被过滤，只有指定的字段会返回。
        fields: ['标题', '详情', '引用次数'],
        * 使用公式作为筛选条件，返回匹配的记录，访问 https://vika.cn/help/tutorial-getting-started-with-formulas/ 了解公式使用方式
        filterByFormula: '{引用次数} >  0',
        * 限制返回记录的总数量。如果该值小于表中实际的记录总数，则返回的记录总数会被限制为该值。
        maxRecords: 5000,
        * 单元格值类型，默认为 'json'，指定为 'string' 时所有值都将被自动转换为 string 格式。
        cellFormat: 'json',
        * 指定 field 的查询和返回的 key。默认使用列名  'name' 。指定为 'id' 时将以 fieldId 作为查询和返回方式（使用 id 可以避免列名的修改导致代码失效问题）
        fieldKey: 'name',
        """
        _fieldKey = kwargs.get("fieldKey")
        if _fieldKey and _fieldKey != self._dst.field_key:
            # TODO: logger warning
            print(
                f'It seems that you set field_key when init datasheet, all(filedKey="{_fieldKey}") wont work'
            )
        kwargs.update(fieldKey=self._dst.field_key)
        if 'pageSize' in kwargs or 'pageNum' in kwargs:
            resp: GETRecordResponse = self._dst.get_records(**kwargs)
            if resp.success:
                records = resp.data.records
            else:
                print(f"[{self._dst.id}] fetch data fail\n {resp.message}")
                records = []
        else:
            records = self._dst.get_records_all(**kwargs)
        return QuerySet(self._dst, records)

    def get(self, **kwargs):
        """
        查询出符合条件的单条记录，适合使用唯一标识的字段做查询
        book = dst_books.records.get(ISBN="9787506341271")
        print(book.title)
        """
        query_formula = query_parse(self._dst.field_key_map, **kwargs)
        kwargs = {"filterByFormula": query_formula}
        resp: GETRecordResponse = self._dst.get_records(**kwargs)
        if resp.data.records:
            return Record(self._dst, resp.data.records[0])
        raise RecordDoesNotExist()

    def filter(self, **kwargs):
        """
        查询出符合条件的记录集（QuerySet）
        songs = dst_songs.records.filter(artist="faye wong")
        for song in songs:
            print(song.title)
        """
        # 直接通过 filter 调用时候，将 filter 查询参数转化为 filterByFormula，使用服务端计算结果
        records = self._query_records(**kwargs)
        return QuerySet(self._dst, records)

    def _query_records(self, **kwargs):
        # 将查询条件转化为 filterByFormula， 利用服务端计算查询记录集
        query_formula = query_parse(self._dst.field_key_map, **kwargs)
        kwargs = {"filterByFormula": query_formula, "pageSize": MAX_GET_RECORDS_PRE_REQ}
        print(kwargs)
        resp: GETRecordResponse = self._dst.get_records(**kwargs)
        if resp.data.pageNum * resp.data.pageSize < resp.data.total:
            return resp.data.records + self._dst.get_records(pageNum=resp.data.pageNum + 1, **kwargs)
        return resp.data.records
