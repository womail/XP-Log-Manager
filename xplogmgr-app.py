"""
XP-Log-Manager - A log file viewer and manager
Version: 0.005

Features:
- Modern, light UI design with custom icon
- View and monitor log files in real-time
- Bookmark frequently accessed log files
- Search within log files
- Archive logs to zip files
- Backup application settings
- Set default log directory
- Analyze logs for error messages
"""

import sys
import os
import json
import zipfile
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QTextEdit, QFileDialog, QCheckBox, QListWidget, QInputDialog,
                             QLabel, QLineEdit, QListWidgetItem, QMessageBox, QStatusBar)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor, QFont

class FileViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_name = "XP-Log-Manager"
        self.version = "0.005"
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(__file__), "appicon.jpg")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
        else:
            print(f"Warning: Icon file not found at {icon_path}")

        self.setWindowTitle(f"{self.app_name} v{self.version}")
        self.setGeometry(100, 100, 1000, 700)

        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"{self.app_name} v{self.version} - Ready")

        # Create central widget and layouts with minimal spacing
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(2)  # Set spacing between left and right panels to 5 pixels
        main_layout.addLayout(top_layout)

        # Create left layout with fixed width
        left_layout = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(400)
        top_layout.addWidget(left_widget)

        right_layout = QVBoxLayout()
        top_layout.addWidget(QWidget(), stretch=1)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        top_layout.addWidget(right_widget)

        # Bookmark list
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemClicked.connect(self.handle_bookmark_click)
        left_layout.addWidget(self.bookmark_list)

        # Buttons for file operations
        button_layout = QHBoxLayout()
        right_layout.addLayout(button_layout)

        select_file_layout = QHBoxLayout()
        button_layout.addLayout(select_file_layout)

        self.select_button = QPushButton(QIcon.fromTheme("document-open"), "Select File")
        self.select_button.clicked.connect(self.select_file)
        select_file_layout.addWidget(self.select_button)

        self.tick_icon = QLabel()
        self.tick_icon.setPixmap(QIcon.fromTheme("document-open").pixmap(16, 16))
        self.tick_icon.setVisible(False)
        select_file_layout.addWidget(self.tick_icon)

        self.reload_button = QPushButton(QIcon.fromTheme("view-refresh"), "Reload")
        self.reload_button.clicked.connect(self.reload_file)
        self.reload_button.setEnabled(False)
        button_layout.addWidget(self.reload_button)

        self.bookmark_button = QPushButton(QIcon.fromTheme("bookmark-new"), "Bookmark")
        self.bookmark_button.clicked.connect(self.add_bookmark)
        self.bookmark_button.setEnabled(False)
        button_layout.addWidget(self.bookmark_button)

        self.archive_button = QPushButton(QIcon.fromTheme("document-save"), "Archive")
        self.archive_button.clicked.connect(self.archive_file)
        self.archive_button.setEnabled(False)
        button_layout.addWidget(self.archive_button)

        self.analyze_button = QPushButton(QIcon.fromTheme("system-search"), "Analyze Errors")
        self.analyze_button.clicked.connect(self.analyze_log)
        self.analyze_button.setEnabled(False)
        button_layout.addWidget(self.analyze_button)

        self.open_zip_button = QPushButton(QIcon.fromTheme("zip"), "Open from Zip")
        self.open_zip_button.clicked.connect(self.open_from_zip)
        button_layout.addWidget(self.open_zip_button)

        self.follow_checkbox = QCheckBox("Follow (Live Tail)")
        self.follow_checkbox.stateChanged.connect(self.toggle_follow)
        button_layout.addWidget(self.follow_checkbox)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        right_layout.addWidget(self.text_display)

        # Search feature (previously Watch feature)
        search_layout = QHBoxLayout()
        main_layout.addLayout(search_layout)

        self.search_input = QLineEdit()
        search_layout.addWidget(QLabel("Search for:"))
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton(QIcon.fromTheme("search"), "Search")
        self.search_button.clicked.connect(self.start_search)
        search_layout.addWidget(self.search_button)

        self.search_display = QTextEdit()
        self.search_display.setReadOnly(True)
        self.search_display.setMaximumHeight(100)
        main_layout.addWidget(self.search_display)

        self.current_file = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_file_content)

        self.watch_word = ""
        self.watch_lines = []

        self.bookmarks = self.load_bookmarks()
        self.update_bookmark_list()

        # Add exit button
        self.exit_button = QPushButton(QIcon.fromTheme("application-exit"), "Exit")
        self.exit_button.clicked.connect(self.close)
        button_layout.addWidget(self.exit_button)

        # Add default log directory field
        log_dir_layout = QHBoxLayout()
        main_layout.addLayout(log_dir_layout)

        self.log_dir_input = QLineEdit()
        log_dir_layout.addWidget(QLabel("Default Log Directory:"))
        log_dir_layout.addWidget(self.log_dir_input)

        self.set_log_dir_button = QPushButton(QIcon.fromTheme("folder"), "Set")
        self.set_log_dir_button.clicked.connect(self.set_log_directory)
        log_dir_layout.addWidget(self.set_log_dir_button)

        self.load_settings()

        # Add backup button
        self.backup_button = QPushButton(QIcon.fromTheme("document-save"), "Backup Settings")
        self.backup_button.clicked.connect(self.backup_settings)
        button_layout.addWidget(self.backup_button)

    def select_file(self):
        default_dir = self.log_dir_input.text() or None
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", default_dir)
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        self.current_file = file_path
        self.reload_file()
        self.reload_button.setEnabled(True)
        self.bookmark_button.setEnabled(True)
        self.archive_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        self.tick_icon.setVisible(True)
        self.status_bar.showMessage(f"Loaded file: {file_path}")

    def reload_file(self):
        if self.current_file:
            with open(self.current_file, 'r') as file:
                content = file.read()
                self.text_display.setText(content)
            self.text_display.verticalScrollBar().setValue(
                self.text_display.verticalScrollBar().maximum()
            )

    def toggle_follow(self, state):
        if state:
            self.timer.start(1000)  # Update every 1 second
        else:
            self.timer.stop()

    def update_file_content(self):
        if self.current_file:
            with open(self.current_file, 'r') as file:
                content = file.read()
                if content != self.text_display.toPlainText():
                    self.text_display.setText(content)
                    self.text_display.verticalScrollBar().setValue(
                        self.text_display.verticalScrollBar().maximum()
                    )
                    self.update_watch_display()

    def load_bookmarks(self):
        try:
            with open('bookmarks.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_bookmarks(self):
        with open('bookmarks.json', 'w') as f:
            json.dump(self.bookmarks, f)

    def update_bookmark_list(self):
        self.bookmark_list.clear()
        for bookmark in self.bookmarks:
            item = QListWidgetItem(bookmark)
            self.bookmark_list.addItem(item)
            
            delete_button = QPushButton(QIcon.fromTheme("edit-delete"), "")
            delete_button.setFixedSize(20, 20)
            delete_button.clicked.connect(lambda _, b=bookmark: self.delete_bookmark(b))
            
            self.bookmark_list.setItemWidget(item, delete_button)

    def delete_bookmark(self, bookmark):
        reply = QMessageBox.question(self, 'Delete Bookmark',
                                     f"Do you want to delete the bookmark:\n{bookmark}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.bookmarks.remove(bookmark)
            self.save_bookmarks()
            self.update_bookmark_list()

    def handle_bookmark_click(self, item):
        bookmark = item.text()
        self.load_bookmark(item)

    def load_bookmark(self, item):
        file_path = item.text()
        if os.path.exists(file_path):
            self.load_file(file_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"The file {file_path} no longer exists.")
            self.bookmarks.remove(file_path)
            self.save_bookmarks()
            self.update_bookmark_list()

    def archive_file(self):
        if self.current_file:
            zip_path, _ = QFileDialog.getSaveFileName(self, "Save Archive", "", "Zip Files (*.zip)")
            if zip_path:
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    zip_file.write(self.current_file, os.path.basename(self.current_file))
                self.status_bar.showMessage(f"File archived to: {zip_path}")

    def open_from_zip(self):
        zip_path, _ = QFileDialog.getOpenFileName(self, "Open Zip File", "", "Zip Files (*.zip)")
        if zip_path:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                file_list = zip_file.namelist()
                file_name, ok = QInputDialog.getItem(self, "Select File", "Choose a file from the archive:", file_list, 0, False)
                if ok and file_name:
                    temp_dir = "temp_extracted"
                    os.makedirs(temp_dir, exist_ok=True)
                    extracted_path = zip_file.extract(file_name, temp_dir)
                    self.load_file(extracted_path)

    def start_search(self):
        self.search_word = self.search_input.text().strip()
        if self.search_word and self.current_file:
            self.update_search_display()

    def update_search_display(self):
        if self.current_file and self.search_word:
            with open(self.current_file, 'r') as file:
                lines = file.readlines()
                self.search_lines = [line.strip() for line in lines if self.search_word in line]
                self.search_lines = self.search_lines[-5:]  # Keep only the last 5 matching lines
                self.search_display.setText("\n".join(self.search_lines))

    def add_bookmark(self):
        if self.current_file:
            if self.current_file not in self.bookmarks:
                self.bookmarks.append(self.current_file)
                self.save_bookmarks()
                self.update_bookmark_list()
            else:
                QMessageBox.information(self, "Bookmark Exists", "This file is already bookmarked.")
        else:
            QMessageBox.warning(self, "No File Selected", "Please select a file before adding a bookmark.")

    def set_log_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Default Log Directory")
        if directory:
            self.log_dir_input.setText(directory)
            self.save_settings()

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.log_dir_input.setText(settings.get('default_log_directory', ''))
        except FileNotFoundError:
            pass

    def save_settings(self):
        settings = {
            'default_log_directory': self.log_dir_input.text()
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f)

    def backup_settings(self):
        current_date = datetime.now().strftime("%Y%m%d")
        default_filename = f"{self.app_name}_backup_{current_date}.zip"
        backup_path, _ = QFileDialog.getSaveFileName(self, "Save Backup", default_filename, "Zip Files (*.zip)")
        if backup_path:
            try:
                with zipfile.ZipFile(backup_path, 'w') as backup_zip:
                    if os.path.exists('settings.json'):
                        backup_zip.write('settings.json')
                    if os.path.exists('bookmarks.json'):
                        backup_zip.write('bookmarks.json')
                QMessageBox.information(self, "Backup Successful", "Settings and bookmarks have been backed up successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Backup Failed", f"An error occurred during backup: {str(e)}")

    def analyze_log(self):
        if self.current_file:
            try:
                with open(self.current_file, 'r') as file:
                    # Create set to store unique error lines
                    error_lines = set()
                    for line in file:
                        if "error" in line.lower():
                            error_lines.add(line.strip())
                    
                    # Display results
                    if error_lines:
                        result = "Found unique error lines:\n\n" + "\n".join(error_lines)
                    else:
                        result = "No error messages found in the log file."
                    
                    self.text_display.setText(result)
                    self.status_bar.showMessage(f"Analysis complete - Found {len(error_lines)} unique error messages")
            except Exception as e:
                QMessageBox.warning(self, "Analysis Failed", f"Failed to analyze log file: {str(e)}")
                self.status_bar.showMessage("Error analysis failed")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon for taskbar
    icon_path = os.path.join(os.path.dirname(__file__), "appicon.jpg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = FileViewerApp()
    window.show()
    sys.exit(app.exec())