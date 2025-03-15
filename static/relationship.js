document.addEventListener("DOMContentLoaded", () => {
    const popup = document.getElementById("popup");
    const test = document.getElementById("test");
    const datingSection = document.getElementById("dating-section");
    const startTest = document.getElementById("startTest");
    const submitTest = document.getElementById("submitTest");
    const testAnswer = document.getElementById("testAnswer");
    const moralityAnswer = document.getElementById("moralityAnswer");
    const marriageAnswer = document.getElementById("marriageAnswer");

    popup.classList.remove("hidden");

    startTest?.addEventListener("click", () => {
        popup.classList.add("hidden");
        test.classList.remove("hidden");
    });

    submitTest?.addEventListener("click", async () => {
        const intention = testAnswer?.value;
        const morality = moralityAnswer?.value;
        const marriage = marriageAnswer?.value;

        if (!intention || !morality || !marriage) {
            alert("Пожалуйста, заполните все поля теста.");
            return;
        }

        if (intention === "fun" || morality !== "avoid" || marriage !== "official") {
            alert(translations.notSuitable);
        } else {
            await saveTestResult({ intention, morality, marriage });
            test.classList.add("hidden");
            datingSection.classList.remove("hidden");
            loadProfiles();
        }
    });
});

function loadProfiles() {
    fetch(`/get_dating_profiles?user_id=${currentUserId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            if (data.length > 0) {
                showProfile(data, 0);
            } else {
                document.getElementById("profile-container").innerHTML = `<p>${translations.noProfiles}</p>`;
            }
        })
        .catch(error => {
            console.error(translations.errorLoadingProfiles, error);
        });
}

function showProfile(profiles, index) {
    if (index >= profiles.length) {
        document.getElementById("profile-container").innerHTML = `<p>${translations.noMoreProfiles}</p>`;
        return;
    }

    const profile = profiles[index];
    document.getElementById("profile-pic").src = `/static/user_photos/${profile.profile_picture || 'default.jpg'}`;
    document.getElementById("profile-name").innerText = profile.name;
    document.getElementById("profile-city").innerText = `${translations.city}: ${profile.city}`;
    document.getElementById("profile-age").innerText = `${translations.age}: ${profile.age}`;

    document.getElementById("like").onclick = async () => {
        await sendLike(profile.id);
        showProfile(profiles, index + 1);
    };
    document.getElementById("dislike").onclick = () => {
        showProfile(profiles, index + 1);
    };
}

async function saveTestResult(answers) {
    try {
        const response = await fetch('/save_test_result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers: answers })
        });
        const data = await response.json();
        console.log(data.message);
    } catch (error) {
        console.error(translations.errorSavingTest, error);
    }
}

async function sendLike(likedUserId) {
    try {
        const response = await fetch('/like_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ liked_user_id: likedUserId })
        });
        const data = await response.json();

        if (data.match) {
            alert(translations.matchFound);

            const matchNotification = document.getElementById("match-notification");
            const chatLink = document.getElementById("chat-link");

            chatLink.href = `/private_chat/${likedUserId}`;
            matchNotification.classList.remove("hidden");
        }

        console.log(data.message);
    } catch (error) {
        console.error(translations.errorSendingLike, error);
    }
}

// Modify the message rendering to show the timestamp above the message
async function loadMessages() {
    try {
        const response = await fetch(`/get_private_messages/${receiverId}`);
        const messages = await response.json();

        messagesDiv.innerHTML = '';
        messages.forEach(msg => {
            messagesDiv.innerHTML += `
                <div class="message">
                    <div class="timestamp" style="display: block; margin-bottom: 5px;">${msg.timestamp}</div>
                    <div><span>${msg.sender}:</span> ${msg.message}</div>
                </div>`;
        });
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);
    }
}

