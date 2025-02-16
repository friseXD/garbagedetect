from flask import Flask, render_template, request, redirect, send_file, flash, send_from_directory
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from ultralytics import YOLO
import logging
import ffmpeg
import cv2
import time

app = Flask(__name__)
app.secret_key = "abhinav@METIS"

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

# Создание папки для загрузки файлов
today = datetime.now()
folder_name = today.strftime("%b-%d-%Y-%H-%M-%S")
uploads_dir = os.path.join(app.instance_path, 'uploads', folder_name)
os.makedirs(uploads_dir, exist_ok=True)

# Загрузка модели YOLOv8
model = YOLO("New_best_model.pt")

@app.route("/")
def uploader():
    # Ищем последнюю папку predictX
    detect_folder = "runs/detect"
    if not os.path.exists(detect_folder):
        return render_template("index.html", uploads=[])

    predict_folders = [f for f in os.listdir(detect_folder) if f.startswith("predict")]
    if not predict_folders:
        return render_template("index.html", uploads=[])

    latest_predict_folder = sorted(predict_folders)[-1]  # Последняя папка
    latest_predict_path = os.path.join(detect_folder, latest_predict_folder)

    # Получаем список файлов из папки predictX
    uploads = []
    for file in os.listdir(latest_predict_path):
        if file.endswith(".jpg") or file.endswith(".png") or file.endswith(".jpeg") or file.endswith(".mp4") or file.endswith(".avi"):
            # Сохраняем относительный путь для отображения в HTML
            uploads.append(f"runs/detect/{latest_predict_folder}/{file}")

    return render_template("index.html", uploads=uploads)

@app.route('/runs/detect/<path:filename>')
def serve_detect_files(filename):
    return send_from_directory('runs/detect', filename)

@app.route("/upload", methods=["POST"])
def upload():
    if request.method == "POST":
        files = request.files.getlist('files[]')
        for f in files:
            filename = secure_filename(f.filename)
            file_path = os.path.join(uploads_dir, filename)
            f.save(file_path)

            # Запуск детекции на изображении
            results = model.predict(file_path, save=True)  # YOLO сохраняет результат в `runs/detect/predictX`

            # Получение пути к последней созданной папке
            detect_folder = "runs/detect"
            if not os.path.exists(detect_folder):
                flash(f'Ошибка: папка {detect_folder} не найдена', 'error')
                continue

            # Находим последнюю созданную папку
            predict_folders = [f for f in os.listdir(detect_folder) if f.startswith("predict")]
            if not predict_folders:
                flash(f'Ошибка: папки predict не найдены в {detect_folder}', 'error')
                continue

            latest_predict_folder = sorted(predict_folders)[-1]  # Последняя папка
            latest_predict_path = os.path.join(detect_folder, latest_predict_folder)

            # Поиск обработанного файла в папке
            processed_files = os.listdir(latest_predict_path)
            processed_file = None
            for file in processed_files:
                if file.endswith(".jpg") or file.endswith(".png") or file.endswith(".jpeg"):
                    processed_file = file
                    break

            if processed_file:
                detect_img_path = os.path.join(latest_predict_path, processed_file)
                flash(f'Файл {processed_file} успешно обработан и сохранен в {latest_predict_path}')
            else:
                flash(f'Ошибка: обработанный файл не найден в {latest_predict_path}', 'error')

    return redirect("/")

