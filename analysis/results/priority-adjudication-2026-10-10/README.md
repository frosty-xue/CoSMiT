# E020 / E029 / E030 裁决证据包

日期：2026-10-10。完成规格、原断言、候选代码、参数适配、源端资格和失败重放记录的连接。三个案例均可形成**有规格和执行证据支持的限域行为违反判断**。本轮是已知方法结果后的非盲复核，不是独立人工 gold；不更新总体准确率、召回率或缺陷数量。

## 1. 裁决结果

| 案例 | 可冻结的证据结论 | 测试层面的结论 | 当前不得扩大的结论 |
|---|---|---|---|
| E020 | 默认 perm 的行为在记录的 16 个输入上被违反 | 保留上游 testTranspose2DAuto 的构造替换测试在目标操作处失败 | 不是断言删除；不是只能靠 CoSMiT 才能发现的错误 |
| E029 | 合法单侧 None 界限在记录的 16 个输入上被违反 | 保留 test_clamp 的构造替换测试在目标操作处失败 | 不代表所有 clip 输入错误；不是外部历史迁移测试标签 |
| E030 | 标量输出形状在记录的 16 个输入上被违反 | 新增规格派生形状断言在保存观察上拒绝这些目标结果 | 不证明原二维测试丢失意图；不是新的独立评测样本 |

每份 `E*-dossier.json` 保存完整源规格、counterpart、保留测试正文、16 个见证输入、96 条相关源/目标主执行记录，以及6条保留测试正常模式记录。其他模式的判断见 retained_verification；反例无包装复验由本次再次通过的动态离线核验确认。

## 2. E020：默认转置

### 证据链

1. 保存于原运行档案的 TensorFlow 2.20.0 `tf.transpose` docstring 规定：未给出 perm 时按反向轴序转置。
2. 原函数 `tensorflow_call(a, perm=None, conjugate=False)` 将参数直接传给 tf.transpose。
3. 保留上游 `testTranspose2DAuto` 使用 `[[1,2,3],[4,5,6]]`，未传 perm，并断言结果等于 `[[1,4],[2,5],[3,6]]`。这是默认参数义务的直接测试证据。
4. 操作替换适配器只补入默认 `perm=None`、`conjugate=False` 并转换张量；没有将合法默认输入变成其他参数。
5. 目标原代码执行 `a.permute(*perm)`。None 不能被解包为轴序，错误发生在 counterpart-execution 阶段。
6. 保留源测试正常模式三次均通过；目标三次均为 TypeError。动态批次另有 16 个源端合格输入，失败三次稳定，并通过无包装原函数复验。

### 裁决

行为违反的限域结论成立。默认调用应产生转置输出，目标却无法正常返回。构造替换测试也无法完成源测试的检查义务，但源/目标断言表达式仍保留，不能命名为“断言丢失”。普通正常执行检查已能发现该错误，不能用它证明高级意图检查的增量能力。

动态批次与保留方法使用不同输入，应分别引用；不能声称同一输入覆盖了两层实验。异常文本中包装函数名与 Tensor.permute 的差异已由原核验器限定规范化，其余错误类型与 None 解包诊断保持一致。

## 3. E029：单侧裁剪界限

### 证据链

1. 保存的 torch.clip docstring 指向 torch.clamp；clamp 规定 min=None 表示没有下界，max=None 表示没有上界。
2. 原函数保留 `min=None, max=None` 默认值，直接调用 torch.clip。
3. 上游 `test_clamp` 先后断言双侧裁剪、`x.clamp(min=lb)`、`x.clamp(max=ub)` 及广播结果。单侧界限不是为触发异常而虚构的源端用法。
4. 适配器把未提供的一侧保留为 None；目标函数却无条件对 min 和 max 执行 tf.cast。
5. 已保存的首个动态见证为 input_index=24：源端正常返回，目标在对 max 的 tf.cast 处失败。另一类单侧 None 也纳入16个见证，全部通过无包装复验。
6. 保留源方法以 CPU、float64 配置三次通过；目标三次在 counterpart-execution 阶段发生 ValueError。原方法中的断言仍存在，失败并非 assert 表达式被删。

