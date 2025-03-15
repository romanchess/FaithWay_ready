document.addEventListener("DOMContentLoaded", () => {
    const popup = document.getElementById("popup");
    const test = document.getElementById("test");
    const datingSection = document.getElementById("dating-section");
    const startTest = document.getElementById("startTest");
    const submitTest = document.getElementById("submitTest");
    const testAnswer = document.getElementById("testAnswer");
    const moralityAnswer = document.getElementById("moralityAnswer");
    const marriageAnswer = document.getElementById("marriageAnswer");
    const matchNotification = document.getElementById("match-notification");
    const chatLink = document.getElementById("chat-link");

    popup.classList.remove("hidden");

    startTest.addEventListener("click", () => {
        popup.classList.add("hidden");
        test.classList.remove("hidden");
    });

    submitTest.addEventListener("click", async () => {
        const intention = testAnswer.value;
        const morality = moralityAnswer.value;
        const marriage = marriageAnswer.value;

        console.log('Test Values:', { intention, morality, marriage });

        if (!intention || !morality || !marriage) {
            alert('Все поля обязательны!');
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
    document.getElementById("profile-pic").src = profile.profile_picture || '/static/default.jpg';
    document.getElementById("profile-name").innerText = profile.name || 'Без имени';
    document.getElementById("profile-city").innerText = `${translations.city}: ${profile.city || 'Не указан'}`;
    document.getElementById("profile-age").innerText = `${translations.age}: ${profile.age || 'Не указан'}`;

    document.getElementById("like").onclick = async () => {
        if (!profile.id) {
            console.error("Profile ID is undefined", profile);
            return;
        }

        const result = await sendLike(profile.id);
        console.log('Like Result:', result);

        if (result && result.match) {
            matchNotification.classList.remove("hidden");
            chatLink.href = `/private_chat/${profile.id}`;
            chatLink.innerText = translations.matchFound;
        } else if (result && result.message) {
            alert(result.message);
        } else {
            console.error("Unexpected like response", result);
        }

        showProfile(profiles, index + 1);
    };

    document.getElementById("dislike").onclick = () => {
        showProfile(profiles, index + 1);
    };
}

async function saveTestResult(answers) {
    try {
        console.log('Sending Test Answers:', answers);

        const response = await fetch('/save_test_result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                intention: answers.intention,
                morality: answers.morality,
                marriage: answers.marriage
            })
        });

        const data = await response.json();
        console.log('Server Response:', data);

        if (!response.ok) {
            throw new Error(`Ошибка на сервере: ${data.error || data.message}`);
        }

    } catch (error) {
        console.error('Error Saving Test Result:', error);
    }
}

async function sendLike(likedUserId) {
    try {
        if (!likedUserId) {
            console.error('likedUserId is undefined!');
            return;
        }

        const response = await fetch('/like_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ liked_user_id: likedUserId })
        });

        const data = await response.json();
        console.log('Server Like Response:', data);

        if (!response.ok) {
            throw new Error(`Ошибка на сервере: ${data.error || data.message}`);
        }

        return data;
    } catch (error) {
        console.error('Error Sending Like:', error);
    }
}

