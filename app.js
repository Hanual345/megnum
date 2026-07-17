// Sidebar Toggle logic
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const menuBtn = document.getElementById('menuBtn');
const mainContent = document.getElementById('main');

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
let currentSessionId = localStorage.getItem('currentSessionId') || generateUUID();
localStorage.setItem('currentSessionId', currentSessionId);
let selectedModel = 'magma2';
let currentUser = { id: 'default_user', username: 'Guest', email: 'guest@volcano.ai' };

function toggleSidebar() {
  sidebar.classList.toggle('closed');
}

sidebarToggle.addEventListener('click', toggleSidebar);
menuBtn.addEventListener('click', toggleSidebar);

// Auto-adjusting Textarea Height & Input Actions
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

const attachBtn = document.getElementById('attachBtn');
const imageBtn = document.getElementById('imageBtn');
const documentInput = document.getElementById('documentInput');
const imageInputEl = document.getElementById('imageInputEl');
const filePreviewContainer = document.getElementById('filePreviewContainer');

let currentAttachment = null;

messageInput.addEventListener('input', () => {
  messageInput.style.height = 'auto';
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 200)}px`;
  
  if (messageInput.value.trim() !== '' || currentAttachment !== null) {
    sendBtn.removeAttribute('disabled');
  } else {
    sendBtn.setAttribute('disabled', 'true');
  }
});

// Attach file click triggers
attachBtn.addEventListener('click', () => documentInput.click());
imageBtn.addEventListener('click', () => imageInputEl.click());

documentInput.addEventListener('change', handleFileSelect);
imageInputEl.addEventListener('change', handleFileSelect);

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  
  if (file.type.startsWith('image/')) {
    reader.onload = function(event) {
      currentAttachment = {
        name: file.name,
        type: file.type,
        size: formatBytes(file.size),
        data: event.target.result
      };
      showFilePreview();
    };
    reader.readAsDataURL(file);
  } else {
    const isTextReadable = file.type.startsWith('text/') || 
                           file.name.endsWith('.json') || 
                           file.name.endsWith('.js') || 
                           file.name.endsWith('.css') || 
                           file.name.endsWith('.html') ||
                           file.name.endsWith('.csv');
    
    if (isTextReadable) {
      reader.onload = function(event) {
        currentAttachment = {
          name: file.name,
          type: file.type,
          size: formatBytes(file.size),
          content: event.target.result,
          data: null
        };
        showFilePreview();
      };
      reader.readAsText(file);
    } else {
      reader.onload = function(event) {
        currentAttachment = {
          name: file.name,
          type: file.type,
          size: formatBytes(file.size),
          data: event.target.result
        };
        showFilePreview();
      };
      reader.readAsDataURL(file);
    }
  }
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showFilePreview() {
  if (!currentAttachment) {
    filePreviewContainer.style.display = 'none';
    filePreviewContainer.innerHTML = '';
    return;
  }

  filePreviewContainer.style.display = 'flex';
  let previewHtml = '';

  if (currentAttachment.type.startsWith('image/')) {
    previewHtml = `
      <div class="file-preview-card">
        <img src="${currentAttachment.data}" class="file-preview-image" alt="preview" />
        <div class="file-preview-info">
          <span class="file-preview-name">${currentAttachment.name}</span>
          <span class="file-preview-size">${currentAttachment.size}</span>
        </div>
        <div class="file-preview-remove" onclick="removeAttachment()">✕</div>
      </div>
    `;
  } else {
    let icon = '📄';
    if (currentAttachment.name.endsWith('.pdf')) icon = '📕';
    if (currentAttachment.name.endsWith('.csv') || currentAttachment.name.endsWith('.xlsx')) icon = '📊';
    if (currentAttachment.name.endsWith('.json') || currentAttachment.name.endsWith('.js') || currentAttachment.name.endsWith('.html')) icon = '💻';
    
    previewHtml = `
      <div class="file-preview-card">
        <div class="file-preview-icon">${icon}</div>
        <div class="file-preview-info">
          <span class="file-preview-name">${currentAttachment.name}</span>
          <span class="file-preview-size">${currentAttachment.size}</span>
        </div>
        <div class="file-preview-remove" onclick="removeAttachment()">✕</div>
      </div>
    `;
  }

  filePreviewContainer.innerHTML = previewHtml;
  sendBtn.removeAttribute('disabled');
}

window.removeAttachment = function() {
  currentAttachment = null;
  documentInput.value = '';
  imageInputEl.value = '';
  showFilePreview();
  
  if (messageInput.value.trim() === '') {
    sendBtn.setAttribute('disabled', 'true');
  }
};

// Modals Trigger logic
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeSettings = document.getElementById('closeSettings');
const upgradeBtn = document.getElementById('upgradeBtn');
const upgradeModal = document.getElementById('upgradeModal');
const closeUpgrade = document.getElementById('closeUpgrade');

function openModal(modal) {
  modal.classList.add('open');
}

function closeModal(modal) {
  modal.classList.remove('open');
}

settingsBtn.addEventListener('click', () => openModal(settingsModal));
closeSettings.addEventListener('click', () => closeModal(settingsModal));
upgradeBtn.addEventListener('click', () => openModal(upgradeModal));
closeUpgrade.addEventListener('click', () => closeModal(upgradeModal));

// Close modal when clicking outside content area
[settingsModal, upgradeModal].forEach(modal => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeModal(modal);
    }
  });
});

// Model selection & theme toggling logic
const settingsOptions = document.querySelectorAll('input[name="model"]');
settingsOptions.forEach(radio => {
  if (radio.checked) {
    selectedModel = radio.value;
  }
  radio.addEventListener('change', (e) => {
    document.querySelectorAll('input[name="model"]').forEach(r => {
      r.closest('.settings-option').classList.remove('selected');
    });
    e.target.closest('.settings-option').classList.add('selected');
    selectedModel = e.target.value;
    
    // Update badge in topbar
    const modelBadgeName = document.querySelector('.model-badge span:last-child');
    if (e.target.value === 'magma2') {
      modelBadgeName.textContent = 'Fernace flash lite';
    } else if (e.target.value === 'magma-flash') {
      modelBadgeName.textContent = 'Fernace Flash';
    } else {
      modelBadgeName.textContent = 'Magma Ultra';
    }
  });
});

const themeOptions = document.querySelectorAll('input[name="theme"]');
themeOptions.forEach(radio => {
  radio.addEventListener('change', (e) => {
    document.querySelectorAll('input[name="theme"]').forEach(r => {
      r.closest('.settings-option').classList.remove('selected');
    });
    e.target.closest('.settings-option').classList.add('selected');
    
    if (e.target.value === 'light') {
      document.body.classList.add('light-mode');
    } else {
      document.body.classList.remove('light-mode');
    }
  });
});

// Deep Think and Web Search toggling
const deepThinkBtn = document.getElementById('deepThinkBtn');
const searchBtn = document.getElementById('searchBtn');

deepThinkBtn.addEventListener('click', () => {
  deepThinkBtn.classList.toggle('active-pill');
});

searchBtn.addEventListener('click', () => {
  searchBtn.classList.toggle('active-pill');
});

// Particle Ambient Emitter Background (Volcano Sparks Effect)
const canvas = document.getElementById('particleCanvas');
const ctx = canvas.getContext('2d');

let particles = [];

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

class EmberParticle {
  constructor() {
    this.reset();
    this.y = Math.random() * canvas.height; // initial distribute
  }
  
  reset() {
    this.x = Math.random() * canvas.width;
    this.y = canvas.height + Math.random() * 20;
    this.size = Math.random() * 2 + 1;
    this.speedY = -(Math.random() * 1.5 + 0.5);
    this.speedX = (Math.random() - 0.5) * 0.5;
    this.opacity = Math.random() * 0.5 + 0.2;
    this.color = Math.random() > 0.5 ? '#ff4d24' : '#ff8c3b';
  }
  
  update() {
    this.y += this.speedY;
    this.x += this.speedX;
    
    if (this.y < 0) {
      this.reset();
    }
  }
  
  draw() {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fillStyle = this.color;
    ctx.globalAlpha = this.opacity;
    ctx.fill();
  }
}

function initParticles() {
  const particleCount = Math.min(Math.floor(canvas.width / 20), 80);
  for (let i = 0; i < particleCount; i++) {
    particles.push(new EmberParticle());
  }
}

function animateParticles() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  particles.forEach(p => {
    p.update();
    p.draw();
  });
  requestAnimationFrame(animateParticles);
}

initParticles();
animateParticles();

// Simulation and response generation
const welcomeScreen = document.getElementById('welcomeScreen');
const messagesContainer = document.getElementById('messagesContainer');
const newChatBtn = document.getElementById('newChatBtn');

// Static mock responses database matching suggestions or general prompts
const mockResponses = {
  "Explain how a volcano forms and the science behind eruptions": `A volcano is formed when magma (hot liquid rock) from deep within the Earth's mantle rises to the surface. This happens because magma is lighter and less dense than the solid rock surrounding it.

