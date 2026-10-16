# 作者材料索取草稿（尚未发送）

## DLLens

Subject: Request for released paired test artifacts for 110 DLLens counterparts

Dear authors,

We are studying whether existing cross-framework test translations preserve API behavior and the objective of the source test. We have selected 110 counterpart records from your public artifact at commit `0f617e92c34d60bfdd3bc06d80c17d938879ed9c`.

The public records provide source-side input snippets and counterpart functions. To study existing translations without generating new ones, could you share the original saved source/target test programs associated with these records, if available?

In particular, we need:

- A mapping from each counterpart JSON to its source test and translated target test.
- The original inputs, checks/assertions or expected outcomes, and the corresponding target-side checks.
- Framework versions, execution configuration and recorded outcomes, if retained.
- Both successful and failed translations; we do not require repaired tests.
- Clarification on whether these artifacts were translated from existing tests or generated as differential programs around counterpart functions.

The attached candidate list includes exact API names and immutable links. If the public sample inputs and shared differential comparator are the only retained artifacts, confirmation would also help us describe the dataset accurately.

Thank you for your time.

附件建议：candidate-coverage.json（110 个候选及 source_url），或 COVERAGE.md。不要附当前实验预测、标签草稿或密钥。

## CrossProbe

Subject: Request for source-to-translated-test mapping and complete released corpus

Dear authors,

We are studying behavior and test-intent preservation in existing PyTorch/TensorFlow test migrations. We inspected the public CrossProbe repository and its 2025-04-12 release, including the `pytorch`, `tensorflow`, `pytorch-test` and `tensorflow-test` directories.

Could you share a complete source-to-generated-test manifest and any additional retained migration outputs, including failed translations? We are particularly interested in the APIs listed in the attached candidate table. Original tests, migrated scripts, input fixtures, checks or expected outcomes, framework versions, and generation/execution logs would help establish provenance.

We also found same-issue `-tf` scripts in the source directory. Clarification on which files are actual source/target pairs, versus later bug-report variants, would be valuable. We intend to preserve the released outputs unchanged and avoid generating replacement migrations.

Thank you for your time.
