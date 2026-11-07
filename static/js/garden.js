// === VIRTUAL BLOOMING GARDEN ===

class PastelGarden {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.flowers = [];
  }

  async loadFlowers() {
    try {
      const res = await fetch('/api/garden');
      if (res.ok) {
        this.flowers = await res.json();
        this.render();
      }
    } catch (e) {
      console.log('Error loading garden:', e);
    }
  }

  addFlower(flowerData) {
    this.flowers.push(flowerData);
    this.render();
  }

  render() {
    if (!this.container) return;
    this.container.innerHTML = '';

    // Render each flower on the meadow
    this.flowers.forEach((flower, idx) => {
      const el = document.createElement('div');
      el.className = 'garden-flower-element garden-flower-bloom';
      el.style.left = `${flower.x_pct}%`;
      el.style.bottom = `${100 - flower.y_pct}%`;
      el.style.width = '42px';
      el.style.height = '62px';
      el.title = `Bloomed on ${flower.bloom_date} (${flower.flower_type.toUpperCase()})`;

      el.innerHTML = this.getFlowerSVG(flower.flower_type, flower.color);
      this.container.appendChild(el);
    });

    // Update flower count badge if present
    const countBadge = document.getElementById('garden-flower-count');
    if (countBadge) {
      countBadge.innerText = `${this.flowers.length} Flowers Bloomed 💐`;
    }
  }

  getFlowerSVG(type, color) {
    switch (type) {
      case 'daisy':
        return `
          <svg viewBox="0 0 50 70" width="100%" height="100%">
            <path d="M 25 35 Q 26 55 25 70" stroke="#4ade80" stroke-width="4" stroke-linecap="round" fill="none"/>
            <ellipse cx="18" cy="52" rx="6" ry="3" fill="#86efac" transform="rotate(-30 18 52)"/>
            <ellipse cx="32" cy="48" rx="6" ry="3" fill="#86efac" transform="rotate(30 32 48)"/>
            <g transform="translate(25, 25)">
              ${[0, 45, 90, 135, 180, 225, 270, 315].map(d => `
                <ellipse cx="0" cy="-14" rx="4" ry="9" fill="#fef9c3" stroke="#fef08a" transform="rotate(${d})"/>
              `).join('')}
              <circle cx="0" cy="0" r="7" fill="#facc15"/>
            </g>
          </svg>
        `;

      case 'sunflower':
        return `
          <svg viewBox="0 0 50 70" width="100%" height="100%">
            <path d="M 25 35 Q 27 55 25 70" stroke="#4ade80" stroke-width="4.5" stroke-linecap="round" fill="none"/>
            <ellipse cx="17" cy="54" rx="7" ry="3.5" fill="#86efac" transform="rotate(-35 17 54)"/>
            <ellipse cx="33" cy="49" rx="7" ry="3.5" fill="#86efac" transform="rotate(35 33 49)"/>
            <g transform="translate(25, 24)">
              ${[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map(d => `
                <ellipse cx="0" cy="-14" rx="4" ry="10" fill="#facc15" transform="rotate(${d})"/>
              `).join('')}
              <circle cx="0" cy="0" r="8" fill="#78350f"/>
            </g>
          </svg>
        `;

      case 'forgetmenot':
        return `
          <svg viewBox="0 0 50 70" width="100%" height="100%">
            <path d="M 25 35 Q 24 55 25 70" stroke="#4ade80" stroke-width="3.5" stroke-linecap="round" fill="none"/>
            <ellipse cx="18" cy="50" rx="5" ry="2.5" fill="#86efac" transform="rotate(-25 18 50)"/>
            <g transform="translate(25, 25)">
              ${[0, 72, 144, 216, 288].map(d => `
                <ellipse cx="0" cy="-12" rx="6" ry="8" fill="#38bdf8" stroke="#bae6fd" transform="rotate(${d})"/>
              `).join('')}
              <circle cx="0" cy="0" r="5" fill="#fef08a"/>
            </g>
          </svg>
        `;

      case 'lavender':
        return `
          <svg viewBox="0 0 50 70" width="100%" height="100%">
            <line x1="25" y1="10" x2="25" y2="70" stroke="#4ade80" stroke-width="3" stroke-linecap="round"/>
            <ellipse cx="20" cy="18" rx="4" ry="6" fill="#c084fc" transform="rotate(-30 20 18)"/>
            <ellipse cx="30" cy="18" rx="4" ry="6" fill="#a855f7" transform="rotate(30 30 18)"/>
            <ellipse cx="20" cy="28" rx="4.5" ry="6.5" fill="#c084fc" transform="rotate(-30 20 28)"/>
            <ellipse cx="30" cy="28" rx="4.5" ry="6.5" fill="#a855f7" transform="rotate(30 30 28)"/>
            <ellipse cx="20" cy="38" rx="4" ry="6" fill="#c084fc" transform="rotate(-25 20 38)"/>
            <ellipse cx="30" cy="38" rx="4" ry="6" fill="#a855f7" transform="rotate(25 30 38)"/>
          </svg>
        `;

      case 'cherry':
      default:
        return `
          <svg viewBox="0 0 50 70" width="100%" height="100%">
            <path d="M 25 35 Q 26 55 25 70" stroke="#4ade80" stroke-width="4" stroke-linecap="round" fill="none"/>
            <ellipse cx="17" cy="52" rx="6" ry="3" fill="#86efac" transform="rotate(-30 17 52)"/>
            <ellipse cx="33" cy="48" rx="6" ry="3" fill="#86efac" transform="rotate(30 33 48)"/>
            <g transform="translate(25, 25)">
              ${[0, 72, 144, 216, 288].map(d => `
                <circle cx="0" cy="-12" r="8" fill="${color || '#f472b6'}" transform="rotate(${d})"/>
              `).join('')}
              <circle cx="0" cy="0" r="5" fill="#fef08a"/>
            </g>
          </svg>
        `;
    }
  }

  async clearGarden() {
    try {
      const res = await fetch('/api/garden/clear', { method: 'POST' });
      if (res.ok) {
        this.flowers = [];
        this.render();
      }
    } catch (e) {
      console.log('Error clearing garden:', e);
    }
  }
}

window.PastelGarden = PastelGarden;

