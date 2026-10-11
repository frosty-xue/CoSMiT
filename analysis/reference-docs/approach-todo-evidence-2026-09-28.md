> **2026-09-28 范围更正：**用户确认 datasets/ 下仅 expansion-2026-09-18 可用，其余均已废弃。本文涉及 migration_verification_v1、MV001–MV012 及其衍生 artifacts 的分析全部撤回作为论文依据；历史记录保留。关于可用正例和数据就绪度的判断须纳入 expansion 的 2026-09-20 已执行结果重新评估。

# Approach TODO 证据核对（2026-09-28）

## 修改范围

修改论文目录的 ISSTA2026.tex，修改前备份为 ISSTA2026.before-approach-todos-2026-09-28.tex.bak。原始数据及历史结果未修改，未重新执行深度学习框架，未调用模型。

| 原 TODO | 本次处理 | 剩余条件 |
|---|---|---|
| approach-registration | 补入加法源测试到数值/形状义务、目标调用要求、输入域、容差和运行环境的对应关系 | 真实候选的独立审查与匹配版本的规格依据仍待补充，改为 approach-registration-review |
| approach-evidence | 将原概念示例替换为 MV011 具体见证，增加数值计算及源/目标结果表 | 此项仅以受控开发案例范围完成；没有升级为真实迁移错误或人工 gold |
| approach-reproducibility | 校验冻结包与原始代码，明确四个缺失运行器文件及历史哈希位置 | 无法由现有记录恢复实现；保留 TODO，不能宣称完成框架重放 |

## 使用的证据

- `datasets/migration_verification_v1/sources/add.py`：独立重建源测试，包含 shape 与 assert_allclose 两项检查。
- `candidates/MV010.py`、`candidates/MV011.py`、`answer-key/mutations/MV011.json`：确认 MV011 恰为父候选删除数值断言后的代码。
- `obligations.json`：add 的输入范围 [-5,20]，shape [1,3,5]，float32 CPU，atol=rtol=1e-6；dtype 是执行条件，未添加独立 dtype 断言。
- `probe-plan.json`：原输入、原值重注入、boundary、zero、offset、shape 探针，各重复三次。offset 使用原输入，不依赖 boundary/zero 的域扩展。
- `evidence/add.json`、`evidence/add-upstream-excerpts.json`：上游 BinaryOpTest.testFloatBasic 来源、commit、原文件哈希及重建范围。当前本地上游文件与登记哈希相符。不能据此宣称覆盖上游完整 harness、GPU、梯度或 Variable 路径。
- `artifacts/migration-verification-pilot-v1-final/{pytorch,tensorflow}-executions.jsonl`：MV011 共 42 条执行记录，21 对。每侧原样执行、带调用观察执行和原值重注入共 9 条；加上两类输入和两类观察探针共 12 条。
- `counterexamples.json`：MV011-offset 的六个执行 job ID、失败条款和观察。

## 离线核对结果

机器可读结果：`artifacts/approach-evidence-audit-20260928/mv011-offline-audit.json`。

1. 数据集清单中 44 个文件、结果清单中 11 个文件的精确 SHA256 全部匹配，无需换行规范化。这与此前公开 research-data 包的换行问题是不同数据包。
2. MV011 源/目标代码与 cases.json 的哈希相符；候选与父候选的差异恰为登记删除。
3. 42 个 job ID 唯一；所有输入的形状、值域符合 add 登记。
4. 对所有执行记录，用 Python 标量加法后经 struct 单精度舍入重算 reference，均与记录一致。
5. 对 offset 记录，重算 float32 加 0.01 后的值与 actual 完全一致。三个重复中双方 actual 一致，15 个元素均超过源数值容差，shape 不变。
6. 第一个元素：expected=15；actual=15.010000228881836；绝对误差=0.010000228881835938；容差=0.000016，误差约为容差的 625 倍。
7. 三次 offset：source 为 assertion-failed，target 为 passed；独立 reference 的 shape=true、value=false。
8. 原执行、观察器执行和原值重注入的三次重复均通过且 actual 一致；带观察器的原执行记录了调用。
9. 实际记录环境：TensorFlow 2.20.0、PyTorch 2.9.1+cpu、Python 3.11.16、NumPy 2.4.6。

## 未解决的边界

`benchmark/migration_verification` 不存在；`git log --all --oneline -- benchmark/migration_verification` 未找到可用路径历史。历史 run-manifest 有 build_pilot.py、run_pilot.py、verify_pilot.py、worker.py 的哈希，测试文件也引用这些模块，但哈希和测试不能代替原实现。没有重建文件冒充历史版本。

本次是已有档案的一致性与数值核对，不是独立人工审查，也不是完整框架重放。正文仍明确开发重建与人工变体属性。未使用 D0028，未补造真实样本效果或统计指标。
