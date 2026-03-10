from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
# from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import datetime
import csv
import calendar
from random import choice

app = Flask(__name__)
app.secret_key = secret_key = os.urandom(32).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SCHEDULE_FOLDER'] = 'schedules'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}

db: SQLAlchemy = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    fio = db.Column(db.String(120), nullable=False)
    class_ = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'admin', 'student', 'leader'
    is_graduate = db.Column(db.Boolean, default=False)
    center_name = db.Column(db.String(100))  # только для role='leader'


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, default=datetime.datetime.now())


class SupportChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)
    last_message_time = db.Column(db.DateTime)
    unread_count = db.Column(db.Integer, default=0)
    user = db.relationship('User', foreign_keys=[user_id])
    admin = db.relationship('User', foreign_keys=[admin_id])


class SupportMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('support_chat.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now())
    is_read = db.Column(db.Boolean, default=False)
    chat = db.relationship('SupportChat', backref='messages')
    sender = db.relationship('User')


class CenterLeader(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    center_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text)
    email = db.Column(db.String(100))
    photo = db.Column(db.String(100))


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    publish_date = db.Column(db.DateTime, default=datetime.datetime.now())
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User')


class Center(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    info = db.Column(db.String(200), nullable=False)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10))
    description = db.Column(db.Text)
    organizer = db.Column(db.String(150))
    responsible_leader = db.Column(db.String(150))
    center = db.Column(db.String(100))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User')
    registrations = db.relationship('EventRegistration', backref='event', cascade='all, delete-orphan')


class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_confirmed = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='viewer')
    user = db.relationship('User')


class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    # Роли: 'viewer' (1 балл), 'volunteer' (3 балла), 'participant' (5 баллов)
    role = db.Column(db.String(20), default='viewer')
    user = db.relationship('User', backref='registrations')


