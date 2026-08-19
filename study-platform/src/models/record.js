const mongoose = require('mongoose');

const RecordSchema = new mongoose.Schema({
    userEmail: {
        type: String,
        required: true
    },

    questionId: {
        type: String,
        required: true
    },

    userAnswer: {
        type: String,
        required: true
    },

    correct: {
        type: Boolean,
        required: true
    },

    solveTime: {
        type: Number,
        default: 0
    },

    createdAt: {
        type: Date,
        default: Date.now
    }
});

module.exports = mongoose.model('Record', RecordSchema);