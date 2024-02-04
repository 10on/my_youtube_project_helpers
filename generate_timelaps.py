import cv2
import numpy as np
import os
from glob import glob
from progress.bar import IncrementalBar
import subprocess


def image_difference(imageA, imageB):
    # Вычислить разницу между двумя изображениями
    diff = cv2.absdiff(imageA, imageB)

    # Конвертировать изображение в grayscale
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Бинаризовать изображение (черное - неизмененные области, белое - измененные области)
    _, thresholded = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)

    # Вычислить долю белых пикселей
    white_ratio = np.sum(thresholded == 255) / float(thresholded.size)

    return white_ratio


def sort_images(directory):
    # Получаем список файлов
    files = [f for f in os.listdir(directory) if f.endswith('.jpg') or f.endswith('.JPG')]

    bar = IncrementalBar('Sorting images', max=len(files))

    # Сортируем файлы по дате изменения
    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)))

    # Переименовываем файлы
    for i, file in enumerate(files):
        # Получаем расширение файла

        # Формируем новое имя файла
        new_file = f'{i:04}.jpg'

        # Переименовываем файл
        os.rename(os.path.join(directory, file), os.path.join(directory, new_file))
        bar.next()
    bar.finish()


def delete_duplicates(directory):
    # Получаем список всех .jpg файлов в директории и сортируем его
    files = sorted(glob(os.path.join(directory, '*.jpg')))

    bar = IncrementalBar('Deleting duplicates', max=len(files))

    prev_image = None

    for file in files:
        bar.next()
        # Загружаем изображение
        image = cv2.imread(file)

        if prev_image is not None:
            diff_ratio = image_difference(prev_image, image)

            # Если разница между изображениями меньше порогового значения (например, 0.01), удаляем изображение
            #print(diff_ratio, file)
            if diff_ratio < 0.01:  # Порог можно настроить
                os.remove(file)
                continue

        prev_image = image
    bar.finish()


def delete_hands(directory):
    # Примеры цветовых кодов в формате RGB. Добавьте столько, сколько вам нужно.
    colors = [
        {
            'lower': np.array([112, 141, 206]),  # BGR format
            'upper': np.array([131, 161, 221])  # BGR format
        },
        {
            'lower': np.array([59, 75, 117]),  # BGR format
            'upper': np.array([79, 93, 136])  # BGR format
        }
    ]

    files = sorted(glob(os.path.join(directory, '*.jpg')))

    bar = IncrementalBar('Deleting hands', max=len(files))

    # Проходим через все файлы в директории
    for file in files:
        #print(file)
        # Загружаем изображение
        image = cv2.imread(file)

        for color in colors:
            # Создаем маску для каждого цвета
            mask = cv2.inRange(image, color['lower'], color['upper'])

            # Находим количество пикселей с нужным цветом
            color_pixels = cv2.countNonZero(mask)

            if color_pixels > 5000:
                # Находим общее количество пикселей на изображении
                total_pixels = image.shape[0] * image.shape[1]

                # Вычисляем и выводим процентное соотношение
                color_percentage = (color_pixels / total_pixels) * 100
                #print(f'Color found in {file}. It covers {color_percentage:.2f}% of the image.')
                #print(color_pixels)
                os.remove(file)
                break
        bar.next()
    bar.finish()


def process_ffmpeg(directory):
    # Путь к вашим изображениям
    input_path = f"{directory}/*.jpg"
    # Выходное имя файла видео
    output_file = f"{directory}/../{os.path.basename(os.path.normpath(directory))}.mp4"

    # Составляем команду для FFmpeg
    command = [
        "ffmpeg",
        "-framerate", "60",
        "-pattern_type", "glob",
        "-i", input_path,
        "-pix_fmt", "yuv420p",
        "-c:v", "h264_videotoolbox",
        "-b:v", "100M",
        output_file
    ]

    # Вызываем команду
    subprocess.run(command)

def rotate_images(directory):
    # Получаем список всех .jpg файлов в директории
    files = glob(os.path.join(directory, '*.jpg'))
    bar = IncrementalBar('Rotating images', max=len(files))

    for file in files:
        # Загружаем изображение
        image = cv2.imread(file)

        # Если изображение в портретной ориентации, поворачиваем его
        if image.shape[0] > image.shape[1]:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

            # Сохраняем повернутое изображение
            cv2.imwrite(file, image)
        bar.next()
    bar.finish()


def find_timelapse_folders(path):
    timelapse_folders = []
    for root, dirs, files in os.walk(path):
        for dir in dirs:
            if dir.startswith("timelapse_"):
                timelapse_folders.append(os.path.join(root, dir))
    return timelapse_folders



if __name__ == "__main__":
    directory = input("Введите путь к директории с изображениями: ")
    folders = find_timelapse_folders(directory)

    if folders:
        print('Нашел папки с таймлапсами')
    else:
        print('Не нашел папки с таймлапсами')
        folders.append(directory)

    for directory in folders:
        print('Крутим папку ' + directory)
        sort_images(directory)
        rotate_images(directory)
        delete_hands(directory)

        delete_duplicates(directory)
        process_ffmpeg(directory)
    #ffmpeg -framerate 60 -pattern_type glob -i ' /Users/denispushkarev/Desktop/Видосы/6979/iPhone_13_mini_photo/timelapse_2/*.jpg' -pix_fmt yuv420p -c:v h264_videotoolbox -b:v 100M 13_mini.mp4