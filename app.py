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


@app.route('/api/radar-scores', methods=['POST'])
def radar_scores():
    """
    レーダーチャート用: 各性格軸について、DBに蓄積された Score と
    今回セッションの回答を照らし、1〜5の値を返す。

    各設問では「その設問×性格」の全世界の A/B 集計に対し、
    ユーザーが選んだ側が占める割合を [0,1] とみなし、
    セッション内で平均して 1 + 4*平均 で 1〜5 に線形マップする。
    """
    data = request.json or {}
    answers = data.get('answers') or []
    req_personality_ids = data.get('personality_ids') or []

    if req_personality_ids:
        personality_ids = [int(x) for x in req_personality_ids[:5]]
    else:
        personality_ids = [p.id for p in Personality.query.order_by(Personality.id).limit(5).all()]

    out = []
    for pid in personality_ids:
        p = Personality.query.get(pid)
        if not p:
            continue
        ratios = []
        for ans in answers:
            qid = ans.get('question_id')
            choice = ans.get('choice')
            p_ids = ans.get('personality_ids') or []
            if p_ids and pid not in p_ids:
                continue
            if qid is None or choice not in ('A', 'B'):
                continue
            sa = Score.query.filter_by(
                question_id=qid, personality_id=pid, option='A'
            ).first()
            sb = Score.query.filter_by(
                question_id=qid, personality_id=pid, option='B'
            ).first()
            ca = sa.count if sa else 0
            cb = sb.count if sb else 0
            total = ca + cb
            if total == 0:
                continue
            if choice == 'A':
                ratios.append(ca / total)
            else:
                ratios.append(cb / total)

        if not ratios:
            value = 3.0
        else:
            avg = sum(ratios) / len(ratios)
            value = 1 + 4 * avg

        out.append({
            'id': p.id,
            'name': p.name,
            'label': p.label,
            'value': round(value, 1),
        })

    return jsonify(out)


if __name__ == '__main__':
    app.run(debug=True)