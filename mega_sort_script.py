import os
import shutil
import json
import subprocess
from PIL import Image
import imageio
from datetime import datetime
import pathlib


def get_creation_time_from_ffprobe(file_path):
    cmd = [
        'ffprobe',
        '-loglevel', 'error',
        '-print_format', 'json',
        '-show_format',
        file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    tags = json.loads(result.stdout).get("format", {}).get("tags", {})
    creation_time = tags.get("creation_time", "")
    return datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ")


def detect_timelapse_sequences(photo_folder):
    timelapse_count = 0  # Счетчик обнаруженных таймлапсов

    for root, _, filenames in os.walk(photo_folder):
        # Фильтрация только фото файлов
        photo_files = [f for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        creation_times = []

        # Получение времени создания для каждого фото
        for photo in photo_files:
            photo_path = os.path.join(root, photo)
            with Image.open(photo_path) as img:
                exif_data = img._getexif()
                if exif_data and 36867 in exif_data:  # 36867 - DateTimeOriginal
                    creation_times.append((photo, datetime.strptime(exif_data[36867], '%Y:%m:%d %H:%M:%S')))

        # Сортировка по времени создания
        creation_times.sort(key=lambda x: x[1])

        # Поиск серий снимков
        sequence_start = 0
        expected_interval = None
        for i in range(1, len(creation_times)):
            delta = (creation_times[i][1] - creation_times[i - 1][1]).seconds

            if expected_interval is None:
                expected_interval = delta

            if abs(delta - expected_interval) <= 1:
                if i - sequence_start + 1 == 100:  # Найдено 100 снимков последовательности
                    timelapse_count += 1
                    timelapse_folder = os.path.join(root, f'timelapse_{timelapse_count}')
                    if not os.path.exists(timelapse_folder):
                        os.makedirs(timelapse_folder)

                    # Перемещаем первые 99 снимков в папку timelapse_N
                    for j in range(sequence_start, i):
                        shutil.move(os.path.join(root, creation_times[j][0]), timelapse_folder)

                if i - sequence_start + 1 >= 100:  # Перемещение всех снимков последовательности начиная с 100
                    shutil.move(os.path.join(root, creation_times[i][0]), timelapse_folder)
            else:
                sequence_start = i
                expected_interval = None


def move_to_subfolder(base_path, subfolder_name, file_path):
    subfolder_path = os.path.join(base_path, subfolder_name)
    if not os.path.exists(subfolder_path):
        os.makedirs(subfolder_path)
    shutil.move(file_path, subfolder_path)


def find_multicam_matches(base_dir):
    video_times = {}

    for foldername, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.lower().endswith(('.mp4', '.mov')):
                file_path = os.path.join(foldername, filename)
                creation_time = get_creation_time_from_ffprobe(file_path)
                if creation_time:
                    video_times[file_path] = creation_time

    # Шаг 1: Создание списка пар файлов
    pairs = []
    for file1, time1 in video_times.items():
        for file2, time2 in video_times.items():
            if os.path.dirname(file1) != os.path.dirname(file2) and abs((time1 - time2).total_seconds()) <= 10:
                pairs.append((file1, file2))

    # Шаг 2: Группировка пар файлов
    groups = []
    for file1, file2 in pairs:
        found = False
        for group in groups:
            if file1 in group or file2 in group:
                group.add(file1)
                group.add(file2)
                found = True
                break
        if not found:
            groups.append(set([file1, file2]))

    # Создание симлинков для файлов в группах
    multicam_folder = os.path.join(base_dir, 'multicams')
    if not os.path.exists(multicam_folder):
        os.makedirs(multicam_folder)

    for index, group in enumerate(groups, start=1):
        group_folder = os.path.join(multicam_folder, f"Group_{index}")
        if not os.path.exists(group_folder):
            os.makedirs(group_folder)

        for file_path in group:
            link_name = os.path.join(group_folder, pathlib.Path(file_path).name)
            os.symlink(file_path, link_name)


def process_files(base_dir):
    for foldername, _, filenames in os.walk(base_dir):
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            
            # Обработка изображений
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.heic')):
                try:
                    if filename.lower().endswith('.heic'):
                        img = Image.fromarray(imageio.imread(file_path))
                    else:
                        img = Image.open(file_path)

                    exif_data = img._getexif()
                    if exif_data and 272 in exif_data:
                        model = exif_data[272].replace(" ", "_").replace("/", "_")
                        model_dir = os.path.join(base_dir, model)
                        model_dir = model_dir + '_photo'
                        if not os.path.exists(model_dir):
                            os.makedirs(model_dir)
                        shutil.move(file_path, model_dir)
                    else:
                        no_exif_dir = os.path.join(base_dir, "Pictures")
                        if not os.path.exists(no_exif_dir):
                            os.makedirs(no_exif_dir)
                        shutil.move(file_path, no_exif_dir)
                except Exception as e:
                    print(f"Error processing image {file_path}: {e}")

            # Обработка mp3
            if filename.lower().endswith('.mp3'):
                try:
                    cmd = [
                        'ffprobe',
                        '-loglevel', 'error',
                        '-print_format', 'json',
                        '-show_format',
                        file_path
                    ]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    audio_data = json.loads(result.stdout)
                    tags = audio_data.get("format", {}).get("tags", {})

                    # Используем тег encoded_by для сортировки
                    encoder = tags.get("encoded_by", "Unknown")
                    encoder_dir = encoder.replace(" ", "_").replace("/", "_")
                    audio_dir = os.path.join(base_dir, encoder_dir + '_audio')

                    if not os.path.exists(audio_dir):
                        os.makedirs(audio_dir)
                    shutil.move(file_path, audio_dir)
                except Exception as e:
                    print(f"Error processing audio {file_path}: {e}")

            # Обработка видео
            if filename.lower().endswith(('.mp4', '.mov')):
                try:
                    cmd = [
                        'ffprobe',
                        '-loglevel', 'error',
                        '-print_format', 'json',
                        '-show_format',
                        '-show_streams',
                        file_path
                    ]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    video_data = json.loads(result.stdout)
                    tags = video_data.get("format", {}).get("tags", {})

                    # Используем модель камеры или кодировщик для сортировки
                    folder_by_tag = tags.get("com.apple.quicktime.model", tags.get("encoder", "Unknown"))
                    folder_by_tag = folder_by_tag.replace(" ", "_").replace("/", "_")
                    folder_by_tag = folder_by_tag + '_video'
                    video_dir = os.path.join(base_dir, folder_by_tag)

                    duration = float(video_data["format"]["duration"])

                    if duration < 60:  # если длительность меньше 60 секунд
                        move_to_subfolder(video_dir, "footage", file_path)
                    else:
                        if not os.path.exists(video_dir):
                            os.makedirs(video_dir)
                        shutil.move(file_path, video_dir)
                except Exception as e:
                    print(f"Error processing video {file_path}: {e}")


if __name__ == "__main__":
    base_directory = input("Введите путь к основной папке: ")
    if os.path.exists(base_directory) and os.path.isdir(base_directory):
        process_files(base_directory)
        find_multicam_matches(base_directory)
        detect_timelapse_sequences(base_directory)
    else:
        print("Ошибка: указанный путь не существует или не является папкой.")

