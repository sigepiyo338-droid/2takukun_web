from flask import Flask, render_template, request, jsonify
from models import db, Question, Personality, Answer, Score
import random
import os

app = Flask(__name__)

# --- データベース設定 ---
# PythonAnywhereでは絶対パスを使うのが最も安全です
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# --- データベースの初期設定 ---
with app.app_context():
    db.create_all()
    if not Personality.query.first():
        sample_ps = [
            Personality(name="慎重", label="慎重度"),
            Personality(name="大胆", label="大胆度"),
            Personality(name="合理的", label="論理度"),
            Personality(name="情熱的", label="パッション度"),
            Personality(name="個人主義", label="独立度")
        ]
        db.session.bulk_save_objects(sample_ps)
        q1 = Question(text="一生、夏しか来ないのと、冬しか来ないの、どっちがいい？", option_a="一生、夏", option_b="一生、冬", author="運営")
        db.session.add(q1)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/personalities', methods=['GET'])
def get_personalities():
    ps = Personality.query.all()
    return jsonify([{"id": p.id, "name": p.name, "label": p.label} for p in ps])

@app.route('/api/questions', methods=['GET'])
def get_questions():
    count = request.args.get('count', default=10, type=int)
    all_qs = Question.query.all()
    sample_size = min(len(all_qs), count)
    selected_qs = random.sample(all_qs, sample_size)
    return jsonify([{
        "id": q.id, 
        "text": q.text, 
        "option_a": q.option_a, 
        "option_b": q.option_b, 
        "author": q.author
    } for q in selected_qs])

@app.route('/api/post/question', methods=['POST'])
def post_question():
    data = request.json
    if not data.get('text') or not data.get('option_a') or not data.get('option_b'):
        return jsonify({"status": "error", "message": "未入力の項目があります"}), 400
    new_q = Question(
        text=data['text'],
        option_a=data['option_a'],
        option_b=data['option_b'],
        author=data.get('author', '名無し')
    )
    db.session.add(new_q)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/post/personality', methods=['POST'])
def post_personality():
    data = request.json
    name = data.get('name', '').strip()
    label = data.get('label', '').strip()
    if not name or not label:
        return jsonify({"status": "error", "message": "入力が不足しています"}), 400
    db.session.add(Personality(name=name, label=label))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/answer', methods=['POST'])
def submit_answer():
    data = request.json
    q_id, choice, p_ids = data.get('question_id'), data.get('choice'), data.get('personality_ids')
    db.session.add(Answer(question_id=q_id, choice=choice))
    for p_id in p_ids:
        score = Score.query.filter_by(question_id=q_id, option=choice, personality_id=p_id).first()
        if score:
            score.count += 1
        else:
            db.session.add(Score(question_id=q_id, option=choice, personality_id=p_id, count=1))
    db.session.commit()
    total_a = Answer.query.filter_by(question_id=q_id, choice='A').count()
    total_b = Answer.query.filter_by(question_id=q_id, choice='B').count()
    total = total_a + total_b
    return jsonify({
        "percent_a": round((total_a/total)*100, 1) if total>0 else 50,
        "percent_b": round((total_b/total)*100, 1) if total>0 else 50,
        "your_choice": choice
    })

if __name__ == '__main__':
    app.run(debug=True)