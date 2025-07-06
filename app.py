from flask import Flask, render_template, request, url_for
import easyocr
import google.generativeai as genai
import os
import mysql.connector
from config import DB_CONFIG

API = input("Введите Google API ключ: ")

app = Flask(__name__)

reader = easyocr.Reader(['en', 'ru'])
genai.configure(api_key=API)
model = genai.GenerativeModel('gemini-2.5-flash')


@app.route('/',methods =['POST','GET'])
def main():
    translation = None

    if request.method == 'POST':

        file= request.files['image']
        filename = file.filename
        UPLOAD_FOLDER = 'uploads'
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath= os.path.join(UPLOAD_FOLDER, filename) # os.path.join склеивает в единый путь, с учётом операционной системы
        file.save(filepath)

        photo_path = filepath.replace("\\", "/")  # для Windows


        result = reader.readtext(filepath)
        extracted_text = " ".join([text[1] for text in result])

        target_language = request.form['language']
        response = model.generate_content(f"Переведи на {target_language} следующий текст: {extracted_text}")
        translation = response.text



        conn=mysql.connector.connect(**DB_CONFIG)
        cursor=conn.cursor()
        cursor.execute('INSERT INTO user (photo_path,lang,text_before,text_after) VALUES (%s,%s,%s,%s)',(photo_path, target_language,extracted_text,translation))
        conn.commit()
        cursor.close()
        conn.close()

    return render_template('main.html', translation=translation)


if __name__ == '__main__':
    app.run(debug=True)