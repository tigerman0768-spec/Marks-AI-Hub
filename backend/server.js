'use strict';

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const { rateLimit } = require('express-rate-limit');
const { registerVideoGenerationRoutes } = require('./video_generation_routes');

const app = express();
const port = Number(process.env.PORT) || 3000;

app.disable('x-powered-by');
app.set('trust proxy', 1);
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN ? process.env.CORS_ORIGIN.split(',').map(x => x.trim()).filter(Boolean) : true }));
app.use(express.json({ limit: '1mb', strict: true }));

// Bound billable generation submissions. Status polling uses its own generous
// limit so a film can wait for the provider without consuming the generation quota.
app.use('/api/video/generate', rateLimit({
  windowMs: 60 * 60 * 1000,
  limit: 12,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: { error: 'Too many video generation requests. Please wait before starting more clips.' }
}));
app.use('/api/video/status', rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 360,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: { error: 'Too many status checks. Please wait briefly and retry.' }
}));

app.get('/', (_req, res) => res.status(200).json({
  name: "Mark's AI Video Backend",
  ok: true,
  health: '/api/video/health',
  generation: '/api/video/generate'
}));

registerVideoGenerationRoutes(app);

app.use((error, _req, res, _next) => {
  console.error('[server]', error && error.message ? error.message : error);
  const status = error && Number.isInteger(error.status) && error.status >= 400 && error.status < 600 ? error.status : 400;
  res.status(status).json({ error: status === 413 ? 'Request body is too large.' : 'Request could not be processed.' });
});

app.listen(port, '0.0.0.0', () => {
  console.log("Mark's AI video backend listening on port " + port);
  console.log('Provider secret configured:', Boolean(String(process.env.RUNWAYML_API_SECRET || '').trim()));
});
