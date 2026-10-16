# 110组现成测试代码覆盖表

统计单位是候选ID（不是独立测试数）；相同公开测试可能被多个候选复用。

“有”指已保存公开测试代码（含已说明的别名/命名空间或运算符入口），不是执行成功，也不代表整段包装函数已覆盖。组合目标单列；尚未检查输入/意图对齐。

|候选|源 API|目标 API/调用|源端|目标端|备注|
|---|---|---|---|---|---|
|[D0001](candidates/D0001/README.md)|`torch.abs`|`tf.abs`|有|有|输入与检查目标待核对|
|[D0002](candidates/D0002/README.md)|`torch.acos`|`tf.acos`|有|有|输入与检查目标待核对|
|[D0003](candidates/D0003/README.md)|`torch.arccos`|`tf.acos`|有|有|输入与检查目标待核对|
|[D0004](candidates/D0004/README.md)|`torch.arcsin`|`tf.asin`|有|有|输入与检查目标待核对|
|[D0005](candidates/D0005/README.md)|`torch.arctan`|`tf.math.atan`|有|有|输入与检查目标待核对|
|[D0006](candidates/D0006/README.md)|`torch.asin`|`tf.asin`|有|有|输入与检查目标待核对|
|[D0007](candidates/D0007/README.md)|`torch.atan`|`tf.math.atan`|有|有|输入与检查目标待核对|
|[D0008](candidates/D0008/README.md)|`torch.ceil`|`tf.math.ceil`|有|有|输入与检查目标待核对|
|[D0009](candidates/D0009/README.md)|`torch.cos`|`tf.cos`|有|有|输入与检查目标待核对|
|[D0010](candidates/D0010/README.md)|`torch.cosh`|`tf.cosh`|有|有|输入与检查目标待核对|
|[D0011](candidates/D0011/README.md)|`torch.exp`|`tf.exp`|有|有|输入与检查目标待核对|
|[D0012](candidates/D0012/README.md)|`torch.expm1`|`tf.exp`|有|有|保留真实配对 expm1→exp；不能因名称不一致改成 expm1→expm1|
|[D0013](candidates/D0013/README.md)|`torch.floor`|`tf.floor`|有|有|输入与检查目标待核对|
|[D0014](candidates/D0014/README.md)|`torch.log`|`tf.math.log`|有|有|输入与检查目标待核对|
|[D0015](candidates/D0015/README.md)|`torch.log1p`|`tf.math.log1p`|有|有|输入与检查目标待核对|
|[D0016](candidates/D0016/README.md)|`torch.neg`|`tf.negative`|有|有|输入与检查目标待核对|
|[D0017](candidates/D0017/README.md)|`torch.negative`|`tf.negative`|有|有|输入与检查目标待核对|
|[D0018](candidates/D0018/README.md)|`torch.reciprocal`|`tf.math.reciprocal`|有|有|输入与检查目标待核对|
|[D0019](candidates/D0019/README.md)|`torch.round`|`tf.round`|有|有|输入与检查目标待核对|
|[D0020](candidates/D0020/README.md)|`torch.sigmoid`|`tf.sigmoid`|有|有|输入与检查目标待核对|
|[D0021](candidates/D0021/README.md)|`torch.sign`|`tf.sign`|有|有|输入与检查目标待核对|
|[D0022](candidates/D0022/README.md)|`torch.sin`|`tf.sin`|有|有|输入与检查目标待核对|
|[D0023](candidates/D0023/README.md)|`torch.sinh`|`tf.sinh`|有|有|输入与检查目标待核对|
|[D0024](candidates/D0024/README.md)|`torch.sqrt`|`tf.sqrt`|有|有|输入与检查目标待核对|
|[D0025](candidates/D0025/README.md)|`torch.square`|`tf.square`|有|有|输入与检查目标待核对|
|[D0026](candidates/D0026/README.md)|`torch.tan`|`tf.tan`|有|有|输入与检查目标待核对|
|[D0027](candidates/D0027/README.md)|`torch.tanh`|`tf.tanh`|有|有|输入与检查目标待核对|
|[D0029](candidates/D0029/README.md)|`tf.abs`|`torch.abs`|有|有|输入与检查目标待核对|
|[D0030](candidates/D0030/README.md)|`tf.acos`|`torch.acos`|有|有|输入与检查目标待核对|
|[D0031](candidates/D0031/README.md)|`tf.asin`|`torch.asin`|有|有|输入与检查目标待核对|
|[D0032](candidates/D0032/README.md)|`tf.atan`|`torch.atan`|有|有|输入与检查目标待核对|
|[D0033](candidates/D0033/README.md)|`tf.cos`|`torch.cos`|有|有|输入与检查目标待核对|
|[D0034](candidates/D0034/README.md)|`tf.cosh`|`torch.cosh`|有|有|输入与检查目标待核对|
|[D0035](candidates/D0035/README.md)|`tf.exp`|`torch.exp`|有|有|输入与检查目标待核对|
|[D0036](candidates/D0036/README.md)|`tf.floor`|`torch.floor`|有|有|输入与检查目标待核对|
|[D0037](candidates/D0037/README.md)|`tf.math.abs`|`torch.abs`|有|有|输入与检查目标待核对|
|[D0038](candidates/D0038/README.md)|`tf.math.acos`|`torch.acos`|有|有|输入与检查目标待核对|
|[D0039](candidates/D0039/README.md)|`tf.math.asin`|`torch.asin`|有|有|输入与检查目标待核对|
|[D0040](candidates/D0040/README.md)|`tf.math.atan`|`torch.atan`|有|有|输入与检查目标待核对|
|[D0041](candidates/D0041/README.md)|`tf.math.ceil`|`torch.ceil`|有|有|输入与检查目标待核对|
|[D0042](candidates/D0042/README.md)|`tf.math.cos`|`torch.cos`|有|有|输入与检查目标待核对|
|[D0043](candidates/D0043/README.md)|`tf.math.cosh`|`torch.cosh`|有|有|输入与检查目标待核对|
|[D0044](candidates/D0044/README.md)|`tf.math.exp`|`torch.exp`|有|有|输入与检查目标待核对|
|[D0045](candidates/D0045/README.md)|`tf.math.expm1`|`torch.expm1`|有|有|输入与检查目标待核对|
|[D0046](candidates/D0046/README.md)|`tf.math.floor`|`torch.floor`|有|有|输入与检查目标待核对|
|[D0047](candidates/D0047/README.md)|`tf.math.log`|`torch.log`|有|有|输入与检查目标待核对|
|[D0048](candidates/D0048/README.md)|`tf.math.log1p`|`torch.log1p`|有|有|输入与检查目标待核对|
|[D0049](candidates/D0049/README.md)|`tf.math.negative`|`torch.neg`|有|有|输入与检查目标待核对|
|[D0050](candidates/D0050/README.md)|`tf.math.reciprocal`|`torch.Tensor.__rtruediv__`|有|有|目标官方test_rdiv通过30/x测试反向除法；不是与源侧完全相同的1/x输入|
|[D0051](candidates/D0051/README.md)|`tf.math.round`|`torch.round`|有|有|输入与检查目标待核对|
|[D0052](candidates/D0052/README.md)|`tf.math.sigmoid`|`torch.sigmoid`|有|有|输入与检查目标待核对|
|[D0053](candidates/D0053/README.md)|`tf.math.sign`|`torch.sign`|有|有|输入与检查目标待核对|
|[D0054](candidates/D0054/README.md)|`tf.math.sin`|`torch.sin`|有|有|输入与检查目标待核对|
|[D0055](candidates/D0055/README.md)|`tf.math.sinh`|`torch.sinh`|有|有|输入与检查目标待核对|
|[D0056](candidates/D0056/README.md)|`tf.math.sqrt`|`torch.sqrt`|有|有|输入与检查目标待核对|
|[D0057](candidates/D0057/README.md)|`tf.math.square`|`torch.square`|有|有|输入与检查目标待核对|
|[D0058](candidates/D0058/README.md)|`tf.math.tan`|`torch.tan`|有|有|输入与检查目标待核对|
|[D0059](candidates/D0059/README.md)|`tf.math.tanh`|`torch.tanh`|有|有|输入与检查目标待核对|
|[D0060](candidates/D0060/README.md)|`tf.negative`|`torch.negative`|有|有|输入与检查目标待核对|
|[D0061](candidates/D0061/README.md)|`tf.round`|`torch.round`|有|有|输入与检查目标待核对|
|[D0062](candidates/D0062/README.md)|`tf.sigmoid`|`torch.sigmoid`|有|有|输入与检查目标待核对|
|[D0063](candidates/D0063/README.md)|`tf.sign`|`torch.sign`|有|有|输入与检查目标待核对|
|[D0064](candidates/D0064/README.md)|`tf.sin`|`torch.sin`|有|有|输入与检查目标待核对|
|[D0065](candidates/D0065/README.md)|`tf.sinh`|`torch.sinh`|有|有|输入与检查目标待核对|
|[D0066](candidates/D0066/README.md)|`tf.sqrt`|`torch.sqrt`|有|有|输入与检查目标待核对|
|[D0067](candidates/D0067/README.md)|`tf.square`|`torch.square`|有|有|输入与检查目标待核对|
|[D0068](candidates/D0068/README.md)|`tf.tan`|`torch.tan`|有|有|输入与检查目标待核对|
|[D0069](candidates/D0069/README.md)|`tf.tanh`|`torch.tanh`|有|有|输入与检查目标待核对|
|[E001](candidates/E001/README.md)|`torch.add`|`tf.cast, tf.add`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E002](candidates/E002/README.md)|`tf.add`|`torch.add`|有|有|输入与检查目标待核对|
|[E003](candidates/E003/README.md)|`torch.sub`|`tf.subtract, tf.cast`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E004](candidates/E004/README.md)|`tf.subtract`|`torch.sub`|有|有|输入与检查目标待核对|
|[E005](candidates/E005/README.md)|`torch.mul`|`tf.cast, tf.multiply`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E006](candidates/E006/README.md)|`tf.multiply`|`torch.mul`|有|有|输入与检查目标待核对|
|[E007](candidates/E007/README.md)|`torch.div`|`tf.cast, tf.divide`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E008](candidates/E008/README.md)|`tf.divide`|`torch.div`|有|有|输入与检查目标待核对|
|[E009](candidates/E009/README.md)|`torch.maximum`|`tf.cast, tf.maximum`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E010](candidates/E010/README.md)|`tf.maximum`|`torch.maximum`|有|有|输入与检查目标待核对|
|[E011](candidates/E011/README.md)|`torch.minimum`|`tf.cast, tf.minimum`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E012](candidates/E012/README.md)|`tf.minimum`|`torch.min`|有|有|所选torch.min测试同时包含单输入归约与双输入逐元素分支，配对时用后者|
|[E013](candidates/E013/README.md)|`torch.pow`|`tf.cast, tf.pow`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E014](candidates/E014/README.md)|`tf.math.pow`|`torch.pow`|有|有|输入与检查目标待核对|
|[E015](candidates/E015/README.md)|`torch.atan2`|`tf.cast, tf.atan2`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E016](candidates/E016/README.md)|`tf.atan2`|`torch.atan2`|有|有|输入与检查目标待核对|
|[E017](candidates/E017/README.md)|`torch.reshape`|`tf.reshape`|有|有|输入与检查目标待核对|
|[E018](candidates/E018/README.md)|`tf.reshape`|`torch.Tensor.view`|有|有|输入与检查目标待核对|
|[E019](candidates/E019/README.md)|`torch.transpose`|`tf.transpose`|有|有|输入与检查目标待核对|
|[E020](candidates/E020/README.md)|`tf.transpose`|`torch.Tensor.permute, torch.Tensor.conj`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E021](candidates/E021/README.md)|`torch.squeeze`|`tf.squeeze`|有|有|输入与检查目标待核对|
|[E022](candidates/E022/README.md)|`tf.squeeze`|`torch.Tensor.squeeze`|有|有|输入与检查目标待核对|
|[E023](candidates/E023/README.md)|`torch.unsqueeze`|`tf.expand_dims`|有|有|输入与检查目标待核对|
|[E024](candidates/E024/README.md)|`tf.expand_dims`|`torch.Tensor.unsqueeze`|有|有|输入与检查目标待核对|
|[E025](candidates/E025/README.md)|`torch.concat`|`tf.concat`|有|有|输入与检查目标待核对|
|[E026](candidates/E026/README.md)|`tf.concat`|`torch.cat`|有|有|输入与检查目标待核对|
|[E027](candidates/E027/README.md)|`torch.stack`|`tf.stack`|有|有|输入与检查目标待核对|
|[E028](candidates/E028/README.md)|`tf.stack`|`torch.stack`|有|有|输入与检查目标待核对|
|[E029](candidates/E029/README.md)|`torch.clip`|`tf.cast, tf.where`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[E030](candidates/E030/README.md)|`tf.clip_by_value`|`torch.max, torch.clamp, torch.Tensor.new_ones`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[H001](candidates/H001/README.md)|`torch.prod`|`tf.reduce_prod, tf.identity`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[H002](candidates/H002/README.md)|`torch.matmul`|`tf.matmul, tf.expand_dims`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[H003](candidates/H003/README.md)|`torch.det`|`tf.linalg.det`|有|有|输入与检查目标待核对|
|[H004](candidates/H004/README.md)|`torch.trace`|`tf.linalg.trace`|有|有|输入与检查目标待核对|
|[H005](candidates/H005/README.md)|`torch.cumsum`|`tf.cumsum`|有|有|输入与检查目标待核对|
|[H006](candidates/H006/README.md)|`torch.cumprod`|`tf.math.cumprod`|有|有|输入与检查目标待核对|
|[H007](candidates/H007/README.md)|`tf.reduce_prod`|`torch.prod`|有|有|输入与检查目标待核对|
|[H008](candidates/H008/README.md)|`tf.matmul`|`torch.matmul, torch.Tensor.t, torch.Tensor.to_sparse, torch.Tensor.conj`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[H009](candidates/H009/README.md)|`tf.linalg.det`|`torch.linalg.det`|有|有|输入与检查目标待核对|
|[H010](candidates/H010/README.md)|`tf.linalg.trace`|`torch.Tensor.sum, torch.Tensor.dim, torch.Tensor.view, torch.diagonal, torch.Tensor.size`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺; 目标diagonal是trace组合的一部分；整段trace实现尚无现成测试|
|[H011](candidates/H011/README.md)|`tf.cumsum`|`torch.Tensor.to, torch.cumsum, torch.flip`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
|[H012](candidates/H012/README.md)|`tf.math.cumprod`|`torch.cumprod, torch.ones, torch.cat, torch.Tensor.flip`|有|都有（组件）|目标为组合：各API测试已分别收集，整段组合测试仍空缺|
