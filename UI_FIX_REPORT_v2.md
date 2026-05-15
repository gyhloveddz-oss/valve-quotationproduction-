# 成宁阀芯报价工作台 UI 修复说明 v2

本次修复基于当前 Streamlit Cloud 生产版发布包完成，核心修改文件为 `app.py`。修复目标是解决工作台两列布局挤压、报价面板右侧粘性不足、报价金额右对齐、产品卡片下方出现“选择”按钮、数量输入可编辑性检查，以及深色界面文字对比度与圆角一致性问题。

## 修复概览

| 问题编号 | 原问题 | 本次处理结果 |
|---|---|---|
| Bug 1 | 工作台仍为左右两列，右侧报价面板容易挤压产品区。 | 已改为 `st.columns([1, 2.5, 1.2])` 三段式结构：左侧系列导航、中间产品卡片、右侧报价面板。 |
| Bug 2 | 上传控件或按钮图标可能出现乱码。 | 已确认 `file_uploader` 使用 `label_visibility="collapsed"`；代码中未发现 `arrow_right` 写法。 |
| Bug 3 | 报价大卡片金额和 RMB 文本右对齐，不符合要求。 | 已将 `ph-label`、`ph-currency`、`ph-amount`、`ph-rmb`、`ph-sub` 改为左对齐，并对金额区增加 `padding-left:15px`。 |
| Bug 4 | 产品卡片下方出现单独“选择”按钮。 | 已移除产品卡片下方按钮，改为整张产品卡片点击选中。 |
| Bug 5 | 数量输入需要保留 100 快捷步进，同时允许手动输入任意数字。 | 已保留 `step=100`，同时确认 CSS 中没有 `pointer-events:none` 或其他阻止手动输入的样式。 |
| Bug 6 | 深色模式文字对比度和圆角不够统一。 | 已提高 muted/subtle 文本颜色亮度，引入统一圆角变量 `--radius-card` 与 `--radius-control`，主要卡片保持 16px 圆角。 |

## 关键技术改动

本次把主工作台改为明确的三段式列结构，左侧只负责系列导航，中间负责产品选择与报价参数，右侧负责报价结果。右侧报价面板通过 `quote-column-marker` 让所在垂直容器保持 `position: sticky`，避免报价卡片跟随页面滚动丢失。

产品卡片的选择方式从 Streamlit 按钮改为 URL 查询参数驱动的整卡点击。点击产品卡片后，链接会写入 `cat` 与 `prod` 参数，应用加载时通过 `sync_selection_from_query()` 同步到 `st.session_state`，从而既实现整卡点击，又避免显示额外的“选择”按钮。

## 验证结果

| 验证项 | 结果 |
|---|---|
| `python3.11 -m py_compile app.py config.py fetcher.py` | 通过 |
| 产品表 `data/products.xlsx` 必要列检查 | 通过 |
| 产品数据行数 | 25 行 |
| 产品图片数量 | 25 张 |
| 本地 Streamlit 健康检查 `/_stcore/health` | 返回 `ok` |
| 发布包生成 | `/home/ubuntu/valve_quotation_streamlit_production_v2.zip` |

## 零代码替换上传步骤

请下载本次交付的 `valve_quotation_streamlit_production_v2.zip`，解压后进入里面的 `valve_quotation_streamlit_production` 文件夹。你可以把其中所有文件上传并覆盖到 GitHub 仓库 `gyhloveddz-oss/valve-quotationproduction`，尤其要确保新的 `app.py` 覆盖旧版本。

在 GitHub 网页端操作时，建议选择仓库首页的 **Add file → Upload files**，然后把解压后的文件和文件夹拖进去。上传时请确认 `data/products.xlsx` 和 `data/images/` 目录仍然存在。提交说明可以填写：`fix: update three-column layout and product card interaction`。

提交完成后，Streamlit Cloud 通常会自动重新部署。如果页面没有自动更新，可以进入 Streamlit Cloud 对应应用，点击重新启动或手动 Reboot。更新后重点检查三处：工作台是否变为左中右三段、点击产品图片卡片是否直接选中、右侧报价卡片是否左对齐并保持粘性显示。
