from flask import Flask, render_template, request, url_for, redirect
import easyocr
import google.generativeai as genai
import mysql.connector
import os
import uuid

import config
from config import DB_CONFIG

app = Flask(__name__)

reader = easyocr.Reader(['en', 'ru'])
genai.configure(api_key=config.API)
model = genai.GenerativeModel('gemini-2.5-flash')


@app.route('/',methods =['POST','GET'])
def main():
    translation = None

    if request.method == 'POST':

        file= request.files['image']
        filename = file.filename
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        UPLOAD_FOLDER = 'uploads'
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath= os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)

        photo_path = filepath.replace("\\", "/")


        result = reader.readtext(filepath)
        extracted_text = " ".join([text[1] for text in result])

        target_language = request.form['language']
        response = model.generate_content(f"Переведи на {target_language} следующий текст(в ответ напиши только перевод!): {extracted_text}")
        translation = response.text



        conn=mysql.connector.connect(**DB_CONFIG)
        cursor=conn.cursor()
        cursor.execute('INSERT INTO users (photo_path,lang,text_before,text_after) VALUES (%s,%s,%s,%s)',(photo_path, target_language,extracted_text,translation))
        conn.commit()
        cursor.close()
        conn.close()

    return render_template('main.html', translation=translation)

@app.route('/history', methods=['GET','POST'])
def history():

    conn= mysql.connector.connect(**DB_CONFIG)
    cursor=conn.cursor()
    cursor.execute('SELECT id, lang, text_before, text_after, created_at FROM users ORDER BY created_at DESC')
    translations_table=cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('history.html', translations_table=translations_table)


@app.route('/delete/<int:id>', methods=['POST'])
def delete_translation(id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()


    cursor.execute('SELECT photo_path FROM users WHERE id = %s', (id,))
    result = cursor.fetchone()

    if result:
        photo_path = result[0]

        cursor.execute('DELETE FROM users WHERE id = %s', (id,))
        conn.commit()


        if os.path.exists(photo_path):
            os.remove(photo_path)

    cursor.close()
    conn.close()
    return redirect(url_for('history'))


@app.route('/update_translation/<int:id>', methods=['POST'])
def update_translation(id):
    new_lang = request.form.get('new_lang')

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()


    cursor.execute('SELECT text_before FROM users WHERE id = %s', (id,))
    result = cursor.fetchone()

    if result:
        text_before = result[0]

        response = model.generate_content(
            f"Переведи на {new_lang} следующий текст (в ответ напиши только перевод!): {text_before}"
        )
        new_translation = response.text


        cursor.execute('''
            UPDATE users
            SET lang = %s,
                text_after = %s,
                created_at = NOW()
            WHERE id = %s
        ''', (new_lang, new_translation, id))
        conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('history'))


if __name__ == '__main__':
    app.run(debug=True)