Here is the step-by-step process:
1. **Magma Generation**: Intense heat and pressure melts rock in the mantle to form magma.
2. **Magma Chamber**: The magma gathers in chambers closer to the Earth's crust.
3. **Eruption Channel**: When the pressure builds up high enough, or tectonic plates move, the magma rises through vents or fractures in the Earth.
4. **Lava Flow**: Once it breaks through the surface, it is officially called **Lava**. As it cools down, it solidifies into volcanic rock, building the classic mountain shape over centuries.`,

  "Write a creative short story set near an active volcano with vivid descriptions": `The earth beneath Kael's boots hummed with a low, primeval vibration. High above, the crown of Mount Ignis glowed like a dying ember against the velvet night sky. Golden-orange rivers of molten stone crept lazily down the obsidian slopes, casting long, dancing shadows across the ash-dusted valley.

"She's breathing," the elder whispered, pointing to the plume of silver smoke billowing into the stars. The air smelled of sulfur and ancient secrets. With each heartbeat of the mountain, tiny glowing sparks floated upward, joining the stars. Kael knew that tomorrow, the valley would change forever.`,

  "Help me plan a productive daily routine as a software developer": `Here is a high-performance daily routine tailored for software engineers:

* **07:30 AM – 08:30 AM**: Wake up, hydrate, and light physical exercise or walk (clear mind).
* **08:30 AM – 09:00 AM**: Review goals for the day (No email/Slack yet).
* **09:00 AM – 12:00 PM**: **Deep Work Block** (Write core logic, solve complex bugs, turn off notifications).
* **12:00 PM – 01:00 PM**: Lunch break & screen-free walk.
* **01:00 PM – 02:30 PM**: Sync meetings, code reviews, answering team messages.
* **02:30 PM – 04:30 PM**: **Second Focus Block** (Testing, documenting, simpler tasks).
* **04:30 PM – 05:00 PM**: Refactoring & planning tomorrow's list.
* **05:00 PM**: Shutdown & disconnect.`,

  "Explain machine learning to me like I am 10 years old, with fun analogies": `Imagine you have a puppy named Spot. You want to teach Spot to fetch a ball, but he doesn't know how yet!

