我理解你的需求，你希望优化设置页面，主要包括两个方面：
1.  **配置持久化**：用户修改的设置（特别是 AI 相关的 API Key、Model、Base URL 等）需要保存下来，下次打开软件时自动加载，而不是每次都重置为默认值。
2.  **API Key 安全显示**：API Key 输入框需要增加一个“眼睛”按钮，默认以密码形式（圆点）显示，点击眼睛可以切换明文/密文显示。

### **实施方案**

#### **1. 配置持久化 (`Config` 类增强)**
我们将扩展 `Config` 类，使其具备读写 JSON配置文件的能力。
*   **配置文件路径**: `config.json` (保存在应用目录下或用户目录下)。
*   **加载逻辑**: 应用启动时，`Config` 尝试读取 `config.json`。
*   **保存逻辑**: 当用户在 `SettingsTab` 修改配置时（或者在关闭窗口时），将当前配置保存到 `config.json`。
*   **涉及字段**:
    *   AI 配置: `ai_api_key`, `ai_base_url`, `ai_model`, `ai_batch_size`
    *   代理配置: `proxy_enabled`, `proxy_url`
    *   下载配置: `speed_limit_enabled`, `speed_limit`, `chrome_cookies`
    *   字幕配置: `subtitle_enabled`, `subtitle_lang`, `subtitle_only_langs`

#### **2. SettingsTab 改造**
*   **API Key 眼睛按钮**: 使用 `QLineEdit` 的 `addAction` 功能，在右侧添加一个 `QAction` (图标为眼睛)。
    *   点击事件：切换 `EchoMode` (`Normal` <-> `Password`)。
*   **加载配置**: 在 `initUI` 后，调用 `load_settings` 方法，从 `Config` 读取值并填充到控件中。
*   **保存配置**: 监听控件的 `textChanged` 或 `toggled` 信号，实时更新 `Config` 对象，并触发保存（或者提供一个显式的“保存”按钮，但自动保存体验更好）。考虑到实时保存可能频繁 IO，我们可以选择在 `SettingsTab` 被隐藏或应用关闭时保存，或者简单地在每次修改后保存（JSON 文件很小，影响不大）。

### **执行步骤**

1.  **修改 `config.py`**:
    *   添加 `load_config()` 和 `save_config()` 方法。
    *   定义配置项的默认值和存储结构。

2.  **修改 `settings_tab.py`**:
    *   实现 `load_from_config()`：初始化时从 `Config` 获取值。
    *   实现 `save_to_config()`：控件值变化时更新 `Config`。
    *   实现 API Key 的显示/隐藏切换逻辑。
    *   绑定所有控件的信号到 `save_to_config`。

3.  **修改 `ui.py`**:
    *   在应用启动时确保配置已加载。
    *   在应用关闭时确保配置已保存（作为双重保险）。

准备好开始了吗？