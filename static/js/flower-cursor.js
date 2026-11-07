// === CUTE FLOWER CURSORS & PETAL TRAIL ===

class FlowerCursorManager {
  constructor() {
    this.cursorType = localStorage.getItem('pastel_cursor_type') || 'cherry';
    this.trailEnabled = localStorage.getItem('pastel_petal_trail') !== 'false';
    this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    this.cursorEl = null;
    this.lastTrailTime = 0;

    this.init();
  }

  init() {
    if (this.isTouchDevice) {
      this.initTouchSparkles();
      return;
    }

    this.createCursorElement();
    this.attachMouseEvents();
    this.updateCursorSvg();
  }

  createCursorElement() {
    this.cursorEl = document.createElement('div');
    this.cursorEl.id = 'custom-flower-cursor';
    this.cursorEl.style.position = 'fixed';
    this.cursorEl.style.pointerEvents = 'none';
    this.cursorEl.style.zIndex = '999999';
    this.cursorEl.style.width = '36px';
    this.cursorEl.style.height = '36px';
    this.cursorEl.style.transform = 'translate(-50%, -50%)';
    this.cursorEl.style.transition = 'transform 0.15s ease-out, filter 0.2s';
    document.body.appendChild(this.cursorEl);
    document.body.style.cursor = 'none';

    // Ensure all clickable things keep custom cursor
    const style = document.createElement('style');
    style.innerHTML = `* { cursor: none !important; }`;
    document.head.appendChild(style);
  }

  setCursor(type) {
    this.cursorType = type;
    localStorage.setItem('pastel_cursor_type', type);
    this.updateCursorSvg();
  }

  toggleTrail(enabled) {
    this.trailEnabled = enabled !== undefined ? enabled : !this.trailEnabled;
    localStorage.setItem('pastel_petal_trail', this.trailEnabled);
    return this.trailEnabled;
  }

  updateCursorSvg(bloomed = false) {
    if (!this.cursorEl) return;
    const scale = bloomed ? '1.4' : '1.0';
    const petScale = bloomed ? '1.25' : '1.0';

    let svg = '';
    switch (this.cursorType) {
      case 'daisy':
        svg = `
          <svg viewBox="0 0 100 100" width="100%" height="100%" style="transform: scale(${scale}); transform-origin: center; transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);">
            <g transform="translate(50, 50)">
              <!-- Daisy white petals with yellow tint -->
              ${[0, 45, 90, 135, 180, 225, 270, 315].map(deg => `
                <ellipse cx="0" cy="-32" rx="10" ry="20" fill="#fef9c3" stroke="#fef08a" stroke-width="2" transform="rotate(${deg}) scale(1, ${petScale})"/>
              `).join('')}
              <circle cx="0" cy="0" r="16" fill="#facc15"/>
              <circle cx="0" cy="0" r="12" fill="#eab308"/>
            </g>
          </svg>
        `;
        break;

      case 'forgetmenot':
        svg = `
          <svg viewBox="0 0 100 100" width="100%" height="100%" style="transform: scale(${scale}); transform-origin: center; transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);">
            <g transform="translate(50, 50)">
              ${[0, 72, 144, 216, 288].map(deg => `
                <ellipse cx="0" cy="-28" rx="14" ry="18" fill="#38bdf8" stroke="#bae6fd" stroke-width="2" transform="rotate(${deg}) scale(1, ${petScale})"/>
              `).join('')}
              <circle cx="0" cy="0" r="12" fill="#fef08a"/>
              <circle cx="0" cy="0" r="7" fill="#ffffff"/>
            </g>
          </svg>
        `;
        break;

      case 'clover':
        svg = `
          <svg viewBox="0 0 100 100" width="100%" height="100%" style="transform: scale(${scale}); transform-origin: center; transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);">
            <g transform="translate(50, 50)">
              <!-- 4-leaf clover blossom -->
              ${[0, 90, 180, 270].map(deg => `
                <path d="M 0 0 C -18 -18, -25 -38, 0 -42 C 25 -38, 18 -18, 0 0" fill="#4ade80" stroke="#86efac" stroke-width="2" transform="rotate(${deg}) scale(${petScale})"/>
              `).join('')}
              <circle cx="0" cy="0" r="8" fill="#bbf7d0"/>
            </g>
          </svg>
        `;
        break;

      case 'lavender':
        svg = `
          <svg viewBox="0 0 100 100" width="100%" height="100%" style="transform: scale(${scale}); transform-origin: center; transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);">
            <g transform="translate(50, 50) rotate(-25)">
              <line x1="0" y1="-40" x2="0" y2="40" stroke="#86efac" stroke-width="4" stroke-linecap="round"/>
              <ellipse cx="-10" cy="-28" rx="8" ry="12" fill="#c084fc" transform="rotate(-30, -10, -28) scale(${petScale})"/>
              <ellipse cx="10" cy="-28" rx="8" ry="12" fill="#a855f7" transform="rotate(30, 10, -28) scale(${petScale})"/>
              <ellipse cx="-10" cy="-8" rx="9" ry="13" fill="#c084fc" transform="rotate(-30, -10, -8) scale(${petScale})"/>
              <ellipse cx="10" cy="-8" rx="9" ry="13" fill="#a855f7" transform="rotate(30, 10, -8) scale(${petScale})"/>
              <ellipse cx="-8" cy="12" rx="8" ry="11" fill="#c084fc" transform="rotate(-20, -8, 12) scale(${petScale})"/>
              <ellipse cx="8" cy="12" rx="8" ry="11" fill="#a855f7" transform="rotate(20, 8, 12) scale(${petScale})"/>
            </g>
          </svg>
        `;
        break;

      case 'cherry':
      default:
        svg = `
          <svg viewBox="0 0 100 100" width="100%" height="100%" style="transform: scale(${scale}); transform-origin: center; transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);">
            <g transform="translate(50, 50)">
              ${[0, 72, 144, 216, 288].map(deg => `
                <path d="M 0 0 C -16 -16, -22 -38, -6 -42 C 0 -40, 0 -36, 0 -36 C 0 -36, 0 -40, 6 -42 C 22 -38, 16 -16, 0 0" fill="#f472b6" stroke="#fbcfe8" stroke-width="2" transform="rotate(${deg}) scale(${petScale})"/>
              `).join('')}
              <circle cx="0" cy="0" r="12" fill="#fef08a"/>
              <circle cx="0" cy="0" r="7" fill="#facc15"/>
            </g>
          </svg>
        `;
        break;
    }
    this.cursorEl.innerHTML = svg;
  }

