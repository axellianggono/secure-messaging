from flask import request
from datetime import datetime
from flask_socketio import emit, join_room, leave_room
from . import socketio

from . import db
from .models import Chat, User

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    # Get user details to broadcast public key
    user = User.query.filter_by(username=username).first()
    if user:
        emit('member_joined', {
            'id': user.id,
            'username': user.username,
            'public_key': user.kunci_publik
        }, room=room)
        
    emit('message', {'msg': username + ' has entered the room.', 'username': 'System'}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('message', {'msg': username + ' has left the room.', 'username': 'System'}, room=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    ciphertext = data['ciphertext']
    iv = data['iv']
    sender_username = data['sender_username']
    recipients = data['recipients'] # List of {user_id, encrypted_session_key}
    
    # Get sender ID
    sender = User.query.filter_by(username=sender_username).first()
    if not sender:
        return

    # Save to DB for each recipient
    for recipient in recipients:
        new_chat = Chat(
            user_id=sender.id,
            recipient_id=recipient['user_id'],
            room_id=data['room_id'], # We need room_id (int) not just room_name
            ciphertext=ciphertext,
            encrypted_session_key=recipient['encrypted_session_key'],
            iv=iv
        )
        db.session.add(new_chat)
    
    db.session.commit()

    # Broadcast to room
    # We send the full recipients list so each client can find their own key
    emit('message', {
        'ciphertext': ciphertext,
        'iv': iv,
        'sender_username': sender_username,
        'recipients': recipients,
        'timestamp': str(datetime.utcnow())
    }, room=room)
