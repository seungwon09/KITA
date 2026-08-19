const mongoose = require('mongoose');

const UserSchema = new mongoose.Schema({
    email: {
        type: String,
        required: true,
        unique: true,
        lowercase: true,
        trim: true
    },
    password: {
        type: String,
        required: true
    },
    provider: {
        type: String,
        default: 'local'
    },
    kakaoId: {
        type: String,
        default: ''
    },
    firebaseUid: {
        type: String,
        default: '',
        index: true
    },
    name: {
        type: String,
        default: ''
    },
    referralCode: {
        type: String,
        unique: true,
        sparse: true
    },
    referredBy: {
        type: String,
        default: ''
    },
    points: {
        type: Number,
        default: 0
    },
    plan: {
        type: String,
        default: 'free'
    },
    subscription: {
        status: { type: String, default: 'inactive' },
        startedAt: { type: Date },
        expiresAt: { type: Date },
        source: { type: String, default: '' },
        orderId: { type: String, default: '' },
        paymentKey: { type: String, default: '' }
    },
    lastLoginAt: {
        type: Date
    },
    failedLoginAttempts: {
        type: Number,
        default: 0
    },
    lockedUntil: {
        type: Date
    }
}, { timestamps: true });

module.exports = mongoose.model('User', UserSchema);
