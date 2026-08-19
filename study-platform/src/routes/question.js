const express = require('express');

const Question = require('../models/question');
const Record = require('../models/record');
const auth = require('../middleware/auth');

const router = express.Router();
const demoQuestions = [
    {
        _id: 'demo-math-1',
        subject: 'math',
        topic: '이차함수',
        difficulty: 2,
        question: '이차함수 y=x^2-4x+1의 최솟값을 구하시오.',
        options: ['-4', '-3', '2', '3'],
        answer: '-3',
        explanation: '꼭짓점의 x좌표는 -b/(2a)=2이고, x=2를 대입하면 y=-3입니다.'
    },
    {
        _id: 'demo-science-1',
        subject: 'science',
        topic: '전기',
        difficulty: 2,
        question: '저항 4Ω에 전류 3A가 흐를 때 전압과 전력은?',
        options: ['12V, 36W', '7V, 12W', '4V, 3W', '3V, 4W'],
        answer: '12V, 36W',
        explanation: 'V=IR=12V, P=VI=36W입니다.'
    }
];

function demoQuestion(subject) {
    return demoQuestions.find(item => !subject || item.subject === subject) || demoQuestions[0];
}

router.post('/add', auth, async (req, res) => {
    try {
        const question = new Question({ ...req.body, topic: req.body.topic || req.body.unit || '기본' });
        await question.save();
        res.json({ ok: true, msg: '문제 저장 완료', question });
    } catch (err) {
        res.status(500).json({ ok: false, msg: '문제 저장 실패', error: err.message });
    }
});
router.get('/list', async (req, res) => {
    try {
        const filter = {};
        if (req.query.subject) filter.subject = req.query.subject;
        if (req.query.difficulty) filter.difficulty = Number(req.query.difficulty);
        const questions = await Question.find(filter).sort({ _id: -1 }).limit(100);
        res.json(questions.length ? questions : demoQuestions.filter(item => !req.query.subject || item.subject === req.query.subject));
    } catch (err) {
        res.json(demoQuestions);
    }
});
router.get('/random/one', async (req, res) => {
    try {
        const filter = {};
        if (req.query.subject) filter.subject = req.query.subject;
        if (req.query.difficulty) filter.difficulty = Number(req.query.difficulty);
        const count = await Question.countDocuments(filter);
        if (!count) return res.json(demoQuestion(req.query.subject));
        res.json(await Question.findOne(filter).skip(Math.floor(Math.random() * count)) || demoQuestion(req.query.subject));
    } catch (err) {
        res.json(demoQuestion(req.query.subject));
    }
});
router.post('/solve', auth, async (req, res) => {
    try {
        const { id, answer, solveTime } = req.body;
        const question = String(id || '').startsWith('demo-') ? demoQuestions.find(item => item._id === id) : await Question.findById(id);
        if (!question) return res.status(404).json({ msg: '문제를 찾지 못했습니다.' });
        const correct = String(question.answer).trim() === String(answer).trim();
        await Record.create({ userEmail: req.user.email, questionId: String(id), userAnswer: answer, correct, solveTime: solveTime || 0 });
        res.json({ correct, correctAnswer: question.answer, explanation: question.explanation });
    } catch (err) {
        res.status(500).json({ msg: '채점 중 오류가 발생했습니다.', error: err.message });
    }
});
router.get('/stats', auth, async (req, res) => {
    try {
        const records = await Record.find({ userEmail: req.user.email });
        const total = records.length;
        const correct = records.filter(record => record.correct).length;
        const totalTime = records.reduce((sum, record) => sum + (record.solveTime || 0), 0);
        const times = records.map(record => record.solveTime).filter(time => time > 0);
        res.json({ total, correct, wrong: total - correct, accuracy: total ? correct / total * 100 : 0, totalTime, averageTime: total ? totalTime / total : 0, fastestTime: times.length ? Math.min(...times) : 0 });
    } catch (err) {
        res.status(500).json({ msg: '통계를 불러오지 못했습니다.', error: err.message });
    }
});
router.get('/wrong', auth, async (req, res) => {
    try {
        res.json(await Record.find({ userEmail: req.user.email, correct: false }).sort({ createdAt: -1 }));
    } catch (err) {
        res.status(500).json({ msg: '오답노트를 불러오지 못했습니다.', error: err.message });
    }
});
router.get('/:id', async (req, res) => {
    try {
        const question = String(req.params.id).startsWith('demo-') ? demoQuestions.find(item => item._id === req.params.id) : await Question.findById(req.params.id);
        if (!question) return res.status(404).json({ msg: '문제를 찾지 못했습니다.' });
        res.json(question);
    } catch (err) {
        res.status(500).json({ msg: '문제를 불러오지 못했습니다.', error: err.message });
    }
});
router.delete('/:id', auth, async (req, res) => {
    try {
        await Question.findByIdAndDelete(req.params.id);
        res.json({ ok: true, msg: '삭제 완료' });
    } catch (err) {
        res.status(500).json({ msg: '삭제에 실패했습니다.', error: err.message });
    }
});

module.exports = router;
