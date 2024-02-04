import cv2
import os
import shutil

# Путь к директории, где хранятся видеофайлы
src_directory = input("Введите путь к файлу для перекодирования")

# Путь к директории, куда переместить видеофайлы
dst_directory_120 = f"{src_directory}_120"
dst_directory_240 = f"{src_directory}_240"

# Убедитесь, что директории назначения существуют, в противном случае создайте их
os.makedirs(dst_directory_120, exist_ok=True)
os.makedirs(dst_directory_240, exist_ok=True)

# Обход файлов в src_directory
for file_name in os.listdir(src_directory):
    # Полный путь к файлу
    file_path = os.path.join(src_directory, file_name)

    # Проверка на видеофайл может быть дополнена/изменена под ваш случай
    if file_path.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".flv")):
        # Открываем видеофайл
        cap = cv2.VideoCapture(file_path)

        # Получаем fps
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Освобождаем объект cap
        cap.release()

        # Проверяем fps и перемещаем файл
        if fps > 60:
            if round(fps) == 120:
                shutil.move(file_path, os.path.join(dst_directory_120, file_name))
            elif round(fps) == 240:
                shutil.move(file_path, os.path.join(dst_directory_240, file_name))
