# D0050: tf.math.reciprocal → torch.Tensor.__rtruediv__

状态：**两端API测试齐**。这是代码材料覆盖，不代表迁移正确或测试已运行。

## 源测试

- [test_tensorflow_reciprocal](source-test-excerpt.py)；[完整原文件](source-test-full.py)
- [上游固定版本](https://github.com/ivy-llc/ivy/blob/a701151c85d59c0260a4dbf505479805bdeec00f/ivy_tests/test_ivy/test_frontends/test_tensorflow/test_math.py#L2158)；匹配方式：exact API / explicit decorator alias

## 目标测试

- `torch.Tensor.__rtruediv__`：[测试摘录](target-01-test-excerpt.py)、[完整原文件](target-01-test-full.py)、[上游](https://github.com/pytorch/pytorch/blob/8ac9b20d4b090c213799e81acf48a55ea8d437d6/test/test_binary_ufuncs.py#L2657)；exact API / explicit decorator alias

## 使用范围

- 完整原文件未修改；摘录仅便于阅读，不能脱离原仓库依赖直接运行。
- Ivy 测试通过公共助手调用原生参考实现及 Ivy 前端/后端；不是直接测试当前 DLLens 包装函数。
- 输入范围和检查目标尚待对齐；不要把两套测试已有默认当作意图保持。
- 缺少整段 counterpart 的现成测试时，不把组件测试合并计作已有组合测试。
- 目标官方test_rdiv通过30/x测试反向除法；不是与源侧完全相同的1/x输入
