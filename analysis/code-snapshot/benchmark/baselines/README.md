# 论文实验基线与运行入口

当前公开API共同实验使用 `protocol-v3.yaml`，开发控制沿用v2，未见组协议另行冻结。TransFuzz仅作方法参考，不进入基线表。本目录按论文实验需要实现验证组件，只记录方法定义、参数、版本与实际结果。

2026-09-17完成状态：[公开逐项数据](../../research-data/2026-09-17/README.md)。81个公开候选15,552对执行；模型455主调用+33次限定重试，主结果278有效/177失败，重试补充视图295有效/160失败。数据包可用 `export_public_results.py --verify` 离线校验。下文关于“尚未执行”“待接入”的描述是开发阶段记录，当前以公开数据及 `docs/full-experiment-status.md` 为准。

| 方法 | 实验功能 | 入口 |
| --- | --- | --- |
| DLLens验证组件 | 同输入源/目标执行、类型观察、数值输入变换、输出一致性检查 | `verification_ports.py`、`experiment_worker.py` |
| DocTer约束组件 | 必需参数、tensor类型、dtype、结构、字面量维数和数值枚举检查 | `check_docter` |
| IntentTester验证组件 | 源TDL忠实性、目标语法/API使用检查 | `prepare_llm_jobs`、`run_verifier_llm.py` |
| 目标TDL检查 | 检查目标程序是否体现同一源意图 | 同上，单独报告 |
| 直接LLM / LLM＋轨迹 | 比较无执行证据与有执行证据的判定 | 同上 |
| self-test / target-binding | 执行结果与目标API实际调用检查 | `experiment_worker.py` |
| CoSMiT | 值、形状、dtype义务检查与三次执行确认 | `src/cosmit/engine/certification.py` |

来源和哈希见 `frozen-manifest.json`；历史档案在 `artifacts/baselines/20260916-v1/sources/`。已取得DLLens的1,401份对应程序（pt2tf 712、tf2pt 689）及19,188条输入代码，DocTer的2,415份约束。正式样本量在源/API家族去重和语义核验之后计算。

## 运行一次实验

在项目根目录执行，输出目录须是新的：

```bash
python benchmark/baselines/build_development_packet.py artifacts/baselines/new-development
python benchmark/baselines/run_experiment.py artifacts/baselines/new-development/packet.json artifacts/baselines/new-experiment
python benchmark/baselines/run_verifier_llm.py artifacts/baselines/new-experiment artifacts/baselines/new-llm --case C001 --limit 5 --execute
python benchmark/baselines/summarize_experiment.py artifacts/baselines/new-experiment artifacts/baselines/new-report --llm artifacts/baselines/new-llm --control-key artifacts/baselines/new-development/control-key.json
```

模型使用现有环境配置，凭据不写入结果。去掉`--execute`不会调用模型；`--limit`限制请求数。每次响应和失败都保留。

流程：冻结候选与源性质 → 生成固定输入 → 源/目标执行 → 各验证器判定 → 保存模型请求与响应 → 合并候选结果 → 最后打开独立参考或控制答案。执行阶段不读取答案文件，LLM只看到源代码、目标代码、输入、性质和允许的原始观察。

产物包括`packet.json`、`configuration.json`、每候选的`execution.json` / `record.json` / `llm-jobs.json`、统一的`method-matrix.csv`与`summary.json`。未运行、失败、超时、无效源测试和未决都保留。

## 当前开发检查

`artifacts/baselines/20260916-v2/development/`有10条控制：两个方向的原始程序、形状变化、数值变化、目标调用缺失和源断言无效。它们来自一个abs API家族，每条两个输入、各执行三次，共60对执行。第二个输入由固定seed数值变换生成。该包不具备正式评估资格，不计算论文准确率。

最终执行在`artifacts/baselines/20260916-v2/experiment-final/`；首轮`experiment/`只保留调试记录。正式数据按相同格式接入，先按源/API家族分组；已使用的abs家族排除出未见API留出集。

