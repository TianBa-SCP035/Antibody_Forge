"""测试公用：内存 SQLite 库与外部只读库桩。"""

import json
import unittest

from sqlalchemy import BigInteger, create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateIndex

from db.session import Base


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, _compiler, **_kwargs):
    # SQLite 只有 INTEGER 主键才会自增
    return "INTEGER"


@compiles(CreateIndex, "sqlite")
def _compile_create_index_for_sqlite(create, compiler, **kwargs):
    # MySQL 多值索引 CAST(... ARRAY) SQLite 建不了，测试库不需要
    if any(" ARRAY)" in str(expr) for expr in create.element.expressions):
        return "SELECT 1"
    return compiler.visit_create_index(create, **kwargs)


def _json_items(value):
    return json.loads(value or "[]")


def _register_mysql_json_functions(dbapi_connection, _record):
    # 列表筛选用到的 MySQL JSON 函数，SQLite 没有
    dbapi_connection.create_function("json_length", 1, lambda value: len(_json_items(value)))
    dbapi_connection.create_function(
        "json_overlaps", 2, lambda left, right: bool(set(_json_items(left)) & set(_json_items(right)))
    )


def memory_engine(*models):
    """新建内存 SQLite 库，只建给定模型的表。"""
    # 单连接跨线程共用：TestClient 在线程池里跑同步路由，否则看到的是另一个空库
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    event.listen(engine, "connect", _register_mysql_json_functions)
    Base.metadata.create_all(engine, tables=[model.__table__ for model in models])
    return engine


class DbTestCase(unittest.TestCase):
    """每个用例一个新库：子类在 tables 里列模型，用 self.Session 开会话或直接用 self.db。"""

    tables: tuple = ()
    session_options: dict = {"autoflush": False, "expire_on_commit": False}

    def setUp(self):
        self.engine = memory_engine(*self.tables)
        self.addCleanup(self.engine.dispose)
        self.Session = sessionmaker(bind=self.engine, **self.session_options)
        self.db = self.Session()
        self.addCleanup(self.db.close)


class FakeSourceDb:
    """外部只读库（员工库、靶点源库）：任何查询都返回给定的行。"""

    def __init__(self, rows):
        self.rows = [dict(row) for row in rows]

    def execute(self, _stmt, _params=None):
        return self

    def mappings(self):
        return self

    def all(self):
        return self.rows
