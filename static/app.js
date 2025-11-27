/**
 * Advent of Claude Code - Frontend Application
 */

// Application State
const state = {
    screen: 'setup',
    racing: false,
    currentPart: 1,
    startTime: null,
    pollInterval: null,

    // Race results
    part1: {
        userTime: null,
        claudeTime: null,
        winner: null
    },
    part2: {
        userTime: null,
        claudeTime: null,
        winner: null
    },

    // Puzzle content
    puzzlePart1: null,
    puzzlePart2: null
};

// Stage weights for progress calculation
const STAGE_WEIGHTS = {
    translation: 10,
    planning: 15,
    critique: 10,
    revision: 10,
    coding: 20,
    testing: 20,
    submitting: 15
};

const STAGES_ORDER = ['translation', 'planning', 'critique', 'revision', 'coding', 'testing', 'submitting'];

// DOM Elements
const elements = {
    // Screens
    setupScreen: document.getElementById('setup-screen'),
    raceScreen: document.getElementById('race-screen'),
    resultsScreen: document.getElementById('results-screen'),

    // Setup form
    raceForm: document.getElementById('race-setup-form'),
    tokenInput: document.getElementById('aoc-token'),
    toggleTokenBtn: document.getElementById('toggle-token'),
    yearSelect: document.getElementById('year'),
    daySelect: document.getElementById('day'),
    startBtn: document.getElementById('start-race-btn'),
    setupError: document.getElementById('setup-error'),

    // Race screen
    timer: document.getElementById('race-timer'),
    puzzleTitle: document.getElementById('puzzle-title'),
    puzzleContent: document.getElementById('puzzle-content'),
    inputLink: document.getElementById('input-link'),
    userAnswer: document.getElementById('user-answer'),
    submitAnswerBtn: document.getElementById('submit-answer'),
    answerFeedback: document.getElementById('answer-feedback'),
    tabBtns: document.querySelectorAll('.tab-btn'),

    // Progress
    progressFill: document.getElementById('progress-fill'),
    progressPercent: document.getElementById('progress-percent'),
    currentStage: document.getElementById('current-stage'),
    stageChecklist: document.getElementById('stage-checklist'),
    activityMessages: document.getElementById('activity-messages'),
    claudePart1Status: document.getElementById('claude-part1-status'),
    claudePart2Status: document.getElementById('claude-part2-status'),

    // Results
    winnerAnnouncement: document.getElementById('winner-announcement'),
    userPart1Time: document.getElementById('user-part1-time'),
    claudePart1Time: document.getElementById('claude-part1-time'),
    part1Winner: document.getElementById('part1-winner'),
    userPart2Time: document.getElementById('user-part2-time'),
    claudePart2Time: document.getElementById('claude-part2-time'),
    part2Winner: document.getElementById('part2-winner'),
    userTotalTime: document.getElementById('user-total-time'),
    claudeTotalTime: document.getElementById('claude-total-time'),
    overallWinner: document.getElementById('overall-winner'),
    raceAgainBtn: document.getElementById('race-again-btn'),
    newPuzzleBtn: document.getElementById('new-puzzle-btn')
};

