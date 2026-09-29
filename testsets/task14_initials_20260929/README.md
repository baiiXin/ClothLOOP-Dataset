# Task14：14 条测试序列的最终初值

[网页展示](https://baiixin.github.io/ClothLOOP-Dataset/test-initials/) · [索引](index.json) · [文件校验](manifest.json)

这里只发布每条序列最终选定的**首帧人体和衣服**，不是原绑定姿态，也不是完整仿真数据集；不覆盖 Task9 历史版本。14 组与 Task14 observation1 最终验收初态逐点、逐面一致，单位米、Y 向上，未平滑、简化、重新投影或单独对齐衣物。

每个 `cases/<case>/` 包含：

- `body.npz`：`vertices` 为 float64 `[V,3]` 实际初始人体（包含适用的局部表面修复），`faces` 为原三角面索引。
- `cloth.npz`：同样的 `vertices` 和 `faces`，另存 `component_id` 与 `component_names`；C-IPC 的组件是裁片，不等于服装件数。
- `preview.jpg`：真实初值双视角图。
- `provenance.json`：初态/拓扑/验收/选择索引 SHA-256、源帧0独立衣物相交报告和适用边界。

```python
import numpy as np
body = np.load('cases/ct_00004/body.npz', allow_pickle=False)
cloth = np.load('cases/ct_00004/cloth.npz', allow_pickle=False)
# body['vertices'], body['faces'], cloth['vertices'], cloth['faces']
```

网页 GLB 仅用于 float32 显示，下载 NPZ 保留实际 float64 坐标与原索引；人体与衣服共用同一坐标和相机，不分别归一化。

14 组首帧衣物自交、衣物—人体相交均为零；报告排除共顶点的边面相交，人体自身相交未认证为零，不外推连续时间保证。CT004 为 CC 短裤在内、上衣在外，CT018 为已确认新体型，85_12 为短裤版；两条 D-LAYERS 按许可直接采用原无穿初态。

不上传完整人体/衣物序列、材料 rest mesh、初速度、SMPL 模型、仿真缓存或训练权重。这是几何初值包，不是可直接复现完整动力学的包；已有序列参数与旧数据不更改。

## 体积（按实际文件字节）

14 组初值 NPZ 共 **11,742,626 字节，11.74 MB / 11.20 MiB**，包括人体/衣物坐标、三角面和衣物组件标识；不含图片和网页。初值连同图片、来源与索引约12.68 MB，精确文件大小见清单。

本机正式14序列测试集（8081源状态，跟随软链接、按实际文件去重）共 **14,662,409,263 字节，14.66 GB / 13.66 GiB**，含复现证据；不含复现运行目录的数据/参考结果为 **8,494,190,222 字节，8.49 GB / 7.91 GiB**。这些完整序列未随本次上传。

验证：在仓库根目录运行 `python scripts/validate_task14_initials.py`；网站构建也自动执行该检查，仅依赖本仓库文件和 NumPy。
