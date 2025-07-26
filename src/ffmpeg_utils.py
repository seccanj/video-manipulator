def extract_audio(input_file, output_file):
    command = f"ffmpeg -i {input_file} -q:a 0 -map a {output_file}"
    os.system(command)

def extract_video(input_file, output_file):
    command = f"ffmpeg -i {input_file} -c:v copy -an {output_file}"
    os.system(command)

def extract_subtitles(input_file, output_file):
    command = f"ffmpeg -i {input_file} -map 0:s:0 {output_file}"
    os.system(command)

def merge_files(input_files, output_file):
    input_str = ' '.join([f"-i {file}" for file in input_files])
    filter_str = f"[0:v:0]"
    for i in range(1, len(input_files)):
        filter_str += f"[{i}:v:0]"
    filter_str += f"concat=n={len(input_files)}:v=1:a=0[outv];[0:a:0]"
    for i in range(1, len(input_files)):
        filter_str += f"[{i}:a:0]"
    filter_str += f"concat=n={len(input_files)}:v=0:a=1[outa]"
    
    command = f"ffmpeg {input_str} -filter_complex \"{filter_str}\" -map \"[outv]\" -map \"[outa]\" {output_file}"
    os.system(command)