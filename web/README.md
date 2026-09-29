# ClothLOOP Dataset Explorer

纯静态的科研数据浏览网站。Vite + TypeScript 管理页面，Three.js 只在三维详情页加载；GitHub Actions 生成资源、运行浏览器测试并部署 Pages。

## 本地构建

需要 Node.js 24、Python 3.12+、NumPy。无需 GPU、SMPL 模型、外部 DATA 目录或浏览器端 PKL 反序列化。

```bash
python3 -m pip install -r scripts/requirements-web.txt
cd web
npm ci
npm run build
python3 ../scripts/serve_web.py
```

访问 `http://127.0.0.1:4173/ClothLOOP-Dataset/`。这个测试服务器严格按真实静态路径返回文件，不会把不存在的详情路由回退成首页；支持视频HTTP单字节范围请求，供Chromium准确拖动进度，和Pages行为一致。

日常修改界面可在 `npm run assets` 后运行 `npm run dev`。`dev` 仅供开发；新增或检查真实详情路径时使用完整 build 和上述静态服务器。

## 结构与来源

```text
src/                       页面、样式、类型和按需加载的 Three.js 查看器
media/                     已提交的预览视频、WebP 和来源哈希索引
public/fonts/              小体积 CJK 字体子集及许可证
public/generated/          构建产生的 JSON、GLB、转换验证（不提交）
dist/                      Pages 发布产物，含真实详情页（不提交）
tests/                     Playwright 浏览器行为测试
../scripts/build_web_assets.py   独立资源构建；只读取仓库内输入
../scripts/static_routes.mjs     生成真实 HTML 路径、收集预览
../scripts/import_previews.py    可选的本机历史预览导入工具
```

根目录 `body_sequences.json`、`garments.json`、D-LAYERS 初值索引与每套 `binding.json` 是数据索引来源。`media/manifest.json` 只维护预览文件及来源哈希，不重新维护动作帧数、体型或碰撞状态。构建输出 `ClothLOOP.explorer.v1`，分成 `body`、`cloth`、`initials`；每项含稳定的 `key`、来源 ID、真实详情路径、预览、数据文件及 SHA-256。原数据链接固定到构建时 Git 提交。

当前页面路径：

- `/ClothLOOP-Dataset/`：总览。
- `/ClothLOOP-Dataset/body/`：动作；详情如 `body/ClothTransformer/sim_00000/`。
- `/ClothLOOP-Dataset/cloth/`：服装；详情如 `cloth/ClothTransformer/CT-sim_00002/`。
- `/ClothLOOP-Dataset/initials/`：绑定初值；详情如 `initials/D-LAYERS/01306/`。
- `/ClothLOOP-Dataset/test-initials/`：Task14 最终14组初值与 libuipc 完整仿真；详情如 `test-initials/ct_00004/`。桌面左右对照首帧3D与视频，窄屏上下排列。初值数据独立保存于 `testsets/task14_initials_20260929/`，不替换原绑定初值；构建自动核验独立清单及首帧几何哈希。新增视频在 `media/libuipc/`，不改变初值科学数据。

来源、类别、时长等筛选写入 query string；时长以 `<10 s` 和 `≥10 s` 分组。勾选仅保存到当前浏览器的 localStorage，并可导出带数据版本、文件路径和哈希的 JSON。网站不会写回服务器文件或更改仓库选择。

## 科研数据与展示数据

- NPZ/PKL/OBJ 输入原样保留；浏览器不加载完整动作网格或 SMPL 模型。
- 原人体 MP4 复用已有验证预览，字节不变；CT 的 7 段视频明确标注为最新关节修复对比，不能当成未经修改的原始动作。
- Task14 原14条1080×1080 H.264面片版共46,590,393字节，完整8081源帧，原文件全部保留。新增14条平滑版，详情页默认显示平滑版，可切换回原版；两组合计严格小于120,000,000字节。只读实际保存衣物及实际修复人体，不上传完整逐帧真值数组。画面标注源帧、时间、物理子步、非线性/线性迭代与求解耗时；CSV为区间子步之和，frame0无求解。两条D-LAYERS如实标为mixed_or_semi_implicit，不把所有计数称为full Newton。
- 平滑版直接调用ClothLOOP `render.py`主流程（冻结版本与文件SHA见render.json）：面积加权顶点法线逐帧更新、原材质/灯光/地面/阴影，body-subdiv=0，azim=72度。输入适配器仅把最终源状态送入原加载接口；输出适配器烧录标注并限制视频码率。没有几何平滑、细分、插帧或重仿真，float32显示转换和共同坐标变换沿用默认工具。C-IPC超过8个组件时只循环默认调色板，组件编号/拓扑不变。地面是显示辅助，不是新增物理接触约束。
- 平滑视频烧录Δt，两版播放器均同步显示当前源帧的Δt、非均匀时的最小–最大值和累计区间时长，完整逐子步数组在`media/libuipc-smooth/<case>/timesteps.json`。数值以秒存储、画面以毫秒显示；优先读取原日志physical_dt_s，旧CC55及D-LAYERS缺该字段时按其封存固定fps×substeps配置计算并标明来源。30FPS×4和60FPS×2都为1/120秒，25FPS×5为1/125秒；CC01_01/CC144_02是预先构造的非均匀人体回放时间轴，不是在线自适应步长控制器。
- 新视频的保存源状态CC/CB为零，不代表连续时间独立数学证明或人体自交为零；粗折、帽子遮脸等原结果外观保留。`media/libuipc/<case>/render.json`记录输入hash、验收证书hash、采样语义与编码检查；`iterations.csv`可独立下载。所有预览文件纳入原media清单。
- 52条VTO动作帧率标记为已验证；8条HOOD validation标为项目设定；24条D-LAYERS（含00396、00756原样本片段）标为播放假定，时长前显示 `≈`。
- 人体页支持训练／测试划分筛选和URL参数 `split=train|test|unassigned`，对应52／12／27条；未纳入本轮的动作保留。服装页不分配训练／测试标签。
- 新增00396、00756的人体片段详情显示原动作编号、源帧范围，并与对应静态服装初值互相链接。人体视频的零betas体型仅供预览，不能当成绑定初值的原人体体型。未打包服装逐帧真值。
- CT 动作类别在精简索引中未提供，显示“未提供”；服装文件名推断类别会明确标注推断来源。
- GLB 仅用于显示，保存 float32 坐标与法线、uint16/uint32 三角面索引。无网格简化、坐标量化或逐部件归一化；OBJ 多边形若存在则按顶点顺序扇形三角化。
- 每个 GLB 导出后读回验证三角面及顶点；误差按来源坐标单位报告，不默认换算为米。
- D-LAYERS 人体和服装放在同一父节点，只应用 binding 中共同的显示坐标变换。切换显隐不重新对齐或更换人体。
- 服装相关碰撞、人体自相交、所选姿态和报告是否重新计算分别展示；不推断缺失的最小距离，也不宣称全动作无穿插。

