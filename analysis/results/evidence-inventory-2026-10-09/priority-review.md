# 11 个优先候选的证据复核

本轮为代码及既有记录核查，未新增框架执行、模型调用或独立标签。静态风险线索不计为新增反例。

## E020 · transpose

**检查义务：** 默认 perm=None 应执行轴序反转；保留方法 testTranspose2DAuto 明确检查转置后的 2×3→3×2 内容。

**核查发现：** counterpart 对 None 解包；保留正文实验也在目标操作执行阶段失败，未到达后续断言。

**当前可用结论：** 可作为行为违反及构造操作替换测试的基线失败证据；不能称断言被删除。

**缺少与下一步：** 复核默认参数义务、操作替换适配和源规格；完整历史迁移测试来源仍缺。

保留正文：[source](F:/codes/python/CoSMiT/datasets/expansion-2026-09-18/assertion-batch-2026-09-28/retained/E020-source.py)；[target](F:/codes/python/CoSMiT/datasets/expansion-2026-09-18/assertion-batch-2026-09-28/retained/E020-target.py)

### source counterpart

```python
def tensorflow_call(a,perm=None,conjugate=False):
  return tf.transpose(a,perm,conjugate)
```

### target counterpart

```python
def pytorch_call(a, perm=None, conjugate=False):
    if conjugate:
        a = a.conj()
    return a.permute(*perm)
```

## E029 · clip

**检查义务：** test_clamp 分别断言双侧裁剪、仅 min、仅 max 和广播结果。

**核查发现：** 目标对 None 无条件 tf.cast；单侧裁剪在保留正文实验中触发目标执行错误。

**当前可用结论：** 可作为行为违反及构造操作替换测试的基线失败证据；现有断言表达式仍保留。

**缺少与下一步：** 复核合法可选界限、CPU/dtype 固定设置与适配过程；完整历史迁移测试来源仍缺。

保留正文：[source](F:/codes/python/CoSMiT/datasets/expansion-2026-09-18/assertion-batch-2026-09-28/retained/E029-source.py)；[target](F:/codes/python/CoSMiT/datasets/expansion-2026-09-18/assertion-batch-2026-09-28/retained/E029-target.py)

### source counterpart

```python
def pytorch_call(input,min=None,max=None):
  return torch.clip(input,min,max)
```

### target counterpart

```python
def tensorflow_call(input, min=None, max=None):
    min = tf.cast(min, input.dtype)
    max = tf.cast(max, input.dtype)
    clipped = tf.where(input < min, min, input)
    clipped = tf.where(clipped > max, max, clipped)
    return clipped
```

## E030 · clip

**检查义务：** 动态条款要求保持输出形状；保留的 testClipByValue 使用 2×3 输入并比较期望值。

**核查发现：** 目标 new_ones(1) 引入长度为 1 的维度；标量见证为 []→[1]。保留方法没有标量场景。

**当前可用结论：** 行为形状违反成立于已重放输入；不能用当前 2×3 测试证明标量检查意图丢失。

**缺少与下一步：** 寻找真实覆盖标量形状义务的源测试及其迁移版本；新增构造测试必须单列，不能冒充原测试。

保留正文：[source](F:/codes/python/CoSMiT/datasets/expansion-2026-09-18/assertion-batch-2026-09-28/retained/E030-source.py)；[target](F:/codes/python/CoSMiT/datasets/expansion-2026-09-18/assertion-batch-2026-09-28/retained/E030-target.py)

### source counterpart

```python
def tensorflow_call(t,clip_value_min,clip_value_max):
  return tf.clip_by_value(t,clip_value_min,clip_value_max)
```

### target counterpart

```python
def pytorch_call(t, clip_value_min, clip_value_max):
    clip_value_min = torch.max(clip_value_min, clip_value_max.new_ones(1) * float('-inf'))
    clip_value_max = torch.max(clip_value_min, clip_value_max)
    return torch.clamp(t, clip_value_min, clip_value_max)
```

## D0011 · exp

**检查义务：** 登记域为有限 float32/64 输入 [-8,8]，检查 exp 值、形状与类型。

**核查发现：** 代码为 torch.exp→tf.exp；目标 API 检查给出 false，但公开记录没有理由。

