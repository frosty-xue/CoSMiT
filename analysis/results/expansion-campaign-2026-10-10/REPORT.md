# 110 个候选：基线实验进度（2026-10-10）

## 范围

复用 research-data/2026-09-17 中排除 D0028 后的 80 个候选；扩充仅使用 datasets/expansion-2026-09-18。
扩充集调用现有 prepare_llm_jobs 的五类提示模板，全部 64 个输入和三次重复观察均保留。
源参考输出、人工标签、CoSMiT/DLLens 判断没有放入模型提示。
当前评估范围为登记操作契约；不等于完整迁移测试断言的意图保持。

## 已完成的本地计算

| 项目 | 扩充 30 组 | 合并 110 组 |
| --- | --- | --- |
| CoSMiT 当前核心，保存观察回放 | 26 支持、2 反驳、2 未决 | 106 支持、2 反驳、2 未决 |
| DLLens 固定 dense 比较器 | 28 未发现数值差异、2 未决 | 108 未发现数值差异、2 未决 |
| 正常执行自测试 | 28 通过、2 失败 | 108 通过、2 失败 |
| DocTer 历史字面约束 | 9 满足、10 违反、11 未决 | 45 满足、11 违反、54 未决 |

DocTer 重新计算了全部 110 个候选的逐输入结果，不重复调用模型。98 个候选有约束文件；12 个缺少已冻结映射。
历史约束来自 PyTorch 1.5 / TensorFlow 2.1，与实际框架版本的兼容性未建立。
DocTer 的“违反”表示其历史约束检查结果，不能直接作为迁移意图违反或人工真值。

## 一项必须保留的实现差异

之前的行为审计发现 E020、E029、E030 三个问题，此结论仍成立。
但本次实际调用 src/cosmit/engine/certification.py 的 evaluate，并沿用已有 worker 的调用绑定门槛，
E020 会得到未决：perm=None 在真正调用 permute 之前发生参数解包异常，目标调用列表为空，核心先检查绑定而未进入异常违反分支。
因此不能把“三个已复现的行为问题”直接写成“当前 CoSMiT 核心检测出三个”。
当前核心反驳 E029、E030；E020 和 E021 未决。没有为了提高本批结果修改核心。
DLLens 这里仅运行固定数值比较器；E020/E029 异常没有数值比较，不能据此声称完整 DLLens 漏报。

## 模型实验与重试

模型 DeepSeek-R1，temperature=0、top_p=1、presence_penalty=0、max_tokens=4096、并发 2。
补充轮次以各自 configuration.json 为准：repair-round-02 对已证实 length 截断的两个请求单独使用 8192；不能将该预算结果当作原始 4096 预算结果。
初始 E001 五类请求因连接错误失败，额外一次短请求重试也发生 SSLEOFError；全部记录保留。
用户随后授权失败重试：仅连接/超时类故障最多四次物理尝试（含已有尝试），间隔 5/15/30 秒。
不因模型给出否定结论而重试，不自动重试正常返回后的截断、格式错误。
首次尝试与含重试视图分别写入 combined-110-results.json，不能混合当作同一固定预算实验。

原批次进度见 progress.json；补跑后的累计覆盖见 coverage-current.json，补跑进度见 repair-*/progress.json。
physical-attempts 保存全部物理请求；requests 仅是原批次缓存，补跑后的有效结果以 combined-110-results.json 的 retry-view 为准。
repair-*/offline-format-recovery.json 单独保存完整 fenced JSON 的离线恢复，不覆盖严格解析结果。
当前进度不是完成报告。缺失 usage 不代表零费用；准确率、召回率仍需独立限域参考标签。

生成此报告时，扩充集调用记录：

```json
{
  "physical_attempts": 196,
  "diagnostic_attempts": 1,
  "total_model_requests_including_diagnostics": 197,
  "completed_attempts": 89,
  "reported_tokens": 736802,
  "usage_unavailable_attempts": 102
}
```

累计请求覆盖（含补跑）：

```json
{
  "planned_jobs": 150,
  "attempted_jobs": 96,
  "successful_jobs": 89,
  "failed_jobs": 7,
  "not_attempted_jobs": 54,
  "supplemental_rounds": [
    "repair-round-01",
    "repair-round-02"
  ],
  "counts_by_kind": {
    "direct-llm": {
      "failed": 3
    },
    "intenttester-source-tdl": {
      "failed": 1,
      "completed": 29
    },
    "intenttester-target-api": {
      "completed": 30
    },
    "intenttester-target-tdl-extension": {
      "completed": 30
    },
    "trace-llm": {
      "failed": 3
    }
  }
}
```
