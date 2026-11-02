# 工单数据回传接口
> 供设备或外部平台上传工单实验结果 JSON；当前只保存原文和接收摘要，不解析业务结果。

## 1. 接口

```text
POST /api/order-experiment/sync
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `trace_id` | 文本 | 是 | 去除首尾空白后不能为空；数据库内唯一 |
| `order_json` | 文件 | 是 | UTF-8 编码的 JSON 文件 |

`order_json` 文件上限由 `ORDER_SYNC_MAX_MB` 配置，默认 20 MiB。超过上限返回 HTTP 413。

## 2. 来源认证

| 配置 | 请求要求 |
|---|---|
| `ORDER_SYNC_TOKEN` | 请求头 `X-Callback-Token` 必须与配置值一致 |
| `ORDER_SYNC_IPS` | 调用方 IP 必须在英文逗号分隔的白名单中 |

配置为空时不校验对应项。两项都配置时必须同时通过。Token 不接受 URL 参数。

认证失败由 FastAPI 直接返回：

| HTTP 状态 | 条件 | 响应 |
|---|---|---|
| 401 | Token 缺失或不匹配 | `{"detail":"调用方校验失败"}` |
| 403 | 调用方 IP 不在白名单 | `{"detail":"调用方不在允许列表"}` |

## 3. `order_json` 格式

根节点必须是对象。`order_infos` 必须是非空数组；每个元素必须是对象，并包含非空 `order_no`。

最小有效示例：

```json
{
  "order_infos": [
    {
      "order_no": "ORD202605270001",
      "project_infos": [
        {
          "project_no": "PROJ001",
          "data_type": "TITER",
          "experiment_date": "20260527",
          "target": "CD33"
        }
      ]
    }
  ]
}
```

`project_infos` 不是接收校验的必填项。它是数组时，系统从对象元素提取以下摘要字段：

| 字段 | 摘要用途 |
|---|---|
| `project_no` | 项目号 |
| `data_type` | 数据类型 |
| `experiment_date` | 实验日期 |
| `target` | 靶点 |

除 `order_infos`、`order_no` 的结构要求外，当前接口不校验其他业务字段，也不限制 `data_type` 枚举。完整 JSON 原文会按收到的内容保存。

### 3.1 对接约定的完整结构

以下为与设备平台约定的数据结构，供对接方组织数据。接口只校验上文的必填结构，其余字段按原文保存。`data_type` 约定取 `PLAS`、`PCR`、`TITER`；图片和 CSV 字段传路径，不传文件本体。

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

## 4. 请求示例

```bash
curl -X POST "https://{host}/api/order-experiment/sync" \
  -H "X-Callback-Token: {token}" \
  -F "trace_id=TRACE202605270001" \
  -F "order_json=@order_infos.json;type=application/json"
```

未配置 `ORDER_SYNC_TOKEN` 时可省略请求头。

## 5. 响应

### 5.1 成功

HTTP 200：

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

### 5.2 接口错误

通过来源认证并进入业务处理后，错误使用以下结构，HTTP 状态与 `code` 相同：

```json
{
  "code": 400,
  "message": "order_json 文件格式错误：order_infos 不能为空",
  "trace_id": "TRACE202605270001",
  "data": null
}
```

| HTTP / `code` | 条件 |
|---|---|
| 400 | `trace_id` 为空、文件为空、不是 UTF-8、JSON 不合法、根节点不是对象，或 `order_infos` / `order_no` 不符合要求 |
| 413 | `order_json` 超过 `ORDER_SYNC_MAX_MB` |
| 422 | `trace_id` 已存在 |
| 500 | 保存文件或数据库记录时发生未处理异常 |

缺少 multipart 必填字段时，请求在进入处理函数前由 FastAPI 返回 HTTP 422，响应为框架校验错误结构。来源认证的 401/403 响应见 §2。

## 6. 接收结果

成功后执行以下操作：

1. JSON 原文保存到 `repository/order_sync/<YYYYMMDD>/`。
2. `order_sync` 表写入 `trace_id`、相对文件路径、订单数量、订单号列表、项目数量和项目摘要列表。
3. 接收记录状态写为 `pending`。

`pending` 只表示文件已接收并登记。当前接口不下载 JSON 中引用的图片或 CSV，也不把结果写入效价业务表。
