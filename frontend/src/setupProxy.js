/** Прокси dev-сервера: пересылает `/api` на Django (порт 8000 по умолчанию). */
const { createProxyMiddleware } = require('http-proxy-middleware');

const target = process.env.BACKEND_PROXY_TARGET || 'http://127.0.0.1:8000';

/** Настройка webpack-dev-server для CRA. */
module.exports = function setupProxy(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target,
      changeOrigin: true,
      secure: false,
    })
  );
};
