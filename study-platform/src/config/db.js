const mongoose = require('mongoose');

module.exports = async function connectDB() {
    try {
        if (!process.env.MONGO_URI) {
            console.warn('MONGO_URI가 없어 DB 없이 실행합니다.');
            return false;
        }
        await mongoose.connect(process.env.MONGO_URI, { serverSelectionTimeoutMS: 3000 });
        console.log('MongoDB connected');
        return true;
    } catch (err) {
        console.warn('MongoDB 연결 실패. AI 기능은 계속 실행하지만 계정 기능은 제한됩니다.');
        console.warn(err.message);
        return false;
    }
};
