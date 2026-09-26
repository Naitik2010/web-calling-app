from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Maps user IDs to socket IDs
# Example: {"456": "abc123socketid"}
active_users = {}


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('register_id')
def handle_register(user_id):
    user_id = str(user_id).strip()

    if not user_id:
        emit('registration_failed', {
            'error': 'Please enter a valid ID.'
        })
        return

    # Check if this ID is already registered on another device
    if user_id in active_users:
        existing_sid = active_users[user_id]

        # Same socket registering again -> allow it
        if existing_sid == request.sid:
            emit('registration_success')
            return

        # ID is already being used by another connected device
        emit('registration_failed', {
            'error': f'ID {user_id} is already online on another device.'
        })
        return

    # Register this ID
    active_users[user_id] = request.sid

    print(f"Registered ID: {user_id} -> {request.sid}")

    emit('registration_success')


@socketio.on('call_user')
def handle_call(data):
    target_id = str(data['target_id']).strip()
    caller_id = str(data['caller_id']).strip()
    offer = data['offer']

    target_sid = active_users.get(target_id)

    if target_sid:
        emit(
            'incoming_call',
            {
                'caller_id': caller_id,
                'offer': offer
            },
            room=target_sid
        )
    else:
        emit('call_failed', {
            'error': 'User not online or ID not found.'
        })


@socketio.on('make_answer')
def handle_answer(data):
    caller_id = str(data['caller_id']).strip()
    answer = data['answer']

    caller_sid = active_users.get(caller_id)

    if caller_sid:
        emit(
            'call_answered',
            {'answer': answer},
            room=caller_sid
        )


@socketio.on('ice_candidate')
def handle_ice(data):
    target_id = str(data['target_id']).strip()
    candidate = data['candidate']

    target_sid = active_users.get(target_id)

    if target_sid:
        emit(
            'ice_candidate',
            {'candidate': candidate},
            room=target_sid
        )


@socketio.on('hang_up')
def handle_hang_up(data):
    target_id = str(data.get('target_id', '')).strip()

    target_sid = active_users.get(target_id)

    if target_sid:
        emit('call_ended', room=target_sid)


@socketio.on('disconnect')
def handle_disconnect():
    # Find the ID belonging to this socket and remove it
    for user_id, sid in list(active_users.items()):
        if sid == request.sid:
            del active_users[user_id]

            print(
                f"Disconnected & Removed ID: {user_id}"
            )

            break


import os

if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )