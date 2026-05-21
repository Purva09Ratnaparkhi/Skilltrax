const config = window.interviewConfig;

const livePreview = document.getElementById("livePreview");
const recordedPreview = document.getElementById("recordedPreview");
const startButton = document.getElementById("startRecording");
const stopButton = document.getElementById("stopRecording");
const submitButton = document.getElementById("submitAnswer");
const skipButton = document.getElementById("skipQuestion");
const statusMessage = document.getElementById("statusMessage");
const loadingIndicator = document.getElementById("loadingIndicator");
const questionText = document.getElementById("questionText");
const questionIndex = document.getElementById("questionIndex");
const questionTotal = document.getElementById("questionTotal");
const attemptsUsedEl = document.getElementById("attemptsUsed");
const timerDisplay = document.getElementById("timerDisplay");
const timerValue = document.getElementById("timerValue");

let mediaStream;
let mediaRecorder;
let recordedChunks = [];
let recordedBlob = null;
let recordingTimer = null;
let timerInterval = null;
let timeRemaining = null;

const setStatus = (message, isError = false) => {
    statusMessage.textContent = message;
    statusMessage.classList.toggle("status-error", isError);
};

const updateAttempts = (attemptsUsed) => {
    attemptsUsedEl.textContent = attemptsUsed;
    const attemptsLeft = config.maxAttempts - attemptsUsed;
    startButton.disabled = attemptsLeft <= 0;
};

const resetRecordingState = () => {
    recordedBlob = null;
    recordedChunks = [];
    recordedPreview.src = "";
    submitButton.disabled = true;
};

const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};

const startTimerDisplay = (totalSeconds) => {
    timeRemaining = totalSeconds;
    timerDisplay.classList.remove("hidden");
    timerValue.textContent = formatTime(timeRemaining);
    
    timerInterval = setInterval(() => {
        timeRemaining--;
        timerValue.textContent = formatTime(timeRemaining);
        
        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }, 1000);
};

const stopTimerDisplay = () => {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    timerDisplay.classList.add("hidden");
    timeRemaining = null;
};

const stopRecording = () => {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
        return;
    }
    mediaRecorder.stop();
    stopButton.disabled = true;
    startButton.disabled = false;
    clearTimeout(recordingTimer);
    stopTimerDisplay();
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
        
        // Check video duration
        recordedPreview.onloadedmetadata = () => {
            const duration = recordedPreview.duration;
            if (duration > config.maxSeconds) {
                setStatus(`Recording too long (${Math.ceil(duration)}s > ${config.maxSeconds}s). Please re-record.`, true);
                submitButton.disabled = true;
                recordedBlob = null;
                recordedChunks = [];
            } else {
                submitButton.disabled = false;
                setStatus(`Recording ready (${Math.ceil(duration)}s). Submit when ready.`);
            }
        };
        
        // Increment attempts when recording completes
        config.attemptsUsed += 1;
        updateAttempts(config.attemptsUsed);
        
        if (config.attemptsUsed >= config.maxAttempts) {
            startButton.disabled = true;
            setStatus("Maximum attempts reached. Please submit your answer now.");
        }
    };

    mediaRecorder.start();
    startButton.disabled = true;
    stopButton.disabled = false;
    startTimerDisplay(config.maxSeconds);

    recordingTimer = setTimeout(() => {
        stopRecording();
        setStatus("Recording stopped at the time limit.");
    }, config.maxSeconds * 1000);
});

stopButton.addEventListener("click", () => {
    stopRecording();
});



submitButton.addEventListener("click", async () => {
    if (!recordedBlob) {
        setStatus("Please record an answer before submitting.", true);
        return;
    }

    submitButton.disabled = true;
    skipButton.disabled = true;
    loadingIndicator.classList.remove("hidden");

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

        setStatus("Answer submitted successfully. Loading next question...");
        
        // Auto-advance to next question after successful submission
        const advanceResponse = await fetch(`/api/interview/${config.sessionId}/advance`, { method: "POST" });
        const advanceResult = await advanceResponse.json();
        
        loadingIndicator.classList.add("hidden");
        
        if (!advanceResponse.ok) {
            throw new Error(advanceResult.error || "Unable to advance");
        }

        if (advanceResult.status === "completed") {
            window.location.href = advanceResult.summary_url;
            return;
        }

        // Load new question
        questionText.textContent = advanceResult.question;
        questionIndex.textContent = advanceResult.order;
        questionTotal.textContent = advanceResult.max_questions;
        config.questionOrder = advanceResult.order;
        config.attemptsUsed = 0;
        updateAttempts(0);
        resetRecordingState();
        setStatus("New question loaded.");
        submitButton.disabled = false;
        skipButton.disabled = false;
    } catch (error) {
        submitButton.disabled = false;
        skipButton.disabled = false;
        loadingIndicator.classList.add("hidden");
        setStatus(error.message, true);
    }
});

skipButton.addEventListener("click", async () => {
    skipButton.disabled = true;
    setStatus("Skipping question...");

    try {
        const response = await fetch(`/api/interview/${config.sessionId}/skip`, { method: "POST" });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Unable to skip question");
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
        setStatus("Question skipped. New question loaded.");
        skipButton.disabled = false;
    } catch (error) {
        skipButton.disabled = false;
        setStatus(error.message, true);
    }
});

updateAttempts(config.attemptsUsed);
initMedia();