Instead of writing a giant book of rules for Spot, you play a game:
1. You throw a ball.
2. If Spot runs and brings it back, you give him a tasty treat! 🍖
3. If he ignores it or brings back a stick instead, you don't give him anything.

Over time, Spot remembers what got him the treats and starts fetching the ball perfectly.

**Machine Learning** is exactly like teaching Spot! We show the computer many examples of what is correct, and the computer figures out the rules by itself to get the "treat" (correct answer).`,

  "Give me 5 creative startup ideas for a mobile app in 2025 with market analysis": `Here are 5 innovative app concepts for 2025:

1. **EmberFlow**: An AI-powered energy manager for smart homes that coordinates solar, wind, and grid power dynamically.
2. **NomadNest**: A secure, verified monthly co-living matchmaker for digital nomads.
3. **CalmSight**: Augmented Reality glasses overlay app that actively reduces visual clutter and highlights calming natural elements.
4. **RecipeRescue**: Scan your pantry with your phone's camera, and our local AI immediately models a 3-course meal.
5. **CodeCompanion**: Interactive, voice-based programming tutor that lets developers talk out logic issues hands-free.`,

  "Write a Python function to sort a list of dictionaries by multiple keys": `Here is the clean, pythonic way to sort a list of dictionaries by multiple keys using \`lambda\`:

\`\`\`python
def sort_by_keys(data, keys):
    """
    Sorts a list of dictionaries by multiple keys in sequence.
    """
    # We sort by keys in reverse order of priority to achieve hierarchical sorting
    for key in reversed(keys):
        data.sort(key=lambda x: x.get(key))
    return data

# Example Usage:
students = [
    {"name": "Alice", "grade": "A", "age": 20},
    {"name": "Bob", "grade": "B", "age": 19},
    {"name": "Charlie", "grade": "A", "age": 18}
]

# Sort first by grade, then by age
sorted_students = sort_by_keys(students, ["grade", "age"])
print(sorted_students)
\`\`\``
};

