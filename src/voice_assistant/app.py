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
    QLineEdit,
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
from .speech import SpeechWorker
from .storage import LocalStore


class SettingsDialog(QDialog):
    def __init__(self, settings: AssistantSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки ассистента")
        self.setMinimumWidth(420)
        self.wake_word_enabled = QCheckBox("Включить голосовую фразу активации")
        self.wake_word_enabled.setChecked(settings.wake_word_enabled)
        self.wake_phrase = QLineEdit(settings.wake_phrase)
        self.speech_mode = QComboBox()
        self.speech_mode.addItem("Локально на этом ПК", SpeechProcessingMode.LOCAL)
        self.speech_mode.addItem("Облачная обработка речи", SpeechProcessingMode.CLOUD)
        self.speech_mode.setCurrentIndex(0 if settings.speech_processing_mode is SpeechProcessingMode.LOCAL else 1)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.speech_mode.currentIndexChanged.connect(self._update_notice)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout()
        form.addRow(self.wake_word_enabled)
        form.addRow("Фраза активации:", self.wake_phrase)
        form.addRow("Обработка речи:", self.speech_mode)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.notice)
        layout.addWidget(buttons)
        self._update_notice()

    def _update_notice(self) -> None:
        if self.speech_mode.currentData() is SpeechProcessingMode.CLOUD:
            self.notice.setText("Голосовые данные будут отправляться внешнему сервису для обработки. Облачный провайдер ещё не настроен, поэтому приложение использует локальный режим.")
        else:
            self.notice.setText("Речь обрабатывается локально на этом ПК.")

    def settings(self) -> AssistantSettings:
        return AssistantSettings(
            wake_word_enabled=self.wake_word_enabled.isChecked(),
            wake_phrase=self.wake_phrase.text().strip() or "ассистент",
            speech_processing_mode=self.speech_mode.currentData(),
        )


class MainWindow(QMainWindow):
    def __init__(self, store: LocalStore) -> None:
        super().__init__()
        self._store = store
        self._settings = store.load_settings()
        self._speech_worker: SpeechWorker | None = None
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
        self.help_label = QLabel("Нажмите «Начать прослушивание». Ассистент ждёт фразу активации и затем одну команду.")
        self.help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_label.setWordWrap(True)
        layout.addWidget(self.help_label)
        controls = QHBoxLayout()
        self.listen_button = QPushButton("Начать прослушивание")
        self.listen_button.clicked.connect(self._toggle_listening)
        controls.addWidget(self.listen_button)
        settings_button = QPushButton("Настройки")
        settings_button.clicked.connect(self._open_settings)
        controls.addWidget(settings_button)
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

    def _update_status(self, message: str | None = None) -> None:
        if message:
            self.status_label.setText(message)
        elif not self._settings.wake_word_enabled:
            self.status_label.setText("Голосовая активация выключена")
        elif self._speech_worker and self._speech_worker.isRunning():
            self.status_label.setText("Ожидание голосовой фразы активации")
        else:
            self.status_label.setText("Прослушивание выключено")
        mode = "Локальная обработка" if self._settings.speech_processing_mode is SpeechProcessingMode.LOCAL else "Облачный режим выбран, локальная обработка используется до настройки провайдера"
        self.statusBar().showMessage(mode)

    def _toggle_listening(self) -> None:
        if self._speech_worker and self._speech_worker.isRunning():
            self._speech_worker.stop()
            self._speech_worker.wait(1500)
            self._speech_worker = None
            self.listen_button.setText("Начать прослушивание")
            self._update_status()
            return
        if not self._settings.wake_word_enabled:
            QMessageBox.information(self, "Голосовая активация", "Включите голосовую активацию в настройках.")
            return
        self._speech_worker = SpeechWorker(self._settings.wake_phrase)
        self._speech_worker.status_changed.connect(self._update_status)
        self._speech_worker.wake_word_detected.connect(self._on_wake_word)
        self._speech_worker.command_recognised.connect(self._on_command)
        self._speech_worker.recognition_error.connect(self._on_recognition_error)
        self._speech_worker.finished.connect(self._on_worker_finished)
        self._speech_worker.start()
        self.listen_button.setText("Остановить прослушивание")
        self._update_status("Запуск локального распознавания речи")

    def _on_wake_word(self) -> None:
        self._update_status("Готов принять голосовую команду")

    def _on_command(self, command: str) -> None:
        entry = self._store.append_history(command, "Команда распознана. Выполнение будет добавлено следующим этапом.")
        self._insert_history(entry.timestamp.strftime("%d.%m.%Y %H:%M:%S"), entry.command, entry.result)

    def _on_recognition_error(self, message: str) -> None:
        self._update_status("Распознавание речи недоступно")
        self.help_label.setText(message)

    def _on_worker_finished(self) -> None:
        if self._speech_worker:
            self.listen_button.setText("Начать прослушивание")

    def _open_settings(self) -> None:
        if self._speech_worker and self._speech_worker.isRunning():
            QMessageBox.information(self, "Настройки", "Остановите прослушивание перед изменением настроек.")
            return
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._settings = dialog.settings()
            self._store.save_settings(self._settings)
            self._update_status()

    def _load_history(self) -> None:
        self.history.setRowCount(0)
        for entry in self._store.load_history():
            self._insert_history(entry.timestamp.strftime("%d.%m.%Y %H:%M:%S"), entry.command, entry.result)

    def _insert_history(self, timestamp: str, command: str, result: str) -> None:
        self.history.insertRow(0)
        for column, value in enumerate((timestamp, command, result)):
            self.history.setItem(0, column, QTableWidgetItem(value))

    def closeEvent(self, event: object) -> None:
        if self._speech_worker and self._speech_worker.isRunning():
            self._speech_worker.stop()
            self._speech_worker.wait(1500)
        event.accept()  # type: ignore[union-attr]


def main() -> int:
    application = QApplication(sys.argv)
    window = MainWindow(LocalStore())
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
