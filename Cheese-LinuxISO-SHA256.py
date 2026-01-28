import sys
import hashlib
import threading
import os
import warnings
# 屏蔽XDG_RUNTIME_DIR无关警告，清理终端输出
warnings.filterwarnings('ignore', category=RuntimeWarning)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QFileDialog, QProgressBar, QMessageBox, QMenuBar,
                             QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTranslator
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette

# 多线程信号类：子线程向主线程传递数据，避免界面卡顿
class HashSignals(QObject):
    progress_update = pyqtSignal(int)  # 进度百分比(0-100)
    hash_result = pyqtSignal(str)      # 本地SHA256计算结果
    error_occur = pyqtSignal(str)      # 错误信息

# 主窗口类：修复报错+原生进度条+主题跟随+极简弹窗+菜单栏（多语言+关于）
class LinuxISO_SHA256_Checker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.iso_path = ""          # ISO文件完整路径
        self.block_size = 65536     # 64KB分块，平衡速度与内存
        self.signals = HashSignals()# 初始化信号
        self.init_signal_connect()  # 连接信号与槽函数
        # 语言状态标识：zh-CN / en-US / es-ES
        self.current_lang = "zh-CN"
        # 初始化菜单栏
        self.init_menu_bar()
        # 初始化界面
        self.init_ui()

    # 信号与槽函数连接
    def init_signal_connect(self):
        self.signals.progress_update.connect(self.update_progress)
        self.signals.hash_result.connect(self.set_local_sha256)
        self.signals.error_occur.connect(self.show_error)

    # 初始化菜单栏：语言切换 + 关于
    def init_menu_bar(self):
        menu_bar = self.menuBar()
        # 1. 语言菜单
        lang_menu = QMenu("语言(&L)", self)
        # 中文选项
        self.zh_action = QAction("简体中文(&C)", self, checkable=True)
        self.zh_action.setChecked(True)
        self.zh_action.triggered.connect(lambda: self.switch_language("zh-CN"))
        # 英文选项
        self.en_action = QAction("English(&E)", self, checkable=True)
        self.en_action.triggered.connect(lambda: self.switch_language("en-US"))
        # 西班牙语选项
        self.es_action = QAction("Español(&S)", self, checkable=True)
        self.es_action.triggered.connect(lambda: self.switch_language("es-ES"))
        # 添加语言选项到语言菜单
        lang_menu.addAction(self.zh_action)
        lang_menu.addAction(self.en_action)
        lang_menu.addAction(self.es_action)
        menu_bar.addMenu(lang_menu)

        # 2. 帮助菜单（包含关于）
        help_menu = QMenu("帮助(&H)", self)
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        menu_bar.addMenu(help_menu)

    # 切换语言：更新所有界面文本
    def switch_language(self, lang):
        if self.current_lang == lang:
            return
        self.current_lang = lang
        # 更新语言选项勾选状态
        self.zh_action.setChecked(lang == "zh-CN")
        self.en_action.setChecked(lang == "en-US")
        self.es_action.setChecked(lang == "es-ES")
        # 更新界面所有文本
        self.update_ui_text()

    # 更新界面文本：根据当前语言切换所有显示内容
    def update_ui_text(self):
        # 文本映射表（更新标题文本）
        text_map = {
            "zh-CN": {
                "window_title": "Cheese的Linux-ISO SHA256校验程序",
                "title_label": "Cheese的Linux-ISO SHA256校验程序",
                "iso_label": "导入Linux ISO文件：",
                "iso_edit_placeholder": "请选择需要校验的ISO镜像文件",
                "iso_btn": "选择ISO文件",
                "calc_btn": "计算ISO本地SHA256",
                "check_btn": "一键比对SHA256值",
                "reset_btn": "重置状态",
                "local_label": "本地ISO SHA256值：",
                "local_edit_placeholder": "计算完成后自动显示",
                "input_label": "待对比SHA256值：",
                "input_edit_placeholder": "请输入官方64位SHA256值",
                "calc_complete_title": "计算完成",
                "calc_complete_msg": "SHA256值计算完成，可输入对比值进行校验。",
                "compare_success_title": "比对成功",
                "compare_success_msg": "SHA256值比对成功！\n本地ISO文件与输入值完全一致，文件完整无篡改。",
                "compare_fail_title": "比对失败",
                "compare_fail_msg": "SHA256值比对失败！\n本地ISO文件与输入值不一致，文件可能损坏、被篡改或输入值错误。",
                "perm_error": "权限不足：请以sudo权限运行程序",
                "calc_error": "计算失败：",
                "menu_lang": "语言(&L)",
                "menu_zh": "简体中文(&C)",
                "menu_en": "English(&E)",
                "menu_es": "Español(&S)",
                "menu_help": "帮助(&H)",
                "menu_about": "关于(&A)",
                "file_dialog_title": "选择Linux ISO文件",
                "error_title": "错误"
            },
            "en-US": {
                "window_title": "Cheese's Linux ISO SHA256 Checksum Verification Tool",
                "title_label": "Cheese's Linux ISO SHA256 Checksum Verification Tool",
                "iso_label": "Import Linux ISO File：",
                "iso_edit_placeholder": "Please select the ISO image file to verify",
                "iso_btn": "Select ISO File",
                "calc_btn": "Calculate Local SHA256",
                "check_btn": "Compare SHA256 Values",
                "reset_btn": "Reset Status",
                "local_label": "Local ISO SHA256 Value：",
                "local_edit_placeholder": "Automatically displayed after calculation",
                "input_label": "SHA256 Value to Compare：",
                "input_edit_placeholder": "Please enter the official 64-bit SHA256 value",
                "calc_complete_title": "Calculation Complete",
                "calc_complete_msg": "SHA256 value calculation completed, you can enter the comparison value for verification.",
                "compare_success_title": "Comparison Successful",
                "compare_success_msg": "SHA256 value comparison successful!\nThe local ISO file is exactly the same as the input value, the file is complete and unmodified.",
                "compare_fail_title": "Comparison Failed",
                "compare_fail_msg": "SHA256 value comparison failed!\nThe local ISO file is inconsistent with the input value, the file may be damaged, tampered with, or the input value is wrong.",
                "perm_error": "Permission denied: Please run the program with sudo privileges",
                "calc_error": "Calculation failed: ",
                "menu_lang": "Language(&L)",
                "menu_zh": "Simplified Chinese(&C)",
                "menu_en": "English(&E)",
                "menu_es": "Español(&S)",
                "menu_help": "Help(&H)",
                "menu_about": "About(&A)",
                "file_dialog_title": "Select Linux ISO File",
                "error_title": "Error"
            },
            "es-ES": {
                "window_title": "Programa de verificación SHA256 de Linux-ISO de Cheese",
                "title_label": "Programa de verificación SHA256 de Linux-ISO de Cheese",
                "iso_label": "Importar archivo ISO de Linux：",
                "iso_edit_placeholder": "Seleccione el archivo de imagen ISO a verificar",
                "iso_btn": "Seleccionar archivo ISO",
                "calc_btn": "Calcular SHA256 local del ISO",
                "check_btn": "Comparar valores SHA256",
                "reset_btn": "Restablecer estado",
                "local_label": "Valor SHA256 local del ISO：",
                "local_edit_placeholder": "Mostrado automáticamente después del cálculo",
                "input_label": "Valor SHA256 a comparar：",
                "input_edit_placeholder": "Ingrese el valor SHA256 oficial de 64 bits",
                "calc_complete_title": "Cálculo completado",
                "calc_complete_msg": "Cálculo del valor SHA256 completado, puede ingresar el valor de comparación para verificar.",
                "compare_success_title": "Comparación exitosa",
                "compare_success_msg": "¡Comparación del valor SHA256 exitosa!\nEl archivo ISO local es exactamente igual al valor ingresado, el archivo está completo y sin alteraciones.",
                "compare_fail_title": "Comparación fallida",
                "compare_fail_msg": "¡Comparación del valor SHA256 fallida!\nEl archivo ISO local no coincide con el valor ingresado, el archivo puede estar dañado, alterado o el valor ingresado es incorrecto.",
                "perm_error": "Permiso denegado: Ejecute el programa con privilegios sudo",
                "calc_error": "Cálculo fallido: ",
                "menu_lang": "Idioma(&L)",
                "menu_zh": "Chino simplificado(&C)",
                "menu_en": "Inglés(&E)",
                "menu_es": "Español(&S)",
                "menu_help": "Ayuda(&H)",
                "menu_about": "Acerca de(&A)",
                "file_dialog_title": "Seleccionar archivo ISO de Linux",
                "error_title": "Error"
            }
        }
        current_text = text_map[self.current_lang]
        
        # 更新窗口标题
        self.setWindowTitle(current_text["window_title"])
        # 更新标题标签
        self.title_label.setText(current_text["title_label"])
        # 更新ISO选择区域
        self.iso_label.setText(current_text["iso_label"])
        self.iso_edit.setPlaceholderText(current_text["iso_edit_placeholder"])
        self.iso_btn.setText(current_text["iso_btn"])
        # 更新按钮文本
        self.calc_btn.setText(current_text["calc_btn"])
        self.check_btn.setText(current_text["check_btn"])
        self.reset_btn.setText(current_text["reset_btn"])
        # 更新SHA256展示区域
        self.local_label.setText(current_text["local_label"])
        self.local_sha256_edit.setPlaceholderText(current_text["local_edit_placeholder"])
        self.input_label.setText(current_text["input_label"])
        self.input_sha256_edit.setPlaceholderText(current_text["input_edit_placeholder"])
        
        # 更新菜单栏文本（重新创建保证显示正确）
        menu_bar = self.menuBar()
        lang_menu = menu_bar.actions()[0].menu()
        help_menu = menu_bar.actions()[1].menu()
        lang_menu.setTitle(current_text["menu_lang"])
        self.zh_action.setText(current_text["menu_zh"])
        self.en_action.setText(current_text["menu_en"])
        self.es_action.setText(current_text["menu_es"])
        help_menu.setTitle(current_text["menu_help"])
        help_menu.actions()[0].setText(current_text["menu_about"])

        # 缓存当前语言文本，用于后续弹窗
        self.text_cache = current_text

    # 界面初始化：原生进度条+主题跟随+极简布局+菜单栏
    def init_ui(self):
        # 窗口基础设置（Linux高DPI适配已在程序入口设置）
        self.setWindowTitle("Cheese的Linux-ISO SHA256校验程序")
        self.setGeometry(300, 300, 850, 400)
        self.setMinimumSize(750, 380)

        # 设置窗口LOGO（标题栏）
        self.set_window_logo()

        # 中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(22)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # LOGO+标题区域（界面顶部）
        logo_title_layout = QHBoxLayout()
        self.logo_label = QLabel()
        self.set_interface_logo()  # 设置界面内LOGO
        logo_title_layout.addWidget(self.logo_label)
        # 工具标题（跟随系统字体/颜色）
        self.title_label = QLabel("Cheese的Linux-ISO SHA256校验程序")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        logo_title_layout.addWidget(self.title_label, stretch=1)
        main_layout.addLayout(logo_title_layout)

        # 字体设置（系统兼容，无硬编码）
        normal_font = QFont()
        normal_font.setPointSize(10)
        label_font = QFont()
        label_font.setPointSize(11)
        label_font.setBold(True)

        # 1. ISO文件选择区域（主题跟随样式）
        iso_layout = QHBoxLayout()
        self.iso_label = QLabel("导入Linux ISO文件：")
        self.iso_label.setFont(label_font)
        self.iso_edit = QLineEdit()
        self.iso_edit.setFont(normal_font)
        self.iso_edit.setReadOnly(True)
        self.iso_edit.setPlaceholderText("请选择需要校验的ISO镜像文件")
        iso_layout.addWidget(self.iso_label)
        iso_layout.addWidget(self.iso_edit, stretch=1)
        # 选择按钮（主题跟随）
        self.iso_btn = QPushButton("选择ISO文件")
        self.iso_btn.setFont(normal_font)
        self.iso_btn.clicked.connect(self.select_iso_file)
        iso_layout.addWidget(self.iso_btn)
        main_layout.addLayout(iso_layout)

        # 2. 进度条区域：改回Linux系统原生样式（仅显示百分比）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("%p%")  # 仅显示百分比数字
        self.progress_bar.setTextVisible(True)  # 显示百分比，原生样式适配
        main_layout.addWidget(self.progress_bar)

        # 3. 操作按钮区域（主题跟随）
        btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("计算ISO本地SHA256")
        self.calc_btn.setFont(normal_font)
        self.calc_btn.clicked.connect(self.calc_local_sha256)
        self.calc_btn.setEnabled(False)
        self.calc_btn.setMinimumWidth(140)

        self.check_btn = QPushButton("一键比对SHA256值")
        self.check_btn.setFont(normal_font)
        self.check_btn.clicked.connect(self.compare_sha256)
        self.check_btn.setEnabled(False)
        self.check_btn.setMinimumWidth(140)

        self.reset_btn = QPushButton("重置状态")
        self.reset_btn.setFont(normal_font)
        self.reset_btn.clicked.connect(self.reset_all_status)
        self.reset_btn.setMinimumWidth(100)

        btn_layout.addWidget(self.calc_btn)
        btn_layout.addWidget(self.check_btn)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.reset_btn)
        main_layout.addLayout(btn_layout)

        # 4. SHA256值展示与输入区域（主题跟随）
        # 本地计算结果（只读）
        local_layout = QHBoxLayout()
        self.local_label = QLabel("本地ISO SHA256值：")
        self.local_label.setFont(label_font)
        self.local_sha256_edit = QLineEdit()
        self.local_sha256_edit.setFont(normal_font)
        self.local_sha256_edit.setReadOnly(True)
        self.local_sha256_edit.setPlaceholderText("计算完成后自动显示")
        local_layout.addWidget(self.local_label)
        local_layout.addWidget(self.local_sha256_edit, stretch=1)
        main_layout.addLayout(local_layout)

        # 待对比值输入（可编辑）
        input_layout = QHBoxLayout()
        self.input_label = QLabel("待对比SHA256值：")
        self.input_label.setFont(label_font)
        self.input_sha256_edit = QLineEdit()
        self.input_sha256_edit.setFont(normal_font)
        self.input_sha256_edit.setPlaceholderText("请输入官方64位SHA256值")
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_sha256_edit, stretch=1)
        main_layout.addLayout(input_layout)

        # 初始化文本缓存
        self.text_cache = {
            "calc_complete_title": "计算完成",
            "calc_complete_msg": "SHA256值计算完成，可输入对比值进行校验。",
            "compare_success_title": "比对成功",
            "compare_success_msg": "SHA256值比对成功！\n本地ISO文件与输入值完全一致，文件完整无篡改。",
            "compare_fail_title": "比对失败",
            "compare_fail_msg": "SHA256值比对失败！\n本地ISO文件与输入值不一致，文件可能损坏、被篡改或输入值错误。",
            "perm_error": "权限不足：请以sudo权限运行程序",
            "calc_error": "计算失败：",
            "file_dialog_title": "选择Linux ISO文件",
            "error_title": "错误"
        }
        # 应用系统主题样式（所有控件统一跟随，无硬编码颜色）
        self.apply_system_theme()

    # 应用系统主题：基于QPalette自动适配浅色/深色模式，兼容所有Linux桌面
    def apply_system_theme(self):
        palette = self.palette()
        # 主按钮样式（跟随系统高亮色，原生体验）
        btn_style = f"""
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                background-color: palette(highlight);
                color: {palette.color(QPalette.HighlightedText).name()};
            }}
            QPushButton:disabled {{
                background-color: palette(mid);
                color: palette(bright_text);
                opacity: 0.7;
            }}
            QPushButton:hover {{
                background-color: palette(dark);
            }}
        """
        # 重置按钮样式（灰色系，区分核心操作，跟随系统）
        reset_btn_style = f"""
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                background-color: palette(mid);
                color: palette(windowText);
            }}
            QPushButton:hover {{
                background-color: palette(dark);
                color: palette(bright_text);
            }}
        """
        # 输入框样式（跟随系统原生配色，只读状态区分）
        line_edit_style = f"""
            QLineEdit {{
                border: 1px solid palette(mid);
                border-radius: 6px;
                padding: 6px 10px;
                background-color: palette(base);
                color: palette(windowText);
                selection-background-color: palette(highlight);
                selection-color: palette(highlightedText);
            }}
            QLineEdit:read-only {{
                background-color: palette(alternate-base);
                opacity: 0.9;
            }}
        """
        # 应用样式到所有控件
        self.iso_btn.setStyleSheet(btn_style)
        self.calc_btn.setStyleSheet(btn_style)
        self.check_btn.setStyleSheet(btn_style)
        self.reset_btn.setStyleSheet(reset_btn_style)
        self.iso_edit.setStyleSheet(line_edit_style)
        self.local_sha256_edit.setStyleSheet(line_edit_style)
        self.input_sha256_edit.setStyleSheet(line_edit_style)

    # 设置窗口标题栏LOGO
    def set_window_logo(self):
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

    # 设置界面内LOGO（64x64，保持比例，透明背景）
    def set_interface_logo(self):
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        self.logo_label.setVisible(os.path.exists(logo_path))

    # 选择ISO文件：无弹窗，仅启用计算按钮
    def select_iso_file(self):
        # 根据当前语言设置文件对话框标题
        dialog_title = self.text_cache.get("file_dialog_title", "选择Linux ISO文件")
        file_path, _ = QFileDialog.getOpenFileName(
            self, dialog_title, "", "ISO Files (*.iso);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            self.iso_path = file_path
            self.iso_edit.setText(file_path)
            self.calc_btn.setEnabled(True)

    # 计算本地SHA256：多线程执行，原生进度条实时更新百分比
    def calc_local_sha256(self):
        if not self.iso_path:
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.calc_btn.setEnabled(False)
        # 启动守护线程，避免界面卡顿
        calc_thread = threading.Thread(
            target=self._calc_sha256_worker,
            args=(self.iso_path,),
            daemon=True
        )
        calc_thread.start()

    # 哈希计算工作线程：分块计算，传递百分比进度
    def _calc_sha256_worker(self, file_path):
        try:
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                file_size = os.fstat(f.fileno()).st_size
                read_size = 0
                while chunk := f.read(self.block_size):
                    sha256.update(chunk)
                    read_size += len(chunk)
                    progress = int((read_size / file_size) * 100)
                    self.signals.progress_update.emit(progress)
            self.signals.hash_result.emit(sha256.hexdigest())
        except PermissionError:
            self.signals.error_occur.emit(self.text_cache["perm_error"])
        except Exception as e:
            self.signals.error_occur.emit(f"{self.text_cache['calc_error']}{str(e)}")

    # 更新进度条：仅刷新百分比，原生样式自动适配
    def update_progress(self, value):
        self.progress_bar.setValue(value)

    # 设置本地SHA256结果：仅弹出「计算完成」核心弹窗
    def set_local_sha256(self, sha256_str):
        self.local_sha256_edit.setText(sha256_str)
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        QMessageBox.information(self, self.text_cache["calc_complete_title"], self.text_cache["calc_complete_msg"])

    # 核心比对：仅弹出「比对成功/失败」弹窗，含64位合法性校验
    def compare_sha256(self):
        local_sha = self.local_sha256_edit.text().strip().lower()
        input_sha = self.input_sha256_edit.text().strip().lower()
        # 合法性校验：非64位/空值直接返回，无弹窗
        if not local_sha or not input_sha or len(input_sha) != 64:
            return
        # 比对结果弹窗（仅此类核心弹窗）
        if local_sha == input_sha:
            QMessageBox.information(self, self.text_cache["compare_success_title"], self.text_cache["compare_success_msg"])
        else:
            QMessageBox.critical(self, self.text_cache["compare_fail_title"], self.text_cache["compare_fail_msg"])

    # 错误提示：计算失败时触发（权限/文件问题）
    def show_error(self, msg):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)
        error_title = self.text_cache.get("error_title", "Error")
        QMessageBox.critical(self, error_title, msg)

    # 重置状态：无弹窗，直接清空所有内容
    def reset_all_status(self):
        self.iso_path = ""
        self.iso_edit.clear()
        self.local_sha256_edit.clear()
        self.input_sha256_edit.clear()
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(False)
        self.check_btn.setEnabled(False)

    # 显示关于弹窗（适配西班牙语）
    def show_about(self):
        # 多语言适配关于弹窗内容
        if self.current_lang == "zh-CN":
            about_title = "关于"
            about_text = f"""Cheese的LinuxISO-SHA256 tools
版本：1.0.0

GitHub 仓库地址：
https://github.com/cfkbd2013/Cheese-LinuxISO_SHA256-tools
"""
        elif self.current_lang == "en-US":
            about_title = "About"
            about_text = f"""Cheese's LinuxISO-SHA256 tools
Version: 1.0.0

GitHub Repository:
https://github.com/cfkbd2013/Cheese-LinuxISO_SHA256-tools
"""
        else:  # es-ES
            about_title = "Acerca de"
            about_text = f"""Herramientas LinuxISO-SHA256 de Cheese
Versión: 1.0.0

Repositorio de GitHub:
https://github.com/cfkbd2013/Cheese-LinuxISO_SHA256-tools
"""
        QMessageBox.about(self, about_title, about_text)

# 程序入口：关键修复（高DPI设置时机、系统样式、环境变量）
if __name__ == "__main__":
    # 1. 修复：高DPI属性必须在QApplication创建前设置（PyQt5强制规范）
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # 2. 创建应用实例，设置系统原生样式
    app = QApplication(sys.argv)
    app.setApplicationName("Linux-ISO-SHA256-Checker")
    app.setStyle("Fusion")  # 统一跨桌面环境样式，保证主题跟随一致性
    
    # 3. 启动窗口
    window = LinuxISO_SHA256_Checker()
    # 初始化界面文本（默认中文）
    window.update_ui_text()
    window.show()
    sys.exit(app.exec_())