// Utility Functions
function formatTime(seconds) {
    if (seconds === null || seconds === undefined) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function showScreen(screenName) {
    state.screen = screenName;
    elements.setupScreen.classList.remove('active');
    elements.raceScreen.classList.remove('active');
    elements.resultsScreen.classList.remove('active');
    elements.setupScreen.classList.add('hidden');
    elements.raceScreen.classList.add('hidden');
    elements.resultsScreen.classList.add('hidden');

    const screen = document.getElementById(`${screenName}-screen`);
    if (screen) {
        screen.classList.remove('hidden');
        screen.classList.add('active');
    }

    // Show/hide timer
    if (screenName === 'race') {
        elements.timer.classList.remove('hidden');
    } else {
        elements.timer.classList.add('hidden');
    }
}

function showError(message) {
    elements.setupError.textContent = message;
    elements.setupError.classList.remove('hidden');
}

function hideError() {
    elements.setupError.classList.add('hidden');
}

function showFeedback(message, isError) {
    elements.answerFeedback.textContent = message;
    elements.answerFeedback.classList.remove('hidden', 'success', 'error');
    elements.answerFeedback.classList.add(isError ? 'error' : 'success');
}

function hideFeedback() {
    elements.answerFeedback.classList.add('hidden');
}

function addActivityMessage(message) {
    const entry = document.createElement('div');
    entry.className = 'activity-entry';
    entry.textContent = `> ${message}`;
    elements.activityMessages.prepend(entry);

    // Keep only last 10 messages
    while (elements.activityMessages.children.length > 10) {
        elements.activityMessages.removeChild(elements.activityMessages.lastChild);
    }
}

// API Functions
async function fetchConfig() {
    try {
        const response = await fetch('/api/config');
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch config:', error);
        return { has_session: false, current_year: new Date().getFullYear() };
    }
}

async function startRace(year, day, token) {
    const response = await fetch('/api/race/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year, day, aoc_session: token })
    });
    return await response.json();
}

async function getRaceStatus() {
    const response = await fetch('/api/race/status');
    return await response.json();
}

async function submitAnswer(part, answer) {
    const response = await fetch('/api/race/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ part, answer })
    });
    return await response.json();
}

async function resetRace() {
    await fetch('/api/race/reset', { method: 'POST' });
}

// Progress Tracking
function updateProgress(status) {
    const part = state.currentPart === 1 ? status.part1 : status.part2;
    const claudeStatus = part.claude;

    // Update stage checklist
    const currentStage = claudeStatus.stage;
    let progress = 0;
    let foundCurrent = false;

    STAGES_ORDER.forEach((stage, index) => {
        const li = elements.stageChecklist.querySelector(`[data-stage="${stage}"]`);
        if (!li) return;

        li.classList.remove('completed', 'active', 'pending');

        if (currentStage === stage) {
            li.classList.add('active');
            foundCurrent = true;
            // Add partial progress for current stage
            progress += STAGE_WEIGHTS[stage] * 0.5;
        } else if (!foundCurrent && currentStage) {
            // Before current stage - completed
            li.classList.add('completed');
            progress += STAGE_WEIGHTS[stage];
        } else {
            li.classList.add('pending');
        }
    });

    // Handle completed state
    if (claudeStatus.status === 'completed') {
        progress = 100;
        STAGES_ORDER.forEach(stage => {
            const li = elements.stageChecklist.querySelector(`[data-stage="${stage}"]`);
            if (li) {
                li.classList.remove('active', 'pending');
                li.classList.add('completed');
            }
        });
    }

    // Update progress bar
    elements.progressFill.style.width = `${progress}%`;
    elements.progressPercent.textContent = `${Math.round(progress)}%`;
    elements.currentStage.textContent = currentStage ?
        currentStage.charAt(0).toUpperCase() + currentStage.slice(1) :
        'Waiting...';

    // Update activity message
    if (status.latest_message) {
        addActivityMessage(status.latest_message);
    }

    // Update Claude status display
    updateClaudeStatusDisplay(status);
}

function updateClaudeStatusDisplay(status) {
    // Part 1
    const p1Status = status.part1.claude.status;
    const p1Text = elements.claudePart1Status.querySelector('.status-text');
    p1Text.textContent = p1Status.charAt(0).toUpperCase() + p1Status.slice(1);
    p1Text.className = `status-text ${p1Status}`;

    if (status.part1.claude.finish_time) {
        p1Text.textContent += ` (${formatTime(status.part1.claude.finish_time)})`;
    }

    // Part 2
    const p2Status = status.part2.claude.status;
    const p2Text = elements.claudePart2Status.querySelector('.status-text');
    if (p2Status === 'pending' && !status.puzzle_part2) {
        p2Text.textContent = 'Locked';
        p2Text.className = 'status-text';
    } else {
        p2Text.textContent = p2Status.charAt(0).toUpperCase() + p2Status.slice(1);
        p2Text.className = `status-text ${p2Status}`;

        if (status.part2.claude.finish_time) {
            p2Text.textContent += ` (${formatTime(status.part2.claude.finish_time)})`;
        }
    }

    // Enable Part 2 tab if unlocked
    const part2Tab = document.querySelector('.tab-btn[data-part="2"]');
    if (status.puzzle_part2) {
        part2Tab.disabled = false;
        state.puzzlePart2 = status.puzzle_part2;
    }
}

