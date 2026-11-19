# 工单数据回传接口
> 供镁伽上传流式工单实验结果 JSON。收到后先存原文，再对照下发快照逐板核对并当场回复；核对通过的效价板在后台下载图片和热图、写入效价实验。页面入口与工单侧说明见 [flow-work-order.md](./flow-work-order.md)。

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

| 配置 | 请求要求 | 不满足时 |
|---|---|---|
| `ORDER_SYNC_IPS` | 调用方 IP 在英文逗号分隔的白名单中 | 403 |
| `ORDER_SYNC_TOKEN` | 请求头 `X-Callback-Token` 与配置值一致（不接受 URL 参数） | 401 |

配置为空时不校验对应项；两项都配置时先查 IP 再查令牌。失败时按统一错误格式返回 `{"code":1,"message":…,"data":null}`，不进入业务处理。

## 3. `order_json` 格式

字段沿用镁伽《订单实验检测数据上传接口文档》，不改名。接收时只校验结构：根节点是对象，`order_infos` 是非空数组，每个元素是对象且 `order_no` 非空，不符返回 400。其余字段由 §7 逐板核对，结论在 HTTP 200 的回复里给出。

对接约定：

- `data_type` 取 `PLAS`、`PCR`、`TITER`；`experiment_date` 接受 `20260527` 或 `2026-05-27`。
- 检测板 `barcode` 是镁伽检测整板条码，只存档；`sample_code` 是样本板条码，须等于下发的样品板条码。
- `whole_board_img`（`.png`）、`heatmap_csv`（「统计项」`.csv`）传相对流式结果共享根目录（`FCS_SMB_SHARE`）的路径，用 `/` 分隔，不能是绝对路径或含 `..`。
- 检测板新增 `x_axis`、`y_axis`（原文档没有）：整板图的横、纵坐标通道名，原样写入效价板卡。热图里没有纵轴通道，所以单独传。
- PC 孔另带 `pc_name`、`batch`、`generation`；`target_num`、`extend_info`、`secondary_antibody`、细胞批次代次、`mfi`、单孔图等只存档。

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
          "extend_info": "",
          "experiment_date": "20260527",
          "target_num": "20R270",
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
                  "whole_board_img": "images/xxxxx01/可视化图_xxxxx01.png",
                  "heatmap_csv": "csv/xxxxx01/热图_xxxxx01.csv",
                  "x_axis": "APC-H",
                  "y_axis": "SSC-H",
                  "well_infos": [
                    {
                      "well_no": "A02",
                      "img_path": "well/xxxxx01/A02.png",
                      "sample_name": "Sample-001",
                      "pc_name": "",
                      "batch": "",
                      "generation": "",
                      "mfi": 12345.67,
                      "ppc": 89.45
                    },
                    {
                      "well_no": "A12",
                      "img_path": "well/xxxxx01/A12.png",
                      "sample_name": "PC1",
                      "pc_name": "PC 具体名称",
                      "batch": "PC260527B01",
                      "generation": "P3",
                      "mfi": 23456.78,
                      "ppc": 96.12
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

### 5.1 已处理

文件格式合法时一律 HTTP 200、`code: 0`，核对结论在 `data` 里，按订单、检测板逐条给出：

```json
{
  "code": 0,
  "message": "success",
  "trace_id": "TRACE202605270001",
  "data": {
    "status": "partial",
    "total_orders": 2,
    "success_orders": ["ORD202605270001"],
    "partial_orders": [],
    "failed_orders": ["ORD202605270002"],
    "results": [
      {
        "order_no": "ORD202605270001",
        "status": "accepted",
        "message": "工单尚未完成",
        "boards": [
          {
            "barcode": "xxxxx01",
            "sample_code": "BAO0000001-20R090-RLBWB95-1",
            "cell_name": "CHO-S-hCD33",
            "status": "passed",
            "message": ""
          }
        ]
      },
      {
        "order_no": "ORD202605270002",
        "status": "rejected",
        "message": "订单不存在",
        "boards": []
      }
    ]
  }
}
```

| 字段 | 取值 |
|---|---|
| `data.status` | `passed` 全部通过、`partial` 部分通过、`rejected` 全部未通过 |
| `results[].status` | `accepted` 全部板通过、`partial` 部分板通过、`rejected` 整单未通过 |
| `boards[].barcode` / `sample_code` | 原样带回该检测板回传的 `barcode`、`sample_code` |
| `boards[].status` | `passed` 通过、`rejected` 未通过、`archived` 非效价工单仅存档 |
| `message` | 未通过原因与提醒，多条用 `；` 连接；没有时为空串 |

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
| 400 | 缺少或为空的 `trace_id`、缺少 `order_json`、文件为空、不是 UTF-8、JSON 不合法、根节点不是对象，或 `order_infos` / `order_no` 不符合要求 |
| 409 | 同一 `trace_id` 的上一次推送还在处理；处理被服务中断时会一直 409，在回传记录页「重新处理」后补存回复 |
| 413 | `order_json` 超过 `ORDER_SYNC_MAX_MB` |
| 422 | `trace_id` 已存在，且是本版本之前收下、没有存回复的旧记录 |
| 500 | 核对过程发生未处理异常 |

与镁伽原文档的区别：业务核对不通过不返回 422，而是 HTTP 200 并在 `data` 里逐单、逐板给出结论（原有的 `total_orders`、`success_orders`、`failed_orders` 保留，新增 `status`、`partial_orders`、`results`）；409 是新增的；请求里检测板新增 `x_axis`、`y_axis`（§3）。来源认证的 403/401 响应见 §2。

### 5.3 重推

同一 `trace_id` 再次推送时不重新核对，原样返回第一次的 HTTP 状态和响应体（含 400、500）。镁伽改了数据要重推，须换新的 `trace_id`。

## 6. 处理过程

1. `trace_id` 为空、缺少 `order_json`、文件超限时直接返回 400 / 413，不留记录。
2. JSON 原文保存到 `<REPOSITORY_ROOT>/order_sync/<YYYYMMDD>/`（`REPOSITORY_ROOT` 默认 `repository`，见 [deploy.md](../../deploy.md)），`order_sync` 登记一条 `processing` 记录并先提交。
3. 解析后从 `project_infos` 提取项目号、数据类型、实验日期、靶点作列表摘要，再逐板核对，结论写入 `order_sync.status`（`passed` / `partial` / `rejected`；格式错误 `invalid`；异常 `error`），每块检测板写一行 `order_sync_board`。回复的 HTTP 状态和响应体存进 `order_sync`，供重推原样返回。
4. 有核对通过的效价板时，回复之后在后台导入效价（§8），进度记在 `order_sync.import_status` 与各板的 `import_status`。

本版本之前收下的记录 `status` 仍为 `pending`（旧数据未核对），可在回传记录页「重新处理」。

## 7. 核对规则

对照的是这张工单**最近一次未作废下发**的 Payload 快照，不是工单当前编辑内容。

整单不通过（该单下所有板都不通过）：订单号查不到工单、对应多张工单、工单已作废、工单未下发、效价工单没有检测板。工单未完成只提醒。非效价工单（`orderType` 不是 `TITER`）整单仅存档，不导入。

效价检测板逐块核对：

| 项 | 规则 | 不符时 |
|---|---|---|
| 路径 | `whole_board_img`、`heatmap_csv` 都有、是相对路径、扩展名对 | 不通过 |
| 样品板 | `sample_code` 与某块下发样品板的 `barcode` 完全一致；`barcode`（检测板条码）不参与 | 不通过（`sample_code 为空` / `样本板 … 不在下发的样品板中`） |
| 细胞 | `cell_name` 在该样品板所选细胞里（不区分大小写） | 不通过 |
| 鼠号 | 下发为样品（SAMPLE）的孔，回传 `sample_name` 与下发样品编号一致 | 不通过（列出前 8 个） |
| 效价实验 | 由工单关联的效价订单找到实验；没有时按样品板项目号找 | 不通过 |
| 缺孔 | 下发有样品、回传没有该孔 | 提醒 |
| 靶点 | 回传 `target` 与样品板靶点不同 | 提醒 |
| 实验日期 | 无法识别 | 提醒，不写检测日期 |
| 坐标 | `x_axis`、`y_axis` 未填 | 提醒，板卡坐标留空 |
| 重复 | 同一推送里同一样品板 + 细胞出现多次 | 提醒，后面的覆盖前面的 |

## 8. 导入效价

每块通过的效价板对应效价实验里的一张流式板卡，按「工单 + 样品板 + 细胞」认定是同一张：

1. 从流式结果共享（SMB，`FCS_SMB_*`，见 [deploy.md](../../deploy.md)）下载可视化图 png 和热图 csv，网络异常最多尝试 3 次；未配置共享、文件为空或超过上传上限时不重试，该板记「下载失败」。
2. 两个文件存进效价文件（来源「镁伽」，上传人「镁伽回传」）；同一张板再次回传时原地替换上次的镁伽文件。
3. 解析热图：取 %Parent 表（全部 ≤ 1 时按比例 ×100），大于 15% 为阳性孔；横纵坐标取回传的 `x_axis`、`y_axis` 原样，仪器类型国产。与回传 `ppc` 不一致时以热图为准并提醒。
4. 板卡写入：二维码 = 样品板条码，细胞标靶按细胞名 + 批次匹配（没有则新建），上下排鼠号与 NC/PC 按下发样品板，分组按实验的免疫分组，PC 按下发 `pc_infos` 匹配或新建。实验日期追加到效价订单的检测日期。

不覆盖人工内容：

| 情况 | 结果 |
|---|---|
| 板卡在页面上保存过（来源转为手工） | 不覆盖，该板记「未覆盖」 |
| 镁伽文件被替换或重命名（来源转为手工） | 不再复用，下次回传另存新文件 |
| 镁伽生成的板卡被删除 | 下次回传或重新处理时重新生成 |

导入失败只影响该板，可在回传记录页「重新处理」：按存档原文和当前数据重新核对、重新导入，当初回给镁伽的回复不变；还没回复过的「处理中」记录会补存这次的回复。服务重启会丢掉尚未跑完的后台导入（进度停在「待导入」或「导入中」），同样用「重新处理」补上。
