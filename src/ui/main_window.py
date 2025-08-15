from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QStyle, QStyleOptionButton, QMessageBox,
    QApplication, QToolBar, QAction, QFrame, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import os
import logging
import json
import subprocess

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Manipulator")
        self.setGeometry(100, 100, 1000, 700)

        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Create toolbar
        self.create_toolbar()

        # Create main content area
        self.create_main_content()

        # Initialize data structures
        self.expanded_rows = set()  # Track which rows are expanded
        self.file_streams = {}  # Store ffprobe info for each file

        # Enable drag and drop
        self.setAcceptDrops(True)

    def create_toolbar(self):
        """Create the main toolbar with organized action groups"""
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        
        # File Operations Group
        self.toolbar.addSeparator()
        
        # Add File action
        self.add_file_action = QAction("Add Files", self)
        self.add_file_action.setStatusTip("Add video, audio, or subtitle files")
        self.add_file_action.triggered.connect(self.add_file)
        self.toolbar.addAction(self.add_file_action)
        
        # Clear List action
        self.clear_list_action = QAction("Clear List", self)
        self.clear_list_action.setStatusTip("Clear all files from the list")
        self.clear_list_action.triggered.connect(self.clear_list)
        self.toolbar.addAction(self.clear_list_action)
        
        self.toolbar.addSeparator()
        
        # Extract Video action
        self.extract_video_action = QAction("Extract Video", self)
        self.extract_video_action.setStatusTip("Extract selected video streams")
        self.extract_video_action.triggered.connect(self.extract_video)
        self.toolbar.addAction(self.extract_video_action)
        
        # Extract Audio action
        self.extract_audio_action = QAction("Extract Audio", self)
        self.extract_audio_action.setStatusTip("Extract selected audio streams")
        self.extract_audio_action.triggered.connect(self.extract_audio)
        self.toolbar.addAction(self.extract_audio_action)
        
        # Extract Subtitle action
        self.extract_subtitle_action = QAction("Extract Subtitles", self)
        self.extract_subtitle_action.setStatusTip("Extract selected subtitle streams")
        self.extract_subtitle_action.triggered.connect(self.extract_subtitle)
        self.toolbar.addAction(self.extract_subtitle_action)
        
        self.toolbar.addSeparator()
        
        # Merge Files action
        self.merge_action = QAction("Merge Files", self)
        self.merge_action.setStatusTip("Merge selected streams into a new video file")
        self.merge_action.triggered.connect(self.merge_files)
        self.toolbar.addAction(self.merge_action)

    def create_main_content(self):
        """Create the main content area with file table and status"""
        # Create a splitter for potential future expansion
        self.content_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.content_splitter)
        
        # File table area
        self.table_widget = QWidget()
        self.table_layout = QVBoxLayout()
        self.table_widget.setLayout(self.table_layout)
        
        # Table header
        table_header = QLabel("Media Files and Streams")
        table_header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        self.table_layout.addWidget(table_header)
        
        # Main file table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["File Name", "Type", "Format", "Language"])
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.cellClicked.connect(self.toggle_expand_row)
        self.file_table.setAlternatingRowColors(True)
        self.table_layout.addWidget(self.file_table)
        
        # Instructions label
        instructions = QLabel(
            "Workflow: 1) Add files → 2) Extract streams → 3) Add extracted files → 4) Merge into new video"
        )
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        instructions.setWordWrap(True)
        self.table_layout.addWidget(instructions)
        
        self.content_splitter.addWidget(self.table_widget)
        
        # Status area
        self.status_widget = QWidget()
        self.status_layout = QVBoxLayout()
        self.status_widget.setLayout(self.status_layout)
        
        # Status label
        self.status_label = QLabel("Ready to add files")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        self.status_label.setWordWrap(True)
        self.status_layout.addWidget(self.status_label)
        
        self.content_splitter.addWidget(self.status_widget)
        
        # Set splitter proportions (table takes most space)
        self.content_splitter.setSizes([600, 100])

    def add_file(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video/Audio/Subtitle Files",
            "",
            "All Files (*);;Video Files (*.mp4;*.mkv);;Audio Files (*.mp3;*.wav);;Subtitle Files (*.srt;*.ass)",
            options=options
        )
        if files:
            added_count = 0
            for file in files:
                if file not in self.file_streams:
                    self.file_streams[file] = get_media_streams(file)
                    streams = self.file_streams[file]
                    if not streams:
                        continue
                    stream = streams[0]
                    file_type = stream.get("codec_type", "unknown").capitalize()
                    file_format = stream.get("codec_name", "unknown").upper()
                    row = self.file_table.rowCount()
                    self.file_table.insertRow(row)

                    name = os.path.basename(file)
                    main_item = QTableWidgetItem(name)
                    main_item.setData(Qt.UserRole, "main_file")
                    # Make main file rows bold
                    font = main_item.font()
                    font.setBold(True)
                    main_item.setFont(font)

                    # Add caret icon for video files with multiple streams
                    if file_type.lower() == "video" and len(streams) > 1:
                        main_item.setText("▶ " + name)
                        main_item.setData(Qt.UserRole + 2, "expandable")  # Mark as expandable

                    self.file_table.setItem(row, 0, main_item)  # Name column (index 0)
                    self.file_table.setItem(row, 1, QTableWidgetItem(file_type))
                    self.file_table.setItem(row, 2, QTableWidgetItem(file_format))
                    # Add language column for main file (use first stream's language if available)
                    language = stream.get("tags", {}).get("language", "")
                    self.file_table.setItem(row, 3, QTableWidgetItem(language))
                    added_count += 1
            
            if added_count > 0:
                self.status_label.setText(f"Added {added_count} file(s) to the list")
            else:
                self.status_label.setText("No new files were added")

    def toggle_expand_row(self, row, column):
        # Only expand/collapse if clicking on the name column and is a video file
        if column != 0:
            return
        file_type_item = self.file_table.item(row, 1)
        if not file_type_item or file_type_item.text().lower() != "video":
            return

        # Check if this video file is expandable (has multiple streams)
        main_item = self.file_table.item(row, 0)
        if not main_item or main_item.data(Qt.UserRole + 2) != "expandable":
            return

        # Collapse if already expanded
        if row in self.expanded_rows:
            # Remove all expanded stream rows below this video row
            while (row + 1 < self.file_table.rowCount() and
                   self.file_table.item(row + 1, 0) and
                   self.file_table.item(row + 1, 0).data(Qt.UserRole) == "stream"):
                self.file_table.removeRow(row + 1)
            # Change caret to right (collapsed)
            original_text = main_item.data(Qt.UserRole + 1)
            if original_text:
                main_item.setText("▶ " + original_text)
                main_item.setData(Qt.UserRole + 1, original_text)  # Keep stored text
            self.expanded_rows.remove(row)
            return

        # Expand: insert new rows below, one for each stream
        file_name = self._get_original_filename(row)
        input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == file_name), None)
        if input_file is None:
            return

        streams = self.file_streams.get(input_file, [])
        insert_at = row + 1
        for s in streams:
            name = s.get("tags", {}).get("title", f"Stream {s.get('index', '')}")
            stream_type = s.get("codec_type", "unknown").capitalize()
            stream_format = s.get("codec_name", "unknown").upper()
            language = s.get("tags", {}).get("language", "")
            self.file_table.insertRow(insert_at)
            stream_item = QTableWidgetItem(name)
            stream_item.setData(Qt.UserRole, "stream")
            self.file_table.setItem(insert_at, 0, stream_item)           # Name column - index 0
            self.file_table.setItem(insert_at, 1, QTableWidgetItem(stream_type))
            self.file_table.setItem(insert_at, 2, QTableWidgetItem(stream_format))
            self.file_table.setItem(insert_at, 3, QTableWidgetItem(language))
            insert_at += 1

        # Change caret to down (expanded)
        original_text = main_item.data(Qt.UserRole + 1) or file_name
        main_item.setText("▼ " + original_text)
        main_item.setData(Qt.UserRole + 1, original_text)  # Store original text
        self.expanded_rows.add(row)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        added_count = 0
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                if file_path not in self.file_streams:
                    self.file_streams[file_path] = get_media_streams(file_path)
                    streams = self.file_streams[file_path]
                    if not streams:
                        continue
                    stream = streams[0]
                    file_type = stream.get("codec_type", "unknown").capitalize()
                    file_format = stream.get("codec_name", "unknown").upper()
                    row = self.file_table.rowCount()
                    self.file_table.insertRow(row)
                    name_item = QTableWidgetItem(os.path.basename(file_path))
                    # Make main file rows bold
                    font = name_item.font()
                    font.setBold(True)
                    name_item.setFont(font)
                    
                    # Add caret icon for video files with multiple streams
                    if file_type.lower() == "video" and len(streams) > 1:
                        name_item.setText("▶ " + os.path.basename(file_path))
                        name_item.setData(Qt.UserRole + 2, "expandable")  # Mark as expandable
                    
                    self.file_table.setItem(row, 0, name_item)
                    self.file_table.setItem(row, 1, QTableWidgetItem(file_type))
                    self.file_table.setItem(row, 2, QTableWidgetItem(file_format))
                    # Add language column for main file
                    language = stream.get("tags", {}).get("language", "")
                    self.file_table.setItem(row, 3, QTableWidgetItem(language))
                    added_count += 1
        
        if added_count > 0:
            self.status_label.setText(f"Added {added_count} file(s) via drag and drop")
        event.acceptProposedAction()

    def extract_video(self):
        selected_rows = self.file_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No File Selected", "Please select a video stream or file to extract.")
            return

        video_streams_to_extract = []

        for row_index in [row.row() for row in selected_rows]:
            stream_name_item = self.file_table.item(row_index, 0)
            # Check if this is a stream row (expanded)
            if stream_name_item and stream_name_item.data(Qt.UserRole) == "stream":
                print(f"Processing stream row {row_index} with name '{stream_name_item.text()}'")
                # This is a stream row, get the parent video file

                # Find the main file row above this stream row
                parent_row = row_index - 1
                while parent_row >= 0:
                    parent_type_item = self.file_table.item(parent_row, 0)
                    if parent_type_item and parent_type_item.data(Qt.UserRole) == "main_file":
                        break
                    parent_row -= 1
                if parent_row < 0:
                    print(f"Could not find parent main file row for stream row {row_index}")
                    continue
                parent_file_name = self._get_original_filename(parent_row)

                print(f"Found parent main file row {parent_row} with name '{parent_file_name}'")

                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == parent_file_name), None)

                print(f"Input file for stream row: {input_file}")

                if input_file:
                    stream_name = stream_name_item.text()
                    streams = self.file_streams.get(input_file, [])
                    for s in streams:
                        name = s.get("tags", {}).get("title", f"Stream {s.get('index', '')}")
                        if name == stream_name and s.get("codec_type") == "video":
                            video_streams_to_extract.append((input_file, s))
                            break
            else:
                # Main file row (extract first video stream)
                file_name = self._get_original_filename(row_index)
                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == file_name), None)
                if input_file:
                    streams = self.file_streams.get(input_file, [])
                    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                    if video_stream:
                        video_streams_to_extract.append((input_file, video_stream))

        if not video_streams_to_extract:
            QMessageBox.warning(self, "No Video Stream", "No video stream found in the selected rows.")
            return

        for input_file, video_stream in video_streams_to_extract:
            video_index = video_stream.get("index", 0)
            video_codec = video_stream.get("codec_name", "copy")
            ext_map = {"h264": ".mp4", "hevc": ".mkv", "vp9": ".webm", "mpeg4": ".mp4"}
            output_ext = ext_map.get(video_codec, ".mkv")
            base, _ = os.path.splitext(input_file)
            lang = video_stream.get("tags", {}).get("language", "")
            title = video_stream.get("tags", {}).get("title", f"video_{video_index}")
            # Make output file unique per stream
            output_file = f"{base}_video_{video_index}{output_ext}"

            # Overwrite dialog
            if os.path.exists(output_file):
                if not confirm_overwrite_dialog(self, output_file):
                    self.status_label.setText("Extraction cancelled by user.")
                    continue

            self.status_label.setText(f"Extracting video stream {video_index} to {output_file}...")
            QApplication.processEvents()

            # Find type-relative index for video
            rel_index = self._get_type_relative_index(input_file, "video", video_index)

            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-an",  # no audio
                "-map", f"0:v:{rel_index}",
                "-c:v", "copy",
                output_file,
                "-y"
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.status_label.setText(f"Video extracted: {output_file}")
                else:
                    self.status_label.setText("Error extracting video.")
                    log_file = os.path.join(os.path.dirname(input_file), "ffmpeg_error.log")
                    logger = get_logger(log_file)
                    logger.error(f"FFmpeg error extracting video stream {video_index} from {input_file}: {result.stderr}")
                    QMessageBox.critical(self, "FFmpeg Error", f"An error occurred. See log: {log_file}")
            except Exception as e:
                self.status_label.setText("Error extracting video.")
                log_file = os.path.join(os.path.dirname(input_file), "ffmpeg_error.log")
                logger = get_logger(log_file)
                logger.error(f"Exception extracting video stream {video_index} from {input_file}: {str(e)}")
                QMessageBox.critical(self, "Error", f"An error occurred. See log: {log_file}")

    def extract_audio(self):
        selected_rows = self.file_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No File Selected", "Please select an audio stream or file to extract.")
            return

        audio_streams_to_extract = []

        for row_index in [row.row() for row in selected_rows]:
            stream_name_item = self.file_table.item(row_index, 0)
            # Check if this is a stream row (expanded)
            if stream_name_item and stream_name_item.data(Qt.UserRole) == "stream":
                print(f"Processing stream row {row_index} with name '{stream_name_item.text()}'")
                # This is a stream row, get the parent video file

                # Find the main file row above this stream row
                parent_row = row_index - 1
                while parent_row >= 0:
                    parent_type_item = self.file_table.item(parent_row, 0)
                    if parent_type_item and parent_type_item.data(Qt.UserRole) == "main_file":
                        break
                    parent_row -= 1
                if parent_row < 0:
                    print(f"Could not find parent main file row for stream row {row_index}")
                    continue
                parent_file_name = self._get_original_filename(parent_row)

                print(f"Found parent main file row {parent_row} with name '{parent_file_name}'")

                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == parent_file_name), None)

                print(f"Input file for stream row: {input_file}")

                if input_file:
                    stream_name = stream_name_item.text()
                    streams = self.file_streams.get(input_file, [])
                    for s in streams:
                        name = s.get("tags", {}).get("title", f"Stream {s.get('index', '')}")
                        if name == stream_name and s.get("codec_type") == "audio":
                            audio_streams_to_extract.append((input_file, s))
                            break
            else:
                # Main file row (extract first audio stream)
                file_name = self._get_original_filename(row_index)
                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == file_name), None)
                if input_file:
                    streams = self.file_streams.get(input_file, [])
                    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
                    if audio_stream:
                        audio_streams_to_extract.append((input_file, audio_stream))

        if not audio_streams_to_extract:
            QMessageBox.warning(self, "No Audio Stream", "No audio stream found in the selected rows.")
            return

        for input_file, audio_stream in audio_streams_to_extract:
            audio_index = audio_stream.get("index", 0)
            audio_codec = audio_stream.get("codec_name", "aac")
            ext_map = {"aac": ".aac", "mp3": ".mp3", "ac3": ".ac3", "opus": ".opus", "flac": ".flac", "wav": ".wav"}
            output_ext = ext_map.get(audio_codec, ".mka")
            base, _ = os.path.splitext(input_file)
            lang = audio_stream.get("tags", {}).get("language", "")
            title = audio_stream.get("tags", {}).get("title", f"audio_{audio_index}")
            
            # Use language code in filename if available, otherwise use index
            if lang:
                output_file = f"{base}_audio_{lang}{output_ext}"
            else:
                output_file = f"{base}_audio_{audio_index}{output_ext}"

            # Overwrite dialog
            if os.path.exists(output_file):
                if not confirm_overwrite_dialog(self, output_file):
                    self.status_label.setText("Extraction cancelled by user.")
                    continue

            self.status_label.setText(f"Extracting audio stream {audio_index} to {output_file}...")
            QApplication.processEvents()

            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-vn",  # no video
                "-map", f"0:a:{self._get_type_relative_index(input_file, 'audio', audio_index)}",
                "-c:a", "copy",
                output_file,
                "-y"
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.status_label.setText(f"Audio extracted: {output_file}")
                else:
                    self.status_label.setText("Error extracting audio.")
                    log_file = os.path.join(os.path.dirname(input_file), "ffmpeg_error.log")
                    logger = get_logger(log_file)
                    logger.error(f"FFmpeg error extracting audio stream {audio_index} from {input_file}: {result.stderr}")
                    QMessageBox.critical(self, "FFmpeg Error", f"An error occurred. See log: {log_file}")
            except Exception as e:
                self.status_label.setText("Error extracting audio.")
                log_file = os.path.join(os.path.dirname(input_file), "ffmpeg_error.log")
                logger = get_logger(log_file)
                logger.error(f"Exception extracting audio stream {audio_index} from {input_file}: {str(e)}")
                QMessageBox.critical(self, "Error", f"An error occurred. See log: {log_file}")

    def extract_subtitle(self):
        selected_rows = self.file_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No File Selected", "Please select a subtitle stream or file to extract.")
            return

        subtitle_streams_to_extract = []

        for row_index in [row.row() for row in selected_rows]:
            stream_name_item = self.file_table.item(row_index, 0)
            # Check if this is a stream row (expanded)
            if stream_name_item and stream_name_item.data(Qt.UserRole) == "stream":
                print(f"Processing stream row {row_index} with name '{stream_name_item.text()}'")
                # This is a stream row, get the parent video file

                # Find the main file row above this stream row
                parent_row = row_index - 1
                while parent_row >= 0:
                    parent_type_item = self.file_table.item(parent_row, 0)
                    if parent_type_item and parent_type_item.data(Qt.UserRole) == "main_file":
                        break
                    parent_row -= 1
                if parent_row < 0:
                    print(f"Could not find parent main file row for stream row {row_index}")
                    continue
                parent_file_name = self._get_original_filename(parent_row)

                print(f"Found parent main file row {parent_row} with name '{parent_file_name}'")

                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == parent_file_name), None)

                print(f"Input file for stream row: {input_file}")

                if input_file:
                    stream_name = stream_name_item.text()
                    streams = self.file_streams.get(input_file, [])
                    for s in streams:
                        name = s.get("tags", {}).get("title", f"Stream {s.get('index', '')}")
                        if name == stream_name and s.get("codec_type") == "subtitle":
                            subtitle_streams_to_extract.append((input_file, s))
                            break
            else:
                # Main file row (extract all subtitle streams)
                file_name = self._get_original_filename(row_index)
                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == file_name), None)
                if input_file:
                    streams = self.file_streams.get(input_file, [])
                    for s in streams:
                        if s.get("codec_type") == "subtitle":
                            subtitle_streams_to_extract.append((input_file, s))

        if not subtitle_streams_to_extract:
            QMessageBox.warning(self, "No Subtitle Stream", "No subtitle stream found in the selected rows.")
            return

        success_count = 0

        for input_file, subtitle_stream in subtitle_streams_to_extract:
            subtitle_index = subtitle_stream.get("index", 0)
            lang = subtitle_stream.get("tags", {}).get("language", "")
            base, _ = os.path.splitext(input_file)
            
            # Use language code in filename if available, otherwise use index
            if lang:
                output_file = f"{base}_subtitle_{lang}.srt"
            else:
                output_file = f"{base}_subtitle_{subtitle_index}.srt"

            # Overwrite dialog
            if os.path.exists(output_file):
                if not confirm_overwrite_dialog(self, output_file):
                    self.status_label.setText("Extraction cancelled by user.")
                    continue

            self.status_label.setText(f"Extracting subtitle stream {subtitle_index} to {output_file}...")
            QApplication.processEvents()

            # Find type-relative index for subtitle
            rel_index = self._get_type_relative_index(input_file, "subtitle", subtitle_index)

            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-map", f"0:s:{rel_index}",
                "-c:s", "srt",
                output_file,
                "-y"
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    success_count += 1
                else:
                    log_file = os.path.join(os.path.dirname(input_file), "ffmpeg_error.log")
                    logger = get_logger(log_file)
                    logger.error(f"FFmpeg error extracting subtitle stream {subtitle_index} from {input_file}: {result.stderr}")
            except Exception as e:
                log_file = os.path.join(os.path.dirname(input_file), "ffmpeg_error.log")
                logger = get_logger(log_file)
                logger.error(f"Exception extracting subtitle stream {subtitle_index} from {input_file}: {str(e)}")

        if success_count:
            self.status_label.setText(f"Extracted {success_count} subtitle file(s).")
        else:
            self.status_label.setText("No subtitles extracted.")
            QMessageBox.warning(self, "Extraction Failed", "No subtitles could be extracted. See log for details.")

    def merge_files(self):
        selected_rows = self.file_table.selectionModel().selectedRows()
        if len(selected_rows) < 2:
            QMessageBox.warning(self, "Select Files/Streams", "Please select at least a video stream and one audio or subtitle stream to merge.")
            return

        video_file = None
        stream_maps = []
        external_files = []

        for row_index in [row.row() for row in selected_rows]:
            for col in range(self.file_table.columnCount()):
                item = self.file_table.item(row_index, col)
                if item:
                    print(f"Row {row_index} Col {col}: text='{item.text()}', UserRole={item.data(Qt.UserRole)}")
            stream_name_item = self.file_table.item(row_index, 0)
            # Check if this is a stream row (expanded)
            if stream_name_item and stream_name_item.data(Qt.UserRole) == "stream":
                print(f"Processing stream row {row_index} with name '{stream_name_item.text()}'")
                # This is a stream row, get the parent video file

                # Find the main file row above this stream row
                parent_row = row_index - 1
                while parent_row >= 0:
                    parent_type_item = self.file_table.item(parent_row, 0)
                    if parent_type_item and parent_type_item.data(Qt.UserRole) == "main_file":
                        break
                    parent_row -= 1
                if parent_row < 0:
                    print(f"Could not find parent main file row for stream row {row_index}")
                    continue
                parent_file_name = self._get_original_filename(parent_row)

                print(f"Found parent main file row {parent_row} with name '{parent_file_name}'")

                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == parent_file_name), None)

                print(f"Input file for stream row: {input_file}")

                if input_file:
                    stream_name = stream_name_item.text()
                    print(f"Selected stream name/title from expanded row: '{stream_name}'")
                    streams = self.file_streams.get(input_file, [])
                    for s in streams:
                        name = s.get("tags", {}).get("title", f"Stream {s.get('index', '')}")
                        if name == stream_name:
                            stream_type = s.get("codec_type", "unknown")
                            stream_index = s.get("index", 0)
                            print(f"Adding to stream_maps: file={input_file}, type={stream_type}, index={stream_index}, name={name}")
                            stream_maps.append((input_file, stream_type, stream_index))
                            if stream_type == "video" and not video_file:
                                video_file = input_file
                            break
            else:
                # Main file row (external audio/subtitle)
                print(f"Processing main file row {row_index} with name '{stream_name_item.text()}'")

                file_name = self._get_original_filename(row_index)
                input_file = next((f for f in self.file_streams.keys() if os.path.basename(f) == file_name), None)

                print(f"Input file for main row: {input_file}")

                if input_file:
                    file_type = self.file_table.item(row_index, 1).text().lower()

                    print(f"Selected file type: {file_type}")

                    if file_type in ("audio", "subtitle"):
                        external_files.append((input_file, file_type))

        if not video_file:
            QMessageBox.warning(self, "No Video", "At least one video stream must be selected.")
            return

        base, _ = os.path.splitext(video_file)
        output_file = f"{base}_merged.mkv"

        # Check if output file exists
        if os.path.exists(output_file):
            reply = QMessageBox.question(
                self,
                "Overwrite File?",
                f"The file '{output_file}' already exists.\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self.status_label.setText("Merge cancelled by user.")
                return

        # Build ffmpeg input arguments
        input_args = []
        map_args = []
        metadata_args = []
        input_indices = {}
        idx = 0

        # Add video file as input
        input_args += ["-i", video_file]
        input_indices[video_file] = idx
        idx += 1

        # Add external files as inputs
        for ext_file, ext_type in external_files:
            if ext_file not in input_indices:
                input_args += ["-i", ext_file]
                input_indices[ext_file] = idx
                idx += 1

        # Map selected streams from video file, using type-relative index
        for (input_file, stream_type, stream_index) in stream_maps:
            file_idx = input_indices[input_file]
            streams = self.file_streams.get(input_file, [])
            type_key = stream_type.lower()
            # Only streams of the same type
            type_streams = [s for s in streams if s.get("codec_type", "").lower() == type_key]
            # Find the type-relative index
            rel_index = None
            for idx2, s in enumerate(type_streams):
                if s.get("index") == stream_index:
                    rel_index = idx2
                    break
            if rel_index is None:
                print(f"Warning: Could not find type-relative index for {stream_type} stream {stream_index} in {input_file}")
                continue
            # Debug: print mapping
            print(f"Mapping {stream_type} stream: file {input_file}, ffmpeg input {file_idx}, type-relative index {rel_index}")
            if type_key == "video":
                map_args.append(f"-map {file_idx}:v:{rel_index}")
            elif type_key == "audio":
                map_args.append(f"-map {file_idx}:a:{rel_index}")
            elif type_key == "subtitle":
                map_args.append(f"-map {file_idx}:s:{rel_index}")

        # Map all streams from external files
        for ext_file, ext_type in external_files:
            file_idx = input_indices[ext_file]
            if ext_type == "audio":
                map_args.append(f"-map {file_idx}:a:0")
            elif ext_type == "subtitle":
                map_args.append(f"-map {file_idx}:s:0")

        # Add language metadata for subtitle streams if available
        sub_idx = 0
        for (input_file, stream_type, stream_index) in stream_maps:
            if stream_type == "subtitle":
                streams = self.file_streams.get(input_file, [])
                s = next((s for s in streams if s.get("index") == stream_index), {})

                tags = s.get("tags", {})

                if not tags:
                    print(f"Warning: No tags found for subtitle stream {stream_index} in {input_file}, using 'und'")
                    lang = "und"
                else:
                    lang = tags.get("language", "und")

                print(f"Adding metadata for subtitle stream {stream_index} in {input_file}: language={lang}")

                metadata_args += [f"-metadata:s:s:{sub_idx}", f"language={lang}"]
                sub_idx += 1

        for ext_file, ext_type in external_files:
            if ext_type == "subtitle":
                streams = self.file_streams.get(ext_file, [])
                lang = "und"
                if streams and "tags" in streams[0] and "language" in streams[0]["tags"]:
                    lang = streams[0]["tags"]["language"]
                else:
                    print(f"Warning: No language tag found for subtitle file {ext_file}, using 'und'")

                print(f"Adding metadata for subtitle file {stream_index} in {input_file}: language={lang}")

                metadata_args += [f"-metadata:s:s:{sub_idx}", f"language={lang}"]
                sub_idx += 1

        # Output command
        cmd = ["ffmpeg"]
        cmd += input_args
        for m in map_args:
            cmd += m.split()
        cmd += metadata_args
        cmd += ["-c", "copy", output_file, "-y"]

        self.status_label.setText(f"Merging to {output_file}...")
        QApplication.processEvents()  # Ensure UI updates before starting the process

        try:
            print(f"Running command: {' '.join(cmd)}")  # Debug: print the full command
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.status_label.setText(f"Merged file created: {output_file}")
            else:
                self.status_label.setText("Error merging files.")
                log_file = os.path.join(os.path.dirname(video_file), "ffmpeg_error.log")
                logger = get_logger(log_file)
                logger.error(f"FFmpeg error merging files: {result.stderr}")
                QMessageBox.critical(self, "FFmpeg Error", f"An error occurred. See log: {log_file}")
        except Exception as e:
            self.status_label.setText("Error merging files.")
            log_file = os.path.join(os.path.dirname(video_file), "ffmpeg_error.log")
            logger = get_logger(log_file)
            logger.error(f"Exception merging files: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred. See log: {log_file}")

    def clear_list(self):
        self.file_table.setRowCount(0)
        self.file_streams.clear()
        self.expanded_rows.clear()
        self.status_label.setText("File list cleared. Ready to add new files.")

    def _get_original_filename(self, row):
        """Helper to get the original filename from a table row, removing any expand indicators"""
        item = self.file_table.item(row, 0)
        if not item:
            return ""
        filename = item.data(Qt.UserRole + 1) or item.text()
        # Remove "▼ " or "▶ " prefix if present
        if filename.startswith("▼ ") or filename.startswith("▶ "):
            filename = filename[2:]
        return filename

    def _get_type_relative_index(self, input_file, stream_type, global_index):
        """Helper to get the type-relative index for a stream (e.g. 0 for first audio, 1 for second, etc.)"""
        streams = self.file_streams.get(input_file, [])
        type_streams = [s for s in streams if s.get("codec_type", "").lower() == stream_type.lower()]
        for idx, s in enumerate(type_streams):
            if s.get("index") == global_index:
                return idx
        return None

def confirm_overwrite_dialog(parent, output_file):
    reply = QMessageBox.question(
        parent,
        "Overwrite File?",
        f"The file '{output_file}' already exists.\nDo you want to overwrite it?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    return reply == QMessageBox.Yes

def get_logger(log_path):
    logger = logging.getLogger(log_path)
    if not logger.handlers:
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def get_media_streams(file_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=index,codec_type,codec_name:stream_tags=language,title",
        "-of", "json",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        # Log ffprobe output for debugging
        print(f"ffprobe info for {file_path}:\n{json.dumps(info, indent=2)}")
        return info.get("streams", [])
    except Exception as e:
        log_file = os.path.join(os.path.dirname(file_path), "ffmpeg_error.log")
        logger = get_logger(log_file)
        logger.error(f"Error probing file {file_path}: {str(e)}")
        return []

# Example usage in add_file or when a file is selected:
# streams = get_media_streams(selected_file)
# for stream in streams:
#     print(stream["index"], stream["codec_type"], stream["codec_name"])
