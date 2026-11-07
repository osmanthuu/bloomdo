// === MAIN PASTEL TO-DO APPLICATION LOGIC ===

document.addEventListener('DOMContentLoaded', async () => {
  // Application State
  const state = {
    tasks: [],
    categories: [],
    lists: [],
    habits: [],
    goals: [],
    countdowns: [],
    stickers: [],
    currentList: 'Today',
    currentCategory: 'All',
    currentFilter: 'all', // all, active, completed, archived
    searchQuery: '',
    bulkSelected: new Set(),
    activeStopwatchId: null,
    stopwatchInterval: null,
    lastDeletedTask: null,
    pomodoro: {
      timeLeft: 25 * 60,
      totalTime: 25 * 60,
      timer: null,
      isRunning: false,
      mode: 'work', // work or break
      sessionsCompleted: 0
    },
    settings: {
      theme: 'pink',
      cursor: 'cherry',
      font: 'rounded',
      textSize: 'md',
      layout: 'comfortable',
      checkboxShape: 'flower',
      season: 'spring',
      customAccent: '#f472b6',
      wallpaper: '',
      petalsEnabled: true,
      autoLockMins: 5,
      lockOnBlur: false
    },
    isLocked: false,
    failedAttempts: 0,
    lockoutUntil: 0
  };

  // Instantiate Sub-Systems
  const mascot = new PastelMascot('mascot-avatar', 'mascot-bubble');
  const garden = new PastelGarden('garden-meadow-flowers');

  // DOM Elements
  const taskListEl = document.getElementById('task-items-list');
  const quickAddInput = document.getElementById('quick-add-input');
  const quickAddBtn = document.getElementById('quick-add-btn');
  const parserChipsBar = document.getElementById('parser-chips-bar');
  const searchInput = document.getElementById('search-tasks-input');
  const viewTabs = document.querySelectorAll('.view-tab');
  const todayProgressFill = document.getElementById('today-progress-fill');
  const todayProgressText = document.getElementById('today-progress-text');
  const streakCountBadge = document.getElementById('streak-count-badge');
  const eatFrogBanner = document.getElementById('eat-frog-banner');
  const bulkToolbar = document.getElementById('bulk-toolbar');
  const bulkCountSpan = document.getElementById('bulk-selected-count');

  // Quotes bundled list
  const dailyQuotes = [
    "“Bloom with grace wherever life plants you.” 🌸",
    "“Small sweet steps lead to big beautiful days.” ✨",
    "“Do something today that your future self will smile about.” 🍓",
    "“Like wildflowers, you must allow yourself to grow in all the places people thought you never would.” 🌼",
    "“Resting is part of blooming. Be gentle with yourself.” 🐰",
    "“You have everything it takes to create a lovely day.” 🍵"
  ];

  // --- INITIALIZATION ---
  async function init() {
    loadLocalPreferences();
    applyPreferences();
    await checkAuthStatus();

    if (!state.isLocked) {
      await loadAllData();
      startPetals();
      setupEventListeners();
      setupKeyboardShortcuts();
      setupInactivityTimer();
      checkBackupReminder();
      checkEndOfDayPrompt();
      registerServiceWorker();
    }
  }

  // --- LOCAL PREFERENCES & THEMES ---
  function loadLocalPreferences() {
    const saved = localStorage.getItem('pastel_todo_settings');
    if (saved) {
      try {
        state.settings = { ...state.settings, ...JSON.parse(saved) };
      } catch (e) {}
    }
  }

  function saveLocalPreferences() {
    localStorage.setItem('pastel_todo_settings', JSON.stringify(state.settings));
  }

  function applyPreferences() {
    document.documentElement.setAttribute('data-theme', state.settings.theme);
    document.body.className = '';
    document.body.classList.add(`font-${state.settings.font}`);
    document.body.classList.add(`text-size-${state.settings.textSize}`);
    document.body.classList.add(`layout-${state.settings.layout}`);
    document.body.classList.add(`shape-${state.settings.checkboxShape}`);
    document.body.classList.add(`season-${state.settings.season}`);

    if (state.settings.customAccent && state.settings.theme !== 'dark') {
      document.documentElement.style.setProperty('--accent-color', state.settings.customAccent);
    } else {
      document.documentElement.style.removeProperty('--accent-color');
    }

    if (state.settings.wallpaper) {
      document.body.style.backgroundImage = `url(${state.settings.wallpaper})`;
      document.body.classList.add('has-custom-wallpaper');
    } else {
      document.body.style.backgroundImage = 'none';
      document.body.classList.remove('has-custom-wallpaper');
    }

    if (window.flowerCursor) {
      window.flowerCursor.setCursor(state.settings.cursor);
    }
  }

  // --- FLOATING PETALS / LEAVES / SNOWFLAKES ---
  function startPetals() {
    const container = document.getElementById('petal-container');
    if (!container || !state.settings.petalsEnabled) {
      if (container) container.innerHTML = '';
      return;
    }
    container.innerHTML = '';

    const petalSVGs = {
      spring: `<svg width="20" height="20" viewBox="0 0 20 20"><ellipse cx="10" cy="10" rx="9" ry="6" fill="#fbcfe8" opacity="0.8" transform="rotate(35 10 10)"/></svg>`,
      summer: `<svg width="18" height="18" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="#fef08a" opacity="0.75"/></svg>`,
      autumn: `<svg width="22" height="22" viewBox="0 0 24 24"><path d="M12 2 C14 6 18 9 21 12 C18 15 15 19 12 22 C9 19 6 15 3 12 C6 9 10 6 12 2" fill="#fed7aa" opacity="0.8"/></svg>`,
      winter: `<svg width="16" height="16" viewBox="0 0 20 20"><path d="M10 2 L10 18 M2 10 L18 10 M4 4 L16 16 M4 16 L16 4" stroke="#e0f2fe" stroke-width="2" opacity="0.85"/></svg>`
    };

    const currentSvg = petalSVGs[state.settings.season] || petalSVGs.spring;

    for (let i = 0; i < 15; i++) {
      const p = document.createElement('div');
      p.className = 'floating-petal';
      p.innerHTML = currentSvg;
      p.style.left = `${Math.random() * 98}vw`;
      p.style.top = `-${Math.random() * 20 + 20}px`;
      p.style.animationDuration = `${Math.random() * 6 + 7}s`;
      p.style.animationDelay = `${Math.random() * 8}s`;
      container.appendChild(p);
    }
  }

  // --- AUTH & LOCK SCREEN ---
  async function checkAuthStatus() {
    try {
      const res = await fetch('/api/auth/status');
      const data = await res.json();
      state.authConfig = data;
      if (data.is_setup && !sessionStorage.getItem('pastel_unlocked')) {
        showLockScreen();
      }
    } catch (e) {
      console.log('Auth check error:', e);
    }
  }

  function showLockScreen() {
    state.isLocked = true;
    document.getElementById('lock-screen-modal').style.display = 'flex';
    document.querySelector('.app-container').classList.add('app-locked-blur');
    const hintText = document.getElementById('lock-hint-text');
    if (hintText && state.authConfig && state.authConfig.hint) {
      hintText.innerText = `Hint: ${state.authConfig.hint}`;
    }
  }

  function hideLockScreen() {
    state.isLocked = false;
    sessionStorage.setItem('pastel_unlocked', 'true');
    document.getElementById('lock-screen-modal').style.display = 'none';
    document.querySelector('.app-container').classList.remove('app-locked-blur');
  }

  // --- DATA LOADING & SYNC ---
  async function loadAllData() {
    await Promise.all([
      loadTasks(),
      loadCategories(),
      loadLists(),
      loadHabits(),
      loadGoals(),
      loadCountdowns(),
      loadStickers(),
      loadStats(),
      garden.loadFlowers()
    ]);
    renderAll();
  }

  async function loadTasks() {
    try {
      const params = new URLSearchParams();
      if (state.currentList !== 'All') params.append('list', state.currentList);
      if (state.currentCategory !== 'All') params.append('category', state.currentCategory);
      if (state.searchQuery) params.append('search', state.searchQuery);
      params.append('status', state.currentFilter);

      const res = await fetch(`/api/tasks?${params.toString()}`);
      if (res.ok) {
        state.tasks = await res.json();
      }
    } catch (e) {
      console.log('Error loading tasks:', e);
    }
  }

  async function loadCategories() {
    try {
      const res = await fetch('/api/categories');
      if (res.ok) state.categories = await res.json();
    } catch (e) {}
  }

  async function loadLists() {
    try {
      const res = await fetch('/api/lists');
      if (res.ok) state.lists = await res.json();
    } catch (e) {}
  }

  async function loadHabits() {
    try {
      const res = await fetch('/api/habits');
      if (res.ok) state.habits = await res.json();
    } catch (e) {}
  }

  async function loadGoals() {
    try {
      const res = await fetch('/api/goals');
      if (res.ok) state.goals = await res.json();
    } catch (e) {}
  }

  async function loadCountdowns() {
    try {
      const res = await fetch('/api/countdowns');
      if (res.ok) state.countdowns = await res.json();
    } catch (e) {}
  }

  async function loadStickers() {
    try {
      const res = await fetch('/api/stickers');
      if (res.ok) state.stickers = await res.json();
    } catch (e) {}
  }

  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) state.stats = await res.json();
    } catch (e) {}
  }

  // --- RENDERING ---
  function renderAll() {
    renderGreeting();
    renderListsMenu();
    renderCategoriesMenu();
    renderTasksList();
    renderEatTheFrog();
    renderProgressAndStreak();
    renderHabitsWidget();
    renderCountdownsWidget();
    renderDailyQuote();
    renderCalendarGrid();
    renderStatsView();
    renderStickersView();
  }

  function renderGreeting() {
    const greetingText = document.getElementById('greeting-heading');
    const todayDateEl = document.getElementById('today-date-text');
    const hour = new Date().getHours();
    let greet = "Good evening! 🌙";
    if (hour < 12) greet = "Good morning! ☀️";
    else if (hour < 17) greet = "Good afternoon! 🌸";

    if (greetingText) greetingText.innerText = greet;
    if (todayDateEl) {
      const options = { weekday: 'long', month: 'short', day: 'numeric' };
      todayDateEl.innerText = new Date().toLocaleDateString(undefined, options);
    }
  }

  function renderListsMenu() {
    const container = document.getElementById('sidebar-lists-menu');
    if (!container) return;
    container.innerHTML = '';

    // "All" pseudo list
    const allItem = document.createElement('div');
    allItem.className = `list-menu-item ${state.currentList === 'All' ? 'active' : ''}`;
    allItem.innerHTML = `<span>🌈 All Tasks</span><span class="list-item-badge">${state.tasks.length}</span>`;
    allItem.onclick = () => { state.currentList = 'All'; loadTasks().then(renderTasksList); };
    container.appendChild(allItem);

    state.lists.forEach(l => {
      const el = document.createElement('div');
      el.className = `list-menu-item ${state.currentList === l.name ? 'active' : ''}`;
      el.innerHTML = `
        <span>${l.icon} ${l.name} ${l.is_locked ? '🔒' : ''}</span>
      `;
      el.onclick = () => {
        if (l.is_locked && !sessionStorage.getItem(`unlocked_list_${l.name}`)) {
          promptLockedList(l.name);
        } else {
          state.currentList = l.name;
          loadTasks().then(renderTasksList);
          renderListsMenu();
        }
      };
      container.appendChild(el);
    });
  }

  function promptLockedList(listName) {
    const entered = prompt(`🔒 "${listName}" is a secret locked list. Enter master password:`);
    if (entered) {
      fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: entered })
      }).then(r => r.json()).then(res => {
        if (res.success) {
          sessionStorage.setItem(`unlocked_list_${listName}`, 'true');
          state.currentList = listName;
          loadTasks().then(renderTasksList);
          renderListsMenu();
        } else {
          showToast('Incorrect password for secret list! 🌸');
        }
      });
    }
  }

  function renderCategoriesMenu() {
    const container = document.getElementById('sidebar-categories-menu');
    if (!container) return;
    container.innerHTML = '';

    const allCat = document.createElement('div');
    allCat.className = `list-menu-item ${state.currentCategory === 'All' ? 'active' : ''}`;
    allCat.innerHTML = `<span>✨ All Categories</span>`;
    allCat.onclick = () => { state.currentCategory = 'All'; loadTasks().then(renderTasksList); renderCategoriesMenu(); };
    container.appendChild(allCat);

    state.categories.forEach(c => {
      const el = document.createElement('div');
      el.className = `list-menu-item ${state.currentCategory === c.name ? 'active' : ''}`;
      el.innerHTML = `<span><span class="category-dot" style="background:${c.color}"></span> ${c.name}</span>`;
      el.onclick = () => { state.currentCategory = c.name; loadTasks().then(renderTasksList); renderCategoriesMenu(); };
      container.appendChild(el);
    });
  }

  function renderTasksList() {
    if (!taskListEl) return;
    taskListEl.innerHTML = '';

    if (state.tasks.length === 0) {
      taskListEl.innerHTML = `
        <div class="empty-state-card">
          <div class="empty-state-art">🐰💤</div>
          <div class="empty-state-title">All caught up! Time to rest ✨</div>
          <div class="empty-state-desc">No tasks to display in this view. Enjoy the peaceful moments or add a cute task!</div>
        </div>
      `;
      return;
    }

    const todayStr = new Date().toISOString().split('T')[0];

    state.tasks.forEach((task, index) => {
      const card = document.createElement('div');
      card.className = `task-card ${task.is_completed ? 'completed-card' : ''}`;
      card.setAttribute('draggable', 'true');
      card.dataset.taskId = task.id;
      card.dataset.index = index;

      // Check if blocked by dependency
      const isBlocked = task.blocked_by_id && !isTaskDone(task.blocked_by_id);
      const isOverdue = task.due_date && task.due_date < todayStr && !task.is_completed;

      // Subtasks calculation
      const totalSub = task.subtasks ? task.subtasks.length : 0;
      const doneSub = task.subtasks ? task.subtasks.filter(s => s.is_completed).length : 0;
      const subPct = totalSub > 0 ? (doneSub / totalSub) * 100 : 0;

      // Checkbox Shape symbol
      let checkSymbol = '✓';
      if (state.settings.checkboxShape === 'heart') checkSymbol = task.is_completed ? '♥' : '♡';
      else if (state.settings.checkboxShape === 'star') checkSymbol = task.is_completed ? '★' : '☆';
      else checkSymbol = task.is_completed ? '✿' : '○';

      card.innerHTML = `
        <div class="washi-tape"></div>
        <div class="task-header">
          <span class="drag-handle" title="Drag to reorder">⋮⋮</span>
          
          <input type="checkbox" class="bulk-select-box" data-id="${task.id}" ${state.bulkSelected.has(task.id) ? 'checked' : ''} style="${state.bulkSelected.size > 0 ? 'display:inline-block' : 'display:none'}"/>

          <div class="custom-checkbox-wrapper" data-id="${task.id}" title="${task.is_completed ? 'Mark incomplete' : 'Complete task'}">
            <div class="custom-checkbox ${task.is_completed ? 'checked checkbox-anim-pop' : ''}">
              ${checkSymbol}
            </div>
          </div>

          <div class="task-body">
            <div class="task-title-row">
              ${task.is_pinned ? '<span class="pin-icon" title="Pinned to top">📌</span>' : ''}
              <span class="task-title ${task.is_completed ? 'strikethrough' : ''}">${escapeHtml(task.title)}</span>
            </div>

            ${task.notes ? `<div class="task-notes">${escapeHtml(task.notes)}</div>` : ''}

            <div class="task-meta-row">
              ${isOverdue ? '<span class="meta-badge badge-overdue">⚠️ Overdue</span>' : ''}
              ${task.due_date ? `<span class="meta-badge">📅 ${task.due_date}${task.due_time ? ' ' + task.due_time : ''}</span>` : ''}
              <span class="meta-badge"><span class="priority-dot dot-${task.priority}"></span> ${task.priority.toUpperCase()}</span>
              ${task.category ? `<span class="meta-badge">🏷️ ${escapeHtml(task.category)}</span>` : ''}
              ${task.recurring && task.recurring !== 'none' ? `<span class="meta-badge">🔄 ${task.recurring}</span>` : ''}
              ${task.time_estimate_minutes ? `<span class="meta-badge">⏱️ ~${task.time_estimate_minutes}m</span>` : ''}
              ${task.time_spent_seconds > 0 ? `<span class="meta-badge">⌛ ${formatSeconds(task.time_spent_seconds)}</span>` : ''}
              ${isBlocked ? `<span class="meta-badge dependency-lock-badge">🔒 Blocked by prerequisite</span>` : ''}
            </div>

            ${totalSub > 0 ? `
              <div class="subtasks-wrapper">
                <div class="subtasks-progress-bar"><div class="subtasks-progress-fill" style="width: ${subPct}%"></div></div>
                <div class="subtasks-list">
                  ${task.subtasks.map(s => `
                    <div class="subtask-item">
                      <span class="subtask-checkbox" data-sub-id="${s.id}">${s.is_completed ? '☑️' : '◻️'}</span>
                      <span style="${s.is_completed ? 'text-decoration: line-through; opacity: 0.6;' : ''}">${escapeHtml(s.title)}</span>
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}
          </div>

          <div class="task-actions">
            <button class="action-mini-btn btn-stopwatch" data-id="${task.id}" title="Track Time Stopwatch">⏱️</button>
            <button class="action-mini-btn btn-focus" data-id="${task.id}" title="Focus Mode">🎯</button>
            <button class="action-mini-btn btn-snooze" data-id="${task.id}" title="Snooze to Tomorrow">🌙</button>
            <button class="action-mini-btn btn-edit" data-id="${task.id}" title="Edit Task">✏️</button>
            <button class="action-mini-btn btn-delete" data-id="${task.id}" title="Delete Task">🗑️</button>
          </div>
        </div>
      `;

      // Event Listeners on Card Elements
      attachCardEvents(card, task);
      taskListEl.appendChild(card);
    });

    setupDragAndDrop();
  }

  function isTaskDone(taskId) {
    const found = state.tasks.find(t => t.id === taskId);
    return found ? Boolean(found.is_completed) : true;
  }

  function attachCardEvents(card, task) {
    // Checkbox toggle
    const chk = card.querySelector('.custom-checkbox-wrapper');
    if (chk) {
      chk.onclick = (e) => {
        e.stopPropagation();
        toggleTaskComplete(task.id);
      };
    }

    // Subtask click
    card.querySelectorAll('.subtask-checkbox').forEach(subEl => {
      subEl.onclick = async (e) => {
        e.stopPropagation();
        const sid = subEl.dataset.subId;
        await fetch(`/api/subtasks/${sid}/toggle`, { method: 'POST' });
        window.pastelAudio.playPop();
        await loadTasks();
        renderTasksList();
      };
    });

    // Stopwatch tracking
    const swBtn = card.querySelector('.btn-stopwatch');
    if (swBtn) {
      swBtn.onclick = (e) => {
        e.stopPropagation();
        toggleStopwatch(task.id, swBtn);
      };
    }

    // Focus mode button
    const focusBtn = card.querySelector('.btn-focus');
    if (focusBtn) {
      focusBtn.onclick = (e) => {
        e.stopPropagation();
        openFocusMode(task);
      };
    }

    // Snooze button
    const snoozeBtn = card.querySelector('.btn-snooze');
    if (snoozeBtn) {
      snoozeBtn.onclick = async (e) => {
        e.stopPropagation();
        const tom = new Date();
        tom.setDate(tom.getDate() + 1);
        const tomStr = tom.toISOString().split('T')[0];
        await fetch(`/api/tasks/${task.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ due_date: tomStr })
        });
        showToast(`Snoozed "${task.title}" to tomorrow! 🌙`);
        await loadTasks();
        renderTasksList();
      };
    }

    // Edit button
    const editBtn = card.querySelector('.btn-edit');
    if (editBtn) {
      editBtn.onclick = (e) => {
        e.stopPropagation();
        openEditTaskModal(task);
      };
    }

    // Delete button
    const delBtn = card.querySelector('.btn-delete');
    if (delBtn) {
      delBtn.onclick = async (e) => {
        e.stopPropagation();
        await deleteTask(task.id);
      };
    }

    // Long press or right click for bulk select mode
    card.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      toggleBulkSelection(task.id);
    });
  }

  // --- TASK ACTIONS ---
  async function toggleTaskComplete(taskId) {
    const t = state.tasks.find(x => x.id === taskId);
    if (!t) return;

    const newCompleted = t.is_completed ? 0 : 1;
    try {
      const res = await fetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_completed: newCompleted })
      });
      if (res.ok) {
        const updated = await res.json();
        if (newCompleted) {
          window.pastelAudio.playCompletionChime();
          triggerPetalBurst();
          mascot.setState('happy');
          if (updated.new_flower) {
            garden.addFlower(updated.new_flower);
          }
          checkStreakMilestones();
        }
        await loadTasks();
        renderTasksList();
        renderProgressAndStreak();
        renderEatTheFrog();
      }
    } catch (e) {
      console.log('Error toggling task:', e);
    }
  }

  async function deleteTask(taskId) {
    try {
      const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
      if (res.ok) {
        const data = await res.json();
        state.lastDeletedTask = data.deleted_task;
        showToast(`Task deleted.`, true); // show undo option
        await loadTasks();
        renderTasksList();
        renderProgressAndStreak();
        renderEatTheFrog();
      }
    } catch (e) {
      console.log('Error deleting task:', e);
    }
  }

  async function undoLastDelete() {
    if (!state.lastDeletedTask) return;
    const t = state.lastDeletedTask;
    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(t)
      });
      if (res.ok) {
        state.lastDeletedTask = null;
        showToast('Restored task successfully! 🌸');
        await loadTasks();
        renderTasksList();
      }
    } catch (e) {
      console.log('Error restoring task:', e);
    }
  }

  // --- STOPWATCH TIME TRACKING ---
  function toggleStopwatch(taskId, btnEl) {
    if (state.activeStopwatchId === taskId) {
      // Stop tracking
      clearInterval(state.stopwatchInterval);
      state.activeStopwatchId = null;
      btnEl.innerText = '⏱️';
      showToast('Time tracking paused 🌸');
      loadTasks().then(renderTasksList);
    } else {
      // If another was running, clear it
      if (state.stopwatchInterval) clearInterval(state.stopwatchInterval);

      state.activeStopwatchId = taskId;
      btnEl.innerText = '⏸️';
      showToast('Tracking time for this task... ⏱️');

      state.stopwatchInterval = setInterval(async () => {
        await fetch(`/api/tasks/${taskId}/time`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ seconds: 5 })
        });
      }, 5000);
    }
  }

  function formatSeconds(secs) {
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m`;
    const hrs = (mins / 60).toFixed(1);
    return `${hrs}h`;
  }

  // --- DRAG AND DROP REORDER ---
  function setupDragAndDrop() {
    let draggedCard = null;

    taskListEl.querySelectorAll('.task-card').forEach(card => {
      card.addEventListener('dragstart', (e) => {
        draggedCard = card;
        card.classList.add('dragging');
        e.dataTransfer.setData('text/plain', card.dataset.taskId);
      });

      card.addEventListener('dragend', () => {
        if (draggedCard) draggedCard.classList.remove('dragging');
        draggedCard = null;
      });

      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        const afterElement = getDragAfterElement(taskListEl, e.clientY);
        if (afterElement == null) {
          taskListEl.appendChild(draggedCard);
        } else {
          taskListEl.insertBefore(draggedCard, afterElement);
        }
      });
    });

    taskListEl.addEventListener('drop', async () => {
      const cards = taskListEl.querySelectorAll('.task-card');
      const taskIds = Array.from(cards).map(c => parseInt(c.dataset.taskId, 10));
      await fetch('/api/tasks/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_ids: taskIds })
      });
    });
  }

  function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.task-card:not(.dragging)')];
    return draggableElements.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset: offset, element: child };
      } else {
        return closest;
      }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
  }

  // --- SMART QUICK ADD & LIVE PARSER ---
  if (quickAddInput) {
    quickAddInput.addEventListener('input', () => {
      const parsed = SmartQuickAddParser.parse(quickAddInput.value);
      renderParserChips(parsed);
    });

    quickAddInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        submitQuickAdd();
      }
    });
  }

  if (quickAddBtn) {
    quickAddBtn.addEventListener('click', submitQuickAdd);
  }

  function renderParserChips(parsed) {
    if (!parserChipsBar) return;
    if (!parsed || !quickAddInput.value.trim()) {
      parserChipsBar.style.display = 'none';
      parserChipsBar.innerHTML = '';
      return;
    }

    parserChipsBar.style.display = 'flex';
    parserChipsBar.innerHTML = '';

    if (parsed.dueDate) {
      parserChipsBar.innerHTML += `<span class="preview-chip chip-date">📅 Due: ${parsed.dueDate} ${parsed.dueTime || ''}</span>`;
    }
    if (parsed.priority !== 'medium') {
      parserChipsBar.innerHTML += `<span class="preview-chip chip-priority">⚡ Priority: ${parsed.priority.toUpperCase()}</span>`;
    }
    if (parsed.category) {
      parserChipsBar.innerHTML += `<span class="preview-chip chip-tag">🏷️ #${parsed.category}</span>`;
    }
    if (parsed.estimateMinutes > 0) {
      parserChipsBar.innerHTML += `<span class="preview-chip chip-est">⏱️ ~${parsed.estimateMinutes}m</span>`;
    }
  }

  async function submitQuickAdd() {
    const val = quickAddInput.value.trim();
    if (!val) return;

    const parsed = SmartQuickAddParser.parse(val);
    const payload = {
      title: parsed.title,
      due_date: parsed.dueDate || (state.currentList === 'Today' ? new Date().toISOString().split('T')[0] : ''),
      due_time: parsed.dueTime || '',
      priority: parsed.priority || 'medium',
      category: parsed.category || (state.currentCategory !== 'All' ? state.currentCategory : 'Personal'),
      list_name: state.currentList !== 'All' ? state.currentList : 'Today',
      time_estimate_minutes: parsed.estimateMinutes || 0
    };

    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        quickAddInput.value = '';
        renderParserChips(null);
        window.pastelAudio.playPop();
        showToast(`Added: "${payload.title}" 🌸`);
        await loadTasks();
        renderTasksList();
        renderProgressAndStreak();
        renderEatTheFrog();
      }
    } catch (e) {
      console.log('Error adding task:', e);
    }
  }

  // --- EAT THE FROG RECOMMENDATION ---
  function renderEatTheFrog() {
    if (!eatFrogBanner) return;
    const pending = state.tasks.filter(t => !t.is_completed && !t.is_archived);
    if (pending.length === 0) {
      eatFrogBanner.style.display = 'none';
      return;
    }

    // Frog task: highest priority (high > medium > low), then longest estimate
    const sorted = [...pending].sort((a, b) => {
      const pScore = { high: 3, medium: 2, low: 1 };
      const scoreDiff = pScore[b.priority] - pScore[a.priority];
      if (scoreDiff !== 0) return scoreDiff;
      return (b.time_estimate_minutes || 0) - (a.time_estimate_minutes || 0);
    });

    const frog = sorted[0];
    eatFrogBanner.style.display = 'flex';
    eatFrogBanner.innerHTML = `
      <div class="frog-badge">🐸 Eat The Frog: <b>${escapeHtml(frog.title)}</b></div>
      <button class="btn-primary bloom-hover" id="btn-frog-tackle" style="padding: 6px 14px; font-size: 0.82rem;">Focus Now 🎯</button>
    `;

    document.getElementById('btn-frog-tackle').onclick = () => {
      openFocusMode(frog);
    };
  }

  // --- PROGRESS & STREAK ---
  function renderProgressAndStreak() {
    const todayStr = new Date().toISOString().split('T')[0];
    const todayTasks = state.tasks.filter(t => t.due_date === todayStr && !t.is_archived);
    const completedToday = todayTasks.filter(t => t.is_completed);

    const pct = todayTasks.length > 0 ? Math.round((completedToday.length / todayTasks.length) * 100) : 100;
    if (todayProgressFill) todayProgressFill.style.width = `${pct}%`;
    if (todayProgressText) todayProgressText.innerText = `${completedToday.length}/${todayTasks.length} Done (${pct}%)`;

    // Streak count
    let streak = parseInt(localStorage.getItem('pastel_streak_count') || '1', 10);
    if (todayTasks.length > 0 && completedToday.length === todayTasks.length) {
      streak = Math.max(streak, 3);
    }
    if (streakCountBadge) streakCountBadge.innerText = `🔥 ${streak} Day Streak`;
  }

  function checkStreakMilestones() {
    const streak = parseInt(localStorage.getItem('pastel_streak_count') || '1', 10);
    if (streak >= 3) {
      fetch('/api/stickers/streak_3/unlock', { method: 'POST' });
    }
    if (streak >= 7) {
      fetch('/api/stickers/streak_7/unlock', { method: 'POST' });
    }
  }

  // --- HABITS WIDGET ---
  function renderHabitsWidget() {
    const container = document.getElementById('habits-widget-container');
    if (!container) return;
    container.innerHTML = '';

    const todayStr = new Date().toISOString().split('T')[0];

    state.habits.forEach(habit => {
      const row = document.createElement('div');
      row.className = 'habit-item-row';
      const isDoneToday = Boolean(habit.logs && habit.logs[todayStr]);

      row.innerHTML = `
        <div class="habit-name-wrap">
          <span>${habit.icon}</span>
          <span>${escapeHtml(habit.name)}</span>
        </div>
        <button class="habit-check-btn ${isDoneToday ? 'completed' : ''}" data-id="${habit.id}">
          ${isDoneToday ? '✓' : ''}
        </button>
      `;

      row.querySelector('.habit-check-btn').onclick = async () => {
        await fetch(`/api/habits/${habit.id}/toggle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ date: todayStr })
        });
        window.pastelAudio.playPop();
        await loadHabits();
        renderHabitsWidget();
      };

      container.appendChild(row);
    });
  }

  // --- COUNTDOWNS WIDGET ---
  function renderCountdownsWidget() {
    const container = document.getElementById('countdowns-widget-container');
    if (!container) return;
    container.innerHTML = '';

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    state.countdowns.forEach(cd => {
      const target = new Date(cd.target_date);
      target.setHours(0, 0, 0, 0);
      const diffTime = target - today;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      const el = document.createElement('div');
      el.className = 'countdown-card-item';
      el.innerHTML = `
        <span>${cd.emoji} ${escapeHtml(cd.title)}</span>
        <span class="countdown-days-badge">${diffDays > 0 ? `${diffDays} days left` : diffDays === 0 ? 'Today! 🎉' : 'Passed'}</span>
      `;
      container.appendChild(el);
    });
  }

  // --- DAILY MOTIVATIONAL QUOTE ---
  function renderDailyQuote() {
    const quoteEl = document.getElementById('daily-quote-text');
    if (!quoteEl) return;
    const dayOfYear = Math.floor((new Date() - new Date(new Date().getFullYear(), 0, 0)) / 1000 / 60 / 60 / 24);
    const q = dailyQuotes[dayOfYear % dailyQuotes.length];
    quoteEl.innerText = q;

    const refreshBtn = document.getElementById('refresh-quote-btn');
    if (refreshBtn) {
      refreshBtn.onclick = () => {
        const rand = dailyQuotes[Math.floor(Math.random() * dailyQuotes.length)];
        quoteEl.innerText = rand;
      };
    }
  }

  // --- CALENDAR GRID VIEW ---
  function renderCalendarGrid() {
    const grid = document.getElementById('calendar-month-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const date = new Date();
    const year = date.getFullYear();
    const month = date.getMonth();

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayStr = date.toISOString().split('T')[0];

    // Blank cells before day 1
    for (let i = 0; i < firstDay; i++) {
      const blank = document.createElement('div');
      blank.className = 'calendar-day-cell';
      blank.style.opacity = '0.35';
      grid.appendChild(blank);
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const cellDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const cell = document.createElement('div');
      cell.className = `calendar-day-cell ${cellDateStr === todayStr ? 'is-today' : ''}`;
      cell.dataset.date = cellDateStr;

      cell.innerHTML = `<div class="calendar-day-num">${d}</div>`;

      // Find tasks due on this day
      const dayTasks = state.tasks.filter(t => t.due_date === cellDateStr);
      dayTasks.forEach(t => {
        const pill = document.createElement('div');
        pill.className = 'calendar-task-pill';
        pill.title = t.title;
        pill.innerText = `${t.is_completed ? '✓ ' : ''}${t.title}`;
        cell.appendChild(pill);
      });

      // Drag task onto calendar day to reschedule!
      cell.addEventListener('dragover', (e) => {
        e.preventDefault();
        cell.classList.add('droppable-hover');
      });

      cell.addEventListener('dragleave', () => {
        cell.classList.remove('droppable-hover');
      });

      cell.addEventListener('drop', async (e) => {
        e.preventDefault();
        cell.classList.remove('droppable-hover');
        const taskId = e.dataTransfer.getData('text/plain');
        if (taskId) {
          await fetch(`/api/tasks/${taskId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ due_date: cellDateStr })
          });
          showToast(`Rescheduled task to ${cellDateStr}! 📅`);
          await loadTasks();
          renderTasksList();
          renderCalendarGrid();
        }
      });

      grid.appendChild(cell);
    }
  }

  // --- STATS & INSIGHTS VIEW ---
  function renderStatsView() {
    if (!state.stats) return;
    const rateEl = document.getElementById('stats-completion-rate');
    const spentEl = document.getElementById('stats-time-spent');
    const weeklyBarContainer = document.getElementById('stats-weekly-chart');

    if (rateEl) rateEl.innerText = `${state.stats.completion_rate}%`;
    if (spentEl) spentEl.innerText = formatSeconds(state.stats.time_spent_total_seconds);

    if (weeklyBarContainer && state.stats.weekly_activity) {
      weeklyBarContainer.innerHTML = '';
      const maxCount = Math.max(...state.stats.weekly_activity.map(a => a.count), 1);
      state.stats.weekly_activity.forEach(a => {
        const col = document.createElement('div');
        col.style.display = 'flex';
        col.style.flexDirection = 'column';
        col.style.alignItems = 'center';
        col.style.gap = '4px';

        const hPct = Math.round((a.count / maxCount) * 85);
        col.innerHTML = `
          <div style="font-size:0.75rem; font-weight:700;">${a.count}</div>
          <div style="width: 22px; height: ${Math.max(hPct, 8)}px; background: var(--accent-color); border-radius: 8px;"></div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${a.day_name}</div>
        `;
        weeklyBarContainer.appendChild(col);
      });
    }
  }

  // --- STICKERS COLLECTION VIEW ---
  function renderStickersView() {
    const grid = document.getElementById('stickers-collection-grid');
    if (!grid) return;
    grid.innerHTML = '';

    state.stickers.forEach(s => {
      const card = document.createElement('div');
      card.className = `sticker-card ${s.unlocked_at ? '' : 'locked'}`;
      card.innerHTML = `
        <div class="sticker-emoji">${s.emoji}</div>
        <div class="sticker-name">${escapeHtml(s.name)}</div>
        <div class="sticker-desc">${s.unlocked_at ? '✨ Unlocked!' : escapeHtml(s.description)}</div>
      `;
      grid.appendChild(card);
    });
  }

  // --- POMODORO & FOCUS MODE ---
  function initPomodoroControls() {
    const startBtn = document.getElementById('pomodoro-start-btn');
    const resetBtn = document.getElementById('pomodoro-reset-btn');
    const timeDisplay = document.getElementById('pomodoro-timer-display');
    const modeBadge = document.getElementById('pomodoro-mode-badge');

    function updateDisplay() {
      const m = Math.floor(state.pomodoro.timeLeft / 60);
      const s = state.pomodoro.timeLeft % 60;
      const str = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
      if (timeDisplay) timeDisplay.innerText = str;
      const focusTimer = document.getElementById('focus-timer-clock');
      if (focusTimer) focusTimer.innerText = str;
    }

    if (startBtn) {
      startBtn.onclick = () => {
        if (state.pomodoro.isRunning) {
          clearInterval(state.pomodoro.timer);
          state.pomodoro.isRunning = false;
          startBtn.innerText = 'Start Focus ⏱️';
        } else {
          state.pomodoro.isRunning = true;
          startBtn.innerText = 'Pause ⏸️';
          state.pomodoro.timer = setInterval(() => {
            if (state.pomodoro.timeLeft > 0) {
              state.pomodoro.timeLeft--;
              updateDisplay();
            } else {
              clearInterval(state.pomodoro.timer);
              state.pomodoro.isRunning = false;
              startBtn.innerText = 'Start Focus ⏱️';
              window.pastelAudio.playPomodoroFinish();

              if (state.pomodoro.mode === 'work') {
                state.pomodoro.sessionsCompleted++;
                state.pomodoro.mode = 'break';
                state.pomodoro.timeLeft = 5 * 60;
                if (modeBadge) modeBadge.innerText = 'Relaxing Break 🍵';
                showToast('Great job! Enjoy a 5-minute break 🍵');
                mascot.setState('happy', "You worked so hard! Time for tea! 🍵");
              } else {
                state.pomodoro.mode = 'work';
                state.pomodoro.timeLeft = 25 * 60;
                if (modeBadge) modeBadge.innerText = 'Focus Session 🎯';
                showToast('Break finished! Ready to focus? 🌸');
              }
              updateDisplay();
            }
          }, 1000);
        }
      };
    }

    if (resetBtn) {
      resetBtn.onclick = () => {
        clearInterval(state.pomodoro.timer);
        state.pomodoro.isRunning = false;
        state.pomodoro.timeLeft = 25 * 60;
        state.pomodoro.mode = 'work';
        if (startBtn) startBtn.innerText = 'Start Focus ⏱️';
        if (modeBadge) modeBadge.innerText = 'Focus Session 🎯';
        updateDisplay();
      };
    }

    updateDisplay();
  }

  function openFocusMode(task) {
    const overlay = document.getElementById('focus-mode-overlay');
    const titleEl = document.getElementById('focus-task-title');
    if (titleEl) titleEl.innerText = task.title;
    if (overlay) overlay.classList.add('open');

    document.getElementById('focus-close-btn').onclick = () => {
      overlay.classList.remove('open');
    };
    document.getElementById('focus-done-btn').onclick = async () => {
      await toggleTaskComplete(task.id);
      overlay.classList.remove('open');
    };
  }

  // --- CONFETTI & PETAL BURST ---
  function triggerPetalBurst() {
    const burstCount = 20;
    const colors = ['#f472b6', '#fbcfe8', '#facc15', '#bbf7d0', '#c084fc', '#67e8f9'];
    for (let i = 0; i < burstCount; i++) {
      const piece = document.createElement('div');
      piece.className = 'confetti-piece';
      piece.style.left = `${50 + (Math.random() * 30 - 15)}%`;
      piece.style.top = `${40 + (Math.random() * 20 - 10)}%`;
      piece.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
      piece.style.transform = `rotate(${Math.random() * 360}deg)`;
      document.body.appendChild(piece);
      setTimeout(() => piece.remove(), 850);
    }
  }

  // --- TOAST NOTIFICATIONS ---
  function showToast(message, allowUndo = false) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'cute-toast';
    toast.innerHTML = `
      <span>🌸 ${escapeHtml(message)}</span>
      ${allowUndo ? '<button class="toast-undo-btn">Undo (Ctrl+Z)</button>' : ''}
    `;

    if (allowUndo) {
      toast.querySelector('.toast-undo-btn').onclick = () => {
        undoLastDelete();
        toast.remove();
      };
    }

    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4500);
  }

  // --- EVENT LISTENERS & SHORTCUTS ---
  function setupEventListeners() {
    // Search input
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim();
        loadTasks().then(renderTasksList);
      });
    }

    // Filter pills
    document.querySelectorAll('.filter-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        state.currentFilter = pill.dataset.filter;
        loadTasks().then(renderTasksList);
      });
    });

    // View navigation tabs
    viewTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        viewTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const viewName = tab.dataset.view;

        document.querySelectorAll('.view-section').forEach(s => s.style.display = 'none');
        const targetView = document.getElementById(`view-${viewName}`);
        if (targetView) targetView.style.display = 'block';

        if (viewName === 'calendar') renderCalendarGrid();
        if (viewName === 'stats') renderStatsView();
        if (viewName === 'garden') garden.render();
      });
    });

    // Mood check-in buttons
    document.querySelectorAll('.mood-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        const mood = btn.dataset.mood;
        await fetch('/api/moods', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mood_emoji: mood })
        });
        showToast(`Mood logged: ${mood} 🌸`);
        mascot.say(`Logged your mood: ${mood}! I hope you have the sweetest day! ✨`);
      });
    });

    // Bulk action toolbar buttons
    document.getElementById('bulk-complete-btn')?.addEventListener('click', () => handleBulkAction('complete'));
    document.getElementById('bulk-delete-btn')?.addEventListener('click', () => handleBulkAction('delete'));
    document.getElementById('bulk-snooze-btn')?.addEventListener('click', () => handleBulkAction('snooze'));

    // Sound mute toggle button
    const muteBtn = document.getElementById('mute-toggle-btn');
    if (muteBtn) {
      muteBtn.innerText = window.pastelAudio.isMuted() ? '🔇' : '🔔';
      muteBtn.onclick = () => {
        const isMuted = window.pastelAudio.toggleMute();
        muteBtn.innerText = isMuted ? '🔇' : '🔔';
        showToast(isMuted ? 'Sound muted 🔇' : 'Sound unmuted 🔔');
      };
    }

    // Panic Lock button
    document.getElementById('panic-lock-btn')?.addEventListener('click', () => {
      showLockScreen();
    });

    // Settings Modal Trigger
    document.getElementById('open-settings-btn')?.addEventListener('click', openSettingsModal);
    document.getElementById('shortcuts-btn')?.addEventListener('click', () => {
      document.getElementById('shortcuts-modal').classList.add('open');
    });

    // AI PDF Summarizer Modal
    document.getElementById('open-pdf-modal-btn')?.addEventListener('click', () => {
      document.getElementById('pdf-modal').classList.add('open');
    });

    // Share Modal Trigger
    document.getElementById('share-list-btn')?.addEventListener('click', openShareModal);

    // Template Drop Buttons
    document.querySelectorAll('.template-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const type = btn.dataset.template;
        await fetch(`/api/templates/${type}`, { method: 'POST' });
        showToast(`Template added to your to-do list! 🌸`);
        await loadTasks();
        renderTasksList();
      });
    });

    // Close buttons on all modals
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
      });
    });

    initPomodoroControls();
    initSettingsForm();
    initEditTaskModal();
    initPdfUpload();
    initLockScreenForm();
  }

  function setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      // Escape closes modals or triggers panic lock
      if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal-overlay.open');
        if (openModal) {
          openModal.classList.remove('open');
        } else if (e.altKey) {
          showLockScreen();
        }
      }

      // Alt + L for Panic Lock
      if (e.altKey && (e.key === 'l' || e.key === 'L')) {
        showLockScreen();
      }

      // If typing in input, ignore normal shortcuts
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        return;
      }

      // N for new task
      if (e.key === 'n' || e.key === 'N') {
        e.preventDefault();
        quickAddInput?.focus();
      }

      // / for search
      if (e.key === '/') {
        e.preventDefault();
        searchInput?.focus();
      }

      // Ctrl + Z for undo
      if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        undoLastDelete();
      }

      // ? for shortcuts help
      if (e.key === '?') {
        document.getElementById('shortcuts-modal')?.classList.add('open');
      }
    });
  }

  // --- BULK SELECTION ---
  function toggleBulkSelection(taskId) {
    if (state.bulkSelected.has(taskId)) {
      state.bulkSelected.delete(taskId);
    } else {
      state.bulkSelected.add(taskId);
    }
    updateBulkToolbar();
    renderTasksList();
  }

  function updateBulkToolbar() {
    if (!bulkToolbar || !bulkCountSpan) return;
    if (state.bulkSelected.size > 0) {
      bulkToolbar.style.display = 'flex';
      bulkCountSpan.innerText = `${state.bulkSelected.size} selected`;
    } else {
      bulkToolbar.style.display = 'none';
    }
  }

  async function handleBulkAction(action) {
    const ids = Array.from(state.bulkSelected);
    if (ids.length === 0) return;

    await fetch('/api/tasks/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_ids: ids, action: action })
    });

    state.bulkSelected.clear();
    updateBulkToolbar();
    showToast(`Bulk ${action} completed! 🌸`);
    await loadTasks();
    renderTasksList();
  }

  // --- EDIT TASK MODAL ---
  function openEditTaskModal(task) {
    const modal = document.getElementById('edit-task-modal');
    if (!modal) return;

    document.getElementById('edit-task-id').value = task.id;
    document.getElementById('edit-task-title-input').value = task.title || '';
    document.getElementById('edit-task-notes-input').value = task.notes || '';
    document.getElementById('edit-task-due-date').value = task.due_date || '';
    document.getElementById('edit-task-due-time').value = task.due_time || '';
    document.getElementById('edit-task-priority').value = task.priority || 'medium';
    document.getElementById('edit-task-estimate').value = task.time_estimate_minutes || 0;
    document.getElementById('edit-task-recurring').value = task.recurring || 'none';

    // Populate category dropdown
    const catSelect = document.getElementById('edit-task-category');
    if (catSelect) {
      catSelect.innerHTML = '';
      state.categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.name;
        opt.innerText = c.name;
        if (c.name === task.category) opt.selected = true;
        catSelect.appendChild(opt);
      });
    }

    // Populate list dropdown
    const listSelect = document.getElementById('edit-task-list');
    if (listSelect) {
      listSelect.innerHTML = '';
      state.lists.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.name;
        opt.innerText = `${l.icon} ${l.name}`;
        if (l.name === task.list_name) opt.selected = true;
        listSelect.appendChild(opt);
      });
    }

    modal.classList.add('open');
  }

  function initEditTaskModal() {
    document.getElementById('save-task-edit-btn')?.addEventListener('click', async () => {
      const tid = document.getElementById('edit-task-id').value;
      const title = document.getElementById('edit-task-title-input').value.trim();
      if (!title) {
        showToast('Task title is required! 🌸');
        return;
      }
      const notes = document.getElementById('edit-task-notes-input').value.trim();
      const due_date = document.getElementById('edit-task-due-date').value;
      const due_time = document.getElementById('edit-task-due-time').value;
      const priority = document.getElementById('edit-task-priority').value;
      const time_estimate_minutes = parseInt(document.getElementById('edit-task-estimate').value || '0', 10);
      const category = document.getElementById('edit-task-category').value;
      const list_name = document.getElementById('edit-task-list').value;
      const recurring = document.getElementById('edit-task-recurring').value;

      try {
        const res = await fetch(`/api/tasks/${tid}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title, notes, due_date, due_time, priority, time_estimate_minutes, category, list_name, recurring
          })
        });
        if (res.ok) {
          document.getElementById('edit-task-modal').classList.remove('open');
          showToast('Task updated successfully! 🌸');
          await loadTasks();
          renderTasksList();
          renderEatTheFrog();
        }
      } catch (e) {
        console.log('Error updating task:', e);
      }
    });
  }

  // --- SETTINGS MODAL & FORM ---
  function openSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (!modal) return;

    document.getElementById('setting-theme-select').value = state.settings.theme;
    document.getElementById('setting-cursor-select').value = state.settings.cursor;
    document.getElementById('setting-font-select').value = state.settings.font;
    document.getElementById('setting-size-select').value = state.settings.textSize;
    document.getElementById('setting-layout-select').value = state.settings.layout;
    document.getElementById('setting-shape-select').value = state.settings.checkboxShape;
    document.getElementById('setting-season-select').value = state.settings.season;
    document.getElementById('setting-accent-picker').value = state.settings.customAccent;
    document.getElementById('setting-petals-toggle').checked = state.settings.petalsEnabled;

    modal.classList.add('open');
  }

  function initSettingsForm() {
    document.getElementById('save-settings-btn')?.addEventListener('click', () => {
      state.settings.theme = document.getElementById('setting-theme-select').value;
      state.settings.cursor = document.getElementById('setting-cursor-select').value;
      state.settings.font = document.getElementById('setting-font-select').value;
      state.settings.textSize = document.getElementById('setting-size-select').value;
      state.settings.layout = document.getElementById('setting-layout-select').value;
      state.settings.checkboxShape = document.getElementById('setting-shape-select').value;
      state.settings.season = document.getElementById('setting-season-select').value;
      state.settings.customAccent = document.getElementById('setting-accent-picker').value;
      state.settings.petalsEnabled = document.getElementById('setting-petals-toggle').checked;

      saveLocalPreferences();
      applyPreferences();
      startPetals();
      renderTasksList();

      document.getElementById('settings-modal').classList.remove('open');
      showToast('Settings saved successfully! 🌸');
    });

    // Custom Wallpaper Upload
    document.getElementById('wallpaper-upload-input')?.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          state.settings.wallpaper = event.target.result;
          saveLocalPreferences();
          applyPreferences();
          showToast('Wallpaper background applied! 🌸');
        };
        reader.readAsDataURL(file);
      }
    });

    document.getElementById('clear-wallpaper-btn')?.addEventListener('click', () => {
      state.settings.wallpaper = '';
      saveLocalPreferences();
      applyPreferences();
      showToast('Wallpaper cleared! 🌸');
    });

    // Export to JSON & CSV
    document.getElementById('export-json-btn')?.addEventListener('click', () => {
      window.location.href = '/api/export?format=json';
    });
    document.getElementById('export-csv-btn')?.addEventListener('click', () => {
      window.location.href = '/api/export?format=csv';
    });

    // Import from JSON
    document.getElementById('import-file-input')?.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/import', { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        showToast(`Imported ${data.count} tasks! 🌸`);
        await loadAllData();
      } else {
        showToast(data.error || 'Import failed');
      }
    });
  }

  // --- AI PDF SUMMARISER ---
  function initPdfUpload() {
    const dropZone = document.getElementById('pdf-drop-zone');
    const fileInput = document.getElementById('pdf-file-input');
    const statusText = document.getElementById('pdf-status-text');
    const summaryBox = document.getElementById('pdf-summary-result');
    const addTasksBtn = document.getElementById('pdf-add-tasks-btn');
    let extractedTasks = [];

    if (!dropZone || !fileInput) return;

    dropZone.onclick = () => fileInput.click();

    fileInput.onchange = (e) => {
      const file = e.target.files[0];
      if (file) handlePdfFile(file);
    };

    dropZone.ondragover = (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--accent-hover)';
    };

    dropZone.ondragleave = () => {
      dropZone.style.borderColor = 'var(--card-border)';
    };

    dropZone.ondrop = (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--card-border)';
      const file = e.dataTransfer.files[0];
      if (file) handlePdfFile(file);
    };

    async function handlePdfFile(file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please choose a valid PDF file! 🌸');
        return;
      }
      statusText.innerText = 'Extracting and summarizing with AI... 🌸';
      statusText.style.display = 'block';
      summaryBox.style.display = 'none';
      addTasksBtn.style.display = 'none';

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/ai/summarize-pdf', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (res.ok) {
          statusText.style.display = 'none';
          summaryBox.style.display = 'block';
          summaryBox.innerHTML = `
            <h4 style="color:var(--accent-hover); margin-bottom:6px;">Summary:</h4>
            <p style="font-size:0.9rem; margin-bottom:12px;">${escapeHtml(data.summary)}</p>
            <h4 style="color:var(--accent-hover); margin-bottom:6px;">Extracted Tasks (${data.tasks.length}):</h4>
            <ul style="font-size:0.85rem; padding-left:18px;">
              ${data.tasks.map(t => `<li><b>${escapeHtml(t.title)}</b> (${t.priority})</li>`).join('')}
            </ul>
            ${data.notice ? `<div style="font-size:0.75rem; color:var(--text-muted); margin-top:10px;">${data.notice}</div>` : ''}
          `;
          extractedTasks = data.tasks;
          if (extractedTasks.length > 0) {
            addTasksBtn.style.display = 'block';
          }
        } else {
          statusText.innerText = data.error || 'Failed to process PDF.';
        }
      } catch (err) {
        statusText.innerText = 'Error uploading PDF.';
      }
    }

    addTasksBtn.onclick = async () => {
      for (const t of extractedTasks) {
        await fetch('/api/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: t.title,
            notes: t.notes || 'Extracted from PDF',
            priority: t.priority || 'medium',
            category: t.category || 'School',
            list_name: 'Today'
          })
        });
      }
      showToast(`Added ${extractedTasks.length} tasks from PDF! 🌸`);
      document.getElementById('pdf-modal').classList.remove('open');
      await loadTasks();
      renderTasksList();
    };
  }

  // --- SHARE LIST MODAL ---
  function openShareModal() {
    const modal = document.getElementById('share-modal');
    if (!modal) return;

    document.getElementById('share-generate-btn').onclick = async () => {
      const res = await fetch('/api/share', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `My Pastel To-Dos (${state.currentList})`,
          tasks: state.tasks
        })
      });
      const data = await res.json();
      if (res.ok) {
        document.getElementById('share-link-input').value = data.share_url;
        document.getElementById('share-link-row').style.display = 'flex';
      }
    };

    document.getElementById('share-copy-btn').onclick = () => {
      const input = document.getElementById('share-link-input');
      input.select();
      navigator.clipboard.writeText(input.value);
      showToast('Link copied to clipboard! 🌸');
    };

    document.getElementById('share-print-btn').onclick = () => {
      window.print();
    };

    modal.classList.add('open');
  }

  // --- INACTIVITY AUTO-LOCK ---
  function setupInactivityTimer() {
    let idleSecs = 0;
    const resetIdle = () => { idleSecs = 0; };

    window.addEventListener('mousemove', resetIdle, { passive: true });
    window.addEventListener('keydown', resetIdle, { passive: true });

    setInterval(() => {
      idleSecs++;
      const limitSecs = (state.settings.autoLockMins || 5) * 60;
      if (state.authConfig && state.authConfig.is_setup && idleSecs >= limitSecs && !state.isLocked) {
        showLockScreen();
      }
    }, 1000);

    // Lock on blur / tab switch
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && state.settings.lockOnBlur && state.authConfig && state.authConfig.is_setup) {
        showLockScreen();
      }
    });
  }

  function initLockScreenForm() {
    const submitBtn = document.getElementById('lock-submit-btn');
    const passInput = document.getElementById('lock-password-input');
    const errText = document.getElementById('lock-error-text');

    if (!submitBtn || !passInput) return;

    submitBtn.onclick = async () => {
      const now = Date.now();
      if (now < state.lockoutUntil) {
        const waitSec = Math.ceil((state.lockoutUntil - now) / 1000);
        errText.innerText = `Too many wrong attempts! Please wait ${waitSec}s.`;
        return;
      }

      const pw = passInput.value;
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        passInput.value = '';
        errText.innerText = '';
        state.failedAttempts = 0;
        hideLockScreen();
        await loadAllData();
      } else {
        state.failedAttempts++;
        if (state.failedAttempts >= 3) {
          const delay = Math.min(state.failedAttempts * 5, 30);
          state.lockoutUntil = Date.now() + delay * 1000;
          errText.innerText = `Incorrect! Locked out for ${delay} seconds.`;
        } else {
          errText.innerText = 'Incorrect password, please try again.';
        }
      }
    };

    passInput.onkeydown = (e) => {
      if (e.key === 'Enter') submitBtn.click();
    };
  }

  // --- AUTO BACKUP & REMINDERS ---
  function checkBackupReminder() {
    const lastBackup = localStorage.getItem('pastel_last_backup_reminder');
    const now = Date.now();
    if (!lastBackup || (now - parseInt(lastBackup, 10)) > 7 * 24 * 60 * 60 * 1000) { // 7 days
      setTimeout(() => {
        showToast('💡 Cute reminder: Back up your to-do lists via Settings > Export JSON!');
        localStorage.setItem('pastel_last_backup_reminder', String(now));
      }, 5000);
    }
  }

  function checkEndOfDayPrompt() {
    const hour = new Date().getHours();
    if (hour >= 18) { // 6 PM onwards
      const pendingToday = state.tasks.filter(t => !t.is_completed && t.due_date === new Date().toISOString().split('T')[0]);
      if (pendingToday.length > 0) {
        setTimeout(() => {
          showToast(`Gentle evening reminder: ${pendingToday.length} tasks left today. Would you like to snooze them to tomorrow? 🌸`);
        }, 8000);
      }
    }
  }

  // --- SERVICE WORKER REGISTRATION ---
  function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(err => {
        console.log('SW registration error:', err);
      });
    }
  }

  // --- UTILS ---
  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Run initialization
  await init();
});