function addMessage(sender, text, isBot = false, attachment = null) {
  welcomeScreen.style.display = 'none';
  messagesContainer.style.display = 'flex';
  
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${isBot ? 'bot-message' : 'user-message'}`;
  
  const avatarText = isBot ? '🌋' : 'V';
  const senderName = isBot ? 'Volcano' : 'You';
  
  let attachmentHtml = '';
  if (attachment) {
    if (attachment.type.startsWith('image/')) {
      attachmentHtml = `<img src="${attachment.data}" class="message-attachment-image" alt="attached image" />`;
    } else {
      let icon = '📄';
      if (attachment.name.endsWith('.pdf')) icon = '📕';
      if (attachment.name.endsWith('.csv') || attachment.name.endsWith('.xlsx')) icon = '📊';
      if (attachment.name.endsWith('.json') || attachment.name.endsWith('.js') || attachment.name.endsWith('.html')) icon = '💻';
      
      attachmentHtml = `
        <div class="message-attachment">
          <div class="message-attachment-icon">${icon}</div>
          <div class="message-attachment-info">
            <span class="message-attachment-name">${attachment.name}</span>
            <span class="message-attachment-meta">${attachment.size || 'Document'}</span>
          </div>
        </div>
      `;
    }
  }

  msgDiv.innerHTML = `
    <div class="avatar ${isBot ? 'bot-avatar' : ''}">${avatarText}</div>
    <div class="message-body">
      <div class="message-sender">${senderName}</div>
      <div class="message-text">${formatMessageText(text)}</div>
      ${attachmentHtml}
    </div>
  `;
  
  messagesContainer.appendChild(msgDiv);
  
  // Call KaTeX rendering here if available
  if (typeof renderMathInElement === 'function') {
    renderMathInElement(msgDiv, {
      delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '$', right: '$', display: false},
        {left: '\\(', right: '\\)', display: false},
        {left: '\\[', right: '\\]', display: true}
      ],
      throwOnError: false
    });
  }

  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMessageText(text) {
  let mathBlocks = [];
  
  // Replace block math $$...$$
  let formatted = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, equation) => {
    const placeholder = `__MATH_BLOCK_${mathBlocks.length}__`;
    mathBlocks.push({ placeholder: placeholder, equation: equation, display: true });
    return placeholder;
  });

  // Replace inline math $...$
  formatted = formatted.replace(/\$([^\$\n]+?)\$/g, (match, equation) => {
    const placeholder = `__MATH_INLINE_${mathBlocks.length}__`;
    mathBlocks.push({ placeholder: placeholder, equation: equation, display: false });
    return placeholder;
  });

  // Escape HTML
  formatted = formatted
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  
  // Format fenced code blocks
  formatted = formatted.replace(/\`\`\`(python|javascript|html|css)?\n([\s\S]*?)\`\`\`/g, '<pre><code>$2</code></pre>');
  // Format inline code
  formatted = formatted.replace(/\`([^\`\n]+)\`/g, '<code>$1</code>');
  // Format bold text (**text**)
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Format newlines
  formatted = formatted.split('\n').map(line => {
    if (line.trim().startsWith('*') || line.trim().startsWith('-')) {
      return `<li>${line.substring(2)}</li>`;
    }
    return line ? `<p>${line}</p>` : '';
  }).join('');

  // Restore math blocks with proper KaTeX HTML
  mathBlocks.forEach(item => {
    if (window.katex) {
      try {
        let html = katex.renderToString(item.equation, {
          displayMode: item.display,
          throwOnError: false
        });
        if (item.display) {
          html = `<div class="math-card"><div class="math-card-label">Formula</div><div class="math-card-content">${html}</div></div>`;
        }
        formatted = formatted.replaceAll(item.placeholder, html);
      } catch (e) {
        const rawDelimiter = item.display ? '$$' : '$';
        let htmlContent = rawDelimiter + item.equation + rawDelimiter;
        if (item.display) {
          htmlContent = `<div class="math-card"><div class="math-card-label">Formula</div><div class="math-card-content">${htmlContent}</div></div>`;
        }
        formatted = formatted.replaceAll(item.placeholder, htmlContent);
      }
    } else {
      const rawDelimiter = item.display ? '$$' : '$';
      let htmlContent = rawDelimiter + item.equation + rawDelimiter;
      if (item.display) {
        htmlContent = `<div class="math-card"><div class="math-card-label">Formula</div><div class="math-card-content">${htmlContent}</div></div>`;
      }
      formatted = formatted.replaceAll(item.placeholder, htmlContent);
    }
  });
  
  return formatted;
}

function generateBotResponse(prompt, attachment = null) {
  const isDeepThink = deepThinkBtn.classList.contains('active-pill');

  const loaderDiv = document.createElement('div');
  loaderDiv.className = 'message bot-message loading-msg';
  loaderDiv.innerHTML = `
    <div class="avatar">🌋</div>
    <div class="message-body">
      <div class="message-sender">Volcano</div>
      <div class="loading-indicator">
        <div class="lava-bar">
          <div class="lava-bar-fill"></div>
        </div>
        <div class="loading-text">${isDeepThink ? 'Deep thinking and analyzing magma cores...' : 'Erupting response...'}</div>
      </div>
    </div>
  `;
  messagesContainer.appendChild(loaderDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  function safeJson(res) {
    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
      throw new Error(`Server error (HTTP ${res.status}). Please try again in a moment.`);
    }
    return res.json();
  }

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: prompt,
      session_id: currentSessionId,
      user_id: currentUser ? currentUser.id : 'default_user',
      model: selectedModel,
      attachment: attachment,
      deep_think: isDeepThink
    })
  })
  .then(safeJson)
  .then(data => {
    loaderDiv.remove();
    if (data.success) {
      loadRecentSessions();
      let responseContent = '';
      if (data.reasoning) {
        responseContent += `*Thinking Process:*\n\`\`\`\n${data.reasoning}\n\`\`\`\n\n`;
      }
      responseContent += data.content;
      addMessage('Volcano', responseContent, true);
    } else {
      addMessage('Volcano', `An eruption error occurred: ${data.error}`, true);
    }
  })
  .catch(err => {
    loaderDiv.remove();
    addMessage('Volcano', `🌋 ${err.message}`, true);
  });
}




