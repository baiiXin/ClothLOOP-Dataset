# ClothLOOP-Dataset：人体训练／测试划分与初值

本目录按来源保留当前确定的数据及必要元数据，所有数据文件均为实体文件，不依赖 DATA 目录的符号链接。

| 来源 | 人体动作 | 衣服与初值 |
| --- | --- | --- |
| ClothTransformer | 7 条已去重、经最新关节合理性修复的 SMPL 参数序列 | 用户选定 `CT-sim_00000`、`CT-sim_00002` 两件静态网格 |
| ContourCraft / HOOD-VTO | 60 条：52 条 VTO 来源 + 8 条 HOOD 验证动作，每条只保留 NPZ | 32 个 SMPL + 25 个 SMPL-X 衣服／套装 OBJ |
| D-LAYERS / CMU | 原有22条动作 + 2条样本原始片段，PKL参数 | 40套所选初值，89件衣服 + 40个人体网格；20个 frame0、20个 restpose |

人体动作合计91条。按2026-09-20用户确认名单，52条训练、12条测试、27条保留但未纳入本轮划分。原92条初选中的10条ClothTransformer动作此前已归并为7条。40套衣服初值是静态状态绑定，不另外计为40条运动；衣服不分配训练／测试标签，也未宣称完成所有来源的全库去重。

## 本轮人体划分

| 来源／分组 | 训练 | 测试 | 未纳入本轮划分 |
| --- | ---: | ---: | ---: |
| ClothTransformer | 0 | 2 | 5 |
| ContourCraft / VTO52 | 52 | 0 | 0 |
| ContourCraft / HOOD validation8 | 0 | 6 | 2 |
| D-LAYERS原样本片段 | 0 | 2 | 0 |
| D-LAYERS已有精选动作 | 0 | 2 | 20 |
| 合计 | 52 | 12 | 27 |

训练集为VTO52的全部52条。测试集为CT `sim_00004`、`sim_00018`；ContourCraft `05_06`、`05_08`、`05_16`、`01_01`、`55_27`、`144_02`；D-LAYERS样本 `00396`、`00756` 及补充动作 `06_13`、`85_12`。其中 `144_02` 使用本次指定的ContourCraft版本，未纳入D-LAYERS同名版本。

完整清单及文件SHA-256见 [splits/body_sequences.json](splits/body_sequences.json)。[train.txt](splits/train.txt)、[test.txt](splits/test.txt)、[unassigned.txt](splits/unassigned.txt) 每行一个相对于仓库根目录的参数文件路径。训练／测试间已检查CMU原动作编号和文件SHA-256无重叠；未纳入本轮的动作可能与已选动作同源，不应自动混入训练集。

新增样本片段使用本地帧号0起始，原始帧号映射保存在同名JSON中：

| 样本 | 原动作 | 原始帧号（0起始，含两端） | 帧数 | 假定30 FPS时长 |
| --- | --- | --- | ---: | ---: |
| 00396 | 114_07 | 0–404 | 405 | 13.50秒 |
| 00756 | 01_10 | 508–772 | 265 | 8.83秒 |

00396保留完整405帧文件的原始字节；00756从817帧原动作截取265帧并重编号，姿态、平移和数据类型逐帧完全一致，未重采样。两套 `frame0` 初值均来自对应样本起始帧，人体和衣服整套保留。源动作PKL不含体型betas，因此不宣称仅凭动作参数即可重建与绑定初值完全相同的人体；网页人体视频采用样本性别与零betas作预览，明确标记此限制。

00396、00756只加入人体动作参数、静态首帧人体／服装网格、元数据及小体积预览，**不包含逐帧服装真值或完整服装仿真大文件**。

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
  body_sequences/      # 原有22个动作PKL
    sample_clips/      # 00396、00756参数片段及原始帧号映射
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
splits/                # 训练／测试／未纳入本轮清单
```

## 数据含义

ClothTransformer 只保留 `smpl_parameters.npz` 的参数内容：`poses`、`body_pose`、`global_orient`、`transl`、`betas`、`scale`、`gender`、`fps`。每条 240 帧、60 FPS、4 秒。静态说明记录所需 SMPL 模型文件名和校验值，模型本身未打包。重建公式为：

`V_world = scale * SMPL(betas, global_orient, body_pose, transl=0) + transl`

两件衣服采用已浏览页面的静态网格，与用户选择一致，来源为原仿真 `initial[:, :3]`。这不是为重建后人体重新适配或通过碰撞认证的初值。完整衣服仿真数组、速度、展开三角形缓存、逐帧人体网格、其他 CT 衣服、旧拟合版本和渲染预览均不在本目录。

ContourCraft 动作 NPZ 为原已验证文件，保留原帧数和体型；每条动作不再同时存一份 PKL。来源的 52 条训练动作取 VTO shape00，与源训练表里的多个体型实例并非一一对应；训练表仅用于追溯。本目录不宣称已覆盖 HOOD 原训练任务所需的全部材料或预处理资产。

D-LAYERS 人体PKL为 `poses`、`trans` 按帧键存储的动作参数；新增样本片段仅作上述截取和帧号重编号。索引中的30 FPS是现有播放假定，不能当作已确认的采集帧率。

D-LAYERS 初值保持原始 NPZ 字节和坐标。`binding.json` 的 `path_base="."`，其中人体／衣服文件相对于该 binding 文件所在目录解析；`source` 只作原 DATA 路径追溯。人体与衣服必须整套使用，不能混用其他 sample 或姿态。碰撞状态依据所选状态的上传报告，人体自身相交单独保留，不代表整个动作过程中无穿透。原始坐标与显示用 Y-up 变换在 binding 中区分记录。

## 校验与来源

索引中的相对文件路径以本目录为根（binding内部路径除外）。`manifest.json` 覆盖科学数据与索引说明，`source_reference_base` 下的路径仅用于追溯，不是运行依赖。原有NPZ/PKL/OBJ和新增静态网格均保留原始字节；新增00756动作片段在manifest中明确记录为截取结果，并保留完整源文件SHA-256。文件大小按实际字节统计，不含打包压缩率假定。运行 `python scripts/validate_dataset.py` 校验文件哈希、52/12/27划分、片段帧号和初值绑定；科学元数据有意修改后可加 `--refresh-manifest` 更新清单。

上述三个来源目录不打包 HTML、视频、图片、缓存、SMPL 模型或旧体积统计报告。原始来源库和实验结果继续保留在相邻 DATA 工作空间。整理过程使用 CPU，未使用 CUDA2。

## Dataset Explorer

网站将人体动作、独立服装资产、人体—服装绑定初值分开浏览，支持分类筛选、视频播放、可旋转的三维网格、碰撞报告和选择 JSON 导出。

预期访问地址：**https://baiixin.github.io/ClothLOOP-Dataset/**

页面代码与已提交预览位于 `web/`，构建脚本位于 `scripts/`。GLB、网页索引和 HTML 详情页在构建时生成，不提交 Git；GitHub Actions 通过校验与浏览器测试后发布。构建只使用本仓库的输入，不依赖相邻 DATA 工作空间或 SMPL 模型。

根目录 `manifest.json` 和 `validation.json` 描述科学数据包，不统计网页及构建工具；预览文件由 `web/media/manifest.json` 单独校验。网站 GLB 采用 float32 显示坐标，原始 NPZ/PKL/OBJ 数值保持不变。

完整的本地启动、数据结构、新增数据、构建与部署说明见 [web/README.md](web/README.md)。
