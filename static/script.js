const sendBtn = document.getElementById('send-btn');
const userInputField = document.getElementById('user-input');
const chatBox = document.getElementById('chat-box');
const themeToggleButton = document.getElementById('theme-toggle');
const themeElement = document.body;
const lightThemeClass = 'light-theme';

function toggleTheme() {
    const isLightTheme = themeElement.classList.contains(lightThemeClass);

    if (isLightTheme) {
        themeElement.classList.remove(lightThemeClass);
        localStorage.setItem('theme', 'dark');
        themeToggleButton.textContent = '🌙';
    } else {
        themeElement.classList.add(lightThemeClass);
        localStorage.setItem('theme', 'light');
        themeToggleButton.textContent = '☀️';
    }
}

function applySavedTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        themeElement.classList.add(lightThemeClass);
        themeToggleButton.textContent = '☀️';
    } else {
        themeToggleButton.textContent = '🌙';
    }
}

applySavedTheme();
sendBtn.addEventListener('click', sendMessage);
userInputField.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
themeToggleButton.addEventListener('click', toggleTheme);

function sendMessage() {
    const userInput = userInputField.value.trim();
    if (!userInput) return;

    displayMessage(userInput, 'user');
    userInputField.value = '';

    displayTypingIndicator();
    fetchChatbotResponse(userInput);
}

function displayMessage(message, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);

    const textDiv = document.createElement('div');
    textDiv.classList.add('message-text');
    textDiv.innerHTML = message;
    messageDiv.appendChild(textDiv);
    chatBox.appendChild(messageDiv);

    chatBox.scrollTop = chatBox.scrollHeight;
}


function displayTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typing-indicator';
    typingDiv.classList.add('message', 'bot');
    typingDiv.innerHTML = `<div class="message-text typing"><span>.</span><span>.</span><span>.</span></div>`;
    chatBox.appendChild(typingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}


function fetchChatbotResponse(userInput) {
    fetch('http://127.0.0.1:8000/chatbot_gpt/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: userInput }),
    })
        .then((response) => response.json())
        .then((data) => {
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) typingIndicator.remove();

            const chatbotReply =
                typeof data.response === 'object'
                    ? data.response.response
                    : data.response;

            displayMessage(chatbotReply || "Sorry, I didn't understand that.", 'bot');
        })
        .catch((error) => {
            console.error('Error fetching chatbot response:', error);
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) typingIndicator.remove();
            displayMessage("⚠️ Error connecting to server.", 'bot');
        });
}