**当前可用结论：** 现有代码与通过记录不能裁定该 false 的具体原因；未确认误报。

**缺少与下一步：** 补原始否定理由与精确提示，核对环境/调用上下文；补原测试断言与迁移来源。

否定判断：intenttester-target-api {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/pytorch/counterparts/torch.exp.json)

### source counterpart

```python
def pytorch_call(input):
  return torch.exp(input)
```

### target counterpart

```python
def tensorflow_call(input):
    return tf.exp(input)
```

## D0012 · expm1

**检查义务：** 登记域为 [-8,8]，检查 expm1 值、形状与类型及已固定容差。

**核查发现：** 目标实际是 tf.exp(x)-1，不是直接 tf.math.expm1；存在需要核验的小量消减精度问题。

**当前可用结论：** 这是代码审查线索，不是已验证的新反例；是否超过固定绝对/相对容差尚未验证。

**缺少与下一步：** 补模型理由；在已登记容差下检查近零输入，保留独立数值参考；补源/迁移测试断言。

否定判断：intenttester-target-api {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/pytorch/counterparts/torch.expm1.json)

### source counterpart

```python
def pytorch_call(input):
  return torch.expm1(input)
```

### target counterpart

```python
def tensorflow_call(input):
    return tf.exp(input) - 1
```

## D0030 · acos

**检查义务：** 有限浮点输入 [-1,1]，检查 acos 值、形状与类型。

**核查发现：** 源端 TDL 检查 false；源函数只有 tf.acos 调用，没有测试断言。

**当前可用结论：** 可能涉及声明条款与函数正文的对应方式；模型具体原因未知。

**缺少与下一步：** 补模型理由，复核条款是否应由函数或外部测试 harness 承担；补真实断言。

否定判断：intenttester-source-tdl {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/tensorflow/counterparts/tf.acos.json)

### source counterpart

```python
def tensorflow_call(x):
  return tf.acos(x)
```

### target counterpart

```python
def pytorch_call(x):
    return torch.acos(x)
```

## H003 · det

**检查义务：** 行列式域为 1×1 至 4×4 严格对角占优浮点矩阵；独立参考为排列求和。

**核查发现：** 源端 TDL 检查 false；torch.det 函数正文没有断言，公开记录没有理由。

**当前可用结论：** 有限执行支持仍保留；不能把模型否定解释为行列式计算错误。

**缺少与下一步：** 补理由并分别核对矩阵域、参考、容差及原测试的检查义务。

否定判断：intenttester-source-tdl {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/pytorch/counterparts/torch.det.json)

### source counterpart

```python
def pytorch_call(input):
  return torch.det(input)
```

### target counterpart

```python
def tensorflow_call(input):
    return tf.linalg.det(input)
```

## H008 · matmul

**检查义务：** 登记的是二维稠密浮点矩阵；转置、伴随、稀疏标志均 false，output_type=None。

**核查发现：** 目标有额外标志分支，但忽略 output_type；模型目标 API 检查 false。

**当前可用结论：** 域外分支问题与当前域内判定必须分开；未确认该模型判断针对哪个条件。

**缺少与下一步：** 补精确提示/理由，核对模型是否获得了范围约束；另列可选参数审查，不回填当前域错误标签。

否定判断：intenttester-target-api {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/tensorflow/counterparts/tf.matmul.json)

### source counterpart

```python
def tensorflow_call(a,b,transpose_a=False,transpose_b=False,adjoint_a=False,adjoint_b=False,a_is_sparse=False,b_is_sparse=False,output_type=None):
  return tf.matmul(a,b,transpose_a,transpose_b,adjoint_a,adjoint_b,a_is_sparse,b_is_sparse,output_type)
```

### target counterpart

```python
def pytorch_call(a, b, transpose_a=False, transpose_b=False, adjoint_a=False, adjoint_b=False, a_is_sparse=False, b_is_sparse=False, output_type=None):
    if transpose_a:
        a = a.t()
    if transpose_b:
        b = b.t()
    if adjoint_a:
        a = a.conj().t()
    if adjoint_b:
        b = b.conj().t()
    if a_is_sparse:
        a = a.to_sparse()
    if b_is_sparse:
        b = b.to_sparse()
    result = torch.matmul(a, b)
    return result
```

