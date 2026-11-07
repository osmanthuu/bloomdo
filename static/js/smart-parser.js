// === SMART NATURAL LANGUAGE QUICK-ADD PARSER ===

class SmartQuickAddParser {
  static parse(inputText) {
    let text = inputText.trim();
    if (!text) return null;

    let priority = 'medium';
    let category = null;
    let dueDate = '';
    let dueTime = '';
    let estimateMinutes = 0;

    // 1. Extract Priority (!high, !urgent, !med, !low)
    const priorityMatch = text.match(/!(high|urgent|med|medium|low)\b/i);
    if (priorityMatch) {
      const p = priorityMatch[1].toLowerCase();
      if (p === 'urgent' || p === 'high') priority = 'high';
      else if (p === 'low') priority = 'low';
      else priority = 'medium';
      text = text.replace(priorityMatch[0], '');
    }

    // 2. Extract Category / Tag (#tagname)
    const tagMatch = text.match(/#([\w\-]+)/);
    if (tagMatch) {
      category = tagMatch[1];
      // Capitalize first letter
      category = category.charAt(0).toUpperCase() + category.slice(1);
      text = text.replace(tagMatch[0], '');
    }

    // 3. Extract Time Estimate (~30m, ~1h, ~90m)
    const estMatch = text.match(/~(\d+)(m|min|mins|h|hr|hours?)\b/i);
    if (estMatch) {
      const num = parseInt(estMatch[1], 10);
      const unit = estMatch[2].toLowerCase();
      if (unit.startsWith('h')) {
        estimateMinutes = num * 60;
      } else {
        estimateMinutes = num;
      }
      text = text.replace(estMatch[0], '');
    }

    // 4. Extract Specific Times (5pm, 5:30pm, 17:00, 9am, noon, midnight)
    const timeMatch = text.match(/\b(noon|midnight|((0?[1-9]|1[0-2])(:[0-5][0-9])?\s*(am|pm))|(([01]?[0-9]|2[0-3]):[0-5][0-9]))\b/i);
    if (timeMatch) {
      const matchedStr = timeMatch[0].toLowerCase();
      if (matchedStr === 'noon') {
        dueTime = '12:00';
      } else if (matchedStr === 'midnight') {
        dueTime = '23:59';
      } else if (matchedStr.includes('am') || matchedStr.includes('pm')) {
        let isPm = matchedStr.includes('pm');
        let cleanTime = matchedStr.replace(/am|pm|\s/g, '');
        let parts = cleanTime.split(':');
        let h = parseInt(parts[0], 10);
        let m = parts[1] ? parts[1].padStart(2, '0') : '00';
        if (isPm && h < 12) h += 12;
        if (!isPm && h === 12) h = 0;
        dueTime = `${String(h).padStart(2, '0')}:${m}`;
      } else if (matchedStr.includes(':')) {
        let parts = matchedStr.split(':');
        dueTime = `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
      }
      text = text.replace(timeMatch[0], '');
    }

    // 5. Extract Relative Dates (today, tomorrow, tonight, in 2 hours, weekdays)
    const today = new Date();

    const inHoursMatch = text.match(/\bin\s+(\d+)\s+hours?\b/i);
    if (inHoursMatch) {
      const hrs = parseInt(inHoursMatch[1], 10);
      const future = new Date(today.getTime() + hrs * 60 * 60 * 1000);
      dueDate = future.toISOString().split('T')[0];
      dueTime = `${String(future.getHours()).padStart(2, '0')}:${String(future.getMinutes()).padStart(2, '0')}`;
      text = text.replace(inHoursMatch[0], '');
    }

    if (!dueDate) {
      if (/\btoday\b/i.test(text)) {
        dueDate = today.toISOString().split('T')[0];
        text = text.replace(/\btoday\b/i, '');
      } else if (/\btomorrow\b/i.test(text)) {
        const tom = new Date(today);
        tom.setDate(today.getDate() + 1);
        dueDate = tom.toISOString().split('T')[0];
        text = text.replace(/\btomorrow\b/i, '');
      } else if (/\btonight\b/i.test(text)) {
        dueDate = today.toISOString().split('T')[0];
        if (!dueTime) dueTime = '20:00';
        text = text.replace(/\btonight\b/i, '');
      } else if (/\bnext\s+week\b/i.test(text)) {
        const nextWk = new Date(today);
        nextWk.setDate(today.getDate() + 7);
        dueDate = nextWk.toISOString().split('T')[0];
        text = text.replace(/\bnext\s+week\b/i, '');
      } else {
        const weekdays = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
        const dayMatch = text.match(/\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i);
        if (dayMatch) {
          const targetDay = dayMatch[2].toLowerCase();
          const targetIdx = weekdays.indexOf(targetDay);
          const currentIdx = today.getDay();
          let diff = (targetIdx - currentIdx + 7) % 7;
          if (diff === 0 || dayMatch[1]) diff += 7; // if today is monday and user typed monday, assume next week
          const targetDate = new Date(today);
          targetDate.setDate(today.getDate() + diff);
          dueDate = targetDate.toISOString().split('T')[0];
          text = text.replace(dayMatch[0], '');
        }
      }
    }

    // Clean remaining title
    let title = text.replace(/\s+/g, ' ').trim();
    if (!title) title = "New Cute Task";

    return {
      title,
      dueDate,
      dueTime,
      priority,
      category,
      estimateMinutes
    };
  }
}

window.SmartQuickAddParser = SmartQuickAddParser;
