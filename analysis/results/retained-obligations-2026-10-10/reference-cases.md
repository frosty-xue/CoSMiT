# 有限范围保持参照材料

以下为代表性材料，不是新增实验或独立正确标签。

## E001：_test_reference_numerics

检查义务：与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查

限制：替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型

判定分组：限域值/形状参照候选。

```json
[
  {
    "scenario": 0,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  },
  {
    "scenario": 16,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  }
]
```

断言位置：

- 源正文第 4 行：`assert isinstance(actual, torch.Tensor)`
- 源正文第 6 行：`self.assertEqual(actual.item(), expected, msg=msg, **kwargs)`
- 源正文第 13 行：`self.assertEqual(actual, torch.from_numpy(expected).to(actual.dtype), msg, exact_device=False, **kwargs)`
- 源正文第 15 行：`self.assertEqual(actual, expected, msg, exact_device=False, **kwargs)`
- 源正文第 23 行：`self.assertEqualHelper(actual, expected, msg, dtype=dtype, exact_dtype=exact_dtype, rtol=0.016, atol=1e-05)`
- 源正文第 25 行：`self.assertEqualHelper(actual, expected, msg, dtype=dtype, equal_nan=equal_nan, exact_dtype=exact_dtype)`
- 源正文第 10 行：`assert actual.dtype in (torch.float16, torch.bfloat16, torch.float32)`
- 源正文第 12 行：`assert expected.dtype == torch_to_numpy_dtype_dict[actual.dtype]`

## E002：_compareCpu

检查义务：张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致

限制：替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义

判定分组：限域值/形状参照候选。

```json
[
  {
    "scenario": 0,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  },
  {
    "scenario": 16,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  }
]
```

断言位置：

- 源正文第 27 行：`self.assertShapeEqual(np_ans, out)`
- 源正文第 21 行：`self.assertAllClose(np_ans, tf_cpu)`
- 源正文第 22 行：`self.assertAllClose(np_ans, np_left)`
- 源正文第 23 行：`self.assertAllClose(np_ans, np_right)`
- 源正文第 25 行：`self.assertAllClose(np_ans, np_var_left)`
- 源正文第 26 行：`self.assertAllClose(np_ans, np_var_right)`

## E018：testFloatBasic

检查义务：输出形状符合 NumPy reshape；静态形状与运行结果形状相符；int64 shape 参数调用

限制：原方法无数值相等断言，数值扰动接受不构成丢失；桥接将 shape 参数张量转为 Python 值，不能确认目标原生 int64 参数支持

判定分组：仅形状参照候选。

```json
[
  {
    "scenario": null,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "source-does-not-reject"
    },
    "baseline_failures": []
  }
]
```

断言位置：

- 源正文第 8 行：`self.assertEqual(tf_ans.get_shape(), out.shape)`
- 源正文第 9 行：`self.assertShapeEqual(np_ans, tf_ans)`
- 源正文第 13 行：`self.assertEqual(tf_ans.get_shape(), out.shape)`
- 源正文第 14 行：`self.assertShapeEqual(np_ans, tf_ans)`

## E024：testExpandDimsDimType

检查义务：axis=0 扩维结果的值与形状；原方法的 axis int32/int64 张量参数兼容性

限制：适配器将轴张量转为 Python int，目标原生轴 dtype 兼容性未验证；仅限 axis=0 与长度2零向量

判定分组：限域值/形状参照候选。

```json
[
  {
    "scenario": null,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  }
]
```

断言位置：

- 源正文第 10 行：`self.assertShapeEqual(np_ans, tensor)`
- 源正文第 11 行：`self.assertAllEqual(np_ans, tf_ans)`

## E026：testConcatTuple

检查义务：list 与 tuple 两种容器输入的拼接结果一致

限制：适配器将 list 和 tuple 都变成 list，原生容器类型义务被归一化；原断言是两次调用的关系检查，不提供完整独立期望值；一次扰动只影响第一次调用，不代表普遍容器语义保持

判定分组：容器义务被归一化。

```json
[
  {
    "scenario": null,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  }
]
```

断言位置：

- 源正文第 8 行：`self.assertAllEqual(self.evaluate(concat_list_t), self.evaluate(concat_tuple_t))`

## E027：test_stack

检查义务：正负轴 stack 结果一致；stack 输出尺寸；沿新增轴取切片可恢复各输入

限制：值桥接不验证存储共享/布局或原生返回对象；仅第一次调用受到扰动，不能扩展为每个 dtype/axis 都有敏感性覆盖

判定分组：限域值/形状参照候选。

```json
[
  {
    "scenario": null,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  }
]
```

断言位置：

- 源正文第 12 行：`self.assertEqual(res, res_neg)`
- 源正文第 13 行：`self.assertEqual(res.size(), expected_size)`
- 源正文第 14 行：`self.assertEqual(res.select(dim, 0), x, atol=0, rtol=0)`
- 源正文第 15 行：`self.assertEqual(res.select(dim, 1), y, atol=0, rtol=0)`
- 源正文第 16 行：`self.assertEqual(res.select(dim, 2), z, atol=0, rtol=0)`

## E030：testClipByValue

检查义务：2×3 输入裁剪结果与期望值接近

限制：原方法未覆盖标量输入，不能给标量形状保持标签；本层通过不能推翻 E030 既有标量行为违反

判定分组：限域值/形状参照候选。

```json
[
  {
    "scenario": null,
    "baseline_qualified": true,
    "transparent": true,
    "probes": {
      "wrong-shape": "rejection-retained",
      "wrong-value": "rejection-retained"
    },
    "baseline_failures": []
  }
]
```

断言位置：

- 源正文第 10 行：`self.assertAllClose(np_ans, tf_ans)`

