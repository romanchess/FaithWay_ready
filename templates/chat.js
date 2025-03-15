document.addEventListener("DOMContentLoaded", function () {
    // Настройка отправки сообщения
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-btn');

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage();
        }
    });

    // Запускаем загрузку сообщений
    fetchMessages();
    // Обновляем чат каждые 3 секунды
    setInterval(fetchMessages, 3000);
});

function fetchMessages() {
    fetch("/get_messages")
        .then(response => response.json())
        .then(data => {
            const chatBox = document.getElementById("chat-box");
            const userLang = document.getElementById("current-lang").value;
            chatBox.innerHTML = "";

            data.forEach(msg => {
                const needsTranslation = msg.lang && msg.lang !== userLang;
                // Здесь мы выводим время (msg.timestamp) СВЕРХУ сообщения
                chatBox.innerHTML += `
                    <div class="message">
                        <div class="timestamp" style="display: block; margin-bottom: 5px; color: #888;">
                            ${msg.timestamp}
                        </div>
                        <p>${msg.user}: ${msg.message}</p>
                        ${
                            needsTranslation
                            ? `<button class="translate-btn" data-id="${msg.id}">Перевести</button>`
                            : ""
                        }
                    </div>
                `;
            });

            // Назначаем обработчики для кнопок перевода
            document.querySelectorAll(".translate-btn").forEach(button => {
                button.addEventListener("click", function () {
                    const messageId = this.dataset.id;
                    translateMessage(messageId, userLang);
                });
            });
        })
        .catch(error => {
            console.error("Ошибка при загрузке сообщений:", error);
        });
}

function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const text = chatInput.value.trim();
    if (text !== '') {
        fetch('/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        })
        .then(res => res.json())
        .then(result => {
            if (result.status === 'ok') {
                chatInput.value = '';
                fetchMessages();
            } else {
                alert('Ошибка: ' + result.message);
            }
        })
        .catch(error => console.error("Ошибка при отправке сообщения:", error));
    }
}

function translateMessage(messageId, targetLang) {
    fetch("/translate_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: messageId, lang: targetLang })
    })
    .then(response => response.json())
    .then(data => {
        if (data.translated_text) {
            alert("Перевод: " + data.translated_text);
        } else {
            alert("Ошибка перевода");
        }
    });
}

