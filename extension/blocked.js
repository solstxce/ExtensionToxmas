function generateRandomIP() {
    const segments = [
        Math.floor(Math.random() * 223) + 1,
        Math.floor(Math.random() * 256),
        Math.floor(Math.random() * 256),
        Math.floor(Math.random() * 254) + 1
    ];
    return segments.join('.');
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function setCookie(name, value) {
    const date = new Date();
    date.setTime(date.getTime() + (30 * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${date.toUTCString()};path=/`;
}

function updateTimestamp() {
    document.getElementById('timestamp').textContent = new Date().toUTCString();
}

function initializeIP() {
    let clientIP = getCookie('client_ip');
    if (!clientIP) {
        clientIP = generateRandomIP();
        setCookie('client_ip', clientIP);
    }
    document.getElementById('client-ip').textContent = clientIP;
}

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    initializeIP();
    updateTimestamp();
}); 