  attachMouseEvents() {
    window.addEventListener('mousemove', (e) => {
      if (!this.cursorEl) return;
      this.cursorEl.style.left = `${e.clientX}px`;
      this.cursorEl.style.top = `${e.clientY}px`;

      // Spawn subtle petal particle trail
      if (this.trailEnabled) {
        const now = Date.now();
        if (now - this.lastTrailTime > 65) {
          this.createTrailParticle(e.clientX, e.clientY);
          this.lastTrailTime = now;
        }
      }
    });

    // Detect hover on interactive elements to bloom the flower
    document.addEventListener('mouseover', (e) => {
      const interactive = e.target.closest('button, a, input, select, textarea, .custom-checkbox-wrapper, .task-card, .mood-btn, .view-tab, [role="button"]');
      if (interactive) {
        this.updateCursorSvg(true);
      }
    });

    document.addEventListener('mouseout', (e) => {
      const interactive = e.target.closest('button, a, input, select, textarea, .custom-checkbox-wrapper, .task-card, .mood-btn, .view-tab, [role="button"]');
      if (interactive) {
        this.updateCursorSvg(false);
      }
    });
  }

  createTrailParticle(x, y) {
    const particle = document.createElement('div');
    particle.className = 'petal-trail-particle';
    particle.style.left = `${x}px`;
    particle.style.top = `${y}px`;

    const colors = {
      cherry: '#fbcfe8',
      daisy: '#fef08a',
      forgetmenot: '#bae6fd',
      clover: '#bbf7d0',
      lavender: '#e9d5ff'
    };
    const c = colors[this.cursorType] || '#fbcfe8';

    particle.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 20 20">
        <ellipse cx="10" cy="10" rx="7" ry="5" fill="${c}" opacity="0.85" transform="rotate(${Math.random() * 360} 10 10)"/>
      </svg>
    `;

    document.body.appendChild(particle);
    setTimeout(() => {
      particle.remove();
    }, 650);
  }

  initTouchSparkles() {
    window.addEventListener('touchstart', (e) => {
      const touch = e.touches[0];
      if (touch) {
        this.createTrailParticle(touch.clientX, touch.clientY);
        this.createTrailParticle(touch.clientX + (Math.random() * 20 - 10), touch.clientY + (Math.random() * 20 - 10));
      }
    }, { passive: true });
  }
}

window.flowerCursor = new FlowerCursorManager();

