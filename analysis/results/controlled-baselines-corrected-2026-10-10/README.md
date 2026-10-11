# 受控试验的既有基线补接与更正

日期：2026-10-10。前一轮只评价新增执行/静态对照及CoSMiT记录观察适配器，未完整接入benchmark/baselines中的既有组件。那些简单对照应列为补充控制，不能代替DLLens、DocTer和IntentTester。

## 逐项状态

| 项目既有方法 | 真实入口 | 本轮状态 |
|---|---|---|
| DLLens比较组件 | verification_ports.dllens_comparator | 已调用，9个样本×3次已保存观察，共27次比较 |
| DocTer约束组件 | verification_ports.check_docter | 未运行；固定约束数据缺失，还需序列化方法实际调用参数 |
| IntentTester源TDL＋目标API | prepare_llm_jobs / run_verifier_llm.py | 未运行；固定Java提示模板、旧源码锁及模型服务配置缺失，测试harness上下文还需适配 |
| 目标TDL扩展 | 同上 | 同上 |
| Direct LLM / Trace LLM | 同上 | 未运行；模型服务配置缺失，不能复用旧样本结果 |
| self-test | experiment_worker中的执行判定 | 前一轮正常运行对照已复用测试记录，但不是旧worker完整重跑 |
| 原生target-binding | experiment_worker中的实际API插桩 | 未运行；当前保留正文记录只有操作边界计数，不能冒充原生API调用轨迹 |
| CoSMiT | certification.certify/evaluate | 前一轮已调用核心＋新登记的测试结果记录适配器；不是原有操作行为实验流程 |

TransFuzz按既有协议仅作方法参考，不加入基线。

## DLLens如何恢复与运行

原始`artifacts/baselines/20260916-v1/sources/sources.lock.json`当前缺失。根据`benchmark/baselines/frozen-manifest.json`，从本地DLLens Git对象库读取指定提交`0f617e92c34d60bfdd3bc06d80c17d938879ed9c`的比较器文件，建立新的最小恢复锁。没有伪造原锁，也没有改写公共verification_ports实现。

调用现有`verification_ports.dllens_comparator(np)`，其按原逻辑提取并执行上游compare_res、convert_to_numpy、sparse_to_dense。为该模块实例配置本次恢复锁；恢复代码和哈希保存在本目录。比较对象为三次observe模式的首次未扰动操作返回值，按保存dtype重建NumPy数组。

9个样本的27次比较全部一致。按“未发现操作差异→保持”的行为对照映射，得到TN=3、FN=6，准确率33.33%、召回率0%，没有正向检出，precision未定义。

该结果限于**DLLens既有输出比较组件在当前保存观察上的结果**，没有运行完整输入生成、模糊测试或全部异常流程。也没有把人为注入的相同扰动送给DLLens后假装是其自身生成的反例。它说明仅靠这里的操作输出比较不能发现删断言，不是DLLens整体能力的结论。

## 修正后的比较

| 已运行方法 | 准确率 | 召回率 | 定位 |
|---|---:|---:|---|
| DLLens既有比较组件 | 33.33% | 0% | 既有行为比较基线，限上述观察 |
| 正常运行检查 | 33.33% | 0% | 补充控制 |
| 断言存在检查 | 66.67% | 50% | 补充控制 |
| 排除字面恒真断言的存在检查 | 100% | 100% | 补充静态强对照 |
| CoSMiT核心＋测试结果记录适配器 | 100% | 100% | 新适配后的受控开发验证 |

DocTer的输出是历史API输入约束满足情况，不能直接将satisfied当成测试意图正确。IntentTester及LLM分支仍需真正运行后才能比较。当前表尚不是完整论文基线实验，静态强对照也与CoSMiT打平。

所有未运行方法保留not-run，指标为null，不算作失败或漏检。未将9个构造样本加入110个公开候选，未新增模型请求或框架测试执行。

## 文件

- `baseline-status.json`：各方法入口、缺失依赖和适用边界。
- `dllens-port-audit.json`：27次真实比较器返回结果。
- `recovered-sources.lock.json`、`recovered-sources/`：指定提交的恢复来源。
- `predictions.json`、`metrics.json`：扩充后的逐项结果与指标。

运行脚本为`benchmark/baselines/extend_pilot_existing_baselines.py`；评分复用`evaluate_controlled_assertions.py score`。其他方法结果沿用前一轮文件，并没有伪称本轮重跑。前一轮详细门槛和核心轨迹保存在`artifacts/analysis/controlled-evaluation-2026-10-10`。
