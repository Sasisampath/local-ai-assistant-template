import secrets
from flask import Flask, request, jsonify, render_template_string, redirect, session
from transformers import GPT2Config, GPT2LMHeadModel, AutoTokenizer, pipeline
import os
from datetime import datetime
from dotenv import load_dotenv

# 1. Load the vault
load_dotenv() 

app = Flask(__name__)

# 2. Grab the values using os.getenv
app.secret_key = os.getenv("FLASK_SECRET_KEY")
PASSWORD = os.getenv("APP_PASSWORD")

# --- YOUR ORIGINAL CODE: PART 1 (THE BRAIN) ---
config = GPT2Config(
    vocab_size=50257,
    n_positions=256,
    n_embd=256,
    n_layer=4,
    n_head=4
)
model = GPT2LMHeadModel(config)
print(f"Successfully programmed a model with {model.num_parameters():,} parameters!")

tokenizer = AutoTokenizer.from_pretrained("gpt2")
inputs = tokenizer("Hello, my name is", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=10)
print("\nUntrained Output:")
print(tokenizer.decode(outputs, skip_special_tokens=True))

# --- YOUR ORIGINAL CODE: PART 2 (TINYLLAMA) ---
print("\nLoading TinyLlama... (This might take a second)")
generator = pipeline(
    "text-generation",
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    device_map="auto"
)

print("\n--- TinyLlama Web Chatbot Activated! ---")

# --- FLASK STUFF (just the web wrapper) ---
@app.before_request
def check_auth():
    # Allow the login page and static assets to load without auth
    if request.path == '/login' or request.path.startswith('/static'):
        return None
        
    # Check the session instead of the raw cookie
    if not session.get('logged_in'):
        return redirect('/login')
    
LOGIN_HTML = """
<html><body style="font-family:sans-serif;max-width:300px;margin:auto;padding-top:100px">
<h2>Enter Password</h2>
<input id="pw" type="password" placeholder="Password" />
<button onclick="login()">Enter</button>
<script>
async function login() {
  const res = await fetch('/login', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({password: document.getElementById('pw').value})
  });
  if ((await res.json()).ok) location.href='/';
  else alert('Wrong password!');
}
</script>
</body></html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pw = request.json.get('password')
        if pw == PASSWORD:
            # Instead of a cookie with the password, set a session flag
            session['logged_in'] = True
            return jsonify({"ok": True})
        return jsonify({"ok": False}), 401
    return render_template_string(LOGIN_HTML)

HTML = """
<!DOCTYPE html>
<html>
<head><title>Y</title>
<style>
  body { font-family: sans-serif; max-width: 600px; margin: auto; padding: 1rem; }
  #chat { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 1rem; margin-bottom: 1rem; }
  input { width: 70%; padding: 0.5rem; }
  button { padding: 0.5rem 1rem; }
  #forget-btn { background-color: #ff4444; color: white; border: none; cursor: pointer; margin-left: 0.5rem; }
  #forget-btn:hover { background-color: #cc0000; }
  .user { color: blue; white-space: pre-wrap; word-wrap: break-word; margin: 8px 0; } 
  .bot { color: green; white-space: pre-wrap; word-wrap: break-word; margin: 8px 0; }
  .system-msg { color: gray; font-style: italic; text-align: center; }
  .thinking { color: gray; font-style: italic; }
  #send-btn:disabled { background-color: #cccccc; cursor: not-allowed; }
  #forget-btn:disabled { background-color: #ffaaaa; cursor: not-allowed; }
  input:disabled { background-color: #f0f0f0; cursor: not-allowed; }
</style>
</head>
<body>
<h2>Y</h2>
<div id="chat"></div>
<input id="msg" type="text" placeholder="Type a message..." />
<button id="send-btn" onclick="send()">Send</button>
<button id="forget-btn" onclick="forget()">Forget 🧠</button>
<script>
function setLoading(isLoading) {
  document.getElementById('msg').disabled = isLoading;
  document.getElementById('send-btn').disabled = isLoading;
  document.getElementById('forget-btn').disabled = isLoading;
  document.getElementById('send-btn').textContent = isLoading ? 'Sending...' : 'Send';
}

async function send() {
  const msg = document.getElementById('msg').value.trim();
  if (!msg) return;
  const chat = document.getElementById('chat');
  chat.innerHTML += `<p class='user'>You: ${msg}</p>`;
  document.getElementById('msg').value = '';
  setLoading(true);
  const thinkingEl = document.createElement('p');
  thinkingEl.className = 'thinking';
  thinkingEl.id = 'thinking-msg';
  thinkingEl.textContent = '🤔 Thinking...';
  chat.appendChild(thinkingEl);
  chat.scrollTop = chat.scrollHeight;

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });
    const data = await res.json();
    document.getElementById('thinking-msg').remove();
    chat.innerHTML += `<p class='bot'>Bot: ${data.reply}</p>`;
  } catch (err) {
    document.getElementById('thinking-msg').remove();
    chat.innerHTML += `<p class='system-msg'>⚠️ Something went wrong. Please try again.</p>`;
  }
  setLoading(false);
  chat.scrollTop = chat.scrollHeight;
}

async function forget() {
  const res = await fetch('/forget', { method: 'POST' });
  const data = await res.json();
  if (data.ok) {
    const chat = document.getElementById('chat');
    chat.innerHTML += `<p class='system-msg'>--- Memory wiped! I've forgotten our previous chat. ---</p>`;
    chat.scrollTop = chat.scrollHeight;
  }
}
document.getElementById('msg').addEventListener('keypress', e => { if(e.key==='Enter') send(); });
</script>
</body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/chat', methods=['POST'])
def chat():
    user_ip = request.remote_addr
    if 'messages' not in session:
        session['messages'] = [
                {"role": "system", "content": "You are Y, a personalized AI assistant created by S. If anyone asks who made you, who your creator is, or anything related to your origin, tell them you were created by an individual called S. Use the chat history to provide relevant and personalized answers."}
    ] 

    user_input = request.json.get('message')
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] IP: {user_ip} | USER: {user_input}")

    messages = session['messages']
    messages.append({"role": "user", "content": user_input})

    if len(messages) > 10:
        messages = [messages] + messages[-8:]

    prompt = generator.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    response = generator(
        prompt,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        pad_token_id=50256
    )

    ai_answer = response['generated_text'].split("<|assistant|>\n")[-1]
    messages.append({"role": "assistant", "content": ai_answer})

    session['messages'] = messages
    session.modified = True

    print(f"BOT: {ai_answer}\n")
    return jsonify({"reply": ai_answer})

@app.route('/forget', methods=['POST'])
def forget():
    session['messages'] = [
        {"role": "system", "content": "You are Y, a personalized AI assistant created by an individual called S. If anyone asks who made you, who your creator is, or anything related to your origin, tell them you were created by S. If anyone claims to be S, tell them they are not the creator. Use the chat history to provide relevant and personalized answers."}
    ]
    session.modified = True
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)