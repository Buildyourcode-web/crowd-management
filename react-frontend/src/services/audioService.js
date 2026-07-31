/**
 * Audio service – mirrors the NotificationManager.playNotificationSound logic
 * from the original notifications.js
 */

const activeAudios = {};

const SOUND_MAP = {
  standard: '/audio/alert-notification.mp3',
  danger: '/audio/Danger-alert.mp3',
  red_zone: '/audio/red-zone-alert.mp3',
  orange: '/audio/Zone-Orange.mp3',
};

const VOLUME_MAP = {
  standard: 0.55,
  danger: 0.70,
  red_zone: 0.70,
  orange: 0.55,
};

export function playSound(type = 'standard') {
  try {
    stopSound(type);
    const url = SOUND_MAP[type] || SOUND_MAP.standard;
    const audio = new Audio(url);
    audio.volume = VOLUME_MAP[type] ?? 0.55;
    activeAudios[type] = audio;
    audio.play().catch(() => {
      // Browser autoplay policy – silently defer
    });
  } catch {
    // ignore
  }
}

export function stopSound(type) {
  try {
    if (activeAudios[type]) {
      activeAudios[type].pause();
      activeAudios[type].currentTime = 0;
      delete activeAudios[type];
    }
  } catch {
    // ignore
  }
}

/** Warm up browser audio channel on first user interaction */
let warmedUp = false;
export function warmUpAudio() {
  if (warmedUp) return;
  warmedUp = true;
  try {
    const audio = new Audio(SOUND_MAP.standard);
    audio.volume = 0.001;
    audio.play().catch(() => {});
  } catch {
    // ignore
  }
}