// Timer
function updateTimer() {
    if (!state.startTime) return;
    const elapsed = (Date.now() - state.startTime) / 1000;
    elements.timer.textContent = formatTime(elapsed);
}

function startTimer() {
    state.startTime = Date.now();
    setInterval(updateTimer, 100);
}

// Polling
function startPolling() {
    state.pollInterval = setInterval(async () => {
        if (!state.racing) return;

        try {
            const status = await getRaceStatus();
            updateProgress(status);

            // Check for part completion
            checkPartCompletion(status);

        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 1000);
}

function stopPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
        state.pollInterval = null;
    }
}

function checkPartCompletion(status) {
    // Update state with results
    if (status.part1.winner && !state.part1.winner) {
        state.part1.winner = status.part1.winner;
        state.part1.userTime = status.part1.user.finish_time;
        state.part1.claudeTime = status.part1.claude.finish_time;
    }

    if (status.part2.winner && !state.part2.winner) {
        state.part2.winner = status.part2.winner;
        state.part2.userTime = status.part2.user.finish_time;
        state.part2.claudeTime = status.part2.claude.finish_time;
    }
}

// Initialize year/day dropdowns
async function initializeDropdowns() {
    const config = await fetchConfig();
    const currentYear = config.current_year;

    // Populate years (2015 to current)
    for (let year = currentYear; year >= 2015; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        elements.yearSelect.appendChild(option);
    }

    // Populate days (1-25)
    for (let day = 1; day <= 25; day++) {
        const option = document.createElement('option');
        option.value = day;
        option.textContent = day;
        elements.daySelect.appendChild(option);
    }

    // Pre-fill token if available in environment
    if (config.has_session) {
        elements.tokenInput.placeholder = 'Using token from environment (or enter new one)';
        // Hide toggle button when using env token (nothing to show)
        elements.toggleTokenBtn.classList.add('hidden');
    }
}

// Show toggle button when user starts typing a token
function setupTokenInputHandler() {
    elements.tokenInput.addEventListener('input', () => {
        if (elements.tokenInput.value.length > 0) {
            elements.toggleTokenBtn.classList.remove('hidden');
        } else {
            // Check if env has session
            fetchConfig().then(config => {
                if (config.has_session) {
                    elements.toggleTokenBtn.classList.add('hidden');
                }
            });
        }
    });
}

