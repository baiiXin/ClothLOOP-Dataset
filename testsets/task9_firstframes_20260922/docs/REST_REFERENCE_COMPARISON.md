# 原参考rest与实际派生rest对照

这里只提供可恢复的原参考和只读统计。已验收firstframe.npz中的几何及实际求解rest一律没有修改。原参考仍是三维绑定快照/restpose代理，不能伪称原裁片UV。

| 组 | 实际交付rest：主伸长范围 | 原参考：主伸长范围 | 实际最大面面积变化（实际/原） | 可选原参考 |
|---|---|---|---|---|
|cc_05_06|0.719951–4.06624|0.250036–1.73724|0.0711047|[NPZ](../cases/cc_05_06/default/references/rest_reference_original.npz) / [完整分布](../cases/cc_05_06/default/references/rest_reference_comparison.json)|
|cc_01_01|0.153528–13.0131|0.0286992–2.2103|0.023289|[NPZ](../cases/cc_01_01/default/references/rest_reference_original.npz) / [完整分布](../cases/cc_01_01/default/references/rest_reference_comparison.json)|
|cc_55_27|0.0262057–27.6667|0.015099–1.22965|0.00835828|[NPZ](../cases/cc_55_27/default/references/rest_reference_original.npz) / [完整分布](../cases/cc_55_27/default/references/rest_reference_comparison.json)|

05_06可选原参考由未修复source frame0做与实际代理rest相同的刚性变换，拟合误差小于1e-10 m；记录了R/t和原始哈希。它没有参与已经结束的900步IPC求解。原参考较少受去穿透局部位置修复造成的小面收缩影响，但不能据此声称所有面满足1.5屏障。

01_01/55_27可选原参考来自输出中已有original_rest，对应原restpose而非运动frame0，未包含后续官网体型场适配。这两组没有做物理求解，而是形状适配/LBS后局部几何清理。比较同时揭示形状场对个别小面的压缩，以及局部去穿透位置修复对小面的展开；不把这些高主伸长掩盖为普通正常材料应变。

所有三组的可选原参考都只是供后续选用的来源清楚的三维代理，不是已验收动力学材料。后续加载任一参考前，必须重新选择/验证材料基准并检查应变、几何和求解可行性；不能直接把13x/27x代理或替代原参考标成动力学就绪。已验收网格、实际交付rest和历史求解输入均未覆盖。
