from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Room, RoomMember, User, Chat
from . import db

views = Blueprint('views', __name__)


@views.route('/')
def home():
    return render_template('index.html')

@views.route('/room')
@login_required
def room():
    # Get rooms the user has joined
    joined_rooms = db.session.query(Room).join(RoomMember).filter(RoomMember.user_id == current_user.id).all()
    return render_template('room.html', joined_rooms=joined_rooms)


@views.route('/create-room', methods=['POST'])
@login_required
def create_room():
    room_name = request.form.get('room_name')
    password = request.form.get('password')

    if not room_name:
        flash('Room name cannot be empty.', category='error')
        return redirect(url_for('views.room'))

    existing_room = Room.query.filter_by(room_name=room_name).first()
    if existing_room:
        flash('Room already exists.', category='error')
        return redirect(url_for('views.room'))

    # Hash password if provided
    hashed_password = None
    if password:
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(password)

    new_room = Room(room_name=room_name, password=hashed_password)
    db.session.add(new_room)
    db.session.commit()

    # Add creator as member
    member = RoomMember(room_id=new_room.id, user_id=current_user.id)
    db.session.add(member)
    db.session.commit()

    flash('Room created!', category='success')
    return redirect(url_for('views.chat', room_code=room_name))

@views.route('/join-room', methods=['POST'])
@login_required
def join_room():
    room_name = request.form.get('room_code') # Using room_code input name from room.html which acts as name
    password = request.form.get('password')

    if not room_name:
        flash('Please enter a room name.', category='error')
        return redirect(url_for('views.room'))

    room = Room.query.filter_by(room_name=room_name).first()
    if not room:
        flash('Room does not exist.', category='error')
        return redirect(url_for('views.room'))

    # Verify password if room has one
    if room.password:
        from werkzeug.security import check_password_hash
        if not password or not check_password_hash(room.password, password):
            flash('Incorrect room password.', category='error')
            return redirect(url_for('views.room'))

    # Check if already a member
    is_member = RoomMember.query.filter_by(room_id=room.id, user_id=current_user.id).first()
    if is_member:
        flash('You are already in this room.', category='info')
        return redirect(url_for('views.chat', room_code=room_name))

    # Check member limit
    member_count = RoomMember.query.filter_by(room_id=room.id).count()
    if member_count >= 5:
        flash('Room is full (max 5 members).', category='error')
        return redirect(url_for('views.room'))

    # Join room
    new_member = RoomMember(room_id=room.id, user_id=current_user.id)
    db.session.add(new_member)
    db.session.commit()

    flash('Joined room successfully!', category='success')
    return redirect(url_for('views.chat', room_code=room_name))

@views.route('/chat/<room_code>')
@login_required
def chat(room_code):
    room = Room.query.filter_by(room_name=room_code).first()
    if not room:
        flash('Room not found.', category='error')
        return redirect(url_for('views.room'))
    
    # Check if user is a member
    is_member = RoomMember.query.filter_by(room_id=room.id, user_id=current_user.id).first()
    if not is_member:
        flash('You are not a member of this room.', category='error')
        return redirect(url_for('views.room'))

    # Get all members of the room
    members = db.session.query(User).join(RoomMember).filter(RoomMember.room_id == room.id).all()

    # Fetch chat history for this user in this room
    chats = db.session.query(Chat, User.username).join(User, Chat.user_id == User.id).filter(
        Chat.room_id == room.id,
        Chat.recipient_id == current_user.id
    ).order_by(Chat.timestamp).all()

    return render_template('chat.html', room_code=room_code, room_id=room.id, user=current_user, members=members, chats=chats)

@views.route('/leave-room/<int:room_id>')
@login_required
def leave_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        flash('Room not found.', category='error')
        return redirect(url_for('views.room'))

    member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
        flash('You have left the room.', category='success')
    else:
        flash('You are not a member of this room.', category='error')

    return redirect(url_for('views.room'))
