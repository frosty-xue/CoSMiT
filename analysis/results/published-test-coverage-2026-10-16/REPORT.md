# 现有 110 组的公开迁移测试材料核查

核查日期：2026-10-16。范围：原主集 80 组及 expansion-2026-09-18 的 30 组；不使用其他废弃 datasets，不使用 D0028。

## 结论

**尚未完成用户要求的 110 组真实迁移前后测试补齐。** 本次补回 110 组作者原始 counterpart JSON、1,568 条源框架输入代码片段、两侧操作函数，以及公开比较器和相关缺陷复现脚本。它们是可追溯的实验材料，但不是 110 对已有完整测试。

当前已核实“完整源测试 → 作者公开迁移目标测试，且对应现有被测 counterpart”的数量仍为 0。这里的 0 是本次核实结果，不是断言公开世界中不存在这些测试。没有把未找到记作迁移失败，也没有把缺失测试记作意图不保持。

完整逐组清单见 [COVERAGE.md](COVERAGE.md)，机器可读记录见 [candidate-coverage.json](candidate-coverage.json)。材料在 [published-test-intake](../../../research-data/2026-10-16/published-test-intake/)。

|材料|本次核实情况|可以支持什么|
|---|---:|---|
|110 组 DLLens 原始 JSON|110/110 下载成功|原函数配对和输入来源|
|作者源框架 sample_inputs|1,568 条，110/110 非空|输入条件、边界和后续复现准备；不是实际执行次数|
|作者两侧操作函数|110/110 原文提取|被迁移操作的上下文|
|带迁移前后独立测试检查的完整历史配对|0 组核实完成|目前不能据此做完整意图保持标注|
|CrossProbe API 出现线索|4 个候选 ID|仅检索线索，不是 4 对合格测试|

输入片段中有随机生成表达式，1,568 不是固定输入向量数量；也没有新增实验执行或模型调用。原文提取没有添加 imports、调用、断言、转换逻辑。旧的 27 组构造测试仍保持原先的 constructed 身份。

## 来源调查

### DLLens：与 110 组最直接相关，但缺少历史完整测试文件

