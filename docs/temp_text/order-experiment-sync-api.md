# 工单数据回传接口

## 业务说明

设备管理平台将工单实验检测数据整理为 JSON 文件，通过本接口回传到本系统。本系统当前只负责接收、校验、保存原始 JSON 文件，并写入一条 `order_sync` 接收记录；暂不解析入效价业务表，也不下载图片或 CSV 文件。

## 请求

**POST** `/api/order-experiment/sync`

Content-Type：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `trace_id` | 字符串 | 是 | 本次上传的追踪 ID；重复提交返回 `422` |
| `order_json` | 文件 | 是 | UTF-8 JSON 文件 |

### order_json 结构

```json
{
  "order_infos": [
    {
      "order_no": "ORD202605270001",
      "order_name": "订单名称1",
      "project_infos": [
        {
          "project_no": "PROJ001",
          "data_type": "TITER",
          "experiment_date": "20260527",
          "target": "CD33",
          "secondary_antibody": ["Alexa Fluor 647 Goat Anti-Human IgG 1:4000"],
          "cell_board_infos": [
            {
              "cell_name": "CHO-S-hCD33",
              "cell_type": "肿瘤",
              "batch": "C260527B01",
              "generation": "P18",
              "detect_board_infos": [
                {
                  "barcode": "xxxxx01",
                  "sample_code": "BAO0000001-20R090-RLBWB95-1",
                  "whole_board_img": "/data/images/xxxxx01.png",
                  "heatmap_csv": "/data/csv/xxxxx01.csv",
                  "well_infos": [
                    {
                      "well_no": "A01",
                      "img_path": "/data/well/xxxxx01/A01.png",
                      "sample_name": "Sample-001",
                      "mfi": 12345.67,
                      "ppc": 89.45
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

`data_type` 可为 `PLAS`、`PCR`、`TITER`。图片和 CSV 字段传路径，不传文件本体。

## 示例请求

```bash
curl -X POST "http://{host}/api/order-experiment/sync" \
  -F "trace_id=TRACE202605270001" \
  -F "order_json=@order_infos.json;type=application/json"
```

## 响应

成功：

```json
{
  "code": 0,
  "message": "success",
  "trace_id": "TRACE202605270001",
  "data": {
    "total_orders": 1,
    "success_orders": ["ORD202605270001"],
    "failed_orders": []
  }
}
```

失败：

```json
{
  "code": 400,
  "message": "order_json 文件格式错误：order_infos 不能为空",
  "trace_id": "TRACE202605270001",
  "data": null
}
```

| code | 含义 |
|------|------|
| `0` | 成功 |
| `400` | 参数错误，如缺少 `trace_id`、JSON 不合法、`order_infos` 为空 |
| `422` | 业务校验失败，如 `trace_id` 重复 |
| `500` | 服务端异常 |

## 当前保存方式

- JSON 原文保存到 `repository/order_sync/<YYYYMMDD>/`
- 数据库记录写入 `order_sync` 表
- 接收记录保存 `trace_id`、文件路径、订单数量、订单号列表、项目数量、项目摘要列表
- 项目摘要列表包含 `order_no`、`project_no`、`data_type`、`experiment_date`、`target`
- `status` 表示后续处理状态；初始值为 `pending`，表示已接收但尚未做业务入库