目前支持有限实数稠密张量（float32/float64、rank≤4、元素数≤4096）的登记性质。其他输入域需要对应的转换和观察规则。框架错误或无法确认的假设返回未决。DocTer未解释的符号约束返回未决，历史约束满足与当前版本兼容性分别记录。约束满足不代表意图正确。

DLLens比较使用`squeeze`后展平，`allclose(atol=0.1, rtol=1e-5, equal_nan=True)`。CoSMiT开发包检查形状、dtype和值，值容差`atol=1e-6, rtol=1e-5`。这些控制用于验证代码路径，不据此证明严格容差在真实任务中更好。

执行环境固定为Python 3.10.9、TensorFlow 2.16.2、PyTorch 2.1.0、NumPy 1.26.2；依赖锁为`dllens-smoke.requirements.lock.txt`。LLM配置与实际响应版本记录在每次运行中。

```bash
uv venv --python 3.10 tmp/public-system-envs/dllens-smoke-restored
uv pip sync --python tmp/public-system-envs/dllens-smoke-restored/bin/python benchmark/baselines/dllens-smoke.requirements.lock.txt
python benchmark/baselines/freeze_sources.py verify artifacts/baselines/20260916-v1/sources
python -m pytest -q tests/test_baseline_ports.py
```

正式实验过程见`docs/experiment-procedure-2026-09-16.md`；数据交接见`docs/dataset-collection-2026-09-17.md`。

最终开发结果：10/10控制预期通过、60对执行完成、13项测试通过；单候选5个模型请求全部完成。总共准备50个请求，其余45个未执行。合并报告位于`artifacts/baselines/20260916-v2/final-report/report.md`，机器表为同目录`method-matrix.csv`。

## 自主获取公开数据与构建源性质

本轮材料位于 `artifacts/dataset-sources/20260916-v1/`，完整记录见 `docs/dataset-collection-2026-09-17.md`。已取得 BESSER/TensorScope 固定仓库、24 份官方规格、24 个数学性质家族、69 个 DLLens 公开候选，以及 5 组 BESSER 模型定义。数据收集及证据核验由代理负责。

新输出目录须不存在；固定仓库须位于 `tmp/baseline-sources/` 且与脚本 commit 一致。

```bash
python benchmark/baselines/collect_public_corpus.py artifacts/dataset-sources/NEW
# 使用已冻结的 Python 3.10 / TF 2.16.2 / torch 2.1.0 环境：
tmp/public-system-envs/dllens-smoke/bin/python benchmark/baselines/run_source_evidence.py artifacts/dataset-sources/NEW artifacts/dataset-sources/NEW/unary-execution
tmp/public-system-envs/dllens-smoke/bin/python benchmark/baselines/probe_besser_sources.py artifacts/dataset-sources/NEW artifacts/dataset-sources/NEW/besser-source-execution
tmp/public-system-envs/dllens-smoke/bin/python benchmark/baselines/validate_public_pairs.py artifacts/dataset-sources/NEW artifacts/dataset-sources/NEW/pair-validation
```

API 源性质检查已执行 69 × 64 × 3 对，源端全部支持，目标 68 份支持、1 份稳定违规。原 `trunc` 的 17 个公开输入复跑 51 对没有暴露该违规；新增负整数边界会暴露，同一输入下 DLLens 原输出比较器也能检出。BESSER 7 个源模型通过性质检查、3 个保留未决，两个权重对齐模型对完成 12 对数值检查。

这些是发现阶段的数据与源性质验证，不是全方法正式对照。下一阶段须接入共同 baseline、目标调用观察，并在未见组上评估。样本按 API 家族/模型架构分组，不能把别名和重复执行当独立样本。新脚本只运行已检查的公开函数/模型类；完整模型训练、随机初始化数值等价及全部原迁移生成过程不在本轮结论中。
