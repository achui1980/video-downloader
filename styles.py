class Styles:
    DARK_THEME = """
    QMainWindow {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QWidget {
        background-color: #2b2b2b;
        color: #ffffff;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 14px;
    }
    QGroupBox {
        border: 1px solid #3d3d3d;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: bold;
        color: #e0e0e0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        background-color: #2b2b2b;
    }
    QLineEdit {
        background-color: #363636;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 5px;
        color: #ffffff;
        selection-background-color: #007acc;
    }
    QLineEdit:focus {
        border: 1px solid #007acc;
    }
    QPushButton {
        background-color: #007acc;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #0098ff;
    }
    QPushButton:pressed {
        background-color: #005c99;
    }
    QPushButton:disabled {
        background-color: #404040;
        color: #808080;
    }
    QProgressBar {
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        text-align: center;
        background-color: #363636;
    }
    QProgressBar::chunk {
        background-color: #007acc;
        border-radius: 3px;
    }
    QComboBox {
        background-color: #363636;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 5px;
        min-width: 6em;
    }
    QComboBox::drop-down {
        border: none;
        background: transparent;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #ffffff;
        margin-right: 5px;
    }
    QTableWidget {
        background-color: #363636;
        border: 1px solid #3d3d3d;
        gridline-color: #2b2b2b;
        selection-background-color: #007acc;
    }
    QHeaderView::section {
        background-color: #252526;
        color: #e0e0e0;
        padding: 5px;
        border: none;
        border-right: 1px solid #3d3d3d;
        border-bottom: 1px solid #3d3d3d;
    }
    QScrollBar:vertical {
        border: none;
        background: #2b2b2b;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #505050;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QTabWidget::pane {
        border: 1px solid #3d3d3d;
        background-color: #2b2b2b;
    }
    QTabBar::tab {
        background-color: #1e1e1e;
        color: #b0b0b0;
        padding: 8px 16px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #2b2b2b;
        color: #ffffff;
        border-bottom: 2px solid #007acc;
    }
    QTabBar::tab:hover {
        background-color: #333333;
    }
    QTextEdit {
        background-color: #363636;
        border: 1px solid #3d3d3d;
        color: #e0e0e0;
    }
    /* Specific styles for Task Widget */
    #TaskWidget {
        background-color: #333333;
        border: 1px solid #3d3d3d;
        border-radius: 6px;
    }
    #TaskTitle {
        font-weight: bold;
        font-size: 15px;
        color: #ffffff;
    }
    #TaskStatus {
        color: #aaaaaa;
        font-size: 12px;
    }
    """
