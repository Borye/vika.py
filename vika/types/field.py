from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel


class MemberEnum(str, Enum):
    Member = 'Member'
    Team = 'Team'


class RollUpFunctionEnum(str, Enum):
    VALUES = 'VALUES'
    AVERAGE = 'AVERAGE'
    COUNT = 'COUNT'
    COUNTA = 'COUNTA'
    COUNTALL = 'COUNTALL'
    SUM = 'SUM'
    MIN = 'MIN'
    MAX = 'MAX'
    AND = 'AND'
    OR = 'OR'
    XOR = 'XOR'
    CONCATENATE = 'CONCATENATE'
    ARRAYJOIN = 'ARRAYJOIN'
    ARRAYUNIQUE = 'ARRAYUNIQUE'
    ARRAYCOMPACT = 'ARRAYCOMPACT'


class ComputeValueTypeEnum(str, Enum):
    String = 'String'
    Boolean = 'Boolean'
    Number = 'Number'
    Array = 'Array'
    DateTime = 'DateTime'


# field property
class SingleTextFieldProperty(BaseModel):
    defaultValue: Optional[str]


class NumberFieldProperty(BaseModel):
    defaultValue: Optional[str]
    precision: int


class CurrencyFieldProperty(NumberFieldProperty):
    symbol: str


class PercentFieldProperty(NumberFieldProperty):
    pass


class SelectOptionColor(BaseModel):
    name: str
    value: str


class SelectOption(BaseModel):
    id: str
    name: str
    color: SelectOptionColor


class SingleSelectFieldProperty(BaseModel):
    options: List[SelectOption]


class MultiSelectFieldProperty(SingleSelectFieldProperty):
    pass


class MemberOption(BaseModel):
    id: str
    name: str
    type: MemberEnum
    avatar: Optional[str]


class MemberFieldProperty(BaseModel):
    options: List[MemberOption]


class UserOption(BaseModel):
    id: str
    name: str
    avatar: str


class CreateByFieldProperty(BaseModel):
    options: List[UserOption]


class LastModifiedByFieldProperty(CreateByFieldProperty):
    pass


class CheckboxFieldProperty(BaseModel):
    icon: str


class RatingFieldProperty(BaseModel):
    icon: str
    max: int


class DateTimeFieldProperty(BaseModel):
    format: str
    autoFill: bool
    includeTime: bool


class CreatedTimeFieldProperty(DateTimeFieldProperty):
    pass


class LastModifiedTimeFieldProperty(DateTimeFieldProperty):
    pass


class MagicLinkFieldProperty(BaseModel):
    foreignDatasheetId: str
    brotherFieldId: str


class FieldPropertyWithDstId(BaseModel):
    datasheetId: str
    field: "MetaField"


class MagicLookupFieldProperty(BaseModel):
    relatedLinkFieldId: str
    targetFieldId: str
    hasError: Optional[bool]
    entityField: Optional[FieldPropertyWithDstId]
    rollupFunction: RollUpFunctionEnum
    valueType: ComputeValueTypeEnum


class FormulaFieldProperty(BaseModel):
    expression: Optional[str]  # 一定会有公式表达式吗
    valueType: ComputeValueTypeEnum
    hasError: Optional[bool]


FieldProperty = Union[
    SingleTextFieldProperty,
    NumberFieldProperty,
    CurrencyFieldProperty,
    PercentFieldProperty,
    SingleSelectFieldProperty,
    MultiSelectFieldProperty,
    MemberFieldProperty,
    CreateByFieldProperty,
    LastModifiedByFieldProperty,
    CheckboxFieldProperty,
    RatingFieldProperty,
    DateTimeFieldProperty,
    DateTimeFieldProperty,
    CreatedTimeFieldProperty,
    LastModifiedTimeFieldProperty,
    MagicLinkFieldProperty,
    MagicLookupFieldProperty,
    FormulaFieldProperty,
]


# field item
class MetaField(BaseModel):
    id: str
    name: str
    type: str
    isPrimary: Optional[bool]
    desc: Optional[str]
    property: Optional[FieldProperty]
    editable: Optional[bool]
