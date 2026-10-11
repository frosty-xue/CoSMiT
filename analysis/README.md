# 实验分析工作区

整理日期：2026-10-11。这里集中保存分析报告、逐候选汇总、分析脚本和复现代码快照。
新实验数据在 **../research-data/2026-10-11/**；旧 80 组的数据仍在 **../research-data/2026-09-17/**。

## 从哪里开始

1. 最新基线汇总：`results/expansion-campaign-2026-10-10/REPORT.md`。
2. 110 组逐项方法结果：同目录 `combined-110-results.json`，区分 primary 和 retry-view。
3. 模型覆盖：同目录 `coverage-current.json`。该文件是严格解析口径；格式恢复单独记录在新实验归档的 `baseline-campaign/repair-round-*/offline-format-recovery.json`。
4. 整理来源与校验：`organization-manifest-2026-10-11.json`、`organization-validation-2026-10-11.json`。

这是固定快照，不是仍在运行的任务。复制的 STATUS.md/progress.json 保留历史状态；不要仅凭旧标题推断当前后台进程。

## 目录职责

| 目录 | 内容 |
| --- | --- |
| `results/` | 现有全部分析产物，各批次独立保留 |
| `scripts/` | 8 个主要离线分析脚本，原文件的等内容副本 |
| `code-snapshot/benchmark/baselines/` | 完整基线脚本及配置快照，用于溯源，不直接作为迁移后的运行入口 |
| `reference-docs/` | 与数据收集、实验流程、证据和待办有关的文档快照 |
| `operations/` | 历史运行日志及报告更新 PowerShell 脚本；仅作记录，不要重新启动这些绑定旧进程号的监控脚本 |

## results 下各项分析的作用

| 子目录 | 作用 |
| --- | --- |
| `research-data-2026-10-09` | 原始 80 组的结果、覆盖、成本审计 |
| `combined-data-2026-10-09` | 旧数据与扩充集的行为审计合并；不是新模型实验结果 |
| `evidence-inventory-2026-10-09` | 候选、来源、测试证据及缺口清单 |
| `priority-adjudication-2026-10-10` | 三个行为问题及优先复核项的证据包 |
| `retained-obligations-2026-10-10` | 保留测试正文的义务与适配边界审计 |
| `unified-evaluation-units-2026-10-10` | 110 组统一评估材料，含 27 组构造测试对；不是 110 组 gold |
| `controlled-evaluation-2026-10-10` | 9 个受控变体上的 CoSMiT 及轻量对照分析 |
| `controlled-baselines-corrected-2026-10-10` | 受控变体的 DLLens 移植比较补充 |
| `expansion-campaign-2026-10-10` | 最新批量基线结果、合并视图和调用成本 |

早期行为审计中的“三个问题”与最新核心运行的“两个反驳”口径不同。最新实现结果与边界说明以新实验归档 README 和本目录最新 campaign 报告为准，不能将早期统计静默覆盖或混用。

## 脚本使用

此次为校验后的复制整理，没有删除原文件或改写历史配置中的路径，因而现有 benchmark 脚本仍可使用原入口。
`scripts/` 中的脚本保持与原 benchmark/baselines 相同的目录深度，部分仍明确依赖原 artifacts、datasets、benchmark 或本机上游源码路径；不是脱离项目即可运行的独立发布包。

例如，在项目根目录运行原始数据的离线分析，使用一个尚不存在的新输出目录：

```powershell
& 'F:/environment/python/miniconda3/envs/tf220/python.exe' analysis/scripts/analyze_research_export.py research-data/2026-09-17 analysis/results/recomputed-original-80
```

其它脚本先查看 `--help`。不要覆盖冻结的归档或已有结果目录。执行模型脚本仍使用 benchmark/baselines 正式入口和原始运行目录；本次整理没有新增模型调用。

## 校验范围

1,873 个文件复制时逐一验证源与目标 SHA-256 相同；总量约 284 MB。所有原始文件仍保留。
`SHA256.json` 提供 analysis 归档文件的相对路径校验；组织清单记录每个副本的来源。不同目录中的重复证据不得重复计数。
reference-docs 是历史背景材料，可能讨论旧数据；本次实际归档的数据集只采用 expansion-2026-09-18。