// Event Handlers
function setupEventListeners() {
    // Toggle token visibility
    elements.toggleTokenBtn.addEventListener('click', () => {
        const isPassword = elements.tokenInput.type === 'password';
        elements.tokenInput.type = isPassword ? 'text' : 'password';
        elements.toggleTokenBtn.textContent = isPassword ? 'Hide' : 'Show';
    });

    // Form submission
    elements.raceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError();

        const year = parseInt(elements.yearSelect.value);
        const day = parseInt(elements.daySelect.value);
        const token = elements.tokenInput.value.trim();

        elements.startBtn.disabled = true;
        elements.startBtn.textContent = 'Starting...';

        try {
            const result = await startRace(year, day, token);

            if (result.success) {
                state.racing = true;
                state.puzzlePart1 = result.puzzle_part1;

                // Update UI
                elements.puzzleTitle.textContent = result.puzzle_title || `Day ${day}`;
                elements.puzzleContent.innerHTML = markdownToHtml(result.puzzle_part1);
                elements.inputLink.href = result.input_url;

                showScreen('race');
                startTimer();
                startPolling();
            } else {
                showError(result.error || 'Failed to start race');
            }
        } catch (error) {
            showError(`Error: ${error.message}`);
        } finally {
            elements.startBtn.disabled = false;
            elements.startBtn.textContent = 'Start the Race!';
        }
    });

    // Submit answer
    elements.submitAnswerBtn.addEventListener('click', async () => {
        const answer = elements.userAnswer.value.trim();
        if (!answer) return;

        hideFeedback();
        elements.submitAnswerBtn.disabled = true;
        elements.submitAnswerBtn.textContent = 'Submitting...';

        try {
            const result = await submitAnswer(state.currentPart, answer);

            if (result.success) {
                if (result.correct) {
                    showFeedback('Correct!', false);

                    // Record user time
                    const elapsed = (Date.now() - state.startTime) / 1000;
                    if (state.currentPart === 1) {
                        state.part1.userTime = elapsed;
                    } else {
                        state.part2.userTime = elapsed;
                    }

                    elements.userAnswer.value = '';

                    // Check if we should show results or move to part 2
                    if (state.currentPart === 1) {
                        // Part 1 done - check if part 2 is available
                        setTimeout(async () => {
                            const status = await getRaceStatus();
                            if (status.puzzle_part2) {
                                state.puzzlePart2 = status.puzzle_part2;
                                document.querySelector('.tab-btn[data-part="2"]').disabled = false;
                                showFeedback('Part 1 complete! Part 2 is now available.', false);
                            }
                        }, 1000);
                    } else {
                        // Part 2 done - show results after a moment
                        setTimeout(() => showResults(), 2000);
                    }
                } else {
                    let msg = result.message || 'Incorrect answer';
                    if (result.hint) {
                        msg += ` (Hint: ${result.hint})`;
                    }
                    showFeedback(msg, true);
                }
            } else {
                showFeedback(result.message || 'Submission failed', true);
            }
        } catch (error) {
            showFeedback(`Error: ${error.message}`, true);
        } finally {
            elements.submitAnswerBtn.disabled = false;
            elements.submitAnswerBtn.textContent = 'Submit';
        }
    });

    // Enter key to submit
    elements.userAnswer.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            elements.submitAnswerBtn.click();
        }
    });

    // Part tabs
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;

            const part = parseInt(btn.dataset.part);
            state.currentPart = part;

            // Update tab styles
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update puzzle content
            const content = part === 1 ? state.puzzlePart1 : state.puzzlePart2;
            if (content) {
                elements.puzzleContent.innerHTML = markdownToHtml(content);
            }

            hideFeedback();
            elements.userAnswer.value = '';
        });
    });

    // Results screen buttons
    elements.raceAgainBtn.addEventListener('click', async () => {
        await resetRace();
        resetState();
        showScreen('setup');
    });

    elements.newPuzzleBtn.addEventListener('click', async () => {
        await resetRace();
        resetState();
        showScreen('setup');
    });
}

function resetState() {
    state.racing = false;
    state.currentPart = 1;
    state.startTime = null;
    state.puzzlePart1 = null;
    state.puzzlePart2 = null;
    state.part1 = { userTime: null, claudeTime: null, winner: null };
    state.part2 = { userTime: null, claudeTime: null, winner: null };
    stopPolling();

    // Reset UI
    elements.userAnswer.value = '';
    elements.activityMessages.innerHTML = '';
    elements.progressFill.style.width = '0%';
    elements.progressPercent.textContent = '0%';
    elements.currentStage.textContent = 'Waiting...';

    // Reset stage checklist
    document.querySelectorAll('.stage-list li').forEach(li => {
        li.classList.remove('completed', 'active');
        li.classList.add('pending');
    });

    // Reset tabs
    elements.tabBtns.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.part === '1') {
            btn.classList.add('active');
        } else {
            btn.disabled = true;
        }
    });
}

