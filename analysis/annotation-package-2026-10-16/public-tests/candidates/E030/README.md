# E030: tf.clip_by_value → clip_value_max.new_ones, float, torch.clamp, torch.max

状态：**两端组件测试齐，组合测试缺**。这是代码材料覆盖，不代表迁移正确或测试已运行。

## 源测试

- [test_tensorflow_clip_by_value](source-test-excerpt.py)；[完整原文件](source-test-full.py)
- [上游固定版本](https://github.com/ivy-llc/ivy/blob/a701151c85d59c0260a4dbf505479805bdeec00f/ivy_tests/test_ivy/test_frontends/test_tensorflow/test_general_functions.py#L654)；匹配方式：exact API / explicit decorator alias

## 目标测试

- `torch.max`：[测试摘录](target-01-test-excerpt.py)、[完整原文件](target-01-test-full.py)、[上游](https://github.com/ivy-llc/ivy/blob/a701151c85d59c0260a4dbf505479805bdeec00f/ivy_tests/test_ivy/test_frontends/test_torch/test_reduction_ops.py#L425)；exact API / explicit decorator alias
- `torch.clamp`：[测试摘录](target-02-test-excerpt.py)、[完整原文件](target-02-test-full.py)、[上游](https://github.com/ivy-llc/ivy/blob/a701151c85d59c0260a4dbf505479805bdeec00f/ivy_tests/test_ivy/test_frontends/test_torch/test_pointwise_ops.py#L907)；exact API / explicit decorator alias
- `torch.Tensor.new_ones`：[测试摘录](target-03-test-excerpt.py)、[完整原文件](target-03-test-full.py)、[上游](https://github.com/ivy-llc/ivy/blob/a701151c85d59c0260a4dbf505479805bdeec00f/ivy_tests/test_ivy/test_frontends/test_torch/test_tensor.py#L10604)；exact API / explicit decorator alias

## 使用范围

- 完整原文件未修改；摘录仅便于阅读，不能脱离原仓库依赖直接运行。
- Ivy 测试通过公共助手调用原生参考实现及 Ivy 前端/后端；不是直接测试当前 DLLens 包装函数。
- 输入范围和检查目标尚待对齐；不要把两套测试已有默认当作意图保持。
- 缺少整段 counterpart 的现成测试时，不把组件测试合并计作已有组合测试。
- 目标为组合：各API测试已分别收集，整段组合测试仍空缺
