const express = require('express');
const nodemailer = require('nodemailer');
const cors = require('cors');
const { auth } = require('express-oauth2-jwt-bearer');
const fetch = require('node-fetch');

const app = express();
const PORT = 3000;

// Configure Auth0 middleware
const jwtCheck = auth({
  audience: 'https://toxmas.us.auth0.com/api/v2/',
  issuerBaseURL: 'https://toxmas.us.auth0.com/',
  tokenSigningAlg: 'RS256'
});

// Store active sessions and their last ping time
const activeSessions = new Map();

// Email configuration
const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: 'kvhkc2332@gmail.com',
    pass: 'xioi npbc xhqt nfhu'
  }
});

app.use(cors());
app.use(express.json());

// Endpoint to receive pings
app.post('/ping', jwtCheck, (req, res) => {
  const { sessionId, parentEmail } = req.body;
  activeSessions.set(sessionId, {
    lastPing: Date.now(),
    parentEmail
  });
  res.sendStatus(200);
});

// Check for missed pings every 10 seconds
setInterval(() => {
  const now = Date.now();
  activeSessions.forEach((session, sessionId) => {
    if (now - session.lastPing > 7000) { // 7 seconds threshold
      sendAlertEmail(session.parentEmail);
      activeSessions.delete(sessionId);
    }
  });
}, 10000);

function sendAlertEmail(parentEmail) {
  const mailOptions = {
    from: 'your-email@gmail.com',
    to: parentEmail,
    subject: '⚠️ Important: Browser Safety Alert',
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #e63946;">Browser Safety Alert</h2>
        <p style="color: #1d3557; font-size: 16px;">
          Dear Parent,
        </p>
        <p style="color: #1d3557; font-size: 16px;">
          We've detected that the Toxmas Parental Control protection may have been disabled on your child's browser. 
          This could potentially expose them to inappropriate content.
        </p>
        <div style="background-color: #f1faee; padding: 15px; border-left: 4px solid #e63946; margin: 20px 0;">
          <p style="margin: 0; color: #1d3557;">
            Please check your child's browser settings to ensure the Toxmas Parental Control extension is properly enabled.
          </p>
        </div>
        <p style="color: #1d3557; font-size: 16px;">
          If you need assistance, please don't hesitate to contact our support team.
        </p>
        <hr style="border: 1px solid #a8dadc; margin: 20px 0;">
        <p style="color: #457b9d; font-size: 14px;">
          This is an automated security alert. Please do not reply to this email.
        </p>
      </div>
    `
  };

  transporter.sendMail(mailOptions);
}

app.post('/login', async (req, res) => {
  const { email, password, client_id, client_secret } = req.body;
  
  try {
    const auth0Response = await fetch('https://toxmas.us.auth0.com/oauth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        grant_type: 'password',
        username: email,
        password: password,
        audience: 'https://toxmas.us.auth0.com/api/v2/',
        scope: 'openid profile email',
        client_id,
        client_secret
      })
    });

    const data = await auth0Response.json();
    res.json(data);
  } catch (error) {
    console.error('Auth0 error:', error);
    res.status(500).json({ error: 'Authentication failed' });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
}); 