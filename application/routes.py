import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage
from application import app, db, socketio
from flask.json import dumps
from flask import render_template, request, json, Response, redirect, flash, url_for, session
from application.models import User, ChatMessage, Note, ChatRoom, Availability
from application.forms import LoginForm, RegisterForm, AvailabilityForm
from flask_socketio import join_room, leave_room, emit, send
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
from bson import ObjectId
from bson.json_util import dumps



@app.route("/")
@app.route("/index")
@app.route("/home")
def index():
    return render_template("index.html", index=True)

@app.route("/login", methods=['GET','POST'])
def login():
    if session.get('username'):
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.objects(email=email).first()
        if user and user.get_password(password):
            flash(f"{user.first_name}, you are successfully logged in!", "success")
            session['user_id'] = str(user.user_id)
            session['username'] = user.first_name
            return redirect("/index")
        else:
            flash("Sorry, something went wrong.", "danger")
    return render_template("login.html", title="Login", form=form, login=True)

@app.route("/logout")
def logout():
    session['user_id'] = False
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/register", methods=['POST','GET'])
def register():
    if session.get('username'):
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        user_id = User.objects.count()
        user_id += 1

        email = form.email.data
        password = form.password.data
        first_name = form.first_name.data
        last_name = form.last_name.data

        user = User(user_id=user_id, email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.save()
        flash("You are successfully registered!", "success")
        return redirect(url_for('index'))
    return render_template("register.html", title="Register", form=form, register=True)

@app.before_first_request
def create_rooms():
    # Creating 5 default rooms
    for i in range(1, 6):
        room_name = f'Room {i}'
        existing_room = ChatRoom.objects(room_name=room_name).first()
        if not existing_room:
            new_room = ChatRoom(room_name=room_name, password=generate_password_hash('Enter.123'))
            new_room.save()

@app.route("/rooms")
def rooms():
    if not session.get('username'):
        return redirect(url_for('login'))
    rooms = ChatRoom.objects.all()
    return render_template("rooms.html", rooms=rooms)

@app.route("/rooms/join", methods=['POST'])
def join_chat_room():
    room_name = request.form.get('room_name')
    password = request.form.get('password')
    room = ChatRoom.objects(room_name=room_name).first()
    if room and room.check_password(password):
        user = User.objects.get(first_name=session.get('username'))
        if user not in room.users:
            room.users.append(user)
            room.save()
        session['room_id'] = str(room.id)
        return redirect(url_for('chat'))
    else:
        flash("Invalid room name or password.", "danger")
        return redirect(url_for('rooms'))

@app.route("/chat")
def chat():
    if not session.get('username'):
        return redirect(url_for('login'))
    
    room_id = session.get('room_id')
    if not room_id:
        flash("You must join a room before entering the chat.", "danger")
        return redirect(url_for('rooms'))
    room_object = ChatRoom.objects.get(id=room_id)

    chat_messages = ChatMessage.objects(room=room_object).order_by('-created_at')

    messages = [{'username': message.user.first_name, 'message': message.message, 'created_at': message.created_at.isoformat()} for message in list(chat_messages)][::-1]
    
    return render_template("chat.html", room=room_object, messages=messages, user=session.get('username'), chat=True)

@socketio.on('join')
def on_join(data):
    room_id = data['room_id']
    join_room(room_id)
    emit('load_messages', room=room_id)

@socketio.on('leave')
def on_leave(data):
    user_id = data['user_id']
    room_id = data['room_id']
    leave_room(room_id)
    # Fetch user's first name and last name from database using user_id
    user = User.objects.get(user_id=user_id)
    if user:
        send(user.first_name + ' ' + user.last_name + ' has left the room.', room=room_id)

@socketio.on('message')
def handle_message(data):
    user_id = session.get('user_id')
    room_id = session.get('room_id')
    message_content = data['message']

    user = User.objects(user_id=user_id).first()
    room = ChatRoom.objects.get(id=room_id)

    if user and room:
        chat_message = ChatMessage(user=user, room=room, message=message_content)
        chat_message.save()

        message_data = {
            'user_id': str(user.user_id),
            'username': user.first_name,
            'message': message_content
        }
        print('message', message_data)
        emit('message', message_data, room=room_id)

@socketio.on('request_messages')
def load_messages():
    room_id = session.get('room_id')
    room = ChatRoom.objects.get(id=room_id)
    chat_messages = ChatMessage.objects(room=room).order_by('-created_at')
    messages = []
    for message in chat_messages:
        message_dict = {
            'username': message.user.first_name,
            'message': message.message,
            'created_at': message.created_at.isoformat()
        }
        messages.append(message_dict)
    emit('display_messages', {'messages': messages})

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    
    if not session.get('username'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        content = request.form.get('content')
        note = Note(content=content)
        note.save()
        note_dict = {
            'content': note.content,
            'created_at': note.created_at.isoformat()
        }
        return jsonify({'message': 'Note added successfully.', 'note': note_dict})
    elif request.method == 'GET':
        notes = Note.objects.order_by('-created_at')
        return render_template('notes.html', notes=notes)

@app.route("/contact")
def contact():
    return render_template("contact.html", contact=True)

@app.route('/availability', methods=['GET', 'POST'])
def availability():
    if not session.get('username'):
        return redirect(url_for('login'))

    form = AvailabilityForm()
    if form.validate_on_submit():
        user_id = session.get('user_id')
        if user_id:
            day = form.day.data
            status = form.status.data
            user = User.objects.get(user_id=user_id)
            availability = Availability.objects(user=user, day=day).first()
            if availability:
                availability.status = status
            else:
                availability = Availability(user=user, day=day, status=status)
            availability.save()
            socketio.emit('availability_updated', {
                'first_name': user.first_name,
                'user_id': str(user_id),
                'day': day,
                'status': status
            }, )
            flash('Availability saved successfully', 'success')
        else:
            flash('Please log in to save availability', 'danger')
            return redirect(url_for('login'))

    # Fetch all availabilities and send them to the template
    availabilities = Availability.objects().all()
    return render_template('availability.html', form=form, availabilities=availabilities)

def send_email(name, email, message):
    sender_email = "sendresponse8@gmail.com"
    sender_password = "Enter.123"
    receiver_email = "aleks.preni1@gmail.com"
    email_msg = EmailMessage()
    email_msg["From"] = name
    email_msg["To"] = receiver_email
    email_msg["Subject"] = "New Contact Form Submission"
    email_msg.set_content(f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}")
    try:
        # Connect to the SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(email_msg)
        return True
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
        return False

@app.route('/submit_contact_form', methods=['POST'])
def submit_contact_form():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    # Perform form validation
    if not name or not email or not message:
        flash('Please fill in all the required fields.', 'error')
        return redirect(request.referrer)
    # Send the email
    send_email(name, email, message)
    # Flash success message
    flash('Thank you for your message!', 'success')
    # Redirect back to the contact form
    return redirect(request.referrer)


if __name__ == "__main__":
    socketio.run(app)