## H010 · trace

**检查义务：** 登记矩阵形状均为二维，要求对角线求和及其输出形状。

**核查发现：** 目标对 rank>2 的结果额外 view；该分支不在当前输入域。模型否定来自源 TDL 检查。

**当前可用结论：** 高维形状是另一个审查线索，不能拿它解释源 TDL 的 false 或判当前域错误。

**缺少与下一步：** 补源 TDL 否定理由和源断言；高维行为若研究，应另立扩展域与实验。

否定判断：intenttester-source-tdl {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/tensorflow/counterparts/tf.linalg.trace.json)

### source counterpart

```python
def tensorflow_call(x):
  return tf.linalg.trace(x)
```

### target counterpart

```python
def pytorch_call(x):
    if x.dim() < 2:
        raise ValueError('Input tensor must be at least 2D.')
    trace = torch.diagonal(x, dim1=-2, dim2=-1).sum(dim=-1)
    if x.dim() > 2:
        return trace.view(trace.size(0), -1)
    else:
        return trace
```

## H011 · cumsum

**检查义务：** 有限小整数浮点输入，有效轴；exclusive=False、reverse=False。

**核查发现：** Direct LLM 为 invalid-assumption，目标 TDL 为 false；正文也包含域外 exclusive/reverse 分支。

**当前可用结论：** 两次否定不等于两份独立真实标签；没有理由，无法确定争议前提。

**缺少与下一步：** 优先恢复两条理由及提示，核对条款、函数正文与输入域；补真实测试断言。

否定判断：direct-llm {"verdict": "invalid-assumption"}；intenttester-target-tdl-extension {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/tensorflow/counterparts/tf.cumsum.json)

### source counterpart

```python
def tensorflow_call(x,axis=0,exclusive=False,reverse=False):
  return tf.cumsum(x,axis,exclusive,reverse)
```

### target counterpart

```python
def pytorch_call(x, axis=0, exclusive=False, reverse=False):
    original_dtype = x.dtype
    if original_dtype == torch.float16:
        x = x.to(torch.float32)
    if exclusive:
        cumsum = torch.cumsum(x, dim=axis) - x
    else:
        cumsum = torch.cumsum(x, dim=axis)
    if reverse:
        cumsum = torch.cumsum(torch.flip(x, dims=[axis]), dim=axis)
        if exclusive:
            cumsum = cumsum - torch.flip(x, dims=[axis])
        cumsum = torch.flip(cumsum, dims=[axis])
    return cumsum.to(original_dtype)
```

## H012 · cumprod

**检查义务：** 有限小整数浮点输入，有效轴；exclusive=False、reverse=False。

**核查发现：** exclusive 分支使用 cumprod[:-1]，切片固定第一维；当前登记域未启用该分支。

**当前可用结论：** 域外切片与 axis 的关系值得另查，但不能据此把当前域的通过记录标成错误。

**缺少与下一步：** 补目标 API 否定理由；按 axis/标志分开建立范围，真实源/迁移断言仍缺。

否定判断：intenttester-target-api {"valid": false}

哈希匹配的原始对应代码：[本地来源](F:/codes/python/DLLens/data/working_dir/rq1/dllens/tensorflow/counterparts/tf.math.cumprod.json)

### source counterpart

```python
def tensorflow_call(x,axis=0,exclusive=False,reverse=False):
  return tf.math.cumprod(x,axis,exclusive,reverse)
```

### target counterpart

```python
def pytorch_call(x, axis=0, exclusive=False, reverse=False):
    if exclusive:
        if reverse:
            x = x.flip(dims=[axis])
        cumprod = torch.cumprod(x, dim=axis)
        ones_shape = list(x.shape)
        ones_shape[axis] = 1
        ones_tensor = torch.ones(ones_shape, dtype=x.dtype, device=x.device)
        cumprod = torch.cat((ones_tensor, cumprod[:-1]), dim=axis)
        if reverse:
            cumprod = cumprod.flip(dims=[axis])
        return cumprod
    else:
        if reverse:
            x = x.flip(dims=[axis])
        cumprod = torch.cumprod(x, dim=axis)
        if reverse:
            cumprod = cumprod.flip(dims=[axis])
        return cumprod
```

