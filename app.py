from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory dictionary to map user IDs to socket IDs
active_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register_id')
def handle_register(user_id):
    active_users[user_id] = request.sid
    print(f"Registered ID: {user_id} -> {request.sid}")

@socketio.on('call_user')
def handle_call(data):
    target_id = data['target_id']
    caller_id = data['caller_id']
    offer = data['offer']
    
    target_sid = active_users.get(target_id)
    if target_sid:
        emit('incoming_call', {'caller_id': caller_id, 'offer': offer}, room=target_sid)
    else:
        emit('call_failed', {'error': 'User not online or ID not found.'})

@socketio.on('make_answer')
def handle_answer(data):
    caller_id = data['caller_id']
    answer = data['answer']
    caller_sid = active_users.get(caller_id)
    if caller_sid:
        emit('call_answered', {'answer': answer}, room=caller_sid)

@socketio.on('ice_candidate')
def handle_ice(data):
    target_id = data['target_id']
    candidate = data['candidate']
    target_sid = active_users.get(target_id)
    if target_sid:
        emit('ice_candidate', {'candidate': candidate}, room=target_sid)

@socketio.on('hang_up')
def handle_hang_up(data):
    target_id = data.get('target_id')
    target_sid = active_users.get(target_id)
    if target_sid:
        emit('call_ended', room=target_sid)

@socketio.on('disconnect')
def handle_disconnect():
    for user_id, sid in list(active_users.items()):
        if sid == request.sid:
            del active_users[user_id]
            print(f"Disconnected & Removed ID: {user_id}")
            break

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)