@app.route("/upload_video", methods=["POST"])
def upload_video():
    if request.method == "POST":
        video_file = request.files['video']
        if video_file:
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(uploads_dir, filename)
            video_file.save(video_path)

            # Конвертация в MP4 (если исходное видео не в MP4)
            mp4_filename = os.path.splitext(filename)[0] + "_converted.mp4"
            mp4_path = os.path.join(uploads_dir, mp4_filename)

            # Удалите существующий файл, если он есть
            if os.path.exists(mp4_path):
                os.remove(mp4_path)

            try:
                ffmpeg.input(video_path).output(mp4_path, vcodec='libx264', acodec='aac').run()
                flash('Видео успешно сконвертировано и обработано')
            except ffmpeg.Error as e:
                flash(f'Ошибка при конвертации видео: {e.stderr}', 'error')
                return redirect("/")

            # Запуск детекции на видео
            results = model.predict(mp4_path, save=True)

            # Получение пути обработанного видео
            detect_folder = "runs/detect"
            predict_folders = [f for f in os.listdir(detect_folder) if f.startswith("predict")]
            if not predict_folders:
                flash(f'Ошибка: папки predict не найдены в {detect_folder}', 'error')
                return redirect("/")

            latest_predict_folder = sorted(predict_folders)[-1]
            latest_predict_path = os.path.join(detect_folder, latest_predict_folder)

            # Поиск обработанного файла в папке
            processed_files = os.listdir(latest_predict_path)
            processed_file = None
            for file in processed_files:
                if file.endswith(".avi"):  # Ищем файл с расширением .avi
                    processed_file = file
                    break

            if processed_file:
                detect_video_path = os.path.join(latest_predict_path, processed_file)
                flash(f'Видео успешно обработано и сохранено в {latest_predict_path}')
            else:
                flash('Ошибка: обработанный файл не найден', 'error')

    return redirect("/")

@app.route("/capture_webcam", methods=["POST"])
def capture_webcam():
    logging.debug("Захват кадров с веб-камеры начат")
    if request.method == "POST":
        # Открываем веб-камеру
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            flash('Ошибка: не удалось открыть веб-камеру', 'error')
            return redirect("/")

        # Создаем папку для сохранения скриншотов
        webcam_dir = os.path.join(uploads_dir, "webcam")
        os.makedirs(webcam_dir, exist_ok=True)
        logging.debug(f"Папка для скриншотов: {webcam_dir}")

        # Захватываем кадры каждые 10 секунд
        try:
            for i in range(3):  # Захватываем 3 кадра
                ret, frame = cap.read()
                if not ret:
                    flash('Ошибка: не удалось захватить кадр', 'error')
                    break

                # Сохраняем кадр
                screenshot_path = os.path.join(webcam_dir, f"frame_{i}.jpg")
                cv2.imwrite(screenshot_path, frame)
                logging.debug(f"Скриншот сохранен: {screenshot_path}")

                # Запуск детекции на изображении
                results = model.predict(screenshot_path, save=True)
                logging.debug(f"Результаты детекции: {results}")

                # Получение пути обработанного изображения
                detect_folder = "runs/detect"
                predict_folders = [f for f in os.listdir(detect_folder) if f.startswith("predict")]
                if not predict_folders:
                    flash(f'Ошибка: папки predict не найдены в {detect_folder}', 'error')
                    continue

                latest_predict_folder = sorted(predict_folders)[-1]
                latest_predict_path = os.path.join(detect_folder, latest_predict_folder)
                logging.debug(f"Последняя папка predict: {latest_predict_path}")

                # Поиск обработанного файла в папке
                processed_files = os.listdir(latest_predict_path)
                processed_file = None
                for file in processed_files:
                    if file.endswith(".jpg") or file.endswith(".png") or file.endswith(".jpeg"):
                        processed_file = file
                        break

                if processed_file:
                    detect_img_path = os.path.join(latest_predict_path, processed_file)
                    flash(f'Кадр {processed_file} успешно обработан и сохранен в {latest_predict_path}')
                    logging.debug(f"Файл сохранен в: {latest_predict_path}")
                else:
                    flash(f'Ошибка: обработанный файл не найден в {latest_predict_path}', 'error')
                    logging.debug(f"Обработанный файл не найден в: {latest_predict_path}")

                time.sleep(10)  # Ждем 10 секунд перед следующим кадром

        finally:
            # Закрываем веб-камеру
            cap.release()
            logging.debug("Захват кадров с веб-камеры завершен")

    return redirect("/")

@app.route('/return-files', methods=['GET'])
def return_file():
    try:
        detect_folder = "runs/detect"
        predict_folders = [f for f in os.listdir(detect_folder) if f.startswith("predict")]
        if not predict_folders:
            return "Ошибка: папки predict не найдены"

        latest_predict_folder = sorted(predict_folders)[-1]
        latest_predict_path = os.path.join(detect_folder, latest_predict_folder)

        processed_files = os.listdir(latest_predict_path)
        if not processed_files:
            return "Ошибка: обработанные файлы не найдены"

        filename = sorted(processed_files)[-1]  # Последний обработанный файл
        path = os.path.join(latest_predict_path, filename)
        return send_file(path)
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run(debug=True)