// === CUTE SVG MASCOT COMPANION ===

class PastelMascot {
  constructor(containerId, bubbleId) {
    this.container = document.getElementById(containerId);
    this.bubble = document.getElementById(bubbleId);
    this.mascotType = localStorage.getItem('pastel_mascot_type') || 'bunny';
    this.state = 'idle'; // idle, happy, cheer, sleep
    this.idleTimer = null;
    this.cheerPhrases = [
      "Yay! You're doing so wonderful! 🌸",
      "One step closer to your dreams! ✨",
      "Look at that bloom! Keep going! 🐰",
      "You're a productivity star! 💖",
      "So proud of your hard work! 🍰"
    ];
    this.idlePhrases = [
      "I'm here cheering for you! 🎀",
      "Take a sip of water when you need to 💧",
      "Your garden is blooming beautifully! 🌱",
      "Take it easy, one petal at a time 🌸"
    ];

    this.render();
    this.setupIdleDetection();
  }

  setMascotType(type) {
    this.mascotType = type;
    localStorage.setItem('pastel_mascot_type', type);
    this.render();
  }

  render() {
    if (!this.container) return;

    if (this.mascotType === 'flower') {
      this.container.innerHTML = `
        <svg viewBox="0 0 100 100" class="mascot-svg mascot-state-${this.state}">
          <!-- Stem and leaves -->
          <path d="M 50 70 Q 52 90 50 96" stroke="#4ade80" stroke-width="6" stroke-linecap="round" fill="none"/>
          <ellipse cx="36" cy="84" rx="10" ry="5" fill="#86efac" transform="rotate(-30 36 84)"/>
          <ellipse cx="64" cy="80" rx="10" ry="5" fill="#86efac" transform="rotate(30 64 80)"/>
          <!-- Petals -->
          ${[0, 60, 120, 180, 240, 300].map(deg => `
            <circle cx="50" cy="20" r="14" fill="#f472b6" transform="rotate(${deg} 50 50)"/>
          `).join('')}
          <!-- Face Center -->
          <circle cx="50" cy="50" r="22" fill="#fef08a"/>
          <!-- Eyes -->
          <ellipse class="mascot-eye" cx="42" cy="46" rx="3.5" ry="4" fill="#4a3b43"/>
          <ellipse class="mascot-eye" cx="58" cy="46" rx="3.5" ry="4" fill="#4a3b43"/>
          <circle cx="43" cy="44" r="1.2" fill="#ffffff"/>
          <circle cx="59" cy="44" r="1.2" fill="#ffffff"/>
          <!-- Blush -->
          <ellipse cx="37" cy="53" rx="4" ry="2.5" fill="#f43f5e" opacity="0.45"/>
          <ellipse cx="63" cy="53" rx="4" ry="2.5" fill="#f43f5e" opacity="0.45"/>
          <!-- Smile -->
          <path d="M 45 54 Q 50 59 55 54" stroke="#4a3b43" stroke-width="2.5" stroke-linecap="round" fill="none"/>
        </svg>
      `;
    } else {
      // Bunny Mascot (Default)
      this.container.innerHTML = `
        <svg viewBox="0 0 100 100" class="mascot-svg mascot-state-${this.state}">
          <!-- Bunny Ears -->
          <ellipse cx="36" cy="24" rx="7" ry="20" fill="#ffffff" stroke="#fce7f3" stroke-width="2" transform="rotate(-10 36 24)"/>
          <ellipse cx="36" cy="24" rx="4" ry="14" fill="#fbcfe8" transform="rotate(-10 36 24)"/>
          <ellipse cx="64" cy="24" rx="7" ry="20" fill="#ffffff" stroke="#fce7f3" stroke-width="2" transform="rotate(10 64 24)"/>
          <ellipse cx="64" cy="24" rx="4" ry="14" fill="#fbcfe8" transform="rotate(10 64 24)"/>
          <!-- Flower Crown -->
          <circle cx="42" cy="38" r="5" fill="#f472b6"/>
          <circle cx="50" cy="36" r="6" fill="#facc15"/>
          <circle cx="58" cy="38" r="5" fill="#c084fc"/>
          <!-- Bunny Head -->
          <ellipse cx="50" cy="62" rx="30" ry="26" fill="#ffffff" stroke="#fce7f3" stroke-width="2"/>
          <!-- Eyes -->
          <ellipse class="mascot-eye" cx="40" cy="60" rx="3.5" ry="4.5" fill="#4a3b43"/>
          <ellipse class="mascot-eye" cx="60" cy="60" rx="3.5" ry="4.5" fill="#4a3b43"/>
          <circle cx="41.5" cy="58.5" r="1.3" fill="#ffffff"/>
          <circle cx="61.5" cy="58.5" r="1.3" fill="#ffffff"/>
          <!-- Cheeks -->
          <ellipse cx="33" cy="67" rx="5" ry="3" fill="#f43f5e" opacity="0.4"/>
          <ellipse cx="67" cy="67" rx="5" ry="3" fill="#f43f5e" opacity="0.4"/>
          <!-- Nose & Mouth -->
          <polygon points="48,65 52,65 50,68" fill="#f472b6"/>
          <path d="M 46 69 Q 50 72 50 69 Q 50 72 54 69" stroke="#4a3b43" stroke-width="2" stroke-linecap="round" fill="none"/>
        </svg>
      `;
    }
  }

  setState(state, customPhrase = null) {
    this.state = state;
    this.render();

    if (customPhrase) {
      this.say(customPhrase);
    } else if (state === 'happy' || state === 'cheer') {
      const p = this.cheerPhrases[Math.floor(Math.random() * this.cheerPhrases.length)];
      this.say(p);
    } else if (state === 'sleep') {
      this.say("Zzz... resting softly 💤");
    }

    if (state !== 'idle' && state !== 'sleep') {
      clearTimeout(this.resetTimer);
      this.resetTimer = setTimeout(() => {
        this.setState('idle');
      }, 3000);
    }
  }

  say(phrase) {
    if (!this.bubble) return;
    this.bubble.innerText = phrase;
    this.bubble.style.animation = 'cutePop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
  }

  setupIdleDetection() {
    let idleCounter = 0;
    const resetIdle = () => {
      idleCounter = 0;
      if (this.state === 'sleep') {
        this.setState('idle', "Welcome back! Let's do this! 🌸");
      }
    };

    window.addEventListener('mousemove', resetIdle, { passive: true });
    window.addEventListener('keydown', resetIdle, { passive: true });
    window.addEventListener('touchstart', resetIdle, { passive: true });

    setInterval(() => {
      idleCounter++;
      if (idleCounter >= 45 && this.state !== 'sleep') { // 45 seconds idle
        this.setState('sleep');
      }
    }, 1000);

    // Click on mascot for a cheer
    if (this.container) {
      this.container.addEventListener('click', () => {
        this.setState('happy');
      });
    }
  }
}

window.PastelMascot = PastelMascot;

