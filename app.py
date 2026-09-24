from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory dictionary to map emails to socket IDs
active_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register_email')
def handle_register(email):
    active_users[email] = request.sid
    print(f"Registered: {email} -> {request.sid}")

@socketio.on('call_user')
def handle_call(data):
    target_email = data['target_email']
    caller_email = data['caller_email']
    offer = data['offer']
    
    target_sid = active_users.get(target_email)
    if target_sid:
        # Forward the WebRTC call offer to the target user
        emit('incoming_call', {'caller_email': caller_email, 'offer': offer}, room=target_sid)
    else:
        emit('call_failed', {'error': 'User not online or email not found.'})

@socketio.on('make_answer')
def handle_answer(data):
    caller_email = data['caller_email']
    answer = data['answer']
    caller_sid = active_users.get(caller_email)
    if caller_sid:
        emit('call_answered', {'answer': answer}, room=caller_sid)

@socketio.on('ice_candidate')
def handle_ice(data):
    target_email = data['target_email']
    candidate = data['candidate']
    target_sid = active_users.get(target_email)
    if target_sid:
        emit('ice_candidate', {'candidate': candidate}, room=target_sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)