// Netlify Function: CryptoBot Webhook Handler
// - Verifies HMAC signature from CryptoBot (header: X-Crypto-Pay-API-Signature)
// - Optionally confirms invoice status via CryptoBot API
// - On paid, can notify a Telegram admin (no local DB persistence on Netlify)

const crypto = require('crypto');

// Environment variables expected to be set in Netlify dashboard or via CLI:
// - WEBHOOK_SECRET: HMAC secret shared with CryptoBot
// - CRYPTOBOT_TOKEN: API token for https://pay.crypt.bot/api
// - BOT_TOKEN: Telegram bot token (optional, for admin notifications)
// - ADMIN_ID: Telegram user/chat id to notify (optional)

const CRYPTOBOT_API_URL = 'https://pay.crypt.bot/api';

function verifySignature(rawBody, signatureHex, secret) {
  if (!secret) return true; // allow if not configured, mirrors existing behavior
  const hmac = crypto.createHmac('sha256', Buffer.from(secret, 'utf8'));
  hmac.update(Buffer.from(rawBody, 'utf8'));
  const digest = hmac.digest('hex');
  const sigBuf = Buffer.from(signatureHex || '', 'utf8');
  const digBuf = Buffer.from(digest, 'utf8');
  if (sigBuf.length !== digBuf.length) return false;
  return crypto.timingSafeEqual(sigBuf, digBuf);
}

async function getInvoiceStatus(invoiceId, token) {
  try {
    const res = await fetch(`${CRYPTOBOT_API_URL}/getInvoice`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Crypto-Pay-API-Token': token,
      },
      body: JSON.stringify({ invoice_id: invoiceId }),
    });
    if (!res.ok) return null;
    const json = await res.json();
    if (!json.ok) return null;
    return json.result?.status || null;
  } catch (err) {
    return null;
  }
}

async function notifyTelegramAdmin(message, botToken, adminId) {
  if (!botToken || !adminId) return;
  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  try {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: adminId, text: message }),
    });
  } catch (_) {
    // ignore notification errors
  }
}

async function forwardToBackend(rawBody, originalSignature, forwardUrl, relayToken) {
  if (!forwardUrl) return { ok: true, status: 204 };
  const headers = {
    'Content-Type': 'application/json',
    'X-Crypto-Pay-API-Signature': originalSignature || '',
    'X-Forwarded-By': 'netlify-cryptobot-webhook',
  };
  if (relayToken) headers['X-Relay-Token'] = relayToken;

  const res = await fetch(forwardUrl, {
    method: 'POST',
    headers,
    body: rawBody,
  });
  return { ok: res.ok, status: res.status, text: await res.text().catch(() => '') };
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  const rawBody = event.body || '';
  const signature = event.headers['x-crypto-pay-api-signature'] || event.headers['X-Crypto-Pay-API-Signature'] || '';

  const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || '';
  const CRYPTOBOT_TOKEN = process.env.CRYPTOBOT_TOKEN || '';
  const BOT_TOKEN = process.env.BOT_TOKEN || '';
  const ADMIN_ID = process.env.ADMIN_ID || '';
  const FORWARD_URL = process.env.FORWARD_URL || '';
  const RELAY_TOKEN = process.env.RELAY_TOKEN || '';

  // Verify signature first
  const isValid = verifySignature(rawBody, signature, WEBHOOK_SECRET);
  if (!isValid) {
    return { statusCode: 401, body: 'Invalid signature' };
  }

  let data;
  try {
    data = JSON.parse(rawBody);
  } catch (err) {
    return { statusCode: 400, body: 'Invalid JSON' };
  }

  const status = data?.status;
  const invoiceId = data?.invoice_id;
  if (!invoiceId) {
    return { statusCode: 400, body: 'Invoice ID not found' };
  }

  // Confirm invoice status with CryptoBot (best practice)
  if (!CRYPTOBOT_TOKEN) {
    return { statusCode: 500, body: 'Server not configured: CRYPTOBOT_TOKEN missing' };
  }

  const confirmedStatus = await getInvoiceStatus(invoiceId, CRYPTOBOT_TOKEN);
  if (!confirmedStatus) {
    return { statusCode: 400, body: 'Payment info not found' };
  }

  // Forward to user's backend with original body and signature (pass-through)
  const forwardRes = await forwardToBackend(rawBody, signature, FORWARD_URL, RELAY_TOKEN);

  // Optional admin notification (only on paid)
  if (status === 'paid' && confirmedStatus === 'paid') {
    await notifyTelegramAdmin(
      `✅ Payment received\nInvoice: ${invoiceId}\nAmount: ${data?.amount || ''} ${data?.currency || ''}`,
      BOT_TOKEN,
      ADMIN_ID
    );
  }

  if (!forwardRes.ok) {
    return { statusCode: 502, body: `Forward failed (${forwardRes.status}): ${forwardRes.text || ''}` };
  }

  return { statusCode: 200, body: 'Webhook processed and forwarded' };
};


