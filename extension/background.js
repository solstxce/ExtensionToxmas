let sessionId = crypto.randomUUID();
let parentEmail = null;
let accessToken = null;
let isParentMode = false;
let extensionStatus = 'enabled';
let blockList = new Set(); // Store blocked domains

// Function to convert filter rule to match pattern
function convertFilterToPattern(filter) {
    // Remove the filter syntax
    if (filter.startsWith('||')) {
        filter = filter.slice(2);
    }
    // Remove the ending syntax
    if (filter.endsWith('^')) {
        filter = filter.slice(0, -1);
    }
    return filter;
}

// Load the block list
fetch(chrome.runtime.getURL('oisd_nsfw_abp.txt'))
    .then(response => response.text())
    .then(text => {
        // Process each line
        text.split('\n').forEach(line => {
            line = line.trim();
            // Only process filter rules (not comments or empty lines)
            if (line && !line.startsWith('!') && !line.startsWith('[')) {
                blockList.add(convertFilterToPattern(line));
            }
        });
        console.log('Loaded block list with', blockList.size, 'entries');
    })
    .catch(error => console.error('Error loading block list:', error));

// Function to check if URL should be blocked
function shouldBlockUrl(url) {
    try {
        const hostname = new URL(url).hostname;
        return blockList.has(hostname);
    } catch (e) {
        console.error('Error parsing URL:', e);
        return false;
    }
}

// Block both chrome URLs and NSFW content
chrome.webNavigation.onBeforeNavigate.addListener(
    function(details) {
        // Only process if extension is enabled and not in parent mode
        if (extensionStatus !== 'enabled' || isParentMode) return;

        // Block chrome:// URLs except newtab
        if (details.url.startsWith('chrome://') && 
            !details.url.startsWith('chrome://newtab') && 
            !details.url.startsWith('chrome://new-tab-page')) {
            chrome.tabs.update(details.tabId, {
                url: chrome.runtime.getURL('blocked.html')
            });
            return;
        }

        // Check against NSFW block list
        if (shouldBlockUrl(details.url)) {
            console.log('Blocking NSFW URL:', details.url);
            chrome.tabs.update(details.tabId, {
                url: chrome.runtime.getURL('blocked.html')
            });
        }
    }
);

// Send ping every 5 seconds when enabled
function sendPing() {
  if (sessionId && parentEmail && accessToken && extensionStatus === 'enabled') {
    fetch('http://127.0.0.1:3000/ping', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        sessionId,
        parentEmail
      })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data && data.status && data.status !== extensionStatus) {
        extensionStatus = data.status;
      }
    })
    .catch(error => {
      console.error('Ping failed:', error);
      // Optionally handle failed pings (e.g., retry logic or status updates)
    });
  }
}

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  try {
    if (message.type === 'getSessionId') {
      sendResponse(sessionId);
    } else if (message.type === 'statusChanged') {
      extensionStatus = message.status;
      sendResponse({ success: true });
    } else {
      sendResponse({ error: 'Unknown message type' });
    }
  } catch (error) {
    console.error('Message handling error:', error);
    sendResponse({ error: error.message });
  }
  return true; // Keep the message channel open for async response
});

setInterval(sendPing, 5000);

// Listen for auth status changes
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (changes.accessToken) {
    accessToken = changes.accessToken.newValue;
  }
  if (changes.parentEmail) {
    parentEmail = changes.parentEmail.newValue;
  }
  if (changes.isParentMode) {
    isParentMode = changes.isParentMode.newValue;
  }
});

// Initialize state from storage
chrome.storage.local.get(['accessToken', 'parentEmail', 'isParentMode'], (result) => {
  accessToken = result.accessToken;
  parentEmail = result.parentEmail;
  isParentMode = result.isParentMode || false;
});

// Handle cleanup on extension update/reload
chrome.runtime.onStartup.addListener(() => {
  chrome.storage.local.set({ isParentMode: false });
  extensionStatus = 'enabled';
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ isParentMode: false });
  extensionStatus = 'enabled';
});

// Handle extension unload
chrome.runtime.onSuspend.addListener(async () => {
  if (sessionId && parentEmail && accessToken) {
    try {
      await fetch('http://127.0.0.1:3000/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        }
      });
      chrome.storage.local.set({ isParentMode: false });
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }
}); 