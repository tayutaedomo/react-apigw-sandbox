// 実環境の URL は実行時に渡す。ブラウザーと HTTP テストで同じ接続先を使う。
export const apiBaseUrl = (process.env.AWS_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export const frontendOrigin = process.env.HOSTING_BASE_URL || 'http://localhost:5173';
export const helloUrl = `${apiBaseUrl}/hello`;
