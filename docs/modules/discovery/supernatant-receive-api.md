# 上清板布局接收接口
> 合成公司发货时推送蛋白上清的板布局（每孔的蛋白名称与浓度等）；校验后保存，并按订单号给合成与验证工单写发货日期和发货个数，尚未关联流式工单。相关：[合成与验证](./synthesis-progress.md) · [镁伽流式工单](../mega-automation/flow-work-order.md)

## 1. 接口

```text
POST /api/protein-supernatant/receive
Content-Type: application/json; charset=utf-8
X-Callback-Token: {token}
```

来源认证与 [工单数据回传](../mega-automation/order-experiment-sync-api.md) §2 相同，配置项为 `SUPERNATANT_RECEIVE_TOKEN`、`SUPERNATANT_RECEIVE_IPS`（见 [deploy.md](../../deploy.md)）。

## 2. 请求体

字段名不区分大小写（对方文档同一字段有 `samplename`、`sampleName` 等写法）；未列出的字段（如 `organCode`）忽略。

| 层级 | 字段 | 必填 | 规则 |
|---|---|---|---|
| 外层 | `orderNo` | 是 | 合成订单号，最长 64 |
| 外层 | `corpName` | 是 | 合成公司，最长 64 |
| 外层 | `data` | 是 | 非空数组，每个孔一条 |
| `data[]` | `plateno` | 是 | 板号，最长 128（君跻旧板号形如 `订单号-GSZB00159/20R246_RMBWB02B11_Protein Supernatant-A`，超过 64） |
| `data[]` | `wellno` | 是 | 96 孔板 `A1`-`H12`，`A01` 写法与小写也接受，统一存为 `A01`；「未合成」见 §3 |

推送方：擎科 `corpName` 为「擎科生物」；君跻 `corpName` 固定 `GentleGen`，订单号形如 `CN2611240000481`。`corpName` 原样保存。
| `data[]` | `sampleName` | 是 | 蛋白名称，最长 128 |
| `data[]` | `potency`、`specs` | 是 | 浓度 ug/mL、规格 mL/支。数字规则同下；蛋白推送里不适用时传 `/`（全角 `／` 同样），存为空。不要用 `0` 占位 |
| `data[]` | `volume`、`sampleEnterVol` | 是 | 体积 mL、质粒量 ug；字符串或数字，非负且小于 10^12，四舍五入保留 4 位小数。`/` 不接受 |

示例：

```json
{
  "orderNo": "BAO0000900",
  "corpName": "擎科",
  "data": [
    {"plateno": "20261118-JH001", "wellno": "A1", "sampleName": "20R200_RMBKD1AAKE23_h1.0",
     "potency": "100", "specs": "2", "volume": "20", "sampleEnterVol": "2"}
  ]
}
```

## 3. 保存规则

- 每个孔存一行 `synthesis_supernatant_well`：`order_no`、`corp_name`、`plate_no`、`well_no`、`sample_name`、`not_synthesized`、`potency`、`specs`、`volume`、`sample_enter_vol`，`order_no` + `plate_no` + `well_no` 唯一，`sample_name` 有索引。
- 一单可以分几批推，同一块板拆在不同批里也会累加。同一订单号 + 板号 + 孔号再次推送时覆盖该孔，可安全重发；不会删除本次没带的孔。同一板号出现在不同订单号下互不影响。
- 任一条不合格整次不入库；同一板内孔号重复也算不合格。错误信息列出前 10 处，格式如 `data[3]：wellno「A13」不是 96 孔板孔号（A1-H12）`。
- 每次推送记一条操作日志「接收上清板布局」，成功与否按 HTTP 状态判定；被拒时日志记下返回给对方的原因。
- 孔号写「未合成」或 `noShipping`（擎科），或板号写「未合成」、孔号写 `0`（君跻）的行是没合成出来的样品，不在板上。只校验样品名，其他字段（对方会填 `M`、`0`）不校验也不保存。按订单号 + 样品名记一行，`not_synthesized = 1`，板号、孔号、数值为空。重复推送不重复记。同一样品之后出现在板上时去掉这条标记；已经在板上的样品再收到「未合成」不覆盖孔位。只有这类行时也返回成功。
- 合成与验证下载版布局时，未合成的样品排在最后，孔号列显示「未合成」。
- 合成与验证的发货日期、发货个数只从这里来：某订单号收到孔位（不是只有未合成）时，把同订单号、`合成到货`、未完成未取消的工单发货日期写成该订单第一批孔位的接收日期，发货个数写成该订单当前在板的蛋白数（按样品名去重：君跻有的单同一批蛋白同时挂在新旧两个板号下，按孔数会翻倍），状态随之推导；规则见 [合成与验证](./synthesis-progress.md) 的 One 同步说明。

## 4. 响应

按合成公司约定 `code` 为 1 成功、0 失败（与本系统统一响应相反），所有情况都由接口自己返回，不走全局异常格式：

| HTTP | 响应 | 条件 |
|---|---|---|
| 200 | `{"code":1,"msg":"success","data":null}` | 保存成功 |
| 400 | `{"code":0,"msg":"<原因>","data":null}` | 不是 UTF-8、JSON 不合法、根节点不是对象或字段校验不通过 |
| 401 / 403 | `{"code":0,"msg":"调用方校验失败" / "调用方不在允许列表","data":null}` | 令牌或 IP 不符 |
| 500 | `{"code":0,"msg":"服务端异常，请稍后重试","data":null}` | 未预期异常，已回滚；对方应重试 |

## 5. 对方查询接口

两家合成公司都提供按订单号查询的接口，一次只能查一个订单号，成功返回 `code: 1`，`data` 与推送请求体结构相同（含未合成样品）：

- **擎科**：`POST http://172.16.1.177:8088/baiao/api/query-protein-clear-plate-layout-push`，请求头 `X-Callback-Token` 与本接口相同，请求体 `{"orderNo": "BAO0001130"}`（不区分大小写）。订单不存在时返回 `code: 0` 和「订单不存在：订单号」。单次约 2–6 秒，大订单可能更久。
- **君跻**：`POST http://192.168.99.120:8080/Delivery/ProteinQuery`（没有 `/api`，对方文档总览表里的路径是旧的），令牌是君跻单独给的，与推送令牌不同。订单号须为 14 位以上大写字母和数字，本系统查询时统一转大写。没发货的单返回 HTTP 200 + `code: 0`「订单不存在：xxx」，文档另列的「订单数据为空（尚未发货）」也是 200 + `code: 0`；订单号格式不对文档写 400，实测是 200 + `code: 0`「订单号格式不合法!」；令牌不符 401，服务端异常 500。空孔和已取消的板、样品不返回。单次约 0.5 秒，返回的孔数与 One 记的到货个数一致。

本系统通过 `SUPERNATANT_QUERY_URLS`（`合成公司=地址`，英文分号分隔）配置查询地址，`SUPERNATANT_QUERY_TOKENS`（`合成公司=令牌`）配置各家令牌，没配令牌的沿用 `SUPERNATANT_RECEIVE_TOKEN`。回复里有「不存在」，或 HTTP 200 且有「为空」「未发货」「尚未」时算未发货，其余 `code: 0` 算查询失败并原样提示原因。在两处调用：合成与验证的定时任务「合成公司上清补查」，以及工单抽屉版布局弹窗里的「刷新」（见 [合成与验证](./synthesis-progress.md) §6、§7）。补查和刷新按合成公司订单号，不限订单性质和供应方式；`TRF-` 转染工单号不查。查到的内容按 §3 入库，与推送的区别是：已有发货日期的工单不改日期，发货个数照常更新，并且这两项仍只写到 `合成到货` 工单。没有配查询地址的合成公司只能等对方推送。
