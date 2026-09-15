# ClothLOOP-Dataset：精简初筛数据

本目录按来源保留当前确定的数据及必要元数据，所有数据文件均为实体文件，不依赖 DATA 目录的符号链接。

| 来源 | 人体动作 | 衣服与初值 |
| --- | --- | --- |
| ClothTransformer | 7 条已去重、经最新关节合理性修复的 SMPL 参数序列 | 用户选定 `CT-sim_00000`、`CT-sim_00002` 两件静态网格 |
| ContourCraft / HOOD-VTO | 60 条：52 条 VTO 来源 + 8 条 HOOD 验证动作，每条只保留 NPZ | 32 个 SMPL + 25 个 SMPL-X 衣服／套装 OBJ |
| D-LAYERS / CMU | 精选 22 条人体动作，保留原始 PKL | 38 套所选初值，85 件衣服 + 38 个人体网格；18 个 frame0、20 个 restpose |

人体动作合计 89 条：原 92 条初选中的 10 条 ClothTransformer 动作已经归并为 7 条。38 套衣服初值是静态状态绑定，不另外计为 38 条运动。所有最终训练／测试归属仍为 `unassigned`；这里只完成已选资产整理，不把源训练划分自动当成最终划分，也未宣称完成所有来源的全库去重。

## 目录

```text
ClothTransformer/
  body_sequences/      # 7 个 SMPL 参数 NPZ + 各自静态参数说明
  garments/            # CT-sim_00000.obj、CT-sim_00002.obj
  deduplication.json   # 10 → 7 的动作来源映射
ContourCraft/
  body_sequences/vto52/
  body_sequences/validation8/
  garments/smpl/
  garments/smplx/
  provenance/          # 来源训练表、转换依据、验证体型表
D-LAYERS/
  body_sequences/      # 22 个动作 PKL
  garment_body_initials/<sample>/
    human.npz
    garments/<name>.npz
    binding.json
    collision.json
    sample_meta.original.json
  garment_body_initials.json
  selection.original.json
  collision_report.snapshot.json
  collision_classification.snapshot.json
body_sequences.json    # 动作、帧数、帧率、来源及分类索引
garments.json          # 两件 CT 与 57 份 ContourCraft 静态衣服索引
manifest.json          # 文件大小、SHA256、来源清单
validation.json        # 本版校验结果
```

## 数据含义

ClothTransformer 只保留 `smpl_parameters.npz` 的参数内容：`poses`、`body_pose`、`global_orient`、`transl`、`betas`、`scale`、`gender`、`fps`。每条 240 帧、60 FPS、4 秒。静态说明记录所需 SMPL 模型文件名和校验值，模型本身未打包。重建公式为：

`V_world = scale * SMPL(betas, global_orient, body_pose, transl=0) + transl`

两件衣服采用已浏览页面的静态网格，与用户选择一致，来源为原仿真 `initial[:, :3]`。这不是为重建后人体重新适配或通过碰撞认证的初值。完整衣服仿真数组、速度、展开三角形缓存、逐帧人体网格、其他 CT 衣服、旧拟合版本和渲染预览均不在本目录。

ContourCraft 动作 NPZ 为原已验证文件，保留原帧数和体型；每条动作不再同时存一份 PKL。来源的 52 条训练动作取 VTO shape00，与源训练表里的多个体型实例并非一一对应；训练表仅用于追溯。本目录不宣称已覆盖 HOOD 原训练任务所需的全部材料或预处理资产。

D-LAYERS 人体 PKL 为 `poses`、`trans` 按帧键存储的原始动作参数；索引中的 30 FPS 是现有播放假定，不能当作已确认的采集帧率。

D-LAYERS 初值保持原始 NPZ 字节和坐标。`binding.json` 的 `path_base="."`，其中人体／衣服文件相对于该 binding 文件所在目录解析；`source` 只作原 DATA 路径追溯。人体与衣服必须整套使用，不能混用其他 sample 或姿态。碰撞状态依据所选状态的上传报告，人体自身相交单独保留，不代表整个动作过程中无穿透。原始坐标与显示用 Y-up 变换在 binding 中区分记录。

## 校验与来源

索引中的相对文件路径以本目录为根（binding 内部路径除外）。`manifest.json` 覆盖全部数据与说明文件，`source_reference_base` 下的路径仅用于追溯，不是运行依赖。NPZ/PKL/OBJ 均已核对来源 SHA256；适配后的 JSON 只更改索引和相对路径。文件大小按实际字节统计，不含打包压缩率假定。

上述三个来源目录不打包 HTML、视频、图片、缓存、SMPL 模型或旧体积统计报告。原始来源库和实验结果继续保留在相邻 DATA 工作空间。整理过程使用 CPU，未使用 CUDA2。

## Dataset Explorer

网站将人体动作、独立服装资产、人体—服装绑定初值分开浏览，支持分类筛选、视频播放、可旋转的三维网格、碰撞报告和选择 JSON 导出。

预期访问地址：**https://baiixin.github.io/ClothLOOP-Dataset/**

页面代码与已提交预览位于 `web/`，构建脚本位于 `scripts/`。GLB、网页索引和 HTML 详情页在构建时生成，不提交 Git；GitHub Actions 通过校验与浏览器测试后发布。构建只使用本仓库的输入，不依赖相邻 DATA 工作空间或 SMPL 模型。

根目录 `manifest.json` 和 `validation.json` 描述科学数据包，不统计网页及构建工具；预览文件由 `web/media/manifest.json` 单独校验。网站 GLB 采用 float32 显示坐标，原始 NPZ/PKL/OBJ 数值保持不变。

完整的本地启动、数据结构、新增数据、构建与部署说明见 [web/README.md](web/README.md)。
