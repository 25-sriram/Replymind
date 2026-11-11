
let lastRequest = null;

async function generateReply() {

    const email = document.getElementById("email").value.trim();
    const context = document.getElementById("context").value.trim();
    const tone = document.getElementById("tone").value;

    const status = document.getElementById("status");
    const button = document.getElementById("generateBtn");

    if (!email) {
        status.textContent = "Please enter an email first.";
        return;
    }

    lastRequest = { email, context, tone };

    button.disabled = true;
    button.textContent = "Generating...";
    status.textContent = "AI is analyzing your email...";

    try {

        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(lastRequest)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Request failed");
        }

        document.getElementById("result").classList.remove("hidden");

        document.getElementById("category").textContent = data.category;
        document.getElementById("priority").textContent = data.priority;
        document.getElementById("intent").textContent = data.intent;
        document.getElementById("summary").textContent = data.summary;
        document.getElementById("reply").value = data.reply;

        displayList("keyPoints", data.key_points);
        displayList("actions", data.required_actions);

        status.textContent = "Reply generated successfully!";

    } catch (error) {

        status.textContent = error.message;

    } finally {

        button.disabled = false;
        button.textContent = "Generate Reply";
    }
}


function displayList(elementId, items) {

    const list = document.getElementById(elementId);

    list.replaceChildren();

    (Array.isArray(items) ? items : []).forEach(item => {

        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);

    });
}


async function copyReply() {

    const reply = document.getElementById("reply").value;

    if (!reply.trim()) {
        document.getElementById("copyStatus").textContent =
            "No reply available.";
        return;
    }

    try {
        await navigator.clipboard.writeText(reply);

        document.getElementById("copyStatus").textContent =
            "Reply copied successfully!";

    } catch (error) {

        document.getElementById("copyStatus").textContent =
            "Copy failed. Please select and copy manually.";
    }
}
