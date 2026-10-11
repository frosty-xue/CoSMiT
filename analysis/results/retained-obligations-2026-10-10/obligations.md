# 27 对保留正文测试：义务与证据表

所有“参照候选”均不是独立 gold。原生类型、布局与存储义务不能由数值桥接自动继承。

| ID | 家族／入口 | 实际检查义务 | 关键限制 | 当前分组 |
|---|---|---|---|---|
| E001 | add / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E002 | add / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E003 | subtract / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E004 | subtract / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E005 | multiply / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E006 | multiply / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E007 | divide / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E008 | divide / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E009 | maximum / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E010 | maximum / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E011 | minimum / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E012 | minimum / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E013 | power / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E014 | power / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E015 | atan2 / _test_reference_numerics | 与 NumPy 对应运算参考比较；返回张量及条件 dtype 检查 | 替换上游输入生成器，仅扩充索引0、16；固定的有限输入不覆盖所有 dtype/promotion/标量分支；跨框架结果重建为源框架张量，不验证目标原生返回对象类型 | 限域值/形状参照候选 |
| E016 | atan2 / _compareCpu | 张量/混合 NumPy 参数调用的值与 NumPy 参考接近；输出形状与参考一致 | 替换上游输入生成器，仅扩充索引0、16；also_compare_variables=False，Variable 分支未覆盖；混合参数经适配均转为目标张量，不验证原生 NumPy/张量混合调用语义 | 限域值/形状参照候选 |
| E018 | reshape / testFloatBasic | 输出形状符合 NumPy reshape；静态形状与运行结果形状相符；int64 shape 参数调用 | 原方法无数值相等断言，数值扰动接受不构成丢失；桥接将 shape 参数张量转为 Python 值，不能确认目标原生 int64 参数支持 | 仅形状参照候选 |
| E019 | transpose / test_transposes | 转置结果与 T/H/mT/mH/adjoint 关系一致 | 运行固定 CPU float32，不覆盖复数共轭分支语义；值桥接复制输入/输出，不验证视图别名或存储共享 | 限域值/形状参照候选 |
| E020 | transpose / testTranspose2DAuto | 省略 perm 时二维默认转置的结果值 | 目标基线失败，不进入扰动拒绝保持评价 | 基线行为失败 |
| E022 | squeeze / testSqueeze | 去掉单位轴后的形状符合 NumPy；输出值符合 NumPy squeeze | 测试正文含 GPU 上下文但执行限制为 CPU，不能计为独立 GPU 验证；零值输入和既定形状不能代表全部数值域 | 限域值/形状参照候选 |
| E024 | expand_dims / testExpandDimsDimType | axis=0 扩维结果的值与形状；原方法的 axis int32/int64 张量参数兼容性 | 适配器将轴张量转为 Python int，目标原生轴 dtype 兼容性未验证；仅限 axis=0 与长度2零向量 | 限域值/形状参照候选 |
| E025 | concat / test_cat2 | 拼接后的各区段等于对应输入；split/chunk 再拼接恢复原张量；最终拼接尺寸 | 值桥接复制了非连续输入，不能验证目标原生非连续布局支持；形状扰动在 narrow 处发生运行异常，未到相关断言；仅第一次操作被扰动，不能推出所有区段断言均有独立敏感性证据 | 数值扰动参照候选 |
| E026 | concat / testConcatTuple | list 与 tuple 两种容器输入的拼接结果一致 | 适配器将 list 和 tuple 都变成 list，原生容器类型义务被归一化；原断言是两次调用的关系检查，不提供完整独立期望值；一次扰动只影响第一次调用，不代表普遍容器语义保持 | 容器义务被归一化 |
| E027 | stack / test_stack | 正负轴 stack 结果一致；stack 输出尺寸；沿新增轴取切片可恢复各输入 | 值桥接不验证存储共享/布局或原生返回对象；仅第一次调用受到扰动，不能扩展为每个 dtype/axis 都有敏感性覆盖 | 限域值/形状参照候选 |
| E028 | stack / testSimple | 对指定形状、轴、dtype 的 split 后 stack 恢复原数据 | float8_e5m2 输入在适配器转换时失败；属于 harness 能力限制，不是 counterpart 缺陷；整体方法没有通过，不将此前循环部分成功算成完整通过 | 适配器阻塞 |
| E029 | clip / test_clamp | 双侧/单侧裁剪值；裁剪界限及输入广播结果 | 目标单侧 None 处理失败，后续断言可能未到达；固定 CPU float64；非连续布局经桥接复制，不证明布局语义保持 | 基线行为失败 |
| E030 | clip / testClipByValue | 2×3 输入裁剪结果与期望值接近 | 原方法未覆盖标量输入，不能给标量形状保持标签；本层通过不能推翻 E030 既有标量行为违反 | 限域值/形状参照候选 |
