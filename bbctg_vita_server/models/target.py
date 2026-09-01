from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class Target(Base):
    __tablename__ = "target"
    __table_args__ = (
        Index("uk_target_external_id", "external_id", unique=True),
        Index("uk_target_snum", "snum", unique=True),
        Index("idx_target_name", "name"),
        Index("idx_target_human_gene_name", "human_gene_official_name"),
        Index("idx_target_mouse_gene_name", "mouse_gene_official_name"),
        Index("idx_target_status_type", "status", "type"),
        {"comment": "靶点表（项目管理同步）"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    external_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="外部平台靶点ID",
    )
    snum: Mapped[str] = mapped_column(String(100), nullable=False, comment="靶点编号")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="靶点名称")
    type: Mapped[int | None] = mapped_column(comment="靶点类型")
    status: Mapped[int | None] = mapped_column(comment="开发状态")
    category: Mapped[str | None] = mapped_column(String(200), comment="靶点分类")

    ko_lethal_info: Mapped[int | None] = mapped_column(comment="KO致死情况")
    ko_lethal_info_desc: Mapped[str | None] = mapped_column(String(1000), comment="KO致死信息备注")
    structural_properties: Mapped[str | None] = mapped_column(String(200), comment="结构特性类别")
    structure_feature: Mapped[str | None] = mapped_column(String(100), comment="结构特性（跨膜次数）")
    shape_remark: Mapped[str | None] = mapped_column(String(200), comment="形式备注")
    structure_feature_remark: Mapped[str | None] = mapped_column(
        String(1000),
        comment="结构特性备注",
    )
    ko_mgi: Mapped[str | None] = mapped_column(Text, comment="KO鼠表型MGI")
    ko_impc: Mapped[str | None] = mapped_column(String(100), comment="KO鼠表型IMPC")
    effect_cell: Mapped[str | None] = mapped_column(String(1000), comment="靶点作用细胞")
    ko_gt: Mapped[str | None] = mapped_column(String(100), comment="KO鼠表型GT")

    official_full_name: Mapped[str | None] = mapped_column(String(300), comment="官方全名")
    human_gene_official_name: Mapped[str | None] = mapped_column(
        String(200),
        comment="人基因官方名称",
    )
    human_gene_alias_name: Mapped[str | None] = mapped_column(String(500), comment="人基因别名")
    human_ncbi_gene_id: Mapped[str | None] = mapped_column(String(200), comment="人NCBI Gene ID")
    human_chromosome_position: Mapped[str | None] = mapped_column(
        String(200),
        comment="人染色体位置",
    )

    is_homologous_gene: Mapped[bool | None] = mapped_column(Boolean, comment="是否有同源基因")
    mouse_gene_official_name: Mapped[str | None] = mapped_column(
        String(200),
        comment="小鼠基因官方名称",
    )
    mouse_gene_alias_name: Mapped[str | None] = mapped_column(String(255), comment="小鼠基因别名")
    mouse_ncbi_gene_id: Mapped[str | None] = mapped_column(
        String(200),
        comment="小鼠NCBI Gene ID",
    )
    mouse_chromosome_position: Mapped[str | None] = mapped_column(
        String(200),
        comment="小鼠染色体位置",
    )

    human_mouse_homology: Mapped[str | None] = mapped_column(String(200), comment="人鼠同源性")
    human_dog_homology: Mapped[str | None] = mapped_column(String(200), comment="人犬同源性")
    human_cat_homology: Mapped[str | None] = mapped_column(String(200), comment="人猫同源性")
    human_monkey_homology: Mapped[str | None] = mapped_column(String(200), comment="人猴同源性")
    human_mouse_homology_expect_functional_domain: Mapped[str | None] = mapped_column(
        String(200),
        comment="预期主要功能结构域人鼠同源性",
    )

    gene_functional_desc: Mapped[str | None] = mapped_column(Text, comment="基因功能描述")
    is_ko_affect_humoral_immunity: Mapped[bool | None] = mapped_column(
        Boolean,
        comment="KO是否影响体液免疫",
    )
    is_ko_affect_humoral_immunity_desc: Mapped[str | None] = mapped_column(
        String(500),
        comment="KO是否影响体液免疫备注",
    )
    is_human_mouse_cross: Mapped[str | None] = mapped_column(
        String(1000),
        comment="配体或受体是否人鼠交叉",
    )
    treatment_field: Mapped[str | None] = mapped_column(String(500), comment="治疗领域")
    indication: Mapped[str | None] = mapped_column(String(200), comment="适应症")
    gene_family: Mapped[str | None] = mapped_column(String(200), comment="基因家族")
    signal_path: Mapped[str | None] = mapped_column(String(1000), comment="信号通路")
    remark: Mapped[str | None] = mapped_column(String(2000), comment="备注")

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("1"),
        comment="数据是否有效",
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        comment="最近变更时间",
    )
