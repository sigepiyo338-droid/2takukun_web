let currentQuestions = []; 
let currentIndex = 0;      
let sessionAnswers = [];   

// 画面切り替え
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
    const target = document.getElementById(sectionId);
    if (target) target.classList.remove('hidden');
}

// 診断開始
async function startDiagnosis() {
    const count = document.querySelector('input[name="q-count"]:checked').value;
    const response = await fetch(`/api/questions?count=${count}`);
    currentQuestions = await response.json();
    
    if (currentQuestions.length === 0) {
        alert("問題がまだ登録されていないようです。各種投稿から追加してください！");
        return;
    }
    currentIndex = 0;
    sessionAnswers = [];
    showNextQuestion();
}

// 問題の表示
function showNextQuestion() {
    if (currentIndex >= currentQuestions.length) {
        showFinalResult();
        return;
    }
    const q = currentQuestions[currentIndex];
    document.getElementById('q-text').innerText = q.text;
    document.getElementById('btn-a').innerText = q.option_a;
    document.getElementById('btn-b').innerText = q.option_b;
    document.getElementById('q-author').innerText = `投稿者: ${q.author}`;
    document.getElementById('q-number').innerText = `${currentIndex + 1} / ${currentQuestions.length}`;
    showSection('diagnosis-page');
}

// 回答の送信
async function selectOption(choice) {
    const q = currentQuestions[currentIndex];
    const pIds = Array.from(document.querySelectorAll('#personality-list input:checked'))
                      .map(cb => parseInt(cb.value));

    // APIから結果を取得
    const response = await fetch('/api/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: q.id, choice: choice, personality_ids: pIds })
    });
    const result = await response.json();

    // 演出を挟まず、即座に結果を保存して次の問題へ
    const isMajority = (choice === 'A' && result.percent_a >= 50) || (choice === 'B' && result.percent_b >= 50);
    
    sessionAnswers.push({
        question_id: q.id,
        choice_letter: choice,
        personality_ids: pIds,
        question: q.text,
        choice: choice === 'A' ? q.option_a : q.option_b,
        percent: choice === 'A' ? result.percent_a : result.percent_b,
        type: isMajority ? "多数派" : "少数派"
    });
    
    currentIndex++;
    showNextQuestion();
}

// 結果表示とチャート
function showFinalResult() {
    showSection('result-page');
    const list = document.getElementById('result-list');
    list.innerHTML = "";
    let majorityCount = 0;

    sessionAnswers.forEach(ans => {
        if (ans.type === "多数派") majorityCount++;
        const li = document.createElement('li');
        li.innerHTML = `<strong>${ans.question}</strong><br>選んだ: ${ans.choice} (${ans.percent}%) - <span class="${ans.type}">${ans.type}</span>`;
        list.appendChild(li);
    });
    document.getElementById('total-result').innerText = `あなたは合計で ${majorityCount}回 多数派でした！`;
    drawRadarChart();
}

// レーダーチャート表示（DBの Score 蓄積とセッション回答から算出）
async function drawRadarChart() {
    const ctx = document.getElementById('resultChart').getContext('2d');
    if (window.myRadarChart) window.myRadarChart.destroy();

    if (!sessionAnswers.length) return;

    try {
        const checked = Array.from(
            document.querySelectorAll('#personality-list input:checked')
        ).map((cb) => parseInt(cb.value, 10));

        const res = await fetch('/api/radar-scores', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                personality_ids: checked,
                answers: sessionAnswers.map((a) => ({
                    question_id: a.question_id,
                    choice: a.choice_letter,
                    personality_ids: a.personality_ids
                }))
            })
        });
        if (!res.ok) return;

        const series = await res.json();
        if (!series || series.length === 0) return;

        window.myRadarChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: series.map((s) => s.label || s.name),
                datasets: [{
                    label: '価値観分析（蓄積データ反映）',
                    data: series.map((s) => s.value),
                    backgroundColor: 'rgba(52, 152, 219, 0.2)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                scales: { r: { min: 0, max: 5, ticks: { stepSize: 1 } } },
                plugins: { legend: { display: false } }
            }
        });
    } catch (e) { console.error(e); }
}

// ユーザー投稿機能
async function submitPost() {
    const text = document.getElementById('new-q-text').value.trim();
    const a = document.getElementById('new-q-a').value.trim();
    const b = document.getElementById('new-q-b').value.trim();
    const author = document.getElementById('new-q-author').value.trim();

    if (!text || !a || !b) return alert("必須項目を入力してください。");

    await fetch('/api/post/question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, option_a: a, option_b: b, author })
    });
    alert("投稿しました！");
    location.reload(); 
}

/** 新しい性格軸（診断項目）の追加 */
async function addUserPersonality() {
    const name = document.getElementById('user-p-name').value.trim();
    const label = document.getElementById('user-p-label').value.trim();

    // 入力バリデーションの追加：空欄の場合は中断
    if (!name || !label) return alert("必須項目を入力してください。");

    const res = await fetch('/api/post/personality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, label })
    });
    if (res.ok) {
        alert("新しい性格軸を追加しました！");
        location.reload(); 
    }
}

// --- X 連携機能 ---
function shareOnX() {
    if (sessionAnswers.length === 0) return;

    // 1. ランダムな質問の選出
    const randomEntry = sessionAnswers[Math.floor(Math.random() * sessionAnswers.length)];
    const highlight = `${randomEntry.question}......${randomEntry.choice} ！？`;

    // 2. 統計データの取得
    const majorityCount = sessionAnswers.filter(ans => ans.type === "多数派").length;
    const totalCount = sessionAnswers.length;
    const username = document.getElementById('username').value || "名無し";
    
    // 3. ハッシュタグとURLの準備
    const tags = "#プログラミング初心者 #心理テスト #性格診断 #究極の二択";
    const url = window.location.href; 
    
    // 4. 文章の組み立て (URLを上、ハッシュタグを一番下に配置)
    const text = `【究極二択くん】\n${highlight}\n${username}さんは ${totalCount}問中 ${majorityCount}回 多数派でした！\n\n${url}\n${tags}`;
    
    // 𝕏 の投稿画面を開く（textの中にURLを含めたので、urlパラメータは空にします）
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
}