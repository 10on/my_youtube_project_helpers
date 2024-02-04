import subprocess
import json


def get_video_codec(input_file):
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "v:0", input_file
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        info = json.loads(result.stdout)
        return info['streams'][0]['codec_name']
    except Exception as e:
        print(f"Error getting video codec: {str(e)}")
        return None


def is_videotoolbox_supported():
    try:
        result = subprocess.run(["ffmpeg", "-codecs"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "videotoolbox" in result.stdout
    except Exception as e:
        print(f"Error checking FFmpeg codecs: {str(e)}")
        return False


def encode_video(input_file, input_fps, output_fps):
    try:
        setpts_value = float(output_fps) / float(input_fps)
        atempo_value = float(input_fps) / float(output_fps)
        use_videotoolbox = is_videotoolbox_supported()
        output_file = f"{input_file}_encoded_{output_fps}.mp4"

        # Constructing the atempo filter string
        atempo_str = ""
        while atempo_value < 0.5:
            atempo_str += "atempo=0.5,"
            atempo_value *= 2
        atempo_str += f"atempo={atempo_value}"

        command = [
            "ffmpeg", "-i", input_file,
            "-vf", f"setpts={setpts_value}*PTS",
            "-af", atempo_str,
            "-r", str(output_fps)
        ]

        if use_videotoolbox:
            codec = get_video_codec(input_file)
            if codec == "hevc":
                command.extend(["-c:v", "hevc_videotoolbox"])
            else:
                command.extend(["-c:v", "h264_videotoolbox"])

        command.append(output_file)

        subprocess.run(command, check=True)
        print(f"Video encoded successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error during encoding: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


def main():
    input_file = input("Введите путь к файлу для перекодирования")
    input_fps = 120  # Replace with your input FPS
    output_fps = 60  # Replace with your desired output FPS

    encode_video(input_file, input_fps, output_fps)


if __name__ == "__main__":
    main()
