from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import AssistantSettings, SpeechProcessingMode
from .storage import LocalStore


class SettingsDialog(QDialog):
    def __init__(self, settings: AssistantSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки ассистента")
        self.setMinimumWidth(390)

        self.wake_word_enabled = QCheckBox("Включить голосовую фразу активации")
        self.wake_word_enabled.setChecked(settings.wake_word_enabled)
        self.speech_mode = QComboBox()
        self.speech_mode.addItem("Локально на этом ПК", SpeechProcessingMode.LOCAL)
        self.speech_mode.addItem("Облачная обработка речи", SpeechProcessingMode.CLOUD)
        self.speech_mode.setCurrentIndex(0 if settings.speech_processing_mode is SpeechProcessingMode.LOCAL else 1)
        self.notice = QLabel("По умолчанию речь обрабатывается локально.")
        self.notice.setWordWrap(True)
        self.speech_mode.currentIndexChanged.connect(self._update_notice)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow(self.wake_word_enabled)
        form.addRow("Обработка речи:", self.speech_mode)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.notice)
        layout.addWidget(buttons)
        self._update_notice()

    def _update_notice(self) -> None:
        cloud_mode = self.speech_mode.currentData() is SpeechProcessingMode.CLOUD
        self.notice.setText(
            "Голосовые данные будут отправляться внешнему сервису для обработки."
            if cloud_mode
            else "По умолчанию речь обрабатывается локально на этом ПК."
        )

    def settings(self) -> AssistantSettings:
        return AssistantSettings(
            wake_word_enabled=self.wake_word_enabled.isChecked(),
            speech_processing_mode=self.speech_mode.currentData(),
        )


class MainWindow(QMainWindow):
    def __init__(self, store: LocalStore) -> None:
        super().__init__()
        self._store = store
        self._settings = store.load_settings()
        self.setWindowTitle("Голосовой ассистент для Windows")
        self.resize(820, 520)
        self._build_interface()
        self._load_history()
        self._update_status()

    def _build_interface(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 18px; font-weight: 600; padding: 16px;")
        layout.addWidget(self.status_label)

        help_label = QLabel("Ассистент пока готовит голосовой ввод. Настройте режим обработки речи или просмотрите журнал команд.")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        controls = QHBoxLayout()
        settings_button = QPushButton("Настройки")
        settings_button.clicked.connect(self._open_settings)
        controls.addWidget(settings_button)
        test_button = QPushButton("Добавить тестовую запись")
        test_button.clicked.connect(self._add_test_entry)
        controls.addWidget(test_button)
        controls.addStretch()
        layout.addLayout(controls)

        layout.addWidget(QLabel("Журнал команд"))
        self.history = QTableWidget(0, 3)
        self.history.setHorizontalHeaderLabels(["Время", "Команда", "Результат"])
        self.history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.history)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())

    def _update_status(self) -> None:
        if self._settings.wake_word_enabled:
            self.status_label.setText("Ожидание голосовой фразы активации")
            self.statusBar().showMessage("Локальная обработка" if self._settings.speech_processing_mode is SpeechProcessingMode.LOCAL else "Облачная обработка включена")
        else:
            self.status_label.setText("Голосовая активация выключена")
            self.statusBar().showMessage("Включите голосовую активацию в настройках")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._settings = dialog.settings()
            self._store.save_settings(self._settings)
            self._update_status()

    def _load_history(self) -> None:
        self.history.setRowCount(0)
        for entry in reversed(self._store.load_history()):
            self._insert_history(entry.timestamp.strftime("%d.%m.%Y %H:%M:%S"), entry.command, entry.result)

    def _insert_history(self, timestamp: str, command: str, result: str) -> None:
        self.history.insertRow(0)
        for column, value in enumerate((timestamp, command, result)):
            self.history.setItem(0, column, QTableWidgetItem(value))

    def _add_test_entry(self) -> None:
        entry = self._store.append_history("Тестовая команда", "Запись добавлена")
        self._insert_history(entry.timestamp.strftime("%d.%m.%Y %H:%M:%S"), entry.command, entry.result)

    def request_dangerous_action_confirmation(self, action_description: str) -> bool:
        response = QMessageBox.question(
            self,
            "Подтвердите действие",
            f"Подтвердить действие: {action_description}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return response is QMessageBox.StandardButton.Yes


def main() -> int:
    application = QApplication(sys.argv)
    window = MainWindow(LocalStore())
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