function showResults() {
    stopPolling();
    state.racing = false;

    // Calculate totals
    const userTotal = (state.part1.userTime || 0) + (state.part2.userTime || 0);
    const claudeTotal = (state.part1.claudeTime || 0) + (state.part2.claudeTime || 0);

    // Determine overall winner
    let overallWinner = 'tie';
    if (userTotal < claudeTotal) {
        overallWinner = 'user';
    } else if (claudeTotal < userTotal) {
        overallWinner = 'claude';
    }

    // Update results table
    elements.userPart1Time.textContent = formatTime(state.part1.userTime);
    elements.claudePart1Time.textContent = formatTime(state.part1.claudeTime);
    elements.part1Winner.textContent = state.part1.winner || '--';

    elements.userPart2Time.textContent = formatTime(state.part2.userTime);
    elements.claudePart2Time.textContent = formatTime(state.part2.claudeTime);
    elements.part2Winner.textContent = state.part2.winner || '--';

    elements.userTotalTime.textContent = formatTime(userTotal);
    elements.claudeTotalTime.textContent = formatTime(claudeTotal);
    elements.overallWinner.textContent = overallWinner === 'user' ? 'You' :
                                         overallWinner === 'claude' ? 'Claude' : 'Tie';

    // Update winner banner
    elements.winnerAnnouncement.className = 'winner-banner';
    if (overallWinner === 'user') {
        elements.winnerAnnouncement.classList.add('user-wins');
        elements.winnerAnnouncement.innerHTML = '<h2>You Win!</h2><p>Congratulations!</p>';
    } else if (overallWinner === 'claude') {
        elements.winnerAnnouncement.classList.add('claude-wins');
        elements.winnerAnnouncement.innerHTML = '<h2>Claude Wins!</h2><p>Better luck next time!</p>';
    } else {
        elements.winnerAnnouncement.classList.add('tie');
        elements.winnerAnnouncement.innerHTML = '<h2>It\'s a Tie!</h2><p>Great minds think alike!</p>';
    }

    showScreen('results');
}

// Simple markdown to HTML conversion (basic)
function markdownToHtml(markdown) {
    if (!markdown) return '';

    return markdown
        // Escape HTML
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // Code blocks
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic/emphasis
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Headers
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        // Wrap in paragraph
        .replace(/^(.+)$/, '<p>$1</p>');
}

// Check for existing race and restore state
async function checkExistingRace() {
    try {
        const status = await getRaceStatus();
        if (status.status === 'racing') {
            // Restore race state
            state.racing = true;
            state.puzzlePart1 = status.puzzle_part1;
            state.puzzlePart2 = status.puzzle_part2;

            // Restore timer from server elapsed time
            state.startTime = Date.now() - (status.elapsed_seconds * 1000);

            // Update UI
            elements.puzzleTitle.textContent = status.puzzle_title || `Day ${status.day}`;
            if (state.puzzlePart1) {
                elements.puzzleContent.innerHTML = markdownToHtml(state.puzzlePart1);
            }
            if (status.input_url) {
                elements.inputLink.href = status.input_url;
            }

            // Restore part 2 tab if available
            if (status.puzzle_part2) {
                const part2Tab = document.querySelector('.tab-btn[data-part="2"]');
                part2Tab.disabled = false;
            }

            // Restore user completion status
            if (status.part1.user.status === 'completed') {
                state.part1.userTime = status.part1.user.finish_time;
                state.part1.winner = status.part1.winner;
            }
            if (status.part2.user.status === 'completed') {
                state.part2.userTime = status.part2.user.finish_time;
                state.part2.winner = status.part2.winner;
            }

            // Restore Claude completion status
            if (status.part1.claude.status === 'completed') {
                state.part1.claudeTime = status.part1.claude.finish_time;
            }
            if (status.part2.claude.status === 'completed') {
                state.part2.claudeTime = status.part2.claude.finish_time;
            }

            showScreen('race');
            setInterval(updateTimer, 100);
            startPolling();

            // Update progress immediately
            updateProgress(status);

            return true;
        }
    } catch (error) {
        console.error('Error checking existing race:', error);
    }
    return false;
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await initializeDropdowns();
    setupEventListeners();
    setupTokenInputHandler();

    // Check if there's an existing race to restore
    await checkExistingRace();
});
