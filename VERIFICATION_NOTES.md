# 本地验证记录

验证时间：2026-05-16

## 发现的问题

本地运行 Streamlit 应用后，原始修复只保留了 `header[data-testid="stHeader"]`，但 CSS 仍隐藏了 `[data-testid="stToolbar"]`。在 Streamlit 当前版本中，侧边栏收起后的真实展开按钮为 `button[data-testid="stExpandSidebarButton"]`，它位于工具栏相关区域内。因此，当工具栏被隐藏时，展开按钮会存在于 DOM 中，但宽高为 `0×0`，用户无法点击。

## 已实施的修复

1. 不再隐藏 `[data-testid="stToolbar"]`，确保侧边栏展开按钮的父级区域可见。
2. 明确为 `[data-testid="stExpandSidebarButton"]` 设置 `position: fixed`、`36×36` 尺寸、左上角位置和较高层级，确保收起后始终有可点击入口。
3. 已通过浏览器交互验证：点击左上角展开入口后，侧边栏可从收起状态恢复显示。

## 待完善项

当前因恢复 toolbar 可见，Streamlit 的 `Deploy` 按钮也重新显示。下一步将只隐藏 `Deploy` 类型的 header 按钮，同时保留 `stExpandSidebarButton` 与 `stSidebarCollapseButton`。
