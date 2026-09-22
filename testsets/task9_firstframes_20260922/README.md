# Task9：14组测试的穿衣首帧与人体参数

本目录是独立、追加式测试集。**原仓库的数据、动作划分、代码、网页及根清单均不修改。** 本测试集使用自己的 `dataset.json`、`manifest.json` 和校验脚本。

## 内容与状态

- **14组动作、15份目标首帧**：85_12同时保留`shorts`和`skirt`，默认展示/选用短裤版本，不删除裙子版本。
- **14份几何无穿、1份有穿失败候选**。按每组默认版本统计，是13组无穿、CT004一组失败。
- **CT018采用用户确认的SMPL v1.1女性人体**，保留该版本实际betas、pose、translation和scale。旧v1.0原版人体未恢复，不再把它作为本新测试集的必需模型。
- **CT004保存有穿目标首帧及失败证据**，明确`geometry_passed=false`。两个源准备姿态的清理失败另存`diagnostics_not_target/`，不冒充目标首帧。
- **只认证单个首帧几何**，不是14条完整服装仿真、静态平衡或全部动力学就绪。相交检查不证明有限厚度间隙、人体自身无自交或连续动作无穿。

[本地检查界面](index.html)提供15份首帧正背图、状态筛选、放大拖动、人工备注和JSON导出。浏览器直接打开即可，不需网络或SMPL模型；也可在本目录运行`python -m http.server 8000 --bind 127.0.0.1`后访问本地页面。GitHub文件浏览器不会执行HTML，可克隆后打开。原仓库网站未修改或接入本目录。

## 目录和读取

```text
dataset.json                         # 14组映射、15份快照、默认版本及状态
manifest.json                        # 本目录全部交付文件的大小/SHA256
cases/<case>/<variant>/
  firstframe.npz                     # 实际衣物+人体、原拓扑、rest、部件及附加字段
  body_parameters.json               # 模型身份、性别、betas、首帧pose/trans/scale、坐标和来源
  state.json                         # 本新测试集的明确验收/失败状态
  components.json                    # 部件名称与顶点/面映射
  cloth.obj / body.obj               # 同一实际首帧的便携网格
  reports/                           # 严格相交、包含、质量、来源、渲染及原验收记录
  media/preview_front_back.png        # 从同一NPZ渲染的正背图
  references/                        # 部分案例保留的原rest参考/附着元数据
cases/ct_00004/diagnostics_not_target/# 源姿态失败尝试，非额外目标首帧
docs/                                # 质量、人体参数、CT及C-IPC限制说明
tools/                               # 独立校验、示例读取和检查页构建工具
```

```bash
python -m pip install -r requirements.txt
python tools/validate.py
python tools/load_firstframe.py added_85_12 --variant shorts
python tools/load_firstframe.py added_85_12 --variant skirt
python tools/load_firstframe.py ct_00018
```

`firstframe.npz`使用`numpy.load(..., allow_pickle=False)`读取；`cloth`为衣物顶点，`triangles`为衣物三角形，`body`/`body_triangles`为实际人体，`rest`为本次实际保留的材料参考，`component_id`/`component_names`用于分层。所有数组索引从0开始；OBJ面索引按格式从1开始。统一单位为米、坐标Y-up。部分NPZ还有速度、蒙皮/源参考或C-IPC缝合字段，不应误把它们丢弃或认为全部速度为零。

原14份展示结果的NPZ原始字节不变。新增85_12裙子版由Task8已验收转移末态无损导出：衣物、人体、rest、拓扑和速度数组保持原值，并重新通过首帧严格检查/包含/穿着复核。没有从全序列的人体修复帧取初态。

## 人体参数与体型

13份快照使用SMPL v1.1，2份C-IPC仅有原生人体网格。`body_parameters.json`逐份保存精确模型版本/性别、模型文件和数值缓存hash、10维betas、72维轴角pose（弧度）、3维translation（米）、scale和原动作来源。**不打包SMPL模型权重或模型缓存**；仅加载已保存网格无需这些模型。

- 00242的06_13、85_12两版本均保留绑定女性体型。源静态网格乘0.1是单位换算，**最终人体SMPL scale=1，不能再缩小10倍**。
- D-LAYERS的输出pose/translation已转换到Y-up；原始Z-up参数与转换公式单独保留。不要对已转换参数再旋转一次。
- 00396为male绑定betas，00756为female绑定betas，不使用旧网页零betas人体预览。二者原float32流水线造成约0.35/0.38微米的独立重建差异，实际保存人体网格始终是精确依据，不把舍入误差当作表面修复。
- CT018使用确认的新v1.1女性人体及scale≈0.986918；CT004失败候选使用v1.1男性人体及scale≈0.992812。冻结目标骨骼/位移参数保持。
- C-IPC人体是12811点原生网格，**没有可用SMPL性别/betas/pose**。参数明确为null，保留原drape人体及后续shell坐标转换说明；不虚构零betas。原生动作来源和hash可追溯，但本目录不打包完整逐帧人体动作网格。

## 质量限制不能忽略

| 组/版本 | 已知限制 |
|---|---|
| CC01_01、CC55_27 | 几何修复而非物理松弛；派生三维代理rest的个别小面最大伸长约13.013/27.667。另存原参考，但不得把原参考误称本次求解所用rest。 |
| CC05_06 | 源修复改变代理rest小面，实际参考下最大伸长4.066；原参考另存。 |
| CC05_08、CC144_02 | 局部最大伸长约1.645/1.620，不满足统一1.5屏障。 |
| D-LAYERS00756 | 保留原生初态约2.204的最大伸长及宽松外套。 |
| 85_12 shorts | 短裤局部修复最大22.998mm，主伸长约0.01968–3.00689；原上衣/人体不变。 |
| C-IPC单层 | 局部缝合开口3.541mm与高压缩保留，包含未收敛IPC试验的几何种子；不是精确缝合平衡。 |
| C-IPC多层 | 仅0.045mm局部微调；原791条缝合及约0.301mm最大缝隙保留。 |
| CT018新体型 | 原裙孔缘最大主伸长6.132，末速1.601m/s；50kPa为构造材料，不是原CT材料复现。 |
| CT004失败 | 目标候选CC=954、CB=1957、内部衣物点424；不得作为无穿初态使用。 |

完整数值和修复来源位于每份`reports/`及`docs/`。不要通过将`rest`替换成最终衣物位置来隐藏应变，也不要将单帧无穿自动外推到后续动作。

## 独立验证与来源

`python tools/validate.py`核对目录清单hash、所有NPZ数组、部件/拓扑、人体参数、图像与几何报告坐标摘要、13组默认状态、15份快照及85_12两版共享人体/上衣。它重验归档一致性，**不是重新运行精确相交求解器**；原独立检查结果及checker hash保留在reports。

人体动作仍可按`body_parameters.json.original_motion`追溯原仓库相对文件及固定commit；C-IPC指向原项目原生场景。`local-evidence:`和`external-reference:`字符串只用于来源追溯，不是运行路径。所有本目录页面/工具只读取本目录文件，不依赖实验服务器绝对路径。素材与模型仍遵循各原始来源的许可/使用条件，本归档不替代其授权，也不重新许可SMPL模型。