// Handling user input triggers
function handleSend() {
  const text = messageInput.value.trim();
  if (!text && !currentAttachment) return;
  
  addMessage('You', text, false, currentAttachment);
  
  const sentPrompt = text;
  const sentAttachment = currentAttachment;
  
  messageInput.value = '';
  messageInput.style.height = 'auto';
  sendBtn.setAttribute('disabled', 'true');
  
  // Reset attachment
  currentAttachment = null;
  documentInput.value = '';
  imageInputEl.value = '';
  showFilePreview();
  
  generateBotResponse(sentPrompt, sentAttachment);
}

sendBtn.addEventListener('click', handleSend);
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

// Suggestions click handler
const suggestionCards = document.querySelectorAll('.suggestion-card');
suggestionCards.forEach(card => {
  card.addEventListener('click', () => {
    const prompt = card.getAttribute('data-prompt');
    addMessage('You', prompt, false);
    generateBotResponse(prompt);
  });
});

// New Chat button
newChatBtn.addEventListener('click', () => {
  messagesContainer.innerHTML = '';
  messagesContainer.style.display = 'none';
  welcomeScreen.style.display = 'flex';
  
  // Generate a new session ID for a fresh session
  currentSessionId = generateUUID();
  localStorage.setItem('currentSessionId', currentSessionId);
  loadRecentSessions();
});

