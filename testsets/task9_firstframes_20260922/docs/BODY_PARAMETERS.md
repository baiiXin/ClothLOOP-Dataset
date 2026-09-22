# 发布人体参数只读审计（15份首帧）

2026-09-22T21:14:06.512061+08:00

范围：14组选择＋85_12裙子variant，共15份；13份有SMPL参数，2份CIPC仅原生网格。本报告不发布模型权重、不推送、不改既有结果。实际body顶点/面是精确几何依据；浮点重建误差另报。

| 组 | 实际模型/性别 | scale | 重建最大误差(m) | 源动作相对路径 |
|---|---|---:|---:|---|
|ct_00004|SMPL v1.1 male|0.9928121566772461|0|ClothTransformer/body_sequences/sim_00004.npz|
|ct_00018|SMPL v1.1 female|0.9869181513786316|0|ClothTransformer/body_sequences/sim_00018.npz|
|cc_05_06|SMPL v1.1 female|1.0|0|ContourCraft/body_sequences/validation8/05_06.npz|
|cc_05_08|SMPL v1.1 female|1.0|0|ContourCraft/body_sequences/validation8/05_08.npz|
|cc_05_16|SMPL v1.1 female|1.0|0|ContourCraft/body_sequences/validation8/05_16.npz|
|cc_01_01|SMPL v1.1 female|1.0|0|ContourCraft/body_sequences/validation8/01_01.npz|
|cc_55_27|SMPL v1.1 female|1.0|0|ContourCraft/body_sequences/validation8/55_27.npz|
|cc_144_02|SMPL v1.1 female|1.0|0|ContourCraft/body_sequences/validation8/144_02.npz|
|dlayers_00396|SMPL v1.1 male|1.0|3.5e-07|D-LAYERS/body_sequences/sample_clips/00396.pkl|
|dlayers_00756|SMPL v1.1 female|1.0|3.76e-07|D-LAYERS/body_sequences/sample_clips/00756.pkl|
|added_06_13|SMPL v1.1 female|1.0|0|D-LAYERS/body_sequences/06_13.pkl|
|added_85_12|SMPL v1.1 female|1.0|0|D-LAYERS/body_sequences/85_12.pkl|
|added_85_12_skirt|SMPL v1.1 female|1.0|0|D-LAYERS/body_sequences/85_12.pkl|
|cipc_dress_knife|原生网格；SMPL/gender/betas未知|1|网格逐点相等|Projects/FEMShell/input/Rumba_Dancing|
|cipc_multilayer|原生网格；SMPL/gender/betas未知|1|网格逐点相等|Projects/FEMShell/input/Kick|

## 绑定体型与坐标语义

- 00396：male，betas=[0.09598314762115479,0.9216049313545227,0,0,0,0,0,0,0,0]。00756：female，betas=[2.913630723953247,0.5517416596412659,0,0,0,0,0,0,0,0]；分别核对原meta.json，不使用零betas网页预览。00756片段0对应完整01_10动作508帧。
- 00242：female，前两betas为2.6669766902923575、0.3537134528160097，其余约1e-14的拟合值完整保留在JSON；06_13、85_12短裤与裙子均保留。源静态网格scale=10，转米0.1；最终SMPL体scale=1，不应二次缩放。
- D-LAYERS统一S=[[1,0,0],[0,0,1],[0,-1,0]]，R_out=S@R_raw；t_out=S@t_raw+S@J0-J0。输出72维pose和trans已完成转换，不可再旋转。根J0、原始和输出参数及数值误差逐组写入JSON。
- CT004/018保留冻结pose/betas/trans/scale，明确采用v1.1；不是v1.0精确恢复。CT004仍有穿透，不能标无穿。CT018明确使用target_after_ipc。
- 六组CC采用官网female+各自原betas，完整保留root/关节/手部姿态和trans；模型默认性别并非从NPZ推测，依据原官方loader/config复核。
- CIPC每体12811点/25472面，不是6890点SMPL；仅可存model_kind=native_mesh及null参数，不能填零betas来冒充可重建。首帧取drape中人体，后续shell0..120平移(0,-0.75,0)，25Hz。所有121个动作OBJ和drape的hash已列JSON。

## 发布字段建议

每份保存实际body_vertices/body_faces；13份SMPL再存model family/version/gender/文件名与hash、10维betas、72维axis-angle pose（弧度）、3维trans（米）、scale、坐标约定及原动作相对路径/hash/帧映射。模型权重不打包。CIPC把SMPL字段显式null，保留原网格/平移及原生动作来源。

JSON包含全部15份原NPZ的hash、逐组完整参数、模型与cache哈希和独立重建误差。两份D-LAYERS sample_clips通过冻结commit的本地Git blob验证实际字节hash，并核对clip首帧等于完整源动作对应帧；未展开或修改稀疏checkout。

完整参数与逐份重建审计：各快照目录的 body_parameters.json。