### 裁决

源端允许的单侧裁剪行为在这些输入上未被保持。可将其作为限域行为错误与构造替换测试正常运行失败的证据。不能扩展为 TensorFlow 自身缺陷，也不能将未执行完的后续广播断言记为“全部被验证”。

## 4. E030：补齐标量形状的检查义务

### 上游测试检索

检查了本地固定版本 `upstream/tf_clip.py` 中 ClipTest 的 ClipByValue 相关方法，并保存方法名、行号和全文到 `E030-upstream-search.json`。

- `testClipByValue` 和几类 Type 测试主要使用 2×3 输入。
- `testClipByValueGradient` 确实包含标量输入，但检查的是梯度；不能把它当成标量前向输出形状断言，也不能用当前数值桥接声称验证了梯度。
- `testClipByValueBadShape` 检查非法广播形状的异常，不能替代合法标量输出的形状保持。

在此次检查的文件与方法范围内，没有建立可直接复用的“合法标量输入→前向标量输出形状”测试对。此结论不代表整个上游仓库不存在这类测试。

### 规格到断言

保存的 `tf.clip_by_value` docstring 明确要求输出保持 t 的形状。因而对标量 t，期望输出形状为 []。目标中的 `clip_value_max.new_ones(1)` 引入长度1维度，已有见证表现为源输出0.0、目标输出[0.0]。

本轮新增一个明确标记为**事后构造、规格派生**的断言：

```python
assert observed['status'] == 'ok'
assert observed['shape'] == input_shape
```

该断言独立作用于源端和目标端保存的观察，以输入形状为期望，不用源输出作为目标形状答案。对 E030 全部64个冻结输入、每个3次记录重放：

| 侧别 | 断言通过记录 | 断言拒绝记录 | 不同拒绝输入 |
|---|---:|---:|---:|
| 源端 | 192 | 0 | 0 |
| 目标端 | 144 | 48 | 16 |

拒绝输入集合与原有16个标量反例完全一致。这里只对384条已有观察执行了 Python 断言，**新增框架调用为0**，没有新增候选或问题。完整结果见 `E030-constructed-assertion-replay.json`。

### 裁决

已经建立“源规格→标量形状义务→显式断言→已有反例触发断言”的证据链。这足以加强行为形状检查的解释，但仍不能说明原始2×3上游测试的检查意图被迁移丢失。若后续把构造测试纳入正式评价，应独立冻结其来源和范围，并使用未依据已知结果挑选的评价集。

## 5. 标签与后续指标

机器记录分别保留：

- `scoped_behavior_decision=violated-on-documented-witness-inputs`：限于已记录见证的证据判断。
- `constructed_test_baseline_decision`：E020/E029 目标失败，E030 在登记2×3输入上通过。
- `full_historical_test_intent_label=null`：没有补造成真实历史迁移测试标签。
- `independent_gold=false`、`blind_review=false`、`independent_evaluation_eligible=false`：不把已知反例后复核当成独立评测。

本次可冻结的是材料快照与适用范围。合并统计仍为110个候选、3个已知行为问题、1个绑定未决；不产生新的召回率分母。下一步应把27对构造测试的具体义务逐项整理，明确评价范围，并补充有证据支持的保持案例和可执行但丢失检查能力的错误案例，形成独立于方法输出的参照集。

## 6. 复现

```powershell
python benchmark/baselines/build_priority_adjudication.py artifacts/analysis/priority-adjudication-rerun
```

需要 NumPy，输出目录须尚不存在。脚本只读取批准的 expansion 目录，调用只读动态与保留正文离线核验函数，不触发框架或模型调用。`input-hashes.json` 保留直接消费文件哈希；源动态运行的全档案哈希由原核验器再次检查。未修改已有数据、标签表或论文。
