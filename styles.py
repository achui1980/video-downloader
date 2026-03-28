class Styles:
    # 基于 design_concept.html 的配色方案
    DARK_THEME = """
    /* 全局变量模拟 */
    /* bg-dark: #1e1e1e */
    /* bg-sidebar: #252526 */
    /* bg-card: #2d2d30 */
    /* bg-input: #3c3c3c */
    /* text-primary: #cccccc */
    /* accent: #007acc */
    
    QMainWindow, QWidget#MainContent {
        background-color: #1e1e1e;
        color: #cccccc;
    }
    
    QWidget {
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 14px;
        color: #cccccc;
    }

    /* 侧边栏样式 */
    QWidget#Sidebar {
        background-color: #252526;
        border-right: 1px solid #3e3e42;
    }
    
    /* 侧边栏按钮 */
    QToolButton.SidebarBtn {
        background-color: transparent;
        border: none;
        color: #858585;
        text-align: left;
        padding: 12px 20px;
        font-size: 14px;
    }
    
    QToolButton.SidebarBtn:hover {
        background-color: #2a2d2e;
        color: #cccccc;
    }
    
    QToolButton.SidebarBtn:checked {
        background-color: #37373d;
        color: #ffffff;
        border-left: 3px solid #007acc;
    }
    
    /* 标题栏 */
    QLabel#PageTitle {
        font-size: 20px;
        font-weight: 500;
        color: #ffffff;
        padding: 15px 0 20px 0;
    }
    
    /* 卡片样式 */
    QFrame.Card {
        background-color: #2d2d30;
        border-radius: 8px;
        border: 1px solid #3e3e42;
    }
    
    /* 输入框 */
    QLineEdit {
        background-color: #3c3c3c;
        border: 1px solid #3e3e42;
        border-radius: 4px;
        padding: 10px;
        color: #ffffff;
        font-size: 14px;
    }
    
    QLineEdit:focus {
        border: 1px solid #007acc;
    }
    
    /* 按钮 */
    QPushButton {
        background-color: #3c3c3c;
        color: #cccccc;
        border: 1px solid #3e3e42;
        border-radius: 4px;
        padding: 8px 16px;
    }
    
    QPushButton:hover {
        background-color: #454545;
    }
    
    QPushButton.PrimaryBtn {
        background-color: #007acc;
        color: white;
        border: none;
        font-weight: 600;
        font-size: 15px;
        padding: 10px 24px;
    }
    
    QPushButton.PrimaryBtn:hover {
        background-color: #0098ff;
    }
    
    QPushButton.PrimaryBtn:pressed {
        background-color: #005c99;
    }

    /* 下拉框 */
    QComboBox {
        background-color: #3c3c3c;
        border: 1px solid #3e3e42;
        border-radius: 4px;
        padding: 8px;
        color: #cccccc;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    
    QComboBox::down-arrow {
        image: none;
        border: none;
    }

    /* 分组标题 */
    QLabel.SectionTitle {
        font-size: 14px;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 8px;
    }
    
    /* 滚动条 */
    QScrollBar:vertical {
        border: none;
        background: #1e1e1e;
        width: 10px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background: #424242;
        min-height: 20px;
        border-radius: 5px;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    /* 表格 */
    QTableWidget {
        background-color: #2d2d30;
        border: 1px solid #3e3e42;
        gridline-color: #3e3e42;
        color: #cccccc;
    }
    
    QHeaderView::section {
        background-color: #252526;
        color: #cccccc;
        padding: 8px;
        border: none;
        border-bottom: 1px solid #3e3e42;
    }

    /* Task Widget */
    #TaskWidget {
        background-color: #333333;
        border: 1px solid #3e3e42;
        border-radius: 6px;
    }
    """
