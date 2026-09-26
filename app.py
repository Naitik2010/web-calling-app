```python
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import secrets
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Stores persistent browser sessions.
#
# Example:
# {
#     "123": {
#         "session_token": "...",
#         "socket_id": "..."
#     }
# }
#
# The session stays here even when the browser reloads or disconnects.
# It is removed only when the user explicitly logs out
# or the server restarts.
registered_users = {}


@app.route('/')
def index():
    return render_template('index.html')


# ---------------------------------------------------------
# REGISTER / RESTORE SESSION
# ---------------------------------------------------------

@socketio.on('register_id')
def handle_register(data):
    """
    Handles both:
    1. First-time registration
    2. Automatic restoration after page reload
    """

    if not isinstance(data, dict):
        emit('registration_failed', {
            'error': 'Invalid registration request.'
        })
        return

    user_id = str(data.get('user_id', '')).strip()
    existing_token = str(data.get('session_token', '')).strip()

    if not user_id:
        emit('registration_failed', {
            'error': 'Please enter a valid ID.'
        })
        return

    # -----------------------------------------------------
    # ID ALREADY EXISTS
    # -----------------------------------------------------

    if user_id in registered_users:

        saved_session = registered_users[user_id]
        saved_token = saved_session['session_token']

        # Same browser/device reconnecting after reload
        if existing_token and existing_token == saved_token:

            saved_session['socket_id'] = request.sid

            print(
                f"Session restored: {user_id} -> {request.sid}"
            )

            emit('registration_success', {
                'user_id': user_id,
                'session_token': saved_token,
                'restored': True
            })

            return

        # Another device/browser trying to use the ID
        emit('registration_failed', {
            'error': f'ID {user_id} is already registered on another device.'
        })

        return

    # -----------------------------------------------------
    # FIRST-TIME REGISTRATION
    # -----------------------------------------------------

    session_token = secrets.token_urlsafe(32)

    registered_users[user_id] = {
        'session_token': session_token,
        'socket_id': request.sid
    }

    print(
        f"New registration: {user_id} -> {request.sid}"
    )

    emit('registration_success', {
        'user_id': user_id,
        'session_token': session_token,
        'restored': False
    })


# ---------------------------------------------------------
# LOG OUT
# ---------------------------------------------------------

@socketio.on('logout')
def handle_logout(data):

    if not isinstance(data, dict):
        return

    user_id = str(data.get('user_id', '')).strip()
    session_token = str(data.get('session_token', '')).strip()

    if not user_id:
        return

    saved_session = registered_users.get(user_id)

    if not saved_session:
        emit('logout_success')
        return

    # Only the device that owns the session can log out
    if saved_session['session_token'] != session_token:
        emit('logout_failed', {
            'error': 'Invalid session.'
        })
        return

    # Make sure the request is coming from the registered socket
    if saved_session['socket_id'] != request.sid:
        emit('logout_failed', {
            'error': 'Invalid connection.'
        })
        return

    del registered_users[user_id]

    print(f"Logged out: {user_id}")

    emit('logout_success')


# ---------------------------------------------------------
# CALL USER
# ---------------------------------------------------------

@socketio.on('call_user')
def handle_call(data):

    target_id = str(data.get('target_id', '')).strip()
    caller_id = str(data.get('caller_id', '')).strip()
    offer = data.get('offer')

    target_session = registered_users.get(target_id)

    if target_session and target_session.get('socket_id'):

        emit(
            'incoming_call',
            {
                'caller_id': caller_id,
                'offer': offer
            },
            room=target_session['socket_id']
        )

    else:

        emit('call_failed', {
            'error': 'User not online or ID not found.'
        })


# ---------------------------------------------------------
# ANSWER CALL
# ---------------------------------------------------------

@socketio.on('make_answer')
def handle_answer(data):

    caller_id = str(data.get('caller_id', '')).strip()
    answer = data.get('answer')

    caller_session = registered_users.get(caller_id)

    if caller_session and caller_session.get('socket_id'):

        emit(
            'call_answered',
            {
                'answer': answer
            },
            room=caller_session['socket_id']
        )


# ---------------------------------------------------------
# ICE CANDIDATES
# ---------------------------------------------------------

@socketio.on('ice_candidate')
def handle_ice(data):

    target_id = str(data.get('target_id', '')).strip()
    candidate = data.get('candidate')

    target_session = registered_users.get(target_id)

    if target_session and target_session.get('socket_id'):

        emit(
            'ice_candidate',
            {
                'candidate': candidate
            },
            room=target_session['socket_id']
        )


# ---------------------------------------------------------
# HANG UP
# ---------------------------------------------------------

@socketio.on('hang_up')
def handle_hang_up(data):

    target_id = str(data.get('target_id', '')).strip()

    target_session = registered_users.get(target_id)

    if target_session and target_session.get('socket_id'):

        emit(
            'call_ended',
            room=target_session['socket_id']
        )


# ---------------------------------------------------------
# DISCONNECT
# ---------------------------------------------------------

@socketio.on('disconnect')
def handle_disconnect():

    # IMPORTANT:
    #
    # We DO NOT delete the user's registration here.
    #
    # This is what makes page reload/browser close/reconnect
    # different from an explicit Logout.
    #
    # We only remove the temporary Socket.IO connection.

    for user_id, session in registered_users.items():

        if session.get('socket_id') == request.sid:

            session['socket_id'] = None

            print(
                f"Socket disconnected, session preserved: {user_id}"
            )

            break


# ---------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------

if __name__ == '__main__':

    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )