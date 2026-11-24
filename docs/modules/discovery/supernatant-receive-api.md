# 上清板布局接收接口
> 合成公司发货时推送蛋白上清的板布局（每孔的蛋白名称与浓度等）；当前只校验并保存，尚未关联合成与验证工单或流式工单。相关：[合成与验证](./synthesis-progress.md) · [镁伽流式工单](../mega-automation/flow-work-order.md)

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
| `data[]` | `plateno` | 是 | 板号，最长 64 |
| `data[]` | `wellno` | 是 | 96 孔板 `A1`-`H12`，`A01` 写法与小写也接受，统一存为 `A01` |
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

- 每个孔存一行 `synthesis_supernatant_well`：`order_no`、`corp_name`、`plate_no`、`well_no`、`sample_name`、`potency`、`specs`、`volume`、`sample_enter_vol`，`order_no` + `plate_no` + `well_no` 唯一，`sample_name` 有索引。
- 同一订单号 + 板号再次推送时整板覆盖（先删该板原有各孔再写入），可安全重发；同一板号出现在不同订单号下互不影响。
- 任一条不合格整次不入库；同一板内孔号重复也算不合格。错误信息列出前 10 处，格式如 `data[3]：wellno「A13」不是 96 孔板孔号（A1-H12）`。

## 4. 响应

按合成公司约定 `code` 为 1 成功、0 失败（与本系统统一响应相反），所有情况都由接口自己返回，不走全局异常格式：

| HTTP | 响应 | 条件 |
|---|---|---|
| 200 | `{"code":1,"msg":"success","data":null}` | 保存成功 |
| 400 | `{"code":0,"msg":"<原因>","data":null}` | 不是 UTF-8、JSON 不合法、根节点不是对象或字段校验不通过 |
| 401 / 403 | `{"code":0,"msg":"调用方校验失败" / "调用方不在允许列表","data":null}` | 令牌或 IP 不符 |
| 500 | `{"code":0,"msg":"服务端异常，请稍后重试","data":null}` | 未预期异常，已回滚；对方应重试 |
