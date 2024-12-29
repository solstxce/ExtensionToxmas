let currentStatus = 'enabled';

// Function to fetch current status from server
async function fetchCurrentStatus() {
    try {
        const storage = await chrome.storage.local.get(['accessToken', 'parentEmail']);
        if (!storage.accessToken || !storage.parentEmail) return;

        const sessionId = await sendMessageToBackground({ type: 'getSessionId' });
        const response = await fetch('http://127.0.0.1:3000/ping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${storage.accessToken}`
            },
            body: JSON.stringify({
                sessionId,
                parentEmail: storage.parentEmail
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.status) {
                currentStatus = data.status;
                updateToggleButton();
                await sendMessageToBackground({ 
                    type: 'statusChanged', 
                    status: currentStatus 
                });
            }
        }
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

// Check login status and fetch current status when popup opens
chrome.storage.local.get(['accessToken', 'parentEmail'], async (result) => {
    if (result.accessToken && result.parentEmail) {
        showToggleInterface();
        await fetchCurrentStatus();
    }
});

document.getElementById('login').addEventListener('click', async () => {
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  try {
    const response = await fetch('http://127.0.0.1:3000/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email,
        password,
        client_id: 'dD6luveN6VjFHg12z11xWJI7NDs6Sei7',
        client_secret: '_D-EfNfhxpn_DtrhLtr2Axey7RvSJsnWZVuGFQbCSEUyR_qBCvYxxPzyEHg25X8r'
      })
    });

    const data = await response.json();
    if (data.access_token) {
      chrome.storage.local.set({
        accessToken: data.access_token,
        parentEmail: email,
        isParentMode: true
      });
      showToggleInterface();
    }
  } catch (error) {
    console.error('Authentication failed:', error);
  }
});

// Helper function for sending messages to background script
function sendMessageToBackground(message) {
    return new Promise((resolve, reject) => {
        try {
            chrome.runtime.sendMessage(message, response => {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve(response);
                }
            });
        } catch (error) {
            reject(error);
        }
    });
}

// Modified toggle button handler for immediate status update
document.getElementById('toggle').addEventListener('click', async () => {
    const newStatus = currentStatus === 'enabled' ? 'disabled' : 'enabled';
    const button = document.getElementById('toggle');
    
    // Disable button during status change
    button.disabled = true;
    
    try {
        const storage = await chrome.storage.local.get(['accessToken', 'parentEmail']);
        const sessionId = await sendMessageToBackground({ type: 'getSessionId' });
        
        // Immediately update UI and background status
        currentStatus = newStatus;
        updateToggleButton();
        await sendMessageToBackground({ 
            type: 'statusChanged', 
            status: currentStatus 
        });

        if (!response.ok || data.status !== newStatus) {
            // Revert if server update failed
            currentStatus = data.status || (newStatus === 'enabled' ? 'disabled' : 'enabled');
            updateToggleButton();
            await sendMessageToBackground({ 
                type: 'statusChanged', 
                status: currentStatus 
            });
        }
    } catch (error) {
        console.error('Toggle failed:', error);
        // Revert on error
        currentStatus = currentStatus === 'enabled' ? 'disabled' : 'enabled';
        updateToggleButton();
        await sendMessageToBackground({ 
            type: 'statusChanged', 
            status: currentStatus 
        });
    } finally {
        button.disabled = false;
    }
});

document.getElementById('logout').addEventListener('click', async () => {
  try {
    const sessionId = await sendMessageToBackground({ type: 'getSessionId' });
    const storage = await chrome.storage.local.get(['accessToken']);
    
    await fetch('http://127.0.0.1:3000/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${storage.accessToken}`
      },
      body: JSON.stringify({ sessionId })
    });

    await chrome.storage.local.clear();
    showLoginInterface();
  } catch (error) {
    console.error('Logout failed:', error);
  }
});

function showToggleInterface() {
  document.getElementById('login-container').style.display = 'none';
  document.getElementById('toggle-container').style.display = 'block';
}

function showLoginInterface() {
  document.getElementById('login-container').style.display = 'block';
  document.getElementById('toggle-container').style.display = 'none';
}

function updateToggleButton() {
  const button = document.getElementById('toggle');
  const statusText = document.querySelector('.status-text');
  const svg = button.querySelector('svg');
  
  if (currentStatus === 'enabled') {
    // Pause icon (two vertical bars)
    svg.innerHTML = '<path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>';
    button.classList.remove('disabled');
    statusText.textContent = 'Extension is Active';
  } else {
    // Play icon (triangle)
    svg.innerHTML = '<path d="M8 5v14l11-7z"/>';
    button.classList.add('disabled');
    statusText.textContent = 'Extension is Paused';
  }
} 