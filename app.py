from flask import Flask, render_template, request, redirect, url_for, jsonify
import easyocr
import google.generativeai as genai
import os
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Инициализация EasyOCR и Gemini
reader = easyocr.Reader(['en', 'ru'])
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/', methods=['GET', 'POST'])
def main():
    translation = None
    history = []

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, photo_path, original_text, translated_text, date FROM translations ORDER BY date DESC LIMIT 10")
            history = cursor.fetchall()
    except Exception as e:
        print("Ошибка при получении истории:", e)
    finally:
        if connection:
            connection.close()

    if request.method == 'POST':
        if 'image' not in request.files:
            return redirect(request.url)

        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)

        UPLOAD_FOLDER = 'uploads'
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        result = reader.readtext(filepath)
        extracted_text = " ".join([text[1] for text in result])

        target_language = request.form['language']
        response = model.generate_content(
            f"Переведи на {target_language} следующий текст: \n{extracted_text}\n"
            "Выведи только переведенный текст без дополнительных комментариев"
        )
        translation = response.text

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO translations 
                (photo_path, original_text, translated_text) 
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (filepath, extracted_text, translation))
            connection.commit()
        except Exception as e:
            print("Ошибка при сохранении в БД:", e)
        finally:
            if connection:
                connection.close()

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, photo_path, original_text, translated_text, date FROM translations ORDER BY date DESC LIMIT 10")
                history = cursor.fetchall()
        except Exception as e:
            print("Ошибка при обновлении истории:", e)
        finally:
            if connection:
                connection.close()

    return render_template('main.html', 
                         translation=translation,
                         history=history)

@app.route('/history/<int:translation_id>')
def translation_detail(translation_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM translations WHERE id = %s", (translation_id,))
            translation = cursor.fetchone()
            
            if not translation:
                return "Перевод не найден", 404
                
            return render_template('translation_detail.html', translation=translation)
    except Exception as e:
        print(f"Ошибка при получении перевода {translation_id}:", e)
        return "Произошла ошибка", 500
    finally:
        if connection:
            connection.close()

if __name__ == '__main__':
    app.run(debug=True)