原始提交：`0f617e92c34d60bfdd3bc06d80c17d938879ed9c`。见 [作者仓库](https://github.com/maybeLee/DLLens/tree/0f617e92c34d60bfdd3bc06d80c17d938879ed9c)。所有 110 组按现有 candidate-index 中的原始 URL 回取，不以 API 相似性替换来源。

JSON 保存 `sample_inputs`、`counterparts` 等字段。下载了作者 `codes/counterpart/evaluate_counterpart.py`、程序生成和测试代码，以及公开缺陷复现文件。共同比较器对数组 squeeze/flatten 后使用 allclose；它不是逐条源测试断言迁移的记录。作者公开 README 明确当前只包含部分代码及实验结果。

不能把“输入片段 + 函数 + 比较器”重新拼装为测试，再称为作者已经迁移的测试。也不能因为有比较器就预设所有源测试的意图仅为数值相同。下一步最有价值的是索取这 110 个条目的实际两侧执行脚本、输入对应和原始检查条件。

### CrossProbe：有公开脚本配对，当前 110 组的覆盖不足

[作者仓库](https://github.com/CrossProbe2024/CrossProbe)、[公开发布版本](https://zenodo.org/records/15201811)。当前快照提交 `7a413c2ab34e160f98b3d7751c960f447e9f5717`；另核对 `2025-04-12` 标签的完整文件树（6,534 文件，未截断），标签没有额外的大型迁移测试输出目录。

当前快照有 26 对按生成流程和同相对文件名关联的脚本，另有 8 条源目录中同 issue 编号的 `-tf` 文件关联线索，合计 **34 条配对线索**，不是 34 个独立、有效的测试。后 8 条的历史迁移关系仍需原 issue 或日志证明。11 条线索的目标脚本静态语法解析失败；未修复或执行原文件。

API 出现检查使用 AST 导入别名解析、精确调用名匹配，不做同义 API 扩展，也不推断张量实例方法类型。因此不是所有语义相关性的穷尽搜索。

|候选|公开线索|为何不能直接补入旧结果|
|---|---|---|
|D0062 `tf.sigmoid`|`pytorch/pt-124252-tf.py` → `tensorflow-test/pt-124252-tf.py`|sigmoid 是交叉熵示例的辅助处理；目标文件语法有误，独立 sigmoid 测试目标没有得到证明|
|E018 `tf.reshape`|`tensorflow/tfmot-1062.py` → `pytorch-test/tfmot-1062.py`|模型量化/通道重排上下文；目标调用 tensor.reshape，而旧 counterpart 是 view；不能沿用旧结果|
|E020 `tf.transpose`|同一个 tfmot-1062 配对|目标原文调用多参数 tensor.transpose，与旧 counterpart 的 permute 路径不同|
|E026 `tf.concat`|同一个 tfmot-1062 配对|有 concat/cat 对应，但全测试目标是模型构建和量化，不能仅凭这个局部映射标注意图保持|

tfmot-1062 目标文件还将量化实现写为返回原模型的占位函数。这是值得研究的意图变化线索，不能直接归因于 E018/E020/E026 中某一个 API。源脚本能否在声明环境完成、模型量化的原始预期、目标早期语法失败和后续语义问题应分别记录。即使是失败迁移也可以成为研究对象，但须先明确源测试和实验单位，不能把它当作成功迁移后才检测到的 API 行为偏差。

### 其他论文及工件

|来源|查到的公开材料|本次对 110 组的适用性|
|---|---|---|
|[TensorScope](https://github.com/tensorscopepro/Tensorscope)|21 个文件，下载 src；有 TF→ONNX→PyTorch 模型转换测试驱动|`tf2torch_op_test.py` 示例是 tf.raw_ops.Abs，目标模型需转换产生；没有得到当前 110 个 DLLens counterpart 的现成完整测试对|
|[TransFuzz](https://github.com/transfuzz/transfuzz)|主仓库和 transfuzzbak 各只有一个 README|未获得测试代码；需向作者索取|
|[OPERA，ICSE 2025](https://github.com/ShenQingchao/OPERA)|227 文件，已存树和 README；公开库测试到编译器的迁移工件|迁移目标是 TVM/OpenVINO/TensorRT，不是本批 TF/PT 对应函数；不能填充现有方向|
|[EAGLE，ICSE 2022](https://github.com/lin-tan/eagle)|README 描述规则驱动等价图测试；递归树返回 truncated=true|不能将同框架等价图当作跨框架历史迁移；此次未穷尽全部文件，不能声称绝无相关测试|
|[FreeFuzz，ICSE 2022](https://github.com/ise-uiuc/FreeFuzz)|已保存完整树和 README|可提供源测试来源，尚未证明 TF/PT 历史配对；只有源测试不能填上目标侧|
|[Muffin，ICSE 2022](https://github.com/library-testing/Muffin)|已保存树、README 和 Python 源码|架构/模型级测试，未建立与当前 110 个操作配对的历史关系|
|[XAMT](https://arxiv.org/html/2508.12546v1)|论文描述 API 匹配、输入对齐及差分测试|没有从本次读取的论文定位到可验证的对应完整测试包；保留为后续线索，未算覆盖|

以上结论限定于本次实际取得的材料；未穷尽所有论文、所有 issue、历史分支或作者未公开附件。

## 后续路线更新

用户明确要求不向作者索取材料。以下原建议已被替代；当前执行依据为 [PUBLIC_ONLY_PLAN.md](PUBLIC_ONLY_PLAN.md)，包含新取得的 Ivy 测试覆盖及 DLLens 公开工件重建路线。原邮件草稿不再使用。

## 原后续建议（已归档，不再执行）

1. **优先找 DLLens 作者要精确 110 条的测试产物。** 当前名单与它的 counterpart JSON 一一对应，优先级高于从其他论文凑同名 API。索取清单和邮件草稿见 [AUTHOR_REQUEST.md](AUTHOR_REQUEST.md)，未对外发送。
2. **向 CrossProbe 作者索取完整迁移语料及源→目标索引。** 公开少量缺陷脚本与 110 组重叠很低。明确接受迁移失败样本，不只要通过测试的样本。
3. 收到材料后，逐对登记源测试、迁移目标、输入、检查/期望、版本、原始日志、迁移关系。测试意图可以来自断言、预期异常或明确的 bug 复现目标；没有 assert 不能自动判为没有意图。
4. 如果外部测试使用了**不同目标实现**，保留旧的 110 API 槽位关联，同时新增测试对 ID 和结果；CoSMiT 与基线必须在新测试对上重新评估。不能继承旧操作实验的预测或把覆盖同一 API 当作同一候选实例。
5. 如果作者也没有保存历史迁移产物，则“110 个固定候选全部配上现成真实迁移测试”暂时没有证据支持可完成。应向导师说明这一材料限制，再决定允许缩小真实迁移子集或调整实验单位；本次没有擅自替换数据集或自行生成迁移。

## 可复查性

- `analysis/scripts/collect_published_test_materials.py`：固定提交的元数据收集。
- `analysis/scripts/collect_published_test_payloads.py`：下载作者原文件；235 项全部成功。
- `analysis/scripts/audit_published_test_coverage.py`：静态调用线索、原文提取及逐组表。
- 原材料目录 `payload-manifest.json` 记录 URL、字节数和 SHA256；`SHA256.json` 记录目录内容。
- 没有调用 DeepSeek，没有执行第三方测试，没有改变现有 110 组实验结果或标注包。
