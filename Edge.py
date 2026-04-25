import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string, redirect, session
from transformers import pipeline

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Secret config
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
PASSWORD = os.getenv("APP_PASSWORD", "676767")

# Load TinyLlama model
print("\nLoading TinyLlama... (first run may take time)")
generator = pipeline(
    "text-generation",
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    device_map="auto"
)

print("\n--- TinyLlama Web Chatbot Activated! ---")

# Auth middleware
@app.before_request
def check_auth():
    if request.path == '/login' or request.path.startswith('/static'):
        return None
        
    if not session.get('logged_in'):
        return redirect('/login')


# Login page
LOGIN_HTML = """
<html>
<body style="font-family:sans-serif;max-width:300px;margin:auto;padding-top:100px">
<h2>Enter Password</h2>
<input id="pw" type="password" placeholder="Password" />
<button onclick="login()">Enter</button>

<script>
async function login() {
  const res = await fetch('/login', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({password:document.getElementById('pw').value})
  });

  if ((await res.json()).ok) location.href='/';
  else alert('Wrong password!');
}
</script>
</body>
</html>
"""


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        pw = request.json.get('password')

        if pw == PASSWORD:
            session['logged_in'] = True
            return jsonify({"ok":True})

        return jsonify({"ok":False}), 401

    return render_template_string(LOGIN_HTML)


# Main UI
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Local AI Assistant</title>

<style>
body { font-family:sans-serif; max-width:600px; margin:auto; padding:1rem; }
#chat { height:400px; overflow-y:auto; border:1px solid #ccc; padding:1rem; margin-bottom:1rem; }
input { width:70%; padding:0.5rem; }
button { padding:0.5rem 1rem; }

.user { color:blue; margin:8px 0; }
.bot { color:green; margin:8px 0; }

.system-msg {
color:gray;
font-style:italic;
text-align:center;
}
</style>
</head>

<body>

<h2>Local AI Assistant</h2>

<div id="chat"></div>

<input id="msg" type="text" placeholder="Type a message..." />

<button onclick="send()">Send</button>

<button onclick="forget()">Forget 🧠</button>

<script>

async function send(){

const msg=document.getElementById('msg').value;

if(!msg) return;

const chat=document.getElementById('chat');

chat.innerHTML+=`<p class='user'>You: ${msg}</p>`;

document.getElementById('msg').value='';

const res=await fetch('/chat',{
method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({message:msg})
});

const data=await res.json();

chat.innerHTML+=`<p class='bot'>Bot: ${data.reply}</p>`;

chat.scrollTop=chat.scrollHeight;
}


async function forget(){

const res=await fetch('/forget',{method:'POST'});

const data=await res.json();

if(data.ok){

const chat=document.getElementById('chat');

chat.innerHTML+=`<p class='system-msg'>Memory cleared.</p>`;
}
}

</script>

</body>
</html>
"""


@app.route('/')
def home():
    return render_template_string(HTML)


@app.route('/chat', methods=['POST'])
def chat():

    if 'messages' not in session:
        session['messages']=[
            {
                "role":"system",
                "content":"You are a helpful private local AI assistant."
            }
        ]

    user_input=request.json.get('message')

    print(f"[{datetime.now()}] USER:", user_input)

    messages=session['messages']

    messages.append({
        "role":"user",
        "content":user_input
    })

    prompt=generator.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    response=generator(
        prompt,
        max_new_tokens=256,
        temperature=0.7
    )

    ai_answer=response[0]['generated_text'].split("<|assistant|>")[-1]

    messages.append({
        "role":"assistant",
        "content":ai_answer
    })

    session['messages']=messages

    session.modified=True

    return jsonify({"reply":ai_answer})


@app.route('/forget', methods=['POST'])
def forget():

    session['messages']=[
        {
            "role":"system",
            "content":"You are a helpful private local AI assistant."
        }
    ]

    session.modified=True

    return jsonify({"ok":True})


if __name__=="__main__":
    app.run(host="0.0.0.0", port=5050)