// Chat history click handler using event delegation
const chatHistory = document.getElementById('chatHistory');
chatHistory.addEventListener('click', (e) => {
  const item = e.target.closest('.history-item');
  if (!item) return;
  
  document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
  item.classList.add('active');
  
  const sessId = item.getAttribute('data-session-id');
  currentSessionId = sessId;
  localStorage.setItem('currentSessionId', sessId);
  
  loadSessionHistory();
});

function loadRecentSessions() {
  if (!currentUser) return;
  fetch(`/api/sessions?user_id=${currentUser.id}`)
    .then(res => {
      const ct = res.headers.get('content-type') || '';
      return ct.includes('application/json') ? res.json() : null;
    })
    .then(data => {
      if (!data) return;
      if (data.success && data.sessions) {
        chatHistory.innerHTML = '';
        data.sessions.forEach(s => {
          const li = document.createElement('li');
          li.className = 'history-item';
          if (s.session_id === currentSessionId) {
            li.classList.add('active');
          }
          li.setAttribute('data-session-id', s.session_id);
          li.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <span>${s.title}</span>
          `;
          chatHistory.appendChild(li);
        });
      }
    })
    .catch(err => console.error("Error loading recent sessions:", err));
}


// Clear all sessions
const clearAllSessionsBtn = document.getElementById('clearAllSessionsBtn');
clearAllSessionsBtn.addEventListener('click', () => {
  if (!currentUser) return;
  if (confirm("Are you sure you want to clear all your recent chat sessions and history?")) {
    fetch('/api/sessions/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: currentUser.id })
    })
    .then(res => {
      const ct = res.headers.get('content-type') || '';
      return ct.includes('application/json') ? res.json() : null;
    })
    .then(data => {
      if (!data) return;
      if (data.success) {
        messagesContainer.innerHTML = '';
        messagesContainer.style.display = 'none';
        welcomeScreen.style.display = 'flex';
        currentSessionId = generateUUID();
        localStorage.setItem('currentSessionId', currentSessionId);
        loadRecentSessions();
      } else {
        alert("Failed to clear sessions: " + data.error);
      }
    })
    .catch(err => console.error("Error clearing sessions:", err));

  }
});

function loadSessionHistory() {
  const sessionId = localStorage.getItem('currentSessionId');
  if (!sessionId) return;
  
  fetch(`/api/history?session_id=${sessionId}`)
    .then(res => {
      const ct = res.headers.get('content-type') || '';
      return ct.includes('application/json') ? res.json() : null;
    })
    .then(data => {
      if (!data) return;
      if (data.success && data.history && data.history.length > 0) {
        messagesContainer.innerHTML = '';
        welcomeScreen.style.display = 'none';
        messagesContainer.style.display = 'flex';
        
        data.history.forEach(msg => {
          const isBot = msg.role === 'assistant';
          let content = msg.content;
          if (isBot && msg.reasoning) {
            content = `*Thinking Process:*\n\`\`\`\n${msg.reasoning}\n\`\`\`\n\n` + content;
          }
          addMessage(isBot ? 'Volcano' : 'You', content, isBot, msg.attachment);
        });
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    })
    .catch(err => console.error("Error loading chat history:", err));
}

