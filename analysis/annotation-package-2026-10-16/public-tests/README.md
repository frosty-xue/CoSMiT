# 110组公开测试代码材料包

入口：[逐组表](COVERAGE.md)。每个 candidates/ID 有源侧完整原测试文件、目标侧各API完整原测试文件、便于阅读的摘录和固定版本出处。

|覆盖情况|组数|
|---|---:|
|源侧API已有测试|110|
|目标单个API/运算符已有测试|93|
|目标组合的各组件已有测试，但整段组合测试缺失|17|
|缺少API级测试材料的组|0|

source-operation.py / target-operation.py 保存本批原始操作函数，供对照。它们不计入测试数量。17组组合测试缺口详见 summary.json 的 composite_target_ids；没有为这些组合另写新测试。

这是按用户允许的宽松口径配对的公开API测试材料，不是自动生成的迁移，也不是历史迁移记录。未修改任何测试断言；未执行测试；没有增加准确率或意图保持标签。

Ivy 测试依赖 Ivy、Hypothesis、pytest 和对应框架；测试调用与检查常在公共助手中。upstream/ 保留下载的原始目录和助手，但不是完整可安装仓库。运行时须使用 metadata 中固定提交的完整仓库和适配环境；摘录仅用于阅读。

TensorFlow 官方 sign 测试选用 testFloatBasic，它同时测试多个一元操作，包含 sign 的具体输入和参考检查。PyTorch 反向除法测试选用官方 test_rdiv（30/x），详见 D0050。cast 与稀疏转换也使用官方测试。

TensorFlow 顶层API测试若缺失，采用 Ivy 显式从 math 或 linalg 导出的同名入口测试，逐条记在 source_match / target_tests.match；torch.neg 使用官方文档说明的 negative 别名。没有修改测试内部名称。

组合目标各子操作有测试不代表组合函数有测试。旧 110 组的运行结果没有改动；新配对测试需要输入/检查目标核对和重新运行，才能用于后续实验。
