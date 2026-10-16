# 17组组合函数受控适配

这里实际调用完整原函数，而不是分别调用组件。输入取自 DLLens 公开 sample_inputs；检查器取自公开 Ivy 测试助手，原文保留。

运行需要同一 Python 环境中的 NumPy、PyTorch、TensorFlow，不需要 Ivy 或模型服务。命令：`python run_adapters.py --output results/run.json`。`--case ID` 可限定单组。

不是原 Ivy 测试全量复现：没有执行其 Hypothesis 输入策略、out/inplace/gradient/device 等模式。输入转换仅按值/dtype，结果只适用于实际有效输入。原函数没有的 alpha/dtype 等参数没有被添加。目标异常、源无效、转换失败和检查失败分开记录；所有输出都是技术观察，不是人工标签。

每条记录包含具体输入值、两侧输出/异常、原函数执行行和检查结果。未执行行列在 coverage 中，不等于完整分支覆盖结论。未出现的参数组合不假设已覆盖。
