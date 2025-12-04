from flask import Blueprint


chats = Blueprint('chats', __name__)


@chats.route('/send-message', methods=['POST'])
def send_message():
    return render_template('chats.html')
