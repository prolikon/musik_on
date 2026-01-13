const socket = io();

let selectedIds = [];
const download = document.getElementById("download");
const request = document.getElementById("requeset");
const selectAll = document.getElementById("select_all");
const dirButton = document.getElementById("select_dir");
const cards = document.querySelectorAll("[data-card]");

let dirHandle;

async function promptDir() {
    try {
        dirHandle = await window.showDirectoryPicker({
            id: "1",
            mode: "readwrite",
            startIn: "music",
        });
    } finally {
        dirButton.innerHTML = `&nbsp;<i class="fa-solid fa-folder-open"></i>&nbsp;${dirHandle.name}&nbsp;`;

        for (const card of cards) {
            const fileName = `${card.id}.opus`;

            try {
                await dirHandle.getFileHandle(fileName);
                card.dataset.state = "complete";
            } catch (err) {
                card.dataset.state = "complete";
            }
        }
    }
}

async function downloadSelected() {
    if (!dirHandle) {
        alert("Please select a folder first");
        return;
    }

    let m3u = "";

    for (const id of selectedIds) {
        try {
            m3u += id + ".opus\n";
            await downloadAudio(id);
        } catch (error) {
            console.log(`Failed to download ${id}`);
        }
    }

    const fileHandle = await dirHandle.getFileHandle(`{{playlist.name}}.m3u`, {
        create: true,
    });
    const writable = await fileHandle.createWritable();
    await writable.write(m3u);
    await writable.close();
}

async function downloadAudio(id) {
    const filename = `${id}.opus`;

    try {
        await dirHandle.getFileHandle(filename, { create: false });
        return;
    } catch (e) {
        // we lowkey wanna get here 8-)
    }

    const response = await fetch(`/static/media/${id}.opus`);
    if (!response.ok) throw new Error(`HTTP error ${response.status}`);

    const fileHandle = await dirHandle.getFileHandle(filename, {
        create: true,
    });
    const writable = await fileHandle.createWritable();

    await response.body.pipeTo(writable);

    document.getElementById(id).dataset.state = "complete";
}

// SOCKET //

function requestAudio(id) {
    console.log("Requesting", id);
    socket.emit("request_audios", { video_id: [id] });
}

function requestSelectedAudios(id) {
    console.log("Requesting", selectedIds);
    socket.emit("request_audios", { video_id: selectedIds });
}

socket.on("tasks_enqueued", function (data) {
    if (data.type == "request_audio") {
        data.tasks.forEach((task) => {
            let card = document.getElementById(task.video_id);
            if (card) {
                card.dataset.state = "in-progress";
            }
        });
    }
});

socket.on("task_complete", (data) => {
    if (data.task == "request_audio") {
        let card = document.getElementById(data.video_id);
        if (card) {
            card.dataset.state = "download";
        }
    }
});

// HTML //

function toggleCard(id) {
    const cards = Array.from(document.querySelectorAll("[data-card]"));
    const el = document.getElementById(id);
    if (selectedIds.includes(id)) {
        if (selectedIds.length === cards.length) {
            selectAll.classList.add("bg-main-3");
            selectAll.classList.remove("bg-lime-700");
        }
        selectedIds = selectedIds.filter((x) => x !== id);
        el.classList.remove("outline-3");
    } else {
        selectedIds.push(id);
        el.classList.add("outline-3");
        if (selectedIds.length === cards.length) {
            selectAll.classList.remove("bg-main-3");
            selectAll.classList.add("bg-lime-700");
        }
    }
}

function toggleSelectAll() {
    const cards = Array.from(document.querySelectorAll("[data-card]"));

    if (selectedIds.length === cards.length) {
        // all selected → deselect all
        selectedIds = [];
        document.querySelectorAll("[data-card]").forEach((card) => {
            if (!selectedIds.includes(card.id)) {
                card.classList.remove("outline-3");
            }
        });
        selectAll.classList.add("bg-main-3");
        selectAll.classList.remove("bg-lime-700");
    } else {
        // not all selected → select all
        selectedIds = cards.map((card) => card.id);
        selectedIds.forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.classList.add("outline-3");
        });
        selectAll.classList.remove("bg-main-3");
        selectAll.classList.add("bg-lime-700");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-card]").forEach((card) => {
        card.addEventListener("click", (e) => {
            if (e.target.closest("a")) return;
            toggleCard(card.id);
        });
    });
});