// Auth Elements
const authOverlay = document.getElementById('authOverlay');
const tabLoginBtn = document.getElementById('tabLoginBtn');
const tabSignupBtn = document.getElementById('tabSignupBtn');
const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');
const loginErrorMsg = document.getElementById('loginErrorMsg');
const signupErrorMsg = document.getElementById('signupErrorMsg');
const logoutBtn = document.getElementById('logoutBtn');
const profileUsername = document.getElementById('profileUsername');
const profileEmail = document.getElementById('profileEmail');
const userAvatar = document.getElementById('userAvatar');

// Switch tabs
tabLoginBtn.addEventListener('click', () => {
  tabSignupBtn.classList.remove('active');
  tabLoginBtn.classList.add('active');
  signupForm.style.display = 'none';
  loginForm.style.display = 'flex';
  loginErrorMsg.textContent = '';
  signupErrorMsg.textContent = '';
});

tabSignupBtn.addEventListener('click', () => {
  tabLoginBtn.classList.remove('active');
  tabSignupBtn.classList.add('active');
  loginForm.style.display = 'none';
  signupForm.style.display = 'flex';
  loginErrorMsg.textContent = '';
  signupErrorMsg.textContent = '';
});

function checkAuth() {
  if (authOverlay) authOverlay.style.display = 'none';
  if (profileUsername) profileUsername.textContent = currentUser.username;
  if (profileEmail) profileEmail.textContent = currentUser.email;
  if (userAvatar) userAvatar.textContent = currentUser.username.charAt(0).toUpperCase();
  if (logoutBtn) logoutBtn.style.display = 'none';
  loadRecentSessions();
  loadSessionHistory();
}

// Login Submit
loginForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const emailVal = document.getElementById('loginEmail').value;
  const passwordVal = document.getElementById('loginPassword').value;
  
  fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: emailVal, password: passwordVal })
  })
  .then(res => {
    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) throw new Error('Server error — please try again.');
    return res.json();
  })
  .then(data => {
    if (data.success) {
      currentUser = data.user;
      localStorage.setItem('currentUser', JSON.stringify(currentUser));
      loginForm.reset();
      checkAuth();
    } else {
      loginErrorMsg.textContent = data.error || "Login failed";
    }
  })
  .catch(err => {
    loginErrorMsg.textContent = err.message;
  });
});


// Signup Submit
signupForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const usernameVal = document.getElementById('signupUsername').value;
  const emailVal = document.getElementById('signupEmail').value;
  const passwordVal = document.getElementById('signupPassword').value;
  
  fetch('/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: usernameVal, email: emailVal, password: passwordVal })
  })
  .then(res => {
    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) throw new Error('Server error — please try again.');
    return res.json();
  })
  .then(data => {
    if (data.success) {
      currentUser = data.user;
      localStorage.setItem('currentUser', JSON.stringify(currentUser));
      signupForm.reset();
      checkAuth();
    } else {
      signupErrorMsg.textContent = data.error || "Signup failed";
    }
  })
  .catch(err => {
    signupErrorMsg.textContent = err.message;
  });
});


// Logout Submit
logoutBtn.addEventListener('click', () => {
  if (confirm("Are you sure you want to log out?")) {
    currentUser = null;
    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentSessionId');
    currentSessionId = generateUUID();
    localStorage.setItem('currentSessionId', currentSessionId);
    
    messagesContainer.innerHTML = '';
    messagesContainer.style.display = 'none';
    welcomeScreen.style.display = 'flex';
    chatHistory.innerHTML = '';
    
    checkAuth();
  }
});

// Remove active highlights by default on initial page load
document.addEventListener("DOMContentLoaded", () => {
  checkAuth();
});
