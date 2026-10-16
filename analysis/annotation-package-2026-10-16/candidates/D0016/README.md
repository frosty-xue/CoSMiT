# D0016: torch.neg → tf.negative

**唯一填写入口：[本组标注工作表](review.md)。** [返回110组总表](../../ANNOTATIONS.md)

两端公开 API/运算符测试已提供；本轮未运行这些公开测试。

## 全部材料

- [两端现成测试、完整原文件及出处](../../public-tests/candidates/D0016/README.md)
- [源操作](source-operation.py) · [目标操作](target-operation.py)
- [既有登记输入](inputs.json) · [既有观察](observations.json) · [声明范围](declared-behavior-scope.json)

## 使用说明

将以上材料共同用于本组复核，不需分别填写 v3/v4 表。标签与证据范围写在同一工作表中。公开测试输入域和断言可能不同；完整函数适配记录只支持其实际固定样本及公开检查器覆盖的性质。旧观察与本轮 sample_index 属于不同实验，引用时注明文件。
