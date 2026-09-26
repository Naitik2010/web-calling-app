from flask import Flask, render_template
from flask_socketio import SocketIO, emit, request

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Track registered IDs: { "user_id": "socket_sid" }
registered_users = {}
# Track socket sessions: { "socket_sid": "user_id" }
sid_to_id = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register_id')
def handle_register(user_id):
    sid = request.sid
    
    # Check if this ID is already taken by another active device/tab
    if user_id in registered_users and registered_users[user_id] != sid:
        emit('registration_error', {'error': 'This ID is already in use. Please try another ID.'})
        return

    # If this socket was already registered under a different ID, clean it up first
    if sid in sid_to_id:
        old_id = sid_to_id[sid]
        if old_id in registered_users:
            del registered_users[old_id]

    # Register the new ID
    registered_users[user_id] = sid
    sid_to_id[sid] = user_id
    print(f"User registered: {user_id} (SID: {sid})")

@socketio.on('call_user')
def handle_call(data):
    target_id = data['target_id']
    if target_id in registered_users:
        target_sid = registered_users[target_id]
        emit('incoming_call', {
            'caller_id': data['caller_id'],
            'offer': data['offer']
        }, room=target_sid)
    else:
        emit('call_failed', {'error': 'Target ID is offline or does not exist.'})

@socketio.on('make_answer')
def handle_answer(data):
    caller_id = data['caller_id']
    if caller_id in registered_users:
        caller_sid = registered_users[caller_id]
        emit('call_answered', {'answer': data['answer']}, room=caller_sid)

@socketio.on('ice_candidate')
def handle_ice(data):
    target_id = data['target_id']
    if target_id in registered_users:
        target_sid = registered_users[target_id]
        emit('ice_candidate', {'candidate': data['candidate']}, room=target_sid)

@socketio.on('hang_up')
def handle_hangup(data):
    target_id = data['target_id']
    if target_id in registered_users:
        target_sid = registered_users[target_id]
        emit('call_ended', room=target_sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in sid_to_id:
        user_id = sid_to_id[sid]
        if user_id in registered_users:
            del registered_users[user_id]
        del sid_to_id[sid]
        print(f"User disconnected and ID freed: {user_id}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)