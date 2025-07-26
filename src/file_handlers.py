def validate_file_type(file_path):
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.mp3', '.wav', '.flac', '.srt', '.ass']
    return any(file_path.endswith(ext) for ext in valid_extensions)

def organize_files(file_paths):
    video_files = []
    audio_files = []
    subtitle_files = []
    
    for file_path in file_paths:
        if validate_file_type(file_path):
            if file_path.endswith(('.mp4', '.mkv', '.avi', '.mov')):
                video_files.append(file_path)
            elif file_path.endswith(('.mp3', '.wav', '.flac')):
                audio_files.append(file_path)
            elif file_path.endswith(('.srt', '.ass')):
                subtitle_files.append(file_path)
    
    return video_files, audio_files, subtitle_files

def handle_drag_and_drop(event):
    file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
    return organize_files(file_paths)