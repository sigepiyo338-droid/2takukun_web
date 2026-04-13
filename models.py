from flask_sqlalchemy import SQLAlchemy

# データベース操作用のインスタンス
db = SQLAlchemy()

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    option_a = db.Column(db.String(100), nullable=False)
    option_b = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(50), default='ゲスト')
    # ↓ これを追加（質問を消すと関連データも消える魔法の呪文）
    answers = db.relationship('Answer', backref='question', cascade="all, delete-orphan")
    scores = db.relationship('Score', backref='question', cascade="all, delete-orphan")

class Personality(db.Model):
    """性格の定義テーブル"""
    __tablename__ = 'personalities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)      # 性格名 (例: 慎重)
    label = db.Column(db.String(50), nullable=False)     # 表示ラベル (例: 慎重度)

class Answer(db.Model):
    """純粋な回答集計テーブル (多数派・少数派の判定用)"""
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    choice = db.Column(db.String(1), nullable=False)     # 'A' または 'B'

class Score(db.Model):
    """
    【自己成長の核】
    どの問題のどの選択肢が、どの性格とどれだけ紐づいているかを記録
    """
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    personality_id = db.Column(db.Integer, db.ForeignKey('personalities.id'))
    option = db.Column(db.String(1)) # 'A' or 'B'
    count = db.Column(db.Integer, default=0) # 選択された回数