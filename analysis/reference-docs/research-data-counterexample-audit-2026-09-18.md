# 已完成实验的反例审计

日期：2026-09-18。范围仅为 `research-data/2026-09-17` 及其关联的原始公开函数和运行记录。之前构建的 `datasets/migration_verification_v1` 和旧 RQ 实验不纳入当前结论。本次没有新增实验候选，没有调用模型，也没有修改已有的冻结结果。

## 审计结论

**81 条公开候选中，目前确认的有效行为反例仍是 D0028，对应 1 个错误 counterpart。** 它在本次审计前半程已完成原始代码校验与动态重放；本次又核验了全部归档判定，没有发现被遗漏的已记录行为反例。

其余负向结果必须按原因区分：4 条人工错误控制、2 条目标调用缺失控制、2 条源断言无效控制、模型否定判断，以及补充实验里的源模型不可执行。它们不能相加作为真实迁移错误数量。

| 对象 | 审计结果 | 可支持的结论 |
| --- | --- | --- |
| D0028 | 代码哈希匹配，192 对重放与归档一致；30 个输入、90 对执行违反 value | 1 个外部公开 counterpart 存在负整数处理错误 |
| 其余 80 条公开候选 | 源／目标函数哈希匹配；归档输入、源参考、条款结果、重复稳定性和汇总均复核通过 | 在登记输入与条款下没有已记录行为反例；不证明全域正确 |
| C002/C003/C007/C008 | 从原始构造器恢复代码，哈希匹配；重新执行后与归档一致 | 检查器能识别既有 shape/value 人工控制 |
| C004/C009 | 重放确认输出存在，但没有目标调用 | 目标绑定证据缺失，应为 undetermined，不是行为反例 |
| C005/C010 | 重放确认源断言失败 | 无效源测试，应排除出有效迁移反例 |
| 8 条公开候选的模型否定判断 | 归档存在，但未附可执行 witness，理由被导出过程省略 | 待核实线索；不能算新增反例或已确认模型误报 |
| BESSER CNN-RNN | 归档报错发生在源模型，形状推导与报错吻合 | 源契约不可执行，不是目标迁移错误 |

## 做了哪些核查

对 discovery、unseen、controls 的全部 **91 条候选、15,612 对观察**逐条检查：

- case/input/repeat 身份完整、无重复；每个登记输入都有 3 次运行。
- 输入满足各分组登记域，重复的源／目标观察稳定。
- 对 15,600 个源端成功观察重新计算登记参考；另 12 个观察来自源断言无效控制，不强行计算数值参考。
- 从实际归档观察重新计算 value/shape/dtype 条款、目标绑定门槛和 DLLens 的 dense 数值比较结果；核对条款内嵌观察与行级观察。
- 重新汇总候选 verdict，与 cases.json 一致。
- 81 条公开候选的两侧函数字符串 SHA256 均与本地 DLLens 对应文件一致。

上述检查没有发现不一致。这里的“重新计算”是对保留输出的审计，复用登记参考定义与容差，不是重新执行全部框架程序，也不是独立人工 gold。

对现有 10 条 controls，使用项目原来的 `build_development_packet.py` 恢复代码，要求两侧代码哈希、reviewed_code 哈希、输入和契约与归档相同后才执行。在 PyTorch、TensorFlow 独立环境共运行 **120 次单侧执行，即 60 对**；输出、shape、dtype、调用记录或异常类型与历史一致。恢复控制代码是重放步骤，没有增加数据集条目。

## D0028 的有效性与计数

源为 `torch.trunc(input)`，目标为 `tf.where(input >= 0, tf.floor(input), tf.floor(input) + 1)`。DLLens 固定提交为 `0f617e92c34d60bfdd3bc06d80c17d938879ed9c`。

float32 标量 `-8` 是直接证据：源输出 `-8`，目标输出 `-7`。负整数 n 的 floor(n)+1 等于 n+1，向零截断应保持 n，因此这是候选逻辑错误，不是容差问题。全部输入位于登记的有限 [-8,8] 域；30 个失败输入恰好都是含有负整数的输入，其余输入没有登记条款违反。此条件核对覆盖全部 64 个输入。

此前实际重放 64×3=192 对，value/shape/dtype 与历史逐条一致。本次复用该重放证据，未为增加计数重复执行。应报告 **1 个错误候选、30 个失败输入、90 对重复失败执行**，不能报告 90 个缺陷。