with app.app_context():
    db.create_all()

    # Миграция: добавляем новые столбцы если их нет (для существующих БД)
    with db.engine.connect() as conn:
        existing_cols = [row[1] for row in conn.execute(db.text("PRAGMA table_info(user)")).fetchall()]
        if 'center_name' not in existing_cols:
            conn.execute(db.text("ALTER TABLE user ADD COLUMN center_name VARCHAR(100)"))
            conn.commit()

        event_table = conn.execute(
            db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='event'")).fetchone()
        if not event_table:
            pass  # create_all уже создал таблицу выше

    if not User.query.first():
        admin = User(
            username='admin',
            password='admin123',
            fio='Администратор Системы',
            class_='Администрация',
            role='admin'
        )
        db.session.add(admin)

        student = User(
            username='student1',
            password='password123',
            fio='Иванов Иван Иванович',
            class_='10А'
        )
        db.session.add(student)

        db.session.add(Achievement(
            user_id=2,
            title='Победитель олимпиады по математике'
        ))

        centers_data = [
            {
                'center_name': 'IT',
                'role': 'leader',
                'name': 'Чадаев Матвей Александрович',
                'position': 'Руководитель IT-центра',
                'bio': 'Ну короче это я',
                'email': 'matveyka.chadaev@gmail.com',
                'photo': 'Chadaev_Matvey.jpg'
            },
            {
                'center_name': 'IT',
                'role': 'deputy',
                'name': 'Ахмадуллин Аяз Кто-тотамович',
                'position': 'Заместитель руководителя IT-центра',
                'bio': 'Вообще крутой пацанчик',
                'email': 'Ayaz@gmail.com',
                'photo': ''
            },
            {
                'center_name': 'Патриотического воспитания',
                'role': 'leader',
                'name': 'Захаров Данила',
                'position': 'Руководитель Центра патриотического воспитания',
                'bio': 'Состоит в юнармии',
                'email': 'mail@gmail.com',
                'photo': ''
            },
        ]

        for data in centers_data:
            db.session.add(CenterLeader(**data))

        centers = [
            {
                "name": "IT",
                "info": '''С этого года у нас появился новый IT-центр, и я являюсь его руководителем. 

Мы запускаем амбициозный проект — создание приложения для гимназии, которое значительно упростит учебный процесс для учеников, учителей и родителей.

В приложении будут реализованы такие важные функции, как:  
1) Просмотр расписания уроков;  
2) Новости гимназии, школьная газета и календарь событий;  
3) Информация о гимназии: профильные классы, питание, ученическое самоуправление;  
4) Просмотр личных достижений.

Уверен, что это приложение сделает учебу удобнее и эффективнее для всех.

Призываю участников IT-центра активно делиться своими идеями! Вместе мы сможем достичь больших результатов!'''
            },
            {
                "name": "Патриотического воспитания",
                "info": '''Всем привет!  
Меня зовут Данила, и я новый руководитель Центра патриотического воспитания. Также я являюсь активным участником отряда Юнармии нашей гимназии

Уверен, что мы непременно сдружимся, ведь любить свою страну, гордиться её достижениями и беречь её традиции — это важная часть воспитания каждого гражданина. Пусть ваше стремление к знаниям и уважение к родной земле укрепляют ваш патриотический дух и помогают строить будущее нашей великой страны! 🇷🇺

Этот учебный год обещает быть очень насыщенным: начиная от участия в различных акциях, сотрудничества с Волонтёрами Победы, и заканчивая созданием музея Боевой славы на базе нашей гимназии.

Надеюсь на вашу активность! Удачи всем в новом учебном году! 💪'''
            }
        ]

        for center in centers:
            db.session.add(Center(**center))

        db.session.commit()


def generate_key(length):
    result = ""
    alphabet = "qwertyuiopasdfghjklzxcvbnm1234567890"

    for _ in range(length):
        result += choice(alphabet)

    return result


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_schedule_filename(class_name):
    translit = {
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }

    filename = ''.join([translit.get(c, c) for c in class_name])
    return f"schedule_{filename}.csv"


def load_schedule(class_name):
    filename = get_schedule_filename(class_name)
    filepath = os.path.join(app.config['SCHEDULE_FOLDER'], filename)
    print(f"Ищем расписание по пути: {filepath}")

    schedule = {}
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    day = row[0].strip()
                    lessons = [lesson.strip() for lesson in row[1:]]
                    schedule[day] = lessons
    except FileNotFoundError:
        print(f"Файл не найден: {filepath}")
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")

    return schedule


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username
            session['logged_in'] = True
            session['role'] = user.role
            if user.role == 'leader':
                session['center_name'] = user.center_name
            flash('Вы успешно вошли в систему', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    achievements = Achievement.query.filter_by(user_id=user.id).all()

    return render_template('profile.html',
                           fio=user.fio,
                           class_=user.class_,
                           achievements=[a.title for a in achievements])


@app.route('/centers')
def centers():
    # centers = db.session.query(CenterLeader).distinct().all()
    # centers = [c[0] for c in centers]

    # selected_center = request.args.get('center', centers[0] if centers else None)

    centers = db.session.query(Center).all()
    selected_center = request.args.get('center', centers[0].name if centers else None)
    selected_center = Center.query.filter_by(name=selected_center).first()

    leaders = {}
    if selected_center:
        leaders['leader'] = CenterLeader.query.filter_by(
            center_name=selected_center.name,
            role='leader'
        ).first()

        leaders['deputies'] = CenterLeader.query.filter_by(
            center_name=selected_center.name,
            role='deputy'
        ).all()

    return render_template('centers.html',
                           centers=centers,
                           selected_center=selected_center,
                           leaders=leaders)


@app.route('/download_gazette')
def download_gazette():
    return send_from_directory('static', 'school_gazette.pdf', as_attachment=True)


@app.route('/support', methods=['GET', 'POST'])
def support():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session.get('role')

    if request.method == 'POST':
        message = request.form['message']
        chat_id = request.form.get('chat_id')

        if role == 'admin' and not chat_id:
            flash('Выберите чат для отправки сообщения', 'error')
            return redirect(url_for('support'))

        if role == 'student':
            chat = SupportChat.query.filter_by(user_id=user_id).first()
            if not chat:
                chat = SupportChat(user_id=user_id)
                db.session.add(chat)
                db.session.commit()

        if role == 'admin':
            chat = SupportChat.query.get(chat_id)
            if not chat:
                flash('Чат не найден', 'error')
                return redirect(url_for('support'))

            if not chat.admin_id:
                chat.admin_id = user_id

        new_message = SupportMessage(
            chat_id=chat.id,
            sender_id=user_id,
            message=message
        )

        chat.last_message_time = datetime.datetime.now()

        if role == 'student':
            chat.unread_count += 1
        else:
            new_message.is_read = True

        db.session.add(new_message)
        db.session.commit()

        flash('Сообщение отправлено', 'success')
        return redirect(url_for('support'))

    if role == 'student':
        chat = SupportChat.query.filter_by(user_id=user_id).first()
        if not chat:
            chat = SupportChat(user_id=user_id)
            db.session.add(chat)
            db.session.commit()

        SupportMessage.query.filter_by(chat_id=chat.id, is_read=False) \
            .update({'is_read': True}, synchronize_session=False)
        chat.unread_count = 0
        db.session.commit()

        messages = SupportMessage.query.filter_by(chat_id=chat.id) \
            .order_by(SupportMessage.timestamp.asc()).all()

        return render_template('support_student.html',
                               messages=messages,
                               chat=chat)

    if role == 'admin':
        chats = SupportChat.query.order_by(SupportChat.last_message_time.desc()).all()
        current_chat_id = request.args.get('chat_id')

        if current_chat_id:
            current_chat = SupportChat.query.get(current_chat_id)

            SupportMessage.query.filter_by(chat_id=current_chat.id, is_read=False) \
                .update({'is_read': True}, synchronize_session=False)
            current_chat.unread_count = 0
            db.session.commit()

            messages = SupportMessage.query.filter_by(chat_id=current_chat.id) \
                .order_by(SupportMessage.timestamp.asc()).all()
        else:
            current_chat = None
            messages = []

        return render_template('support_admin.html',
                               chats=chats,
                               current_chat=current_chat,
                               messages=messages)


@app.route('/support/notifications')
def support_notifications():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return jsonify({})

    unread_chats = SupportChat.query.filter(SupportChat.unread_count > 0).count()
    return jsonify({
        'unread_chats': unread_chats,
        'unread_messages': sum(c.unread_count for c in SupportChat.query.all())
    })


@app.route('/reply_support/<int:message_id>', methods=['POST'])
def reply_support(message_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    message = SupportMessage.query.get_or_404(message_id)
    reply_text = request.form['reply_text']

    message.admin_response = reply_text
    message.is_read = True
    db.session.commit()

    flash('Ответ отправлен', 'success')
    return redirect(url_for('support'))


@app.route('/schedule')
def schedule():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    print(f"Загружаем расписание для класса: {user.class_}")
    schedule_data = load_schedule(user.class_)
    print(f"Загруженное расписание: {schedule_data}")

    return render_template('schedule.html',
                           schedule=schedule_data,
                           class_name=user.class_)


@app.route('/upload_schedule', methods=['GET', 'POST'])
def upload_schedule():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'schedule_file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(request.url)

        class_name = request.form.get('class_name')
        if not class_name:
            flash('Укажите класс', 'error')
            return redirect(request.url)

        file = request.files['schedule_file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            os.makedirs(app.config['SCHEDULE_FOLDER'], exist_ok=True)
            filename = get_schedule_filename(class_name)
            filepath = os.path.join(app.config['SCHEDULE_FOLDER'], filename)
            file.save(filepath)

            flash(f'Расписание для {class_name} успешно загружено', 'success')
            return redirect(url_for('upload_schedule'))
        else:
            flash('Разрешены только CSV файлы', 'error')
    classes = [user.class_ for user in User.query.distinct(User.class_).all()]
    return render_template('upload_schedule.html', classes=classes)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/news')
def news():
    news_list = News.query.order_by(News.publish_date.desc()).all()
    return render_template('news.html', news_list=news_list)


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


@app.route('/admin/news', methods=['GET', 'POST'])
def admin_news():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        new_news = News(
            title=title,
            content=content,
            publish_date=datetime.datetime.now(),
            author_id=session['user_id']
        )
        print(new_news.publish_date)
        db.session.add(new_news)
        db.session.commit()
        flash('Новость успешно добавлен', 'success')
        return redirect(url_for('admin_news'))

    news_list = News.query.order_by(News.publish_date.desc()).all()
    return render_template('admin_news.html', news_list=news_list)


@app.route('/news/view_news<int:news_id>')
def view_news(news_id):
    news = News.query.filter_by(id=news_id).first()
    return render_template('view_news.html', news=news)


@app.route('/admin/news/delete/<int:news_id>')
def delete_news(news_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    news = News.query.get_or_404(news_id)
    db.session.delete(news)
    db.session.commit()
    flash('Новость удалена', 'success')
    return redirect(url_for('admin_news'))


@app.route('/admin/students/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    student = User.query.get_or_404(student_id)

    if request.method == 'POST':
        student.username = request.form['username']
        if request.form['password']:
            student.password = request.form['password']
        student.fio = request.form['fio']
        class_ = request.form['class']
        if class_.lower() == "выпускник":
            student.class_ = "Выпускник"
            student.is_graduate = True
        else:
            student.class_ = class_
            student.is_graduate = False

        db.session.commit()
        flash('Данные ученика обновлены', 'success')
        return redirect(url_for('admin_students'))

    return render_template('edit_student.html', student=student)


@app.route('/admin/students/delete/<int:student_id>')
def delete_student(student_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    student = User.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash('Ученик удалён', 'success')
    return redirect(url_for('admin_students'))


# @app.route('/admin/students/promote_all', methods=['POST'])
# def promote_all_students():
#     print(11)
#     if not session.get('logged_in') or session.get('role') != 'admin':
#         return redirect(url_for('login'))
#
#     print(19)
#
#     students = User.query.filter_by(is_graduate=False).all()
#
#     for student in students:
#         class_num = ''.join(filter(str.isdigit, student.class_))
#         if class_num:
#             class_num = int(class_num)
#             if class_num < 11:
#                 letter = ''.join(filter(str.isalpha, student.class_))
#                 student.class_ = f"{class_num + 1}{letter}"
#             else:
#                 student.is_graduate = True
#                 student.class_ = "Выпускник"
#
#     db.session.commit()
#     flash('Все классы успешно переведены', 'success')
#     return redirect(url_for('admin_students'))


@app.route('/admin/students/promote_all', methods=['POST'])
def promote_students():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    current_class = request.form['current_class']

    if current_class == "all":
        students = User.query.filter_by(is_graduate=False).all()
    else:
        students = User.query.filter_by(class_=current_class, is_graduate=False).all()

    for student in students:
        class_num = ''.join(filter(str.isdigit, student.class_))
        if class_num:
            class_num = int(class_num)
            if class_num < 11:
                letter = ''.join(filter(str.isalpha, student.class_))
                student.class_ = f"{class_num + 1}{letter}"
            else:
                student.is_graduate = True
                student.class_ = "Выпускник"

    db.session.commit()
    if current_class == "all":
        flash(f'Все ученики переведены в следующий класс', 'success')
    else:
        flash(f'Ученики класса {current_class} переведены', 'success')
    return redirect(url_for('admin_students'))


@app.route('/admin/schedules')
def admin_schedules():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    classes = {user.class_ for user in User.query.distinct(User.class_).all()}
    schedules = {}

    for class_ in classes:
        schedules[class_] = load_schedule(class_)

    return render_template('admin_schedules.html',
                           schedules=schedules,
                           classes=classes)


@app.route('/admin/students', methods=['GET', 'POST'])
def admin_students():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    class_filter = request.args.get('class', '')

    if request.method == 'POST':
        username = generate_key(8)
        while User.query.filter_by(username=username).first():
            username = generate_key(8)
        password = generate_key(12)
        fio = request.form['fio']
        class_ = request.form['class']

        new_student = User(
            username=username,
            password=password,
            fio=fio,
            class_=class_,
            role='student'
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Ученик успешно добавлен', 'success')
        return redirect(url_for('admin_students'))

    query = User.query.filter_by(role='student')
    if class_filter:
        query = query.filter_by(class_=class_filter)

    students = query.order_by(User.class_, User.fio).all()
    classes = set(user.class_ for user in User.query.distinct(User.class_).all())

    return render_template('admin_students.html',
                           students=students,
                           classes=classes,
                           current_class=class_filter)


@app.route('/admin/students/<int:student_id>/achievements', methods=['GET', 'POST'])
def student_achievements(student_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    student = User.query.get_or_404(student_id)

    if request.method == 'POST':
        title = request.form['title']
        new_achievement = Achievement(
            user_id=student.id,
            title=title
        )
        db.session.add(new_achievement)
        db.session.commit()
        flash('Достижение добавлено', 'success')
        return redirect(url_for('student_achievements', student_id=student.id))

    achievements = Achievement.query.filter_by(user_id=student.id).all()
    return render_template('student_achievements.html',
                           student=student,
                           achievements=achievements)


@app.route('/admin/students/passwords')
def students_passwords():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    class_ = request.args.get('class', '')
    students = User.query.filter_by(role='student')

    if class_:
        students = students.filter_by(class_=class_)

    students = students.order_by(User.class_, User.fio).all()
    classes = [user.class_ for user in User.query.distinct(User.class_).all()]

    return render_template('students_passwords.html',
                           students=students,
                           classes=classes,
                           current_class=class_)


@app.route('/admin/news/edit/<int:news_id>', methods=['GET', 'POST'])
def edit_news(news_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    news = News.query.get_or_404(news_id)

    if request.method == 'POST':
        news.title = request.form['title']
        news.content = request.form['content']
        db.session.commit()
        flash('Новость обновлена', 'success')
        return redirect(url_for('admin_news'))

    return render_template('edit_news.html', news=news)


# ────────────────────────────────────────────
#  СОБЫТИЯ
# ────────────────────────────────────────────

MONTHS_RU = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}


@app.route('/events')
def events():
    today = datetime.date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    cal = calendar.monthcalendar(year, month)

    start = datetime.date(year, month, 1)
    end = datetime.date(year, month, calendar.monthrange(year, month)[1])
    events_list = Event.query.filter(Event.date >= start, Event.date <= end) \
        .order_by(Event.date, Event.time).all()

    events_by_day = {}
    for ev in events_list:
        events_by_day.setdefault(ev.date.day, []).append(ev)

    return render_template('events.html',
                           calendar_weeks=cal,
                           events_by_day=events_by_day,
                           events_list=events_list,
                           year=year, month=month,
                           month_name=MONTHS_RU[month],
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month,
                           today_day=today.day if (year == today.year and month == today.month) else -1,
                           current_month=(month == today.month),
                           current_year=(year == today.year))


@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    is_registered = False
    if session.get('logged_in'):
        is_registered = EventRegistration.query.filter_by(
            event_id=event_id, user_id=session['user_id']
        ).first() is not None
    return render_template('event_detail.html', event=event, is_registered=is_registered)


@app.route('/events/confirm_participation/<int:reg_id>', methods=['POST'])
def confirm_participation(reg_id):
    if session.get('role') not in ['admin', 'leader']:
        flash('У вас нет прав для этого действия', 'error')
        return redirect(url_for('events'))

    registration = EventRegistration.query.get_or_404(reg_id)

    if not registration.is_confirmed:
        registration.is_confirmed = True

        new_achievement = Achievement(
            user_id=registration.user_id,
            title=f"Участие в мероприятии: {registration.event.title}",
            date=datetime.date.today()
        )
        db.session.add(new_achievement)

        db.session.commit()
        flash(f'Участие {registration.user.fio} подтверждено. Баллы начислены!', 'success')
    else:
        flash('Участие уже было подтверждено ранее', 'info')

    return redirect(url_for('event_detail', event_id=registration.event_id))


@app.route('/events/<int:event_id>/register', methods=['POST'])
def event_register(event_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    role = request.form.get('role', 'viewer')
    existing = EventRegistration.query.filter_by(
        event_id=event_id, user_id=session['user_id']
    ).first()
    if not existing:
        reg = EventRegistration(event_id=event_id, user_id=session['user_id'], role=role)
        db.session.add(reg)
        db.session.commit()
        flash('Вы успешно записались на мероприятие!', 'success')
    else:
        flash('Вы уже записаны на это мероприятие', 'error')
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/events/<int:event_id>/unregister', methods=['POST'])
def event_unregister(event_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    reg = EventRegistration.query.filter_by(
        event_id=event_id, user_id=session['user_id']
    ).first()
    if reg:
        db.session.delete(reg)
        db.session.commit()
        flash('Запись отменена', 'success')
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/admin/events', methods=['GET', 'POST'])
def admin_events():
    if not session.get('logged_in') or session.get('role') not in ('admin', 'leader'):
        return redirect(url_for('login'))

    is_leader = session.get('role') == 'leader'
    leader_center = session.get('center_name') if is_leader else None

    if request.method == 'POST':
        date_str = request.form['date']
        time_str = request.form.get('time') or None
        center = leader_center if is_leader else (request.form.get('center') or None)
        ev = Event(
            title=request.form['title'],
            date=datetime.date.fromisoformat(date_str),
            time=time_str,
            organizer=request.form.get('organizer') or None,
            responsible_leader=request.form.get('responsible_leader') or None,
            center=center,
            description=request.form.get('description') or None,
            author_id=session['user_id']
        )
        db.session.add(ev)
        db.session.commit()
        flash('Событие добавлено', 'success')
        return redirect(url_for('admin_events'))

    if is_leader:
        all_events = Event.query.filter_by(center=leader_center).order_by(Event.date.desc()).all()
    else:
        all_events = Event.query.order_by(Event.date.desc()).all()

    leaders = CenterLeader.query.filter_by(role='leader').all()
    centers = Center.query.all()
    return render_template('admin_events.html',
                           events=all_events,
                           leaders=leaders,
                           centers=centers,
                           edit_event=None,
                           is_leader=is_leader,
                           leader_center=leader_center)


@app.route('/admin/events/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if not session.get('logged_in') or session.get('role') not in ('admin', 'leader'):
        return redirect(url_for('login'))

    ev = Event.query.get_or_404(event_id)
    is_leader = session.get('role') == 'leader'
    leader_center = session.get('center_name') if is_leader else None

    if is_leader and ev.center != leader_center:
        flash('У вас нет доступа к этому событию', 'error')
        return redirect(url_for('admin_events'))

    if request.method == 'POST':
        ev.title = request.form['title']
        ev.date = datetime.date.fromisoformat(request.form['date'])
        ev.time = request.form.get('time') or None
        ev.organizer = request.form.get('organizer') or None
        ev.responsible_leader = request.form.get('responsible_leader') or None
        ev.center = leader_center if is_leader else (request.form.get('center') or None)
        ev.description = request.form.get('description') or None
        db.session.commit()
        flash('Событие обновлено', 'success')
        return redirect(url_for('admin_events'))

    all_events = Event.query.filter_by(center=leader_center).order_by(Event.date.desc()).all() \
        if is_leader else Event.query.order_by(Event.date.desc()).all()
    leaders = CenterLeader.query.filter_by(role='leader').all()
    centers = Center.query.all()
    return render_template('admin_events.html',
                           events=all_events,
                           leaders=leaders,
                           centers=centers,
                           edit_event=ev,
                           is_leader=is_leader,
                           leader_center=leader_center)


@app.route('/admin/events/delete/<int:event_id>')
def delete_event(event_id):
    if not session.get('logged_in') or session.get('role') not in ('admin', 'leader'):
        return redirect(url_for('login'))
    ev = Event.query.get_or_404(event_id)
    if session.get('role') == 'leader' and ev.center != session.get('center_name'):
        flash('У вас нет доступа к этому событию', 'error')
        return redirect(url_for('admin_events'))
    db.session.delete(ev)
    db.session.commit()
    flash('Событие удалено', 'success')
    return redirect(url_for('admin_events'))


@app.route('/admin/leaders', methods=['GET', 'POST'])
def admin_leaders():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'assign':
            user_id = request.form.get('user_id')
            center_name = request.form.get('center_name')
            user = User.query.get_or_404(user_id)
            user.role = 'leader'
            user.center_name = center_name
            db.session.commit()
            flash(f'{user.fio} назначен руководителем центра «{center_name}»', 'success')

        elif action == 'revoke':
            user_id = request.form.get('user_id')
            user = User.query.get_or_404(user_id)
            user.role = 'student'
            user.center_name = None
            db.session.commit()
            flash(f'Права руководителя центра сняты с {user.fio}', 'success')

        elif action == 'create':
            username = generate_key(8)
            while User.query.filter_by(username=username).first():
                username = generate_key(8)
            password = generate_key(12)
            center_name = request.form.get('center_name')
            fio = request.form.get('fio')
            new_leader = User(
                username=username,
                password=password,
                fio=fio,
                class_='Руководство',
                role='leader',
                center_name=center_name
            )
            db.session.add(new_leader)
            db.session.commit()
            flash(f'Создан аккаунт руководителя: логин {username}, пароль {password}', 'success')

        return redirect(url_for('admin_leaders'))

    leaders = User.query.filter_by(role='leader').all()
    students = User.query.filter_by(role='student').order_by(User.fio).all()
    centers = Center.query.all()
    return render_template('admin_leaders.html',
                           leaders=leaders,
                           students=students,
                           centers=centers)


@app.context_processor
def inject_news():
    latest_news = News.query.order_by(News.publish_date.desc()).limit(10).all()
    return dict(marquee_news=latest_news)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
