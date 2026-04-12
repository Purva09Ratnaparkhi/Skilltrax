const config = window.interviewConfig;

const livePreview = document.getElementById("livePreview");
const recordedPreview = document.getElementById("recordedPreview");
const startButton = document.getElementById("startRecording");
const stopButton = document.getElementById("stopRecording");
const submitButton = document.getElementById("submitAnswer");
const retryButton = document.getElementById("retryAnswer");
const nextButton = document.getElementById("nextQuestion");
const statusMessage = document.getElementById("statusMessage");
const questionText = document.getElementById("questionText");
const questionIndex = document.getElementById("questionIndex");
const questionTotal = document.getElementById("questionTotal");
const attemptsUsedEl = document.getElementById("attemptsUsed");

let mediaStream;
let mediaRecorder;
let recordedChunks = [];
let recordedBlob = null;
let recordingTimer = null;

const setStatus = (message, isError = false) => {
    statusMessage.textContent = message;
    statusMessage.classList.toggle("status-error", isError);
};

const updateAttempts = (attemptsUsed) => {
    attemptsUsedEl.textContent = attemptsUsed;
    const attemptsLeft = config.maxAttempts - attemptsUsed;
    retryButton.disabled = attemptsLeft <= 0;
    nextButton.disabled = attemptsUsed === 0;
};

const resetRecordingState = () => {
    recordedBlob = null;
    recordedChunks = [];
    recordedPreview.src = "";
    submitButton.disabled = true;
};

const stopRecording = () => {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
        return;
    }
    mediaRecorder.stop();
    stopButton.disabled = true;
    startButton.disabled = false;
    clearTimeout(recordingTimer);
};

const initMedia = async () => {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        livePreview.srcObject = mediaStream;
    } catch (error) {
        setStatus("Unable to access camera and microphone.", true);
    }
};

startButton.addEventListener("click", () => {
    if (!mediaStream) {
        setStatus("Camera access is required to record.", true);
        return;
    }

    resetRecordingState();
    setStatus("Recording started.");

    mediaRecorder = new MediaRecorder(mediaStream, { mimeType: "video/webm" });
    mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
            recordedChunks.push(event.data);
        }
    };

    mediaRecorder.onstop = () => {
        recordedBlob = new Blob(recordedChunks, { type: "video/webm" });
        recordedPreview.src = URL.createObjectURL(recordedBlob);
        submitButton.disabled = false;
        retryButton.disabled = true;
        setStatus("Recording ready. Preview and submit when ready.");
    };

    mediaRecorder.start();
    startButton.disabled = true;
    stopButton.disabled = false;

    recordingTimer = setTimeout(() => {
        stopRecording();
        setStatus("Recording stopped at the time limit.");
    }, config.maxSeconds * 1000);
});

stopButton.addEventListener("click", () => {
    stopRecording();
});

retryButton.addEventListener("click", () => {
    resetRecordingState();
    setStatus("You can record again.");
});

submitButton.addEventListener("click", async () => {
    if (!recordedBlob) {
        setStatus("Please record an answer before submitting.", true);
        return;
    }

    submitButton.disabled = true;
    setStatus("Submitting answer...");

    const formData = new FormData();
    formData.append("video", recordedBlob, "answer.webm");

    try {
        const response = await fetch(`/api/interview/${config.sessionId}/submit`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Submission failed");
        }

        config.attemptsUsed = result.attempts_used;
        updateAttempts(config.attemptsUsed);
        setStatus("Answer saved. You can record again or continue.");
        retryButton.disabled = result.attempts_left <= 0;
        nextButton.disabled = false;
    } catch (error) {
        submitButton.disabled = false;
        setStatus(error.message, true);
    }
});

nextButton.addEventListener("click", async () => {
    nextButton.disabled = true;
    setStatus("Loading next question...");

    try {
        const response = await fetch(`/api/interview/${config.sessionId}/advance`, { method: "POST" });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Unable to advance");
        }

        if (result.status === "completed") {
            window.location.href = result.summary_url;
            return;
        }

        questionText.textContent = result.question;
        questionIndex.textContent = result.order;
        questionTotal.textContent = result.max_questions;
        config.questionOrder = result.order;
        config.attemptsUsed = 0;
        updateAttempts(0);
        resetRecordingState();
        setStatus("New question loaded.");
    } catch (error) {
        nextButton.disabled = false;
        setStatus(error.message, true);
    }
});

updateAttempts(config.attemptsUsed);
initMedia();