这是 API counterpart 错误，不能自动扩大为“完整迁移测试的断言不保持”。同输入 DLLens 比较器也检出了该错误，因此本批实验尚无相对该比较器的额外发现。

## 模型和其他方法的负向结果

主记录中有以下 8 条公开候选、9 个否定判断；单次传输重试记录未增加新的公开候选否定判断：

| 候选 | 映射 | 否定判断来源 |
| --- | --- | --- |
| D0011 | torch.exp → tf.exp | target-api |
| D0012 | torch.expm1 → tf.exp 组合 | target-api |
| D0030 | tf.acos → torch.acos | source-tdl |
| H003 | torch.det → tf.linalg.det | source-tdl |
| H008 | tf.matmul → torch.matmul | target-api |
| H010 | tf.linalg.trace → torch.diagonal 组合 | source-tdl |
| H011 | tf.cumsum → torch.cumsum | direct-llm 的 invalid-assumption；target-tdl-extension |
| H012 | tf.math.cumprod → torch.cumprod | target-api |

这些候选的归档运行均通过登记条款。有限输入通过不能排除模型指出其他适用域或假设问题；但仅有 `valid:false` / `invalid-assumption` 也不能证明存在迁移错误。需要师兄保留的原始模型响应、对应 prompt 和逐候选结果，才能审查其具体理由。当前导出不足以完成这一步，本次没有猜测理由或重新请求模型来替换原结论。

455 个主请求中 177 个 failed，是请求／输出解析失败，不是 177 个迁移反例。33 次重试单列；没有将模型判断当作 ground truth。

DocTer 在 unseen 汇总中的 1 个 violated 是历史约束判定，不是源／目标输出差异。导出没有逐候选约束检查明细，暂不能定位具体条款；应保留为待核实方法输出，不算有效行为反例。

## 补充实验与证据边界

4 个网络的 24 对保留输出重新计算了 shape、finite 和最大绝对误差。最大误差分别为 tf_tutorial `2.2351741790771484e-8`、LSTM `0`、AlexNet `6.891787052154541e-8`、VGG16 `6.332993507385254e-8`，与记录一致，均小于这些实验的绝对容差 `1e-6`。没有从这些输出中发现反例。本次未恢复权重或重跑网络，dtype 也不能仅靠 JSON 数值重新证明。

TensorScope 的 192 组三端观察逐条满足 source=ONNX=PyTorch=整数 abs 参考；未重新执行 ONNX 转换流程。它没有新增反例。

CNN-RNN 的源模型在输入长度非 50 时通道不匹配；长度 50 时卷积／池化／拼接形成末维 46，而 GRU 要求 400。归档的 49、50、51、100 长度报错符合该推导，但本次没有恢复原模型代码并动态重放，故维持“归档源端失败”，不升级为目标错误。

冻结数据的字节完整性问题仍在：3 个 gzip 哈希一致，32 个文本文件仅在 CRLF→LF 后一致。本次未改写原始文件，也不宣称全部原始字节哈希通过。当前重放环境为 Python 3.11.16、NumPy 2.4.6、PyTorch 2.9.1+cpu / TensorFlow 2.20.0；历史主运行 NumPy 为 2.1.3，属于跨环境结果复现。

## 产物与后续

- 可随项目保留的逐候选账本和结论：`research-data/audits/2026-09-18/`，含 91 条 case ledger、81 条来源校验、模型否定判断清单、D0028 重放摘要和 SHA256。
- 当前审计脚本：`benchmark/baselines/audit_recorded_counterexamples.py`。
- 完整控制重放与本次归档复核：`artifacts/research-data-audit-20260918-final/`。
- D0028 原始重放证据：`artifacts/counterexample-audit-20260918/external-and-legacy-final/`，本次只引用其中 D0028 部分。

复现本次审计（输出目录必须不存在）：

```powershell
& F:/environment/python/miniconda3/envs/torch291/python.exe benchmark/baselines/audit_recorded_counterexamples.py --output artifacts/research-data-audit-new --dllens F:/codes/python/DLLens --pytorch-python F:/environment/python/miniconda3/envs/torch291/python.exe --tensorflow-python F:/environment/python/miniconda3/envs/tf220/python.exe
```

现有材料内的反例核验已完成。尚不能结案的是模型否定理由、DocTer 逐条约束明细及补充源模型的动态复验，它们缺少关联原始产物。后续若扩大实验，应沿用师兄的现有流程和登记方式增加迁移条目；之前的小数据集不再进入这条工作线。