## 新增数据与预览

1. 将授权整理的数据放入相应来源目录，并更新对应根索引、binding 和科学数据 `manifest.json` 的字节数、SHA-256。不得为了页面修改原科研数组。
2. 在本机生成或复用预览。需要 SMPL 模型时仍在有模型的本机完成，不在 GitHub Actions 下载或上传模型。
3. 将预览存入 `media/<body|cloth|initials>/<source>/<id>/`，更新 `media/manifest.json` 的路径、字节数和哈希。推荐缩略图最大 640×480、WebP，视频 H.264 MP4。历史导入可运行：

```bash
python3 scripts/import_previews.py --source-workspace /absolute/path/to/DATA
```

此可选步骤需要 Pillow，复制视频并从历史图片生成 WebP；DATA 路径仅用于一次性导入，不参与日常构建。

4. 重新构建并检查 `dist/generated/validation.json`，运行浏览器测试。

Task14 高清预览的可选离线再生成：`python scripts/render_task14_hd.py --source /path/to/selected --output web/media/libuipc`，需要numpy、PyVista、Pillow、ffmpeg及DejaVuSans。输出不覆盖已有完整视频；新位置试验更合适。使用固定正交尺度、逐帧更新渲染、CPU Mesa；不在CI重新渲染。随后 `python scripts/register_task14_hd.py --source /path/to/selected --audit /path/to/audit.json`核对公开初值逐点相同、逐帧迭代与原子步日志重聚合相同，再更新预览清单。构建不依赖这些外部输入。

迭代模式沿用历史报表的终止分类：该源帧所有子步达到native_tolerance时标full_newton，其余标mixed_or_semi_implicit。因此D-LAYERS运行即使启用了半隐式策略，也可能在个别源帧达到完整容差。不要把这些个别帧解读为整条运行关闭了半隐式策略。

平滑版再生成使用`python scripts/render_task14_smooth.py --source /path/to/selected --output web/media/libuipc-smooth --renderer /path/to/frozen/ClothLOOP/render.py --evidence /path/to/task/results`（额外需要PyYAML）；然后运行`python scripts/register_task14_smooth.py`，它会先校验原版媒体字节不变再登记新文件。新资源不参与网站构建时的重渲染，CI无需ClothLOOP工作区或PyVista。

## 测试与部署

```bash
cd web
npx playwright install --with-deps --only-shell chromium
npm run build
npm test
```

浏览器测试覆盖真实详情路由、缩略图、视频解码播放、搜索和筛选、10 秒边界、选择导出、3D 控制及显隐、窄屏布局和失败回退。测试证据位于忽略的 `test-results/`；CI 保留 14 天。测试服务器使用 4173 端口，运行测试前停止手工预览服务器。

在无 sudo 的服务器上，可以仅安装浏览器，不使用 `--with-deps`；系统依赖需本来可用。Ubuntu 20.04 的本次测试使用 `PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu22.04-x64` 下载兼容浏览器，已实际验证。渲染使用 SwiftShader，不使用 CUDA。

GitHub 仓库 Settings → Pages → Build and deployment → Source 需设为 **GitHub Actions**。`.github/workflows/pages.yml` 在 main 推送时生成、测试并部署；PR 只构建测试。Actions 使用固定版本提交、npm 锁文件和固定 NumPy 依赖。不会向 Git 提交 dist、GLB 或 node_modules。

预期网站：**https://baiixin.github.io/ClothLOOP-Dataset/**

Pages 首次启用属于仓库设置，需要管理员的 GitHub 登录或对应 API 凭据；SSH agent 的 Git 推送认证不提供这项 API 权限。启用后可在 Actions 手动运行 Dataset Explorer，后续 main 推送自动更新。
