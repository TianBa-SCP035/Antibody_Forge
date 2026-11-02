"""测试公用：内存 SQLite 库。"""

import unittest

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
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


def memory_engine(*models):
    """新建内存 SQLite 库，只建给定模型的表。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
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
